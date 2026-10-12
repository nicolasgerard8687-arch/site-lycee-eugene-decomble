# Lycée Eugène Decomble — version corrigée

## Ce qui est corrigé
- Le HTML a été remis dans `templates/index.html`, à l'emplacement attendu par Flask.
- Le document HTML démarre désormais par un doctype et possède un `head` cohérent.
- Ajout de SQLAlchemy et d'une base PostgreSQL sur Render (SQLite en local si `DATABASE_URL` n'est pas défini).
- Les tables sont créées au démarrage et les 20 formations du site sont insérées une seule fois.
- `/health` vérifie aussi la connexion à la base, pour que le contrôle de santé Render détecte les erreurs.
- `/api/formations` renvoie le catalogue depuis la base de données.

## Déploiement sur Render
1. Décompressez ce dossier et envoyez **tous les fichiers** dans le dépôt Git relié à Render.
2. Vérifiez que `render.yaml` est à la racine du dépôt.
3. Dans Render, créez ou mettez à jour le service via le Blueprint (Infrastructure as Code) afin que le service web **et** la base `lycee-decomble-db` soient créés.
4. Acceptez la création de la base et le déploiement. Render renseignera `DATABASE_URL` depuis la base liée.
5. Ouvrez `https://VOTRE-SITE.onrender.com/health`. La réponse attendue est `{"database":"connected","status":"ok"}`.
6. Ouvrez `https://VOTRE-SITE.onrender.com/api/formations`. Vous devez voir les 20 formations.

## Test local
```bash
python -m venv .venv
# Windows : .venv\\Scripts\\activate
# macOS/Linux :
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```
Visitez `http://127.0.0.1:5000/health` et `http://127.0.0.1:5000/api/formations`.

Sans `DATABASE_URL`, le développement local utilise `instance/lycee_decomble.db` (SQLite). Ne mettez jamais de mot de passe ou de chaîne de connexion dans Git.

## Important
Le catalogue visible sur la page est toujours rendu depuis le HTML existant; l'API permet de vérifier que les données sont enregistrées et disponibles dans la base. La base n'est pas un panneau d'administration. Le plan gratuit de Render peut avoir des limites ou une politique d'expiration propres à Render : vérifiez les conditions affichées dans votre compte.
