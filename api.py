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

    # 1. Carrega dados do banco
    try:
        V, F, DEP, DUR, C, C_hotel, C_food, C_transfer = parse_db_to_model_inputs(JSON_PATH)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error parsing database: {str(e)}")

    # 2. Validações básicas
    if request.ida_volta:
        # O modelo atual (otm_model.py) tem assert origin != dest.
        # Para suportar ida e volta, seria necessário adaptar o modelo.
        raise HTTPException(status_code=501, detail="Round trip (ida_volta=True) not currently supported.")

    origin = request.origem
    dest = request.destino
    
    if origin not in V:
        raise HTTPException(status_code=400, detail=f"Origin {origin} not found in database")
    if dest not in V:
        raise HTTPException(status_code=400, detail=f"Destination {dest} not found in database")

    # 3. Configuração de Dias (d_min, d_max, D_total)
    # Calcula total de dias solicitado
    total_days_requested = sum(request.dias_por_cidade.values())
    D_total = float(total_days_requested)
    
    # Se D_total for 0 (nenhum dia especificado), definimos um padrão?
    # Vamos assumir que o usuário deve especificar dias.
    if D_total <= 0:
         # Fallback ou erro? Vamos deixar 7 dias padrão se vazio, mas o usuário passou dias.
         pass

    d_min = {i: 0.0 for i in V}
    d_max = {i: D_total for i in V} # Permite flexibilidade por padrão

    # Cidades com dias fixos
    cities_to_force_visit = set(request.locais_visitar)
    
    for city, days in request.dias_por_cidade.items():
        if city in V:
            d_min[city] = float(days)
            d_max[city] = float(days)
            if days > 0:
                cities_to_force_visit.add(city)

    # 4. Custos efetivos (toggle via request)
    # Se incluir_X é false, zeramos o custo para não influenciar a otimização (ou deixamos 0).
    C_hotel_eff = C_hotel.copy() if request.incluir_hospedagem else {i: 0.0 for i in V}
    C_food_eff = C_food.copy() if request.incluir_refeicao else {i: 0.0 for i in V}
    C_transfer_eff = C_transfer.copy() if request.incluir_transporte else {i: 0.0 for i in V}

    # 5. Parâmetros de passageiros
    nA = request.numero_adultos
    nC = request.numero_criancas
    # Assumindo alpha=0.75 para crianças se não especificado no modelo
    alpha = 0.75 

    # 6. TMAX (Tempo máximo de voo)
    # Não veio no JSON, definindo um valor alto para não restringir indevidamente
    TMAX = 48.0 

    # 7. Construção do Modelo
    model = build_trip_milp_pulp(
        V=V, origin=origin, dest=dest,
        F=F, DEP=DEP, DUR=DUR, C=C,
        tau=24.0,
        D_total=D_total,
        TMAX=TMAX,
        d_min=d_min, d_max=d_max,
        C_hotel=C_hotel_eff, C_food=C_food_eff, 
        nA=nA, nC=nC, alpha=alpha,
        C_transfer=C_transfer_eff,
    )

    # 8. Constraints Adicionais: Forçar visita
    variables = model.variablesDict()
    for local in cities_to_force_visit:
        if local in V and local != origin and local != dest:
            # y_local == 1
            if f"y_{local}" in variables:
                model += variables[f"y_{local}"] == 1, f"Force_visit_{local}"

    # 9. Resolução
    # msg=False para não sujar o log da API
    status = model.solve(PULP_CBC_CMD(msg=False))
    
    if LpStatus[status] != 'Optimal':
        return {
            "status": LpStatus[status],
            "message": "Could not find an optimal solution. Check constraints (e.g., flight connectivity).",
            "rota": None
        }

    # 10. Exportação
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        db = json.load(f)

    # Nota: build_front_json_from_solution usa o modelo resolvido para montar o JSON
    result_json = build_front_json_from_solution(model, db, origin=origin, dest=dest)
    
    return result_json

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
