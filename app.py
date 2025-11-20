import os
import json
import requests
import unicodedata
import re
from flask import Flask, request, jsonify
from flask_cors import CORS
from bs4 import BeautifulSoup

# Importation de l'API NBA
from nba_api.stats.endpoints import commonallplayers

app = Flask(__name__)
CORS(app)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Referer': 'https://www.nbcsports.com/'
}

JSON_FILE = 'nba_players.json'
PLAYER_CACHE = {}

def normalize_text(text):
    """Nettoyage de texte standard"""
    if not text: return ""
    return ''.join(c for c in unicodedata.normalize('NFD', str(text)) if unicodedata.category(c) != 'Mn').lower().strip()

def generate_team_slug(team_city, team_name):
    """
    Transforme 'Portland', 'Trail Blazers' en 'portland-trail-blazers'
    pour l'URL NBC Sports.
    """
    full_name = f"{team_city} {team_name}"
    return full_name.lower().replace(" ", "-").replace(".", "")

def update_player_database():
    """
    Utilise l'API NBA pour récupérer tous les joueurs actifs et leurs équipes.
    Sauvegarde le résultat dans un fichier JSON.
    """
    print("Mise à jour de la base de données joueurs via NBA API...")
    try:
        # Récupère tous les joueurs de la saison en cours (IsOnlyCurrentSeason=1)
        nba_response = commonallplayers.CommonAllPlayers(is_only_current_season=1)
        data = nba_response.get_dict()
        
        # Parsing de la réponse (Headers: PERSON_ID, DISPLAY_LAST_COMMA_FIRST, ..., TEAM_CITY, TEAM_NAME, ...)
        headers = data['resultSets'][0]['headers']
        rows = data['resultSets'][0]['rowSet']
        
        players_dict = {}
        
        # Index des colonnes
        idx_name = headers.index('DISPLAY_FIRST_LAST')
        idx_city = headers.index('TEAM_CITY')
        idx_team_name = headers.index('TEAM_NAME')
        idx_team_id = headers.index('TEAM_ID')
        
        for row in rows:
            name = row[idx_name]
            team_city = row[idx_city]
            team_name = row[idx_team_name]
            team_id = row[idx_team_id]
            
            # On ne garde que les joueurs associés à une équipe (TEAM_ID != 0)
            if team_id != 0:
                slug = generate_team_slug(team_city, team_name)
                # Clé normalisée pour la recherche facile
                players_dict[name] = {
                    "name": name,
                    "team_slug": slug,
                    "team_city": team_city,
                    "team_name": team_name
                }
        
        # Sauvegarde JSON
        with open(JSON_FILE, 'w') as f:
            json.dump(players_dict, f)
            
        print(f"Base de données mise à jour : {len(players_dict)} joueurs actifs.")
        return players_dict

    except Exception as e:
        print(f"Erreur lors de la mise à jour NBA API: {e}")
        return {}

def load_player_database():
    """Charge le JSON en mémoire, ou le crée s'il n'existe pas."""
    global PLAYER_CACHE
    
    if os.path.exists(JSON_FILE):
        with open(JSON_FILE, 'r') as f:
            PLAYER_CACHE = json.load(f)
    else:
        PLAYER_CACHE = update_player_database()

# Chargement au démarrage de l'application
with app.app_context():
    load_player_database()

# --- LOGIQUE SCRAPING ---

def scrape_nbc_data(player_name):
    """
    1. Trouve l'équipe du joueur dans le cache JSON.
    2. Construit l'URL : nbcsports.com/nba/{team-slug}/injuries
    3. Scrape avec la structure HTML fournie par l'utilisateur.
    """
    
    # 1. Recherche du joueur dans le cache (recherche approximative)
    player_info = None
    normalized_input = normalize_text(player_name)
    
    # Recherche exacte d'abord
    if player_name in PLAYER_CACHE:
        player_info = PLAYER_CACHE[player_name]
    else:
        # Recherche partielle
        for db_name, info in PLAYER_CACHE.items():
            if normalized_input in normalize_text(db_name):
                player_info = info
                break
    
    if not player_info:
        return "Joueur introuvable dans la base NBA actuelle."
        
    team_slug = player_info['team_slug']
    url = f"https://www.nbcsports.com/nba/{team_slug}/injuries"
    
    try:
        print(f"Scraping NBC pour {player_info['name']} sur {url}")
        response = requests.get(url, headers=HEADERS, timeout=10)
        
        if response.status_code != 200:
            return f"Erreur page équipe NBC ({response.status_code})"

        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 2. Parsing basé sur votre structure HTML précise
        # Classe parente : sr-us-injuries-line__wrapper
        injury_rows = soup.find_all("div", class_=lambda x: x and "sr-us-injuries-line__wrapper" in x)
        
        if not injury_rows:
            return "Aucune donnée chargée (Widget JS potentiellement bloqué par Render/Cloudflare)."

        target_name_norm = normalize_text(player_info['name'])
        # Parfois NBA API dit "Nicolas Batum" et NBC "Nic Batum", on checke le nom de famille
        target_lastname = target_name_norm.split()[-1] if " " in target_name_norm else target_name_norm

        for row in injury_rows:
            # Nom du joueur dans la ligne
            name_div = row.find("div", class_=lambda x: x and "sr-us-injuries-line__player-name" in x)
            
            if name_div:
                row_name = normalize_text(name_div.get_text(strip=True))
                
                # Vérification : Est-ce notre joueur ?
                if target_lastname in row_name:
                    
                    # Type de blessure
                    injury_div = row.find("div", class_=lambda x: x and "sr-us-injuries-line__injury" in x)
                    injury_text = injury_div.get_text(strip=True) if injury_div else "Blessure"
                    
                    # Commentaire complet
                    comment_div = row.find("div", class_=lambda x: x and "sr-us-injuries-line__comment" in x)
                    comment_text = comment_div.get_text(strip=True) if comment_div else "Pas de détails."
                    
                    return f"{injury_text}: {comment_text}"
        
        return f"Joueur sain (Pas sur la liste des blessés de {player_info['team_name']})."

    except Exception as e:
        print(f"Erreur NBC: {e}")
        return "Erreur technique lors du scraping."

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
                    injury = injury_div.get_text(strip=True) if injury_div else "Unknown"
                    status = status_div.get_text(strip=True) if status_div else ""
                    return f"{status} - {injury}"
        return None
    except:
        return None

# --- ROUTES ---

@app.route('/')
def home():
    count = len(PLAYER_CACHE)
    return f"API NBA Ready. {count} joueurs en base de données (JSON)."

@app.route('/api/refresh-db')
def refresh_db():
    """Route manuelle pour forcer la mise à jour depuis NBA API"""
    global PLAYER_CACHE
    PLAYER_CACHE = update_player_database()
    return jsonify({"status": "success", "count": len(PLAYER_CACHE)})

@app.route('/api/players', methods=['GET'])
def get_all_players():
    # Retourne la liste des noms pour l'autocomplétion
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
            "CBS": cbs if cbs else "Healthy / Pas sur la liste",
            "Rotowire": rotowire if rotowire else "Pas sur la liste"
        }
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
