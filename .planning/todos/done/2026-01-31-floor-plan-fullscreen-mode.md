---
created: 2026-01-31T21:45
completed: 2026-01-31T22:30
title: Add floor plan fullscreen mode
area: ui
priority: high
files:
  - src/frontend/src/components/buildings/FloorPlanViewer.tsx
  - src/frontend/src/components/buildings/FloorPlanEditor.tsx
---

## Problem

Floor plans need a fullscreen mode for field use. First responders using tablets or phones during interventions need to:

1. See the full floor plan without UI clutter
2. Zoom and pan easily on touch devices
3. Quickly toggle between fullscreen and normal view
4. Still see critical overlays (devices, markers, evacuation routes)

## Requirements

- Toggle button to enter/exit fullscreen mode
- Escape key should exit fullscreen
- Touch-friendly controls for mobile/tablet use
- Maintain all interactive overlays in fullscreen
- Clean, distraction-free UI in fullscreen mode
- Work in both FloorPlanViewer (read-only) and FloorPlanEditor (edit mode)

## Solution

### Implementation

1. **Browser Fullscreen API** - Used `requestFullscreen()` and `exitFullscreen()`
2. **Fullscreen toggle button** - Added expand/collapse icon to toolbar
3. **State tracking** - `isFullscreen` state synced with `fullscreenchange` event
4. **Dark mode styling** - Toolbar switches to dark theme in fullscreen
5. **Text visibility** - Floor name and info text use light colors in fullscreen

### Files Modified

- `FloorPlanViewer.tsx` - Added fullscreen state, toggle handler, button, and styling
- `FloorPlanEditor.tsx` - Added fullscreen state, toggle handler, button, and styling

### Usage

- Click fullscreen button in toolbar to enter fullscreen
- Press Escape or click button again to exit
- All overlays (markers, devices) remain visible and functional

## Status: **COMPLETED**
