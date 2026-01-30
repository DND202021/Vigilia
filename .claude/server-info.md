# Informations Serveur Vigilia

## Accès
- **Serveur**: 10.0.0.13
- **User SSH**: dnoiseux
- **Password SSH**: 4541linux
- **Chemin projet**: `/home/dnoiseux/projects/Vigilia/Vigilia`

## URLs
- **Local**: http://10.0.0.13:83
- **Externe**: https://vigilia.4541f.duckdns.org
- **NPM**: http://10.0.0.13:81
- **Portainer**: http://10.0.0.13:9000
- **n8n**: https://n8n.4541f.duckdns.org
- **Swagger**: https://vigilia.4541f.duckdns.org/api/docs

## Credentials Vigilia Admin
- **Email**: admin@vigilia.com
- **Password**: Admin123Strong

## Credentials NPM (Nginx Proxy Manager)
- **Email**: noiseux@gmail.com
- **Password**: 4541linux

## Credentials n8n
- **URL**: https://n8n.4541f.duckdns.org
- **Email**: (set by user during owner setup)
- **Password**: (set by user during owner setup)

## Conteneurs Docker
- `eriop-postgres` - Base de données PostgreSQL/TimescaleDB
- `eriop-redis` - Cache Redis
- `eriop-backend` - API FastAPI (port 8000)
- `eriop-frontend` - Frontend React (port 80)
- `eriop-nginx` - Reverse proxy (port 83)
- `nginx-proxy-manager-app-1` - NPM (port 81)
- `n8n` - Workflow automation (port 5678, via NPM)
- `portainer` - Container management (port 9000)

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

---

## n8n Configuration (Updated 2026-01-29)

### Container Settings
The n8n container runs with these environment variables:
```bash
docker run -d \
  --name n8n \
  --network nginx-proxy-manager_default \
  --restart unless-stopped \
  -v n8n_data:/home/node/.n8n \
  -e N8N_HOST=n8n.4541f.duckdns.org \
  -e N8N_PORT=5678 \
  -e N8N_PROTOCOL=https \
  -e N8N_TRUST_PROXY=true \
  -e WEBHOOK_URL=https://n8n.4541f.duckdns.org/ \
  -e TZ=America/Toronto \
  -e N8N_HIDE_USAGE_PAGE=true \
  -e N8N_PERSONALIZATION_ENABLED=false \
  -e N8N_VERSION_NOTIFICATIONS_ENABLED=false \
  -e N8N_DIAGNOSTICS_ENABLED=false \
  -e N8N_HIRING_BANNER_ENABLED=false \
  n8nio/n8n:latest
```

### SSL Certificate
- Let's Encrypt certificate via NPM
- Expires: April 28, 2026
- Certificate ID in NPM: 12

---

## PENDING: Email Cleanup Workflow Project

### Status
**Waiting for IT Admin approval** for Microsoft OAuth app

### What was done
1. n8n container fixed and running with proper proxy settings
2. Azure App registered: `n8n-email-cleanup`
3. Redirect URI configured: `https://n8n.4541f.duckdns.org/rest/oauth2-credential/callback`

### Azure App Permissions Required
- `Mail.Read` - Read emails
- `Mail.ReadWrite` - Move/delete emails
- `MailboxSettings.ReadWrite` - Access folder settings

### What IT Admin needs to do
1. Go to Azure Portal → Enterprise Applications → find `n8n-email-cleanup`
2. Click Permissions → Grant admin consent for the organization
3. Or approve when user tries to sign in

### Next Steps (after IT approval)
1. In n8n: Settings → Credentials → Add "Microsoft Outlook OAuth2"
2. Enter Azure Client ID and Client Secret
3. Click "Sign in with Microsoft" and authorize
4. Import the email cleanup workflow (AI-assisted classification)
5. Configure folders: Work, Personal, Finance, Newsletters, Notifications, Trash

### Workflow Design
- **Trigger**: Manual or scheduled
- **Get Emails**: Fetch from Inbox (batches of 50)
- **AI Classification**: Use Claude API to categorize emails
- **Categories**: WORK, PERSONAL, FINANCE, NEWSLETTERS, NOTIFICATIONS, TRASH
- **Actions**: Move to appropriate folders, trash goes to Deleted Items

### User has
- Anthropic API key (for Claude classification)
- Azure app Client ID and Secret (pending IT approval)
