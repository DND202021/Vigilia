# Informations Serveur Vigilia

## Accès
- **Serveur**: 10.0.0.13
- **User SSH**: dnoiseux
- **Chemin projet**: `/home/dnoiseux/projects/Vigilia/Vigilia`

## URLs
- **Local**: http://10.0.0.13:83
- **Externe**: https://vigilia.4541f.duckdns.org
- **NPM**: http://10.0.0.13:81/nginx/proxy
- **Swagger**: https://vigilia.4541f.duckdns.org/api/docs

## Credentials Admin
- **Email**: admin@vigilia.com
- **Password**: Admin123Strong

## Conteneurs Docker
- `eriop-postgres` - Base de données PostgreSQL/TimescaleDB
- `eriop-redis` - Cache Redis
- `eriop-backend` - API FastAPI (port 8000)
- `eriop-frontend` - Frontend React (port 80)
- `eriop-nginx` - Reverse proxy (port 83)
- `nginx-proxy-manager-app-1` - NPM (port 81)

## Commandes de déploiement

### Rebuild Backend
```bash
ssh dnoiseux@10.0.0.13 "cd /home/dnoiseux/projects/Vigilia/Vigilia && git pull && docker compose -f docker-compose.portainer.yml build --no-cache backend && docker compose -f docker-compose.portainer.yml up -d backend"
```

### Rebuild Frontend
```bash
ssh dnoiseux@10.0.0.13 "cd /home/dnoiseux/projects/Vigilia/Vigilia && git pull && docker compose -f docker-compose.portainer.yml build --no-cache frontend && docker compose -f docker-compose.portainer.yml up -d frontend"
```

### Redémarrer un service
```bash
ssh dnoiseux@10.0.0.13 "docker restart eriop-backend"
ssh dnoiseux@10.0.0.13 "docker restart eriop-frontend"
```

### Voir les logs
```bash
ssh dnoiseux@10.0.0.13 "docker logs eriop-backend --tail 50"
ssh dnoiseux@10.0.0.13 "docker logs eriop-frontend --tail 50"
```

## Configuration NPM
- Forward Hostname: `eriop-nginx`
- Forward Port: `80`
- NPM est connecté au réseau Docker `eriop_eriop-external`
