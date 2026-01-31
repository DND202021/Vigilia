---
created: 2026-01-31T21:45
completed: 2026-01-31T22:30
title: Device positioning on floor plans
area: ui
priority: high
files:
  - src/frontend/src/components/buildings/FloorPlanEditor.tsx
  - src/frontend/src/components/buildings/DeviceStatusOverlay.tsx
  - src/frontend/src/components/buildings/DeviceEditSidebar.tsx
  - src/frontend/src/stores/devicePositionStore.ts
  - src/frontend/src/types/index.ts
---

## Problem

IoT devices (cameras, microphones, sensors, gateways) need to be visually positioned on floor plans so first responders can:

1. See device locations at a glance during interventions
2. Quickly identify which devices cover which areas
3. Know exact positions for tactical planning

## Solution

### Implementation

#### 1. Device Edit Mode in FloorPlanEditor
- Added `deviceEditMode` state toggle (separate from marker edit mode)
- Device toggle button in toolbar (chip icon)
- Modes are mutually exclusive (entering device mode exits marker mode)

#### 2. DeviceEditSidebar Component (NEW)
- Shows unplaced and placed devices for the building
- Filter tabs: Unplaced / Placed
- Draggable device items with type icon and status indicator
- Help tips for drag, right-click, and reposition actions
- Fullscreen-aware dark/light theming

#### 3. Enhanced DeviceStatusOverlay
- Made interactive when `isEditable=true`
- Devices are draggable in edit mode
- Right-click context menu with "Remove from floor plan" option
- Edit indicator (blue dot) on editable devices
- Tooltip shows drag/remove instructions in edit mode

#### 4. Device Position Store Enhancements
- `addDeviceToFloorPlan(deviceId, x, y)` - Place device on floor plan
- `removeDeviceFromFloorPlan(deviceId)` - Clear floor_plan_id and positions
- Optimistic updates with rollback on error

#### 5. Type Updates
- `IoTDeviceUpdateRequest` now allows `null` for `floor_plan_id`, `position_x`, `position_y`

### Usage

1. Click device icon (chip) in toolbar to enter Device Edit Mode
2. Drag device from sidebar onto floor plan to place
3. Drag placed device to reposition
4. Right-click device to remove from floor plan
5. Click device icon again to exit Device Edit Mode

### Files Created/Modified

- **NEW:** `DeviceEditSidebar.tsx` - Sidebar component for device list
- **Modified:** `FloorPlanEditor.tsx` - Device edit mode integration
- **Modified:** `DeviceStatusOverlay.tsx` - Interactive edit capabilities
- **Modified:** `devicePositionStore.ts` - Add/remove device methods
- **Modified:** `types/index.ts` - Nullable position fields

## Status: **COMPLETED**
