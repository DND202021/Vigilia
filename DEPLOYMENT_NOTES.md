# Deployment Notes - ERIOP/Vigilia

## Critical: Network Configuration

When rebuilding containers, you MUST ensure proper network connectivity:

### Required Network Connections for eriop-frontend:

1. **eriop_eriop-net** - For backend communication (alias: `backend`)
2. **nginx-proxy-manager_default** - For external proxy (alias: `eriop-nginx`)

### After Rebuilding Frontend Container:

```bash
# Stop and remove old container
docker stop eriop-frontend && docker rm eriop-frontend

# Build new image
docker build -t eriop-frontend:latest --build-arg VITE_API_URL=/api/v1 --build-arg VITE_WS_URL=/ws .

# Run container on main network
docker run -d --name eriop-frontend --network eriop_eriop-net -p 83:80 eriop-frontend:latest

# CRITICAL: Connect to proxy network with alias
docker network connect --alias eriop-nginx nginx-proxy-manager_default eriop-frontend

# CRITICAL: Ensure backend alias exists
docker network connect --alias backend eriop_eriop-net eriop-backend 2>/dev/null || true
```

### Verification Commands:

```bash
# Check all networks are connected
docker inspect eriop-frontend --format '{{range $net, $conf := .NetworkSettings.Networks}}{{$net}}: {{$conf.IPAddress}} aliases={{$conf.Aliases}}{{"\n"}}{{end}}'

# Test internal connectivity (backend)
docker exec eriop-frontend wget -q -O- http://backend:8000/health

# Test proxy can reach frontend
docker exec nginx-proxy-manager-app-1 curl -s http://eriop-nginx:80/nginx-health

# Test external URL
curl -sI https://vigilia.4541f.duckdns.org/
```

## Root Cause of 502 Errors

The nginx-proxy-manager is configured to forward `vigilia.4541f.duckdns.org` to hostname `eriop-nginx` on port 80.

When containers are rebuilt:
- They get new IP addresses
- Network connections are lost
- Network aliases are lost

Without the `eriop-nginx` alias on the `nginx-proxy-manager_default` network, the proxy cannot resolve the hostname, causing 502 Bad Gateway errors.

## Container Dependencies

```
nginx-proxy-manager
    └── eriop-frontend (alias: eriop-nginx)
            └── eriop-backend (alias: backend)
                    ├── eriop-postgres
                    └── eriop-redis
```

## Local vs External Access

- **Local**: http://10.0.0.13:83/ - Direct to eriop-frontend port mapping
- **External**: https://vigilia.4541f.duckdns.org/ - Through nginx-proxy-manager

Local access may work while external fails if network aliases are missing.

## WebSocket / Socket.IO Configuration

The frontend uses Socket.IO for real-time updates. The nginx configuration must proxy `/socket.io/` to the backend.

### nginx.conf and nginx.conf.template must include:

```nginx
# Socket.IO proxy (for real-time updates)
location /socket.io/ {
    proxy_pass http://backend:8000/socket.io/;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_read_timeout 86400;
    proxy_buffering off;
}
```

### Verify WebSocket connectivity:

```bash
# Test Socket.IO endpoint (should return JSON with sid)
curl -s "https://vigilia.4541f.duckdns.org/socket.io/?EIO=4&transport=polling"
# Expected: 0{"sid":"xxx","upgrades":["websocket"],...}
```

### Common WebSocket Issues:
1. **Missing /socket.io/ location** - Frontend can't connect to real-time updates
2. **Missing Upgrade headers** - WebSocket upgrade fails, falls back to polling
3. **nginx-proxy-manager not forwarding WS** - Check "Websockets Support" is enabled in proxy host settings
4. **WebSocket-only transport fails** - Frontend should use `transports: ['polling', 'websocket']` to allow fallback
5. **HTTP/2 conflicts** - WebSocket upgrade works differently with HTTP/2; ensure proxy handles this

### Frontend Socket.IO Configuration (src/hooks/useWebSocket.ts):
```typescript
const socket = io(wsUrl, {
  auth: { token },
  transports: ['polling', 'websocket'],  // Allow fallback to polling
  reconnection: true,
  reconnectionAttempts: 5,
  reconnectionDelay: 1000,
});
```

## File Upload Configuration

Floor plan uploads support files up to 50MB. nginx must be configured:

### nginx.conf requirements:
```nginx
# At server level:
client_max_body_size 50M;

# In /api/ location:
proxy_connect_timeout 120s;
proxy_send_timeout 120s;
proxy_read_timeout 120s;
proxy_request_buffering off;
```

### nginx-proxy-manager custom config (/data/nginx/custom/server_proxy.conf):
```nginx
client_max_body_size 100M;
proxy_connect_timeout 120s;
proxy_send_timeout 120s;
proxy_read_timeout 120s;
proxy_request_buffering off;
```

Apply with: `docker exec nginx-proxy-manager-app-1 nginx -s reload`

## Quick Fix Script

Save this as `reconnect-networks.sh`:

```bash
#!/bin/bash
# Reconnect ERIOP containers to required networks after rebuild

# Frontend to proxy network
docker network disconnect nginx-proxy-manager_default eriop-frontend 2>/dev/null || true
docker network connect --alias eriop-nginx nginx-proxy-manager_default eriop-frontend

# Backend alias for frontend
docker network connect --alias backend eriop_eriop-net eriop-backend 2>/dev/null || true

echo "Networks reconnected. Verify with:"
echo "curl -sI https://vigilia.4541f.duckdns.org/"
```

## Complete Frontend Rebuild (One-Liner)

```bash
cd /workspace/Vigilia/Vigilia/src/frontend && \
docker stop eriop-frontend 2>/dev/null; docker rm eriop-frontend 2>/dev/null; \
docker build --no-cache -t eriop-frontend:latest --build-arg VITE_API_URL=/api/v1 --build-arg VITE_WS_URL=/ws . && \
docker run -d --name eriop-frontend --network eriop_eriop-net -p 83:80 eriop-frontend:latest && \
docker network connect --alias eriop-nginx nginx-proxy-manager_default eriop-frontend && \
docker network connect --alias backend eriop_eriop-net eriop-backend 2>/dev/null; \
echo "Done! Verify: curl -sI https://vigilia.4541f.duckdns.org/"
```

## Full Verification Checklist

After deployment, verify ALL of these:

```bash
# 1. Container health
docker ps --format "table {{.Names}}\t{{.Status}}" | grep eriop

# 2. Network connections
docker inspect eriop-frontend --format '{{range $net, $conf := .NetworkSettings.Networks}}{{$net}}: aliases={{$conf.Aliases}}{{"\n"}}{{end}}'

# 3. External access (should return 200)
curl -sI https://vigilia.4541f.duckdns.org/ | head -1

# 4. Favicon (should return 200)
curl -sI https://vigilia.4541f.duckdns.org/favicon.ico | head -1

# 5. API connectivity (should return JSON)
curl -s https://vigilia.4541f.duckdns.org/health

# 6. Socket.IO (should return 0{"sid":...})
curl -s "https://vigilia.4541f.duckdns.org/socket.io/?EIO=4&transport=polling"
```

## File Upload / Floor Plan Storage

The backend stores uploaded floor plans in `/data/buildings/`. This directory must be writable by the container user.

### Common Issue: Permission Denied on Upload

**Symptom:** 500 error when uploading floor plans with:
```
PermissionError: [Errno 13] Permission denied: '/data/buildings/...'
```

**Root Cause:** The `building_files` Docker volume is created with root ownership, but the backend container runs as user `eriop` (uid=1000).

**Solution:** Fix permissions on the volume:
```bash
docker exec -u root eriop-backend chown -R eriop:eriop /data
```

**Prevention:** Add this to docker-compose.portainer.yml backend service:
```yaml
# After container starts, ensure correct ownership
command: sh -c "chown -R eriop:eriop /data 2>/dev/null || true && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"
```

Or create an entrypoint script that handles permissions.

### Verification:
```bash
# Check ownership
docker exec eriop-backend ls -la /data/buildings

# Test upload (requires valid auth token)
curl -X POST "https://vigilia.4541f.duckdns.org/api/v1/buildings/{id}/floor-plans/upload?floor_number=1" \
  -H "Authorization: Bearer {token}" \
  -F "file=@floorplan.png"
```

---

## Recurring Issues Checklist

When debugging ERIOP issues, check these common problems:

| Issue | Symptom | Quick Fix |
|-------|---------|-----------|
| 502 Bad Gateway | External URL unreachable | `docker network connect --alias eriop-nginx nginx-proxy-manager_default eriop-frontend` |
| Socket.IO errors | Console spam, WS connection failed | Ensure nginx.conf has `/socket.io/` location block |
| Floor plan upload fails | 500 error, permission denied | `docker exec -u root eriop-backend chown -R eriop:eriop /data` |
| API 401 errors | Auth not working | Check JWT secret matches, token not expired |
| Container unhealthy | Health check failing | Check `docker logs <container>` for errors |

---
Last updated: 2026-01-25
