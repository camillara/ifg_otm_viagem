# ✈️ Otimizador de Viagens - IFG

Este projeto foi desenvolvido como parte da disciplina de **Modelagem e Otimização** da Pós-Graduação em **Inteligência Artificial Aplicada** do **Instituto Federal de Goiás (IFG)**.

O sistema utiliza **Programação Linear Inteira Mista (MILP)** para planejar roteiros de viagem otimizados, minimizando custos totais (passagens aéreas, hospedagem, alimentação e transporte) enquanto respeita restrições de tempo, conexões e preferências do usuário.

---

## 📋 Funcionalidades

- **Otimização de Roteiros**: Encontra a melhor combinação de voos e estadias para minimizar o custo total.
- **Restrições Personalizáveis**:
  - Definição de origem e destino.
  - Escolha de cidades intermediárias obrigatórias.
  - Definição de dias mínimos/fixos por cidade.
  - Inclusão/Exclusão de custos (hospedagem, alimentação, transporte).
- **API RESTful**: Interface construída com **FastAPI** para integração fácil com front-ends.
- **Modelagem Matemática**: Uso da biblioteca **PuLP** para resolução do problema de otimização.

---

## 🛠️ Tecnologias Utilizadas

- **Linguagem**: Python 3.10+
- **Framework Web**: FastAPI + Uvicorn
- **Otimização**: PuLP (CBC Solver)
- **Gerenciamento de Dados**: JSON (Database local)
- **Validação de Dados**: Pydantic

---

## 🚀 Como Executar

### Pré-requisitos

Certifique-se de ter o Python instalado em sua máquina.

### 1. Clone o repositório

```bash
git clone https://github.com/seu-usuario/ifg-otm-viagem.git
cd ifg-otm-viagem
```

### 2. Crie um ambiente virtual (Recomendado)

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Linux/Mac
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Instale as dependências

```bash
pip install -r requirements.txt
```

### 4. Execute a API

```bash
python api.py
# Ou usando uvicorn diretamente:
# uvicorn api:app --reload
```

A API estará disponível em `http://localhost:8000`.

---

## 📖 Documentação da API

A documentação interativa (Swagger UI) pode ser acessada em:
👉 **http://localhost:8000/docs**

### Endpoint Principal: `/optimize`

**Método**: `POST`

**Exemplo de Payload (JSON):**

```json
{
  "ida_volta": false,
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
  "incluir_refeicao": true,
  "incluir_hospedagem": true,
  "incluir_transporte": false
}
```

**Resposta de Sucesso:**

Retorna o roteiro detalhado com voos escolhidos, custos por categoria e cronograma.

---

## 📂 Estrutura do Projeto

```
ifg-otm-viagem/
├── api.py                 # Aplicação FastAPI e endpoints
├── main.py                # Script principal para testes locais (CLI)
├── otm_model.py           # Construção do modelo matemático (MILP)
├── import_export_json.py  # Utilitários de leitura/escrita de dados
├── database.json          # Base de dados de voos e custos (Mock)
├── requirements.txt       # Dependências do projeto
└── README.md              # Documentação
```

---

## 🧠 Sobre o Modelo

O problema é modelado como um grafo onde:
- **Nós** representam cidades.
- **Arestas** representam voos disponíveis.
- **Variáveis de Decisão** determinam quais voos escolher e quantos dias ficar em cada cidade.
- **Função Objetivo**: Minimizar $\sum (Custo_{voos} + Custo_{hospedagem} + Custo_{alimentação} + Custo_{transporte})$.

---

## 📝 Autores

Desenvolvido por **Renato Milhomem** e equipe, para a disciplina de Modelagem e Otimização - IFG.
