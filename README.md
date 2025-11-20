# NBA Injury Tracker

Application web permettant de vérifier les blessures et le statut des joueurs NBA en agrégeant les informations de NBC Sports, ESPN et CBS Sports.

## 🚀 Déploiement sur Render.com

### Prérequis
- Compte GitHub
- Compte Render.com

### Instructions

1. **Créer un dépôt GitHub**
   - Uploadez tous les fichiers du projet sur GitHub
   - Assurez-vous que `app.py`, `requirements.txt`, et `render.yaml` sont à la racine

2. **Déployer sur Render**
   - Allez sur [Render.com](https://render.com)
   - Cliquez sur "New +" puis "Web Service"
   - Connectez votre dépôt GitHub
   - Render détectera automatiquement qu'il s'agit d'une application Python
   - Configurez:
     - **Name**: `nba-injury-tracker` (ou votre choix)
     - **Environment**: `Python 3`
     - **Build Command**: `pip install -r requirements.txt`
     - **Start Command**: `gunicorn app:app`
   - Cliquez sur "Create Web Service"

3. **Mettre à jour le frontend**
   - Une fois déployé, notez l'URL de votre service (ex: `https://nba-injury-tracker.onrender.com`)
   - Dans le fichier `index.html`, ligne 338, remplacez:
     ```javascript
     const API_BASE_URL = window.location.hostname === 'localhost' 
         ? 'http://localhost:5000' 
         : 'https://your-render-app.onrender.com';
     ```
   - Par votre URL Render:
     ```javascript
     const API_BASE_URL = window.location.hostname === 'localhost' 
         ? 'http://localhost:5000' 
         : 'https://nba-injury-tracker.onrender.com';
     ```

4. **Héberger le frontend**
   - Option 1: GitHub Pages (gratuit)
   - Option 2: Render Static Site (gratuit)
   - Option 3: Netlify/Vercel (gratuit)

## 🧪 Test en local

### Backend
```bash
# Installer les dépendances
pip install -r requirements.txt

# Lancer le serveur
python app.py
```
Le serveur sera accessible sur `http://localhost:5000`

### Frontend
Ouvrez simplement `index.html` dans votre navigateur, ou utilisez un serveur local:
```bash
python -m http.server 8000
```
Puis allez sur `http://localhost:8000`

## 📁 Structure du projet

```
nba-injury-tracker/
├── app.py              # Backend Flask
├── requirements.txt    # Dépendances Python
├── render.yaml        # Configuration Render
├── index.html         # Frontend
└── README.md          # Ce fichier
```

## 🔧 API Endpoints

- `GET /api/players` - Liste de tous les joueurs NBA
- `GET /api/injuries/<player_name>` - Informations sur les blessures d'un joueur

## 🌐 Sources de données

- **NBC Sports**: https://www.nbcsports.com/nba/
- **ESPN**: https://www.espn.com/nba/
- **CBS Sports**: https://www.cbssports.com/nba/

## ⚠️ Notes importantes

- Le web scraping peut nécessiter des ajustements si les sites changent leur structure HTML
- Render.com free tier peut mettre le service en veille après 15 min d'inactivité
- Premier chargement après veille peut prendre 30-60 secondes

## 📝 Licence

MIT
