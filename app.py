import os
import requests
import unicodedata
import re
from flask import Flask, request, jsonify
from flask_cors import CORS
from bs4 import BeautifulSoup

app = Flask(__name__)
CORS(app)

# --- CONFIGURATION ---
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer': 'https://www.google.com/'
}

# Liste complète des joueurs (Même liste que précédemment, abrégée ici pour la lisibilité du code généré, 
# mais gardez votre liste complète dans le déploiement réel)
# Note: Assurez-vous d'avoir la liste ALL_PLAYERS complète comme dans la version précédente.
ALL_PLAYERS = [
    "Precious Achiuwa", "Bam Adebayo", "Ochai Agbaji", "Santi Aldama", "Nickeil Alexander-Walker", "Grayson Allen", "Jarrett Allen", "Jose Alvarado", "Kyle Anderson", "Giannis Antetokounmpo", "Thanasis Antetokounmpo", "Cole Anthony", "OG Anunoby", "Ryan Arcidiacono", "Deni Avdija", "Deandre Ayton", "Udoka Azubuike",
    "Marvin Bagley III", "Patrick Baldwin Jr.", "LaMelo Ball", "Lonzo Ball", "Mo Bamba", "Paolo Banchero", "Desmond Bane", "Dalano Banton", "Dominick Barlow", "Harrison Barnes", "Scottie Barnes", "RJ Barrett", "Charles Bassey", "Emoni Bates", "Keita Bates-Diop", "Nicolas Batum", "Bradley Beal", "Malik Beasley", "MarJon Beauchamp", "Davis Bertans", "Patrick Beverley", "Saddiq Bey", "Goga Bitadze", "Bismack Biyombo", "Anthony Black", "Bogdan Bogdanovic", "Bojan Bogdanovic", "Bol Bol", "Marques Bolden", "Devin Booker", "Brandon Boston Jr.", "Chris Boucher", "James Bouknight", "Christian Braun", "Mikal Bridges", "Miles Bridges", "Oshae Brissett", "Malcolm Brogdon", "Dillon Brooks", "Bruce Brown", "Jaylen Brown", "Kendall Brown", "Kobe Brown", "Moses Brown", "Greg Brown III", "Jalen Brunson", "Thomas Bryant", "Kobe Bufkin", "Reggie Bullock", "Alec Burks", "Jimmy Butler",
    "Kentavious Caldwell-Pope", "Toumani Camara", "Vlatko Cancar", "Clint Capela", "Jevon Carter", "Wendell Carter Jr.", "Alex Caruso", "Julian Champagnie", "Max Christie", "Sidy Cissoko", "Jordan Clarkson", "Nic Claxton", "Noah Clowney", "Amir Coffey", "John Collins", "Zach Collins", "Mike Conley", "Pat Connaughton", "Bilal Coulibaly", "Robert Covington", "Torrey Craig", "Jae Crowder", "Cade Cunningham", "Seth Curry", "Stephen Curry", "Dyson Daniels",
    "Anthony Davis", "Johnny Davis", "DeMar DeRozan", "Dewayne Dedmon", "Ousmane Dieng", "Spencer Dinwiddie", "Donte DiVincenzo", "Luka Doncic", "Luguentz Dort", "Ayo Dosunmu", "Andre Drummond", "Chris Duarte", "Kris Dunn", "Kevin Durant", "Jalen Duren", "Tari Eason", "Anthony Edwards", "Keon Ellis", "Joel Embiid", "Drew Eubanks",
    "Dante Exum", "Bruno Fernando", "Dorian Finney-Smith", "Malachi Flynn", "Simone Fontecchio", "Jordan Ford", "Evan Fournier", "De'Aaron Fox", "Daniel Gafford", "Danilo Gallinari", "Darius Garland", "Usman Garuba", "Luka Garza", "Paul George", "Keyonte George", "Taj Gibson", "Josh Giddey", "Harry Giles III", "Shai Gilgeous-Alexander", "Anthony Gill", "Rudy Gobert", "Jordan Goodwin", "Aaron Gordon", "Eric Gordon", "Devonte' Graham", "Jerami Grant", "RaiQuan Gray", "AJ Green", "Draymond Green", "Jalen Green", "Jeff Green", "Josh Green", "Griffin Login", "Quentin Grimes",
    "Rui Hachimura", "Tyrese Haliburton", "R.J. Hampton", "Tim Hardaway Jr.", "James Harden", "Jaden Hardy", "Tobias Harris", "Josh Hart", "Isaiah Hartenstein", "Sam Hauser", "Jaxson Hayes", "Killian Hayes", "Gordon Hayward", "Scoot Henderson", "Taylor Hendricks", "Tyler Herro", "Buddy Hield", "Haywood Highsmith", "Nate Hinton", "Aaron Holiday", "Jrue Holiday", "Richaun Holmes", "Chet Holmgren", "Jalen Hood-Schifino", "Al Horford", "Talen Horton-Tucker", "Danuel House Jr.", "Caleb Houstan", "Jett Howard", "Kevin Huerter", "De'Andre Hunter", "Bones Hyland",
    "Joe Ingles", "Brandon Ingram", "Kyrie Irving", "Jonathan Isaac", "Jaden Ivey", "G.G. Jackson", "Isaiah Jackson", "Reggie Jackson", "Trayce Jackson-Davis", "Jaren Jackson Jr.", "LeBron James", "Jaime Jaquez Jr.", "DaQuan Jeffries", "Ty Jerome", "Isaiah Joe", "Cameron Johnson", "Jalen Johnson", "Keldon Johnson", "Keon Johnson", "Keyontae Johnson", "Nikola Jokic", "Damian Jones", "Herbert Jones", "Tre Jones", "Tyus Jones", "Cory Joseph", "Nikola Jovic", "Johnny Juzang",
    "Luke Kennard", "Walker Kessler", "Braxton Key", "Corey Kispert", "Maxi Kleber", "Kevin Knox II", "Christian Koloko", "John Konchar", "Furkan Korkmaz", "Luke Kornet", "Jonathan Kuminga", "Kyle Kuzma", "Jake LaRavia", "Zach LaVine", "Jock Landale", "Caris LeVert", "Damion Lee", "Saben Lee", "Alex Len", "Kawhi Leonard", "Kira Lewis Jr.", "Maxwell Lewis", "Damian Lillard", "Nassir Little", "Dereck Lively II", "Kenneth Lofton Jr.", "Kevon Looney", "Brook Lopez", "Robin Lopez", "Kyle Lowry", "Seth Lundy", "Trey Lyles",
    "Theo Maledon", "Terance Mann", "Tre Mann", "Boban Marjanovic", "Lauri Markkanen", "Naji Marshall", "Caleb Martin", "Cody Martin", "K.J. Martin", "Garrison Mathews", "Bennedict Mathurin", "Wesley Matthews", "Tyrese Maxey", "Skylar Mays", "Miles McBride", "C.J. McCollum", "T.J. McConnell", "Jaden McDaniels", "Jalen McDaniels", "Doug McDermott", "JaVale McGee", "Cameron McGough", "Bryce McGowens", "Jordan McLaughlin", "De'Anthony Melton", "Sam Merrill", "Chimezie Metu", "Vasilije Micic", "Khris Middleton", "Brandon Miller", "Leonard Miller", "Patty Mills", "Shake Milton", "Davion Mitchell", "Donovan Mitchell", "Evan Mobley", "Isaiah Mobley", "Malik Monk", "Moses Moody", "Xavier Moon", "Wendell Moore Jr.", "Ja Morant", "Marcus Morris Sr.", "Markieff Morris", "Monte Morris", "Trey Murphy III", "Dejounte Murray", "Jamal Murray", "Keegan Murray", "Kris Murray", "Mike Muscala", "Svi Mykhailiuk",
    "Larry Nance Jr.", "Andrew Nembhard", "Aaron Nesmith", "Georges Niang", "Daishen Nix", "Zeke Nnaji", "Jaylen Nowell", "Frank Ntilikina", "Jusuf Nurkic", "Jordan Nwora", "Royce O'Neale", "Chuma Okeke", "Josh Okogie", "Onyeka Okongwu", "Isaac Okoro", "Kelly Olynyk", "Cedi Osman", "Kelly Oubre Jr.",
    "Chris Paul", "Cameron Payne", "Gary Payton II", "Filip Petrusev", "Julian Phillips", "Jalen Pickett", "Mason Plumlee", "Brandin Podziemski", "Jakob Poeltl", "Aleksej Pokusevski", "Jordan Poole", "Kevin Porter Jr.", "Michael Porter Jr.", "Otto Porter Jr.", "Bobby Portis", "Kristaps Porzingis", "Dwight Powell", "Norman Powell", "Taurean Prince", "Payton Pritchard", "Olivier-Maxence Prosper",
    "Neemias Queta", "Immanuel Quickley", "Lester Quinones", "Julius Randle", "Duop Reath", "Austin Reaves", "Cam Reddish", "Paul Reed", "Naz Reid", "Jared Rhoden", "Nick Richards", "Josh Richardson", "Duncan Robinson", "Jerome Robinson", "Mitchell Robinson", "David Roddy", "Ryan Rollins", "Derrick Rose", "Terry Rozier", "Rayan Rupert", "D'Angelo Russell",
    "Domantas Sabonis", "Luka Samanic", "Adama Sanogo", "Dario Saric", "Olivier Sarr", "Marcus Sasser", "Schofield Admiral", "Dennis Schroder", "Alperen Sengun", "Brice Sensabaugh", "Collin Sexton", "Landry Shamet", "Day'Ron Sharpe", "Shaedon Sharpe", "Pascal Siakam", "Ben Simmons", "Anfernee Simons", "Jericho Sims", "Marcus Smart", "Dru Smith", "Ish Smith", "Jalen Smith", "Jabari Smith Jr.", "Dennis Smith Jr.", "Jeremy Sochan", "Jaden Springer", "Lamar Stevens", "Isaiah Stewart", "Julian Strawther", "Max Strus", "Jalen Suggs", "Edmond Sumner", "Cole Swider",
    "Jae'Sean Tate", "Jayson Tatum", "Terry Taylor", "Garrett Temple", "Dalen Terry", "Daniel Theis", "Cam Thomas", "Amen Thompson", "Ausar Thompson", "Klay Thompson", "Tristan Thompson", "JT Thor", "Matisse Thybulle", "Xavier Tillman", "Obi Toppin", "Karl-Anthony Towns", "Gary Trent Jr.", "Oscar Tshiebwe", "P.J. Tucker", "Myles Turner",
    "Jonas Valanciunas", "Fred VanVleet", "Jarred Vanderbilt", "Devin Vassell", "Sasha Vezenkov", "Gabe Vincent", "Nikola Vucevic", "Dean Wade", "Franz Wagner", "Moritz Wagner", "Ish Wainright", "Jabari Walker", "Jarace Walker", "Lonnie Walker IV", "Cason Wallace", "T.J. Warren", "P.J. Washington", "TyTy Washington Jr.", "Yuta Watanabe", "Lindy Waters III", "Trendon Watford", "Peyton Watson", "Victor Wembanyama", "Blake Wesley", "Russell Westbrook", "Coby White", "Derrick White", "Cam Whitmore", "Aaron Wiggins", "Andrew Wiggins", "Lindell Wigginton", "Grant Williams", "Jalen Williams", "Jaylin Williams", "Kenrich Williams", "Mark Williams", "Patrick Williams", "Robert Williams III", "Vince Williams Jr.", "Zion Williamson", "D.J. Wilson", "Dylan Windler", "James Wiseman", "Christian Wood", "Delon Wright", "McKinley Wright IV",
    "Thaddeus Young", "Trae Young", "Omer Yurtseven", "Cody Zeller", "Ivica Zubac"
]

def normalize_text(text):
    """Supprime accents et minuscules"""
    if not text:
        return ""
    return ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn').lower().strip()

def clean_slug(text):
    """Prépare le nom pour les URLs (ex: 'C.J. McCollum' -> 'cj-mccollum')"""
    text = normalize_text(text)
    text = text.replace('.', '') # Enlever les points (C.J. -> cj)
    text = text.replace("'", '') # Enlever les apostrophes (De'Aaron -> deaaron)
    text = re.sub(r'\s+', '-', text) # Espaces -> tirets
    return text

def scrape_cbs_injuries(player_name):
    url = "https://www.cbssports.com/nba/injuries/"
    try:
        response = requests.get(url, headers=HEADERS, timeout=6)
        soup = BeautifulSoup(response.content, 'html.parser')
        rows = soup.find_all('tr')
        normalized_target = normalize_text(player_name)
        
        for row in rows:
            cols = row.find_all('td')
            if len(cols) >= 2:
                name_col = cols[0].get_text()
                # Vérification plus souple
                if normalized_target in normalize_text(name_col):
                    status = cols[-1].get_text(strip=True)
                    injury = cols[-2].get_text(strip=True)
                    return f"{status} - {injury}"
        return None
    except Exception as e:
        print(f"Erreur CBS: {e}")
        return None

def scrape_rotowire_injuries(player_name):
    """Remplace ESPN par Rotowire"""
    url = "https://www.rotowire.com/basketball/injury-report.php"
    try:
        response = requests.get(url, headers=HEADERS, timeout=6)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        normalized_target = normalize_text(player_name)
        
        # Rotowire utilise souvent des divs ou tables. On cherche les liens joueurs
        # Structure commune: div.injury-report__player-name a -> text
        links = soup.find_all('a', href=True)
        
        for link in links:
            if "player" in link['href'] and normalized_target in normalize_text(link.get_text()):
                # On a trouvé le joueur, on cherche le conteneur parent (souvent une ligne de table ou div)
                # Rotowire Table structure: 
                # Row -> Cell Name -> Cell Injury -> Cell Status -> Cell Est. Return
                row = link.find_parent('div', class_='injury-report__row') # Format div
                if not row:
                    row = link.find_parent('tr') # Fallback format table
                
                if row:
                    # Essayer d'extraire les infos selon les classes CSS de Rotowire
                    injury_div = row.find(class_='injury-report__injury')
                    status_div = row.find(class_='injury-report__status')
                    return_div = row.find(class_='injury-report__return')
                    
                    injury = injury_div.get_text(strip=True) if injury_div else "Unknown"
                    status = status_div.get_text(strip=True) if status_div else ""
                    est_return = return_div.get_text(strip=True) if return_div else ""
                    
                    # Fallback si classes non trouvées (si c'est une table standard)
                    if not injury_div and isinstance(row, object) and hasattr(row, 'find_all'):
                        cols = row.find_all('td')
                        if len(cols) > 3:
                            injury = cols[2].get_text(strip=True)
                            status = cols[3].get_text(strip=True)
                    
                    return f"{status} - {injury} (Est. return: {est_return})"

        return None
    except Exception as e:
        print(f"Erreur Rotowire: {e}")
        return None

def scrape_nbc_data(player_name):
    """
    Nouvelle méthode pour NBC Sports.
    Utilise la balise META description pour contourner le rendu React complexe.
    """
    slug = clean_slug(player_name)
    url = f"https://www.nbcsports.com/nba/player/{slug}"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=8)
        
        if response.status_code != 200:
            return f"Page joueur introuvable (Code {response.status_code})"

        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 1. Essayer de trouver la Meta Description (contient souvent la dernière news)
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            content = meta_desc.get('content')
            # Nettoyer le texte standard de NBC
            if "Latest news, stats" in content:
                # Parfois c'est juste un placeholder, on continue de chercher
                pass
            else:
                return content[:250] + "..."

        # 2. Recherche spécifique News Headline (si le HTML est rendu)
        news_headline = soup.find(class_='PlayerNews-headline')
        if news_headline:
            headline_text = news_headline.get_text(strip=True)
            # Chercher le corps du texte associé
            news_body = news_headline.find_next(class_='PlayerNews-body')
            body_text = news_body.get_text(strip=True) if news_body else ""
            return f"{headline_text}: {body_text}"[:250] + "..."

        # 3. Fallback : JSON-LD (Données structurées Google)
        # Parfois les news sont dans un script json+ld
        scripts = soup.find_all('script', type='application/ld+json')
        for script in scripts:
            if player_name in script.get_text():
                # C'est trop complexe de parser tout le JSON ici, mais souvent présent
                pass

        return "Aucune news récente détectée (Format de page protégé)."

    except Exception as e:
        print(f"Erreur NBC: {e}")
        return "Erreur d'accès NBC Sports"

@app.route('/')
def home():
    return "API NBA Injury Running."

@app.route('/api/players', methods=['GET'])
def get_all_players():
    return jsonify(ALL_PLAYERS)

@app.route('/api/check', methods=['GET'])
def check_injury():
    player_name = request.args.get('player')
    if not player_name:
        return jsonify({"error": "Nom manquant"}), 400
        
    cbs = scrape_cbs_injuries(player_name)
    rotowire = scrape_rotowire_injuries(player_name)
    nbc = scrape_nbc_data(player_name)
    
    return jsonify({
        "player": player_name,
        "sources": {
            "CBS": cbs if cbs else "Healthy / Pas sur la liste",
            "Rotowire": rotowire if rotowire else "Pas sur la liste",
            "NBC": nbc
        }
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
