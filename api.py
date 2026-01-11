from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
from pulp import PULP_CBC_CMD, LpStatus
import json
import os

from otm_model import build_trip_milp_pulp
from import_export_json import parse_db_to_model_inputs, build_front_json_from_solution, get_available_date_range
from fallback_optimizer import optimize_with_fallback
from multiple_optimizer import gerar_multiplas_opcoes

app = FastAPI(title="SmartTrip API", version="1.0.0")

# =========================
# CORS (para React)
# =========================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


class MultipleOptionsRequest(BaseModel):
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
    numero_opcoes: Optional[int] = 3


JSON_PATH = "database.json"


@app.get("/")
def health_check():
    return {"status": "ok"}


@app.get("/available-dates")
def get_available_dates():
    """Retorna o intervalo de datas disponíveis para viagens"""
    if not os.path.exists(JSON_PATH):
        raise HTTPException(status_code=500, detail="Database file not found")
    
    try:
        date_range = get_available_date_range(JSON_PATH)
        return {
            "data_minima": date_range["data_minima"],
            "data_maxima": date_range["data_maxima"],
            "mensagem": f"Voos disponíveis de {date_range['data_minima']} até {date_range['data_maxima']}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao obter datas: {str(e)}")


@app.post("/optimize")
def optimize_trip(request: TripRequest):
    if not os.path.exists(JSON_PATH):
        raise HTTPException(status_code=500, detail="Database file not found")

    # 1. Carrega dados do banco
    try:
        V, F, DEP, DUR, C, C_hotel, C_food, C_transfer = parse_db_to_model_inputs(
            JSON_PATH, 
            user_start_date=request.data_ida
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error parsing database: {str(e)}")

    # 2. Validações básicas
    if request.ida_volta:
        raise HTTPException(
            status_code=501,
            detail="Round trip (ida_volta=True) not currently supported."
        )

    origin = request.origem
    dest = request.destino

    if origin not in V:
        raise HTTPException(status_code=400, detail=f"Origin {origin} not found in database")
    if dest not in V:
        raise HTTPException(status_code=400, detail=f"Destination {dest} not found in database")

    # 3. Dias
    total_days_requested = sum(request.dias_por_cidade.values())
    D_total = float(total_days_requested)

    d_min = {i: 0.0 for i in V}
    d_max = {i: D_total for i in V}

    cities_to_force_visit = set(request.locais_visitar)

    for city, days in request.dias_por_cidade.items():
        if city in V:
            d_min[city] = float(days)
            d_max[city] = float(days)
            if days > 0:
                cities_to_force_visit.add(city)

    # 4. Custos
    C_hotel_eff = C_hotel.copy() if request.incluir_hospedagem else {i: 0.0 for i in V}
    C_food_eff = C_food.copy() if request.incluir_refeicao else {i: 0.0 for i in V}
    C_transfer_eff = C_transfer.copy() if request.incluir_transporte else {i: 0.0 for i in V}

    # 5. Passageiros
    nA = request.numero_adultos
    nC = request.numero_criancas
    alpha = 0.75

    # 6. Parâmetros adicionais
    TMAX = 48.0

    # 7. Preparar parâmetros do modelo
    model_params = {
        'V': V,
        'origin': origin,
        'dest': dest,
        'F': F,
        'DEP': DEP,
        'DUR': DUR,
        'C': C,
        'tau': 24.0,
        'D_total': D_total,
        'TMAX': TMAX,
        'd_min': d_min,
        'd_max': d_max,
        'C_hotel': C_hotel_eff,
        'C_food': C_food_eff,
        'nA': nA,
        'nC': nC,
        'alpha': alpha,
        'C_transfer': C_transfer_eff,
    }

    # 8. Carregar database completo
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        db = json.load(f)

    # 9. Preparar dados da requisição
    request_data = {
        'origem': origin,
        'destino': dest,
        'data_ida': request.data_ida,
        'locais_visitar': list(cities_to_force_visit)
    }

    # 10. Usar sistema de fallback - GARANTE sempre retornar resposta válida
    result_json = optimize_with_fallback(
        request_data=request_data,
        db=db,
        model_params=model_params,
        build_result_func=build_front_json_from_solution
    )

    return result_json


@app.post("/optimize-multiple")
def optimize_trip_multiple_options(request: MultipleOptionsRequest):
    """
    Retorna múltiplas opções de rotas (3 melhores) com diferentes trade-offs
    - Opção 1: Mais Econômica (menor custo)
    - Opção 2: Melhor Custo-Benefício (equilibrada)
    - Opção 3: Mais Rápida e Confortável (menos tempo/escalas)
    """
    if not os.path.exists(JSON_PATH):
        raise HTTPException(status_code=500, detail="Database file not found")

    # 1. Carrega dados do banco
    try:
        V, F, DEP, DUR, C, C_hotel, C_food, C_transfer = parse_db_to_model_inputs(
            JSON_PATH, 
            user_start_date=request.data_ida
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error parsing database: {str(e)}")

    # 2. Validações básicas
    if request.ida_volta:
        raise HTTPException(
            status_code=501,
            detail="Round trip (ida_volta=True) not currently supported."
        )

    origin = request.origem
    dest = request.destino

    if origin not in V:
        raise HTTPException(status_code=400, detail=f"Origin {origin} not found in database")
    if dest not in V:
        raise HTTPException(status_code=400, detail=f"Destination {dest} not found in database")

    # 3. Dias
    total_days_requested = sum(request.dias_por_cidade.values())
    D_total = float(total_days_requested)

    d_min = {i: 0.0 for i in V}
    d_max = {i: D_total for i in V}

    cities_to_force_visit = set(request.locais_visitar)

    for city, days in request.dias_por_cidade.items():
        if city in V:
            d_min[city] = float(days)
            d_max[city] = float(days)
            if days > 0:
                cities_to_force_visit.add(city)

    # 4. Custos
    C_hotel_eff = C_hotel.copy() if request.incluir_hospedagem else {i: 0.0 for i in V}
    C_food_eff = C_food.copy() if request.incluir_refeicao else {i: 0.0 for i in V}
    C_transfer_eff = C_transfer.copy() if request.incluir_transporte else {i: 0.0 for i in V}

    # 5. Passageiros
    nA = request.numero_adultos
    nC = request.numero_criancas
    alpha = 0.75

    # 6. Parâmetros adicionais
    TMAX = 48.0

    # 7. Preparar parâmetros do modelo
    model_params = {
        'V': V,
        'origin': origin,
        'dest': dest,
        'F': F,
        'DEP': DEP,
        'DUR': DUR,
        'C': C,
        'tau': 24.0,
        'D_total': D_total,
        'TMAX': TMAX,
        'd_min': d_min,
        'd_max': d_max,
        'C_hotel': C_hotel_eff,
        'C_food': C_food_eff,
        'nA': nA,
        'nC': nC,
        'alpha': alpha,
        'C_transfer': C_transfer_eff,
    }

    # 8. Carregar database completo
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        db = json.load(f)

    # 9. Preparar dados da requisição
    request_data = {
        'origem': origin,
        'destino': dest,
        'data_ida': request.data_ida,
        'locais_visitar': list(cities_to_force_visit)
    }

    # 10. Gerar múltiplas opções
    result = gerar_multiplas_opcoes(
        request_data=request_data,
        db=db,
        model_params=model_params,
        build_result_func=build_front_json_from_solution,
        num_opcoes=request.numero_opcoes
    )

    return result
