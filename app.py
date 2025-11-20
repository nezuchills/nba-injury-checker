from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import re

app = Flask(__name__)
CORS(app)

# Liste des joueurs NBA avec leurs équipes
NBA_PLAYERS = [
    # Atlanta Hawks
    {"name": "Trae Young", "team": "Atlanta Hawks", "abbr": "ATL"},
    {"name": "Dejounte Murray", "team": "Atlanta Hawks", "abbr": "ATL"},
    {"name": "Clint Capela", "team": "Atlanta Hawks", "abbr": "ATL"},
    {"name": "Bogdan Bogdanovic", "team": "Atlanta Hawks", "abbr": "ATL"},
    {"name": "De'Andre Hunter", "team": "Atlanta Hawks", "abbr": "ATL"},
    
    # Boston Celtics
    {"name": "Jayson Tatum", "team": "Boston Celtics", "abbr": "BOS"},
    {"name": "Jaylen Brown", "team": "Boston Celtics", "abbr": "BOS"},
    {"name": "Kristaps Porzingis", "team": "Boston Celtics", "abbr": "BOS"},
    {"name": "Jrue Holiday", "team": "Boston Celtics", "abbr": "BOS"},
    {"name": "Derrick White", "team": "Boston Celtics", "abbr": "BOS"},
    
    # Brooklyn Nets
    {"name": "Mikal Bridges", "team": "Brooklyn Nets", "abbr": "BKN"},
    {"name": "Cam Thomas", "team": "Brooklyn Nets", "abbr": "BKN"},
    {"name": "Nicolas Claxton", "team": "Brooklyn Nets", "abbr": "BKN"},
    {"name": "Ben Simmons", "team": "Brooklyn Nets", "abbr": "BKN"},
    
    # Charlotte Hornets
    {"name": "LaMelo Ball", "team": "Charlotte Hornets", "abbr": "CHA"},
    {"name": "Brandon Miller", "team": "Charlotte Hornets", "abbr": "CHA"},
    {"name": "Miles Bridges", "team": "Charlotte Hornets", "abbr": "CHA"},
    {"name": "Mark Williams", "team": "Charlotte Hornets", "abbr": "CHA"},
    
    # Chicago Bulls
    {"name": "Zach LaVine", "team": "Chicago Bulls", "abbr": "CHI"},
    {"name": "DeMar DeRozan", "team": "Chicago Bulls", "abbr": "CHI"},
    {"name": "Nikola Vucevic", "team": "Chicago Bulls", "abbr": "CHI"},
    {"name": "Coby White", "team": "Chicago Bulls", "abbr": "CHI"},
    
    # Cleveland Cavaliers
    {"name": "Donovan Mitchell", "team": "Cleveland Cavaliers", "abbr": "CLE"},
    {"name": "Darius Garland", "team": "Cleveland Cavaliers", "abbr": "CLE"},
    {"name": "Evan Mobley", "team": "Cleveland Cavaliers", "abbr": "CLE"},
    {"name": "Jarrett Allen", "team": "Cleveland Cavaliers", "abbr": "CLE"},
    
    # Dallas Mavericks
    {"name": "Luka Doncic", "team": "Dallas Mavericks", "abbr": "DAL"},
    {"name": "Kyrie Irving", "team": "Dallas Mavericks", "abbr": "DAL"},
    {"name": "Dereck Lively II", "team": "Dallas Mavericks", "abbr": "DAL"},
    
    # Denver Nuggets
    {"name": "Nikola Jokic", "team": "Denver Nuggets", "abbr": "DEN"},
    {"name": "Jamal Murray", "team": "Denver Nuggets", "abbr": "DEN"},
    {"name": "Michael Porter Jr.", "team": "Denver Nuggets", "abbr": "DEN"},
    {"name": "Aaron Gordon", "team": "Denver Nuggets", "abbr": "DEN"},
    
    # Detroit Pistons
    {"name": "Cade Cunningham", "team": "Detroit Pistons", "abbr": "DET"},
    {"name": "Jaden Ivey", "team": "Detroit Pistons", "abbr": "DET"},
    {"name": "Ausar Thompson", "team": "Detroit Pistons", "abbr": "DET"},
    
    # Golden State Warriors
    {"name": "Stephen Curry", "team": "Golden State Warriors", "abbr": "GSW"},
    {"name": "Klay Thompson", "team": "Golden State Warriors", "abbr": "GSW"},
    {"name": "Draymond Green", "team": "Golden State Warriors", "abbr": "GSW"},
    {"name": "Andrew Wiggins", "team": "Golden State Warriors", "abbr": "GSW"},
    
    # Houston Rockets
    {"name": "Alperen Sengun", "team": "Houston Rockets", "abbr": "HOU"},
    {"name": "Jalen Green", "team": "Houston Rockets", "abbr": "HOU"},
    {"name": "Jabari Smith Jr.", "team": "Houston Rockets", "abbr": "HOU"},
    {"name": "Fred VanVleet", "team": "Houston Rockets", "abbr": "HOU"},
    
    # Indiana Pacers
    {"name": "Tyrese Haliburton", "team": "Indiana Pacers", "abbr": "IND"},
    {"name": "Myles Turner", "team": "Indiana Pacers", "abbr": "IND"},
    {"name": "Pascal Siakam", "team": "Indiana Pacers", "abbr": "IND"},
    {"name": "Bennedict Mathurin", "team": "Indiana Pacers", "abbr": "IND"},
    
    # LA Clippers
    {"name": "Kawhi Leonard", "team": "LA Clippers", "abbr": "LAC"},
    {"name": "Paul George", "team": "LA Clippers", "abbr": "LAC"},
    {"name": "James Harden", "team": "LA Clippers", "abbr": "LAC"},
    {"name": "Russell Westbrook", "team": "LA Clippers", "abbr": "LAC"},
    
    # Los Angeles Lakers
    {"name": "LeBron James", "team": "Los Angeles Lakers", "abbr": "LAL"},
    {"name": "Anthony Davis", "team": "Los Angeles Lakers", "abbr": "LAL"},
    {"name": "D'Angelo Russell", "team": "Los Angeles Lakers", "abbr": "LAL"},
    {"name": "Austin Reaves", "team": "Los Angeles Lakers", "abbr": "LAL"},
    
    # Memphis Grizzlies
    {"name": "Ja Morant", "team": "Memphis Grizzlies", "abbr": "MEM"},
    {"name": "Jaren Jackson Jr.", "team": "Memphis Grizzlies", "abbr": "MEM"},
    {"name": "Desmond Bane", "team": "Memphis Grizzlies", "abbr": "MEM"},
    
    # Miami Heat
    {"name": "Jimmy Butler", "team": "Miami Heat", "abbr": "MIA"},
    {"name": "Bam Adebayo", "team": "Miami Heat", "abbr": "MIA"},
    {"name": "Tyler Herro", "team": "Miami Heat", "abbr": "MIA"},
    
    # Milwaukee Bucks
    {"name": "Giannis Antetokounmpo", "team": "Milwaukee Bucks", "abbr": "MIL"},
    {"name": "Damian Lillard", "team": "Milwaukee Bucks", "abbr": "MIL"},
    {"name": "Khris Middleton", "team": "Milwaukee Bucks", "abbr": "MIL"},
    {"name": "Brook Lopez", "team": "Milwaukee Bucks", "abbr": "MIL"},
    
    # Minnesota Timberwolves
    {"name": "Anthony Edwards", "team": "Minnesota Timberwolves", "abbr": "MIN"},
    {"name": "Karl-Anthony Towns", "team": "Minnesota Timberwolves", "abbr": "MIN"},
    {"name": "Rudy Gobert", "team": "Minnesota Timberwolves", "abbr": "MIN"},
    {"name": "Mike Conley", "team": "Minnesota Timberwolves", "abbr": "MIN"},
    
    # New Orleans Pelicans
    {"name": "Zion Williamson", "team": "New Orleans Pelicans", "abbr": "NOP"},
    {"name": "Brandon Ingram", "team": "New Orleans Pelicans", "abbr": "NOP"},
    {"name": "CJ McCollum", "team": "New Orleans Pelicans", "abbr": "NOP"},
    {"name": "Herb Jones", "team": "New Orleans Pelicans", "abbr": "NOP"},
    
    # New York Knicks
    {"name": "Jalen Brunson", "team": "New York Knicks", "abbr": "NYK"},
    {"name": "Julius Randle", "team": "New York Knicks", "abbr": "NYK"},
    {"name": "RJ Barrett", "team": "New York Knicks", "abbr": "NYK"},
    {"name": "Mitchell Robinson", "team": "New York Knicks", "abbr": "NYK"},
    
    # Oklahoma City Thunder
    {"name": "Shai Gilgeous-Alexander", "team": "Oklahoma City Thunder", "abbr": "OKC"},
    {"name": "Chet Holmgren", "team": "Oklahoma City Thunder", "abbr": "OKC"},
    {"name": "Jalen Williams", "team": "Oklahoma City Thunder", "abbr": "OKC"},
    {"name": "Josh Giddey", "team": "Oklahoma City Thunder", "abbr": "OKC"},
    
    # Orlando Magic
    {"name": "Paolo Banchero", "team": "Orlando Magic", "abbr": "ORL"},
    {"name": "Franz Wagner", "team": "Orlando Magic", "abbr": "ORL"},
    {"name": "Wendell Carter Jr.", "team": "Orlando Magic", "abbr": "ORL"},
    
    # Philadelphia 76ers
    {"name": "Joel Embiid", "team": "Philadelphia 76ers", "abbr": "PHI"},
    {"name": "Tyrese Maxey", "team": "Philadelphia 76ers", "abbr": "PHI"},
    {"name": "Tobias Harris", "team": "Philadelphia 76ers", "abbr": "PHI"},
    
    # Phoenix Suns
    {"name": "Kevin Durant", "team": "Phoenix Suns", "abbr": "PHX"},
    {"name": "Devin Booker", "team": "Phoenix Suns", "abbr": "PHX"},
    {"name": "Bradley Beal", "team": "Phoenix Suns", "abbr": "PHX"},
    {"name": "Jusuf Nurkic", "team": "Phoenix Suns", "abbr": "PHX"},
    
    # Portland Trail Blazers
    {"name": "Damian Lillard", "team": "Portland Trail Blazers", "abbr": "POR"},
    {"name": "Anfernee Simons", "team": "Portland Trail Blazers", "abbr": "POR"},
    {"name": "Jerami Grant", "team": "Portland Trail Blazers", "abbr": "POR"},
    {"name": "Shaedon Sharpe", "team": "Portland Trail Blazers", "abbr": "POR"},
    
    # Sacramento Kings
    {"name": "De'Aaron Fox", "team": "Sacramento Kings", "abbr": "SAC"},
    {"name": "Domantas Sabonis", "team": "Sacramento Kings", "abbr": "SAC"},
    {"name": "Keegan Murray", "team": "Sacramento Kings", "abbr": "SAC"},
    
    # San Antonio Spurs
    {"name": "Victor Wembanyama", "team": "San Antonio Spurs", "abbr": "SAS"},
    {"name": "Devin Vassell", "team": "San Antonio Spurs", "abbr": "SAS"},
    {"name": "Keldon Johnson", "team": "San Antonio Spurs", "abbr": "SAS"},
    
    # Toronto Raptors
    {"name": "Scottie Barnes", "team": "Toronto Raptors", "abbr": "TOR"},
    {"name": "Pascal Siakam", "team": "Toronto Raptors", "abbr": "TOR"},
    {"name": "OG Anunoby", "team": "Toronto Raptors", "abbr": "TOR"},
    
    # Utah Jazz
    {"name": "Lauri Markkanen", "team": "Utah Jazz", "abbr": "UTA"},
    {"name": "Jordan Clarkson", "team": "Utah Jazz", "abbr": "UTA"},
    {"name": "Walker Kessler", "team": "Utah Jazz", "abbr": "UTA"},
    
    # Washington Wizards
    {"name": "Kyle Kuzma", "team": "Washington Wizards", "abbr": "WAS"},
    {"name": "Jordan Poole", "team": "Washington Wizards", "abbr": "WAS"},
    {"name": "Tyus Jones", "team": "Washington Wizards", "abbr": "WAS"},
]

TEAM_MAPPINGS = {
    'ATL': {'nbc': 'atlanta-hawks', 'espn': 'atl', 'cbs': 'ATL'},
    'BOS': {'nbc': 'boston-celtics', 'espn': 'bos', 'cbs': 'BOS'},
    'BKN': {'nbc': 'brooklyn-nets', 'espn': 'bkn', 'cbs': 'BKN'},
    'CHA': {'nbc': 'charlotte-hornets', 'espn': 'cha', 'cbs': 'CHA'},
    'CHI': {'nbc': 'chicago-bulls', 'espn': 'chi', 'cbs': 'CHI'},
    'CLE': {'nbc': 'cleveland-cavaliers', 'espn': 'cle', 'cbs': 'CLE'},
    'DAL': {'nbc': 'dallas-mavericks', 'espn': 'dal', 'cbs': 'DAL'},
    'DEN': {'nbc': 'denver-nuggets', 'espn': 'den', 'cbs': 'DEN'},
    'DET': {'nbc': 'detroit-pistons', 'espn': 'det', 'cbs': 'DET'},
    'GSW': {'nbc': 'golden-state-warriors', 'espn': 'gs', 'cbs': 'GSW'},
    'HOU': {'nbc': 'houston-rockets', 'espn': 'hou', 'cbs': 'HOU'},
    'IND': {'nbc': 'indiana-pacers', 'espn': 'ind', 'cbs': 'IND'},
    'LAC': {'nbc': 'la-clippers', 'espn': 'lac', 'cbs': 'LAC'},
    'LAL': {'nbc': 'los-angeles-lakers', 'espn': 'lal', 'cbs': 'LAL'},
    'MEM': {'nbc': 'memphis-grizzlies', 'espn': 'mem', 'cbs': 'MEM'},
    'MIA': {'nbc': 'miami-heat', 'espn': 'mia', 'cbs': 'MIA'},
    'MIL': {'nbc': 'milwaukee-bucks', 'espn': 'mil', 'cbs': 'MIL'},
    'MIN': {'nbc': 'minnesota-timberwolves', 'espn': 'min', 'cbs': 'MIN'},
    'NOP': {'nbc': 'new-orleans-pelicans', 'espn': 'no', 'cbs': 'NOP'},
    'NYK': {'nbc': 'new-york-knicks', 'espn': 'ny', 'cbs': 'NYK'},
    'OKC': {'nbc': 'oklahoma-city-thunder', 'espn': 'okc', 'cbs': 'OKC'},
    'ORL': {'nbc': 'orlando-magic', 'espn': 'orl', 'cbs': 'ORL'},
    'PHI': {'nbc': 'philadelphia-76ers', 'espn': 'phi', 'cbs': 'PHI'},
    'PHX': {'nbc': 'phoenix-suns', 'espn': 'phx', 'cbs': 'PHX'},
    'POR': {'nbc': 'portland-trail-blazers', 'espn': 'por', 'cbs': 'POR'},
    'SAC': {'nbc': 'sacramento-kings', 'espn': 'sac', 'cbs': 'SAC'},
    'SAS': {'nbc': 'san-antonio-spurs', 'espn': 'sa', 'cbs': 'SAS'},
    'TOR': {'nbc': 'toronto-raptors', 'espn': 'tor', 'cbs': 'TOR'},
    'UTA': {'nbc': 'utah-jazz', 'espn': 'utah', 'cbs': 'UTA'},
    'WAS': {'nbc': 'washington-wizards', 'espn': 'wsh', 'cbs': 'WAS'},
}

def get_player_team(player_name):
    """Trouve l'équipe d'un joueur"""
    for player in NBA_PLAYERS:
        if player['name'].lower() == player_name.lower():
            return player['abbr']
    return None

def scrape_nbc_injuries(team_abbr, player_name):
    """Scrape les blessures depuis NBC Sports"""
    try:
        team_slug = TEAM_MAPPINGS[team_abbr]['nbc']
        url = f'https://www.nbcsports.com/nba/{team_slug}/injuries'
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        injuries = []
        
        # Chercher les lignes de tableau ou sections de blessures
        injury_rows = soup.find_all(['tr', 'div'], class_=re.compile('injury|player', re.I))
        
        for row in injury_rows:
            text = row.get_text()
            if player_name.lower() in text.lower():
                injury = {
                    'player': player_name,
                    'status': 'Out',
                    'injury': '',
                    'date': '',
                    'comment': text.strip()
                }
                injuries.append(injury)
                break
        
        return injuries
    except Exception as e:
        print(f"Erreur NBC: {e}")
        return []

def scrape_espn_injuries(team_abbr, player_name):
    """Scrape les blessures depuis ESPN"""
    try:
        team_slug = TEAM_MAPPINGS[team_abbr]['espn']
        url = f'https://www.espn.com/nba/team/injuries/_/name/{team_slug}'
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        injuries = []
        
        # ESPN utilise généralement des tableaux
        tables = soup.find_all('table')
        
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                text = row.get_text()
                if player_name.lower() in text.lower():
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 3:
                        injury = {
                            'player': player_name,
                            'status': cells[1].get_text().strip() if len(cells) > 1 else 'Out',
                            'injury': cells[2].get_text().strip() if len(cells) > 2 else '',
                            'date': cells[3].get_text().strip() if len(cells) > 3 else '',
                            'comment': ''
                        }
                        injuries.append(injury)
                        break
        
        return injuries
    except Exception as e:
        print(f"Erreur ESPN: {e}")
        return []

def scrape_cbs_injuries(team_abbr, player_name):
    """Scrape les blessures depuis CBS Sports"""
    try:
        team_slug = TEAM_MAPPINGS[team_abbr]['cbs']
        team_name_slug = TEAM_MAPPINGS[team_abbr]['nbc']
        url = f'https://www.cbssports.com/nba/teams/{team_slug}/{team_name_slug}/injuries/'
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        injuries = []
        
        # CBS utilise généralement des tableaux avec classe spécifique
        tables = soup.find_all('table')
        
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                text = row.get_text()
                if player_name.lower() in text.lower():
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 2:
                        injury = {
                            'player': player_name,
                            'status': cells[1].get_text().strip() if len(cells) > 1 else 'Out',
                            'injury': cells[2].get_text().strip() if len(cells) > 2 else '',
                            'date': cells[3].get_text().strip() if len(cells) > 3 else '',
                            'comment': ''
                        }
                        injuries.append(injury)
                        break
        
        return injuries
    except Exception as e:
        print(f"Erreur CBS: {e}")
        return []

@app.route('/api/players', methods=['GET'])
def get_players():
    """Retourne la liste de tous les joueurs"""
    return jsonify(NBA_PLAYERS)

@app.route('/api/injuries/<player_name>', methods=['GET'])
def get_injuries(player_name):
    """Récupère les blessures pour un joueur spécifique"""
    
    team_abbr = get_player_team(player_name)
    
    if not team_abbr:
        return jsonify({'error': 'Joueur non trouvé'}), 404
    
    if team_abbr not in TEAM_MAPPINGS:
        return jsonify({'error': 'Équipe non supportée'}), 404
    
    # Scraper les trois sources
    nbc_injuries = scrape_nbc_injuries(team_abbr, player_name)
    espn_injuries = scrape_espn_injuries(team_abbr, player_name)
    cbs_injuries = scrape_cbs_injuries(team_abbr, player_name)
    
    # Construire les URLs
    team_map = TEAM_MAPPINGS[team_abbr]
    urls = {
        'nbc': f'https://www.nbcsports.com/nba/{team_map["nbc"]}/injuries',
        'espn': f'https://www.espn.com/nba/team/injuries/_/name/{team_map["espn"]}',
        'cbs': f'https://www.cbssports.com/nba/teams/{team_map["cbs"]}/{team_map["nbc"]}/injuries/'
    }
    
    return jsonify({
        'player': player_name,
        'team': team_abbr,
        'sources': {
            'nbc': nbc_injuries,
            'espn': espn_injuries,
            'cbs': cbs_injuries
        },
        'urls': urls
    })

@app.route('/', methods=['GET'])
def index():
    """Page d'accueil de l'API"""
    return jsonify({
        'message': 'NBA Injury Tracker API',
        'endpoints': {
            '/api/players': 'Liste de tous les joueurs NBA',
            '/api/injuries/<player_name>': 'Informations sur les blessures d\'un joueur'
        }
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
