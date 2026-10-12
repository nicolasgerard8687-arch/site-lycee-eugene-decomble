import hmac
import os
import secrets
from datetime import datetime, timezone
from functools import wraps

from flask import (Flask, abort, flash, jsonify, redirect, render_template,
                   request, session, url_for)
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("COOKIE_SECURE", "true").lower() == "true"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True}

url = os.environ.get("DATABASE_URL", "sqlite:///lycee_decomble.db")
if url.startswith("postgres://"):
    url = url.replace("postgres://", "postgresql+psycopg://", 1)
elif url.startswith("postgresql://"):
    url = url.replace("postgresql://", "postgresql+psycopg://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = url

db = SQLAlchemy(app)


class Formation(db.Model):
    __tablename__ = "formations"
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(40), nullable=False, index=True)
    title = db.Column(db.String(250), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=False, default="")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False,
                           default=lambda: datetime.now(timezone.utc))


class News(db.Model):
    __tablename__ = "news"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(180), nullable=False)
    summary = db.Column(db.String(500), nullable=False, default="")
    content = db.Column(db.Text, nullable=False, default="")
    published = db.Column(db.Boolean, nullable=False, default=False, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False,
                           default=lambda: datetime.now(timezone.utc))


class SchoolEvent(db.Model):
    __tablename__ = "school_events"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(180), nullable=False)
    description = db.Column(db.Text, nullable=False, default="")
    starts_at = db.Column(db.DateTime, nullable=False, index=True)
    location = db.Column(db.String(180), nullable=False, default="")
    published = db.Column(db.Boolean, nullable=False, default=False, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False,
                           default=lambda: datetime.now(timezone.utc))


INITIAL_FORMATIONS = [
    ('cap', "CAP Conducteur d'engins de travaux publics et carrières", "Formation pratique centrée sur la conduite et l'entretien courant des engins utilisés sur les chantiers et dans les carrières."),
    ('cap', 'CAP Maintenance des véhicules — véhicules légers', "Apprentissage de l'entretien, du contrôle et de la maintenance des voitures, avec recherche de pannes et interventions sur les systèmes du véhicule."),
    ('cap', 'CAP Électricien', 'Découverte des installations électriques : câblage, raccordement, mise en service, contrôle et respect des règles de sécurité.'),
    ('seconde', '2de pro Métiers de la construction durable, du bâtiment et des travaux publics', 'Une seconde professionnelle qui prépare aux métiers de la construction, du bâtiment et des travaux publics grâce à des compétences communes à plusieurs spécialités.'),
    ('seconde', '2de pro Métiers de la maintenance des matériels et des véhicules', 'Découverte de la maintenance des véhicules et des matériels : fonctionnement, entretien, diagnostic et premières interventions techniques.'),
    ('seconde', "2de pro Métiers de la réalisation d'ensembles mécaniques et industriels", "Initiation à la fabrication de pièces et d'ensembles mécaniques : préparation, usinage, contrôle et organisation de la production."),
    ('seconde', '2de pro Métiers des transitions numérique et énergétique', "Une seconde orientée vers le numérique, l'électricité et les systèmes énergétiques, avec des bases en réseaux, équipements connectés et installations."),
    ('seconde', "2de pro Métiers du pilotage et de la maintenance d'installations automatisées", "Découverte des systèmes automatisés : conduite d'installations, maintenance, réglages, diagnostic et prévention des pannes."),
    ('bac', 'Bac Pro Carrossier peintre automobile', "Apprentissage de la réparation et de la remise en état des carrosseries, de la préparation des surfaces jusqu'à la mise en peinture du véhicule."),
    ('bac', 'Bac Pro Cybersécurité, informatique et réseaux, électronique — CIEL', "Formation aux réseaux, à l'informatique, à la cybersécurité et aux systèmes électroniques : installation, configuration, maintenance et diagnostic."),
    ('bac', 'Bac Pro Maintenance des systèmes de production connectés', 'Formation à la maintenance des machines et systèmes industriels : diagnostic, intervention, prévention des pannes et suivi d’équipements connectés.'),
    ('bac', 'Bac Pro Maintenance des véhicules — véhicules légers', 'Formation à l’entretien, au diagnostic et à la réparation des véhicules légers, avec utilisation d’outils de mesure et de diagnostic.'),
    ('bac', "Bac Pro Métiers de l'électricité et de ses environnements connectés — MELEC", "Préparation, réalisation, mise en service et maintenance d'installations électriques, y compris des équipements et environnements connectés."),
    ('bac', 'Bac Pro Technicien en réalisation de produits mécaniques — réalisation et maintenance des outillages', 'Formation à la fabrication et à la maintenance d’outillages mécaniques, avec préparation de production, usinage et contrôle des pièces.'),
    ('bac', 'Bac Pro Technicien en réalisation de produits mécaniques — réalisation et suivi de productions', 'Apprentissage de la préparation et du suivi de productions mécaniques : réglage des moyens de fabrication, contrôle des pièces et organisation du travail.'),
    ('bac', 'Bac Pro Travaux publics', 'Formation aux travaux de chantier : préparation, organisation et réalisation d’ouvrages liés aux routes, réseaux et autres infrastructures.'),
    ('bts', 'BTS Conception des processus de réalisation de produits — option A production unitaire', 'Formation supérieure consacrée à la conception et à la préparation des processus de fabrication de pièces mécaniques réalisées à l’unité ou en petites séries.'),
    ('bts', 'BTS Maintenance des systèmes — option A systèmes de production', 'Formation supérieure pour apprendre à organiser, diagnostiquer et réaliser la maintenance de systèmes de production industriels.'),
    ('dispositif', 'Classe de 3e prépa-métiers', 'Une année destinée aux élèves volontaires qui souhaitent découvrir les métiers et la voie professionnelle, avec enseignements généraux, découverte professionnelle et périodes en milieu professionnel.'),
    ('dispositif', "ULIS lycée — Unité localisée pour l'inclusion scolaire", "Dispositif d'accompagnement et d'inclusion pour des élèves en situation de handicap, avec un parcours adapté et un accompagnement selon les besoins de chacun."),
]


def initialize_database():
    """Create missing tables and seed missing initial formations; never drop data."""
    with app.app_context():
        db.create_all()  # creates missing tables; does not alter/drop existing tables
        for category, title, description in INITIAL_FORMATIONS:
            if not Formation.query.filter_by(title=title).first():
                db.session.add(Formation(category=category, title=title, description=description))
        db.session.commit()


def csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    return session["csrf_token"]


app.jinja_env.globals["csrf_token"] = csrf_token


@app.before_request
def protect_post_requests():
    if request.method == "POST":
        supplied = request.form.get("csrf_token", "")
        expected = session.get("csrf_token", "")
        if not expected or not hmac.compare_digest(supplied, expected):
            abort(400, description="Jeton de sécurité invalide. Recharge la page et réessaie.")


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("admin_authenticated"):
            return redirect(url_for("admin_login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


@app.route("/")
def accueil():
    return render_template("index.html")


@app.route("/health")
def health():
    try:
        db.session.execute(text("SELECT 1"))
        return jsonify(status="ok", database="connected"), 200
    except SQLAlchemyError:
        db.session.rollback()
        app.logger.exception("Database health check failed")
        return jsonify(status="error", database="unavailable"), 503


@app.route("/api/formations")
def api_formations():
    formations = Formation.query.order_by(Formation.id.asc()).all()
    return jsonify([{"id": f.id, "category": f.category, "title": f.title,
                     "description": f.description} for f in formations])


@app.route("/api/news")
def api_news():
    items = News.query.filter_by(published=True).order_by(News.created_at.desc()).all()
    return jsonify([{"id": n.id, "title": n.title, "summary": n.summary,
                     "content": n.content, "created_at": n.created_at.isoformat()} for n in items])


@app.route("/api/events")
def api_events():
    now = datetime.now()
    items = SchoolEvent.query.filter_by(published=True).filter(
        SchoolEvent.starts_at >= now).order_by(SchoolEvent.starts_at.asc()).all()
    return jsonify([{"id": e.id, "title": e.title, "description": e.description,
                     "starts_at": e.starts_at.isoformat(), "location": e.location} for e in items])


@app.route("/actualites")
def news_page():
    items = News.query.filter_by(published=True).order_by(News.created_at.desc()).all()
    return render_template("news.html", items=items)


@app.route("/agenda")
def calendar_page():
    items = SchoolEvent.query.filter_by(published=True).filter(
        SchoolEvent.starts_at >= datetime.now()).order_by(SchoolEvent.starts_at.asc()).all()
    return render_template("events.html", items=items)


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if session.get("admin_authenticated"):
        return redirect(url_for("admin_dashboard"))
    error = None
    if request.method == "POST":
        configured_password = os.environ.get("ADMIN_PASSWORD", "")
        configured_email = os.environ.get("ADMIN_EMAIL", "")
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        if not configured_password or not configured_email:
            error = "Configure ADMIN_EMAIL et ADMIN_PASSWORD dans les variables d’environnement Render."
        elif hmac.compare_digest(email.casefold(), configured_email.casefold()) and hmac.compare_digest(password, configured_password):
            session.clear()
            session["admin_authenticated"] = True
            session["csrf_token"] = secrets.token_urlsafe(32)
            return redirect(url_for("admin_dashboard"))
        else:
            error = "Identifiants incorrects."
    return render_template("admin/login.html", error=error)


@app.route("/admin/logout", methods=["POST"])
@admin_required
def admin_logout():
    session.clear()
    flash("Tu es déconnecté.", "success")
    return redirect(url_for("accueil"))


@app.route("/admin")
@admin_required
def admin_dashboard():
    return render_template("admin/dashboard.html", formation_count=Formation.query.count(),
                           news_count=News.query.count(), event_count=SchoolEvent.query.count(),
                           recent_news=News.query.order_by(News.created_at.desc()).limit(5).all(),
                           recent_events=SchoolEvent.query.order_by(SchoolEvent.starts_at.asc()).limit(5).all())


@app.route("/admin/formations", methods=["GET", "POST"])
@admin_required
def admin_formations():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        category = request.form.get("category", "").strip()
        description = request.form.get("description", "").strip()
        if not title or not category:
            flash("Le titre et la catégorie sont obligatoires.", "error")
        elif len(title) > 250 or len(category) > 40:
            flash("Le titre ou la catégorie est trop long.", "error")
        elif Formation.query.filter_by(title=title).first():
            flash("Une formation portant ce titre existe déjà.", "error")
        else:
            db.session.add(Formation(title=title, category=category, description=description))
            db.session.commit()
            flash("Formation ajoutée.", "success")
            return redirect(url_for("admin_formations"))
    return render_template("admin/formations.html", formations=Formation.query.order_by(Formation.title).all())


@app.route("/admin/formations/<int:item_id>/edit", methods=["POST"])
@admin_required
def admin_edit_formation(item_id):
    item = db.get_or_404(Formation, item_id)
    title = request.form.get("title", "").strip()
    category = request.form.get("category", "").strip()
    if not title or not category or len(title) > 250 or len(category) > 40:
        flash("Vérifie le titre et la catégorie.", "error")
    elif Formation.query.filter(Formation.title == title, Formation.id != item.id).first():
        flash("Ce titre est déjà utilisé.", "error")
    else:
        item.title = title
        item.category = category
        item.description = request.form.get("description", "").strip()
        db.session.commit()
        flash("Formation modifiée.", "success")
    return redirect(url_for("admin_formations"))


@app.route("/admin/formations/<int:item_id>/delete", methods=["POST"])
@admin_required
def admin_delete_formation(item_id):
    item = db.get_or_404(Formation, item_id)
    db.session.delete(item)
    db.session.commit()
    flash("Formation supprimée.", "success")
    return redirect(url_for("admin_formations"))


@app.route("/admin/actualites", methods=["GET", "POST"])
@admin_required
def admin_news():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        if not title or len(title) > 180:
            flash("Le titre est obligatoire (180 caractères maximum).", "error")
        else:
            item = News(title=title, summary=request.form.get("summary", "").strip()[:500],
                        content=request.form.get("content", "").strip(),
                        published=request.form.get("published") == "on")
            db.session.add(item)
            db.session.commit()
            flash("Actualité enregistrée.", "success")
            return redirect(url_for("admin_news"))
    return render_template("admin/news.html", items=News.query.order_by(News.created_at.desc()).all())


@app.route("/admin/actualites/<int:item_id>/toggle", methods=["POST"])
@admin_required
def admin_toggle_news(item_id):
    item = db.get_or_404(News, item_id)
    item.published = not item.published
    db.session.commit()
    flash("Publication mise à jour.", "success")
    return redirect(url_for("admin_news"))


@app.route("/admin/actualites/<int:item_id>/delete", methods=["POST"])
@admin_required
def admin_delete_news(item_id):
    db.session.delete(db.get_or_404(News, item_id))
    db.session.commit()
    flash("Actualité supprimée.", "success")
    return redirect(url_for("admin_news"))


@app.route("/admin/evenements", methods=["GET", "POST"])
@admin_required
def admin_events():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        starts_text = request.form.get("starts_at", "").strip()
        try:
            starts_at = datetime.fromisoformat(starts_text)
        except ValueError:
            starts_at = None
        if not title or len(title) > 180 or starts_at is None:
            flash("Renseigne un titre valide et une date/heure.", "error")
        else:
            item = SchoolEvent(title=title, starts_at=starts_at,
                               description=request.form.get("description", "").strip(),
                               location=request.form.get("location", "").strip()[:180],
                               published=request.form.get("published") == "on")
            db.session.add(item)
            db.session.commit()
            flash("Événement enregistré.", "success")
            return redirect(url_for("admin_events"))
    return render_template("admin/events.html", items=SchoolEvent.query.order_by(SchoolEvent.starts_at.asc()).all())


@app.route("/admin/evenements/<int:item_id>/toggle", methods=["POST"])
@admin_required
def admin_toggle_event(item_id):
    item = db.get_or_404(SchoolEvent, item_id)
    item.published = not item.published
    db.session.commit()
    flash("Publication mise à jour.", "success")
    return redirect(url_for("admin_events"))


@app.route("/admin/evenements/<int:item_id>/delete", methods=["POST"])
@admin_required
def admin_delete_event(item_id):
    db.session.delete(db.get_or_404(SchoolEvent, item_id))
    db.session.commit()
    flash("Événement supprimé.", "success")
    return redirect(url_for("admin_events"))


with app.app_context():
    initialize_database()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=False)
