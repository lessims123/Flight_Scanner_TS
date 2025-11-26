"""Modèles de données pour le scanner de vols."""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional


@dataclass
class Flight:
    """Représente un vol avec ses informations principales."""
    
    origin: str
    destination: str
    departure_date: date
    price: float
    airline: str
    departure_time: Optional[str] = None
    arrival_time: Optional[str] = None
    return_date: Optional[date] = None
    return_departure_time: Optional[str] = None
    return_arrival_time: Optional[str] = None
    booking_url: Optional[str] = None
    currency: str = "EUR"
    
    def to_hash(self) -> str:
        """Génère un hash unique pour ce vol (pour éviter les doublons)."""
        import hashlib
        # Inclure la date de retour si présente pour les vols aller-retour
        return_date_str = self.return_date.isoformat() if self.return_date else "oneway"
        key = f"{self.origin}_{self.destination}_{self.departure_date}_{return_date_str}_{self.price}_{self.airline}"
        return hashlib.md5(key.encode()).hexdigest()
    
    def is_round_trip(self) -> bool:
        """Indique si c'est un vol aller-retour."""
        return self.return_date is not None


@dataclass
class Deal:
    """Représente un deal détecté avec les informations de comparaison."""
    
    flight: Flight
    usual_price: float
    discount_percentage: float
    observations_count: int
    
    def __post_init__(self):
        """Valide que le deal respecte les critères."""
        assert self.discount_percentage >= 50.0, "Un deal doit être au moins 50% moins cher"
        assert self.flight.price <= 200.0, "Un deal doit coûter au maximum 200€"

