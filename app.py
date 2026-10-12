import os
from datetime import datetime, timezone

from flask import Flask, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-only-change-me")

database_url = os.environ.get("DATABASE_URL", "sqlite:///lycee_decomble.db")
# Render may provide the legacy postgres:// scheme; SQLAlchemy expects postgresql://.
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
elif database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True}
db = SQLAlchemy(app)


class Formation(db.Model):
    __tablename__ = "formations"

    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(40), nullable=False, index=True)
    title = db.Column(db.String(250), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=False, default="")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False,
                            default=lambda: datetime.now(timezone.utc))


# Initial content mirrors the 20 formation cards already present in the website.
INITIAL_FORMATIONS = [{'category': 'cap', 'title': "CAP Conducteur d'engins de travaux publics et carrières", 'description': "Formation pratique centrée sur la conduite et l'entretien courant des engins utilisés sur les chantiers et dans les carrières."}, {'category': 'cap', 'title': 'CAP Maintenance des véhicules — véhicules légers', 'description': "Apprentissage de l'entretien, du contrôle et de la maintenance des voitures, avec recherche de pannes et interventions sur les systèmes du véhicule."}, {'category': 'cap', 'title': 'CAP Électricien', 'description': 'Découverte des installations électriques : câblage, raccordement, mise en service, contrôle et respect des règles de sécurité.'}, {'category': 'seconde', 'title': '2de pro Métiers de la construction durable, du bâtiment et des travaux publics', 'description': 'Une seconde professionnelle qui prépare aux métiers de la construction, du bâtiment et des travaux publics grâce à des compétences communes à plusieurs spécialités.'}, {'category': 'seconde', 'title': '2de pro Métiers de la maintenance des matériels et des véhicules', 'description': 'Découverte de la maintenance des véhicules et des matériels : fonctionnement, entretien, diagnostic et premières interventions techniques.'}, {'category': 'seconde', 'title': "2de pro Métiers de la réalisation d'ensembles mécaniques et industriels", 'description': "Initiation à la fabrication de pièces et d'ensembles mécaniques : préparation, usinage, contrôle et organisation de la production."}, {'category': 'seconde', 'title': '2de pro Métiers des transitions numérique et énergétique', 'description': "Une seconde orientée vers le numérique, l'électricité et les systèmes énergétiques, avec des bases en réseaux, équipements connectés et installations."}, {'category': 'seconde', 'title': "2de pro Métiers du pilotage et de la maintenance d'installations automatisées", 'description': "Découverte des systèmes automatisés : conduite d'installations, maintenance, réglages, diagnostic et prévention des pannes."}, {'category': 'bac', 'title': 'Bac Pro Carrossier peintre automobile', 'description': "Apprentissage de la réparation et de la remise en état des carrosseries, de la préparation des surfaces jusqu'à la mise en peinture du véhicule."}, {'category': 'bac', 'title': 'Bac Pro Cybersécurité, informatique et réseaux, électronique — CIEL', 'description': "Formation aux réseaux, à l'informatique, à la cybersécurité et aux systèmes électroniques : installation, configuration, maintenance et diagnostic."}, {'category': 'bac', 'title': 'Bac Pro Maintenance des systèmes de production connectés', 'description': "Formation à la maintenance des machines et systèmes industriels : diagnostic, intervention, prévention des pannes et suivi d'équipements connectés."}, {'category': 'bac', 'title': 'Bac Pro Maintenance des véhicules — véhicules légers', 'description': "Formation à l'entretien, au diagnostic et à la réparation des véhicules légers, avec utilisation d'outils de mesure et de diagnostic."}, {'category': 'bac', 'title': "Bac Pro Métiers de l'électricité et de ses environnements connectés — MELEC", 'description': "Préparation, réalisation, mise en service et maintenance d'installations électriques, y compris des équipements et environnements connectés."}, {'category': 'bac', 'title': 'Bac Pro Technicien en réalisation de produits mécaniques — réalisation et maintenance des outillages', 'description': "Formation à la fabrication et à la maintenance d'outillages mécaniques, avec préparation de production, usinage et contrôle des pièces."}, {'category': 'bac', 'title': 'Bac Pro Technicien en réalisation de produits mécaniques — réalisation et suivi de productions', 'description': 'Apprentissage de la préparation et du suivi de productions mécaniques : réglage des moyens de fabrication, contrôle des pièces et organisation du travail.'}, {'category': 'bac', 'title': 'Bac Pro Travaux publics', 'description': "Formation aux travaux de chantier : préparation, organisation et réalisation d'ouvrages liés aux routes, réseaux et autres infrastructures."}, {'category': 'bts', 'title': 'BTS Conception des processus de réalisation de produits — option A production unitaire', 'description': "Formation supérieure consacrée à la conception et à la préparation des processus de fabrication de pièces mécaniques réalisées à l'unité ou en petites séries."}, {'category': 'bts', 'title': 'BTS Maintenance des systèmes — option A systèmes de production', 'description': 'Formation supérieure pour apprendre à organiser, diagnostiquer et réaliser la maintenance de systèmes de production industriels.'}, {'category': 'dispositif', 'title': 'Classe de 3e prépa-métiers', 'description': 'Une année destinée aux élèves volontaires qui souhaitent découvrir les métiers et la voie professionnelle, avec enseignements généraux, découverte professionnelle et périodes en milieu professionnel.'}, {'category': 'dispositif', 'title': "ULIS lycée — Unité localisée pour l'inclusion scolaire", 'description': "Dispositif d'accompagnement et d'inclusion pour des élèves en situation de handicap, avec un parcours adapté et un accompagnement selon les besoins de chacun."}]


def initialize_database():
    """Create tables and add the initial formations without duplicating existing rows."""
    with app.app_context():
        db.create_all()
        for item in INITIAL_FORMATIONS:
            exists = db.session.query(Formation.id).filter_by(title=item["title"]).first()
            if not exists:
                db.session.add(Formation(**item))
        db.session.commit()


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
        return jsonify(status="error", database="unavailable"), 503


@app.route("/api/formations")
def api_formations():
    """Return the formation catalogue stored in the configured database."""
    formations = Formation.query.order_by(Formation.id.asc()).all()
    return jsonify([
        {
            "id": formation.id,
            "category": formation.category,
            "title": formation.title,
            "description": formation.description,
        }
        for formation in formations
    ])


with app.app_context():
    initialize_database()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=False)
