"""
Sistema de Fallback para Otimização de Viagens
Garante que sempre seja retornada uma resposta válida
"""

import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from pulp import LpStatus, PULP_CBC_CMD
from otm_model import build_trip_milp_pulp
import json


def create_empty_route_response(origem: str, destino: str, error_msg: str = "Nenhuma solução encontrada") -> Dict:
    """
    Cria estrutura de resposta vazia/erro VÁLIDA (nunca retorna None)
    """
    return {
        "rota": {
            "origem": origem,
            "destino": destino,
            "caminho": [origem, destino],
            "trechos": []
        },
        "custos": {
            "total": 0.0,
            "voos": 0.0,
            "hospedagem": 0.0,
            "alimentacao": 0.0,
            "transporte": 0.0
        },
        "detalhes": {
            "hospedagem": [],
            "alimentacao": [],
            "transporte": []
        },
        "metadata": {
            "nivel_otimizacao": "erro",
            "nota": error_msg,
            "tempo_computacao": 0.0
        }
    }


def buscar_voo_direto(db: Dict, origem: str, destino: str, data_ida: str) -> Optional[Dict]:
    """
    Busca voo direto mais barato entre origem e destino
    """
    voos_diretos = [
        a for a in db.get("arestas", [])
        if a["origem"] == origem and a["destino"] == destino and a["data_voo"] == data_ida
    ]
    
    if not voos_diretos:
        return None
    
    # Retorna o mais barato
    return min(voos_diretos, key=lambda x: float(x["custo_passagem"]))


def buscar_voo_com_uma_escala(db: Dict, origem: str, destino: str, data_ida: str) -> Optional[List[Dict]]:
    """
    Busca rota com 1 escala: origem -> intermediaria -> destino
    Retorna lista de 2 voos ou None
    """
    voos_origem = [a for a in db.get("arestas", []) if a["origem"] == origem and a["data_voo"] == data_ida]
    
    if not voos_origem:
        return None
    
    melhor_rota = None
    menor_custo = float('inf')
    
    for voo1 in voos_origem:
        intermediaria = voo1["destino"]
        if intermediaria == destino:
            continue
        
        # Buscar voo da intermediária para destino (pode ser no mesmo dia ou próximo)
        data_voo1 = datetime.strptime(f"{voo1['data_voo']} {voo1['hora_saida']}", "%Y-%m-%d %H:%M:%S")
        duracao_voo1 = float(voo1["tempo_voo"]) / 60.0  # converter minutos para horas
        chegada_intermediaria = data_voo1 + timedelta(hours=duracao_voo1)
        
        # Tempo mínimo de conexão: 2 horas
        saida_minima = chegada_intermediaria + timedelta(hours=2)
        
        for voo2 in db.get("arestas", []):
            if voo2["origem"] != intermediaria or voo2["destino"] != destino:
                continue
            
            data_voo2 = datetime.strptime(f"{voo2['data_voo']} {voo2['hora_saida']}", "%Y-%m-%d %H:%M:%S")
            
            # Verificar se o voo 2 sai após o tempo mínimo de conexão
            if data_voo2 < saida_minima:
                continue
            
            # Verificar se a conexão não demora mais de 12 horas
            tempo_conexao = (data_voo2 - chegada_intermediaria).total_seconds() / 3600.0
            if tempo_conexao > 12:
                continue
            
            custo_total = float(voo1["custo_passagem"]) + float(voo2["custo_passagem"])
            
            if custo_total < menor_custo:
                menor_custo = custo_total
                melhor_rota = [voo1, voo2]
    
    return melhor_rota


def criar_rota_basica(db: Dict, origem: str, destino: str, data_ida: str, request_data: Dict) -> Dict:
    """
    Nível 4 - Fallback final: cria rota mais simples possível
    1. Tenta voo direto
    2. Tenta voo com 1 escala
    3. Retorna estrutura vazia se não houver nenhuma opção
    """
    # Tentar voo direto
    voo_direto = buscar_voo_direto(db, origem, destino, data_ida)
    
    if voo_direto:
        fid = f'{voo_direto["voo_cod"]}_{voo_direto["data_voo"]}_{voo_direto["hora_saida"]}'
        return {
            "rota": {
                "origem": origem,
                "destino": destino,
                "caminho": [origem, destino],
                "trechos": [
                    {
                        "origem": origem,
                        "destino": destino,
                        "voo": {
                            "id": fid,
                            "cia": voo_direto.get("cia", voo_direto.get("companhia", "")),
                            "codigo": voo_direto["voo_cod"],
                            "data": voo_direto["data_voo"],
                            "saida": voo_direto["hora_saida"],
                            "duracao_min": float(voo_direto["tempo_voo"]),
                            "preco": float(voo_direto["custo_passagem"])
                        }
                    }
                ]
            },
            "custos": {
                "total": float(voo_direto["custo_passagem"]),
                "voos": float(voo_direto["custo_passagem"]),
                "hospedagem": 0.0,
                "alimentacao": 0.0,
                "transporte": 0.0
            },
            "detalhes": {
                "hospedagem": [],
                "alimentacao": [],
                "transporte": []
            },
            "metadata": {
                "nivel_otimizacao": "basica",
                "nota": "Rota direta sem otimizações (solução de fallback)",
                "tempo_computacao": 0.0
            }
        }
    
    # Tentar voo com 1 escala
    rota_escala = buscar_voo_com_uma_escala(db, origem, destino, data_ida)
    
    if rota_escala:
        voo1, voo2 = rota_escala
        intermediaria = voo1["destino"]
        
        fid1 = f'{voo1["voo_cod"]}_{voo1["data_voo"]}_{voo1["hora_saida"]}'
        fid2 = f'{voo2["voo_cod"]}_{voo2["data_voo"]}_{voo2["hora_saida"]}'
        
        custo_total = float(voo1["custo_passagem"]) + float(voo2["custo_passagem"])
        
        return {
            "rota": {
                "origem": origem,
                "destino": destino,
                "caminho": [origem, intermediaria, destino],
                "trechos": [
                    {
                        "origem": origem,
                        "destino": intermediaria,
                        "voo": {
                            "id": fid1,
                            "cia": voo1.get("cia", voo1.get("companhia", "")),
                            "codigo": voo1["voo_cod"],
                            "data": voo1["data_voo"],
                            "saida": voo1["hora_saida"],
                            "duracao_min": float(voo1["tempo_voo"]),
                            "preco": float(voo1["custo_passagem"])
                        }
                    },
                    {
                        "origem": intermediaria,
                        "destino": destino,
                        "voo": {
                            "id": fid2,
                            "cia": voo2.get("cia", voo2.get("companhia", "")),
                            "codigo": voo2["voo_cod"],
                            "data": voo2["data_voo"],
                            "saida": voo2["hora_saida"],
                            "duracao_min": float(voo2["tempo_voo"]),
                            "preco": float(voo2["custo_passagem"])
                        }
                    }
                ]
            },
            "custos": {
                "total": custo_total,
                "voos": custo_total,
                "hospedagem": 0.0,
                "alimentacao": 0.0,
                "transporte": 0.0
            },
            "detalhes": {
                "hospedagem": [],
                "alimentacao": [],
                "transporte": []
            },
            "metadata": {
                "nivel_otimizacao": "basica",
                "nota": "Rota com 1 escala (solução de fallback)",
                "tempo_computacao": 0.0
            }
        }
    
    # Nenhuma opção encontrada
    return create_empty_route_response(origem, destino, "Nenhum voo disponível para a data e rota solicitadas")


def relaxar_restricoes(params: Dict) -> Dict:
    """
    Nível 2 - Relaxa restrições para aumentar chance de solução
    - Aumenta TMAX (tempo máximo de voo)
    - Reduz dias mínimos obrigatórios
    - Aumenta dias máximos permitidos
    """
    params_relaxados = params.copy()
    
    # Aumentar tempo máximo de voo em 50%
    params_relaxados['TMAX'] = params_relaxados.get('TMAX', 48.0) * 1.5
    
    # Relaxar dias mínimos (reduzir em 50%, mínimo 0)
    d_min_relaxado = {}
    for city, dias in params_relaxados.get('d_min', {}).items():
        d_min_relaxado[city] = max(0.0, dias * 0.5)
    params_relaxados['d_min'] = d_min_relaxado
    
    # Aumentar dias máximos em 30%
    d_max_relaxado = {}
    D_total = params_relaxados.get('D_total', 7.0)
    for city, dias in params_relaxados.get('d_max', {}).items():
        d_max_relaxado[city] = min(D_total, dias * 1.3)
    params_relaxados['d_max'] = d_max_relaxado
    
    return params_relaxados


def algoritmo_guloso(db: Dict, origem: str, destino: str, data_ida: str, locais_visitar: List[str]) -> Optional[Dict]:
    """
    Nível 3 - Algoritmo guloso: sempre escolhe próximo voo mais barato
    Tenta construir uma rota viável priorizando custo
    """
    caminho = [origem]
    trechos = []
    custo_total = 0.0
    
    visitados = {origem}
    current = origem
    pendentes = set(locais_visitar) - {origem, destino}
    
    # Data atual de busca
    data_busca = data_ida
    data_busca_dt = datetime.strptime(data_busca, "%Y-%m-%d")
    
    max_iterations = 20
    iterations = 0
    
    while current != destino and iterations < max_iterations:
        iterations += 1
        
        # Se ainda há cidades pendentes, tentar visitar uma delas
        if pendentes:
            # Buscar voos mais baratos para as cidades pendentes
            opcoes = []
            for proxima in pendentes:
                voos = [
                    a for a in db.get("arestas", [])
                    if a["origem"] == current and a["destino"] == proxima and a["data_voo"] >= data_busca
                ]
                if voos:
                    mais_barato = min(voos, key=lambda x: float(x["custo_passagem"]))
                    opcoes.append(mais_barato)
            
            if opcoes:
                voo_escolhido = min(opcoes, key=lambda x: float(x["custo_passagem"]))
            else:
                # Não há voos para cidades pendentes, tentar ir direto ao destino
                voo_escolhido = None
        else:
            # Ir direto ao destino
            voos = [
                a for a in db.get("arestas", [])
                if a["origem"] == current and a["destino"] == destino and a["data_voo"] >= data_busca
            ]
            voo_escolhido = min(voos, key=lambda x: float(x["custo_passagem"])) if voos else None
        
        if not voo_escolhido:
            # Não encontrou voo, tentar qualquer próxima cidade não visitada
            voos_possiveis = [
                a for a in db.get("arestas", [])
                if a["origem"] == current and a["destino"] not in visitados and a["data_voo"] >= data_busca
            ]
            
            if not voos_possiveis:
                break
            
            voo_escolhido = min(voos_possiveis, key=lambda x: float(x["custo_passagem"]))
        
        # Adicionar voo à rota
        fid = f'{voo_escolhido["voo_cod"]}_{voo_escolhido["data_voo"]}_{voo_escolhido["hora_saida"]}'
        trechos.append({
            "origem": current,
            "destino": voo_escolhido["destino"],
            "voo": {
                "id": fid,
                "cia": voo_escolhido.get("cia", voo_escolhido.get("companhia", "")),
                "codigo": voo_escolhido["voo_cod"],
                "data": voo_escolhido["data_voo"],
                "saida": voo_escolhido["hora_saida"],
                "duracao_min": float(voo_escolhido["tempo_voo"]),
                "preco": float(voo_escolhido["custo_passagem"])
            }
        })
        
        custo_total += float(voo_escolhido["custo_passagem"])
        current = voo_escolhido["destino"]
        caminho.append(current)
        visitados.add(current)
        pendentes.discard(current)
        
        # Atualizar data de busca (dia seguinte ao voo)
        data_voo_dt = datetime.strptime(voo_escolhido["data_voo"], "%Y-%m-%d")
        data_busca_dt = data_voo_dt + timedelta(days=1)
        data_busca = data_busca_dt.strftime("%Y-%m-%d")
    
    if current != destino:
        return None
    
    return {
        "rota": {
            "origem": origem,
            "destino": destino,
            "caminho": caminho,
            "trechos": trechos
        },
        "custos": {
            "total": custo_total,
            "voos": custo_total,
            "hospedagem": 0.0,
            "alimentacao": 0.0,
            "transporte": 0.0
        },
        "detalhes": {
            "hospedagem": [],
            "alimentacao": [],
            "transporte": []
        },
        "metadata": {
            "nivel_otimizacao": "viavel",
            "nota": "Solução aproximada usando algoritmo guloso (heurística)",
            "tempo_computacao": 0.0
        }
    }


def optimize_with_fallback(
    request_data: Dict,
    db: Dict,
    model_params: Dict,
    build_result_func
) -> Dict:
    """
    Sistema de fallback em 4 níveis
    SEMPRE retorna uma resposta válida (nunca None ou undefined)
    """
    tempo_inicio = time.time()
    origem = request_data["origem"]
    destino = request_data["destino"]
    
    try:
        # NÍVEL 1: Solução Ótima
        model = build_trip_milp_pulp(**model_params)
        
        # Adicionar restrições de locais a visitar
        variables = model.variablesDict()
        for local in request_data.get("locais_visitar", []):
            if local in model_params['V'] and local != origem and local != destino:
                if f"y_{local}" in variables:
                    model += variables[f"y_{local}"] == 1, f"Force_visit_{local}"
        
        status = model.solve(PULP_CBC_CMD(msg=False, timeLimit=30))
        
        if LpStatus[status] == "Optimal":
            resultado = build_result_func(model, db, origem, destino)
            resultado["metadata"] = {
                "nivel_otimizacao": "otima",
                "nota": "Solução ótima encontrada",
                "tempo_computacao": round(time.time() - tempo_inicio, 2)
            }
            return resultado
        
        # NÍVEL 2: Solução Relaxada
        params_relaxados = relaxar_restricoes(model_params)
        model_relaxado = build_trip_milp_pulp(**params_relaxados)
        
        # Adicionar restrições novamente
        variables = model_relaxado.variablesDict()
        for local in request_data.get("locais_visitar", []):
            if local in params_relaxados['V'] and local != origem and local != destino:
                if f"y_{local}" in variables:
                    model_relaxado += variables[f"y_{local}"] == 1, f"Force_visit_{local}"
        
        status = model_relaxado.solve(PULP_CBC_CMD(msg=False, timeLimit=30))
        
        if LpStatus[status] == "Optimal":
            resultado = build_result_func(model_relaxado, db, origem, destino)
            resultado["metadata"] = {
                "nivel_otimizacao": "boa",
                "nota": "Solução com restrições relaxadas",
                "tempo_computacao": round(time.time() - tempo_inicio, 2)
            }
            return resultado
        
        # NÍVEL 3: Algoritmo Guloso
        resultado_guloso = algoritmo_guloso(
            db, origem, destino,
            request_data["data_ida"],
            request_data.get("locais_visitar", [])
        )
        
        if resultado_guloso:
            resultado_guloso["metadata"]["tempo_computacao"] = round(time.time() - tempo_inicio, 2)
            return resultado_guloso
        
        # NÍVEL 4: Rota Básica (último recurso)
        resultado_basico = criar_rota_basica(db, origem, destino, request_data["data_ida"], request_data)
        resultado_basico["metadata"]["tempo_computacao"] = round(time.time() - tempo_inicio, 2)
        return resultado_basico
        
    except Exception as e:
        # Fallback final: retornar estrutura válida com erro
        tempo_computacao = round(time.time() - tempo_inicio, 2)
        return create_empty_route_response(
            origem, destino,
            f"Erro na otimização: {str(e)}"
        )
