# Guide de Déploiement - Vigilia sur Serveur Local avec Portainer

## Informations du Serveur

| Paramètre | Valeur |
|-----------|--------|
| IP du serveur | `10.0.0.13` |
| Utilisateur | `dnoiseux` |
| Chemin du projet | `/home/dnoiseux/projects/Vigilia/Vigilia` |
| Portainer | `https://10.0.0.13:9443` |
| Application | `http://10.0.0.13` |

---

## Prérequis

- Docker installé (vérifié : v29.1.3)
- Docker Compose installé
- Accès SSH au serveur

---

## Étapes de Déploiement

### 1. Connexion au serveur

Depuis Windows PowerShell :
```powershell
ssh dnoiseux@10.0.0.13
```

### 2. Aller dans le dossier du projet

```bash
cd /home/dnoiseux/projects/Vigilia/Vigilia
```

### 3. Créer le fichier .env

Créer le fichier avec nano :
```bash
nano .env
```

Contenu du fichier `.env` :
```
DB_USER=eriop
DB_PASSWORD=eLMpxoBYiV5AbFK8FWxlY52z7rMn9dM8
REDIS_PASSWORD=7a0wciL0dd61RXP0H5to34GECOnS1Ge
SECRET_KEY=jX2TSNS1d0HpilMCyUK9VK3GECN7b4aC6D9PtpVTDAWhL3xP6tg3zolzScKyJy
ENVIRONMENT=production
LOG_LEVEL=info
CORS_ORIGINS=http://localhost,http://10.0.0.13
VITE_API_URL=/api/v1
VITE_WS_URL=ws://10.0.0.13
COMPOSE_PROJECT_NAME=eriop
```

Sauvegarder : `Ctrl+O` → `Entrée` → `Ctrl+X`

### 4. Corriger les permissions (si cloné avec sudo)

```bash
sudo chown -R dnoiseux:dnoiseux /home/dnoiseux/projects/Vigilia/Vigilia
```

### 5. Lancer le déploiement

```bash
docker compose -f docker-compose.portainer.yml up -d --build
```

**Note :** La première exécution peut prendre 5-10 minutes (téléchargement des images + build).

### 6. Vérifier le statut

```bash
docker compose -f docker-compose.portainer.yml ps
```

Tous les services doivent être "Up" ou "healthy".

### 7. Voir les logs (si problème)

```bash
docker compose -f docker-compose.portainer.yml logs -f
```

Appuyer sur `Ctrl+C` pour quitter les logs.

---

## Commandes Utiles

### Arrêter l'application
```bash
docker compose -f docker-compose.portainer.yml down
```

### Redémarrer l'application
```bash
docker compose -f docker-compose.portainer.yml restart
```

### Reconstruire après modification du code
```bash
docker compose -f docker-compose.portainer.yml up -d --build
```

### Voir les logs d'un service spécifique
```bash
docker compose -f docker-compose.portainer.yml logs -f backend
docker compose -f docker-compose.portainer.yml logs -f frontend
docker compose -f docker-compose.portainer.yml logs -f postgres
```

### Supprimer tout (containers + volumes)
```bash
docker compose -f docker-compose.portainer.yml down -v
```

---

## URLs d'Accès

| Service | URL |
|---------|-----|
| Application Web | http://10.0.0.13:83 |
| API Backend | http://10.0.0.13:83/api/v1 |
| Portainer | https://10.0.0.13:9443 |

---

## Créer le Premier Utilisateur

Après le déploiement, exécuter les migrations puis créer un utilisateur :

```bash
# Exécuter les migrations
docker compose -f docker-compose.portainer.yml exec backend alembic upgrade head

# Créer un utilisateur admin
curl -X POST http://localhost:83/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@vigilia.com", "password": "Admin123!@#Strong", "full_name": "Admin User"}'
```

**Identifiants par défaut :**
- Email: `admin@vigilia.com`
- Mot de passe: `Admin123!@#Strong`

---

## Dépannage

### "Permission denied" sur Docker
```bash
sudo usermod -aG docker dnoiseux
# Puis déconnexion/reconnexion SSH
```

### Erreur de build
Vérifier les logs :
```bash
docker compose -f docker-compose.portainer.yml logs --tail=50
```

### Port 80 déjà utilisé
Vérifier ce qui utilise le port :
```bash
sudo lsof -i :80
```

### Réinitialiser complètement
```bash
docker compose -f docker-compose.portainer.yml down -v
docker system prune -a
docker compose -f docker-compose.portainer.yml up -d --build
```

---

## Structure du Projet

```
/home/dnoiseux/projects/Vigilia/Vigilia/
├── .env                          # Variables d'environnement (créé manuellement)
├── docker-compose.portainer.yml  # Config Docker pour Portainer
├── src/
│   ├── backend/                  # FastAPI (Python)
│   │   └── Dockerfile
│   └── frontend/                 # React (TypeScript)
│       └── Dockerfile
└── infrastructure/
    └── nginx/                    # Configuration Nginx
```

---

*Guide créé le 11 janvier 2026*
