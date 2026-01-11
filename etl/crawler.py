import os
import json
import time
import requests
import random
import re
from bs4 import BeautifulSoup
from amadeus import Client
from dotenv import load_dotenv
from unidecode import unidecode
from datetime import datetime, timedelta

# --- CONFIGURAÇÃO ---
load_dotenv()
AMADEUS_ID = os.getenv("AMADEUS_CLIENT_ID")
AMADEUS_SECRET = os.getenv("AMADEUS_CLIENT_SECRET")

HOJE = datetime.now()
DATA_INICIO = HOJE + timedelta(days=60)
DIAS_PARA_COLETAR = 20 

print(f"Configuração: {DATA_INICIO.strftime('%d/%m')} a {(DATA_INICIO + timedelta(days=DIAS_PARA_COLETAR)).strftime('%d/%m')}")

CIDADES = [
    # Numbeo URL  deve ser exato (ex: New-Orleans)
    {'code': 'GYN', 'nome': 'Goiania', 'pais': 'BR', 'city_name': 'Goiania', 'country': 'BR', 'numbeo': 'Goiania'},
    {'code': 'GRU', 'nome': 'Sao Paulo', 'pais': 'BR', 'city_name': 'Sao Paulo', 'country': 'BR', 'numbeo': 'Sao-Paulo'},
    {'code': 'BSB', 'nome': 'Brasilia', 'pais': 'BR', 'city_name': 'Brasilia', 'country': 'BR', 'numbeo': 'Brasilia'},
    {'code': 'ATL', 'nome': 'Atlanta', 'pais': 'US', 'city_name': 'Atlanta', 'country': 'US', 'numbeo': 'Atlanta'},
    {'code': 'ORD', 'nome': 'Chicago', 'pais': 'US', 'city_name': 'Chicago', 'country': 'US', 'numbeo': 'Chicago'},
    {'code': 'MSY', 'nome': 'New Orleans', 'pais': 'US', 'city_name': 'New Orleans', 'country': 'US', 'numbeo': 'New-Orleans'},
    {'code': 'MIA', 'nome': 'Miami', 'pais': 'US', 'city_name': 'Miami', 'country': 'US', 'numbeo': 'Miami'},
    {'code': 'JFK', 'nome': 'Nova York', 'pais': 'US', 'city_name': 'New York', 'country': 'US', 'numbeo': 'New-York'}
]

HOTEIS_BACKUP_REAL = {
    'GYN': {'nome': 'Rede Andrade Goiania Centro', 'diaria': 149.00},
    'GRU': {'nome': 'Attriun Hotel', 'diaria': 220.00},
    'BSB': {'nome': 'Hotel Helly', 'diaria': 261.00},
    'ATL': {'nome': 'Hyatt Regency Atlanta', 'diaria': 950.00},
    'ORD': {'nome': 'Palmer House Hilton', 'diaria': 890.00},
    'MSY': {'nome': 'Hotel Monteleone', 'diaria': 1100.00}
}
COMIDA_BACKUP_REAL = {'GYN': 60.0, 'GRU': 80.0, 'BSB': 75.0, 'ATL': 250.0, 'ORD': 280.0, 'MSY': 260.0}

def get_cotacao_moedas():
    try:
        req = requests.get('https://economia.awesomeapi.com.br/last/USD-BRL,EUR-BRL')
        d = req.json()
        return {'USD': float(d['USDBRL']['bid']), 'EUR': float(d['EURBRL']['bid']), 'BRL': 1.0}
    except: return {'USD': 6.0, 'EUR': 6.5, 'BRL': 1.0}

# --- FUNÇÃO AUXILIAR DE LIMPEZA ---
def limpar_valor_numbeo(texto):
    try:
        texto_limpo = unidecode(texto) 
        nums = ''.join([c for c in texto_limpo if c.isdigit() or c in ['.', ',']])
        
        if ',' in nums and '.' in nums: 
            return float(nums.replace(',', ''))
        elif ',' in nums and '.' not in nums:
            return float(nums.replace(',', '.'))
            
        return float(nums)
    except:
        return 0.0

# --- CRAWLER NUMBEO (2 REFEIÇÕES) ---
def crawler_custo_alimentacao(cidade_slug, cotacoes):
    print(f"Scraping Alimentação Numbeo em {cidade_slug}...", end="")
    time.sleep(random.uniform(10.0, 15.0)) 
    
    url = f"https://www.numbeo.com/cost-of-living/in/{cidade_slug}?displayCurrency=BRL"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Referer": "https://www.google.com/"
    }
    
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code != 200:
            print(f" (Bloqueio {resp.status_code})")
            return None
            
        soup = BeautifulSoup(resp.content, 'html.parser')
        tabela = soup.find("table", {"class": "data_wide_table"})
        
        if not tabela:
            print(" (Tabela não encontrada)")
            return None
            
        preco_refeicao_economica = 0.0
        
        for row in tabela.find_all("tr"):
            texto = row.text.lower()
            if "inexpensive restaurant" in texto and "meal" in texto:
                try:
                    span_preco = row.find("span", class_="first_currency")
                    if span_preco:
                        preco_refeicao_economica = limpar_valor_numbeo(span_preco.text)
                except: pass

        if preco_refeicao_economica > 0:
            #2 Refeições  (Almoço + Jantar)
            total_diaria = preco_refeicao_economica * 2
            print(f" Sucesso! (R$ {total_diaria:.2f}/dia - Econômico)")
            return round(total_diaria, 2)
            
        print(" (Dados vazios)")
        
    except Exception as e:
        print(f" [Erro: {e}]")
        
    return None

# --- CRAWLER BOOKING (MENOR PREÇO ENTRE OS PRIMEIROS) ---
def crawler_booking(cidade_nome, data_iso, cotacoes):
    print(f"Scraping Booking em {cidade_nome}...", end="")
    # Delay longo para evitar bloqueio
    time.sleep(random.uniform(20.0, 35.0)) 
    
    try:
        checkin = datetime.strptime(data_iso, "%Y-%m-%d")
        checkout = checkin + timedelta(days=1)
        url = "https://www.booking.com/searchresults.html"
        params = { "ss": cidade_nome, "checkin_year": checkin.year, "checkin_month": checkin.month, "checkin_monthday": checkin.day, "checkout_year": checkout.year, "checkout_month": checkout.month, "checkout_monthday": checkout.day, "group_adults": 1, "no_rooms": 1, "selected_currency": "BRL" }
        headers = { "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36", "Accept-Language": "pt-BR,pt;q=0.9" }
        
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        if resp.status_code != 200: 
            print(f" (Bloqueio {resp.status_code})")
            return None

        soup = BeautifulSoup(resp.content, 'html.parser')
        
        # Pega TODOS os cartões da primeira página
        cards = soup.find_all("div", {"data-testid": "property-card"})
        if not cards: 
            print(" (Sem dados)")
            return None
        
        melhor_hotel = None
        menor_preco = float('inf')
        
        count = 0
        for card in cards:
            if count >= 10: break
            try:
                # Extração do Preço
                preco_el = card.find("span", {"data-testid": "price-and-discounted-price"}) or card.find("div", {"data-testid": "price-and-discounted-price"})
                
                if preco_el:
                    texto = unidecode(preco_el.text.strip())
                    nums = ''.join([c for c in texto if c.isdigit() or c == ','])
                    
                    valor = 0.0
                    if ',' in nums and '.' in nums: valor = float(nums.replace(',', ''))
                    elif ',' in nums and '.' not in nums: valor = float(nums.replace(',', '.'))
                    else: valor = float(nums)
                    
                    if valor > 50.0:
                        if valor < menor_preco:
                            menor_preco = valor
                            # Extração do Nome (Segura)
                            nome_el = card.find("div", {"data-testid": "title"})
                            nome_hotel = nome_el.text.strip() if nome_el else "Hotel Booking"
                            melhor_hotel = {'nome': nome_hotel, 'diaria': valor}
                        count += 1
            except: continue
        
        if melhor_hotel:
            print(f" Sucesso! {melhor_hotel['nome']} (R$ {melhor_hotel['diaria']:.2f})")
            return melhor_hotel

    except Exception as e:
        print(f" [Erro: {e}]")
    
    return None

# --- API TRANSFER ---
def buscar_transfer_api(cidade_info, data_iso, amadeus, cotacoes):
    print(f"Buscando transfer em {cidade_info['code']}...", end="")
    try:
        body = { "startLocationCode": cidade_info['code'], "endAddressLine": f"City Center {cidade_info['city_name']}", "endCityName": cidade_info['city_name'], "endCountryCode": cidade_info['country'], "passengers": 1, "startDateTime": f"{data_iso}T14:00:00" }
        response = amadeus.post('/v1/shopping/transfer-offers', body)
        if not response.data: 
            print(" (Sem ofertas)")
            return None
        menor = float('inf')
        for offer in response.data:
            try:
                val = float(offer['quotation']['monetaryAmount'])
                moeda = offer['quotation']['currencyCode']
                brl = val * cotacoes.get(moeda, cotacoes.get('USD', 1.0))
                if brl < menor: menor = brl
            except: continue
        if menor == float('inf'): return None
        print(f" Achou! R$ {menor:.2f}")
        return round(menor, 2)
    except: 
        print(" [API Off]")
        return None

# --- ORQUESTRADOR DE DADOS LOCAIS ---
def buscar_dados_locais_inteligentes(cidade, amadeus, cotacoes):
    # 1. Hotel (API -> Crawler -> Cache)
    print(f"Buscando hotel em {cidade['code']}...", end="")
    hotel_res = None
    try:
        hoteis = amadeus.reference_data.locations.hotels.by_city.get(cityCode=cidade['code'])
        if hoteis.data:
            ids = [h['hotelId'] for h in hoteis.data[:2]]
            offers = amadeus.shopping.hotel_offers_search.get(hotelIds=','.join(ids), adults='1', checkInDate=DATA_INICIO.strftime('%Y-%m-%d'), checkOutDate=(DATA_INICIO + timedelta(days=1)).strftime('%Y-%m-%d'))
            if offers.data:
                best = offers.data[0]
                val = float(best['offers'][0]['price']['total'])
                taxa = cotacoes.get(best['offers'][0]['price']['currency'], cotacoes.get('USD', 1.0))
                if best['offers'][0]['price']['currency'] == 'USD': taxa = cotacoes['USD']
                print(f" API OK ({best['hotel']['name']})")
                hotel_res = {'nome': best['hotel']['name'], 'diaria': round(val * taxa, 2)}
    except: pass
    
    if not hotel_res:
        print("")
        hotel_res = crawler_booking(cidade['nome'], DATA_INICIO.strftime('%Y-%m-%d'), cotacoes)
    if not hotel_res:
        hotel_res = HOTEIS_BACKUP_REAL.get(cidade['code'], {'nome': 'Hotel Padrão', 'diaria': 300.0})
        print(f"   🛡️ Cache Hotel ({hotel_res['nome']})")

    # 2. Comida (Crawler -> Cache)
    print("")
    custo_comida = crawler_custo_alimentacao(cidade['numbeo'], cotacoes)
    if not custo_comida:
        custo_comida = COMIDA_BACKUP_REAL.get(cidade['code'], 60.00)
        print(f"Cache Comida (R$ {custo_comida:.2f})")

    return hotel_res, custo_comida

# --- BUSCA DE VOOS (COM HORÁRIO) ---
def buscar_voo_detalhado(origem, destino, data_iso, amadeus, cotacoes):
    try:
        response = amadeus.shopping.flight_offers_search.get(originLocationCode=origem, destinationLocationCode=destino, departureDate=data_iso, adults=1, max=1)
        if not response.data: return None
        offer = response.data[0]
        
        # Preço
        val = float(offer['price']['total'])
        preco = round(val * cotacoes.get(offer['price']['currency'], cotacoes.get('USD', 6.0)), 2)
        
        # Segmentos e Horário
        seg = offer['itineraries'][0]['segments'][0]
        dur = offer['itineraries'][0]['duration']
        
        # Extração Hora de Saída (ex: 2026-02-28T20:55:00 -> 20:55)
        data_hora_completa = seg['departure']['at']
        hora_saida = data_hora_completa.split('T')[1][:5]
        
        # Duração
        h, m = 0, 0
        if 'H' in dur: h = int(dur.split('H')[0].replace('PT',''))
        if 'M' in dur: 
            if 'H' in dur: m = int(dur.split('H')[1].replace('M',''))
            else: m = int(dur.replace('PT','').replace('M',''))
            
        return {
            'preco': preco, 
            'tempo': h*60+m, 
            'cia': seg['carrierCode'], 
            'voo_cod': f"{seg['carrierCode']}{seg['number']}", 
            'hora_saida': hora_saida
        }
    except: return None

# --- EXECUÇÃO PRINCIPAL ---
def executar_etl_final():
    print(f"INICIANDO COLETA DE DADOS (MODELO FINAL)")
    amadeus = Client(client_id=AMADEUS_ID, client_secret=AMADEUS_SECRET)
    cotacoes = get_cotacao_moedas()
    database = {'metadata': {'inicio': str(DATA_INICIO)}, 'nos': {}, 'arestas': []}
    
    print("\nColetando Dados Locais...")
    data_ref = DATA_INICIO.strftime('%Y-%m-%d')
    for cidade in CIDADES:
        hotel_info, custo_food = buscar_dados_locais_inteligentes(cidade, amadeus, cotacoes)
        transfer_trecho = buscar_transfer_api(cidade, data_ref, amadeus, cotacoes)
        transfer_total = transfer_trecho * 2 if transfer_trecho else 200.00
            
        # JSON com os nomes corrigidos
        database['nos'][cidade['code']] = {
            'nome': cidade['nome'], 
            'pais': cidade['pais'],
            'custo_refeicao_diaria': round(custo_food, 2),
            'hotel_nome': hotel_info['nome'], 
            'custo_diaria_hotel': hotel_info['diaria'],
            'transporte': { 'transfer_ida_volta': round(transfer_total, 2) }
        }

    print("\nColetando Voos...")
    datas = [DATA_INICIO + timedelta(days=i) for i in range(DIAS_PARA_COLETAR)]
    for data_obj in datas:
        data_str = data_obj.strftime('%Y-%m-%d')
        print(f"   📅 {data_str}: ", end="")
        found = 0
        for origem in CIDADES:
            for destino in CIDADES:
                if origem['code'] == destino['code']: continue
                res = buscar_voo_detalhado(origem['code'], destino['code'], data_str, amadeus, cotacoes)
                if res:
                    database['arestas'].append({
                        'origem': origem['code'], 'destino': destino['code'], 
                        'data_voo': data_str, 
                        'hora_saida': res['hora_saida'], # Nome corrigido
                        'custo_passagem': res['preco'], 'tempo_voo': res['tempo'], 
                        'cia': res['cia'], 'voo_cod': res['voo_cod']
                    })
                    found += 1
        print(f"OK ({found})")
        time.sleep(1.5) 

    os.makedirs('data', exist_ok=True)
    with open('data/database.json', 'w', encoding='utf-8') as f: 
        json.dump(database, f, indent=4, ensure_ascii=False)
    print("\nCOLETA FINALIZADA!")

if __name__ == "__main__":
    executar_etl_final()