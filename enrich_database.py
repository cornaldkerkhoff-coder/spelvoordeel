# STREAMING_CHUNK: Updaten van het Python-script voor GitHub Actions...
```python:Database Enricher Script:enrich_database.py
import os
import time
import urllib.parse
import re
import pandas as pd
import requests

# =====================================================================
# DEZE GEGEVENS WORDEN NU VEILIG UIT GITHUB SECRETS GEHAALD
# Dit voorkomt dat anderen jouw database codes kunnen zien op GitHub!
# =====================================================================
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

# Headers voor de communicatie met de Supabase database API
HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "resolution=merge-duplicates"
}

def find_feed_file():
    """
    Zoekt automatisch naar het juiste bestand in de map op GitHub.
    """
    possible_files = [
        "Productfeed.xlsx - Sheet.csv",
        "Productfeed.xlsx",
        "Productfeed.csv"
    ]
    for file in possible_files:
        if os.path.exists(file):
            return file
    return None

def get_image_from_barcode_lookup(ean_str):
    """
    Zoekt de echte productafbeelding rechtstreeks op Barcode Lookup via de EAN-code.
    """
    try:
        url = f"https://www.barcodelookup.com/{ean_str}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'nl-NL,nl;q=0.9,en-US;q=0.8,en;q=0.7',
            'Referer': 'https://www.google.com/'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            html = response.text
            matches = re.findall(r'id="product-image"[^>]*src="([^"]+)"', html)
            if not matches:
                matches = re.findall(r'https://images\.barcodelookup\.com/images/choices/[^"\s>]+', html)
            
            if matches:
                image_url = matches[0]
                if image_url.startswith('//'):
                    image_url = 'https:' + image_url
                return image_url
                
            img_tags = re.findall(r'<img[^>]*src="([^"]+)"', html)
            for img in img_tags:
                if 'images.barcodelookup.com' in img:
                    if img.startswith('//'):
                        return 'https:' + img
                    return img
    except Exception as e:
        print(f"  [Fout bij Barcode Lookup]: {e}")
    return None

def get_image_by_ean(ean, name):
    """
    Hoofdfunctie om de afbeelding te zoeken via verschillende bronnen.
    """
    if not ean or pd.isna(ean):
        return None
        
    ean_str = str(ean).split('.')[0].strip() # Schoon decimalen op
    if len(ean_str) < 10:
        return None

    # STAP 1: Barcode Lookup
    print(f"  -> Zoeken op Barcode Lookup...")
    img = get_image_from_barcode_lookup(ean_str)
    if img:
        return img

    # STAP 2: Openbare barcode API als back-up (UpcItemDb)
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

    return None

def main():
    print("=== BOOSTERBOX AFBEELDINGEN ZOEKER (GITHUB CLOUD EDITIE) ===")
    
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("[FOUT] Supabase URL of Key ontbreekt in de GitHub Secrets!")
        return

    # Zoek het bestand
    feed_file = find_feed_file()
    if not feed_file:
        print("[FOUT] Geen productfeed bestand gevonden in je GitHub repository!")
        return
        
    print(f"Bestand gevonden: '{feed_file}'")
    
    # Lees het bestand in
    try:
        if feed_file.endswith('.csv'):
            try:
                df = pd.read_csv(feed_file, sep=',')
                if len(df.columns) < 2:
                    df = pd.read_csv(feed_file, sep=';')
            except Exception:
                df = pd.read_csv(feed_file, sep=';')
        else:
            df = pd.read_excel(feed_file)
    except Exception as e:
        print(f"[FOUT] Kan het bestand niet openen: {e}")
        return
    
    # We pakken voor de veiligheid en snelheid de eerste 50 producten per run
    # zodat GitHub niet urenlang blijft draaien en geblokkeerd wordt.
    df_slice = df.head(50)
    total_rows = len(df_slice)
    print(f"Succesvol ingelezen! We gaan nu de eerste {total_rows} producten verwerken.")
    
    successful_updates = 0
    
    for index, row in df_slice.iterrows():
        sku = str(row['Artikelnummer'])
        ean = row['EAN']
        name = str(row['Naam'])
        
        print(f"\n[{index + 1}/{total_rows}] Bezig met: {name} (EAN: {ean})...")
        
        # Zoek de afbeelding
        image_url = get_image_by_ean(ean, name)
        
        if image_url:
            print(f"  -> AFBEELDING GEVONDEN: {image_url}")
            
            # Update in Supabase
            supabase_endpoint = f"{SUPABASE_URL}/rest/v1/products?sku=eq.{sku}"
            payload = {
                "image_url": image_url
            }
            
            try:
                response = requests.patch(supabase_endpoint, json=payload, headers=HEADERS)
                if response.status_code in [200, 201, 204]:
                    print("  -> Succesvol opgeslagen in Supabase database!")
                    successful_updates += 1
                else:
                    print(f"  -> [DB FOUT] Opslaan mislukt: {response.text}")
            except Exception as e:
                print(f"  -> [VERBINDINGSFOUT] Kan niet verbinden met Supabase: {e}")
        else:
            print("  -> Helaas geen afbeelding kunnen vinden voor dit product.")
            
        # 3 seconden pauze om netjes te blijven voor de servers
        time.sleep(3.0)

    print("\n=== SCRIPT AFGEROND ===")
    print(f"Succesvol verrijkt in deze run: {successful_updates} van de {total_rows} producten.")

if __name__ == "__main__":
    main()
