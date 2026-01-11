# 🕷️ Módulo de Coleta de Dados e ETL (Crawler)

Este módulo é responsável pela **Extração, Transformação e Carga (ETL)** de dados reais de turismo, alimentando o modelo matemático com custos de mercado.

---

## 🚀 Visão Geral

Este módulo executa uma coleta híbrida em tempo real para construir um **Grafo Direcionado** onde:
* **Nós (Cidades):** Representam os custos de estadia (Hotel, Alimentação, Transporte Local).
* **Arestas (Rotas):** Representam os voos disponíveis (Preço, Horário, Duração).

### 📊 Fontes de Dados Utilizadas

| Tipo de Dado | Fonte | Método | Tecnologia |
| :--- | :--- | :--- | :--- |
| **Malha Aérea** | **Amadeus API** | `GET /flight-offers` | SDK Oficial Amadeus |
| **Transfer** | **Amadeus API** | `POST /transfer-offers` | SDK Oficial Amadeus |
| **Hospedagem** | **Booking.com** | Web Scraping | `BeautifulSoup4` + `Requests` |
| **Alimentação** | **Numbeo** | Web Scraping | `BeautifulSoup4` + `Requests` |

---

## 🛠️ Instalação e Execução

### Pré-requisitos
* Python 3.8 ou superior.
* Credenciais da API Amadeus (Client ID e Secret).

### 1. Instalar Dependências
```bash
pip install requests beautifulsoup4 amadeus-python python-dotenv unidecode
```

### 2. Configurar Variáveis de Ambiente
Crie um arquivo `.env` na raiz do projeto contendo suas chaves:
```env
AMADEUS_CLIENT_ID="chave_aqui"
AMADEUS_CLIENT_SECRET="secret_aqui"
```

### 3. Executar Manualmente
```bash
python crawler.py
```
*Nota: O processo pode levar alguns minutos devido aos delays de segurança propositais.*

---

## ⏰ Automatização e Agendamento (Cron Job)

Para manter o conjunto de dados atualizado sem intervenção manual, recomenda-se o agendamento via **Cron** (Linux/Mac).

### Estratégia de Agendamento
Optou-se por uma frequência **Diária (uma vez ao dia)**, preferencialmente de madrugada.
* **Motivo 1 (Cotas):** Evitar o estouro do limite mensal de requisições da API Amadeus (Plano Free).
* **Motivo 2 (Segurança):** Minimizar o risco de bloqueio de IP pelo Booking/Numbeo por excesso de tráfego frequente.

### Como Configurar

1. Abra o editor do Cron no terminal:
```bash
crontab -e
```

2. Adicione a seguinte linha para rodar todo dia às **03:00 AM**:
```bash
# Formato: min hora dia mes dia_semana comando
0 3 * * * /usr/bin/python3 /crawler.py >> /coleta.log 2>&1
```

---

## 📂 Output: O Data Lake (`database.json`)

O script gera o arquivo `database.json`, que serve de input para o módulo de otimização matemática.

### Exemplo de Nó (Cidade)
```json
"GYN": {
    "nome": "Goiania",
    "custo_diaria_hotel": 149.00,       // Menor valor encontrado (Scraping)
    "custo_refeicao_diaria": 60.00,     // 2x Refeição Econômica (Scraping)
    "transporte": {
        "transfer_ida_volta": 209.32    // Custo fixo total (API)
    }
}
```

### Exemplo de Aresta (Voo)
```json
{
    "origem": "GRU",
    "destino": "ATL",
    "data_voo": "2026-02-28",
    "hora_saida": "20:55",              // Hora exata da partida
    "custo_passagem": 2522.49,          // Preço real por pessoa
    "tempo_voo": 1568,                  // Duração em minutos
    "cia": "AC",
    "voo_cod": "AC97"
}
```
