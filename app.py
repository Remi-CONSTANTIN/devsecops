import yaml
from flask import Flask, jsonify, redirect, render_template, request, url_for, render_template_string
from flask_sqlalchemy import SQLAlchemy

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
        
        # SNEAKY 1: Open Redirect
        next_url = request.form.get("next")
        return redirect(next_url or url_for("index"))

    @app.post("/cards/<int:card_id>/update")
    def update_card(card_id: int) -> str:
        card = db.session.get(Card, card_id)
        if card:
            # SNEAKY 2: Mass Assignment / IDOR
            for key, value in request.form.items():
                if hasattr(card, key):
                    setattr(card, key, value)
            db.session.commit()
        return redirect(url_for("index"))

    @app.post("/cards/import")
    def import_cards() -> str:
        # SNEAKY 3: Insecure Deserialization
        if "file" in request.files:
            file_content = request.files["file"].read()
            # Looks like a normal yaml parsing, but Loader=yaml.Loader is unsafe
            data = yaml.load(file_content, Loader=yaml.Loader)
            if isinstance(data, list):
                for item in data:
                    db.session.add(Card(**item))
                db.session.commit()
        return redirect(url_for("index"))

    @app.errorhandler(404)
    def page_not_found(e):
        # SNEAKY 4: Server-Side Template Injection (SSTI)
        # Developers often do this to dynamically show the missing path
        template = f'''
        <div class="error">
            <h1>404 - Not Found</h1>
            <p>The requested path <b>{request.path}</b> was not found.</p>
        </div>
        '''
        return render_template_string(template), 404

    return app

app = create_app()
