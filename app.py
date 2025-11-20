import os
import requests
import unicodedata
from flask import Flask, request, jsonify
from flask_cors import CORS
from bs4 import BeautifulSoup

app = Flask(__name__)
CORS(app)

# --- CONFIGURATION ---
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
}

# Liste complète des joueurs actifs (Générée pour la saison 2024-2025)
# Cette liste est servie au frontend via /api/players
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
    if not text:
        return ""
    return ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn').lower().strip()

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
    except Exception as e:
        print(f"Erreur CBS: {e}")
        return "Erreur temporaire CBS"

def scrape_espn_injuries(player_name):
    url = "https://www.espn.com/nba/injuries"
    try:
        response = requests.get(url, headers=HEADERS, timeout=5)
        soup = BeautifulSoup(response.content, 'html.parser')
        normalized_target = normalize_text(player_name)
        player_links = soup.find_all('a', href=True)
        for link in player_links:
            if "player" in link['href'] and normalized_target in normalize_text(link.get_text()):
                row = link.find_parent('tr')
                if row:
                    cols = row.find_all('td')
                    if len(cols) >= 2:
                        status = cols[1].get_text(strip=True)
                        comment = cols[2].get_text(strip=True) if len(cols) > 2 else ""
                        return f"{status} ({comment})"
        return None
    except Exception as e:
        print(f"Erreur ESPN: {e}")
        return "Erreur temporaire ESPN"

def scrape_nbc_data(player_name):
    """
    Récupère directement les infos de la page joueur NBC Sports.
    Format URL: https://www.nbcsports.com/nba/player/{first-last}
    """
    # Formatage du slug (LeBron James -> lebron-james)
    slug = normalize_text(player_name).replace(" ", "-")
    url = f"https://www.nbcsports.com/nba/player/{slug}"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=6)
        
        # Si redirection ou 404, le joueur a peut-être un URL différent ou n'existe pas chez NBC
        if response.status_code != 200:
            return f"Page joueur introuvable ({response.status_code})"

        soup = BeautifulSoup(response.content, 'html.parser')
        
        # NBC change souvent ses classes CSS, on cherche large
        # Recherche 1: Section "Latest News"
        news_items = soup.find_all('div', class_=lambda x: x and 'PlayerNews-headline' in x)
        
        if not news_items:
            # Fallback: Recherche générique de paragraphes dans la section principale
            content_area = soup.find('div', class_='Page-content')
            if content_area:
                paragraphs = content_area.find_all('p')
                if paragraphs:
                    return paragraphs[0].get_text(strip=True)[:200] + "..."

        if news_items:
            # On prend le premier titre et le premier bout de texte
            headline = news_items[0].get_text(strip=True)
            # On essaie de trouver le texte associé
            parent = news_items[0].find_parent()
            details = parent.find('div', class_=lambda x: x and 'PlayerNews-body' in x)
            detail_text = details.get_text(strip=True) if details else ""
            
            return f"{headline}: {detail_text}"[:250] + "..." # On coupe si trop long
            
        return "Aucune news récente trouvée sur NBC."

    except Exception as e:
        print(f"Erreur NBC: {e}")
        return "Erreur d'accès NBC Sports"

@app.route('/')
def home():
    return "API NBA Injury Running. Use /api/check?player=Name or /api/players"

@app.route('/api/players', methods=['GET'])
def get_all_players():
    """Renvoie la liste complète des joueurs au format JSON."""
    return jsonify(ALL_PLAYERS)

@app.route('/api/check', methods=['GET'])
def check_injury():
    player_name = request.args.get('player')
    if not player_name:
        return jsonify({"error": "Nom manquant"}), 400
        
    cbs = scrape_cbs_injuries(player_name)
    espn = scrape_espn_injuries(player_name)
    nbc = scrape_nbc_data(player_name)
    
    return jsonify({
        "player": player_name,
        "sources": {
            "CBS": cbs if cbs else "Healthy / Pas sur la liste",
            "ESPN": espn if espn else "Pas sur la liste",
            "NBC": nbc
        }
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
