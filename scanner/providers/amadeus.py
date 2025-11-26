"""Provider Amadeus pour la recherche de vols."""

import aiohttp
import logging
from datetime import date, datetime, timedelta
from typing import List, Optional
from scanner.models import Flight
from scanner.config import AmadeusConfig

logger = logging.getLogger(__name__)


class AmadeusFlightProvider:
    """Provider pour l'API Amadeus."""
    
    def __init__(self, config: AmadeusConfig):
        """
        Initialise le provider Amadeus.
        
        Args:
            config: Configuration Amadeus avec API key et secret
        """
        self.config = config
        self.token: Optional[str] = None
        self.token_expiry: Optional[datetime] = None
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Obtient ou crée une session HTTP."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session
    
    async def close(self):
        """Ferme la session HTTP."""
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def _authenticate(self) -> bool:
        """
        Authentifie auprès de l'API Amadeus et récupère un token OAuth2.
        
        Returns:
            True si l'authentification a réussi, False sinon
        """
        try:
            session = await self._get_session()
            url = f"{self.config.base_url}{self.config.token_url}"
            
            data = {
                "grant_type": "client_credentials",
                "client_id": self.config.api_key,
                "client_secret": self.config.api_secret
            }
            
            async with session.post(url, data=data) as response:
                if response.status == 200:
                    result = await response.json()
                    self.token = result.get("access_token")
                    expires_in = result.get("expires_in", 1800)  # Par défaut 30 minutes
                    self.token_expiry = datetime.now() + timedelta(seconds=expires_in - 60)  # Marge de 1 minute
                    logger.info("Authentification Amadeus réussie")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"Échec authentification Amadeus: {response.status} - {error_text}")
                    return False
        except Exception as e:
            logger.error(f"Erreur lors de l'authentification Amadeus: {e}")
            return False
    
    async def _ensure_authenticated(self):
        """S'assure qu'un token valide est disponible."""
        if not self.token or (self.token_expiry and datetime.now() >= self.token_expiry):
            await self._authenticate()
    
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
        
        Args:
            origin: Code IATA de l'aéroport d'origine
            destination: Code IATA de l'aéroport de destination
            departure_date: Date de départ
            return_date: Date de retour (optionnel)
            max_price: Prix maximum en EUR (optionnel)
            
        Returns:
            Liste de vols trouvés
        """
        await self._ensure_authenticated()
        
        if not self.token:
            logger.error("Impossible d'obtenir un token Amadeus")
            return []
        
        try:
            session = await self._get_session()
            url = f"{self.config.base_url}{self.config.flight_offers_url}"
            
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json"
            }
            
            params = {
                "originLocationCode": origin,
                "destinationLocationCode": destination,
                "departureDate": departure_date.strftime("%Y-%m-%d"),
                "adults": 1,
                "max": 10,  # Limiter à 10 résultats
                "currencyCode": "EUR"
            }
            
            if return_date:
                params["returnDate"] = return_date.strftime("%Y-%m-%d")
            
            if max_price:
                params["maxPrice"] = int(max_price)
            
            async with session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_flights(data, origin, destination, departure_date, return_date)
                elif response.status == 401:
                    # Token expiré, réessayer avec une nouvelle authentification
                    logger.warning("Token expiré, réauthentification...")
                    await self._authenticate()
                    if self.token:
                        headers["Authorization"] = f"Bearer {self.token}"
                        async with session.get(url, headers=headers, params=params) as response:
                            if response.status == 200:
                                data = await response.json()
                                return self._parse_flights(data, origin, destination, departure_date, return_date)
                    return []
                else:
                    error_text = await response.text()
                    logger.error(f"Erreur API Amadeus: {response.status} - {error_text}")
                    return []
        except Exception as e:
            logger.error(f"Erreur lors de la recherche de vols: {e}")
            return []
    
    def _parse_flights(
        self,
        data: dict,
        origin: str,
        destination: str,
        departure_date: date,
        return_date: Optional[date]
    ) -> List[Flight]:
        """
        Parse les données JSON d'Amadeus en objets Flight.
        
        Args:
            data: Réponse JSON de l'API Amadeus
            origin: Origine du vol
            destination: Destination du vol
            departure_date: Date de départ
            return_date: Date de retour (optionnel)
            
        Returns:
            Liste de vols parsés
        """
        flights = []
        
        try:
            offers = data.get("data", [])
            
            for offer in offers:
                try:
                    # Prix
                    price_data = offer.get("price", {})
                    total_price = float(price_data.get("total", 0))
                    currency = price_data.get("currency", "EUR")
                    
                    # Compagnie aérienne
                    validating_airlines = offer.get("validatingAirlineCodes", [])
                    airline = validating_airlines[0] if validating_airlines else "Unknown"
                    
                    # Itinéraires
                    itineraries = offer.get("itineraries", [])
                    if not itineraries:
                        continue
                    
                    outbound = itineraries[0]
                    segments_out = outbound.get("segments", [])
                    
                    if not segments_out:
                        continue
                    
                    # Départ aller
                    first_segment = segments_out[0]
                    departure_time = first_segment.get("departure", {}).get("at")
                    
                    # Arrivée aller
                    last_segment = segments_out[-1]
                    arrival_time = last_segment.get("arrival", {}).get("at")
                    
                    # Retour (si présent)
                    return_departure_time = None
                    return_arrival_time = None
                    parsed_return_date = None
                    
                    if len(itineraries) > 1:
                        return_itinerary = itineraries[1]
                        return_segments = return_itinerary.get("segments", [])
                        if return_segments:
                            return_first = return_segments[0]
                            return_last = return_segments[-1]
                            return_departure_time = return_first.get("departure", {}).get("at")
                            return_arrival_time = return_last.get("arrival", {}).get("at")
                            # Extraire la date de retour du premier segment retour
                            if return_departure_time:
                                try:
                                    parsed_return_date = datetime.fromisoformat(
                                        return_departure_time.replace("Z", "+00:00")
                                    ).date()
                                except:
                                    parsed_return_date = return_date
                    
                    # URL de réservation (si disponible)
                    booking_url = None
                    if "source" in offer:
                        # Amadeus fournit parfois des liens, mais souvent il faut utiliser leur front-end
                        booking_url = f"https://www.amadeus.com/fr/offres-vols/{origin}/{destination}"
                    
                    flight = Flight(
                        origin=origin,
                        destination=destination,
                        departure_date=departure_date,
                        price=total_price,
                        airline=airline,
                        departure_time=departure_time,
                        arrival_time=arrival_time,
                        return_date=parsed_return_date or return_date,
                        return_departure_time=return_departure_time,
                        return_arrival_time=return_arrival_time,
                        booking_url=booking_url,
                        currency=currency
                    )
                    
                    flights.append(flight)
                    
                except Exception as e:
                    logger.warning(f"Erreur lors du parsing d'une offre: {e}")
                    continue
            
            logger.info(f"Parsé {len(flights)} vols pour {origin} -> {destination}")
            
        except Exception as e:
            logger.error(f"Erreur lors du parsing de la réponse Amadeus: {e}")
        
        return flights

