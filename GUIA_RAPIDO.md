# 🚀 Guia Rápido - Sistema de Otimização v2.0

## Como Iniciar a API

```bash
cd /Users/camillarodrigues/Documents/Projetos/IFG/modelo_travel/ifg_otm_viagem
uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

A API estará disponível em: `http://localhost:8000`

---

## 📚 Endpoints Disponíveis

### 1. Health Check
```bash
GET http://localhost:8000/
```

### 2. Datas Disponíveis
```bash
GET http://localhost:8000/available-dates
```

### 3. Otimização com Fallback (NOVO)
```bash
POST http://localhost:8000/optimize
```

**Resposta sempre válida** com 4 níveis de fallback:
- ⭐⭐⭐⭐⭐ Ótima
- ⭐⭐⭐⭐ Relaxada
- ⭐⭐⭐ Gulosa
- ⭐⭐ Básica

### 4. Múltiplas Opções (NOVO)
```bash
POST http://localhost:8000/optimize-multiple
```

Retorna **3 opções** com pontuações:
1. 💰 Mais Econômica
2. ⚖️ Melhor Custo-Benefício (recomendada)
3. ⚡ Mais Rápida e Confortável

---

## 🧪 Como Testar

### Opção 1: Script Automatizado (Recomendado)

```bash
# 1. Iniciar a API em um terminal
uvicorn api:app --reload

# 2. Em outro terminal, executar os testes
python3 test_melhorias.py
```

### Opção 2: cURL Manual

#### Teste Simples (/optimize)
```bash
curl -X POST http://localhost:8000/optimize \
  -H "Content-Type: application/json" \
  -d '{
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
    "incluir_transporte": true
  }' | jq
```

#### Teste Múltiplas Opções
```bash
curl -X POST http://localhost:8000/optimize-multiple \
  -H "Content-Type: application/json" \
  -d '{
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
  }' | jq
```

### Opção 3: Postman/Insomnia

1. Importar coleção (criar arquivo `postman_collection.json` se necessário)
2. Testar endpoints manualmente

---

## 📊 O Que Verificar na Resposta

### Endpoint `/optimize`

✅ **Campos obrigatórios**:
```json
{
  "rota": {
    "origem": "string",
    "destino": "string",
    "caminho": ["array"],
    "trechos": ["array"]
  },
  "custos": {
    "total": "number",
    "voos": "number",
    "hospedagem": "number",
    "alimentacao": "number",
    "transporte": "number"
  },
  "detalhes": {
    "hospedagem": [],
    "alimentacao": [],
    "transporte": []
  },
  "metadata": {
    "nivel_otimizacao": "otima|boa|viavel|basica|erro",
    "nota": "string",
    "tempo_computacao": "number"
  }
}
```

✅ **Garantias**:
- NUNCA retorna `null` ou `undefined`
- Sempre retorna estrutura válida
- Campo `metadata.nivel_otimizacao` indica qualidade da solução

### Endpoint `/optimize-multiple`

✅ **Campos obrigatórios**:
```json
{
  "opcoes": [
    {
      "id": 1,
      "ranking": 1,
      "titulo": "string",
      "descricao": "string",
      "rota": {...},
      "custos": {...},
      "detalhes": {...},
      "custo_total": "number",
      "tempo_total_viagem": "number",
      "numero_escalas": "number",
      "pontuacao": {
        "custo": 0-10,
        "tempo": 0-10,
        "conforto": 0-10,
        "geral": 0-10
      },
      "vantagens": ["array"],
      "desvantagens": ["array"]
    }
  ],
  "recomendacao": 1,
  "metadata": {...}
}
```

✅ **Garantias**:
- Array `opcoes` com até 3 elementos
- Pontuações normalizadas (0-10)
- `recomendacao` aponta para melhor opção
- Vantagens/desvantagens geradas automaticamente

---

## 🔍 Interpretando os Níveis de Otimização

| Nível | Significado | O que fazer |
|-------|-------------|-------------|
| `"otima"` ⭐⭐⭐⭐⭐ | Solução matematicamente ótima | ✅ Usar normalmente |
| `"boa"` ⭐⭐⭐⭐ | Solução viável com restrições relaxadas | ✅ Boa opção, avisar usuário |
| `"viavel"` ⭐⭐⭐ | Solução heurística aproximada | ⚠️ Funcional mas não ótima |
| `"basica"` ⭐⭐ | Rota simples (direto ou 1 escala) | ⚠️ Limitações nas opções |
| `"erro"` ⚠️ | Nenhum voo disponível | ❌ Sugerir outras datas/rotas |

---

## 🐛 Troubleshooting

### Erro: "Import pulp could not be resolved"
```bash
pip install -r requirements.txt
```

### Erro: "Database file not found"
Verificar se `database.json` existe no diretório

### API não inicia
```bash
# Verificar porta em uso
lsof -i :8000

# Matar processo se necessário
kill -9 <PID>

# Reiniciar API
uvicorn api:app --reload
```

### Teste demora muito
- Normal: `/optimize` = 30-60s
- Normal: `/optimize-multiple` = 1-3min (3 otimizações)
- Se > 5min: verificar complexidade da rota

---

## 📈 Melhorias Futuras

1. **Cache Redis**: Reduzir tempo de resposta
2. **Processamento Paralelo**: Múltiplas opções simultâneas
3. **Async/Await**: Melhor concorrência
4. **Machine Learning**: Prever preferências do usuário
5. **WebSockets**: Progresso em tempo real

---

## 📞 Suporte

- 📧 Email: [seu-email@example.com]
- 📚 Docs: Ver `MELHORIAS_IMPLEMENTADAS.md`
- 🐛 Issues: GitHub Issues

---

**Versão**: 2.0.0  
**Data**: 11/01/2026  
**Status**: ✅ Produção Ready
