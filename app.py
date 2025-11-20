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

# Headers renforcés pour imiter un vrai navigateur et passer les protections basiques
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Cache-Control': 'max-age=0',
}

JSON_FILE = 'nba_players.json'
PLAYER_CACHE = {}

# Overrides manuels
MANUAL_OVERRIDES = {
    "Damian Lillard": "portland-trail-blazers",
}

def normalize_text(text):
    if not text: return ""
    return ''.join(c for c in unicodedata.normalize('NFD', str(text)) if unicodedata.category(c) != 'Mn').lower().strip()

def generate_team_slug(team_city, team_name):
    full_name = f"{team_city} {team_name}"
    return full_name.lower().replace(" ", "-").replace(".", "").replace("'", "")

def update_player_database():
    print("Mise à jour de la base de données joueurs via NBA API...")
    try:
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
    try:
        info = commonplayerinfo.CommonPlayerInfo(player_id=player_id)
        data = info.get_dict()['resultSets'][0]
        headers = data['headers']
        row = data['rowSet'][0]
        
        def get_val(key):
            return row[headers.index(key)] if key in headers else "N/A"

        birthdate_str = get_val('BIRTHDATE')
        age = "N/A"
        if birthdate_str and "T" in birthdate_str:
            b_date = datetime.strptime(birthdate_str.split('T')[0], "%Y-%m-%d")
            today = datetime.today()
            age = today.year - b_date.year - ((today.month, today.day) < (b_date.month, b_date.day))

        team_city = get_val('TEAM_CITY')
        team_name = get_val('TEAM_NAME')
        player_name = get_val('DISPLAY_FIRST_LAST')
        team_slug = generate_team_slug(team_city, team_name)
        
        if player_name in MANUAL_OVERRIDES:
            team_slug = MANUAL_OVERRIDES[player_name]
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

def clean_text_snippet(text):
    """Nettoie un extrait de texte brut."""
    # Supprime les balises HTML résiduelles
    text = re.sub(r'<[^>]+>', ' ', text)
    # Supprime les caractères spéciaux JSON/JS
    text = text.replace('"', '').replace('\\', '').replace('{', '').replace('}', '')
    # Normalise les espaces
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:400]

def scrape_nbc_team_page(team_slug, player_name):
    if not team_slug: return "Équipe inconnue"
    
    url = f"https://www.nbcsports.com/nba/{team_slug}/injuries"
    
    try:
        # Utilisation d'une session pour gérer les cookies basiques
        session = requests.Session()
        response = session.get(url, headers=HEADERS, timeout=10)
        
        # Si 404 sur /injuries, tenter la page d'équipe principale
        if response.status_code == 404:
             url = f"https://www.nbcsports.com/nba/{team_slug}"
             response = session.get(url, headers=HEADERS, timeout=10)

        if response.status_code != 200:
            return f"Erreur d'accès NBC ({response.status_code})"

        soup = BeautifulSoup(response.content, 'html.parser')
        lastname = player_name.split()[-1]
        norm_lastname = normalize_text(lastname)

        # STRATÉGIE 1 : Extraction de texte pur (Bulldozer)
        # On convertit tout le HTML en texte brut. Si l'info est visible, elle est là.
        full_text = soup.get_text(separator=' ', strip=True)
        
        # On cherche la position du nom dans ce texte géant
        # On utilise une regex simple pour trouver le nom suivi de mots (insensible à la casse)
        # On capture ~300 caractères après le nom
        match = re.search(rf"{re.escape(lastname)}\s+(.{{10,350}})", full_text, re.IGNORECASE)
        
        if match:
            snippet = match.group(1)
            # Vérification de pertinence (Mots clés blessure/status)
            keywords = ['injury', 'out', 'status', 'surgery', 'strain', 'questionable', 'doubtful', 'probable', 'available', 'sidelined', 'return', 'miss', 'day-to-day']
            
            if any(k in snippet.lower() for k in keywords):
                return clean_text_snippet(snippet) + "..."

        # STRATÉGIE 2 : Recherche dans les Scripts JSON (Données cachées)
        # Souvent les données sont dans <script id="__NEXT_DATA__"> ou similaire
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string and lastname in script.string:
                # On a trouvé le nom dans un script. On essaie d'extraire le contexte.
                # C'est du "Sale" regex sur du code JS/JSON, mais c'est efficace quand le parsing échoue.
                match_script = re.search(rf"{re.escape(lastname)}.*?(.{{10,300}})", script.string, re.IGNORECASE)
                if match_script:
                    raw = match_script.group(1)
                    # Nettoyage agressif car c'est du code
                    if "injury" in raw.lower() or "status" in raw.lower():
                         return f"Info (Script): {clean_text_snippet(raw)}"

        return f"Rien à signaler sur la page {team_slug}."

    except Exception as e:
        return f"Erreur NBC: {e}"

def scrape_rotowire(player_name):
    try:
        url = "https://www.rotowire.com/basketball/injury-report.php"
        # Rotowire bloque parfois si pas de User-Agent
        res = requests.get(url, headers=HEADERS, timeout=6)
        soup = BeautifulSoup(res.content, 'html.parser')
        links = soup.find_all('a', href=True)
        norm_name = normalize_text(player_name)
        for link in links:
            if "player" in link['href'] and norm_name in normalize_text(link.text):
                row = link.find_parent('div', class_='injury-report__row')
                if row:
                    inj = row.find(class_='injury-report__injury')
                    status = row.find(class_='injury-report__status')
                    ret = row.find(class_='injury-report__return')
                    res_text = f"{status.text.strip()} - {inj.text.strip()}"
                    if ret:
                         res_text += f" (Retour: {ret.text.strip()})"
                    return res_text
        return None
    except:
        return None

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
    player_data = PLAYER_CACHE.get(player)
    if not player_data:
        for name, data in PLAYER_CACHE.items():
            if normalize_text(player) in normalize_text(name):
                player_data = data
                player = name 
                break
    
    if not player_data:
        return {"error": "Joueur introuvable"}

    details = get_player_details(player_data['id'])
    
    # NBC Scraping
    nbc_info = scrape_nbc_team_page(details['team_slug'], player)
    
    # Rotowire Scraping
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
