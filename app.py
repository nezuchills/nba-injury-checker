import os
import json
import requests
import unicodedata
import re
from datetime import datetime
from fastapi import FastAPI, Query
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
    'Accept-Language': 'en-US,en;q=0.9',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Cache-Control': 'max-age=0',
}

JSON_FILE = 'nba_players.json'
PLAYER_CACHE = {}

def normalize_text(text):
    if not text: return ""
    return ''.join(c for c in unicodedata.normalize('NFD', str(text)) if unicodedata.category(c) != 'Mn').lower().strip()

def generate_team_slug(team_city, team_name):
    full_name = f"{team_city} {team_name}"
    return full_name.lower().replace(" ", "-").replace(".", "").replace("'", "")

def update_player_database():
    print("Mise à jour de la base de données via NBA API...")
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
        print(f"Erreur NBA API: {e}")
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
        
        def get_val(key): return row[headers.index(key)] if key in headers else "N/A"

        birthdate_str = get_val('BIRTHDATE')
        age = "N/A"
        if birthdate_str and "T" in birthdate_str:
            b_date = datetime.strptime(birthdate_str.split('T')[0], "%Y-%m-%d")
            today = datetime.today()
            age = today.year - b_date.year - ((today.month, today.day) < (b_date.month, b_date.day))

        team_city = get_val('TEAM_CITY')
        team_name = get_val('TEAM_NAME')
        team_slug = generate_team_slug(team_city, team_name)

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
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:300]

# --- 1. NBC SPORTS ---
def scrape_nbc(team_slug, player_name):
    if not team_slug: return "Équipe inconnue"
    # URL stricte demandée
    url = f"https://www.nbcsports.com/nba/{team_slug}/injuries"
    
    try:
        session = requests.Session()
        response = session.get(url, headers=HEADERS, timeout=8)

        if response.status_code != 200: return "Erreur accès NBC"

        soup = BeautifulSoup(response.content, 'html.parser')
        lastname = player_name.split()[-1]
        full_text = soup.get_text(separator=' ', strip=True)
        
        match = re.search(rf"{re.escape(lastname)}\s+(.{{10,350}})", full_text, re.IGNORECASE)
        
        if match:
            snippet = clean_text_snippet(match.group(1))
            keywords = ['injury', 'out', 'status', 'surgery', 'strain', 'questionable', 'doubtful', 'probable', 'available', 'sidelined', 'return', 'miss', 'day-to-day', 'game']
            if any(k in snippet.lower() for k in keywords):
                return snippet + "..."
        
        return "Rien à signaler"
    except Exception as e:
        return f"Erreur: {str(e)}"

# --- 2. ESPN ---
def scrape_espn(player_name):
    # URL stricte demandée
    url = "https://www.espn.com/nba/injuries"
    try:
        response = requests.get(url, headers=HEADERS, timeout=6)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        norm_name = normalize_text(player_name)
        links = soup.find_all('a', href=True)
        
        for link in links:
            if "player" in link['href'] and norm_name in normalize_text(link.text):
                row = link.find_parent('tr')
                if row:
                    cols = row.find_all('td')
                    if len(cols) >= 2:
                        status = cols[1].get_text(strip=True)
                        comment = cols[3].get_text(strip=True) if len(cols) > 3 else ""
                        return f"{status}: {comment}"
        return "Rien à signaler"
    except:
        return "Erreur d'accès"

# --- 3. CBS SPORTS ---
def scrape_cbs(player_name):
    # URL stricte demandée
    url = "https://www.cbssports.com/nba/injuries/"
    try:
        response = requests.get(url, headers=HEADERS, timeout=6)
        soup = BeautifulSoup(response.content, 'html.parser')
        rows = soup.find_all('tr')
        norm_name = normalize_text(player_name)
        
        for row in rows:
            cols = row.find_all('td')
            if len(cols) >= 2:
                name_col = cols[0].get_text()
                if norm_name in normalize_text(name_col):
                    status = cols[-1].get_text(strip=True)
                    injury = cols[-2].get_text(strip=True)
                    return f"{status} - {injury}"
        return "Rien à signaler"
    except:
        return "Erreur d'accès"

@app.on_event("startup")
def startup_event():
    load_player_database()

@app.get("/api/players")
def get_players():
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
    
    return {
        "player": player,
        "meta": {
            "age": details['age'],
            "team": details['team_name'],
            "position": details['position'],
            "jersey": details['jersey']
        },
        "sources": {
            "NBC": scrape_nbc(details['team_slug'], player),
            "ESPN": scrape_espn(player),
            "CBS": scrape_cbs(player)
        }
    }

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    uvicorn.run(app, host='0.0.0.0', port=port)
