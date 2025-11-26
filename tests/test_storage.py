"""Tests pour le stockage."""

import pytest
from datetime import date
from scanner.storage import Storage
from scanner.models import Flight


@pytest.fixture
async def storage(tmp_path):
    """Crée une base de données temporaire pour les tests."""
    db_path = str(tmp_path / "test.db")
    storage = Storage(db_path)
    await storage.init_db()
    return storage


@pytest.mark.asyncio
async def test_store_and_retrieve_price(storage):
    """Test le stockage et la récupération de prix."""
    flight = Flight(
        origin="CDG",
        destination="NYC",
        departure_date=date(2024, 6, 15),
        price=250.0,
        airline="AF"
    )
    
    # Stocker le prix
    await storage.store_price(flight)
    
    # Récupérer le prix moyen
    avg_price = await storage.get_average_price("CDG", "NYC", 6, 2024)
    
    assert avg_price == 250.0


@pytest.mark.asyncio
async def test_get_median_price(storage):
    """Test le calcul du prix médian."""
    # Ajouter plusieurs prix
    prices = [100.0, 200.0, 300.0, 400.0, 500.0]
    for price in prices:
        flight = Flight(
            origin="CDG",
            destination="NYC",
            departure_date=date(2024, 6, 15),
            price=price,
            airline="AF"
        )
        await storage.store_price(flight)
    
    # Récupérer le prix médian
    median = await storage.get_median_price("CDG", "NYC", 6, 2024)
    
    assert median == 300.0


@pytest.mark.asyncio
async def test_observations_count(storage):
    """Test le comptage des observations."""
    # Ajouter plusieurs prix
    for i in range(5):
        flight = Flight(
            origin="CDG",
            destination="NYC",
            departure_date=date(2024, 6, 15),
            price=250.0 + i,
            airline="AF"
        )
        await storage.store_price(flight)
    
    # Compter les observations
    count = await storage.get_observations_count("CDG", "NYC", 6, 2024)
    
    assert count == 5


@pytest.mark.asyncio
async def test_deal_notification_tracking(storage):
    """Test le suivi des deals notifiés."""
    flight = Flight(
        origin="CDG",
        destination="NYC",
        departure_date=date(2024, 6, 15),
        price=100.0,
        airline="AF"
    )
    
    flight_hash = flight.to_hash()
    
    # Vérifier qu'il n'est pas notifié
    assert not await storage.is_deal_notified(flight_hash)
    
    # Marquer comme notifié
    await storage.mark_deal_as_notified(flight, 300.0, 66.67)
    
    # Vérifier qu'il est maintenant notifié
    assert await storage.is_deal_notified(flight_hash)

