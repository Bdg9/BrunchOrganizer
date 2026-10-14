# Guide de déploiement pour Jad

But : mettre en ligne `https://brunch.tala.family`, une page où les invités du brunch du
dimanche 18 octobre (11h) notent qui apporte quoi. Merci d'avance !

Ce qu'il faut savoir avant de commencer :

- Un seul conteneur, Python 3.12, aucune dépendance, aucune base de données.
- Il écoute en **HTTP** sur le port **8080**. Le HTTPS est à faire côté reverse proxy.
- Il garde la liste dans un seul fichier, **`/data/data.json`**. Le dossier **`/data`** est le
  seul chemin qui a besoin d'un volume.
- **Pas d'authentification** : toute personne qui a le lien peut tout modifier. C'est voulu.
  Le lien n'est partagé que dans un groupe WhatsApp.
- L'image n'a pas encore été construite par Barbara (pas d'accès à Docker sur son poste).
  Le Dockerfile n'est donc pas testé : si le build échoue, dis-lui quelle est l'erreur.

## 1. Récupérer le code

```bash
git clone https://github.com/Bdg9/BrunchOrganizer.git
cd BrunchOrganizer
```

Si le dépôt est privé, Barbara doit d'abord t'ajouter dans Settings > Collaborators.

## 2. Construire l'image

```bash
docker build -t brunch .
```

## 3. Lancer le conteneur

Avec un volume nommé (le plus simple, les droits sont gérés par Docker) :

```bash
docker run -d --name brunch --restart unless-stopped \
  -p 127.0.0.1:8080:8080 \
  -v brunch-data:/data \
  brunch
```

Ou avec Compose, qui fait la même chose :

```bash
docker compose up -d --build
```

Le port est publié sur `127.0.0.1` seulement : on ne passe que par le reverse proxy.
Change `8080` à gauche si ce port est déjà pris sur ta machine.

Si tu préfères un dossier de l'hôte à un volume nommé, il doit appartenir à l'uid `10001`
(l'utilisateur du conteneur) :

```bash
sudo mkdir -p /srv/brunch && sudo chown 10001 /srv/brunch
# puis : -v /srv/brunch:/data
```

## 4. Vérifier en local

```bash
curl -i http://127.0.0.1:8080/api/state
```

Réponse attendue : `200` et `{"items": [], "signups": []}`.
Après un moment, `docker ps` doit aussi indiquer `(healthy)`.

## 5. DNS

Chez toi, pour `tala.family` : un enregistrement **A** (et **AAAA** si IPv6)
`brunch` → l'IP publique du serveur. Si tu as déjà un enregistrement joker `*.tala.family`,
rien à faire.

## 6. Reverse proxy avec HTTPS

Avec **Caddy** (certificat Let's Encrypt automatique) :

```
brunch.tala.family {
    reverse_proxy 127.0.0.1:8080
}
```

Avec **nginx** (certificat via certbot ou le tien) :

```nginx
server {
    server_name brunch.tala.family;
    listen 443 ssl;
    # ssl_certificate / ssl_certificate_key ...

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $remote_addr;
    }
}
```

Aucun en-tête spécial, aucun WebSocket : la page interroge `/api/state` toutes les 5 secondes.

Optionnel, utile puisque la page est ouverte à tous : limiter le débit par IP au niveau du
proxy (le serveur lui-même n'en fait pas).

## 7. Test final

1. Ouvrir `https://brunch.tala.family` sur un téléphone : on doit voir « Brunch au château »,
   le dimanche 18 octobre, 11h, Chemin de Renens 16.
2. Écrire un prénom, ajouter « Croissants », appuyer sur « + moi ».
3. Ouvrir la page dans un autre navigateur : la liste doit apparaître en moins de 5 secondes.
4. `docker rm -f brunch` puis relancer la commande de l'étape 3 : la liste doit être toujours là.
5. Supprimer le test (la croix à côté de l'item, après avoir retiré les prénoms).

## Exploitation

| Besoin | Commande |
|---|---|
| Voir les logs | `docker logs -f brunch` |
| Mettre à jour | `git pull && docker build -t brunch . && docker rm -f brunch` puis relancer l'étape 3 |
| Sauvegarder | copier `data.json` : `docker cp brunch:/data/data.json .` |
| Remettre la liste à zéro | `docker exec brunch rm /data/data.json` |
| Tout arrêter après le brunch | `docker rm -f brunch` (le volume `brunch-data` reste) |

## Si ça ne marche pas

- **Le build échoue** : envoyer l'erreur à Barbara.
- **`PermissionError` dans les logs** : le dossier monté sur `/data` n'est pas inscriptible par
  l'uid `10001` (voir étape 3).
- **502 / page blanche** : vérifier que le conteneur tourne (`docker ps`) et que le proxy vise
  bien le port publié.
- **La liste ne se met pas à jour** : vérifier que `/api/state` n'est pas mis en cache par le proxy
  (le serveur envoie `Cache-Control: no-store`).
