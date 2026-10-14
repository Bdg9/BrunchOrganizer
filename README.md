# Brunch au château

Petite page web pour savoir qui apporte quoi au brunch. Une colonne pour les items,
une colonne pour les prénoms. Plusieurs personnes peuvent apporter la même chose.

Serveur Python 3 sans aucune dépendance (bibliothèque standard uniquement), une seule
page HTML, et un fichier JSON pour garder la liste.

## Déploiement (conteneur)

```bash
docker build -t brunch .
docker run -d --name brunch --restart unless-stopped \
  -p 127.0.0.1:8080:8080 \
  -v brunch-data:/data \
  brunch
```

Ou avec `docker compose up -d --build`.

| | |
|---|---|
| Port dans le conteneur | `8080` (HTTP, pas de TLS) |
| **Volume à monter** | **`/data`** (contient `data.json`, la liste) |
| Utilisateur du conteneur | `brunch`, uid `10001` : le volume doit être inscriptible par cet uid |
| Variables | `PORT` (8080), `HOST` (0.0.0.0 dans l'image), `DATA_FILE` (`/data/data.json`) |
| Santé | `GET /api/state` renvoie 200, le `HEALTHCHECK` de l'image l'utilise |

Si on monte un dossier de l'hôte au lieu d'un volume nommé : `chown 10001 /chemin/du/dossier`.

Sans volume sur `/data`, la liste est perdue à chaque recréation du conteneur.
Pour sauvegarder, il suffit de copier `data.json`.

Le conteneur ne parle pas HTTPS : le placer derrière un reverse proxy (Caddy, nginx,
Traefik) qui gère le certificat pour le domaine choisi, par exemple `brunch.tala.family`.
Aucun en-tête particulier n'est nécessaire.

## Authentification

Il n'y en a pas, volontairement. Pas de compte, pas de mot de passe : toute personne
qui a le lien peut ajouter un item, s'inscrire sous n'importe quel prénom, retirer un
prénom ou supprimer un item sans inscrit. Le prénom est déclaré par chacun et gardé
dans le navigateur. Le lien est à partager uniquement dans le groupe WhatsApp du brunch.

Limites côté serveur : 200 items, 1000 inscriptions, texte tronqué (40 et 24 caractères),
requêtes de plus de 2 Ko refusées, pas de doublon d'item ni de prénom sur un même item.
Pas de limitation de débit : si besoin, la mettre au niveau du reverse proxy.

## API

| Méthode | Chemin | Corps | |
|---|---|---|---|
| GET | `/api/state` | | `{items, signups}` |
| POST | `/api/items` | `{name}` | ajoute un item |
| DELETE | `/api/items/<id>` | | supprime l'item et ses inscriptions |
| POST | `/api/signups` | `{itemId, who}` | inscrit une personne |
| DELETE | `/api/signups/<id>` | | retire l'inscription |

Les écritures renvoient l'état complet. La page se rafraîchit toutes les 5 secondes.

## Lancer sans conteneur

```bash
python3 server.py 8080      # écoute sur 127.0.0.1, données dans ./data.json
```

## Personnaliser

Titre, date, heure et adresse sont dans `static/index.html` (balise `<header>`).
