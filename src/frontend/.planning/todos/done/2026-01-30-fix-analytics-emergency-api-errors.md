---
created: 2026-01-30T15:15
completed: 2026-01-30T21:30
title: Fix Analytics API errors
area: api
files:
  - src/backend/app/api/buildings.py
  - src/backend/app/services/building_analytics_service.py
  - src/frontend/src/components/analytics/BuildingAnalyticsDashboard.tsx
---

## Problem

Analytics Tab returned errors preventing data from loading.

### Issues Found
1. **401 Unauthorized** - Frontend used direct `fetch()` which bypassed axios token refresh
2. **500 Internal Server Error** - PostgreSQL enum comparison failed: `COMPLETED` vs `completed`

## Root Cause Analysis

PostgreSQL stores enum values as **lowercase strings** (e.g., `completed`, `scheduled`).
SQLAlchemy's `Enum` column type has complex behavior when comparing with values:

### What DOESN'T Work

1. **Using enum member directly:**
   ```python
   Inspection.status == InspectionStatus.COMPLETED
   ```
   SQLAlchemy sends the enum **name** (uppercase): `'COMPLETED'`

2. **Using `.value` on enum:**
   ```python
   Inspection.status == InspectionStatus.COMPLETED.value  # "completed"
   ```
   SQLAlchemy still converts through the Enum type handler, sending: `'COMPLETED'`

3. **Using literal strings:**
   ```python
   Inspection.status == "completed"
   ```
   SQLAlchemy sees the column is Enum type and converts the string, sending: `'COMPLETED'`

### What WORKS

**Cast the enum column to String type:**
```python
from sqlalchemy import cast, String

cast(Inspection.status, String) == "completed"
cast(Inspection.status, String).in_(["scheduled", "overdue"])
```

This bypasses SQLAlchemy's enum handling entirely and compares as plain text.

## Solution

### 1. Frontend: Switch to Axios-based API (BuildingAnalyticsDashboard.tsx)
- Changed from direct `fetch()` to `buildingAnalyticsApi` which uses axios
- This ensures automatic token refresh on 401 responses

### 2. Backend: Cast enum columns to String (building_analytics_service.py)
```python
from sqlalchemy import cast, String

# Instead of:
Inspection.status == "completed"

# Use:
cast(Inspection.status, String) == "completed"
```

### Commits
- `74f4bb9` - Initial attempt with `.value` (didn't work)
- `3e11c21` - Attempt with literal strings (didn't work)
- `6823594` - Final fix using `cast(column, String)` (WORKS)

## Lessons Learned

1. **SQLAlchemy Enum columns are tricky** - They don't behave like regular string columns
2. **PostgreSQL enum labels are lowercase** - Always use lowercase when comparing
3. **`cast(column, String)` is the reliable solution** - Bypasses all enum conversion logic
4. **CORS errors can mask 500 errors** - When backend crashes, CORS headers aren't sent
5. **Check actual SQL parameters** - Log output shows `[parameters: (..., 'COMPLETED')]` revealing the issue

## Future Prevention

When comparing SQLAlchemy Enum columns in PostgreSQL:
```python
# ALWAYS use cast() for enum comparisons
from sqlalchemy import cast, String

cast(Model.enum_column, String) == "value"
cast(Model.enum_column, String).in_(["value1", "value2"])
```

## Status: **FIXED**
