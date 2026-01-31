---
created: 2026-01-31T18:55
title: Floor plan device visibility and navigation
area: ui
files:
  - src/frontend/src/components/floor-plans/FloorPlanViewer.tsx
  - src/frontend/src/components/floor-plans/DeviceStatusOverlay.tsx
  - src/frontend/src/pages/DeviceManagementPage.tsx
---

## Problem

Two issues with floor plan device interaction:

1. **Devices not visible on floor plan**: ~~When viewing a floor plan, the placed devices are not showing up on the map.~~ **FIXED** (commit c2585eb)

2. **No navigation on device selection**: When using "Drag to position on floor plan" feature and clicking on a device that's already placed, the floor plan should:
   - Pan/scroll to show the device location
   - Highlight the selected device visually

## Solution

1. ~~Check that DeviceStatusOverlay or similar component is properly rendering device markers on the floor plan~~ **DONE**
2. Add a "focus on device" feature that:
   - Calculates the viewport transform needed to center the device
   - Smoothly pans the floor plan to the device position
   - Adds a highlight effect (pulse animation, border, glow) to the selected device
