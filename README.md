# Lycée Eugène Decomble — version réparée

## Lancer en local
1. Python 3.10+ recommandé.
2. `python -m venv .venv`
3. Active l'environnement virtuel puis lance `pip install -r requirements.txt`.
4. Configure les variables `ADMIN_EMAIL`, `ADMIN_PASSWORD` et `SECRET_KEY` (voir `.env.example`). Flask ne charge pas automatiquement `.env` : exporte les variables dans le terminal ou utilise ton outil d'hébergement.
5. `python app.py`
6. Ouvre `http://127.0.0.1:5000`, puis `/admin/login`.

## Déploiement
- La commande de démarrage est dans `Procfile` : `gunicorn app:app`.
- Configure `SECRET_KEY`, `ADMIN_EMAIL`, `ADMIN_PASSWORD` et `DATABASE_URL` dans les variables d'environnement de l'hébergeur.
- `COOKIE_SECURE=true` en HTTPS; `false` uniquement en local HTTP.
- Les templates sont rangés dans `templates/` et `templates/admin/`, emplacement attendu par Flask.
- La base crée les tables manquantes et ajoute les formations initiales sans supprimer les données existantes.

## Notes
Les identifiants ne sont volontairement pas fournis dans les fichiers. Si la connexion admin échoue, vérifie que `ADMIN_EMAIL` et `ADMIN_PASSWORD` sont bien définis dans l'environnement d'exécution.

## Comptes utilisateurs
- Les visiteurs peuvent créer un compte via `/inscription` puis se connecter via `/connexion`.
- L’administration peut consulter les comptes et l’historique des connexions sur `/admin/utilisateurs`.
- Les mots de passe sont stockés sous forme de hachage sécurisé et ne sont jamais visibles par l’administrateur.
