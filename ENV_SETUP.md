# Configuration des variables d'environnement

Créez un fichier `.env` à la racine du projet avec le contenu suivant :

```env
# Configuration Travelpayouts API
# Obtenez votre token gratuit sur https://www.travelpayouts.com
TRAVELPAYOUTS_API_TOKEN=votre_token_api

# Configuration SMTP pour les notifications email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password_here
SMTP_USE_TLS=true

# Adresses email
EMAIL_FROM=your_email@gmail.com
EMAIL_TO=recipient@example.com
```

## Notes importantes

1. **Travelpayouts API** : Gratuit avec quotas généreux, modèle d'affiliation. Obtenez votre token sur [travelpayouts.com](https://www.travelpayouts.com)

2. **Gmail** : Pour utiliser Gmail, vous devez :
   - Activer la validation en 2 étapes
   - Créer un "App Password" sur https://myaccount.google.com/apppasswords
   - Utiliser ce mot de passe (pas votre mot de passe normal)

3. **Autres fournisseurs SMTP** :
   - **Outlook/Hotmail** : `smtp-mail.outlook.com`, port `587`
   - **Yahoo** : `smtp.mail.yahoo.com`, port `587`
   - **Autres** : Consultez la documentation de votre fournisseur

4. Le fichier `.env` est ignoré par git (dans `.gitignore`) pour des raisons de sécurité.

