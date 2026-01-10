from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
from pulp import PULP_CBC_CMD, LpStatus
import json
import os

from otm_model import build_trip_milp_pulp
from import_export_json import parse_db_to_model_inputs, build_front_json_from_solution

app = FastAPI()

class TripRequest(BaseModel):
    ida_volta: bool
    origem: str
    destino: str
    locais_visitar: List[str]
    data_ida: str
    numero_adultos: int
    numero_criancas: int
    dias_por_cidade: Dict[str, int]
    incluir_refeicao: bool
    incluir_hospedagem: bool
    incluir_transporte: bool

JSON_PATH = "database.json"

@app.post("/optimize")
def optimize_trip(request: TripRequest):
    if not os.path.exists(JSON_PATH):
        raise HTTPException(status_code=500, detail="Database file not found")

    # Carrega dados do banco
    try:
        V, F, DEP, DUR, C, C_hotel, C_food, C_transfer = parse_db_to_model_inputs(JSON_PATH)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error parsing database: {str(e)}")

    # Configurações baseadas no request
    origin = request.origem
    dest = request.destino
    
    # Verifica se origem e destino existem no grafo
    if origin not in V:
        raise HTTPException(status_code=400, detail=f"Origin {origin} not found in database")
    if dest not in V:
        raise HTTPException(status_code=400, detail=f"Destination {dest} not found in database")

    # Configura dias mínimos e máximos
    # Inicializa com 0 para todos
    d_min = {i: 0.0 for i in V}
    d_max = {i: 0.0 for i in V} # Inicialmente 0, vamos abrir para quem for visitado

    # Cidades a visitar (incluindo origem e destino se necessário, mas o modelo trata origem/destino separado)
    # O modelo espera que d_max seja o horizonte total para nós não visitados ou algo assim?
    # Na verdade, o modelo usa d_max[i] * y[i]. Se y[i]=0, d[i]=0.
    # Se y[i]=1, d[i] <= d_max[i].
    
    # Vamos calcular o total de dias solicitado
    total_days_requested = sum(request.dias_por_cidade.values())
    D_total = float(total_days_requested)

    # Para cidades no request, define min e max iguais ao solicitado (fixo)
    # Ou flexível? O input sugere "dias_por_cidade" como algo definido.
    # Vamos assumir que é fixo para as cidades listadas.
    
    for city, days in request.dias_por_cidade.items():
        if city in V:
            d_min[city] = float(days)
            d_max[city] = float(days)
        else:
             # Se a cidade solicitada não está no banco, pode ser erro ou ignorar
             pass

    # Para as demais cidades (não listadas no dias_por_cidade), d_min=0, d_max=D_total
    # (caso o modelo decida visitar alguma cidade de conexão e pernoitar, embora o input não peça)
    # Mas se o usuário passou "locais_visitar", talvez ele queira forçar visita.
    # O modelo atual (otm_model) não tem restrição explícita "obrigado a visitar X" exceto origem/destino.
    # Se quisermos forçar visita aos "locais_visitar", precisaríamos adicionar constraints y[i] == 1.
    # O código original main.py não mostrava como forçar visitas intermediárias, apenas origem/dest.
    # Vamos assumir que se está em "dias_por_cidade" com dias > 0, o modelo vai tentar cumprir d_min.
    # Se d_min > 0, então y[i] deve ser 1 (pois d[i] >= d_min * y[i] -> se y=0, d=0 ok. Se y=1, d>=d_min).
    # Espere, se d_min > 0 e y=0, a constraint é 0 >= 0. Então não força visita.
    # Para forçar visita, precisaríamos de y[i] == 1 para i em locais_visitar.
    # Vou adicionar essa lógica de forçar visita se estiver na lista.

    # Ajuste de d_max para todos os nós para permitir flexibilidade se não especificado
    for i in V:
        if i not in request.dias_por_cidade:
            d_max[i] = D_total # Pode ficar até o tempo todo se quiser (teoricamente)

    # Parâmetros de custo
    # Se o usuário não quer incluir algo, zeramos o custo no modelo?
    # Ou o modelo deve ignorar? O modelo minimiza custo. Se zerarmos, ele "gosta" de usar.
    # Se o usuário diz "incluir_hospedagem: false", talvez signifique que ele não paga (custo 0) 
    # ou que não quer considerar isso na otimização.
    # Geralmente em apps de viagem, "incluir" significa "calcule isso pra mim".
    # Se for false, assumimos custo 0 para o otimizador não se preocupar, ou mantemos custo e ignoramos no final?
    # Vamos assumir que se false, o custo é 0 para o algoritmo (não penaliza).
    
    C_hotel_eff = C_hotel.copy() if request.incluir_hospedagem else {i: 0.0 for i in V}
    C_food_eff = C_food.copy() if request.incluir_refeicao else {i: 0.0 for i in V}
    C_transfer_eff = C_transfer.copy() if request.incluir_transporte else {i: 0.0 for i in V}

    # Número de pessoas
    nA = request.numero_adultos
    nC = request.numero_criancas
    # alpha não foi passado, assumindo 1.0 ou padrão
    alpha = 0.5 # Crianças pagam metade em comida? O main.py usava 1.0. Vamos manter padrão do modelo se não especificado.
    # No main.py: nA=1, nC=0, alpha=1.0.
    # Vamos usar alpha=0.5 como chute razoável para crianças, ou 1.0 se preferir conservador.
    
    # TMAX: tempo máximo de voo. Não veio no JSON. Vamos chutar alto ou baseado em D_total * 24?
    # O main.py usava 20.0. Vamos deixar fixo ou proporcional.
    TMAX = 48.0 # 48 horas de voo máximo

    # Constrói o modelo
    model = build_trip_milp_pulp(
        V=V, origin=origin, dest=dest,
        F=F, DEP=DEP, DUR=DUR, C=C,
        tau=24.0,
        D_total=D_total,
        TMAX=TMAX,
        d_min=d_min, d_max=d_max,
        C_hotel=C_hotel_eff, C_food=C_food_eff, 
        nA=nA, nC=nC, alpha=0.75, # Chute para alpha
        C_transfer=C_transfer_eff,
    )

    # Forçar visita aos locais intermediários
    # O modelo retorna 'model', podemos adicionar constraints extras antes de resolver
    variables = model.variablesDict()
    for local in request.locais_visitar:
        if local in V and local != origin and local != dest:
            # y_local == 1
            if f"y_{local}" in variables:
                model += variables[f"y_{local}"] == 1, f"Force_visit_{local}"

    # Resolve
    status = model.solve(PULP_CBC_CMD(msg=False))
    
    if LpStatus[status] != 'Optimal':
        return {
            "status": LpStatus[status],
            "message": "Could not find an optimal solution",
            "rota": None
        }

    # Prepara resposta
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        db = json.load(f)

    result_json = build_front_json_from_solution(model, db, origin=origin, dest=dest)
    
    return result_json

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
