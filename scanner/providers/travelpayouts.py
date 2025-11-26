"""Provider Travelpayouts pour la recherche de vols."""

import aiohttp
import logging
import asyncio
from datetime import date, datetime
from typing import List, Optional
from scanner.models import Flight
from scanner.config import TravelpayoutsConfig

logger = logging.getLogger(__name__)


class TravelpayoutsFlightProvider:
    """Provider pour l'API Travelpayouts/Aviasales."""
    
    def __init__(self, config: TravelpayoutsConfig):
        """
        Initialise le provider Travelpayouts.
        
        Args:
            config: Configuration Travelpayouts avec API token
        """
        self.config = config
        self._session: Optional[aiohttp.ClientSession] = None
        self._rate_limit_remaining = 300  # Limite par défaut (300 req/min)
        self._rate_limit_reset = None  # Timestamp de réinitialisation
        self._last_request_time = 0.0  # Pour respecter le délai minimum
        self._request_lock = asyncio.Lock()  # Lock pour synchroniser les requêtes
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Obtient ou crée une session HTTP."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session
    
    async def close(self):
        """Ferme la session HTTP."""
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def search_flights(
        self,
        origin: str,
        destination: str,
        departure_date: date,
        return_date: Optional[date] = None,
        max_price: Optional[float] = None
    ) -> List[Flight]:
        """
        Recherche des vols sur une route donnée.
        
        Note: L'API Travelpayouts utilise des dates au format mois (YYYY-MM),
        donc on recherche pour le mois de départ/retour.
        
        Args:
            origin: Code IATA de l'aéroport d'origine
            destination: Code IATA de l'aéroport de destination
            departure_date: Date de départ (utilisée pour déterminer le mois)
            return_date: Date de retour (optionnel, utilisée pour déterminer le mois)
            max_price: Prix maximum en EUR (optionnel, filtré après réception)
            
        Returns:
            Liste de vols trouvés
        """
        try:
            session = await self._get_session()
            url = f"{self.config.base_url}{self.config.flight_offers_url}"
            
            headers = {
                "X-Access-Token": self.config.api_token
            }
            
            # Travelpayouts utilise le format mois (YYYY-MM)
            depart_month = departure_date.strftime("%Y-%m")
            return_month = return_date.strftime("%Y-%m") if return_date else None
            
            params = {
                "origin": origin,
                "destination": destination,
                "depart_date": depart_month
            }
            
            if return_month:
                params["return_date"] = return_month
            
            # Gestion du rate limiting avec retry et backoff
            max_retries = 3
            retry_delay = 2.0  # Délai initial en secondes (augmenté)
            
            async with self._request_lock:
                # Respecter un délai minimum entre requêtes (300 req/min = 1 req toutes les 0.2s)
                # On met 0.25s pour avoir une marge
                current_time = asyncio.get_event_loop().time()
                time_since_last = current_time - self._last_request_time
                min_delay = 0.25  # 240 req/min max pour être sûr
                if time_since_last < min_delay:
                    await asyncio.sleep(min_delay - time_since_last)
                self._last_request_time = asyncio.get_event_loop().time()
            
            for attempt in range(max_retries):
                # Vérifier les headers de rate limit de la réponse précédente
                if self._rate_limit_remaining <= 20:
                    wait_time = 60.0  # Attendre 1 minute si on approche de la limite
                    logger.warning(f"Rate limit faible ({self._rate_limit_remaining}), attente de {wait_time}s")
                    await asyncio.sleep(wait_time)
                    self._rate_limit_remaining = 300  # Réinitialiser après l'attente
                
                async with session.get(url, headers=headers, params=params) as response:
                    # Lire les headers de rate limit
                    if "X-Rate-Limit-Remaining" in response.headers:
                        try:
                            self._rate_limit_remaining = int(response.headers["X-Rate-Limit-Remaining"])
                        except:
                            pass
                    
                    if "X-Rate-Limit-Reset" in response.headers:
                        try:
                            self._rate_limit_reset = int(response.headers["X-Rate-Limit-Reset"])
                        except:
                            pass
                    
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_flights(
                            data, origin, destination, departure_date, return_date, max_price
                        )
                    elif response.status == 429:
                        # Rate limit dépassé - backoff exponentiel
                        retry_after = retry_delay * (2 ** attempt)
                        logger.warning(
                            f"Rate limit dépassé (429) pour {origin}->{destination}, "
                            f"attente de {retry_after:.1f}s avant retry {attempt + 1}/{max_retries}"
                        )
                        await asyncio.sleep(retry_after)
                        continue  # Réessayer
                    elif response.status == 401:
                        logger.error("Token Travelpayouts invalide ou expiré")
                        return []
                    else:
                        error_text = await response.text()
                        logger.error(f"Erreur API Travelpayouts: {response.status} - {error_text}")
                        return []
            
            # Si on arrive ici, tous les retries ont échoué
            logger.error(f"Échec après {max_retries} tentatives pour {origin}->{destination}")
            return []
        except Exception as e:
            logger.error(f"Erreur lors de la recherche de vols Travelpayouts: {e}")
            return []
    
    def _parse_flights(
        self,
        data: dict,
        origin: str,
        destination: str,
        departure_date: date,
        return_date: Optional[date],
        max_price: Optional[float]
    ) -> List[Flight]:
        """
        Parse les données JSON de Travelpayouts en objets Flight.
        
        Args:
            data: Réponse JSON de l'API Travelpayouts
            origin: Origine du vol
            destination: Destination du vol
            departure_date: Date de départ souhaitée
            return_date: Date de retour souhaitée (optionnel)
            max_price: Prix maximum (filtre)
            
        Returns:
            Liste de vols parsés
        """
        flights = []
        
        try:
            # Taux de change approximatif RUB -> EUR (à mettre à jour régulièrement)
            # 1 EUR ≈ 100 RUB (approximatif, devrait être récupéré dynamiquement)
            RUB_TO_EUR_RATE = 0.01
            
            # Récupérer la devise de la réponse
            response_currency = data.get("currency", "rub").lower()
            currency_multiplier = RUB_TO_EUR_RATE if response_currency == "rub" else 1.0
            
            # Structure réelle: data[destination][index] = {flight_data}
            # Exemple: {"data": {"LON": {"0": {...}}}}
            data_section = data.get("data", {})
            
            # Parcourir les données par destination
            dest_data = data_section.get(destination, {})
            
            if not isinstance(dest_data, dict):
                logger.debug(f"Format de données inattendu pour {destination}")
                return flights
            
            # Parcourir tous les vols pour cette destination
            for key, offer in dest_data.items():
                try:
                    # Prix (convertir en EUR si nécessaire)
                    price_raw = float(offer.get("price", 0))
                    price_eur = price_raw * currency_multiplier
                    
                    # Filtrer par prix max si spécifié
                    if max_price and price_eur > max_price:
                        continue
                    
                    # Compagnie aérienne
                    airline = offer.get("airline", "Unknown")
                    
                    # Dates et heures
                    departure_at = offer.get("departure_at")
                    return_at = offer.get("return_at")
                    
                    # Parser les dates
                    parsed_depart_date = departure_date
                    parsed_return_date = return_date
                    departure_time = None
                    return_departure_time = None
                    return_arrival_time = None
                    
                    if departure_at:
                        try:
                            # Format: "2025-12-16T10:05:00+01:00" ou "2025-12-16T10:05:00Z"
                            dt = datetime.fromisoformat(departure_at.replace("Z", "+00:00"))
                            parsed_depart_date = dt.date()
                            departure_time = dt.strftime("%H:%M")
                        except Exception as e:
                            logger.debug(f"Erreur parsing date départ: {e}")
                    
                    if return_at:
                        try:
                            dt = datetime.fromisoformat(return_at.replace("Z", "+00:00"))
                            parsed_return_date = dt.date()
                            return_departure_time = dt.strftime("%H:%M")
                            return_arrival_time = dt.strftime("%H:%M")  # Même heure pour simplifier
                        except Exception as e:
                            logger.debug(f"Erreur parsing date retour: {e}")
                    
                    # Détecter les escales
                    # L'API Travelpayouts retourne les vols avec escales
                    # Pour les destinations asiatiques depuis Paris, un prix très bas (< 400€) 
                    # indique souvent une escale (les vols directs sont généralement plus chers)
                    has_stopover = False
                    stopovers = None
                    
                    # Liste des destinations asiatiques principales
                    asia_destinations = {
                        "BKK", "SIN", "HKG", "NRT", "HND", "ICN", "PEK", "PVG", "CAN", "KUL",
                        "MNL", "JKT", "HAN", "SGN", "BOM", "DEL", "BLR", "MAA", "DPS", "CGK",
                        "TPE", "KHH", "OKA", "FUK", "KIX", "NGO", "CTS", "GMP", "PUS", "CJU"
                    }
                    
                    # Pour les destinations asiatiques, si le prix est très bas, c'est probablement une escale
                    if destination in asia_destinations and price_eur < 400:
                        has_stopover = True
                        # Les escales communes vers l'Asie depuis Paris
                        if price_eur < 300:
                            stopovers = "Escale probable (Dubai/Doha/Istanbul)"
                    
                    # Vérifier aussi si plusieurs compagnies (indicateur d'escale)
                    if "/" in airline or len(airline.split()) > 1:
                        has_stopover = True
                        if not stopovers:
                            stopovers = "Escale avec changement de compagnie"
                    
                    # URL de réservation (construire avec les paramètres)
                    booking_url = f"https://www.aviasales.ru/search/{origin}{parsed_depart_date.strftime('%d%m')}{destination}"
                    
                    flight = Flight(
                        origin=origin,
                        destination=destination,
                        departure_date=parsed_depart_date,
                        price=price_eur,
                        airline=airline,
                        departure_time=departure_time,
                        arrival_time=None,  # Non fourni par l'API
                        return_date=parsed_return_date,
                        return_departure_time=return_departure_time,
                        return_arrival_time=return_arrival_time,
                        booking_url=booking_url,
                        currency="EUR",  # Toujours convertir en EUR
                        has_stopover=has_stopover,
                        stopovers=stopovers
                    )
                    
                    flights.append(flight)
                    
                except Exception as e:
                    logger.warning(f"Erreur lors du parsing d'une offre Travelpayouts: {e}")
                    continue
            
            logger.info(f"Parsé {len(flights)} vols pour {origin} -> {destination}")
            
        except Exception as e:
            logger.error(f"Erreur lors du parsing de la réponse Travelpayouts: {e}")
        
        return flights

