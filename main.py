"""Point d'entrée principal du scanner de vols."""

import asyncio
import logging
import sys
from pathlib import Path
from scanner.config import ScannerConfig
from scanner.runner import ScannerRunner


def setup_logging(log_file: str = "scanner.log"):
    """
    Configure le logging.
    
    Args:
        log_file: Chemin vers le fichier de log
    """
    # Format de log
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    
    # Configuration
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout)
        ]
    )


async def main():
    """Fonction principale."""
    # Configuration du logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        # Charger la configuration
        logger.info("Chargement de la configuration...")
        config = ScannerConfig.load()
        
        # Vérifier que les configurations essentielles sont présentes
        if not config.travelpayouts:
            logger.error("TRAVELPAYOUTS_API_TOKEN doit être défini dans .env")
            sys.exit(1)
        
        if not config.smtp.host or not config.smtp.user:
            logger.error("Configuration SMTP incomplète dans .env")
            sys.exit(1)
        
        # Créer et initialiser le runner
        runner = ScannerRunner(config)
        await runner.initialize()
        
        # Lancer le scanner
        await runner.run()
        
    except Exception as e:
        logger.error(f"Erreur fatale: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

