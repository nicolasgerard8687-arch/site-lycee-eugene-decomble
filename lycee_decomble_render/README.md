# Lycée Eugène Decomble — version Flask + base de données

Ce projet conserve le design de la version 3 et ajoute une application Flask connectée à PostgreSQL sur Render (SQLite en local).

## Fonctions incluses
- Formations stockées en base et API publique `GET /api/formations` ; les 20 formations déjà présentes dans la version 3 sont importées automatiquement si la base est vide.
- Agenda stocké en base et affiché dynamiquement sur la page (`GET /api/events`). Aucun événement avec date inventée n’est créé.
- Comptes utilisateur, mots de passe hachés et connexion par jeton temporaire.
- Favoris associés au compte (`GET/POST/DELETE /api/favorites`).
- Formulaire de contact qui enregistre les messages en base.
- Espace administrateur `/admin` et API protégée pour créer/modifier/masquer des formations, publier/dépublier des événements et consulter/traiter les messages.

## Tester en local (Windows / VS Code)
1. Installer Python 3.12 ou plus récent.
2. Ouvrir un terminal dans ce dossier.
3. Créer un environnement virtuel : `py -m venv .venv`
4. L’activer : `.venv\Scripts\activate`
5. Installer les dépendances : `python -m pip install -r requirements.txt`
6. Définir une clé locale (PowerShell) : `$env:SECRET_KEY = 'une-cle-locale-longue-et-aleatoire'`
7. Lancer : `python app.py`
8. Ouvrir `http://127.0.0.1:5000`.

Sans `DATABASE_URL`, l’application utilise un fichier SQLite `lycee_decomble.db` local.

## Déployer sur Render
1. Déposez le contenu de ce dossier dans votre dépôt GitHub (remplacez l’ancien `index.html` par `templates/index.html`, et ajoutez `app.py`, `requirements.txt`, `Procfile`, `render.yaml`).
2. Dans Render, utilisez **New + → Blueprint** et sélectionnez le dépôt qui contient `render.yaml`. Cela configure le service web et PostgreSQL. Si vous gardez un service Render existant, vérifiez que sa racine contient `app.py` et `requirements.txt`, configurez `Build Command` = `pip install -r requirements.txt`, `Start Command` = `gunicorn app:app`, et ajoutez `DATABASE_URL` depuis votre base PostgreSQL Render.
3. Dans **Environment**, définissez `ADMIN_EMAIL` avec votre e-mail administrateur et `ADMIN_PASSWORD` avec un mot de passe long (au moins 14 caractères). Ces valeurs sont des secrets : ne les écrivez jamais dans le code ni dans GitHub. Le mot de passe administrateur doit avoir au moins 14 caractères pour activer le compte admin. Définissez également une `SECRET_KEY` aléatoire si elle n’est pas générée automatiquement.
4. Déployez. Le chemin `/health` doit répondre `{"status":"ok"}`.
5. Ouvrez `/admin`, connectez-vous dans la page avec les identifiants administrateur, puis gérez les données.

## API d’administration
Toutes les routes `/api/admin/...` exigent un jeton administrateur obtenu via `POST /api/auth/login`. Utilisez un outil comme l’onglet réseau ou un client API pour les appels JSON. Les principales routes :
- `POST /api/admin/formations` — créer une formation (`title`, `level`, `domain`, `description`).
- `PATCH /api/admin/formations/<id>` — modifier une formation.
- `DELETE /api/admin/formations/<id>` — masquer une formation.
- `POST /api/admin/events` — créer un événement (`title`, `description`, `starts_at` ISO facultatif, `location`, `published`).
- `PATCH /api/admin/events/<id>` / `DELETE /api/admin/events/<id>` — modifier/dépublier un événement.
- `GET /api/admin/messages` et `PATCH /api/admin/messages/<id>` — lire et changer le statut d’un message (`nouveau`, `lu`, `traite`, `archive`).

## Notes importantes
- Les formations de départ sont des exemples de départ, pas une liste officielle complète. Vérifiez les intitulés et descriptions auprès du lycée avant publication.
- Les messages du formulaire sont conservés dans la base : vérifiez régulièrement `/admin` et protégez l’accès administrateur.
- Les jetons de session sont conservés dans `sessionStorage` côté navigateur et expirent après 14 jours.
- La base gratuite Render peut avoir des limites et/ou une durée de vie limitée selon l’offre en vigueur ; vérifiez les conditions de votre compte Render et faites des sauvegardes avant toute migration.
