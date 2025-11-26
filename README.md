# Scanner Automatique de Billets d'Avion

Un scanner automatique de billets d'avion qui surveille les prix depuis Paris vers le monde entier et envoie des notifications par email lorsqu'un deal est détecté (au moins 50% moins cher que le prix habituel, maximum 200€).

## 🎯 Fonctionnalités

- **Scan automatique** : Recherche continue de vols **aller-retour** depuis Paris (CDG, ORY, BVA) vers des destinations mondiales
- **Séjour minimum** : Recherche uniquement des billets aller-retour avec un séjour minimum de 3 jours (configurable)
- **Détection intelligente** : Identifie les deals réels (au moins 50% moins cher que le prix habituel)
- **Historique des prix** : Stocke l'historique dans SQLite pour calculer les prix habituels
- **Notifications email** : Envoie des emails HTML avec tous les détails des deals (dates aller-retour, durées de séjour)
- **Évite les doublons** : Ne notifie qu'une seule fois chaque deal
- **Asynchrone** : Utilise asyncio pour des performances optimales
- **Production-ready** : Prêt à déployer sur un VPS Linux

## 📋 Prérequis

- Python 3.11 ou supérieur
- **Travelpayouts API Token** : Gratuit avec quotas généreux ([travelpayouts.com](https://www.travelpayouts.com))
- Compte email avec accès SMTP (Gmail, Outlook, etc.)

## 🚀 Installation

### 1. Cloner ou télécharger le projet

```bash
cd scanner
```

### 2. Créer un environnement virtuel

```bash
# Sur Linux/Mac
python3 -m venv venv
source venv/bin/activate

# Sur Windows
python -m venv venv
venv\Scripts\activate
```

### 3. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 4. Configurer les variables d'environnement

Copiez le fichier `.env.example` vers `.env` et remplissez vos identifiants :

```bash
# Sur Linux/Mac
cp .env.example .env

# Sur Windows
copy .env.example .env
```

Éditez `.env` avec vos informations :

```env
# Configuration Travelpayouts API
# Obtenez votre token gratuit sur https://www.travelpayouts.com
TRAVELPAYOUTS_API_TOKEN=votre_token_api

# Configuration SMTP
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=votre_email@gmail.com
SMTP_PASSWORD=votre_mot_de_passe_app  # Pour Gmail, utilisez un "App Password"
SMTP_USE_TLS=true

# Adresses email
EMAIL_FROM=votre_email@gmail.com
EMAIL_TO=destinataire@example.com
```

**Note pour Gmail** : Vous devez créer un "App Password" dans les paramètres de sécurité de votre compte Google. Le mot de passe normal ne fonctionnera pas.

### 5. (Optionnel) Personnaliser la configuration

Éditez `config.yaml` pour modifier :
- Les aéroports d'origine
- Les destinations à scanner
- La plage de dates
- Le prix maximum
- Le seuil de réduction
- L'intervalle entre les scans

## 🏃 Utilisation

### Lancer le scanner manuellement

```bash
python main.py
```

Le scanner va :
1. S'authentifier auprès de l'API Travelpayouts
2. Scanner toutes les routes configurées
3. Stocker les prix dans la base de données
4. Détecter les deals
5. Envoyer des emails pour les nouveaux deals
6. Attendre l'intervalle configuré avant de recommencer

### Arrêter le scanner

Appuyez sur `Ctrl+C` pour arrêter proprement le scanner.

## 📦 Déploiement sur VPS Linux

### 1. Installer Python 3.11+

```bash
# Sur Ubuntu/Debian
sudo apt update
sudo apt install python3.11 python3.11-venv python3-pip

# Vérifier l'installation
python3.11 --version
```

### 2. Cloner le projet

```bash
git clone <votre-repo> scanner
cd scanner
```

### 3. Créer et activer l'environnement virtuel

```bash
python3.11 -m venv venv
source venv/bin/activate
```

### 4. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 5. Configurer `.env`

```bash
nano .env
# Remplir avec vos identifiants Travelpayouts et SMTP
```

### 6. Tester le lancement

```bash
python main.py
```

Si tout fonctionne, arrêtez avec `Ctrl+C`.

### 7. Créer un service systemd (recommandé)

Créez un fichier `/etc/systemd/system/flight-scanner.service` :

```ini
[Unit]
Description=Flight Deal Scanner
After=network.target

[Service]
Type=simple
User=votre_utilisateur
WorkingDirectory=/chemin/vers/scanner
Environment="PATH=/chemin/vers/scanner/venv/bin"
ExecStart=/chemin/vers/scanner/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Remplacez :
- `votre_utilisateur` par votre nom d'utilisateur Linux
- `/chemin/vers/scanner` par le chemin absolu vers votre projet

Activer et démarrer le service :

```bash
sudo systemctl daemon-reload
sudo systemctl enable flight-scanner
sudo systemctl start flight-scanner
```

Vérifier le statut :

```bash
sudo systemctl status flight-scanner
```

Voir les logs :

```bash
sudo journalctl -u flight-scanner -f
```

### 8. Alternative : Utiliser cron (plus simple mais moins robuste)

Éditez le crontab :

```bash
crontab -e
```

Ajoutez une ligne pour lancer le scanner toutes les heures :

```cron
0 * * * * cd /chemin/vers/scanner && /chemin/vers/scanner/venv/bin/python main.py >> /chemin/vers/scanner/cron.log 2>&1
```

## 📊 Structure du projet

```
scanner/
├── scanner/
│   ├── __init__.py
│   ├── config.py          # Gestion de la configuration
│   ├── models.py           # Modèles de données (Flight, Deal)
│   ├── storage.py          # Gestion SQLite
│   ├── deal_detector.py    # Logique de détection de deals
│   ├── notifier.py         # Envoi d'emails
│   ├── runner.py           # Orchestrateur principal
│   └── providers/
│       ├── __init__.py
│       ├── base.py         # Interface FlightProvider
│       └── travelpayouts.py # Implémentation Travelpayouts
├── tests/
│   ├── test_deal_detector.py
│   └── test_storage.py
├── main.py                 # Point d'entrée
├── config.yaml             # Configuration YAML
├── .env                    # Variables d'environnement (à créer)
├── .env.example            # Exemple de .env
├── requirements.txt        # Dépendances Python
├── .gitignore
└── README.md
```

## 🧪 Tests

Lancer les tests :

```bash
pytest tests/
```

## ⚙️ Configuration avancée

### Modifier les destinations

Éditez `config.yaml` et modifiez la liste `destinations` avec les codes IATA souhaités.

### Configurer la durée du séjour (aller-retour)

Dans `config.yaml` :
- `min_stay_days` : Séjour minimum en jours (défaut: 3 jours)
- `max_stay_days` : Séjour maximum en jours (défaut: 30 jours)

Le scanner recherche uniquement des billets aller-retour avec une durée de séjour entre ces deux valeurs.

### Ajuster les critères de deals

Dans `config.yaml` :
- `max_price` : Prix maximum pour un deal (défaut: 200€)
- `discount_threshold` : Seuil de réduction (0.5 = 50%, défaut: 0.5)
- `min_observations` : Nombre minimum d'observations avant de notifier (défaut: 10)

### Changer l'intervalle de scan

Modifiez `scan_interval_seconds` dans `config.yaml` :
- `3600` = 1 heure
- `7200` = 2 heures
- `1800` = 30 minutes

## 📝 Logs

Les logs sont écrits dans :
- Console (stdout)
- Fichier `scanner.log` (configurable dans `config.yaml`)

Niveaux de log : INFO, WARNING, ERROR

## 🔧 Dépannage

### Erreur d'authentification API

- Vérifiez que `TRAVELPAYOUTS_API_TOKEN` est correct dans `.env`
- Obtenez votre token gratuit sur [travelpayouts.com](https://www.travelpayouts.com)

### Erreur d'envoi d'email

- Pour Gmail : Utilisez un "App Password" (pas le mot de passe normal)
- Vérifiez que `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` sont corrects
- Testez la connexion SMTP avec un client email externe

### Pas de deals détectés

- Le scanner a besoin de temps pour accumuler de l'historique (minimum `min_observations` observations)
- Vérifiez que les prix trouvés sont bien inférieurs à `max_price`
- Vérifiez que les réductions sont bien supérieures à `discount_threshold * 100%`

### Le scanner consomme trop de requêtes API

- Augmentez `scan_interval_seconds` dans `config.yaml`
- Réduisez le nombre de destinations
- Réduisez la plage de dates (`max_days_from_now`)

## 📄 Licence

Ce projet est fourni tel quel, sans garantie.

## 🤝 Contribution

Les contributions sont les bienvenues ! N'hésitez pas à ouvrir une issue ou une pull request.

## 📧 Support

Pour toute question ou problème, consultez la documentation Travelpayouts : [travelpayouts.github.io](https://travelpayouts.github.io/slate/)

