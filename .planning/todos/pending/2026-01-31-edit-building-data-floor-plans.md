---
created: 2026-01-31T20:25
title: Edit building data and replace floor plans
area: ui
files:
  - src/frontend/src/pages/BuildingsPage.tsx
  - src/frontend/src/pages/BuildingDetailPage.tsx
  - src/backend/app/api/buildings.py
---

## Problem

Currently there's no way to:

1. **Edit building information**: Users need to modify building details like:
   - Name
   - Address
   - Description
   - Other metadata

2. **Replace/update floor plans**: Users need to:
   - Replace an existing floor plan image
   - Update floor plan metadata (name, level number)
   - Possibly delete and re-upload floor plans

## Solution

1. Add an "Edit Building" modal/page with form to update building fields
2. Add PATCH /buildings/{id} endpoint if not exists
3. Add floor plan management UI:
   - Edit button on floor plan to change image or metadata
   - Delete floor plan option
   - Re-order floor plans if needed
