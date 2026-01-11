# 📝 Exemplos de Resposta da API v2.0

Este documento mostra exemplos reais das respostas dos endpoints implementados.

---

## 1. Endpoint `/optimize` - Nível Ótimo

### Request
```json
POST /optimize
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
  "incluir_transporte": true
}
```

### Response
```json
{
  "rota": {
    "origem": "GYN",
    "destino": "GRU",
    "caminho": ["GYN", "GRU"],
    "trechos": [
      {
        "origem": "GYN",
        "destino": "GRU",
        "voo": {
          "id": "G3-1234_2026-03-10_08:00:00",
          "cia": "GOL",
          "codigo": "G3-1234",
          "data": "2026-03-10",
          "saida": "08:00:00",
          "duracao_min": 120.0,
          "preco": 450.50
        }
      }
    ]
  },
  "custos": {
    "total": 1850.50,
    "voos": 450.50,
    "hospedagem": 900.00,
    "alimentacao": 450.00,
    "transporte": 50.00
  },
  "detalhes": {
    "hospedagem": [
      {
        "cidade": "GRU",
        "diarias": 3,
        "diaria": 300.00,
        "total": 900.00
      }
    ],
    "alimentacao": [
      {
        "cidade": "GRU",
        "diarias": 3,
        "custo_dia": 150.00,
        "total": 450.00
      }
    ],
    "transporte": [
      {
        "cidade": "GRU",
        "diarias": 3,
        "custo_dia": 16.67,
        "total": 50.00
      }
    ]
  },
  "metadata": {
    "nivel_otimizacao": "otima",
    "nota": "Solução ótima encontrada",
    "tempo_computacao": 12.5
  }
}
```

---

## 2. Endpoint `/optimize` - Nível Relaxado

### Response (quando nível ótimo falha)
```json
{
  "rota": {
    "origem": "GYN",
    "destino": "MIA",
    "caminho": ["GYN", "GRU", "MIA"],
    "trechos": [
      {
        "origem": "GYN",
        "destino": "GRU",
        "voo": {
          "id": "G3-1234_2026-03-10_08:00:00",
          "cia": "GOL",
          "codigo": "G3-1234",
          "data": "2026-03-10",
          "saida": "08:00:00",
          "duracao_min": 120.0,
          "preco": 450.50
        }
      },
      {
        "origem": "GRU",
        "destino": "MIA",
        "voo": {
          "id": "AA-8765_2026-03-11_14:30:00",
          "cia": "American Airlines",
          "codigo": "AA-8765",
          "data": "2026-03-11",
          "saida": "14:30:00",
          "duracao_min": 540.0,
          "preco": 1850.00
        }
      }
    ]
  },
  "custos": {
    "total": 5950.50,
    "voos": 2300.50,
    "hospedagem": 2400.00,
    "alimentacao": 1200.00,
    "transporte": 50.00
  },
  "detalhes": {
    "hospedagem": [...],
    "alimentacao": [...],
    "transporte": [...]
  },
  "metadata": {
    "nivel_otimizacao": "boa",
    "nota": "Solução com restrições relaxadas",
    "tempo_computacao": 45.2
  }
}
```

---

## 3. Endpoint `/optimize` - Nível Básico (Fallback)

### Response (quando todos os níveis anteriores falham)
```json
{
  "rota": {
    "origem": "GYN",
    "destino": "CGH",
    "caminho": ["GYN", "CGH"],
    "trechos": [
      {
        "origem": "GYN",
        "destino": "CGH",
        "voo": {
          "id": "LA-5678_2026-03-10_12:00:00",
          "cia": "LATAM",
          "codigo": "LA-5678",
          "data": "2026-03-10",
          "saida": "12:00:00",
          "duracao_min": 110.0,
          "preco": 380.00
        }
      }
    ]
  },
  "custos": {
    "total": 380.00,
    "voos": 380.00,
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
    "tempo_computacao": 62.1
  }
}
```

---

## 4. Endpoint `/optimize` - Erro Controlado

### Response (quando nenhum voo disponível)
```json
{
  "rota": {
    "origem": "GYN",
    "destino": "XYZ",
    "caminho": ["GYN", "XYZ"],
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
    "nota": "Nenhum voo disponível para a data e rota solicitadas",
    "tempo_computacao": 0.0
  }
}
```

**IMPORTANTE**: Mesmo em caso de erro, a estrutura é válida (não retorna `null`)

---

## 5. Endpoint `/optimize-multiple` - Múltiplas Opções

### Request
```json
POST /optimize-multiple
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

### Response
```json
{
  "opcoes": [
    {
      "id": 1,
      "ranking": 1,
      "titulo": "Melhor Custo-Benefício",
      "descricao": "Equilíbrio entre preço e conforto",
      "rota": {
        "origem": "GYN",
        "destino": "GRU",
        "caminho": ["GYN", "GRU"],
        "trechos": [
          {
            "origem": "GYN",
            "destino": "GRU",
            "voo": {
              "id": "G3-1234_2026-03-10_08:00:00",
              "cia": "GOL",
              "codigo": "G3-1234",
              "data": "2026-03-10",
              "saida": "08:00:00",
              "duracao_min": 120.0,
              "preco": 450.50
            }
          }
        ]
      },
      "custos": {
        "total": 1850.50,
        "voos": 450.50,
        "hospedagem": 900.00,
        "alimentacao": 450.00,
        "transporte": 50.00
      },
      "detalhes": {
        "hospedagem": [...],
        "alimentacao": [...],
        "transporte": [...]
      },
      "custo_total": 1850.50,
      "tempo_total_viagem": 2.0,
      "numero_escalas": 0,
      "pontuacao": {
        "custo": 10.0,
        "tempo": 10.0,
        "conforto": 10.0,
        "geral": 10.0
      },
      "vantagens": [
        "Menor preço",
        "Viagem rápida",
        "Maior conforto",
        "Voo direto",
        "Excelente custo-benefício"
      ],
      "desvantagens": []
    },
    {
      "id": 2,
      "ranking": 2,
      "titulo": "Mais Econômica",
      "descricao": "Menor custo total, pode ter mais escalas",
      "rota": {
        "origem": "GYN",
        "destino": "GRU",
        "caminho": ["GYN", "BSB", "GRU"],
        "trechos": [
          {
            "origem": "GYN",
            "destino": "BSB",
            "voo": {
              "id": "G3-5555_2026-03-10_06:00:00",
              "cia": "GOL",
              "codigo": "G3-5555",
              "data": "2026-03-10",
              "saida": "06:00:00",
              "duracao_min": 45.0,
              "preco": 180.00
            }
          },
          {
            "origem": "BSB",
            "destino": "GRU",
            "voo": {
              "id": "LA-3333_2026-03-10_11:00:00",
              "cia": "LATAM",
              "codigo": "LA-3333",
              "data": "2026-03-10",
              "saida": "11:00:00",
              "duracao_min": 110.0,
              "preco": 250.00
            }
          }
        ]
      },
      "custos": {
        "total": 1780.00,
        "voos": 430.00,
        "hospedagem": 900.00,
        "alimentacao": 450.00,
        "transporte": 0.0
      },
      "detalhes": {...},
      "custo_total": 1780.00,
      "tempo_total_viagem": 2.58,
      "numero_escalas": 1,
      "pontuacao": {
        "custo": 10.0,
        "tempo": 8.5,
        "conforto": 5.0,
        "geral": 7.8
      },
      "vantagens": [
        "Menor preço",
        "Apenas 1 escala"
      ],
      "desvantagens": [
        "1 escala"
      ]
    },
    {
      "id": 3,
      "ranking": 3,
      "titulo": "Mais Rápida e Confortável",
      "descricao": "Voos diretos, menor tempo total",
      "rota": {
        "origem": "GYN",
        "destino": "GRU",
        "caminho": ["GYN", "GRU"],
        "trechos": [
          {
            "origem": "GYN",
            "destino": "GRU",
            "voo": {
              "id": "G3-9999_2026-03-10_15:00:00",
              "cia": "GOL",
              "codigo": "G3-9999",
              "data": "2026-03-10",
              "saida": "15:00:00",
              "duracao_min": 115.0,
              "preco": 580.00
            }
          }
        ]
      },
      "custos": {
        "total": 1980.00,
        "voos": 580.00,
        "hospedagem": 900.00,
        "alimentacao": 450.00,
        "transporte": 50.00
      },
      "detalhes": {...},
      "custo_total": 1980.00,
      "tempo_total_viagem": 1.92,
      "numero_escalas": 0,
      "pontuacao": {
        "custo": 5.0,
        "tempo": 10.0,
        "conforto": 10.0,
        "geral": 8.3
      },
      "vantagens": [
        "Viagem rápida",
        "Maior conforto",
        "Voo direto"
      ],
      "desvantagens": [
        "Preço mais alto"
      ]
    }
  ],
  "recomendacao": 1,
  "metadata": {
    "tempo_computacao": 78.5,
    "numero_opcoes_geradas": 3,
    "numero_opcoes_solicitadas": 3
  }
}
```

---

## 6. Endpoint `/available-dates`

### Request
```bash
GET /available-dates
```

### Response
```json
{
  "data_minima": "2026-03-01",
  "data_maxima": "2026-12-31",
  "mensagem": "Voos disponíveis de 2026-03-01 até 2026-12-31"
}
```

---

## 🎯 Interpretando as Respostas

### Campo `metadata.nivel_otimizacao`

| Valor | Significado | Ação Sugerida |
|-------|-------------|---------------|
| `"otima"` | Solução matematicamente ótima | ✅ Usar normalmente |
| `"boa"` | Solução viável com restrições relaxadas | ✅ Avisar usuário |
| `"viavel"` | Solução heurística | ⚠️ Mostrar como alternativa |
| `"basica"` | Rota simples de fallback | ⚠️ Sugerir ajustar parâmetros |
| `"erro"` | Nenhuma solução encontrada | ❌ Sugerir outras datas/rotas |

### Campo `pontuacao` (0-10)

- **10.0**: Melhor possível nesta métrica
- **7.0-9.9**: Muito bom
- **5.0-6.9**: Bom
- **3.0-4.9**: Regular
- **0.0-2.9**: Ruim

### Campo `recomendacao`

Indica qual opção tem a maior `pontuacao.geral`, ou seja, o melhor equilíbrio entre custo, tempo e conforto.

---

## 📊 Exemplos de Uso no Frontend

### Exibir Nível de Otimização
```javascript
const nivel = response.metadata.nivel_otimizacao;
const badge = {
  "otima": { color: "green", icon: "⭐⭐⭐⭐⭐", text: "Ótima" },
  "boa": { color: "blue", icon: "⭐⭐⭐⭐", text: "Boa" },
  "viavel": { color: "yellow", icon: "⭐⭐⭐", text: "Viável" },
  "basica": { color: "orange", icon: "⭐⭐", text: "Básica" },
  "erro": { color: "red", icon: "⚠️", text: "Erro" }
}[nivel];
```

### Comparar Opções
```javascript
const opcoes = response.opcoes;
opcoes.forEach(opcao => {
  console.log(`${opcao.titulo} - R$ ${opcao.custo_total}`);
  console.log(`Pontuação: ${opcao.pontuacao.geral}/10`);
  console.log(`Vantagens: ${opcao.vantagens.join(', ')}`);
});
```

### Destacar Recomendação
```javascript
const recomendada = response.opcoes.find(
  op => op.id === response.recomendacao
);
// Destacar visualmente no UI
```

---

**Data**: 11/01/2026  
**Versão**: 2.0.0
