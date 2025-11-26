# Architecture du projet

## Vue d'ensemble

Le scanner de vols est construit avec une architecture modulaire et asynchrone, permettant une maintenance facile et une extensibilité.

## Structure des modules

### `scanner/models.py`
- **Flight** : Modèle de données représentant un vol avec toutes ses informations
- **Deal** : Modèle représentant un deal détecté avec les métriques de comparaison

### `scanner/config.py`
- **ScannerConfig** : Configuration principale du scanner
- **TravelpayoutsConfig** : Configuration pour l'API Travelpayouts
- **SMTPConfig** : Configuration pour l'envoi d'emails
- Charge la configuration depuis `config.yaml` et `.env`

### `scanner/providers/`
- **base.py** : Interface `FlightProvider` (Protocol)
- **travelpayouts.py** : Implémentation Travelpayouts avec :
  - Authentification par token simple
  - Conversion automatique RUB → EUR
  - Parsing des réponses API
  - Normalisation en objets `Flight`

### `scanner/storage.py`
- **Storage** : Gestionnaire SQLite avec :
  - Stockage de l'historique des prix
  - Calcul de prix moyen/médian
  - Suivi des deals notifiés (évite les doublons)
  - Requêtes optimisées avec index

### `scanner/deal_detector.py`
- **DealDetector** : Logique de détection de deals :
  - Filtre par prix maximum
  - Vérifie le nombre minimum d'observations
  - Calcule le prix habituel (médian)
  - Vérifie le seuil de réduction (50%)

### `scanner/notifier.py`
- **EmailNotifier** : Envoi d'emails :
  - Génération de contenu texte et HTML
  - Support SMTP avec TLS
  - Emails formatés avec tous les détails

### `scanner/runner.py`
- **ScannerRunner** : Orchestrateur principal :
  - Génération des dates à scanner
  - Scan de toutes les routes (origine × destination × date)
  - Détection et notification des deals
  - Boucle continue avec intervalle configurable

## Flux d'exécution

```
main.py
  └─> ScannerRunner.initialize()
      └─> Storage.init_db()
  
  └─> ScannerRunner.run()
      └─> Boucle infinie:
          └─> ScannerRunner.scan_cycle()
              ├─> Pour chaque (origine, destination, date):
              │   └─> TravelpayoutsFlightProvider.search_flights()
              │       ├─> Authentification par token
              │       └─> Appel API Travelpayouts
              │
              └─> Storage.store_price() (pour chaque vol)
              
              └─> DealDetector.detect_deals()
                  ├─> Filtre prix < max_price
                  ├─> Vérifie min_observations
                  ├─> Calcule prix habituel (médian)
                  └─> Vérifie discount >= 50%
              
              └─> Pour chaque deal:
                  ├─> Storage.is_deal_notified() ?
                  └─> Si nouveau:
                      ├─> EmailNotifier.send_notification()
                      └─> Storage.mark_deal_as_notified()
              
              └─> Attendre scan_interval_seconds
```

## Base de données SQLite

### Table `price_history`
Stocke l'historique des prix pour calculer les prix habituels :
- `origin`, `destination` : Codes IATA
- `departure_date`, `departure_month`, `departure_year` : Dates
- `price`, `airline`, `currency` : Informations du vol
- Index sur `(origin, destination, departure_month, departure_year)`

### Table `notified_deals`
Évite les doublons de notifications :
- `flight_hash` : Hash unique du vol (PRIMARY KEY)
- `origin`, `destination`, `departure_date`, `price` : Informations du deal
- `usual_price`, `discount_percentage` : Métriques

## Gestion des erreurs

- **Authentification API** : Token Travelpayouts simple, pas de refresh nécessaire
- **Erreurs API** : Loggées, le scanner continue
- **Erreurs email** : Loggées, le deal n'est pas marqué comme notifié (sera réessayé au prochain cycle)
- **Erreurs de stockage** : Loggées, le scanner continue

## Extensibilité

### Ajouter un nouveau provider

1. Implémenter l'interface `FlightProvider` dans `scanner/providers/`
2. Adapter le parsing pour retourner des objets `Flight`
3. Modifier `ScannerRunner` pour utiliser le nouveau provider

### Modifier les critères de deals

Éditer `config.yaml` :
- `max_price` : Prix maximum
- `discount_threshold` : Seuil de réduction (0.5 = 50%)
- `min_observations` : Nombre minimum d'observations

### Ajouter d'autres notifications

Créer un nouveau module `scanner/notifiers/` et implémenter une interface commune.

## Performance

- **Asynchrone** : Utilise `asyncio` et `aiohttp` pour des requêtes parallèles
- **Base de données** : Index sur les colonnes fréquemment interrogées
- **Rate limiting** : Pause de 1 seconde entre chaque requête API
- **Génération de dates** : Une date par semaine pour réduire le nombre de requêtes

## Sécurité

- Les identifiants sensibles sont dans `.env` (ignoré par git)
- Le token Travelpayouts est géré automatiquement
- Les mots de passe SMTP ne sont jamais loggés

