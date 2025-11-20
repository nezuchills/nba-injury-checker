import os
import json
import requests
import unicodedata
import re
from datetime import datetime
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from bs4 import BeautifulSoup
from nba_api.stats.endpoints import commonallplayers, commonplayerinfo

app = FastAPI(title="NBA Injury API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Cache-Control': 'no-cache',
    'Pragma': 'no-cache'
}

JSON_FILE = 'nba_players.json'
PLAYER_CACHE = {}

# Overrides manuels si l'API NBA est en retard sur les transferts récents
MANUAL_OVERRIDES = {
    "Damian Lillard": "portland-trail-blazers", # Exemple selon votre requête
}

def normalize_text(text):
    if not text: return ""
    return ''.join(c for c in unicodedata.normalize('NFD', str(text)) if unicodedata.category(c) != 'Mn').lower().strip()

def generate_team_slug(team_city, team_name):
    """Génère le slug pour NBC : 'Portland', 'Trail Blazers' -> 'portland-trail-blazers'"""
    full_name = f"{team_city} {team_name}"
    return full_name.lower().replace(" ", "-").replace(".", "").replace("'", "")

def update_player_database():
    print("Mise à jour de la base de données joueurs via NBA API...")
    try:
        # On récupère ID et Nom pour la recherche
        nba_response = commonallplayers.CommonAllPlayers(is_only_current_season=1)
        data = nba_response.get_dict()
        headers = data['resultSets'][0]['headers']
        rows = data['resultSets'][0]['rowSet']
        
        players_dict = {}
        idx_id = headers.index('PERSON_ID')
        idx_name = headers.index('DISPLAY_FIRST_LAST')
        
        for row in rows:
            pid = row[idx_id]
            name = row[idx_name]
            players_dict[name] = {"id": pid, "name": name}
        
        with open(JSON_FILE, 'w') as f:
            json.dump(players_dict, f)
        return players_dict
    except Exception as e:
        print(f"Erreur NBA API Update: {e}")
        return {}

def load_player_database():
    global PLAYER_CACHE
    if os.path.exists(JSON_FILE):
        with open(JSON_FILE, 'r') as f:
            PLAYER_CACHE = json.load(f)
    else:
        PLAYER_CACHE = update_player_database()

def get_player_details(player_id):
    """Récupère l'âge, l'équipe actuelle et la position via l'endpoint Detail."""
    try:
        # Appel à l'API NBA pour les détails
        info = commonplayerinfo.CommonPlayerInfo(player_id=player_id)
        data = info.get_dict()['resultSets'][0]
        headers = data['headers']
        row = data['rowSet'][0]
        
        # Extraction sécurisée avec index
        def get_val(key):
            return row[headers.index(key)] if key in headers else "N/A"

        # Calcul de l'âge si BIRTHDATE est présent
        birthdate_str = get_val('BIRTHDATE') # Format: 1990-07-15T00:00:00
        age = "N/A"
        if birthdate_str and "T" in birthdate_str:
            b_date = datetime.strptime(birthdate_str.split('T')[0], "%Y-%m-%d")
            today = datetime.today()
            age = today.year - b_date.year - ((today.month, today.day) < (b_date.month, b_date.day))

        team_city = get_val('TEAM_CITY')
        team_name = get_val('TEAM_NAME')
        
        # Gestion des override manuel pour l'équipe
        player_name = get_val('DISPLAY_FIRST_LAST')
        team_slug = generate_team_slug(team_city, team_name)
        
        if player_name in MANUAL_OVERRIDES:
            team_slug = MANUAL_OVERRIDES[player_name]
            # On met à jour le nom d'affichage pour que ça soit cohérent
            team_name = team_slug.replace("-", " ").title() 

        return {
            "age": str(age),
            "team_name": f"{team_city} {team_name}",
            "team_slug": team_slug,
            "position": get_val('POSITION'),
            "jersey": get_val('JERSEY')
        }
    except Exception as e:
        print(f"Erreur Details: {e}")
        return {"age": "?", "team_name": "Unknown", "team_slug": "", "position": "?"}

def clean_regex_result(text):
    text = re.sub(r'<[^>]+>', '', text)
    text = text.replace('"', '').replace('{', '').replace('}', '').replace('\\', '')
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:350] + "..."

# --- SCRAPING NBC CIBLÉ ---

def scrape_nbc_team_page(team_slug, player_name):
    """
    Cherche sur la page : https://www.nbcsports.com/nba/{team-slug}/injuries
    Utilise le Regex car les données sont souvent dans un widget JS Sportradar.
    """
    if not team_slug: return "Équipe inconnue"
    
    url = f"https://www.nbcsports.com/nba/{team_slug}/injuries"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=8)
        # Fallback 404 : parfois l'URL est sans le '/injuries' pour les news générales
        if response.status_code == 404:
             url = f"https://www.nbcsports.com/nba/{team_slug}"
             response = requests.get(url, headers=HEADERS, timeout=8)

        page_source = response.text
        
        # On cherche le nom de famille du joueur
        lastname = player_name.split()[-1]
        
        # REGEX: Cherche le nom + du texte jusqu'à trouver des mots clés de statut
        # Pattern : Lastname ... (texte de 10 à 400 caractères)
        match = re.search(rf"{re.escape(lastname)}.*?(.{{10,400}})", page_source, re.IGNORECASE | re.DOTALL)
        
        if match:
            raw_fragment = match.group(1)
            cleaned = clean_regex_result(raw_fragment)
            
            # Filtre de pertinence
            keywords = ['injury', 'out', 'status', 'surgery', 'strain', 'questionable', 'doubtful', 'probable', 'available', 'sidelined', 'weeks', 'days']
            if any(k in cleaned.lower() for k in keywords):
                return cleaned
            else:
                # Si on trouve le nom mais pas de mot clé blessure proche, on renvoie quand même le snippet
                # car ça peut être une news tactique
                return f"News: {cleaned}"

        return f"Aucune blessure signalée sur la page {team_slug}."

    except Exception as e:
        return f"Erreur NBC: {e}"

def scrape_rotowire(player_name):
    # Backup simple
    try:
        url = "https://www.rotowire.com/basketball/injury-report.php"
        res = requests.get(url, headers=HEADERS, timeout=5)
        soup = BeautifulSoup(res.content, 'html.parser')
        links = soup.find_all('a', href=True)
        norm_name = normalize_text(player_name)
        for link in links:
            if "player" in link['href'] and norm_name in normalize_text(link.text):
                row = link.find_parent('div', class_='injury-report__row')
                if row:
                    inj = row.find(class_='injury-report__injury')
                    status = row.find(class_='injury-report__status')
                    return f"{status.text.strip()} - {inj.text.strip()}" if status and inj else "Info trouvée"
        return None
    except:
        return None

# --- ROUTES ---

@app.on_event("startup")
def startup_event():
    load_player_database()

@app.get("/")
def home():
    return "API NBA Ready"

@app.get("/api/players")
def get_all_players():
    return list(PLAYER_CACHE.keys())

@app.get("/api/check")
def check_injury(player: str = Query(..., min_length=1)):
    
    # 1. Récupération ID et Métadonnées
    player_data = PLAYER_CACHE.get(player)
    if not player_data:
        # Recherche fuzzy simple
        for name, data in PLAYER_CACHE.items():
            if normalize_text(player) in normalize_text(name):
                player_data = data
                player = name # Correction du nom
                break
    
    if not player_data:
        return {"error": "Joueur introuvable"}

    # 2. Appel API NBA pour détails frais (Age, Team exact)
    details = get_player_details(player_data['id'])
    
    # 3. Scraping ciblé sur l'équipe
    nbc_info = scrape_nbc_team_page(details['team_slug'], player)
    roto_info = scrape_rotowire(player)

    return {
        "player": player,
        "meta": {
            "age": details['age'],
            "team": details['team_name'],
            "position": details['position'],
            "jersey": details['jersey']
        },
        "sources": {
            "NBC": nbc_info,
            "Rotowire": roto_info if roto_info else "Rien à signaler"
        }
    }

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    uvicorn.run(app, host='0.0.0.0', port=port)
