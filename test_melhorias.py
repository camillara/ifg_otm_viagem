"""
Script de Teste para as Melhorias do Sistema de Otimização
Testa os endpoints /optimize e /optimize-multiple
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"

def print_separator(title=""):
    print("\n" + "="*80)
    if title:
        print(f"  {title}")
        print("="*80)

def test_health_check():
    """Teste 1: Health Check"""
    print_separator("TESTE 1: Health Check")
    
    try:
        response = requests.get(f"{BASE_URL}/")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        print("✅ PASSOU")
        return True
    except Exception as e:
        print(f"❌ FALHOU: {e}")
        return False

def test_available_dates():
    """Teste 2: Verificar datas disponíveis"""
    print_separator("TESTE 2: Datas Disponíveis")
    
    try:
        response = requests.get(f"{BASE_URL}/available-dates")
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Data Mínima: {data.get('data_minima')}")
        print(f"Data Máxima: {data.get('data_maxima')}")
        assert response.status_code == 200
        assert "data_minima" in data
        assert "data_maxima" in data
        print("✅ PASSOU")
        return data
    except Exception as e:
        print(f"❌ FALHOU: {e}")
        return None

def test_optimize_endpoint(data_ida="2026-03-10"):
    """Teste 3: Endpoint /optimize com fallback"""
    print_separator(f"TESTE 3: Endpoint /optimize (data: {data_ida})")
    
    payload = {
        "ida_volta": False,
        "origem": "GYN",
        "destino": "GRU",
        "locais_visitar": [],
        "data_ida": data_ida,
        "numero_adultos": 1,
        "numero_criancas": 0,
        "dias_por_cidade": {"GRU": 3},
        "incluir_refeicao": True,
        "incluir_hospedagem": True,
        "incluir_transporte": True
    }
    
    try:
        print("Enviando requisição...")
        response = requests.post(
            f"{BASE_URL}/optimize",
            json=payload,
            timeout=120  # 2 minutos
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            # Validações críticas
            assert "rota" in data, "Campo 'rota' ausente"
            assert "custos" in data, "Campo 'custos' ausente"
            assert "detalhes" in data, "Campo 'detalhes' ausente"
            assert "metadata" in data, "Campo 'metadata' ausente"
            
            # Validar que NUNCA retorna None
            assert data["rota"] is not None, "rota é None!"
            
            # Verificar metadata
            metadata = data["metadata"]
            nivel = metadata.get("nivel_otimizacao")
            nota = metadata.get("nota")
            tempo = metadata.get("tempo_computacao")
            
            print(f"\n📊 Resultado:")
            print(f"  Nível de Otimização: {nivel}")
            print(f"  Nota: {nota}")
            print(f"  Tempo: {tempo}s")
            print(f"  Custo Total: R$ {data['custos']['total']:.2f}")
            print(f"  Origem: {data['rota']['origem']}")
            print(f"  Destino: {data['rota']['destino']}")
            print(f"  Caminho: {' → '.join(data['rota']['caminho'])}")
            print(f"  Número de trechos: {len(data['rota']['trechos'])}")
            
            # Validar níveis aceitos
            assert nivel in ["otima", "boa", "viavel", "basica", "erro"], f"Nível inválido: {nivel}"
            
            print("\n✅ PASSOU - Resposta válida recebida")
            return True
        else:
            print(f"Erro HTTP: {response.status_code}")
            print(f"Response: {response.text}")
            print("❌ FALHOU")
            return False
            
    except Exception as e:
        print(f"❌ FALHOU: {e}")
        return False

def test_optimize_multiple_endpoint(data_ida="2026-03-10"):
    """Teste 4: Endpoint /optimize-multiple"""
    print_separator(f"TESTE 4: Endpoint /optimize-multiple (data: {data_ida})")
    
    payload = {
        "ida_volta": False,
        "origem": "GYN",
        "destino": "GRU",
        "locais_visitar": [],
        "data_ida": data_ida,
        "numero_adultos": 1,
        "numero_criancas": 0,
        "dias_por_cidade": {"GRU": 3},
        "incluir_refeicao": True,
        "incluir_hospedagem": True,
        "incluir_transporte": True,
        "numero_opcoes": 3
    }
    
    try:
        print("Enviando requisição (pode levar ~1-2 minutos)...")
        response = requests.post(
            f"{BASE_URL}/optimize-multiple",
            json=payload,
            timeout=180  # 3 minutos
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            # Validações
            assert "opcoes" in data, "Campo 'opcoes' ausente"
            assert "recomendacao" in data, "Campo 'recomendacao' ausente"
            assert "metadata" in data, "Campo 'metadata' ausente"
            
            opcoes = data["opcoes"]
            print(f"\n📊 {len(opcoes)} opções geradas:")
            
            for i, opcao in enumerate(opcoes, 1):
                print(f"\n  --- Opção {i}: {opcao['titulo']} ---")
                print(f"  Descrição: {opcao['descricao']}")
                print(f"  Custo Total: R$ {opcao['custo_total']:.2f}")
                print(f"  Tempo Viagem: {opcao['tempo_total_viagem']:.1f}h")
                print(f"  Escalas: {opcao['numero_escalas']}")
                
                pontuacao = opcao['pontuacao']
                print(f"  Pontuações:")
                print(f"    - Custo: {pontuacao['custo']}/10")
                print(f"    - Tempo: {pontuacao['tempo']}/10")
                print(f"    - Conforto: {pontuacao['conforto']}/10")
                print(f"    - GERAL: {pontuacao['geral']}/10")
                
                print(f"  Vantagens: {', '.join(opcao['vantagens'])}")
                print(f"  Desvantagens: {', '.join(opcao['desvantagens'])}")
                
                # Validações de cada opção
                assert "id" in opcao
                assert "ranking" in opcao
                assert "titulo" in opcao
                assert "pontuacao" in opcao
                assert all(0 <= pontuacao[k] <= 10 for k in ['custo', 'tempo', 'conforto', 'geral'])
            
            print(f"\n🏆 Recomendação: Opção {data['recomendacao']}")
            print(f"⏱️ Tempo de Computação: {data['metadata']['tempo_computacao']:.2f}s")
            
            print("\n✅ PASSOU - Múltiplas opções geradas com sucesso")
            return True
        else:
            print(f"Erro HTTP: {response.status_code}")
            print(f"Response: {response.text}")
            print("❌ FALHOU")
            return False
            
    except Exception as e:
        print(f"❌ FALHOU: {e}")
        return False

def test_invalid_route():
    """Teste 5: Rota inválida (deve retornar erro controlado)"""
    print_separator("TESTE 5: Rota Inválida (destino não existe)")
    
    payload = {
        "ida_volta": False,
        "origem": "GYN",
        "destino": "CIDADEINEXISTENTE",
        "locais_visitar": [],
        "data_ida": "2026-03-10",
        "numero_adultos": 1,
        "numero_criancas": 0,
        "dias_por_cidade": {},
        "incluir_refeicao": False,
        "incluir_hospedagem": False,
        "incluir_transporte": False
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/optimize",
            json=payload,
            timeout=60
        )
        
        print(f"Status: {response.status_code}")
        
        # Esperamos erro 400 (Bad Request)
        if response.status_code == 400:
            print(f"Mensagem: {response.json()}")
            print("✅ PASSOU - Erro controlado retornado")
            return True
        else:
            print(f"Status inesperado: {response.status_code}")
            print("❌ FALHOU")
            return False
            
    except Exception as e:
        print(f"❌ FALHOU: {e}")
        return False

def run_all_tests():
    """Executa todos os testes"""
    print("\n" + "🧪 INICIANDO TESTES DAS MELHORIAS " + "🧪".center(50))
    print("Data/Hora:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    resultados = []
    
    # Teste 1: Health Check
    resultados.append(("Health Check", test_health_check()))
    
    # Teste 2: Datas disponíveis
    dates_data = test_available_dates()
    resultados.append(("Datas Disponíveis", dates_data is not None))
    
    # Usar data válida se disponível
    data_teste = "2026-03-10"
    if dates_data:
        data_teste = dates_data.get("data_minima", data_teste)
    
    # Teste 3: Endpoint /optimize
    resultados.append(("Endpoint /optimize", test_optimize_endpoint(data_teste)))
    
    # Teste 4: Endpoint /optimize-multiple
    resultados.append(("Endpoint /optimize-multiple", test_optimize_multiple_endpoint(data_teste)))
    
    # Teste 5: Rota inválida
    resultados.append(("Rota Inválida", test_invalid_route()))
    
    # Resumo
    print_separator("RESUMO DOS TESTES")
    total = len(resultados)
    passou = sum(1 for _, r in resultados if r)
    
    for nome, resultado in resultados:
        status = "✅ PASSOU" if resultado else "❌ FALHOU"
        print(f"{nome:.<50} {status}")
    
    print(f"\n📊 Total: {passou}/{total} testes passaram ({passou/total*100:.1f}%)")
    
    if passou == total:
        print("\n🎉 TODOS OS TESTES PASSARAM! Sistema pronto para produção.")
    else:
        print(f"\n⚠️ {total - passou} teste(s) falharam. Verifique os logs acima.")

if __name__ == "__main__":
    print("\n⚠️  IMPORTANTE: Certifique-se de que a API está rodando em http://localhost:8000")
    print("Execute: uvicorn api:app --reload")
    input("\nPressione ENTER quando a API estiver rodando...")
    
    run_all_tests()
