import json
import re
from datetime import datetime


def parse_db_to_model_inputs(json_path: str):
    db = json.load(open(json_path, "r", encoding="utf-8"))

    # Tempo 0 do roteiro (em horas)
    t0 = datetime.fromisoformat(db["metadata"]["inicio"])

    # Nós / cidades
    V = list(db["nos"].keys())

    # Custos por cidade
    C_hotel = {i: float(db["nos"][i]["custo_diaria_hotel"]) for i in V}
    C_food  = {i: float(db["nos"][i]["custo_refeicao_diaria"]) for i in V}
    C_transfer = {i: float(db["nos"][i]["transporte"]["transfer_ida_volta"]) for i in V}

    # Voos: construir F[(i,j)] = [f1,f2,...] e DEP/DUR/C[(i,j,f)]
    F, DEP, DUR, C = {}, {}, {}, {}

    for a in db["arestas"]:
        i, j = a["origem"], a["destino"]

        # id do voo (único) — dá pra usar só voo_cod se você preferir
        f = f'{a["voo_cod"]}_{a["data_voo"]}_{a["hora_saida"]}'

        F.setdefault((i, j), []).append(f)

        # DEP: horas desde t0
        dep_dt = datetime.fromisoformat(f'{a["data_voo"]} {a["hora_saida"]}')
        dep_h = (dep_dt - t0).total_seconds() / 3600.0

        # DUR vem em minutos no JSON -> horas
        dur_h = float(a["tempo_voo"]) / 60.0

        DEP[(i, j, f)] = dep_h
        DUR[(i, j, f)] = dur_h
        C[(i, j, f)]   = float(a["custo_passagem"])

    return V, F, DEP, DUR, C, C_hotel, C_food, C_transfer


def encontrar_voo(database, origem, destino, voo_id):
    """
    Função auxiliar para localizar um voo no database.json
    
    Busca por:
    - origem e destino
    - voo_id no formato VOOCOD_DATA_HORA ou match parcial
    
    Retorna o dict da aresta ou None se não encontrado
    """
    # Tentar extrair componentes do voo_id
    partes = voo_id.split('_')
    
    # Buscar nas arestas
    for aresta in database.get("arestas", []):
        # Match exato de origem e destino
        if aresta["origem"] != origem or aresta["destino"] != destino:
            continue
        
        # Tentar match completo: voo_cod_data_hora
        if len(partes) >= 3:
            voo_cod_esperado = partes[0]
            data_esperada = partes[1]
            hora_esperada = partes[2]
            
            if (aresta.get("voo_cod") == voo_cod_esperado and
                aresta.get("data_voo") == data_esperada and
                aresta.get("hora_saida") == hora_esperada):
                return aresta
        
        # Fallback: match só pelo voo_cod se tiver apenas um voo nessa rota
        if len(partes) >= 1:
            if aresta.get("voo_cod") == partes[0]:
                return aresta
    
    return None


def build_front_json_from_solution(model, db, origin, dest, dias_vars_prefix="dias_"):
    """
    model: LpProblem resolvido (PuLP)
    db: dict já carregado do database.json
    origin/dest: strings
    """

    # ---------------------------
    # 1) Indexar voos do DB: (i,j,fid) -> info
    # ---------------------------
    flight_by_fid = {}
    flights_by_ij = {}

    for a in db["arestas"]:
        i, j = a["origem"], a["destino"]
        fid = f'{a["voo_cod"]}_{a["data_voo"]}_{a["hora_saida"]}'  # mesmo id do parser
        flight_by_fid[(i, j, fid)] = a
        flights_by_ij.setdefault((i, j), []).append(fid)

    # ---------------------------
    # 2) Pegar voos escolhidos x_{i}_{j}_{fid} == 1
    # ---------------------------
    chosen = []  # list of (i,j,fid)
    pat = re.compile(r"^x_(.+?)_(.+?)_(.+)$")

    for v in model.variables():
        if v.varValue is None or v.varValue < 0.5:
            continue
        m = pat.match(v.name)
        if m:
            i, j, fid = m.group(1), m.group(2), m.group(3)
            chosen.append((i, j, fid))

    # ---------------------------
    # 3) Construir caminho (origem -> ... -> destino)
    # ---------------------------
    # como é rota aberta ida, deve ter 1 arco saindo de cada intermediária, etc.
    next_city = {}
    trecho_by_city = {}

    for i, j, fid in chosen:
        next_city[i] = j
        trecho_by_city[i] = (i, j, fid)

    caminho = [origin]
    trechos = []
    cur = origin
    guard = 0
    while cur != dest and guard < 100:
        guard += 1
        if cur not in next_city:
            break  # rota incompleta (debug)
        i, j, fid = trecho_by_city[cur]
        
        # Buscar voo usando função auxiliar mais robusta
        a = flight_by_fid.get((i, j, fid), None)
        
        # Se não encontrou, tentar com a função auxiliar
        if not a:
            a = encontrar_voo(db, i, j, fid)

        # info do voo pro front (preencher com dados reais do database)
        voo_info = {
            "id": fid,
            "cia": a.get("cia", a.get("companhia", "")) if a else "",
            "codigo": a.get("voo_cod", "") if a else "",
            "data": a.get("data_voo", "") if a else "",
            "saida": a.get("hora_saida", "") if a else "",
            "duracao_min": float(a.get("tempo_voo", 0.0)) if a else None,
            "preco": float(a.get("custo_passagem", 0.0)) if a else 0.0
        }

        trechos.append({"origem": i, "destino": j, "voo": voo_info})
        caminho.append(j)
        cur = j

    # ---------------------------
    # 4) Dias por cidade (dias_i inteiros) para custos
    # ---------------------------
    dias = {}
    for v in model.variables():
        if v.varValue is None:
            continue
        if v.name.startswith(dias_vars_prefix):
            city = v.name[len(dias_vars_prefix):]
            dias[city] = int(round(v.varValue))

    # Se o front só mostrar custos do "destino" (ou cidades visitadas)
    visited = set(caminho)  # você pode trocar por y_i==1 se preferir

    # ---------------------------
    # 5) Custos abertos
    # ---------------------------
    # Voos: soma dos preços dos escolhidos (usando dados reais do database)
    custo_voos = 0.0
    for i, j, fid in chosen:
        a = flight_by_fid.get((i, j, fid), None)
        
        # Se não encontrou, tentar com a função auxiliar
        if not a:
            a = encontrar_voo(db, i, j, fid)
        
        if a:
            custo_voos += float(a.get("custo_passagem", 0.0))

    # Hospedagem / Alimentação / Transporte: por cidade * diárias
    detalhes_hosp = []
    detalhes_food = []
    detalhes_transp = []

    custo_hosp = 0.0
    custo_food = 0.0
    custo_transp = 0.0

    # parâmetros do JSON
    nos = db["nos"]

    for city in visited:
        diarias = int(dias.get(city, 0))
        if diarias <= 0:
            continue

        diaria_hotel = float(nos[city].get("custo_diaria_hotel", 0.0))
        diaria_food  = float(nos[city].get("custo_refeicao_diaria", 0.0))
        diaria_trans = float(nos[city].get("transporte", {}).get("transfer_ida_volta", 0.0))

        th = diaria_hotel * diarias
        tf = diaria_food  * diarias
        tt = diaria_trans * diarias

        custo_hosp += th
        custo_food += tf
        custo_transp += tt

        detalhes_hosp.append({"cidade": city, "diarias": diarias, "diaria": diaria_hotel, "total": th})
        detalhes_food.append({"cidade": city, "diarias": diarias, "custo_dia": diaria_food, "total": tf})
        detalhes_transp.append({"cidade": city, "diarias": diarias, "custo_dia": diaria_trans, "total": tt})

    total = custo_voos + custo_hosp + custo_food + custo_transp

    # ---------------------------
    # 6) JSON final
    # ---------------------------
    out = {
        "rota": {
            "origem": origin,
            "destino": dest,
            "caminho": caminho,
            "trechos": trechos
        },
        "custos": {
            "total": float(total),
            "voos": float(custo_voos),
            "hospedagem": float(custo_hosp),
            "alimentacao": float(custo_food),
            "transporte": float(custo_transp)
        },
        "detalhes": {
            "hospedagem": detalhes_hosp,
            "alimentacao": detalhes_food,
            "transporte": detalhes_transp
        }
    }

    return out