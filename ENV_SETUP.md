# Configuration des variables d'environnement

Créez un fichier `.env` à la racine du projet avec le contenu suivant :

```env
# Configuration Amadeus API
# Obtenez vos clés sur https://developers.amadeus.com
AMADEUS_API_KEY=RmWCnnKFmjfmb0SyICBsXHuajcgvkfvy
AMADEUS_API_SECRET=NE4jRUhIUZ6qyNxo

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

1. **Amadeus API** : Les clés fournies sont déjà dans le fichier, mais vous pouvez les remplacer par les vôtres si nécessaire.

2. **Gmail** : Pour utiliser Gmail, vous devez :
   - Activer la validation en 2 étapes
   - Créer un "App Password" sur https://myaccount.google.com/apppasswords
   - Utiliser ce mot de passe (pas votre mot de passe normal)

3. **Autres fournisseurs SMTP** :
   - **Outlook/Hotmail** : `smtp-mail.outlook.com`, port `587`
   - **Yahoo** : `smtp.mail.yahoo.com`, port `587`
   - **Autres** : Consultez la documentation de votre fournisseur

4. Le fichier `.env` est ignoré par git (dans `.gitignore`) pour des raisons de sécurité.

