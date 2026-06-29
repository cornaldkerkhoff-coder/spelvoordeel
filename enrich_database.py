import os
import time
import re
import pandas as pd
import requests

# =====================================================================
# INSTELLINGEN: VUL HIER JOUW EIGEN SUPABASE GEGEVENS IN
# =====================================================================
SUPABASE_URL = "JOUW_SUPABASE_URL_HIER"      # Bijv: https://gqasdfasdfasdf.supabase.co
SUPABASE_KEY = "JOUW_SUPABASE_ANON_KEY_HIER"  # Je lange anon/public API key

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "resolution=merge-duplicates"
}

def vind_productfeed_bestand():
    mogelijke_bestanden = [
        "Productfeed.xlsx - Sheet.csv",
        "Productfeed.xlsx",
        "Productfeed.csv"
    ]
    for bestand in mogelijke_bestanden:
        if os.path.exists(bestand):
            return bestand
    return None

def zoek_afbeelding_op_barcode(ean_str):
    try:
        url = f"https://api.upcitemdb.com/prod/trial/lookup?upc={ean_str}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('items') and len(data['items']) > 0:
                images = data['items'][0].get('images', [])
                if images:
                    return images[0]
    except Exception:
        pass
        
    try:
        url = f"https://www.barcodelookup.com/{ean_str}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            html = response.text
            matches = re.findall(r'id="product-image"[^>]*src="([^"]+)"', html)
            if matches:
                img_url = matches[0]
                if img_url.startswith('//'):
                    img_url = 'https:' + img_url
                return img_url
    except Exception:
        pass
        
    return None

def main():
    print("=== SPELlENSHOP - DATABASE VERRIJKER VANAF DE PC ===")
    
    if SUPABASE_URL == "JOUW_SUPABASE_URL_HIER" or SUPABASE_KEY == "JOUW_SUPABASE_ANON_KEY_HIER":
        print("[FOUT] Vul eerst je eigen Supabase URL en Anon Key in bovenaan dit script!")
        return

    feed_bestand = vind_productfeed_bestand()
    if -not feed_bestand:
        print("[FOUT] Geen productfeed gevonden! Zorg dat 'Productfeed.xlsx - Sheet.csv' in dezelfde map staat als dit script.")
        return
        
    print(f"Productfeed gevonden: '{feed_bestand}'")
    
    try:
        if feed_bestand.endswith('.csv'):
            try:
                df = pd.read_csv(feed_bestand, sep=',')
                if len(df.columns) < 2:
                    df = pd.read_csv(feed_bestand, sep=';')
            except Exception:
                df = pd.read_csv(feed_bestand, sep=';')
        else:
            df = pd.read_excel(feed_bestand)
    except Exception as e:
        print(f"[FOUT] Kan bestand niet openen: {e}")
        return
        
    totaal = len(df)
    print(f"Succesvol ingelezen! Totaal {totaal} producten in de feed.")
    
    succesvol = 0
    
    for index, row in df.iterrows():
        sku = str(row['Artikelnummer'])
        ean = str(row['EAN']).split('.')[0].strip() if not pd.isna(row['EAN']) else ""
        naam = str(row['Naam'])
        
        print(f"\n[{index + 1}/{totaal}] Zoeken naar: {naam} (EAN: {ean})...")
        
        if not ean or len(ean) < 10:
            print("  -> Overgeslagen: Geen geldige EAN barcode aanwezig.")
            continue
            
        afbeelding_url = zoek_afbeelding_op_barcode(ean)
        
        if afbeelding_url:
            print(f"  -> AFBEELDING GEVONDEN: {afbeelding_url}")
            
            endpoint = f"{SUPABASE_URL}/rest/v1/products?sku=eq.{sku}"
            payload = {"image_url": afbeelding_url}
            
            try:
                res = requests.patch(endpoint, json=payload, headers=HEADERS)
                if res.status_code in [200, 201, 204]:
                    print("  -> Succesvol opgeslagen in Supabase!")
                    succesvol += 1
                else:
                    print(f"  -> [Database Fout]: {res.text}")
            except Exception as e:
                print(f"  -> [Verbindingsfout]: {e}")
        else:
            print("  -> Geen afbeelding gevonden.")
            
        time.sleep(2.0)

    print("\n=== KLAAR! ===")
    print(f"Er zijn {succesvol} afbeeldingen succesvol aan je database toegevoegd!")

if __name__ == "__main__":
    main()
