---
created: 2026-01-30T15:15
title: Fix Analytics and Emergency Plan API errors
area: api
files:
  - src/backend/app/api/buildings.py
  - src/backend/app/services/building_analytics.py
  - src/frontend/src/components/analytics/BuildingAnalyticsDashboard.tsx
  - src/frontend/src/pages/BuildingDetailPage.tsx
---

## Problem

Two backend API endpoints are failing in the BuildingDetailPage:

### Error #1: Analytics Tab - 503/401 errors
- **Endpoint:** `GET /api/v1/buildings/{id}/analytics?days=7`
- **Symptoms:** 
  - First attempt returns 503 (Service Unavailable)
  - Retry returns 401 (Unauthorized)
  - Frontend shows "Failed to fetch" error
- **Possible causes:**
  - Backend analytics service not running/crashing
  - Token refresh race condition
  - Missing analytics data for building

### Error #2: Emergency Tab - Server Unavailable
- **Endpoint:** `GET /api/v1/buildings/{id}/emergency-plan`
- **Symptoms:**
  - Multiple toast notifications: "Unable to load emergency plan. Server is unavailable"
  - Loading spinner never completes
- **Possible causes:**
  - Emergency plan service not responding
  - No emergency plan data exists for this building
  - Backend returning 503 without proper error handling

## Solution

1. Check backend container logs for errors:
   ```bash
   ssh dnoiseux@10.0.0.13 "docker logs eriop-backend --tail 100"
   ```

2. Test endpoints directly to verify backend health:
   ```bash
   curl -H "Authorization: Bearer <token>" https://vigilia.4541f.duckdns.org/api/v1/buildings/{id}/analytics
   curl -H "Authorization: Bearer <token>" https://vigilia.4541f.duckdns.org/api/v1/buildings/{id}/emergency-plan
   ```

3. Check if backend is overloaded or has memory issues

4. Verify database queries for analytics/emergency data aren't timing out

5. Add better error handling for 503 responses in frontend
