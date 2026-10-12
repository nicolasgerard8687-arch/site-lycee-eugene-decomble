# Portail Lycée Eugène Decomble — évolution Flask/PostgreSQL

## Fonctionnalités ajoutées
- Espace admin : `/admin/login`, `/admin`
- CRUD du catalogue : `/admin/formations`
- Gestion des actualités : `/admin/actualites`
- Gestion des événements : `/admin/evenements`
- Pages publiques : `/actualites`, `/agenda`
- API : `/api/formations`, `/api/news`, `/api/events`
- Contrôle de santé : `/health`

## Important avant le déploiement
1. Faire une sauvegarde de PostgreSQL.
2. Vérifier que le `render.yaml` correspond aux ressources existantes. Les noms de service et de base ne doivent pas être modifiés à l'aveugle.
3. Dans Render > service Web > Environment, configurer `ADMIN_EMAIL` et `ADMIN_PASSWORD` avec un compte réservé à l'administration. Ne jamais mettre ces secrets dans GitHub.
4. Conserver `DATABASE_URL` reliée à la base existante. Ne pas créer une nouvelle base pour ce projet.
5. Déployer d'abord sur un environnement de test si possible, puis vérifier `/health`, `/api/formations` et `/admin/login`.

## Données et schéma
`db.create_all()` crée les tables manquantes `news` et `school_events`; il ne supprime pas les tables existantes. Il ne remplace pas un outil de migration pour des changements futurs de colonnes. Les formations initiales sont ajoutées uniquement si leur titre n'existe pas déjà.

## Lancer en local
```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
# En local HTTP seulement : COOKIE_SECURE=false
pip install -r requirements.txt
# Configure ADMIN_EMAIL et ADMIN_PASSWORD avant de tester l'administration
python app.py
```

Pour le déploiement Render, `SECRET_KEY` doit être une valeur secrète stable gérée dans les variables d'environnement. Définis `ADMIN_EMAIL` et `ADMIN_PASSWORD` dans Render avant de tenter la connexion.
