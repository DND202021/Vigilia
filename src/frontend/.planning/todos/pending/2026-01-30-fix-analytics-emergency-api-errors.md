---
created: 2026-01-30T15:15
title: Fix Analytics API 401 errors
area: api
files:
  - src/backend/app/api/buildings.py
  - src/frontend/src/components/analytics/BuildingAnalyticsDashboard.tsx
---

## Problem

Analytics Tab returns 401 (Unauthorized) errors.

### Error: Analytics Tab - 401 errors
- **Endpoint:** `GET /api/v1/buildings/{id}/analytics?days=7`
- **Symptoms:** 
  - Returns 401 (Unauthorized)
  - Frontend shows "Failed to fetch" error
- **Possible causes:**
  - Token expired, user needs to re-login
  - Token refresh not working correctly

## Solution

~~Emergency Plan: **FIXED** - API paths corrected to use `/emergency-planning/` prefix~~

Analytics: User should try logging out and back in. If issue persists, investigate token refresh logic.
