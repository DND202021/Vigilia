# Railway Deployment Guide for ERIOP

This guide walks you through deploying ERIOP to Railway.

## Prerequisites

- Railway account (https://railway.app)
- GitHub repository connected to Railway
- Railway CLI (optional): `npm install -g @railway/cli`

## Architecture on Railway

```
┌─────────────────────────────────────────────────────────┐
│                    Railway Project                       │
├─────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐ │
│  │ Frontend │  │ Backend  │  │ Postgres │  │  Redis  │ │
│  │  (Nginx) │  │ (FastAPI)│  │          │  │         │ │
│  └──────────┘  └──────────┘  └──────────┘  └─────────┘ │
└─────────────────────────────────────────────────────────┘
```

## Step-by-Step Deployment

### 1. Create Railway Project

1. Go to https://railway.app/new
2. Click "Deploy from GitHub repo"
3. Select your `Vigilia` repository
4. Railway will detect the monorepo structure

### 2. Add PostgreSQL Database

1. In your Railway project, click "New"
2. Select "Database" → "PostgreSQL"
3. Railway auto-generates `DATABASE_URL`

### 3. Add Redis

1. Click "New" → "Database" → "Redis"
2. Railway auto-generates `REDIS_URL`

### 4. Deploy Backend Service

1. Click "New" → "GitHub Repo" → Select `Vigilia`
2. Configure the service:
   - **Root Directory**: `src/backend`
   - **Build Command**: (auto-detected from Dockerfile)

3. Add environment variables (Settings → Variables):

```env
SECRET_KEY=<generate-a-secure-random-string-64-chars>
ENVIRONMENT=production
CORS_ORIGINS=https://your-frontend.up.railway.app
LOG_LEVEL=info
```

4. Railway auto-links `DATABASE_URL` and `REDIS_URL` from the databases

### 5. Deploy Frontend Service

1. Click "New" → "GitHub Repo" → Select `Vigilia`
2. Configure the service:
   - **Root Directory**: `src/frontend`
   - **Build Command**: (auto-detected from Dockerfile)

3. Add build arguments (Settings → Variables):

```env
VITE_API_URL=https://your-backend.up.railway.app/api/v1
VITE_WS_URL=wss://your-backend.up.railway.app
```

### 6. Configure Networking

1. For each service, go to Settings → Networking
2. Click "Generate Domain" to get a public URL
3. Update `CORS_ORIGINS` in backend with the frontend domain
4. Update `VITE_API_URL` in frontend with the backend domain

## Environment Variables Reference

### Backend Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection (auto) | `postgresql://...` |
| `REDIS_URL` | Redis connection (auto) | `redis://...` |
| `SECRET_KEY` | JWT signing key | `<64-char-random>` |
| `ENVIRONMENT` | Environment mode | `production` |
| `CORS_ORIGINS` | Allowed origins | `https://frontend.railway.app` |
| `LOG_LEVEL` | Logging level | `info` |

### Frontend Variables (Build-time)

| Variable | Description | Example |
|----------|-------------|---------|
| `VITE_API_URL` | Backend API URL | `https://backend.railway.app/api/v1` |
| `VITE_WS_URL` | WebSocket URL | `wss://backend.railway.app` |

## Using Railway CLI

```bash
# Login to Railway
railway login

# Link to project
railway link

# Deploy backend
cd src/backend
railway up

# Deploy frontend
cd src/frontend
railway up

# View logs
railway logs

# Open shell
railway shell
```

## Database Migrations

Run migrations after deploying the backend:

```bash
# Via Railway CLI
cd src/backend
railway run alembic upgrade head

# Or via Railway dashboard
# Go to Backend service → Settings → Run Command
# Add: alembic upgrade head
```

## Custom Domain Setup

1. Go to service Settings → Networking
2. Click "Custom Domain"
3. Add your domain (e.g., `app.eriop.example.com`)
4. Configure DNS:
   - Add CNAME record pointing to `*.up.railway.app`
   - Railway handles SSL automatically

## Monitoring & Logs

- **Logs**: Railway Dashboard → Service → Logs tab
- **Metrics**: Railway Dashboard → Service → Metrics tab
- **Health**: Backend exposes `/health` endpoint

## Scaling

Railway supports horizontal scaling:

1. Go to Service Settings
2. Adjust "Replicas" (requires Pro plan)
3. Railway handles load balancing automatically

## Estimated Costs

Railway pricing (as of 2025):
- **Hobby Plan**: $5/month includes $5 credits
- **Pro Plan**: $20/month + usage-based pricing

Estimated monthly cost for ERIOP:
- Backend: ~$5-10/month
- Frontend: ~$2-5/month
- PostgreSQL: ~$5-10/month
- Redis: ~$3-5/month
- **Total**: ~$15-30/month for small deployments

## Troubleshooting

### Build Fails

1. Check build logs in Railway dashboard
2. Ensure Dockerfile paths are correct
3. Verify all dependencies are in requirements/package.json

### Database Connection Issues

1. Verify `DATABASE_URL` is linked correctly
2. Check if migrations ran successfully
3. Ensure database is in same project (private networking)

### CORS Errors

1. Update `CORS_ORIGINS` with exact frontend URL
2. Include both `http://` and `https://` if needed
3. Restart backend after changes

### Container Health Check Fails

1. Check if service starts correctly in logs
2. Verify health endpoint returns 200
3. Increase `start-period` if startup is slow

## Quick Deploy Button

Add this to your README for one-click deploy:

```markdown
[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/eriop)
```

(Requires creating a Railway template first)
