---
created: 2026-01-31T18:55
completed: 2026-01-31T22:10
title: Floor plan device visibility and navigation
area: ui
files:
  - src/frontend/src/components/buildings/FloorPlanEditor.tsx
  - src/frontend/src/components/buildings/DeviceStatusOverlay.tsx
  - src/frontend/src/components/buildings/DeviceEditSidebar.tsx
  - src/frontend/src/hooks/useFloorPlanSync.ts
  - src/frontend/src/stores/devicePositionStore.ts
  - src/frontend/src/types/index.ts
---

## Problem

Two issues with floor plan device interaction:

1. **Devices not visible on floor plan**: ~~When viewing a floor plan, the placed devices are not showing up on the map.~~ **FIXED** (commit c2585eb)

2. **No navigation on device selection**: ~~When using "Drag to position on floor plan" feature and clicking on a device that's already placed, the floor plan should pan/scroll to show the device location and highlight the selected device visually.~~ **FIXED** (commit 6f2d471)

## Solution

1. **Device visibility fix** (commit c2585eb):
   - Separated device loading from WebSocket connection in useFloorPlanSync
   - Extended DeviceFloorPosition type to include device details
   - Updated devicePositionStore to save full device info when loading
   - Updated DeviceStatusOverlay to use stored device details

2. **Navigation feature** (commit 6f2d471):
   - Added onDeviceClick prop to DeviceEditSidebar
   - Added eye icon for placed devices indicating they're clickable
   - Added focusOnDevice function in FloorPlanEditor to pan/zoom to device
   - Added highlightedDeviceId prop to DeviceStatusOverlay with pulse animation
   - Highlight auto-clears after 3 seconds
