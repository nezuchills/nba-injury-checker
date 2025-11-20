import os
import json
import requests
import unicodedata
import re
from flask import Flask, request, jsonify
from flask_cors import CORS
from bs4 import BeautifulSoup
from nba_api.stats.endpoints import commonallplayers

app = Flask(__name__)
CORS(app)

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

with app.app_context():
    load_player_database()

def clean_regex_result(text):
    """Nettoie les artefacts JSON/HTML du texte extrait brut."""
    # Enlève les balises HTML
    text = re.sub(r'<[^>]+>', '', text)
    # Enlève les caractères JSON courants
    text = text.replace('"', '').replace('{', '').replace('}', '').replace('\\', '')
    # Trouve la fin de phrase probable
    end = text.find('.')
    if end != -1:
        text = text[:end+1]
    return text[:200] + "..."

def scrape_nbc_data(player_name):
    # 1. Identification joueur
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
        
    team_slug = player_info['team_slug']
    url = f"https://www.nbcsports.com/nba/{team_slug}/injuries"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # --- MÉTHODE 1 : DOM Parsing (Si le HTML est rendu) ---
        injury_rows = soup.find_all("div", class_=lambda x: x and "sr-us-injuries-line__wrapper" in x)
        
        target_lastname = normalize_text(player_info['name'].split()[-1])

        if injury_rows:
            for row in injury_rows:
                name_div = row.find("div", class_=lambda x: x and "sr-us-injuries-line__player-name" in x)
                if name_div and target_lastname in normalize_text(name_div.get_text(strip=True)):
                    injury_div = row.find("div", class_=lambda x: x and "sr-us-injuries-line__injury" in x)
                    comment_div = row.find("div", class_=lambda x: x and "sr-us-injuries-line__comment" in x)
                    
                    inj = injury_div.get_text(strip=True) if injury_div else "News"
                    com = comment_div.get_text(strip=True) if comment_div else ""
                    return f"{inj}: {com}"

        # --- MÉTHODE 2 : Fallback Regex sur le texte brut (Si Widget JS) ---
        # On cherche le nom du joueur dans le code source de la page (souvent dans une balise <script> JSON)
        page_source = response.text
        
        # Pattern: Nom du joueur ... (quelques caractères) ... texte de la blessure
        # On cherche le nom du joueur (case insensitive)
        # On capture les 300 caractères qui suivent
        match = re.search(rf"{re.escape(player_info['name'])}.*?(.{{10,300}})", page_source, re.IGNORECASE | re.DOTALL)
        
        if match:
            raw_fragment = match.group(1)
            # Si on trouve des mots clés de blessure dans le fragment
            if "injury" in raw_fragment.lower() or "out" in raw_fragment.lower() or "status" in raw_fragment.lower() or "metatarsal" in raw_fragment.lower():
                cleaned = clean_regex_result(raw_fragment)
                return f"Info détectée (Raw): {cleaned}"
        
        # Si on ne trouve rien sur la page d'équipe, on checke Rotowire comme backup invisible pour NBC
        # car NBC utilise souvent les mêmes sources
        backup = scrape_rotowire_injuries(player_name)
        if backup:
            return f"Via Rotowire (NBC Sync): {backup}"

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

@app.route('/')
def home():
    count = len(PLAYER_CACHE)
    return f"API NBA Ready. {count} joueurs en DB."

@app.route('/api/players', methods=['GET'])
def get_all_players():
    return jsonify(list(PLAYER_CACHE.keys()))

@app.route('/api/check', methods=['GET'])
def check_injury():
    player_name = request.args.get('player')
    if not player_name:
        return jsonify({"error": "Nom manquant"}), 400
        
    nbc = scrape_nbc_data(player_name)
    cbs = scrape_cbs_injuries(player_name)
    rotowire = scrape_rotowire_injuries(player_name)
    
    return jsonify({
        "player": player_name,
        "sources": {
            "NBC": nbc,
            "CBS": cbs if cbs else "Healthy",
            "Rotowire": rotowire if rotowire else "Healthy"
        }
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
