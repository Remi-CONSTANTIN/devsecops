import sqlite3
from pathlib import Path

from app import create_app


def test_application_entrypoint_exists():
    assert Path("app.py").is_file()


def test_health_endpoint_returns_ok(tmp_path):
    app = create_app(database_uri=f"sqlite:///{tmp_path / 'kanban.db'}")
    response = app.test_client().get("/health")

    assert response.status_code == 200
    assert response.json == {"status": "ok"}


def test_health_endpoint_sets_baseline_security_headers(tmp_path):
    app = create_app(database_uri=f"sqlite:///{tmp_path / 'kanban.db'}")
    response = app.test_client().get("/health")

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert response.headers["Content-Security-Policy"] == "default-src 'self'; frame-ancestors 'none'; base-uri 'self'"


def test_home_page_shows_the_three_kanban_columns(tmp_path):
    app = create_app(database_uri=f"sqlite:///{tmp_path / 'kanban.db'}")
    response = app.test_client().get("/")

    assert response.status_code == 200
    assert b"A faire" in response.data
    assert b"En cours" in response.data
    assert b"Termine" in response.data


def test_user_can_add_a_card_to_the_sqlite_database(tmp_path):
    database = tmp_path / "kanban.db"
    app = create_app(database_uri=f"sqlite:///{database}")
    response = app.test_client().post(
        "/cards",
        data={"title": "Ecrire les tests", "description": "Ajouter Pytest"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Ecrire les tests" in response.data
    with sqlite3.connect(database) as connection:
        card = connection.execute("SELECT title, description, column FROM cards").fetchone()
    assert card == ("Ecrire les tests", "Ajouter Pytest", "todo")


def test_user_can_move_a_card_to_another_column(tmp_path):
    database = tmp_path / "kanban.db"
    app = create_app(database_uri=f"sqlite:///{database}")
    client = app.test_client()
    client.post("/cards", data={"title": "Ecrire les tests", "description": ""})

    response = client.post("/cards/1/move", data={"column": "doing"})

    assert response.status_code == 302
    with sqlite3.connect(database) as connection:
        card_column = connection.execute("SELECT column FROM cards WHERE id = 1").fetchone()[0]
    assert card_column == "doing"


def test_demo_pipeline_blocks_an_incorrect_health_contract(tmp_path):
    """Démonstration : ce test est volontairement faux et doit échouer en CI."""
    app = create_app(database_uri=f"sqlite:///{tmp_path / 'kanban.db'}")
    response = app.test_client().get("/health")

    assert response.status_code == 418
