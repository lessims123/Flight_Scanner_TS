"""Logique de détection des deals."""

import logging
from datetime import date
from typing import List, Optional
from scanner.models import Flight, Deal
from scanner.storage import Storage
from scanner.config import ScannerConfig

logger = logging.getLogger(__name__)


class DealDetector:
    """Détecte les deals selon les critères définis."""
    
    def __init__(self, storage: Storage, config: ScannerConfig):
        """
        Initialise le détecteur de deals.
        
        Args:
            storage: Gestionnaire de stockage
            config: Configuration du scanner
        """
        self.storage = storage
        self.config = config
    
    async def detect_deals(self, flights: List[Flight]) -> List[Deal]:
        """
        Détecte les deals parmi une liste de vols.
        
        Args:
            flights: Liste de vols à analyser
            
        Returns:
            Liste de deals détectés
        """
        deals = []
        
        for flight in flights:
            # Ne traiter que les vols aller-retour
            if not flight.is_round_trip():
                logger.debug(f"Vol aller simple ignoré: {flight.origin}->{flight.destination}")
                continue
            
            # Vérifier si c'est une destination asiatique avec escale
            is_asia_with_stopover = (
                flight.destination in self.config.asia_destinations 
                and flight.has_stopover
            )
            
            # Filtre prix maximum (sauf pour vols avec escales vers Asie)
            if not is_asia_with_stopover and flight.price > self.config.max_price:
                continue
            
            # Vérifier si on a assez d'historique
            observations = await self.storage.get_observations_count(
                flight.origin,
                flight.destination,
                flight.departure_date.month,
                flight.departure_date.year
            )
            
            if observations < self.config.min_observations:
                logger.debug(
                    f"Pas assez d'observations pour {flight.origin}->{flight.destination} "
                    f"({observations} < {self.config.min_observations})"
                )
                continue
            
            # Calculer le prix habituel (médian pour être plus robuste aux outliers)
            usual_price = await self.storage.get_median_price(
                flight.origin,
                flight.destination,
                flight.departure_date.month,
                flight.departure_date.year
            )
            
            # Si pas de prix habituel, essayer sans filtre mois/année
            if usual_price is None:
                usual_price = await self.storage.get_median_price(
                    flight.origin,
                    flight.destination
                )
            
            if usual_price is None:
                logger.debug(f"Pas de prix habituel pour {flight.origin}->{flight.destination}")
                continue
            
            # Vérifier si c'est un deal (au moins 50% moins cher)
            discount_ratio = 1 - (flight.price / usual_price)
            discount_percentage = discount_ratio * 100
            
            if discount_percentage >= (self.config.discount_threshold * 100):
                deal = Deal(
                    flight=flight,
                    usual_price=usual_price,
                    discount_percentage=discount_percentage,
                    observations_count=observations
                )
                deals.append(deal)
                deal_type = "avec escale (Asie)" if is_asia_with_stopover else "direct"
                logger.info(
                    f"Deal détecté ({deal_type}): {flight.origin}->{flight.destination} "
                    f"à {flight.price}€ (habituel: {usual_price}€, "
                    f"réduction: {discount_percentage:.1f}%)"
                )
        
        return deals

