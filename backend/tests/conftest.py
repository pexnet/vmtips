"""
Shared test configuration for VMTips backend tests.
Uses an in-memory SQLite database so tests never touch production data.
Rate limiting is bypassed by patching the shared limiter instance.
"""
import pytest
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from database import Base, get_db
from config import settings
from rate_limit import limiter

# In-memory SQLite with StaticPool so all connections share the same DB.
# Without StaticPool, each new connection creates a fresh in-memory DB,
# causing "no such table" errors when the router gets a different connection
# than the one where tables were created.
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False,
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
TEST_START_USERS_FILE = (
    Path(__file__).resolve().parents[1] / "data" / "start_users.example.json"
)


def _override_get_db():
    """Yield a test session and close it after the request."""
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


def _rate_limit_noop(*args, **kwargs):
    """No-op replacement for limiter._check_request_limit (disables rate limiting)."""
    pass


@pytest.fixture(scope="session", autouse=True)
def _bypass_rate_limit():
    """Bypass all rate limiting for the entire test session.

    We patch the shared limiter's _check_request_limit to a no-op so that
    no request is ever rate-limited, regardless of how many calls are made.
    This works because all routers now import the same limiter from rate_limit.py.
    """
    limiter._check_request_limit = _rate_limit_noop
    limiter.enabled = False
    yield
    limiter.enabled = True


@pytest.fixture(scope="function", autouse=True)
def _enable_public_registration_for_existing_tests():
    """Keep existing endpoint tests working while production defaults to closed."""
    previous = settings.allow_public_registration
    settings.allow_public_registration = True
    try:
        yield
    finally:
        settings.allow_public_registration = previous


# Import app AFTER fixtures are defined so that the dependency override
# and rate limit bypass are in place before the app is fully loaded.
from main import app

# Override the app's get_db dependency so all routers use the test DB
app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture(scope="function")
def db():
    """Create all tables, yield a session, then drop everything."""
    Base.metadata.create_all(bind=test_engine)
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client():
    """Yield a TestClient with fresh tables for each test."""
    from fastapi.testclient import TestClient
    from seed import main as seed_main

    class ApiPrefixTestClient(TestClient):
        """Test client that keeps old tests pointed at the mounted API prefix."""

        def request(self, method, url, *args, **kwargs):
            if isinstance(url, str) and url.startswith("/") and not url.startswith("/api/"):
                url = f"/api{url}"
            return super().request(method, url, *args, **kwargs)

    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    # Seed using the test session so data lands in the in-memory DB
    test_session = TestSessionLocal()
    try:
        seed_main(
            session=test_session,
            start_users_file=TEST_START_USERS_FILE,
        )
    finally:
        test_session.close()

    # Ensure rate limiting stays disabled after TestClient startup
    limiter._check_request_limit = _rate_limit_noop
    limiter.enabled = False

    yield ApiPrefixTestClient(app)
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def seeded_db():
    """Drop all tables, recreate, run seed, yield session, then cleanup."""
    from seed import main as seed_main
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    test_session = TestSessionLocal()
    try:
        seed_main(
            session=test_session,
            start_users_file=TEST_START_USERS_FILE,
        )
    finally:
        test_session.close()

    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def set_match_result():
    """Fixture that returns a function to set match results in the test DB."""
    def _set_match_result(match_id, home, away):
        from models import Match
        db = TestSessionLocal()
        try:
            m = db.query(Match).filter(Match.id == match_id).first()
            if m is None:
                raise ValueError(f"Match {match_id} not found")
            m.home_goals = home
            m.away_goals = away
            m.status = "finished"
            db.commit()
        finally:
            db.close()
    return _set_match_result


@pytest.fixture(scope="function")
def set_phase():
    """Fixture that returns a function to set the tournament phase in the test DB."""
    def _set_phase(phase_name: str):
        from models import TournamentPhase
        db = TestSessionLocal()
        try:
            phase_row = db.query(TournamentPhase).first()
            if phase_row:
                phase_row.phase = phase_name
            else:
                phase_row = TournamentPhase(phase=phase_name)
                db.add(phase_row)
            db.commit()
        finally:
            db.close()
    return _set_phase


@pytest.fixture(scope="session")
def test_engine_fixture():
    """Expose the test engine for tests that need to inspect tables."""
    return test_engine
