---
created: 2026-01-30T14:40
title: Fix floor plan image loading failure
area: ui
files:
  - src/frontend/src/components/buildings/FloorPlanEditor.tsx
  - src/frontend/src/components/buildings/FloorPlanViewer.tsx
  - src/backend/app/api/buildings.py
---

## Problem

Floor plan images fail to load in the building detail page. The console shows "Failed to load floor plan image" errors. This may be related to:

1. CORS issues with image URLs from the backend
2. Image path/URL construction issues
3. Backend serving issues for uploaded floor plan files
4. Network errors when backend is unavailable (503 errors seen in session)

The issue was observed while testing the BuildingDetailPage after deploying backend changes.

## Solution

TBD - Needs investigation:

1. Check how floor plan image URLs are constructed
2. Verify backend serves images with correct CORS headers
3. Check if images are being stored/served from the correct path
4. Add error handling/fallback UI for failed image loads
