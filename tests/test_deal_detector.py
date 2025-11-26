"""Tests pour le détecteur de deals."""

import pytest
from datetime import date
from scanner.models import Flight
from scanner.storage import Storage
from scanner.deal_detector import DealDetector
from scanner.config import ScannerConfig, AmadeusConfig, SMTPConfig


@pytest.fixture
async def storage(tmp_path):
    """Crée une base de données temporaire pour les tests."""
    db_path = str(tmp_path / "test.db")
    storage = Storage(db_path)
    await storage.init_db()
    return storage


@pytest.fixture
def config():
    """Crée une configuration de test."""
    return ScannerConfig(
        max_price=200.0,
        discount_threshold=0.5,
        min_observations=5,
        amadeus=AmadeusConfig(api_key="test", api_secret="test"),
        smtp=SMTPConfig(
            host="test", port=587, user="test", password="test",
            from_email="test@test.com", to_email="test@test.com"
        )
    )


@pytest.fixture
async def detector(storage, config):
    """Crée un détecteur de deals pour les tests."""
    return DealDetector(storage, config)


@pytest.mark.asyncio
async def test_detect_deal_with_sufficient_history(detector, storage):
    """Test la détection d'un deal avec suffisamment d'historique."""
    # Créer un historique de prix élevés
    origin = "CDG"
    destination = "NYC"
    test_date = date(2024, 6, 15)
    
    # Ajouter 10 prix élevés (300€)
    for i in range(10):
        flight = Flight(
            origin=origin,
            destination=destination,
            departure_date=test_date,
            price=300.0,
            airline="AF"
        )
        await storage.store_price(flight)
    
    # Créer un vol bon marché (100€ = 66% de réduction)
    cheap_flight = Flight(
        origin=origin,
        destination=destination,
        departure_date=test_date,
        price=100.0,
        airline="AF"
    )
    
    # Détecter les deals
    deals = await detector.detect_deals([cheap_flight])
    
    # Vérifier qu'un deal a été détecté
    assert len(deals) == 1
    assert deals[0].flight.price == 100.0
    assert deals[0].discount_percentage >= 50.0


@pytest.mark.asyncio
async def test_no_deal_with_insufficient_history(detector, storage):
    """Test qu'aucun deal n'est détecté sans assez d'historique."""
    origin = "CDG"
    destination = "NYC"
    test_date = date(2024, 6, 15)
    
    # Ajouter seulement 2 prix (moins que le minimum requis de 5)
    for i in range(2):
        flight = Flight(
            origin=origin,
            destination=destination,
            departure_date=test_date,
            price=300.0,
            airline="AF"
        )
        await storage.store_price(flight)
    
    # Créer un vol bon marché
    cheap_flight = Flight(
        origin=origin,
        destination=destination,
        departure_date=test_date,
        price=100.0,
        airline="AF"
    )
    
    # Détecter les deals
    deals = await detector.detect_deals([cheap_flight])
    
    # Vérifier qu'aucun deal n'a été détecté (pas assez d'historique)
    assert len(deals) == 0


@pytest.mark.asyncio
async def test_no_deal_if_price_too_high(detector, storage):
    """Test qu'aucun deal n'est détecté si le prix dépasse le maximum."""
    origin = "CDG"
    destination = "NYC"
    test_date = date(2024, 6, 15)
    
    # Créer un historique
    for i in range(10):
        flight = Flight(
            origin=origin,
            destination=destination,
            departure_date=test_date,
            price=500.0,
            airline="AF"
        )
        await storage.store_price(flight)
    
    # Créer un vol cher (250€ > 200€ max)
    expensive_flight = Flight(
        origin=origin,
        destination=destination,
        departure_date=test_date,
        price=250.0,
        airline="AF"
    )
    
    # Détecter les deals
    deals = await detector.detect_deals([expensive_flight])
    
    # Vérifier qu'aucun deal n'a été détecté (prix trop élevé)
    assert len(deals) == 0


@pytest.mark.asyncio
async def test_no_deal_if_discount_insufficient(detector, storage):
    """Test qu'aucun deal n'est détecté si la réduction est insuffisante."""
    origin = "CDG"
    destination = "NYC"
    test_date = date(2024, 6, 15)
    
    # Créer un historique de prix moyens (200€)
    for i in range(10):
        flight = Flight(
            origin=origin,
            destination=destination,
            departure_date=test_date,
            price=200.0,
            airline="AF"
        )
        await storage.store_price(flight)
    
    # Créer un vol avec une petite réduction (150€ = 25% de réduction, < 50%)
    flight = Flight(
        origin=origin,
        destination=destination,
        departure_date=test_date,
        price=150.0,
        airline="AF"
    )
    
    # Détecter les deals
    deals = await detector.detect_deals([flight])
    
    # Vérifier qu'aucun deal n'a été détecté (réduction insuffisante)
    assert len(deals) == 0

