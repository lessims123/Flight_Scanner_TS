"""Gestion du stockage SQLite pour l'historique des prix et les deals notifiés."""

import aiosqlite
import logging
from datetime import date, datetime
from typing import Optional, List, Tuple
from scanner.models import Flight

logger = logging.getLogger(__name__)


class Storage:
    """Gestionnaire de stockage SQLite."""
    
    def __init__(self, db_path: str):
        """
        Initialise le gestionnaire de stockage.
        
        Args:
            db_path: Chemin vers le fichier SQLite
        """
        self.db_path = db_path
    
    async def init_db(self):
        """Initialise les tables de la base de données."""
        async with aiosqlite.connect(self.db_path) as db:
            # Table pour l'historique des prix
            await db.execute("""
                CREATE TABLE IF NOT EXISTS price_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    origin TEXT NOT NULL,
                    destination TEXT NOT NULL,
                    departure_date DATE NOT NULL,
                    departure_month INTEGER NOT NULL,
                    departure_year INTEGER NOT NULL,
                    price REAL NOT NULL,
                    airline TEXT,
                    currency TEXT DEFAULT 'EUR',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(origin, destination, departure_date, price, airline)
                )
            """)
            
            # Index pour accélérer les requêtes
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_route_month_year 
                ON price_history(origin, destination, departure_month, departure_year)
            """)
            
            # Table pour les deals notifiés
            await db.execute("""
                CREATE TABLE IF NOT EXISTS notified_deals (
                    flight_hash TEXT PRIMARY KEY,
                    origin TEXT NOT NULL,
                    destination TEXT NOT NULL,
                    departure_date DATE NOT NULL,
                    price REAL NOT NULL,
                    usual_price REAL NOT NULL,
                    discount_percentage REAL NOT NULL,
                    notified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            await db.commit()
            logger.info("Base de données initialisée")
    
    async def store_price(self, flight: Flight):
        """
        Stocke un prix dans l'historique.
        
        Args:
            flight: Vol à stocker
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT OR IGNORE INTO price_history 
                    (origin, destination, departure_date, departure_month, departure_year, price, airline, currency)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    flight.origin,
                    flight.destination,
                    flight.departure_date.isoformat(),
                    flight.departure_date.month,
                    flight.departure_date.year,
                    flight.price,
                    flight.airline,
                    flight.currency
                ))
                await db.commit()
        except Exception as e:
            logger.error(f"Erreur lors du stockage du prix: {e}")
    
    async def get_average_price(
        self,
        origin: str,
        destination: str,
        month: Optional[int] = None,
        year: Optional[int] = None
    ) -> Optional[float]:
        """
        Calcule le prix moyen pour une route donnée.
        
        Args:
            origin: Code IATA de l'origine
            destination: Code IATA de la destination
            month: Mois (optionnel, si None prend tous les mois)
            year: Année (optionnel, si None prend toutes les années)
            
        Returns:
            Prix moyen ou None si pas assez de données
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                query = """
                    SELECT AVG(price), COUNT(*) 
                    FROM price_history
                    WHERE origin = ? AND destination = ?
                """
                params = [origin, destination]
                
                if month is not None:
                    query += " AND departure_month = ?"
                    params.append(month)
                
                if year is not None:
                    query += " AND departure_year = ?"
                    params.append(year)
                
                async with db.execute(query, params) as cursor:
                    row = await cursor.fetchone()
                    if row and row[0] is not None and row[1] > 0:
                        return float(row[0])
                    return None
        except Exception as e:
            logger.error(f"Erreur lors du calcul du prix moyen: {e}")
            return None
    
    async def get_median_price(
        self,
        origin: str,
        destination: str,
        month: Optional[int] = None,
        year: Optional[int] = None
    ) -> Optional[float]:
        """
        Calcule le prix médian pour une route donnée.
        
        Args:
            origin: Code IATA de l'origine
            destination: Code IATA de la destination
            month: Mois (optionnel)
            year: Année (optionnel)
            
        Returns:
            Prix médian ou None si pas assez de données
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                query = """
                    SELECT price 
                    FROM price_history
                    WHERE origin = ? AND destination = ?
                """
                params = [origin, destination]
                
                if month is not None:
                    query += " AND departure_month = ?"
                    params.append(month)
                
                if year is not None:
                    query += " AND departure_year = ?"
                    params.append(year)
                
                query += " ORDER BY price"
                
                async with db.execute(query, params) as cursor:
                    rows = await cursor.fetchall()
                    if not rows:
                        return None
                    
                    prices = [float(row[0]) for row in rows]
                    n = len(prices)
                    
                    if n % 2 == 0:
                        return (prices[n // 2 - 1] + prices[n // 2]) / 2
                    else:
                        return prices[n // 2]
        except Exception as e:
            logger.error(f"Erreur lors du calcul du prix médian: {e}")
            return None
    
    async def get_observations_count(
        self,
        origin: str,
        destination: str,
        month: Optional[int] = None,
        year: Optional[int] = None
    ) -> int:
        """
        Compte le nombre d'observations pour une route.
        
        Args:
            origin: Code IATA de l'origine
            destination: Code IATA de la destination
            month: Mois (optionnel)
            year: Année (optionnel)
            
        Returns:
            Nombre d'observations
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                query = """
                    SELECT COUNT(*) 
                    FROM price_history
                    WHERE origin = ? AND destination = ?
                """
                params = [origin, destination]
                
                if month is not None:
                    query += " AND departure_month = ?"
                    params.append(month)
                
                if year is not None:
                    query += " AND departure_year = ?"
                    params.append(year)
                
                async with db.execute(query, params) as cursor:
                    row = await cursor.fetchone()
                    return row[0] if row else 0
        except Exception as e:
            logger.error(f"Erreur lors du comptage des observations: {e}")
            return 0
    
    async def is_deal_notified(self, flight_hash: str) -> bool:
        """
        Vérifie si un deal a déjà été notifié.
        
        Args:
            flight_hash: Hash du vol
            
        Returns:
            True si déjà notifié, False sinon
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    "SELECT 1 FROM notified_deals WHERE flight_hash = ?",
                    (flight_hash,)
                ) as cursor:
                    return await cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"Erreur lors de la vérification du deal: {e}")
            return False
    
    async def mark_deal_as_notified(
        self,
        flight: Flight,
        usual_price: float,
        discount_percentage: float
    ):
        """
        Marque un deal comme notifié.
        
        Args:
            flight: Vol concerné
            usual_price: Prix habituel
            discount_percentage: Pourcentage de réduction
        """
        try:
            flight_hash = flight.to_hash()
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT OR REPLACE INTO notified_deals 
                    (flight_hash, origin, destination, departure_date, price, usual_price, discount_percentage)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    flight_hash,
                    flight.origin,
                    flight.destination,
                    flight.departure_date.isoformat(),
                    flight.price,
                    usual_price,
                    discount_percentage
                ))
                await db.commit()
                logger.info(f"Deal marqué comme notifié: {flight.origin} -> {flight.destination} à {flight.price}€")
        except Exception as e:
            logger.error(f"Erreur lors du marquage du deal: {e}")

