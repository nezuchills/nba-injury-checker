import os
import json
import requests
import unicodedata
import re
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from bs4 import BeautifulSoup
from nba_api.stats.endpoints import commonallplayers

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

def normalize_text(text):
    if not text: return ""
    return ''.join(c for c in unicodedata.normalize('NFD', str(text)) if unicodedata.category(c) != 'Mn').lower().strip()

def generate_team_slug(team_city, team_name):
    full_name = f"{team_city} {team_name}"
    return full_name.lower().replace(" ", "-").replace(".", "")

def update_player_database():
    print("Mise à jour de la base de données joueurs via NBA API...")
    try:
        nba_response = commonallplayers.CommonAllPlayers(is_only_current_season=1)
        data = nba_response.get_dict()
        headers = data['resultSets'][0]['headers']
        rows = data['resultSets'][0]['rowSet']
        
        players_dict = {}
        idx_name = headers.index('DISPLAY_FIRST_LAST')
        idx_city = headers.index('TEAM_CITY')
        idx_team_name = headers.index('TEAM_NAME')
        idx_team_id = headers.index('TEAM_ID')
        
        for row in rows:
            name = row[idx_name]
            team_id = row[idx_team_id]
            if team_id != 0:
                slug = generate_team_slug(row[idx_city], row[idx_team_name])
                players_dict[name] = {
                    "name": name,
                    "team_slug": slug,
                    "team_city": row[idx_city],
                    "team_name": row[idx_team_name]
                }
        
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

def clean_regex_result(text):
    text = re.sub(r'<[^>]+>', '', text)
    text = text.replace('"', '').replace('{', '').replace('}', '').replace('\\', '')
    # Nettoyer les sauts de ligne multiples
    text = re.sub(r'\s+', ' ', text).strip()
    end = text.find('.')
    # Prendre un peu plus de contexte si possible (2 phrases)
    if end != -1:
        next_end = text.find('.', end + 1)
        if next_end != -1 and next_end < 300:
            text = text[:next_end+1]
        else:
            text = text[:end+1]
    return text[:300]

# --- LOGIQUE DE SCRAPING AMÉLIORÉE ---

def scrape_nbc_player_profile(player_name):
    """
    Scrape la page individuelle du joueur (ex: /nba/player/damian-lillard)
    Utile pour récupérer la 'Meta Description' qui contient souvent la dernière news.
    """
    # Générer le slug joueur : "Damian Lillard" -> "damian-lillard"
    player_slug = normalize_text(player_name).replace(" ", "-")
    url = f"https://www.nbcsports.com/nba/player/{player_slug}"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=8)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 1. Chercher la balise Meta Description (Souvent le résumé de la dernière news)
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc:
                content = meta_desc.get('content', '').strip()
                # Filtrer les descriptions par défaut génériques
                if content and "Latest news, stats" not in content and len(content) > 50:
                    return f"{content}"

            # 2. Chercher dans le JSON-LD (Données structurées)
            scripts = soup.find_all('script', type='application/ld+json')
            for script in scripts:
                if "description" in script.text:
                    try:
                        data = json.loads(script.text)
                        if 'description' in data:
                            return data['description']
                    except:
                        pass
    except:
        pass
    return None

def scrape_nbc_data(player_name):
    player_info = None
    normalized_input = normalize_text(player_name)
    
    if player_name in PLAYER_CACHE:
        player_info = PLAYER_CACHE[player_name]
    else:
        for db_name, info in PLAYER_CACHE.items():
            if normalized_input in normalize_text(db_name):
                player_info = info
                break
    
    if not player_info:
        return "Joueur introuvable dans la base NBA."
        
    # TENTATIVE 1 : Page Équipe (Injuries)
    team_slug = player_info['team_slug']
    url = f"https://www.nbcsports.com/nba/{team_slug}/injuries"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        target_lastname = normalize_text(player_info['name'].split()[-1])

        # A. DOM Parsing
        injury_rows = soup.find_all("div", class_=lambda x: x and "sr-us-injuries-line__wrapper" in x)
        if injury_rows:
            for row in injury_rows:
                name_div = row.find("div", class_=lambda x: x and "sr-us-injuries-line__player-name" in x)
                if name_div and target_lastname in normalize_text(name_div.get_text(strip=True)):
                    injury_div = row.find("div", class_=lambda x: x and "sr-us-injuries-line__injury" in x)
                    comment_div = row.find("div", class_=lambda x: x and "sr-us-injuries-line__comment" in x)
                    inj = injury_div.get_text(strip=True) if injury_div else "Info"
                    com = comment_div.get_text(strip=True) if comment_div else ""
                    return f"{inj}: {com}"

        # B. Fallback Regex sur Page Équipe (Nom de famille uniquement)
        # On cherche "Lillard" suivi de texte, au cas où "Damian" n'est pas écrit
        page_source = response.text
        # Regex : Lastname + caractères arbitraires + mots clés de blessure potentiels dans les 300 caractères
        # On évite d'être trop restrictif sur les mots clés pour attraper les textes libres
        match = re.search(rf"{re.escape(player_info['name'].split()[-1])}.*?(.{{10,300}})", page_source, re.IGNORECASE | re.DOTALL)
        
        if match:
            raw_fragment = match.group(1)
            # Vérification simple pour éviter de capturer du code JS
            if "{" not in raw_fragment[:50]: 
                cleaned = clean_regex_result(raw_fragment)
                # Si le texte semble pertinent (contient des mots clés ou une date)
                if any(x in cleaned.lower() for x in ['injury', 'out', 'status', 'back', 'season', 'game', 'day']):
                     return f"Info Équipe (Raw): {cleaned}"

        # TENTATIVE 2 : Page Profil Joueur (Fallback ultime)
        # Si rien sur la page équipe, on checke la page du joueur
        profile_info = scrape_nbc_player_profile(player_info['name'])
        if profile_info:
            return f"Profil NBC: {profile_info}"
        
        # TENTATIVE 3 : Backup Rotowire
        backup = scrape_rotowire_injuries(player_name)
        if backup:
            return f"Via Rotowire: {backup}"

        return f"Aucune info active trouvée pour {player_info['name']}."

    except Exception as e:
        print(f"Erreur NBC: {e}")
        return "Erreur technique scraping."

def scrape_cbs_injuries(player_name):
    url = "https://www.cbssports.com/nba/injuries/"
    try:
        response = requests.get(url, headers=HEADERS, timeout=5)
        soup = BeautifulSoup(response.content, 'html.parser')
        rows = soup.find_all('tr')
        normalized_target = normalize_text(player_name)
        for row in rows:
            cols = row.find_all('td')
            if len(cols) >= 2:
                name_col = cols[0].get_text()
                if normalized_target in normalize_text(name_col):
                    status = cols[-1].get_text(strip=True)
                    injury = cols[-2].get_text(strip=True)
                    return f"{status} - {injury}"
        return None
    except:
        return None

def scrape_rotowire_injuries(player_name):
    url = "https://www.rotowire.com/basketball/injury-report.php"
    try:
        response = requests.get(url, headers=HEADERS, timeout=6)
        soup = BeautifulSoup(response.content, 'html.parser')
        normalized_target = normalize_text(player_name)
        links = soup.find_all('a', href=True)
        for link in links:
            if "player" in link['href'] and normalized_target in normalize_text(link.get_text()):
                row = link.find_parent('div', class_='injury-report__row')
                if not row: row = link.find_parent('tr')
                if row:
                    injury_div = row.find(class_='injury-report__injury')
                    status_div = row.find(class_='injury-report__status')
                    inj = injury_div.get_text(strip=True) if injury_div else "Unknown"
                    stat = status_div.get_text(strip=True) if status_div else ""
                    return f"{stat} - {inj}"
        return None
    except:
        return None

@app.on_event("startup")
def startup_event():
    load_player_database()

@app.get("/")
def home():
    return f"API NBA Ready (FastAPI). {len(PLAYER_CACHE)} joueurs en DB."

@app.get("/api/players")
def get_all_players():
    return list(PLAYER_CACHE.keys())

@app.get("/api/check")
def check_injury(player: str = Query(..., min_length=1)):
    nbc = scrape_nbc_data(player)
    cbs = scrape_cbs_injuries(player)
    rotowire = scrape_rotowire_injuries(player)
    
    return {
        "player": player,
        "sources": {
            "NBC": nbc,
            "CBS": cbs if cbs else "Healthy",
            "Rotowire": rotowire if rotowire else "Healthy"
        }
    }

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    uvicorn.run(app, host='0.0.0.0', port=port)
