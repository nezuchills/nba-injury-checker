import os
import requests
import unicodedata
import re
from flask import Flask, request, jsonify
from flask_cors import CORS
from bs4 import BeautifulSoup

app = Flask(__name__)
CORS(app)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Referer': 'https://www.nbcsports.com/'
}

# --- MAPPING JOUEUR -> EQUIPE (Nécessaire pour NBC) ---
# NBC classe les blessures par URL d'équipe.
# Format slug: 'portland-trail-blazers', 'los-angeles-lakers', etc.
PLAYER_TEAMS = {
    "Blake Wesley": "san-antonio-spurs", # Note: Il est chez les Spurs en réalité, mais pour l'exemple je vais checker l'URL que vous avez donnée si c'était Portland
    "LeBron James": "los-angeles-lakers",
    "Anthony Davis": "los-angeles-lakers",
    "Stephen Curry": "golden-state-warriors",
    "Kevin Durant": "phoenix-suns",
    "Devin Booker": "phoenix-suns",
    "Nikola Jokic": "denver-nuggets",
    "Jamal Murray": "denver-nuggets",
    "Giannis Antetokounmpo": "milwaukee-bucks",
    "Damian Lillard": "milwaukee-bucks",
    "Luka Doncic": "dallas-mavericks",
    "Kyrie Irving": "dallas-mavericks",
    "Jayson Tatum": "boston-celtics",
    "Jaylen Brown": "boston-celtics",
    "Joel Embiid": "philadelphia-76ers",
    "Tyrese Maxey": "philadelphia-76ers",
    "Shai Gilgeous-Alexander": "oklahoma-city-thunder",
    "Chet Holmgren": "oklahoma-city-thunder",
    "Victor Wembanyama": "san-antonio-spurs",
    "Ja Morant": "memphis-grizzlies",
    "Desmond Bane": "memphis-grizzlies",
    "Zion Williamson": "new-orleans-pelicans",
    "Jimmy Butler": "miami-heat",
    "Bam Adebayo": "miami-heat",
    "Donovan Mitchell": "cleveland-cavaliers",
    "Kawhi Leonard": "los-angeles-clippers",
    "Paul George": "los-angeles-clippers",
    "James Harden": "los-angeles-clippers",
    "LaMelo Ball": "charlotte-hornets",
    "Anthony Edwards": "minnesota-timberwolves",
    "Karl-Anthony Towns": "minnesota-timberwolves",
    "De'Aaron Fox": "sacramento-kings",
    "Domantas Sabonis": "sacramento-kings",
    "Jalen Brunson": "new-york-knicks",
    "Julius Randle": "new-york-knicks",
    "Tyrese Haliburton": "indiana-pacers",
    "Pascal Siakam": "indiana-pacers",
    "Trae Young": "atlanta-hawks",
    "Scottie Barnes": "toronto-raptors",
    "Cade Cunningham": "detroit-pistons",
    "Fred VanVleet": "houston-rockets",
    "Alperen Sengun": "houston-rockets",
    "Lauri Markkanen": "utah-jazz",
    "Deandre Ayton": "portland-trail-blazers",
    "Anfernee Simons": "portland-trail-blazers",
    "Scoot Henderson": "portland-trail-blazers",
    "Shaedon Sharpe": "portland-trail-blazers",
    "Jerami Grant": "portland-trail-blazers",
    "Robert Williams III": "portland-trail-blazers"
}

# Liste pour l'autocomplétion (identique à avant pour le frontend)
ALL_PLAYERS = list(PLAYER_TEAMS.keys()) # Pour l'instant on utilise les clés, mais gardez votre grande liste ALL_PLAYERS ici en prod.

def normalize_text(text):
    if not text: return ""
    return ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn').lower().strip()

def scrape_nbc_data(player_name):
    """
    Scrape la page d'équipe NBC Sports en utilisant la structure HTML spécifique fournie.
    Target URL: https://www.nbcsports.com/nba/{team-slug}/injuries
    Structure: div.sr-us-injuries-line__wrapper
    """
    
    # 1. Trouver l'équipe du joueur
    # Fallback: si on ne connait pas l'équipe, on ne peut pas deviner l'URL NBC
    # Pour "Blake Wesley", il est listé aux Spurs, mais si vous testez Portland, ajustez le dictionnaire.
    team_slug = PLAYER_TEAMS.get(player_name)
    
    # Petite logique floue si le nom exact n'est pas dans les clés
    if not team_slug:
        for name, slug in PLAYER_TEAMS.items():
            if normalize_text(player_name) in normalize_text(name):
                team_slug = slug
                break
    
    if not team_slug:
        return "Équipe inconnue pour ce joueur (Mise à jour DB nécessaire pour NBC)"

    url = f"https://www.nbcsports.com/nba/{team_slug}/injuries"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        
        if response.status_code != 200:
            return f"Erreur accès page équipe ({response.status_code})"

        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 2. Parsing basé sur votre OuterHTML
        # On cherche tous les wrappers de ligne de blessure
        # La classe exacte fournie: "sr-us-injuries-line__wrapper"
        injury_rows = soup.find_all("div", class_=lambda x: x and "sr-us-injuries-line__wrapper" in x)
        
        normalized_target = normalize_text(player_name)
        
        if not injury_rows:
            # Si requests ne voit pas le HTML (car généré par JS), on aura 0 rows.
            # C'est souvent le cas avec les widgets "sr-" (Sportradar).
            return "Données non chargées (Widget JS détecté). Essayez Rotowire."

        for row in injury_rows:
            # Chercher le nom du joueur dans cette ligne
            name_div = row.find("div", class_=lambda x: x and "sr-us-injuries-line__player-name" in x)
            
            if name_div:
                row_name = normalize_text(name_div.get_text(strip=True))
                
                # Comparaison
                if normalized_target in row_name:
                    # On a trouvé le joueur ! Récupérons les détails.
                    
                    # Injury Type
                    injury_div = row.find("div", class_=lambda x: x and "sr-us-injuries-line__injury" in x)
                    injury_text = injury_div.get_text(strip=True) if injury_div else "Blessure inconnue"
                    
                    # Commentaire complet
                    comment_div = row.find("div", class_=lambda x: x and "sr-us-injuries-line__comment" in x)
                    comment_text = comment_div.get_text(strip=True) if comment_div else ""
                    
                    return f"{injury_text}: {comment_text}"
        
        return "Aucune blessure signalée sur la page de l'équipe (Healthy ?)"

    except Exception as e:
        print(f"Erreur NBC: {e}")
        return "Erreur technique scraping NBC"

# --- GARDER LES AUTRES SCRAPERS (CBS/Rotowire) COMME DEMANDÉ ---

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
    return "API NBA Ready"

@app.route('/api/players', methods=['GET'])
def get_all_players():
    # Renvoie la liste pour l'autocomplétion du frontend
    return jsonify(ALL_PLAYERS)

@app.route('/api/check', methods=['GET'])
def check_injury():
    player_name = request.args.get('player')
    if not player_name:
        return jsonify({"error": "Nom manquant"}), 400
        
    # Priorité NBC (nouvelle logique)
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
