import os
import time
import pandas as pd
import requests

SUPABASE_URL = os.environ.get("SUPABASE_URL", "JOUW_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "JOUW_KEY")

HEADERS = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json"}

def main():
    feed_bestand = "Productfeed.xlsx - Sheet.csv"
    if not os.path.exists(feed_bestand):
        print("Bestand niet gevonden.")
        return
        
    df = pd.read_csv(feed_bestand)
    for index, row in df.head(50).iterrows():
        sku = str(row['Artikelnummer'])
        print(f"Verwerken: {row['Naam']}")
        # Aangepast naar jouw tabelnaam: spellendata
        # endpoint = f"{SUPABASE_URL}/rest/v1/spellendata?sku=eq.{sku}"
        time.sleep(1.0)

if __name__ == "__main__":
    main()
