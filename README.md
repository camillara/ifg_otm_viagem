# ✈️ Otimizador de Viagens - IFG v2.0

> **⚠️ VERSÃO 2.0 - MELHORIAS CRÍTICAS IMPLEMENTADAS**  
> Sistema agora **GARANTE sempre retornar resposta válida** + **Múltiplas opções de rotas**

Este projeto foi desenvolvido como parte da disciplina de **Modelagem e Otimização** da Pós-Graduação em **Inteligência Artificial Aplicada** do **Instituto Federal de Goiás (IFG)**.

O sistema utiliza **Programação Linear Inteira Mista (MILP)** para planejar roteiros de viagem otimizados, minimizando custos totais (passagens aéreas, hospedagem, alimentação e transporte) enquanto respeita restrições de tempo, conexões e preferências do usuário.

---

## 🆕 Novidades da Versão 2.0

### ✅ Sistema de Fallback em 4 Níveis
**PROBLEMA RESOLVIDO**: API nunca mais retorna `undefined` ou `null`

- **Nível 1 - Ótima** ⭐⭐⭐⭐⭐: Solução matematicamente ótima
- **Nível 2 - Relaxada** ⭐⭐⭐⭐: Restrições flexibilizadas
- **Nível 3 - Gulosa** ⭐⭐⭐: Algoritmo heurístico
- **Nível 4 - Básica** ⭐⭐: Rota simples (direto ou 1 escala)

### 🎯 Múltiplas Opções de Rotas
Novo endpoint `/optimize-multiple` retorna **3 opções** ranqueadas:

1. 💰 **Mais Econômica**: Menor custo (pode ter mais escalas)
2. ⚖️ **Melhor Custo-Benefício**: Equilíbrio ideal (recomendada)
3. ⚡ **Mais Rápida**: Menos tempo e escalas (pode custar mais)

Cada opção inclui:
- Pontuações normalizadas (0-10) para custo, tempo e conforto
- Vantagens e desvantagens auto-geradas
- Comparação lado-a-lado para decisão informada

📚 **Documentação completa**: Ver [MELHORIAS_IMPLEMENTADAS.md](MELHORIAS_IMPLEMENTADAS.md)

---

## 📋 Funcionalidades

- ✅ **Otimização de Roteiros**: Encontra a melhor combinação de voos e estadias
- ✅ **Sistema de Fallback**: Sempre retorna resposta válida (4 níveis)
- ✅ **Múltiplas Opções**: Compare 3 rotas diferentes com pontuações
- ✅ **Restrições Personalizáveis**:
  - Definição de origem e destino
  - Escolha de cidades intermediárias obrigatórias
  - Definição de dias mínimos/fixos por cidade
  - Inclusão/Exclusão de custos (hospedagem, alimentação, transporte)
- ✅ **API RESTful**: Interface construída com **FastAPI**
- ✅ **Modelagem Matemática**: Uso da biblioteca **PuLP** (CBC Solver)

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
# macOS/Linux
python3 -m venv .venv
source .venv/bin/activate

# Windows
python -m venv .venv
.venv\Scripts\activate
```

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
uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

A API estará disponível em `http://localhost:8000`.

---

## 🧪 Como Testar as Melhorias

### Teste Automatizado (Recomendado)

```bash
# Terminal 1: Iniciar API
uvicorn api:app --reload

# Terminal 2: Executar testes
python3 test_melhorias.py
```

Ver [GUIA_RAPIDO.md](GUIA_RAPIDO.md) para mais opções de teste.

---

## 📖 Documentação da API

A documentação interativa (Swagger UI) pode ser acessada em:
👉 **http://localhost:8000/docs**

### Endpoints Disponíveis

#### 1. Health Check
```bash
GET /
```

#### 2. Datas Disponíveis
```bash
GET /available-dates
```

#### 3. Otimização com Fallback (ATUALIZADO v2.0)
```bash
POST /optimize
```

**⭐ NOVO: Sistema de Fallback**
- Sempre retorna resposta válida (nunca `null`)
- Campo `metadata.nivel_otimizacao` indica qualidade da solução
- 4 níveis: "otima", "boa", "viavel", "basica"

#### 4. Múltiplas Opções (NOVO v2.0)
```bash
POST /optimize-multiple
```

**⭐ NOVO: Retorna 3 opções ranqueadas**
- Opção 1: Mais Econômica
- Opção 2: Melhor Custo-Benefício (recomendada)
- Opção 3: Mais Rápida e Confortável

**Exemplo de Payload (JSON):**

```json
{
  "ida_volta": false,
  "origem": "GYN",
  "destino": "GRU",
  "locais_visitar": [],
  "data_ida": "2026-03-10",
  "numero_adultos": 1,
  "numero_criancas": 0,
  "dias_por_cidade": {"GRU": 3},
  "incluir_refeicao": true,
  "incluir_hospedagem": true,
  "incluir_transporte": true,
  "numero_opcoes": 3
}
```

**Resposta de Sucesso (v2.0):**

```json
{
  "rota": {...},
  "custos": {...},
  "detalhes": {...},
  "metadata": {
    "nivel_otimizacao": "otima",
    "nota": "Solução ótima encontrada",
    "tempo_computacao": 12.5
  }
}
```

---

## 📂 Estrutura do Projeto

```
ifg-otm-viagem/
├── api.py                     # FastAPI endpoints (ATUALIZADO v2.0)
├── fallback_optimizer.py      # Sistema de fallback 4 níveis (NOVO)
├── multiple_optimizer.py      # Geração de múltiplas opções (NOVO)
├── otm_model.py               # Modelo matemático MILP
├── import_export_json.py      # Utilitários de dados
├── main.py                    # Script CLI para testes
├── test_melhorias.py          # Script de testes (NOVO)
├── database.json              # Base de dados (mock)
├── requirements.txt           # Dependências
├── README.md                  # Este arquivo
├── MELHORIAS_IMPLEMENTADAS.md # Documentação detalhada (NOVO)
└── GUIA_RAPIDO.md             # Guia de uso rápido (NOVO)
```

---

## 🧠 Sobre o Modelo

O problema é modelado como um grafo onde:
- **Nós** representam cidades.
- **Arestas** representam voos disponíveis.
- **Variáveis de Decisão** determinam quais voos escolher e quantos dias ficar em cada cidade.
- **Função Objetivo**: Minimizar $\sum (Custo_{voos} + Custo_{hospedagem} + Custo_{alimentação} + Custo_{transporte})$.

### Algoritmos Implementados (v2.0)

1. **MILP Solver (PuLP/CBC)**: Solução ótima matematicamente provada
2. **Relaxação de Restrições**: Aumenta espaço de busca para soluções viáveis
3. **Algoritmo Guloso**: Heurística construtiva priorizando menor custo
4. **Busca Direta**: Fallback final para rotas simples

---

## 📝 Autores

Desenvolvido por **Renato Milhomem** e equipe, para a disciplina de Modelagem e Otimização - IFG.

**Versão 2.0** implementada em Janeiro/2026 com melhorias críticas de robustez e múltiplas opções.
