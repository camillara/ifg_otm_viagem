import requests
import json

# URL da API (certifique-se de que o api.py esteja rodando)
url = "http://localhost:8000/optimize"

# Payload conforme solicitado
payload = {
  "ida_volta": False,
  "origem": "GYN",
  "destino": "ATL",
  "locais_visitar": ["GRU", "JFK"],
  "data_ida": "2026-03-07",
  "numero_adultos": 2,
  "numero_criancas": 1,
  "dias_por_cidade": {
    "GRU": 3,
    "JFK": 4,
    "ATL": 2
  },
  "incluir_refeicao": True,
  "incluir_hospedagem": True,
  "incluir_transporte": False
}

try:
    print(f"Enviando requisição para {url}...")
    response = requests.post(url, json=payload)
    
    if response.status_code == 200:
        print("Sucesso! Resposta da API:")
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    else:
        print(f"Erro {response.status_code}:")
        print(response.text)

except requests.exceptions.ConnectionError:
    print("Erro de conexão: Verifique se a API está rodando (python api.py)")
