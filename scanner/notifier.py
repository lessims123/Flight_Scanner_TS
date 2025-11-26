"""Module de notification par email."""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Tuple
from scanner.models import Flight, Deal
from scanner.config import SMTPConfig

logger = logging.getLogger(__name__)


class EmailNotifier:
    """Gestionnaire d'envoi d'emails."""
    
    def __init__(self, config: SMTPConfig):
        """
        Initialise le notifieur email.
        
        Args:
            config: Configuration SMTP
        """
        self.config = config
    
    def _create_email_content(self, deal: Deal) -> Tuple[str, str]:
        """
        Crée le contenu de l'email (texte et HTML).
        
        Args:
            deal: Deal à notifier
            
        Returns:
            Tuple (texte_brut, html)
        """
        flight = deal.flight
        
        # Texte brut
        text = f"""
🎉 NOUVEAU DEAL DE VOL TROUVÉ ! 🎉

Route: {flight.origin} → {flight.destination}
Compagnie: {flight.airline}
Date de départ: {flight.departure_date.strftime('%d/%m/%Y')}
"""
        
        if flight.departure_time:
            text += f"Heure de départ: {flight.departure_time}\n"
        if flight.arrival_time:
            text += f"Heure d'arrivée: {flight.arrival_time}\n"
        
        if flight.is_round_trip():
            text += f"\nDate de retour: {flight.return_date.strftime('%d/%m/%Y')}\n"
            # Calculer la durée du séjour
            stay_duration = (flight.return_date - flight.departure_date).days
            text += f"Durée du séjour: {stay_duration} jour(s)\n"
            if flight.return_departure_time:
                text += f"Heure de départ retour: {flight.return_departure_time}\n"
            if flight.return_arrival_time:
                text += f"Heure d'arrivée retour: {flight.return_arrival_time}\n"
        
        text += f"""
Prix: {flight.price:.2f} {flight.currency}
Prix habituel: ~{deal.usual_price:.2f} {flight.currency}
Réduction: {deal.discount_percentage:.1f}% moins cher !
Nombre d'observations: {deal.observations_count}

"""
        
        if flight.booking_url:
            text += f"Lien de réservation: {flight.booking_url}\n"
        else:
            text += "Recherchez ce vol sur votre site de réservation préféré !\n"
        
        text += "\n---\n"
        text += "Scanner automatique de billets d'avion\n"
        
        # HTML
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .header {{ background-color: #4CAF50; color: white; padding: 20px; text-align: center; }}
        .content {{ padding: 20px; }}
        .deal-box {{ border: 2px solid #4CAF50; border-radius: 5px; padding: 15px; margin: 20px 0; }}
        .price {{ font-size: 24px; color: #4CAF50; font-weight: bold; }}
        .route {{ font-size: 20px; font-weight: bold; margin: 10px 0; }}
        .info {{ margin: 5px 0; }}
        .discount {{ background-color: #ffeb3b; padding: 10px; border-radius: 5px; margin: 10px 0; }}
        .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 30px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🎉 NOUVEAU DEAL DE VOL TROUVÉ ! 🎉</h1>
    </div>
    <div class="content">
        <div class="deal-box">
            <div class="route">{flight.origin} → {flight.destination}</div>
            <div class="price">{flight.price:.2f} {flight.currency}</div>
            <div class="info"><strong>Compagnie:</strong> {flight.airline}</div>
            <div class="info"><strong>Date de départ:</strong> {flight.departure_date.strftime('%d/%m/%Y')}</div>
"""
        
        if flight.departure_time:
            html += f'            <div class="info"><strong>Heure de départ:</strong> {flight.departure_time}</div>\n'
        if flight.arrival_time:
            html += f'            <div class="info"><strong>Heure d\'arrivée:</strong> {flight.arrival_time}</div>\n'
        
        if flight.is_round_trip():
            stay_duration = (flight.return_date - flight.departure_date).days
            html += f'            <div class="info"><strong>Date de retour:</strong> {flight.return_date.strftime("%d/%m/%Y")}</div>\n'
            html += f'            <div class="info"><strong>Durée du séjour:</strong> {stay_duration} jour(s)</div>\n'
            if flight.return_departure_time:
                html += f'            <div class="info"><strong>Heure de départ retour:</strong> {flight.return_departure_time}</div>\n'
            if flight.return_arrival_time:
                html += f'            <div class="info"><strong>Heure d\'arrivée retour:</strong> {flight.return_arrival_time}</div>\n'
        
        html += f"""
            <div class="discount">
                <strong>💰 Économie:</strong> {deal.discount_percentage:.1f}% moins cher que le prix habituel (~{deal.usual_price:.2f} {flight.currency})<br>
                <strong>📊 Observations:</strong> Basé sur {deal.observations_count} observations historiques
            </div>
"""
        
        if flight.booking_url:
            html += f'            <div style="margin-top: 15px;"><a href="{flight.booking_url}" style="background-color: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Réserver maintenant</a></div>\n'
        
        html += """
        </div>
    </div>
    <div class="footer">
        <p>Scanner automatique de billets d'avion</p>
    </div>
</body>
</html>
"""
        
        return text, html
    
    async def send_notification(self, deal: Deal) -> bool:
        """
        Envoie une notification email pour un deal.
        
        Args:
            deal: Deal à notifier
            
        Returns:
            True si l'envoi a réussi, False sinon
        """
        try:
            text, html = self._create_email_content(deal)
            
            # Créer le message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"🎉 Deal vol: {deal.flight.origin} → {deal.flight.destination} à {deal.flight.price:.2f}€"
            msg["From"] = self.config.from_email
            msg["To"] = self.config.to_email
            
            # Ajouter les parties texte et HTML
            part1 = MIMEText(text, "plain", "utf-8")
            part2 = MIMEText(html, "html", "utf-8")
            
            msg.attach(part1)
            msg.attach(part2)
            
            # Envoyer l'email
            with smtplib.SMTP(self.config.host, self.config.port) as server:
                if self.config.use_tls:
                    server.starttls()
                server.login(self.config.user, self.config.password)
                server.sendmail(self.config.from_email, [self.config.to_email], msg.as_string())
            
            logger.info(f"Email envoyé pour deal: {deal.flight.origin} -> {deal.flight.destination}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi de l'email: {e}")
            return False

