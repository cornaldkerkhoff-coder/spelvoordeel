import os
import pandas as pd
import requests

# Haalt gegevens veilig uit GitHub Secrets
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
HEADERS = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json"}

def main():
    # Zorg dat deze bestandsnaam precies overeenkomt met wat in je repository staat
    feed_bestand = "Productfeed.xlsx - Sheet.csv"
    if not os.path.exists(feed_bestand):
        print(f"Fout: Kan bestand {feed_bestand} niet vinden!")
        return
        
    df = pd.read_csv(feed_bestand)
    for _, row in df.iterrows():
        # Kolomnamen 'Artikelnummer' en 'Naam' moeten exact zo in je CSV staan
        payload = {"sku": str(row['Artikelnummer']), "naam": str(row['Naam'])}
        res = requests.post(f"{SUPABASE_URL}/rest/v1/spellendata", json=payload, headers=HEADERS)
        print(f"Status voor {row['Naam']}: {res.status_code}")

if __name__ == "__main__":
    main()
