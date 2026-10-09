import os
import re
from datetime import datetime, timezone, timedelta
from functools import wraps

from flask import Flask, jsonify, render_template, request, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from sqlalchemy import or_

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'development-only-change-this-secret')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
raw_db = os.environ.get('DATABASE_URL', 'sqlite:///lycee_decomble.db')
if raw_db.startswith('postgres://'):
    raw_db = raw_db.replace('postgres://', 'postgresql://', 1)
if raw_db.startswith('postgresql://') and '+psycopg' not in raw_db:
    raw_db = raw_db.replace('postgresql://', 'postgresql+psycopg://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = raw_db
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {'pool_pre_ping': True}
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(254), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='user')
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    favorites = db.relationship('Favorite', back_populates='user', cascade='all, delete-orphan')

class Formation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(180), nullable=False)
    level = db.Column(db.String(80), nullable=False, default='À préciser')
    domain = db.Column(db.String(100), nullable=False, default='Général')
    category = db.Column(db.String(30), nullable=False, default='dispositif')
    description = db.Column(db.Text, nullable=False, default='')
    active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(180), nullable=False)
    description = db.Column(db.Text, nullable=False, default='')
    starts_at = db.Column(db.DateTime(timezone=True), nullable=True)
    location = db.Column(db.String(180), nullable=False, default='Lycée Eugène Decomble')
    published = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(254), nullable=False, index=True)
    subject = db.Column(db.String(180), nullable=False)
    body = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='nouveau')
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)

class Favorite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    formation_id = db.Column(db.Integer, db.ForeignKey('formation.id', ondelete='CASCADE'), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    user = db.relationship('User', back_populates='favorites')
    formation = db.relationship('Formation')
    __table_args__ = (db.UniqueConstraint('user_id', 'formation_id', name='uq_user_formation_favorite'),)

serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'], salt='lycee-account-token')
def issue_token(user):
    return serializer.dumps({'uid': user.id})
def current_user():
    header = request.headers.get('Authorization', '')
    if not header.startswith('Bearer '): return None
    try:
        payload = serializer.loads(header[7:], max_age=60*60*24*14)
        return db.session.get(User, int(payload['uid']))
    except (BadSignature, SignatureExpired, KeyError, TypeError, ValueError):
        return None
def require_auth(admin=False):
    def deco(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            user = current_user()
            if not user: return jsonify(error='Connectez-vous pour continuer.'), 401
            if admin and user.role != 'admin': return jsonify(error='Accès réservé aux administrateurs.'), 403
            request.user = user
            return fn(*args, **kwargs)
        return wrapped
    return deco

def clean_text(value, limit):
    if not isinstance(value, str): return ''
    return value.strip()[:limit]
def valid_email(email):
    return bool(re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email or ''))
def user_json(user): return {'id': user.id, 'email': user.email, 'role': user.role}
def formation_json(f): return {'id':f.id,'title':f.title,'level':f.level,'domain':f.domain,'category':f.category,'description':f.description}
def event_json(e): return {'id':e.id,'title':e.title,'description':e.description,'starts_at':e.starts_at.isoformat() if e.starts_at else None,'location':e.location}
def event_date(value):
    if not value: return None
    try:
        d = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if d.tzinfo is None: d = d.replace(tzinfo=timezone.utc)
        return d
    except (ValueError, AttributeError): raise ValueError('Date invalide : utilisez un format ISO, par exemple 2026-11-15T09:30:00+01:00.')

@app.get('/')
def home():
    formations = Formation.query.filter_by(active=True).order_by(Formation.id.asc()).all()
    return render_template('index.html', formations=formations)

@app.get('/health')
def health(): return jsonify(status='ok')

@app.get('/api/formations')
def list_formations():
    rows = Formation.query.filter_by(active=True).order_by(Formation.title.asc()).all()
    return jsonify([formation_json(f) for f in rows])

@app.get('/api/events')
def list_events():
    rows = Event.query.filter_by(published=True).order_by(Event.starts_at.is_(None), Event.starts_at.asc()).limit(100).all()
    return jsonify([event_json(e) for e in rows])

@app.post('/api/messages')
def create_message():
    data = request.get_json(silent=True) or {}
    name, email = clean_text(data.get('name'),100), clean_text(data.get('email'),254).lower()
    subject, body = clean_text(data.get('subject'),180), clean_text(data.get('body'),5000)
    if not name or not valid_email(email) or not subject or len(body) < 3:
        return jsonify(error='Vérifiez le nom, l’e-mail, l’objet et le message.'), 400
    msg = Message(name=name,email=email,subject=subject,body=body)
    db.session.add(msg); db.session.commit()
    return jsonify(message='Message enregistré.', id=msg.id), 201

@app.post('/api/auth/register')
def register():
    data = request.get_json(silent=True) or {}
    email = clean_text(data.get('email'),254).lower()
    password = data.get('password') if isinstance(data.get('password'),str) else ''
    if not valid_email(email): return jsonify(error='Adresse e-mail invalide.'), 400
    if len(password) < 10: return jsonify(error='Le mot de passe doit contenir au moins 10 caractères.'), 400
    if User.query.filter_by(email=email).first(): return jsonify(error='Un compte existe déjà pour cet e-mail.'), 409
    user = User(email=email,password_hash=generate_password_hash(password),role='user')
    db.session.add(user); db.session.commit()
    return jsonify(token=issue_token(user),user=user_json(user)), 201

@app.post('/api/auth/login')
def login():
    data=request.get_json(silent=True) or {}; email=clean_text(data.get('email'),254).lower(); password=data.get('password') or ''
    user=User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password_hash,password): return jsonify(error='E-mail ou mot de passe incorrect.'), 401
    return jsonify(token=issue_token(user),user=user_json(user))

@app.get('/api/auth/me')
@require_auth()
def me(): return jsonify(user=user_json(request.user))

@app.get('/api/favorites')
@require_auth()
def list_favorites():
    rows=Favorite.query.filter_by(user_id=request.user.id).all()
    return jsonify([formation_json(x.formation) for x in rows if x.formation])

@app.post('/api/favorites/<int:formation_id>')
@require_auth()
def add_favorite(formation_id):
    if not db.session.get(Formation,formation_id): return jsonify(error='Formation introuvable.'),404
    item=Favorite.query.filter_by(user_id=request.user.id,formation_id=formation_id).first()
    if not item: db.session.add(Favorite(user_id=request.user.id,formation_id=formation_id)); db.session.commit()
    return jsonify(message='Favori enregistré.'),201

@app.delete('/api/favorites/<int:formation_id>')
@require_auth()
def delete_favorite(formation_id):
    item=Favorite.query.filter_by(user_id=request.user.id,formation_id=formation_id).first()
    if item: db.session.delete(item); db.session.commit()
    return jsonify(message='Favori supprimé.')

@app.route('/api/favorites/by-title', methods=['POST','DELETE'])
@require_auth()
def favorite_by_title():
    data=request.get_json(silent=True) or {}; title=clean_text(data.get('title'),180)
    if not title: return jsonify(error='Le titre est obligatoire.'),400
    formation=Formation.query.filter(db.func.lower(Formation.title)==title.lower(), Formation.active.is_(True)).first()
    if not formation: return jsonify(error='Formation introuvable dans la base.'),404
    item=Favorite.query.filter_by(user_id=request.user.id,formation_id=formation.id).first()
    if request.method=='POST':
        if not item: db.session.add(Favorite(user_id=request.user.id,formation_id=formation.id)); db.session.commit()
        return jsonify(message='Favori enregistré.'),201
    if item: db.session.delete(item); db.session.commit()
    return jsonify(message='Favori supprimé.')

# Admin JSON API; admin accounts are provisioned only from environment variables.
@app.post('/api/admin/formations')
@require_auth(admin=True)
def admin_create_formation():
    d=request.get_json(silent=True) or {}; title=clean_text(d.get('title'),180)
    if not title: return jsonify(error='Le titre est obligatoire.'),400
    category=clean_text(d.get('category'),30) or 'dispositif'
    if category not in ('cap','seconde','bac','bts','dispositif'): return jsonify(error='Catégorie invalide.'),400
    f=Formation(title=title,level=clean_text(d.get('level'),80) or 'À préciser',domain=clean_text(d.get('domain'),100) or 'Général',category=category,description=clean_text(d.get('description'),5000))
    db.session.add(f); db.session.commit(); return jsonify(formation=formation_json(f)),201

@app.patch('/api/admin/formations/<int:fid>')
@require_auth(admin=True)
def admin_update_formation(fid):
    f=db.session.get(Formation,fid)
    if not f:return jsonify(error='Formation introuvable.'),404
    d=request.get_json(silent=True) or {}
    for key,limit in [('title',180),('level',80),('domain',100),('description',5000)]:
        if key in d: setattr(f,key,clean_text(d[key],limit))
    if 'category' in d:
        if d['category'] not in ('cap','seconde','bac','bts','dispositif'): return jsonify(error='Catégorie invalide.'),400
        f.category=d['category']
    if 'active' in d:f.active=bool(d['active'])
    db.session.commit();return jsonify(formation=formation_json(f))

@app.delete('/api/admin/formations/<int:fid>')
@require_auth(admin=True)
def admin_delete_formation(fid):
    f=db.session.get(Formation,fid)
    if not f:return jsonify(error='Formation introuvable.'),404
    f.active=False;db.session.commit();return jsonify(message='Formation masquée.')

@app.post('/api/admin/events')
@require_auth(admin=True)
def admin_create_event():
    d=request.get_json(silent=True) or {}; title=clean_text(d.get('title'),180); description=clean_text(d.get('description'),5000)
    if not title:return jsonify(error='Le titre est obligatoire.'),400
    try: starts=event_date(d.get('starts_at'))
    except ValueError as e:return jsonify(error=str(e)),400
    e=Event(title=title,description=description,starts_at=starts,location=clean_text(d.get('location'),180) or 'Lycée Eugène Decomble',published=bool(d.get('published',True)))
    db.session.add(e);db.session.commit();return jsonify(event=event_json(e)),201

@app.patch('/api/admin/events/<int:eid>')
@require_auth(admin=True)
def admin_update_event(eid):
    e=db.session.get(Event,eid)
    if not e:return jsonify(error='Événement introuvable.'),404
    d=request.get_json(silent=True) or {}
    for key,limit in [('title',180),('description',5000),('location',180)]:
        if key in d:setattr(e,key,clean_text(d[key],limit))
    if 'starts_at' in d:
        try:e.starts_at=event_date(d['starts_at'])
        except ValueError as err:return jsonify(error=str(err)),400
    if 'published' in d:e.published=bool(d['published'])
    db.session.commit();return jsonify(event=event_json(e))

@app.delete('/api/admin/events/<int:eid>')
@require_auth(admin=True)
def admin_delete_event(eid):
    e=db.session.get(Event,eid)
    if not e:return jsonify(error='Événement introuvable.'),404
    e.published=False;db.session.commit();return jsonify(message='Événement dépublié.')

@app.get('/api/admin/messages')
@require_auth(admin=True)
def admin_messages():
    return jsonify([{'id':m.id,'name':m.name,'email':m.email,'subject':m.subject,'body':m.body,'status':m.status,'created_at':m.created_at.isoformat()} for m in Message.query.order_by(Message.created_at.desc()).limit(500).all()])

@app.patch('/api/admin/messages/<int:mid>')
@require_auth(admin=True)
def admin_update_message(mid):
    m=db.session.get(Message,mid)
    if not m:return jsonify(error='Message introuvable.'),404
    status=clean_text((request.get_json(silent=True) or {}).get('status'),20)
    if status not in ('nouveau','lu','traite','archive'):return jsonify(error='Statut invalide.'),400
    m.status=status;db.session.commit();return jsonify(message='Statut mis à jour.')

@app.get('/admin')
def admin_page(): return render_template('admin.html')

def initialize_database():
    with app.app_context():
        db.create_all()
        # Safe starter data only; no invented dates are published.
        if Formation.query.count()==0:
            db.session.add_all([
                Formation(title="CAP Conducteur d'engins de travaux publics et carrières", level='CAP', domain='Travaux publics', category='cap', description="Formation pratique centrée sur la conduite et l'entretien courant des engins utilisés sur les chantiers et dans les carrières."),
                Formation(title='CAP Maintenance des véhicules — véhicules légers', level='CAP', domain='Automobile', category='cap', description="Apprentissage de l'entretien, du contrôle et de la maintenance des voitures, avec recherche de pannes et interventions sur les systèmes du véhicule."),
                Formation(title='CAP Électricien', level='CAP', domain='Électricité', category='cap', description='Découverte des installations électriques : câblage, raccordement, mise en service, contrôle et respect des règles de sécurité.'),
                Formation(title='2de pro Métiers de la construction durable, du bâtiment et des travaux publics', level='Seconde professionnelle', domain='Construction', category='seconde', description='Une seconde professionnelle qui prépare aux métiers de la construction, du bâtiment et des travaux publics grâce à des compétences communes à plusieurs spécialités.'),
                Formation(title='2de pro Métiers de la maintenance des matériels et des véhicules', level='Seconde professionnelle', domain='Maintenance', category='seconde', description='Découverte de la maintenance des véhicules et des matériels : fonctionnement, entretien, diagnostic et premières interventions techniques.'),
                Formation(title="2de pro Métiers de la réalisation d'ensembles mécaniques et industriels", level='Seconde professionnelle', domain='Usinage', category='seconde', description="Initiation à la fabrication de pièces et d'ensembles mécaniques : préparation, usinage, contrôle et organisation de la production."),
                Formation(title='2de pro Métiers des transitions numérique et énergétique', level='Seconde professionnelle', domain='Numérique', category='seconde', description="Une seconde orientée vers le numérique, l'électricité et les systèmes énergétiques, avec des bases en réseaux, équipements connectés et installations."),
                Formation(title="2de pro Métiers du pilotage et de la maintenance d'installations automatisées", level='Seconde professionnelle', domain='Automatisme', category='seconde', description="Découverte des systèmes automatisés : conduite d'installations, maintenance, réglages, diagnostic et prévention des pannes."),
                Formation(title='Bac Pro Carrossier peintre automobile', level='Bac professionnel', domain='Carrosserie', category='bac', description="Apprentissage de la réparation et de la remise en état des carrosseries, de la préparation des surfaces jusqu'à la mise en peinture du véhicule."),
                Formation(title='Bac Pro Cybersécurité, informatique et réseaux, électronique — CIEL', level='Bac professionnel', domain='Informatique', category='bac', description="Formation aux réseaux, à l'informatique, à la cybersécurité et aux systèmes électroniques : installation, configuration, maintenance et diagnostic."),
                Formation(title='Bac Pro Maintenance des systèmes de production connectés', level='Bac professionnel', domain='Industrie', category='bac', description="Formation à la maintenance des machines et systèmes industriels : diagnostic, intervention, prévention des pannes et suivi d'équipements connectés."),
                Formation(title='Bac Pro Maintenance des véhicules — véhicules légers', level='Bac professionnel', domain='Automobile', category='bac', description="Formation à l'entretien, au diagnostic et à la réparation des véhicules légers, avec utilisation d'outils de mesure et de diagnostic."),
                Formation(title="Bac Pro Métiers de l'électricité et de ses environnements connectés — MELEC", level='Bac professionnel', domain='Électricité', category='bac', description="Préparation, réalisation, mise en service et maintenance d'installations électriques, y compris des équipements et environnements connectés."),
                Formation(title='Bac Pro Technicien en réalisation de produits mécaniques — réalisation et maintenance des outillages', level='Bac professionnel', domain='Outillage', category='bac', description="Formation à la fabrication et à la maintenance d'outillages mécaniques, avec préparation de production, usinage et contrôle des pièces."),
                Formation(title='Bac Pro Technicien en réalisation de produits mécaniques — réalisation et suivi de productions', level='Bac professionnel', domain='Productique', category='bac', description='Apprentissage de la préparation et du suivi de productions mécaniques : réglage des moyens de fabrication, contrôle des pièces et organisation du travail.'),
                Formation(title='Bac Pro Travaux publics', level='Bac professionnel', domain='Chantier', category='bac', description="Formation aux travaux de chantier : préparation, organisation et réalisation d'ouvrages liés aux routes, réseaux et autres infrastructures."),
                Formation(title='BTS Conception des processus de réalisation de produits — option A production unitaire', level='BTS', domain='Conception', category='bts', description="Formation supérieure consacrée à la conception et à la préparation des processus de fabrication de pièces mécaniques réalisées à l'unité ou en petites séries."),
                Formation(title='BTS Maintenance des systèmes — option A systèmes de production', level='BTS', domain='Maintenance', category='bts', description='Formation supérieure pour apprendre à organiser, diagnostiquer et réaliser la maintenance de systèmes de production industriels.'),
                Formation(title='Classe de 3e prépa-métiers', level='Dispositif', domain='Orientation', category='dispositif', description='Une année destinée aux élèves volontaires qui souhaitent découvrir les métiers et la voie professionnelle, avec enseignements généraux, découverte professionnelle et périodes en milieu professionnel.'),
                Formation(title="ULIS lycée — Unité localisée pour l'inclusion scolaire", level='Dispositif', domain='Inclusion', category='dispositif', description="Dispositif d'accompagnement et d'inclusion pour des élèves en situation de handicap, avec un parcours adapté et un accompagnement selon les besoins de chacun."),
            ])
        # Create/promote admin only when explicit environment credentials are set.
        admin_email=os.environ.get('ADMIN_EMAIL','').strip().lower()
        admin_password=os.environ.get('ADMIN_PASSWORD','')
        if admin_email and admin_password and valid_email(admin_email) and len(admin_password)>=14:
            user=User.query.filter_by(email=admin_email).first()
            if user:
                user.role='admin'; user.password_hash=generate_password_hash(admin_password)
            else:
                db.session.add(User(email=admin_email,password_hash=generate_password_hash(admin_password),role='admin'))
            db.session.commit()

initialize_database()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
