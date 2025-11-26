# Guide de démarrage rapide

## Installation en 5 minutes

### 1. Prérequis
- Python 3.11+
- Compte Amadeus (gratuit sur https://developers.amadeus.com)
- Compte email avec SMTP

### 2. Installation

```bash
# Créer l'environnement virtuel
python3 -m venv venv
source venv/bin/activate  # Sur Windows: venv\Scripts\activate

# Installer les dépendances
pip install -r requirements.txt
```

### 3. Configuration

Créez un fichier `.env` à la racine du projet :

```env
AMADEUS_API_KEY=votre_clé
AMADEUS_API_SECRET=votre_secret
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=votre_email@gmail.com
SMTP_PASSWORD=votre_app_password
SMTP_USE_TLS=true
EMAIL_FROM=votre_email@gmail.com
EMAIL_TO=destinataire@example.com
```

### 4. Lancer

```bash
python main.py
```

## Configuration Gmail

Pour utiliser Gmail, vous devez :

1. Activer la validation en 2 étapes sur votre compte Google
2. Générer un "App Password" :
   - Allez sur https://myaccount.google.com/apppasswords
   - Créez un mot de passe pour "Mail"
   - Utilisez ce mot de passe dans `SMTP_PASSWORD`

## Première exécution

Lors de la première exécution, le scanner va :
- Créer la base de données SQLite (`flights.db`)
- Rechercher uniquement des **billets aller-retour** avec un séjour minimum de 3 jours
- Commencer à collecter des données de prix
- **Ne pas envoyer de deals immédiatement** (il faut au moins 10 observations par route)

Attendez quelques cycles de scan avant de recevoir les premiers deals.

## Personnalisation

Éditez `config.yaml` pour :
- Modifier les destinations
- Ajuster la durée du séjour (`min_stay_days` et `max_stay_days`)
- Ajuster le prix maximum
- Changer l'intervalle de scan

