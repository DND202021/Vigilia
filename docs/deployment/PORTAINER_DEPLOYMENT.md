# Portainer Deployment Guide for ERIOP

Deploy ERIOP on your local Linux server using Portainer with external access.

## Quick Start (Local Network)

### 1. Clone Repository on Your Server

```bash
cd /opt
git clone https://github.com/DND202021/Vigilia.git
cd Vigilia
```

### 2. Create Environment File

```bash
cp .env.example .env
nano .env
```

Update these values:
```env
DB_PASSWORD=your_secure_db_password_here
REDIS_PASSWORD=your_secure_redis_password_here
SECRET_KEY=generate_64_character_random_string_here
SERVER_IP=192.168.1.100  # Your server's LAN IP
```

Generate a secure secret key:
```bash
openssl rand -hex 32
```

### 3. Deploy via Portainer

1. Open Portainer: `http://YOUR_SERVER_IP:9000`
2. Go to **Stacks** → **Add Stack**
3. Name: `eriop`
4. Choose **Upload** and select `docker-compose.local.yml`
   - OR use **Repository** and point to GitHub
5. Add environment variables from your `.env` file
6. Click **Deploy the stack**

### 4. Access ERIOP

- Open `http://YOUR_SERVER_IP` in your browser
- Default credentials: Create first user via API or database

---

## External Access Options

### Option A: Cloudflare Tunnel (Recommended - Free & Secure)

No port forwarding needed. Cloudflare handles SSL automatically.

#### 1. Install Cloudflared

```bash
# Add to docker-compose.local.yml
  cloudflared:
    image: cloudflare/cloudflared:latest
    container_name: eriop-tunnel
    restart: unless-stopped
    command: tunnel run
    environment:
      TUNNEL_TOKEN: ${CLOUDFLARE_TUNNEL_TOKEN}
    networks:
      - eriop-net
```

#### 2. Create Tunnel

1. Go to https://one.dash.cloudflare.com
2. **Zero Trust** → **Access** → **Tunnels**
3. Click **Create a tunnel**
4. Name: `eriop`
5. Copy the tunnel token

#### 3. Configure Routes

In Cloudflare dashboard, add public hostname:
- Subdomain: `eriop`
- Domain: `yourdomain.com`
- Service: `http://nginx:80`

#### 4. Update Environment

```env
CLOUDFLARE_TUNNEL_TOKEN=your_tunnel_token_here
CORS_ORIGINS=https://eriop.yourdomain.com
```

Access at: `https://eriop.yourdomain.com`

---

### Option B: Port Forwarding + Let's Encrypt SSL

#### 1. Router Configuration

Forward these ports to your server:
- Port 80 → Server IP:80
- Port 443 → Server IP:443

#### 2. Get Domain

- Use a free dynamic DNS: DuckDNS, No-IP, or Dynu
- Or point your domain's A record to your public IP

#### 3. Deploy with SSL

Use `docker-compose.portainer.yml` which includes Traefik labels.

Add Traefik to your stack:
```yaml
  traefik:
    image: traefik:v2.10
    container_name: eriop-traefik
    restart: unless-stopped
    command:
      - "--api.dashboard=true"
      - "--providers.docker=true"
      - "--providers.docker.exposedbydefault=false"
      - "--entrypoints.web.address=:80"
      - "--entrypoints.websecure.address=:443"
      - "--certificatesresolvers.letsencrypt.acme.httpchallenge=true"
      - "--certificatesresolvers.letsencrypt.acme.httpchallenge.entrypoint=web"
      - "--certificatesresolvers.letsencrypt.acme.email=${ACME_EMAIL}"
      - "--certificatesresolvers.letsencrypt.acme.storage=/letsencrypt/acme.json"
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - traefik_certs:/letsencrypt
    networks:
      - eriop-external

volumes:
  traefik_certs:
```

#### 4. Update Environment

```env
DOMAIN=eriop.yourdomain.com
ACME_EMAIL=your@email.com
CORS_ORIGINS=https://eriop.yourdomain.com
VITE_API_URL=https://eriop.yourdomain.com/api/v1
```

---

### Option C: Tailscale (Private Access)

Access ERIOP from anywhere via Tailscale's private network.

#### 1. Install Tailscale on Server

```bash
curl -fsSL https://tailscale.com/install.sh | sh
tailscale up
```

#### 2. Get Tailscale IP

```bash
tailscale ip -4
# Example: 100.x.x.x
```

#### 3. Update Environment

```env
SERVER_IP=100.x.x.x  # Tailscale IP
CORS_ORIGINS=http://100.x.x.x
```

Access at: `http://100.x.x.x` from any device on your Tailnet

---

## Portainer Stack Management

### View Logs

1. **Stacks** → `eriop` → **Editor** tab shows compose file
2. Click on any container → **Logs**

### Update Stack

```bash
cd /opt/Vigilia
git pull
```

Then in Portainer:
1. **Stacks** → `eriop`
2. Click **Pull and redeploy**

### Run Database Migrations

1. Go to **Containers** → `eriop-backend`
2. Click **Console** → **Connect**
3. Run:
```bash
alembic upgrade head
```

### Backup Database

```bash
docker exec eriop-db pg_dump -U eriop eriop > backup.sql
```

### Restore Database

```bash
cat backup.sql | docker exec -i eriop-db psql -U eriop eriop
```

---

## Environment Variables Reference

| Variable | Description | Example |
|----------|-------------|---------|
| `DB_PASSWORD` | PostgreSQL password | `SecurePass123!` |
| `REDIS_PASSWORD` | Redis password | `RedisPass456!` |
| `SECRET_KEY` | JWT signing key (64 chars) | `openssl rand -hex 32` |
| `SERVER_IP` | Server LAN/Tailscale IP | `192.168.1.100` |
| `DOMAIN` | Public domain (if using SSL) | `eriop.example.com` |
| `CORS_ORIGINS` | Allowed origins | `http://192.168.1.100` |
| `CLOUDFLARE_TUNNEL_TOKEN` | Cloudflare tunnel token | `eyJ...` |

---

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker logs eriop-backend

# Check if ports are in use
sudo netstat -tlnp | grep :80
```

### Database Connection Failed

```bash
# Verify postgres is healthy
docker exec eriop-db pg_isready -U eriop

# Check connection from backend
docker exec eriop-backend python -c "from app.core.config import settings; print(settings.database_url)"
```

### Can't Access from Browser

1. Check firewall:
```bash
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
```

2. Check container network:
```bash
docker network inspect eriop-net
```

### CORS Errors

Update `CORS_ORIGINS` to include exact URL:
```env
CORS_ORIGINS=http://192.168.1.100,http://eriop.local
```

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Your Linux Server                         │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────┐   │
│  │                    Portainer                         │   │
│  │  ┌─────────────────────────────────────────────┐    │   │
│  │  │              ERIOP Stack                     │    │   │
│  │  │                                              │    │   │
│  │  │  ┌─────────┐      ┌─────────┐               │    │   │
│  │  │  │  Nginx  │ ──── │ Backend │               │    │   │
│  │  │  │ :80/:443│      │ FastAPI │               │    │   │
│  │  │  └────┬────┘      └────┬────┘               │    │   │
│  │  │       │                │                     │    │   │
│  │  │  ┌────┴────┐      ┌────┴────┐  ┌─────────┐ │    │   │
│  │  │  │Frontend │      │Postgres │  │  Redis  │ │    │   │
│  │  │  │  React  │      │TimescaleDB│ │         │ │    │   │
│  │  │  └─────────┘      └─────────┘  └─────────┘ │    │   │
│  │  └─────────────────────────────────────────────┘    │   │
│  └─────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│                External Access Options                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Cloudflare  │  │Port Forward  │  │  Tailscale   │      │
│  │    Tunnel    │  │ + SSL Cert   │  │   (VPN)      │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

---

## Security Recommendations

1. **Change default passwords** - Never use defaults in production
2. **Use Cloudflare Tunnel** - Avoids exposing ports directly
3. **Enable firewall** - Only allow necessary ports
4. **Regular updates** - Keep containers and host updated
5. **Backup regularly** - Automate database backups
6. **Monitor logs** - Check for suspicious activity
