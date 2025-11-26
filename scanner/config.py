"""Gestion de la configuration du scanner."""

import os
import yaml
from pathlib import Path
from typing import List
from dataclasses import dataclass, field
from dotenv import load_dotenv


@dataclass
class AmadeusConfig:
    """Configuration pour l'API Amadeus."""
    
    api_key: str
    api_secret: str
    base_url: str = "https://api.amadeus.com"
    token_url: str = "/v1/security/oauth2/token"
    flight_offers_url: str = "/v2/shopping/flight-offers"


@dataclass
class SMTPConfig:
    """Configuration pour l'envoi d'emails."""
    
    host: str
    port: int
    user: str
    password: str
    from_email: str
    to_email: str
    use_tls: bool = True


@dataclass
class ScannerConfig:
    """Configuration principale du scanner."""
    
    origins: List[str] = field(default_factory=lambda: ["CDG", "ORY", "BVA"])
    destinations: List[str] = field(default_factory=lambda: [
        "NYC", "LON", "BCN", "ROM", "ATH", "LIS", "MAD", "AMS", "BER", "VIE",
        "PRG", "BUD", "WAW", "CPH", "STO", "OSL", "HEL", "DUB", "EDI", "GLA",
        "DXB", "DOH", "BKK", "SIN", "HKG", "NRT", "ICN", "SYD", "MEL", "AKL",
        "JFK", "LAX", "MIA", "SFO", "YVR", "YYZ", "GRU", "EZE", "CPT", "CAI"
    ])
    min_days_from_now: int = 7
    max_days_from_now: int = 120
    min_stay_days: int = 3  # Séjour minimum en jours (pour aller-retour)
    max_stay_days: int = 30  # Séjour maximum en jours (pour aller-retour)
    stay_days_step: int = 1  # Pas entre les durées de séjour testées (1 = toutes les durées, exhaustif)
    date_step_days: int = 7  # Pas entre les dates testées (7 = toutes les semaines, exhaustif)
    request_delay: float = 0.3  # Délai entre les requêtes en secondes (0.3 au lieu de 1 seconde)
    max_concurrent_requests: int = 10  # Nombre de requêtes parallèles (10 pour accélérer sans perdre de deals)
    max_price: float = 200.0
    discount_threshold: float = 0.5  # 50% de réduction minimum
    min_observations: int = 10  # Nombre minimum d'observations avant de notifier
    scan_interval_seconds: int = 3600  # 1 heure par défaut
    db_path: str = "flights.db"
    log_file: str = "scanner.log"
    
    amadeus: AmadeusConfig = field(default=None)
    smtp: SMTPConfig = field(default=None)
    
    @classmethod
    def load(cls, config_path: str = "config.yaml", env_path: str = ".env") -> "ScannerConfig":
        """Charge la configuration depuis les fichiers YAML et .env."""
        # Charger les variables d'environnement
        load_dotenv(env_path)
        
        # Charger le fichier YAML
        config_data = {}
        if Path(config_path).exists():
            with open(config_path, "r", encoding="utf-8") as f:
                config_data = yaml.safe_load(f) or {}
        
        # Configuration Amadeus depuis .env
        amadeus_config = AmadeusConfig(
            api_key=os.getenv("AMADEUS_API_KEY", ""),
            api_secret=os.getenv("AMADEUS_API_SECRET", "")
        )
        
        # Configuration SMTP depuis .env
        smtp_config = SMTPConfig(
            host=os.getenv("SMTP_HOST", ""),
            port=int(os.getenv("SMTP_PORT", "587")),
            user=os.getenv("SMTP_USER", ""),
            password=os.getenv("SMTP_PASSWORD", ""),
            from_email=os.getenv("EMAIL_FROM", ""),
            to_email=os.getenv("EMAIL_TO", ""),
            use_tls=os.getenv("SMTP_USE_TLS", "true").lower() == "true"
        )
        
        # Créer la configuration principale
        config = cls(
            origins=config_data.get("origins", cls().origins),
            destinations=config_data.get("destinations", cls().destinations),
            min_days_from_now=config_data.get("min_days_from_now", cls().min_days_from_now),
            max_days_from_now=config_data.get("max_days_from_now", cls().max_days_from_now),
            min_stay_days=config_data.get("min_stay_days", cls().min_stay_days),
            max_stay_days=config_data.get("max_stay_days", cls().max_stay_days),
            stay_days_step=config_data.get("stay_days_step", cls().stay_days_step),
            date_step_days=config_data.get("date_step_days", cls().date_step_days),
            request_delay=config_data.get("request_delay", cls().request_delay),
            max_concurrent_requests=config_data.get("max_concurrent_requests", cls().max_concurrent_requests),
            max_price=config_data.get("max_price", cls().max_price),
            discount_threshold=config_data.get("discount_threshold", cls().discount_threshold),
            min_observations=config_data.get("min_observations", cls().min_observations),
            scan_interval_seconds=config_data.get("scan_interval_seconds", cls().scan_interval_seconds),
            db_path=config_data.get("db_path", cls().db_path),
            log_file=config_data.get("log_file", cls().log_file),
            amadeus=amadeus_config,
            smtp=smtp_config
        )
        
        return config

