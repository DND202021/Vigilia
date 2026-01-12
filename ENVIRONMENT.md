# Vigilia/ERIOP - Environment Documentation

## Server Information
- **Server**: 4541-linux-server (Linux local)
- **IP Address**: 10.0.0.13
- **User**: dnoiseux
- **Project Path**: ~/projects/Vigilia/Vigilia

## Docker Configuration
- **Docker Compose Version**: v2 (use `docker compose` not `docker-compose`)
- **Compose File**: `docker-compose.portainer.yml`
- **Project Name**: eriop (from COMPOSE_PROJECT_NAME in .env)

## Ports
- **Frontend/Nginx**: Port 83 (external) -> 80 (internal)
- **HTTPS**: Port 8443 (if SSL enabled)
- **Backend**: Port 8000 (internal only, proxied through nginx)

## URLs
- **Frontend**: http://10.0.0.13:83
- **API**: http://10.0.0.13:83/api/v1/
- **WebSocket**: ws://10.0.0.13:83/socket.io/
- **Alternative domain**: eriop.local (if configured in hosts)

## Environment Variables (.env)
```
DB_USER=eriop
DB_PASSWORD=eLMpxoBYiV5AbFK8FWxlY52z7rMn9dM8
REDIS_PASSWORD=7a0wciL0dd61RXP0H5to34GECOnS1Ge
SECRET_KEY=jX2TSNS1d0HpilMCyUK9VK3GECN7b4aC6D9PtpVTDAWhL3xP6tg3zolzScKyJy
ENVIRONMENT=production
LOG_LEVEL=info
CORS_ORIGINS_STR=http://localhost,http://10.0.0.13,http://10.0.0.13:83,https://vigilia.4541f.duckdns.org
VITE_API_URL=/api/v1
VITE_WS_URL=
COMPOSE_PROJECT_NAME=eriop
```

## Git Repository
- **Remote**: https://github.com/DND202021/Vigilia.git
- **Branch**: main

## Architecture
- **Frontend**: React 18 + TypeScript + Vite
- **Backend**: Python 3.11 + FastAPI + SQLAlchemy
- **Database**: PostgreSQL + TimescaleDB
- **Cache**: Redis
- **Message Queue**: MQTT (Mosquitto)
- **Reverse Proxy**: Nginx

## Common Commands
```bash
# Navigate to project
cd ~/projects/Vigilia/Vigilia

# Pull latest code
git pull origin main

# Rebuild containers
docker compose -f docker-compose.portainer.yml build --no-cache backend frontend

# Start/restart services
docker compose -f docker-compose.portainer.yml up -d

# View logs
docker compose -f docker-compose.portainer.yml logs -f backend
docker compose -f docker-compose.portainer.yml logs -f nginx

# Check container status
docker compose -f docker-compose.portainer.yml ps
```

## Known Issues & Solutions
1. **502 Bad Gateway**: Usually means backend container crashed or isn't starting
   - Check backend logs: `docker compose -f docker-compose.portainer.yml logs backend`
   - Ensure python-socketio is installed in Dockerfile (not just pyproject.toml!)
   - The Dockerfile has hardcoded pip installs, must add new packages there too

2. **CORS Errors**: Ensure CORS_ORIGINS_STR includes the correct origin with port

3. **WebSocket Connection Failed**:
   - VITE_WS_URL should be empty to use window.location.origin
   - Nginx must have /socket.io/ route configured

4. **Nginx not starting**:
   - Removed `profiles: - nginx` from docker-compose so it starts by default

## Important Notes
- The backend Dockerfile has HARDCODED pip install list - when adding new Python packages:
  1. Add to pyproject.toml
  2. ALSO add to src/backend/Dockerfile
- VITE_WS_URL in docker-compose build args should be empty (not a URL) to use window.location.origin
