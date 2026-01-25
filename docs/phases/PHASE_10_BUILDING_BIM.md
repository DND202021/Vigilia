# Phase 10: Building Information Management & BIM Integration

**Project:** ERIOP (Emergency Response IoT Platform)
**Created:** 2026-01-25
**Status:** Planning

---

## Executive Summary

This phase enhances the Building Information Management system with comprehensive floor plan visualization, BIM (Building Information Modeling) integration, and tactical planning features. The goal is to provide first responders with detailed building intelligence during emergency response.

---

## Gap Analysis

### Currently Implemented (Backend Complete)

| Feature | Status | Notes |
|---------|--------|-------|
| Building Model | ✅ Complete | 53 columns, all emergency response fields |
| FloorPlan Model | ✅ Complete | BIM data, key locations, emergency info |
| Building CRUD API | ✅ Complete | Full REST API with all operations |
| Floor Plan API | ✅ Complete | Add, update, delete, list floor plans |
| BIM Import Service | ✅ Complete | `import_bim_data()` extracts floors |
| Geospatial Queries | ✅ Complete | Proximity search, Haversine distance |
| Buildings Page UI | ✅ Basic | List, create, detail view |
| Floor Plans Display | ✅ Basic | List only, no visual viewer |

### Missing Features (Gaps)

| Feature | Priority | Effort |
|---------|----------|--------|
| Interactive Floor Plan Viewer | P0 | High |
| Floor Plan Upload/Management | P0 | Medium |
| Building Display on Tactical Map | P0 | Medium |
| Incident-Building Integration | P1 | Medium |
| Key Location Marking Tool | P1 | High |
| BIM File Import (IFC format) | P1 | High |
| 3D Building Visualization | P2 | Very High |
| Inspection Scheduling | P2 | Medium |
| Document/Photo Management | P2 | Medium |
| Mobile App (React Native) | P2 | Very High |
| Offline Building Data Cache | P2 | Medium |

---

## Implementation Plan

### Sprint 1: Floor Plan Viewer (Week 1-2)

**Objective:** Create an interactive floor plan viewer component

#### Tasks

1. **FloorPlanViewer Component** (Frontend)
   - Canvas/SVG-based floor plan rendering
   - Pan and zoom controls
   - Floor selector navigation
   - Responsive design for tablet use

2. **Floor Plan Upload API** (Backend)
   - File upload endpoint for images (PNG, JPG, PDF)
   - Thumbnail generation
   - File storage (local/S3-compatible)
   - File type validation

3. **Floor Plan Upload UI** (Frontend)
   - Drag-and-drop upload component
   - Progress indicator
   - Preview before save

4. **Key Locations Overlay** (Frontend)
   - Display emergency exits on floor plan
   - Display fire equipment locations
   - Display hazard zones
   - Icon legend

#### Deliverables
- `src/frontend/src/components/buildings/FloorPlanViewer.tsx`
- `src/frontend/src/components/buildings/FloorPlanUpload.tsx`
- `src/backend/app/api/floor_plans.py` (file upload endpoints)
- Update `BuildingsPage.tsx` with integrated viewer

#### API Endpoints (New)
```
POST /api/v1/buildings/{id}/floor-plans/upload
GET /api/v1/floor-plans/{id}/image
DELETE /api/v1/floor-plans/{id}
```

---

### Sprint 2: Tactical Map Integration (Week 3-4)

**Objective:** Display buildings on the tactical map with click-to-view details

#### Tasks

1. **Building Markers on Map** (Frontend)
   - Add building layer to Leaflet map
   - Custom building icons by type
   - Clustering for dense areas
   - Hazard level color coding

2. **Building Popup/Quick View** (Frontend)
   - Click building marker to show popup
   - Quick info: name, type, hazard, floors
   - "View Details" button opens full modal
   - "View Floor Plans" quick access

3. **Buildings Near Incident** (Frontend)
   - Show nearby buildings when viewing incident
   - Distance calculation display
   - One-click navigation to building info

4. **Building Search on Map** (Frontend)
   - Search buildings by name/address
   - Zoom to selected building
   - Highlight selected building

#### Deliverables
- `src/frontend/src/components/map/BuildingLayer.tsx`
- `src/frontend/src/components/map/BuildingPopup.tsx`
- Update `TacticalMap.tsx` with building layer toggle

---

### Sprint 3: Incident-Building Integration (Week 5-6)

**Objective:** Link incidents to buildings for contextual response information

#### Tasks

1. **Building Selector in Incident Form** (Frontend)
   - Autocomplete building search
   - "Near me" building suggestions
   - Display selected building summary

2. **Building Info Panel in Incident View** (Frontend)
   - Collapsible building information panel
   - Floor plans quick access
   - Tactical notes highlight
   - Emergency contacts display

3. **Pre-Incident Plan Display** (Frontend)
   - Format and display pre-incident plan text
   - Highlight critical safety information
   - Print-friendly view

4. **Incident History for Buildings** (Backend + Frontend)
   - Track incidents at each building
   - Display incident history in building detail
   - Analytics: incidents by building

#### Deliverables
- `src/frontend/src/components/incidents/BuildingSelector.tsx`
- `src/frontend/src/components/incidents/BuildingInfoPanel.tsx`
- Update `IncidentDetailPage.tsx`
- Update incident creation/edit forms

#### API Endpoints (Enhancement)
```
GET /api/v1/buildings/{id}/incidents  (incident history)
GET /api/v1/incidents?building_id={id}  (filter incidents by building)
```

---

### Sprint 4: Key Location Marking Tool (Week 7-8)

**Objective:** Allow users to mark key locations on floor plans

#### Tasks

1. **Interactive Marking Tool** (Frontend)
   - Click-to-place markers on floor plan
   - Drag markers to reposition
   - Delete markers
   - Save marker positions

2. **Location Type Categories** (Backend + Frontend)
   - Fire Equipment: extinguisher, hose, alarm pull, sprinkler control
   - Access: stairwell, elevator, emergency exit, roof access
   - Utilities: electrical panel, gas shutoff, water shutoff
   - Hazards: hazmat storage, confined space, high voltage
   - Medical: AED, first aid, eyewash station

3. **Marker Properties Form** (Frontend)
   - Name/description
   - Location type selection
   - Notes field
   - Photo attachment

4. **Print View with Annotations** (Frontend)
   - Printable floor plan with all markers
   - Legend with marker descriptions
   - Building summary header

#### Deliverables
- `src/frontend/src/components/buildings/FloorPlanEditor.tsx`
- `src/frontend/src/components/buildings/LocationMarker.tsx`
- `src/frontend/src/components/buildings/FloorPlanPrint.tsx`
- Update floor plan API for marker persistence

---

### Sprint 5: BIM Import (Week 9-10)

**Objective:** Import industry-standard BIM files to extract building data

#### Tasks

1. **IFC Parser Service** (Backend)
   - Parse IFC (Industry Foundation Classes) files
   - Extract building geometry
   - Extract floor information
   - Extract room/space data

2. **BIM Import Workflow** (Frontend)
   - Upload IFC file
   - Preview extracted data
   - Map BIM data to building fields
   - Confirm and save

3. **Automatic Floor Plan Generation** (Backend)
   - Generate 2D floor plans from BIM geometry
   - SVG output for floor plans
   - Extract key locations from BIM

4. **BIM Data Viewer** (Frontend)
   - Display extracted BIM metadata
   - Building specifications from BIM
   - Material information

#### Deliverables
- `src/backend/app/services/bim_parser.py`
- `src/backend/app/api/bim.py`
- `src/frontend/src/components/buildings/BIMImport.tsx`
- Dependencies: `ifcopenshell` Python library

#### API Endpoints (New)
```
POST /api/v1/buildings/import-bim
GET /api/v1/buildings/{id}/bim-data
```

---

### Sprint 6: Document & Photo Management (Week 11-12)

**Objective:** Manage building-related documents and photos

#### Tasks

1. **Document Upload** (Backend + Frontend)
   - PDF upload for permits, inspections, plans
   - Document categorization
   - Version tracking

2. **Photo Gallery** (Frontend)
   - Building exterior photos
   - Interior photos by floor/area
   - Photo metadata (date, description)
   - Thumbnail grid view

3. **Photo Capture Integration** (Frontend)
   - Camera access for photo capture
   - Geolocation tagging
   - Upload directly to building

4. **Inspection Records** (Backend + Frontend)
   - Track inspection dates
   - Inspection findings
   - Due date notifications
   - Compliance status

#### Deliverables
- `src/frontend/src/components/buildings/DocumentManager.tsx`
- `src/frontend/src/components/buildings/PhotoGallery.tsx`
- `src/frontend/src/components/buildings/InspectionTracker.tsx`
- File storage service enhancements

---

### Sprint 7: Advanced Visualization (Week 13-14)

**Objective:** 3D building visualization for complex structures

#### Tasks

1. **3D Viewer Component** (Frontend)
   - Three.js based 3D renderer
   - Floor-by-floor navigation
   - Rotate/zoom controls
   - Mobile-friendly touch controls

2. **BIM to 3D Conversion** (Backend)
   - Convert IFC geometry to glTF/GLB
   - Optimize for web rendering
   - Level-of-detail variants

3. **3D Annotations** (Frontend)
   - Place markers in 3D space
   - Information popups
   - Emergency route visualization

#### Deliverables
- `src/frontend/src/components/buildings/Building3DViewer.tsx`
- `src/backend/app/services/bim_converter.py`
- Dependencies: `three.js`, `@react-three/fiber`

**Note:** This sprint is optional/deferred based on priority.

---

### Sprint 8: Mobile Integration (Week 15-16)

**Objective:** React Native mobile app with building access

#### Tasks

1. **Mobile Building List** (Mobile)
   - Building search and list
   - Offline data sync
   - Nearby buildings by GPS

2. **Mobile Floor Plan Viewer** (Mobile)
   - Touch-optimized viewer
   - Pinch-to-zoom
   - Offline floor plan cache

3. **Mobile Incident Integration** (Mobile)
   - View building during response
   - Quick access floor plans
   - Offline capability

**Note:** This sprint depends on React Native project setup (separate initiative).

---

## Technical Architecture

### File Storage

```
Option A: Local Storage (Development/Small Scale)
/data/buildings/{building_id}/
  ├── floor_plans/
  │   ├── floor_1.png
  │   ├── floor_1_thumb.png
  │   └── floor_2.pdf
  ├── photos/
  │   ├── exterior_001.jpg
  │   └── interior_floor1_001.jpg
  └── documents/
      ├── fire_inspection_2024.pdf
      └── building_permit.pdf

Option B: S3-Compatible Storage (Production)
- MinIO for self-hosted
- AWS S3 for cloud
- Presigned URLs for secure access
```

### Database Schema (No Changes Required)

The existing schema supports all planned features:
- `buildings.photos` - JSON array of photo references
- `buildings.documents` - JSON array of document references
- `buildings.bim_data` - JSON for BIM extracted data
- `floor_plans.plan_file_url` - URL to floor plan file
- `floor_plans.key_locations` - JSON array of marked locations
- `floor_plans.emergency_exits` - JSON array of exit locations
- `floor_plans.fire_equipment` - JSON array of equipment locations

### Frontend Component Hierarchy

```
BuildingsPage
├── BuildingList
├── BuildingCard
├── CreateBuildingModal
└── BuildingDetailModal
    ├── BuildingHeader
    ├── BuildingSafetyFeatures
    ├── BuildingContacts
    ├── FloorPlanViewer (NEW)
    │   ├── FloorSelector
    │   ├── FloorPlanCanvas
    │   └── LocationMarkers
    ├── FloorPlanEditor (NEW)
    │   ├── MarkerPalette
    │   └── MarkerPropertiesForm
    ├── DocumentManager (NEW)
    ├── PhotoGallery (NEW)
    └── InspectionTracker (NEW)
```

---

## Risk Mitigation

### Risk 1: Breaking Existing Functionality
- **Mitigation:** Feature flags for new components
- **Mitigation:** Comprehensive test coverage before deployment
- **Mitigation:** Incremental rollout per sprint

### Risk 2: File Storage Performance
- **Mitigation:** CDN for floor plan images
- **Mitigation:** Thumbnail generation for quick loads
- **Mitigation:** Lazy loading for galleries

### Risk 3: BIM File Complexity
- **Mitigation:** Start with simple IFC support
- **Mitigation:** Fallback to manual entry if parse fails
- **Mitigation:** External BIM processing service option

### Risk 4: Mobile Offline Sync
- **Mitigation:** Selective sync (critical buildings only)
- **Mitigation:** Incremental sync for updates
- **Mitigation:** Conflict resolution strategy

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Floor plans uploaded | 50+ buildings | Database query |
| Average detail view time | < 2 seconds | Performance monitoring |
| Building-incident linkage | 80% of incidents | API analytics |
| BIM import success rate | > 90% | Import logs |
| Mobile offline availability | 100% cached buildings | Sync status |

---

## Dependencies

### Backend
- `Pillow` - Image processing (thumbnail generation)
- `python-multipart` - File uploads (already installed)
- `ifcopenshell` - IFC/BIM parsing (Sprint 5)
- `boto3` - S3 storage (optional, for production)

### Frontend
- `react-zoom-pan-pinch` - Floor plan viewer controls
- `react-dropzone` - File upload drag-and-drop
- `@react-three/fiber` - 3D visualization (Sprint 7)
- `three` - 3D rendering (Sprint 7)

---

## Sprint Summary

| Sprint | Focus | Duration | Priority |
|--------|-------|----------|----------|
| 1 | Floor Plan Viewer & Upload | 2 weeks | P0 |
| 2 | Tactical Map Integration | 2 weeks | P0 |
| 3 | Incident-Building Integration | 2 weeks | P1 |
| 4 | Key Location Marking Tool | 2 weeks | P1 |
| 5 | BIM Import | 2 weeks | P1 |
| 6 | Document & Photo Management | 2 weeks | P2 |
| 7 | Advanced 3D Visualization | 2 weeks | P2 (Optional) |
| 8 | Mobile Integration | 2 weeks | P2 (Deferred) |

**Total Estimated Duration:** 12-16 weeks (depending on optional sprints)

---

## Recommended Starting Point

**Sprint 1: Floor Plan Viewer** is the highest-impact starting point because:
1. Floor plans are critical for first responder tactical planning
2. Backend API already exists - just needs file upload
3. Most immediate value for users
4. Foundation for marking tool (Sprint 4)

---

## Questions for Stakeholder

1. **File Storage:** Preference for local vs S3-compatible storage?
2. **BIM Formats:** Which BIM formats are commonly used? (IFC, RVT, DWG)
3. **3D Priority:** Is 3D visualization required or nice-to-have?
4. **Mobile Timeline:** When is React Native mobile app needed?
5. **Integration:** Any existing building databases to import from?

---

*Document Version: 1.0 | Created: 2026-01-25*
