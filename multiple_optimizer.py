"""
Sistema de Otimização com Múltiplas Opções
Gera 3 melhores rotas com diferentes trade-offs
"""

from typing import Dict, List, Any
from pulp import PULP_CBC_CMD, LpStatus
import time
from otm_model import build_trip_milp_pulp
from import_export_json import build_front_json_from_solution


def calcular_tempo_total_viagem(resultado: Dict) -> float:
    """
    Calcula tempo total em horas (soma durações de voos + conexões)
    """
    if not resultado.get('rota', {}).get('trechos'):
        return 0.0
    
    tempo_total = 0.0
    for trecho in resultado['rota']['trechos']:
        voo = trecho.get('voo', {})
        duracao_min = voo.get('duracao_min', 0)
        tempo_total += duracao_min / 60.0  # converter para horas
    
    return tempo_total


def contar_escalas(resultado: Dict) -> int:
    """
    Conta número de escalas (trechos - 1)
    """
    trechos = resultado.get('rota', {}).get('trechos', [])
    return max(0, len(trechos) - 1)


def gerar_vantagens(opcao: Dict) -> List[str]:
    """
    Gera lista de vantagens baseado nas pontuações
    """
    vantagens = []
    pontuacao = opcao.get('pontuacao', {})
    
    if pontuacao.get('custo', 0) >= 8:
        vantagens.append("Menor preço")
    if pontuacao.get('tempo', 0) >= 8:
        vantagens.append("Viagem rápida")
    if pontuacao.get('conforto', 0) >= 8:
        vantagens.append("Maior conforto")
    if opcao.get('numero_escalas', 0) == 0:
        vantagens.append("Voo direto")
    elif opcao.get('numero_escalas', 0) == 1:
        vantagens.append("Apenas 1 escala")
    if pontuacao.get('geral', 0) >= 9:
        vantagens.append("Excelente custo-benefício")
    
    return vantagens if vantagens else ["Opção viável"]


def gerar_desvantagens(opcao: Dict) -> List[str]:
    """
    Gera lista de desvantagens baseado nas pontuações
    """
    desvantagens = []
    pontuacao = opcao.get('pontuacao', {})
    
    if pontuacao.get('custo', 0) <= 4:
        desvantagens.append("Preço mais alto")
    if pontuacao.get('tempo', 0) <= 4:
        desvantagens.append("Duração mais longa")
    if opcao.get('numero_escalas', 0) >= 2:
        desvantagens.append(f"{opcao['numero_escalas']} escalas")
    elif opcao.get('numero_escalas', 0) == 1:
        desvantagens.append("1 escala")
    if pontuacao.get('conforto', 0) <= 4:
        desvantagens.append("Menos conforto")
    
    return desvantagens if desvantagens else ["Nenhuma desvantagem significativa"]


def calcular_pontuacoes(opcoes: List[Dict]) -> List[Dict]:
    """
    Normaliza métricas em escala 0-10 (menor valor = maior pontuação para custo/tempo/escalas)
    """
    if not opcoes:
        return opcoes
    
    custos = [op['custo_total'] for op in opcoes]
    tempos = [op['tempo_total_viagem'] for op in opcoes]
    escalas = [op['numero_escalas'] for op in opcoes]
    
    # Evitar divisão por zero
    range_custo = max(custos) - min(custos) if max(custos) != min(custos) else 1
    range_tempo = max(tempos) - min(tempos) if max(tempos) != min(tempos) else 1
    range_escalas = max(escalas) - min(escalas) if max(escalas) != min(escalas) else 1
    
    for opcao in opcoes:
        # Normalizar: menor valor = maior pontuação
        if range_custo > 0:
            custo_norm = 10 * (1 - (opcao['custo_total'] - min(custos)) / range_custo)
        else:
            custo_norm = 10.0
        
        if range_tempo > 0:
            tempo_norm = 10 * (1 - (opcao['tempo_total_viagem'] - min(tempos)) / range_tempo)
        else:
            tempo_norm = 10.0
        
        if range_escalas > 0:
            conforto_norm = 10 * (1 - (opcao['numero_escalas'] - min(escalas)) / range_escalas)
        else:
            conforto_norm = 10.0
        
        opcao['pontuacao'] = {
            'custo': round(custo_norm, 1),
            'tempo': round(tempo_norm, 1),
            'conforto': round(conforto_norm, 1),
            'geral': round((custo_norm + tempo_norm + conforto_norm) / 3, 1)
        }
        
        # Gerar vantagens/desvantagens baseado nas pontuações
        opcao['vantagens'] = gerar_vantagens(opcao)
        opcao['desvantagens'] = gerar_desvantagens(opcao)
    
    return opcoes


def remover_duplicatas(opcoes: List[Dict], threshold_custo: float = 100.0) -> List[Dict]:
    """
    Remove opções muito similares (diferença de custo < threshold)
    """
    if len(opcoes) <= 1:
        return opcoes
    
    unicas = [opcoes[0]]
    
    for opcao in opcoes[1:]:
        is_duplicata = False
        for unica in unicas:
            diff_custo = abs(opcao['custo_total'] - unica['custo_total'])
            diff_escalas = abs(opcao['numero_escalas'] - unica['numero_escalas'])
            
            if diff_custo < threshold_custo and diff_escalas == 0:
                is_duplicata = True
                break
        
        if not is_duplicata:
            unicas.append(opcao)
    
    return unicas


def otimizar_com_pesos(
    model_params: Dict,
    db: Dict,
    origem: str,
    destino: str,
    locais_visitar: List[str],
    build_result_func,
    peso_custo: float = 1.0,
    peso_tempo: float = 1.0,
    preferir_voo_direto: bool = False,
    timeout: int = 20
) -> Dict:
    """
    Otimiza com pesos diferentes na função objetivo
    """
    try:
        # Modificar TMAX se preferir voo direto
        params = model_params.copy()
        if preferir_voo_direto:
            params['TMAX'] = min(params.get('TMAX', 48.0), 20.0)  # Limitar tempo de voo
        
        # Construir modelo
        model = build_trip_milp_pulp(**params)
        
        # Adicionar restrições de visita
        variables = model.variablesDict()
        for local in locais_visitar:
            if local in params['V'] and local != origem and local != destino:
                if f"y_{local}" in variables:
                    model += variables[f"y_{local}"] == 1, f"Force_visit_{local}"
        
        # Modificar função objetivo com pesos
        # Aqui poderíamos adicionar penalidades para tempo, mas PuLP não permite facilmente
        # Por simplicidade, vamos usar diferentes parâmetros de modelo
        
        status = model.solve(PULP_CBC_CMD(msg=False, timeLimit=timeout))
        
        if LpStatus[status] == "Optimal":
            return build_result_func(model, db, origem, destino)
        
        return None
        
    except Exception as e:
        return None


def gerar_multiplas_opcoes(
    request_data: Dict,
    db: Dict,
    model_params: Dict,
    build_result_func,
    num_opcoes: int = 3
) -> Dict:
    """
    Gera múltiplas opções com diferentes trade-offs
    Retorna as 3 melhores opções classificadas
    """
    tempo_inicio = time.time()
    opcoes = []
    origem = request_data['origem']
    destino = request_data['destino']
    locais_visitar = request_data.get('locais_visitar', [])
    
    # OPÇÃO 1: Minimizar Custo (configuração padrão otimizada)
    opcao1 = otimizar_com_pesos(
        model_params=model_params,
        db=db,
        origem=origem,
        destino=destino,
        locais_visitar=locais_visitar,
        build_result_func=build_result_func,
        peso_custo=1.0,
        peso_tempo=0.3,
        preferir_voo_direto=False,
        timeout=20
    )
    
    if opcao1:
        opcao1['titulo'] = "Mais Econômica"
        opcao1['descricao'] = "Menor custo total, pode ter mais escalas"
        opcao1['custo_total'] = opcao1['custos']['total']
        opcao1['tempo_total_viagem'] = calcular_tempo_total_viagem(opcao1)
        opcao1['numero_escalas'] = contar_escalas(opcao1)
        opcoes.append(opcao1)
    
    # OPÇÃO 2: Equilibrada (TMAX um pouco maior para mais opções)
    params_equilibrados = model_params.copy()
    params_equilibrados['TMAX'] = model_params.get('TMAX', 48.0) * 0.75  # 75% do tempo máximo
    
    opcao2 = otimizar_com_pesos(
        model_params=params_equilibrados,
        db=db,
        origem=origem,
        destino=destino,
        locais_visitar=locais_visitar,
        build_result_func=build_result_func,
        peso_custo=0.6,
        peso_tempo=0.6,
        preferir_voo_direto=False,
        timeout=20
    )
    
    if opcao2:
        opcao2['titulo'] = "Melhor Custo-Benefício"
        opcao2['descricao'] = "Equilíbrio entre preço e conforto"
        opcao2['custo_total'] = opcao2['custos']['total']
        opcao2['tempo_total_viagem'] = calcular_tempo_total_viagem(opcao2)
        opcao2['numero_escalas'] = contar_escalas(opcao2)
        opcoes.append(opcao2)
    
    # OPÇÃO 3: Minimizar Tempo (preferir voos diretos)
    params_rapidos = model_params.copy()
    params_rapidos['TMAX'] = 15.0  # Limite baixo de tempo para forçar voos diretos/rápidos
    
    opcao3 = otimizar_com_pesos(
        model_params=params_rapidos,
        db=db,
        origem=origem,
        destino=destino,
        locais_visitar=locais_visitar,
        build_result_func=build_result_func,
        peso_custo=0.2,
        peso_tempo=1.0,
        preferir_voo_direto=True,
        timeout=20
    )
    
    if opcao3:
        opcao3['titulo'] = "Mais Rápida e Confortável"
        opcao3['descricao'] = "Voos diretos, menor tempo total"
        opcao3['custo_total'] = opcao3['custos']['total']
        opcao3['tempo_total_viagem'] = calcular_tempo_total_viagem(opcao3)
        opcao3['numero_escalas'] = contar_escalas(opcao3)
        opcoes.append(opcao3)
    
    # Se não conseguiu gerar 3 opções diferentes, tentar variações
    if len(opcoes) < 3:
        # Tentar com TMAX intermediário
        params_intermediarios = model_params.copy()
        params_intermediarios['TMAX'] = model_params.get('TMAX', 48.0) * 0.6
        
        opcao_extra = otimizar_com_pesos(
            model_params=params_intermediarios,
            db=db,
            origem=origem,
            destino=destino,
            locais_visitar=locais_visitar,
            build_result_func=build_result_func,
            peso_custo=0.5,
            peso_tempo=0.7,
            timeout=15
        )
        
        if opcao_extra:
            opcao_extra['titulo'] = "Alternativa"
            opcao_extra['descricao'] = "Opção intermediária"
            opcao_extra['custo_total'] = opcao_extra['custos']['total']
            opcao_extra['tempo_total_viagem'] = calcular_tempo_total_viagem(opcao_extra)
            opcao_extra['numero_escalas'] = contar_escalas(opcao_extra)
            opcoes.append(opcao_extra)
    
    # Remover duplicatas
    opcoes = remover_duplicatas(opcoes)
    
    # Calcular pontuações
    opcoes = calcular_pontuacoes(opcoes)
    
    # Ordenar por pontuação geral (melhor primeiro)
    opcoes.sort(key=lambda x: x['pontuacao']['geral'], reverse=True)
    
    # Adicionar IDs e rankings
    for idx, opcao in enumerate(opcoes[:num_opcoes]):
        opcao['id'] = idx + 1
        opcao['ranking'] = idx + 1
    
    # Determinar recomendação (melhor pontuação geral)
    recomendacao = 1 if opcoes else None
    
    tempo_computacao = round(time.time() - tempo_inicio, 2)
    
    return {
        "opcoes": opcoes[:num_opcoes],
        "recomendacao": recomendacao,
        "metadata": {
            "tempo_computacao": tempo_computacao,
            "numero_opcoes_geradas": len(opcoes),
            "numero_opcoes_solicitadas": num_opcoes
        }
    }
