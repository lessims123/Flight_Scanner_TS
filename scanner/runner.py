"""Runner principal du scanner."""

import asyncio
import logging
from datetime import date, timedelta
from typing import List, Tuple
from scanner.config import ScannerConfig
from scanner.providers.amadeus import AmadeusFlightProvider
from scanner.storage import Storage
from scanner.deal_detector import DealDetector
from scanner.notifier import EmailNotifier
from scanner.models import Flight

logger = logging.getLogger(__name__)


class ScannerRunner:
    """Runner principal qui orchestre le scan de vols."""
    
    def __init__(self, config: ScannerConfig):
        """
        Initialise le runner.
        
        Args:
            config: Configuration du scanner
        """
        self.config = config
        self.provider = AmadeusFlightProvider(config.amadeus)
        self.storage = Storage(config.db_path)
        self.detector = DealDetector(self.storage, config)
        self.notifier = EmailNotifier(config.smtp)
        self._running = False
    
    async def initialize(self):
        """Initialise tous les composants."""
        logger.info("Initialisation du scanner...")
        await self.storage.init_db()
        logger.info("Scanner initialisé")
    
    async def cleanup(self):
        """Nettoie les ressources."""
        await self.provider.close()
        logger.info("Nettoyage terminé")
    
    def _generate_date_pairs(self) -> List[Tuple[date, date]]:
        """
        Génère la liste des paires de dates (départ, retour) à scanner.
        Pour chaque date de départ, génère plusieurs dates de retour avec séjour minimum.
        
        Returns:
            Liste de tuples (date_départ, date_retour) dans la plage configurée
        """
        today = date.today()
        date_pairs = []
        
        # Générer une date de départ par semaine pour éviter trop de requêtes
        current_departure = today + timedelta(days=self.config.min_days_from_now)
        max_departure_date = today + timedelta(days=self.config.max_days_from_now)
        
        while current_departure <= max_departure_date:
            # Pour chaque date de départ, générer plusieurs dates de retour
            # avec séjour entre min_stay_days et max_stay_days
            for stay_days in range(
                self.config.min_stay_days,
                min(self.config.max_stay_days + 1, 15)  # Limiter à 15 jours max pour éviter trop de combinaisons
            ):
                return_date = current_departure + timedelta(days=stay_days)
                
                # Vérifier que la date de retour ne dépasse pas max_days_from_now
                if return_date <= max_departure_date:
                    date_pairs.append((current_departure, return_date))
            
            current_departure += timedelta(days=7)  # Une date de départ par semaine
        
        return date_pairs
    
    async def scan_route(
        self,
        origin: str,
        destination: str,
        departure_date: date,
        return_date: date
    ) -> List[Flight]:
        """
        Scanne une route spécifique pour des dates aller-retour données.
        
        Args:
            origin: Code IATA de l'origine
            destination: Code IATA de la destination
            departure_date: Date de départ
            return_date: Date de retour
            
        Returns:
            Liste de vols trouvés (aller-retour uniquement)
        """
        try:
            logger.debug(
                f"Scan aller-retour: {origin} -> {destination} "
                f"du {departure_date} au {return_date}"
            )
            flights = await self.provider.search_flights(
                origin=origin,
                destination=destination,
                departure_date=departure_date,
                return_date=return_date,
                max_price=self.config.max_price
            )
            
            # Filtrer pour ne garder que les vols aller-retour
            round_trip_flights = [f for f in flights if f.is_round_trip()]
            
            # Stocker tous les prix dans l'historique
            for flight in round_trip_flights:
                await self.storage.store_price(flight)
            
            return round_trip_flights
            
        except Exception as e:
            logger.error(f"Erreur lors du scan {origin}->{destination}: {e}")
            return []
    
    async def scan_cycle(self):
        """Effectue un cycle complet de scan."""
        logger.info("Début d'un cycle de scan (aller-retour uniquement)")
        
        date_pairs = self._generate_date_pairs()
        all_flights = []
        
        # Scanner toutes les combinaisons origine × destination × (départ, retour)
        for origin in self.config.origins:
            for destination in self.config.destinations:
                for departure_date, return_date in date_pairs:
                    flights = await self.scan_route(
                        origin, destination, departure_date, return_date
                    )
                    all_flights.extend(flights)
                    
                    # Petite pause pour éviter de surcharger l'API
                    await asyncio.sleep(1)
        
        logger.info(f"Scan terminé: {len(all_flights)} vols trouvés")
        
        # Détecter les deals
        deals = await self.detector.detect_deals(all_flights)
        logger.info(f"{len(deals)} deals détectés")
        
        # Notifier les nouveaux deals
        notified_count = 0
        for deal in deals:
            flight_hash = deal.flight.to_hash()
            
            # Vérifier si déjà notifié
            if await self.storage.is_deal_notified(flight_hash):
                logger.debug(f"Deal déjà notifié: {deal.flight.origin}->{deal.flight.destination}")
                continue
            
            # Envoyer la notification
            success = await self.notifier.send_notification(deal)
            if success:
                await self.storage.mark_deal_as_notified(
                    deal.flight,
                    deal.usual_price,
                    deal.discount_percentage
                )
                notified_count += 1
        
        logger.info(f"{notified_count} nouveaux deals notifiés")
    
    async def run(self):
        """Lance le scanner en boucle continue."""
        self._running = True
        logger.info("Démarrage du scanner en mode continu")
        
        try:
            while self._running:
                try:
                    await self.scan_cycle()
                except Exception as e:
                    logger.error(f"Erreur lors d'un cycle de scan: {e}", exc_info=True)
                
                # Attendre avant le prochain cycle
                logger.info(
                    f"Attente de {self.config.scan_interval_seconds} secondes "
                    f"avant le prochain cycle..."
                )
                await asyncio.sleep(self.config.scan_interval_seconds)
                
        except KeyboardInterrupt:
            logger.info("Arrêt demandé par l'utilisateur")
        finally:
            self._running = False
            await self.cleanup()
    
    def stop(self):
        """Arrête le scanner."""
        self._running = False
        logger.info("Arrêt du scanner demandé")

