"""Interface de base pour les providers de vols."""

from typing import Protocol, Optional
from datetime import date
from scanner.models import Flight


class FlightProvider(Protocol):
    """Interface pour les providers de vols."""
    
    async def search_flights(
        self,
        origin: str,
        destination: str,
        departure_date: date,
        return_date: Optional[date] = None
    ) -> list[Flight]:
        """
        Recherche des vols pour une route et une date donnée.
        
        Args:
            origin: Code IATA de l'aéroport d'origine
            destination: Code IATA de l'aéroport de destination
            departure_date: Date de départ
            return_date: Date de retour (optionnel, pour aller-retour)
            
        Returns:
            Liste de vols trouvés
        """
        ...

