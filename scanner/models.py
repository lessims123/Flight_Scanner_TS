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
    has_stopover: bool = False  # Indique si le vol a des escales
    stopovers: Optional[str] = None  # Liste des aéroports d'escale (ex: "DXB, DOH")
    
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
        # Pour les vols avec escales vers l'Asie, pas de limite de prix
        # Pour les autres, limite à 200€
        is_asia_with_stopover = self._is_asia_destination() and self.flight.has_stopover
        if not is_asia_with_stopover:
            assert self.flight.price <= 200.0, "Un deal doit coûter au maximum 200€ (sauf vols avec escales vers l'Asie)"
    
    def _is_asia_destination(self) -> bool:
        """Vérifie si la destination est en Asie."""
        asia_codes = {
            "BKK", "SIN", "HKG", "NRT", "HND", "ICN", "PEK", "PVG", "CAN", "KUL", 
            "MNL", "JKT", "HAN", "SGN", "BOM", "DEL", "BLR", "MAA", "DPS", "CGK",
            "TPE", "KHH", "OKA", "FUK", "KIX", "NGO", "CTS", "GMP", "PUS", "CJU",
            "BJS", "SHA", "CAN", "CTU", "XIY", "KMG", "XMN", "SZX", "DLC", "TSN",
            "CCU", "HYD", "COK", "CCJ", "TRV", "GAU", "AMD", "PNQ", "IXC", "LKO",
            "VNS", "PAT", "RPR", "IDR", "JAI", "UDR", "BDQ", "RAJ", "BHO", "GAY",
            "BBI", "VTZ", "IXZ", "IXE", "HBX", "IXU", "NAG", "JLR", "RJA", "TIR",
            "VGA", "BZA", "CJB", "IXM", "IXJ", "IXL", "IXP", "IXR", "IXS", "IXW",
            "JDH", "JGB", "JLR", "JRH", "JSA", "JSH", "JSR", "JTR", "JUB", "JUI"
        }
        return self.flight.destination in asia_codes

