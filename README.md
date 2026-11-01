# Portfolio — Christian Makuku Valentin

Site portfolio trilingue (français, anglais, swahili) avec une page **Réalisations** alimentée par un espace d'administration pour publier des conceptions au format JPEG.

## Fonctionnalités

- Langue détectée automatiquement selon le navigateur du visiteur (FR / EN / SW, anglais par défaut pour les autres langues), sélecteur manuel mémorisé, et paramètre `?lang=fr|en|sw`.
- Sections : accueil, profil, parcours, intelligence artificielle, compétences, formation, réalisations récentes, contact.
- Page `/realisations` : galerie avec filtres par catégorie et visionneuse plein écran.
- Espace `/admin` protégé par mot de passe : envoi de plusieurs JPEG à la fois (glisser-déposer), titre et catégorie, modification et suppression. Les images sont redimensionnées automatiquement (original 2400 px max, miniature 900 px).

## Lancer en local

```bash
pip install -r requirements.txt
export ADMIN_PASSWORD="votre-mot-de-passe"
export SECRET_KEY="une-longue-chaine-aleatoire"
python app.py
```

Puis ouvrir http://localhost:5000 (site) et http://localhost:5000/admin (gestion des réalisations).

## Mise en ligne

Compatible avec tout hébergeur Python (Render, Railway, PythonAnywhere, VPS…) :

```bash
gunicorn app:app --bind 0.0.0.0:$PORT
```

Variables d'environnement :

| Variable | Rôle |
| --- | --- |
| `ADMIN_PASSWORD` | Mot de passe de l'espace `/admin` (obligatoire) |
| `SECRET_KEY` | Clé de session (obligatoire en production) |
| `UPLOAD_DIR` | Dossier des images (par défaut `uploads/`) |
| `DATA_FILE` | Fichier de la liste des réalisations (par défaut `data/realisations.json`) |

Les images et la liste des réalisations sont stockées sur le disque : chez l'hébergeur, utilisez un disque persistant et faites pointer `UPLOAD_DIR` et `DATA_FILE` dessus.

## Modifier les textes

Tous les textes traduits se trouvent dans `static/js/i18n.js` (un bloc par langue : `fr`, `en`, `sw`).
