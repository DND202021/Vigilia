# CLAUDE.md - Context for Claude Code

This file provides context for Claude Code when working on this project.

## Project Overview

**Project:** ERIOP (Emergency Response IoT Platform)
**Repository:** https://github.com/DND202021/Vigilia
**Division:** Vigilia (Security Division)

ERIOP is a mission-critical platform designed to provide real-time tactical and strategic information to emergency responders (SWAT, police, firefighters, medics). Built on the Fundamentum IoT Platform by Amotus.

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.11+ / FastAPI |
| Database | PostgreSQL + TimescaleDB |
| Cache | Redis |
| Frontend | React + TypeScript + Vite |
| Mobile | React Native (planned) |
| Infrastructure | Docker + Kubernetes |
| IoT Platform | Fundamentum (Amotus) |

## Project Structure

```
Vigilia/
├── src/
│   ├── backend/          # FastAPI backend
│   │   ├── app/
│   │   │   ├── api/      # REST endpoints
│   │   │   ├── core/     # Config, security, deps
│   │   │   ├── models/   # SQLAlchemy models
│   │   │   ├── services/ # Business logic
│   │   │   └── integrations/  # External systems
│   │   ├── alembic/      # Database migrations
│   │   └── tests/        # Pytest tests (176 tests)
│   └── frontend/         # React web app
│       ├── src/
│       │   ├── components/   # UI components
│       │   ├── pages/        # Route pages
│       │   ├── stores/       # Zustand state
│       │   ├── services/     # API & offline
│       │   └── hooks/        # Custom hooks
│       └── public/           # Static assets
├── docs/
│   ├── architecture/     # System design
│   ├── phases/           # Development phases
│   └── requirements/     # Specs
└── infrastructure/       # Docker + K8s configs
    ├── nginx/            # Reverse proxy config
    └── k8s/              # Kubernetes manifests
```

## Development Progress

### Completed

- [x] **Phase 1: Foundation** (January 2025)
  - SQLAlchemy models (User, Agency, Incident, Resource, Alert)
  - JWT authentication service
  - Alembic migrations
  - Unit tests (33 tests passing)

- [x] **Phase 2: Core Services**
  - Incident management service
  - Resource tracking service
  - Alert processing service
  - Unit tests (50+ tests)

- [x] **Phase 3: Integrations**
  - Circuit breaker pattern for fault tolerance
  - Alarm system integration (Contact ID protocol)
  - Axis audio analytics integration
  - CAD system adapter with sync service
  - GIS service (geocoding, routing, jurisdictions)
  - Unit tests (93 tests)

- [x] **Phase 4: User Interfaces**
  - React + TypeScript frontend
  - Dashboard with real-time data
  - Incidents list and detail pages
  - Alerts management page
  - Resources tracking page
  - Tactical map with Leaflet
  - Authentication flow (login/logout)
  - Zustand state management
  - API client with token refresh

- [x] **Phase 5: Offline Capability**
  - Service Worker for caching
  - IndexedDB offline storage
  - Sync service for background sync
  - Offline status indicator
  - PWA manifest

- [x] **Phase 6: Security Hardening**
  - Input validation and sanitization
  - XSS prevention (HTML escaping)
  - Rate limiting
  - Content Security Policy
  - Secure storage wrapper
  - Session timeout management

- [x] **Phase 7: Testing & Certification**
  - Backend: 176 pytest tests
  - Frontend: Vitest unit tests
  - Validation tests
  - Store tests

- [x] **Phase 8: Production Deployment**
  - Docker multi-stage builds
  - Docker Compose (dev + prod)
  - Kubernetes manifests
  - Nginx reverse proxy config
  - SSL/TLS configuration
  - Health checks
  - Resource limits

- [x] **Phase 9: Users & Roles Management** (January 2025)
  - Flexible database-backed Role model (replaces hardcoded UserRole enum)
  - Role permissions stored as JSON array
  - Role hierarchy levels for access control
  - 7 default system roles seeded via migration
  - Full Users management page with CRUD operations
  - Full Roles management page with permission editor
  - Backend: RoleService, UserService, REST APIs
  - Frontend: UsersPage, RolesPage, Zustand stores
  - Database migration: 002_add_roles_table.py

## Key Commands

### Backend Development
```bash
cd src/backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest tests/ -v                    # Run tests (176 passing)
uvicorn app.main:app --reload       # Start dev server
```

### Frontend Development
```bash
cd src/frontend
npm install
npm run dev                         # Start dev server
npm run test                        # Run tests
npm run build                       # Production build
```

### Docker
```bash
docker compose up -d                # Start dev environment
docker compose -f docker-compose.prod.yml up -d  # Production
docker compose logs -f backend      # View logs
```

### Kubernetes
```bash
kubectl apply -f infrastructure/k8s/namespace.yaml
kubectl apply -f infrastructure/k8s/secrets.yaml
kubectl apply -f infrastructure/k8s/backend-deployment.yaml
kubectl apply -f infrastructure/k8s/frontend-deployment.yaml
kubectl apply -f infrastructure/k8s/ingress.yaml
```

### Database Migrations
```bash
cd src/backend
alembic upgrade head                # Apply migrations
alembic revision --autogenerate -m "description"  # Create migration
```

## Critical Requirements

1. **Security First** - Handle personal/confidential data securely
2. **High Availability** - 99.9% uptime target
3. **Offline Capability** - Must work without network
4. **Real-time** - Alert processing < 500ms
5. **Audit Trail** - Full logging for compliance
6. **Multi-tenancy** - Agency-level data isolation

## API Endpoints

### Authentication
- `POST /api/v1/auth/login` - Login
- `POST /api/v1/auth/register` - Register
- `POST /api/v1/auth/refresh` - Refresh token
- `POST /api/v1/auth/logout` - Logout
- `GET /api/v1/auth/me` - Current user
- `POST /api/v1/auth/change-password` - Change password

### Incidents
- `GET /api/v1/incidents` - List incidents
- `GET /api/v1/incidents/active` - Active incidents
- `GET /api/v1/incidents/{id}` - Get incident
- `POST /api/v1/incidents` - Create incident
- `PATCH /api/v1/incidents/{id}` - Update incident
- `POST /api/v1/incidents/{id}/status` - Update status
- `POST /api/v1/incidents/{id}/assign` - Assign unit

### Resources
- `GET /api/v1/resources` - List resources
- `GET /api/v1/resources/available` - Available resources
- `GET /api/v1/resources/{id}` - Get resource
- `POST /api/v1/resources` - Create resource
- `PATCH /api/v1/resources/{id}/status` - Update status
- `PATCH /api/v1/resources/{id}/location` - Update location

### Alerts
- `GET /api/v1/alerts` - List alerts
- `GET /api/v1/alerts/pending` - Pending alerts
- `GET /api/v1/alerts/{id}` - Get alert
- `POST /api/v1/alerts/{id}/acknowledge` - Acknowledge
- `POST /api/v1/alerts/{id}/resolve` - Resolve
- `POST /api/v1/alerts/{id}/create-incident` - Create incident

### Users (Admin)
- `GET /api/v1/users` - List users (filters: agency_id, role_id, is_active, search)
- `GET /api/v1/users/stats` - User statistics
- `GET /api/v1/users/{id}` - Get user details
- `POST /api/v1/users` - Create user
- `PATCH /api/v1/users/{id}` - Update user
- `POST /api/v1/users/{id}/deactivate` - Deactivate user
- `POST /api/v1/users/{id}/activate` - Activate user
- `POST /api/v1/users/{id}/verify` - Verify user
- `POST /api/v1/users/{id}/reset-password` - Reset password
- `DELETE /api/v1/users/{id}` - Soft delete user

### Roles (Admin)
- `GET /api/v1/roles` - List roles
- `GET /api/v1/roles/permissions` - List available permissions
- `GET /api/v1/roles/{id}` - Get role details
- `POST /api/v1/roles` - Create custom role
- `PATCH /api/v1/roles/{id}` - Update role
- `DELETE /api/v1/roles/{id}` - Soft delete role

### Health
- `GET /health` - Health check

## Database Models

- **User** - Authentication, role_id FK to Role, MFA support
- **Role** - Flexible RBAC with permissions JSON, hierarchy_level, is_system_role
- **Agency** - Multi-tenant organizations
- **Incident** - Emergency events with status tracking
- **Resource** - Personnel, vehicles, equipment
- **Alert** - Incoming alerts from various sources
- **Building** - Building information management with floor plans

### Default System Roles (seeded in migration 002)
| Name | Hierarchy | Key Permissions |
|------|-----------|-----------------|
| system_admin | 0 | system:admin (full access) |
| agency_admin | 10 | users:manage_agency, all incidents/resources/alerts |
| commander | 20 | incidents:*, resources:*, alerts:* |
| dispatcher | 30 | incidents:read/create/update/assign, alerts:* |
| field_unit_leader | 40 | incidents:read/update, resources:read/update |
| responder | 50 | incidents:read, resources:read, alerts:read |
| public_user | 100 | incidents:report only |

## Integration Adapters

- **AlarmReceiverService** - Contact ID protocol decoder
- **AxisAudioClient** - Axis camera audio analytics
- **CADSyncService** - Computer-Aided Dispatch sync
- **GISService** - Geocoding and routing

## Environment Variables

See `.env.example` for all configuration options.

## Documentation

- [System Architecture](docs/architecture/SYSTEM_ARCHITECTURE.md)
- [Database Design](docs/architecture/DATABASE_DESIGN.md)
- [API Design](docs/architecture/API_DESIGN.md)
- [Functional Requirements](docs/requirements/FUNCTIONAL_REQUIREMENTS.md)
- [Security Requirements](docs/requirements/SECURITY_REQUIREMENTS.md)

## Git Configuration

**Remote URL**: Use SSH for pushing (HTTPS doesn't have credentials configured):
```bash
git remote set-url origin git@github.com:DND202021/Vigilia.git
```

**Push command**: Just use `git push` after setting SSH URL.

## Local Deployment

The application is deployed locally via Docker on a server at **http://10.0.0.13:83/**

**Note**: SSH to the server (port 22) is not accessible from the Claude Code environment due to firewall restrictions. Deployment must be done manually from a machine with SSH access.

### Deployment Commands (on server)
```bash
cd /home/vigilia/Vigilia
git pull origin main
docker compose -f docker-compose.local.yml down
docker compose -f docker-compose.local.yml build --no-cache
docker compose -f docker-compose.local.yml up -d
```

### After deploying new features, run database migrations:
```bash
docker exec -it eriop-backend alembic upgrade head
```

## Recent Changes (January 2025 Session)

### Files Created
- `src/backend/app/models/role.py` - Role model with permissions, hierarchy
- `src/backend/app/services/role_service.py` - RoleService CRUD
- `src/backend/app/services/user_service.py` - UserService CRUD
- `src/backend/app/api/users.py` - Users REST API
- `src/backend/app/api/roles.py` - Roles REST API
- `src/backend/alembic/versions/002_add_roles_table.py` - Migration
- `src/backend/tests/test_role_service.py` - Role tests
- `src/backend/tests/test_user_service.py` - User tests
- `src/frontend/src/pages/UsersPage.tsx` - Users management UI
- `src/frontend/src/pages/RolesPage.tsx` - Roles management UI
- `src/frontend/src/stores/userStore.ts` - User Zustand store
- `src/frontend/src/stores/roleStore.ts` - Role Zustand store
- `src/frontend/netlify.toml` - Netlify config (kept for future use)

### Files Modified
- `src/backend/app/models/user.py` - Added role_id FK, role_obj relationship
- `src/backend/app/models/__init__.py` - Added Role export
- `src/backend/app/services/__init__.py` - Added RoleService, UserService exports
- `src/backend/app/api/__init__.py` - Added users, roles routers
- `src/backend/tests/conftest.py` - Added Role import
- `src/frontend/src/App.tsx` - Added /users, /roles routes (lazy loaded)
- `src/frontend/src/pages/index.ts` - Added UsersPage, RolesPage exports
- `src/frontend/src/services/api.ts` - Added usersApi, rolesApi
- `src/frontend/src/types/index.ts` - Added Role, UserFull types
- `src/frontend/src/components/layout/Navbar.tsx` - Added Users, Roles nav links

### Key Technical Decisions
- Used generic `JSON` type instead of `JSONB` for Role.permissions (SQLite test compatibility)
- Role model uses soft delete pattern (SoftDeleteMixin)
- System roles (is_system_role=true) cannot be deleted, only display name/description edited
- Frontend uses React.lazy() for code-splitting all pages

## Workflow Instructions for Claude Code

When working on sprints or multi-task implementations:

1. **Use sub-agents extensively** - Divide work into sub-tasks that can be completed by specialized sub-agents to manage context window efficiently
2. **Parallel execution** - Launch multiple independent sub-agents simultaneously when tasks have no dependencies
3. **Wave-based execution** - Group tasks into waves based on dependencies:
   - Wave 1: Independent foundational tasks (stores, utilities, independent components)
   - Wave 2: Components that depend on Wave 1 outputs
   - Wave 3: Integration tasks (page refactoring, tests)
4. **Task tracking** - Use TaskCreate/TaskUpdate to track progress and dependencies
5. **Verify before commit** - Run TypeScript build (`npx tsc --noEmit`) and tests before committing
6. **Atomic commits** - Commit completed sprints with descriptive messages

### Sub-agent Task Template
When creating sub-agent tasks, provide:
- Clear file path(s) to create/modify
- Existing patterns to follow (reference similar files)
- Type imports and dependencies
- Expected exports (named + default)
- Integration points with other components

---

## Phase 10: Building Information Management (In Progress)

### Sprint 1: Floor Plan Management ✅ (January 2025)
- FloorPlanViewer, UnifiedFloorPlanViewer, FloorPlanUpload components
- Backend file upload with validation and thumbnails
- BuildingDetailPage with floor plan tabs
- 21 floor plan upload tests, 30 file storage tests

### Sprint 2: Tactical Map Integration ✅ (January 2025)
- buildingMapStore (Zustand) for map-specific state
- BuildingLayer with marker clustering (leaflet.markercluster)
- BuildingPopup, BuildingSearch, NearbyBuildingsPanel components
- MapPage refactored with building search and incident proximity
- 24 building API tests (4 new for nearby/search)

### Sprint 3: Incident-Building Integration ✅ (January 2025)
- WebSocket integration for building updates (emit_building_created/updated, emit_floor_plan_uploaded/updated)
- BuildingSelector component for incident forms
- BuildingInfoPanel for incident detail sidebar
- Building incidents endpoint GET /buildings/{id}/incidents
- useWebSocket hook with joinBuilding/leaveBuilding
- 13 incident API tests

### Sprint 4: Key Location Marking Tool ✅ (January 2025)
- LocationMarker component with draggable markers and type icons
- markerStore (Zustand) for marker editing state
- FloorPlanEditor with toolbar, click-to-place, drag support
- MarkerPropertiesModal for editing marker metadata
- FloorPlanPrint for print-optimized view
- 20+ LocationMarkerType types with category groupings

### Sprint 5: BIM Import ✅ (January 2025)
- IFCParser service for parsing Industry Foundation Classes files
- BIMImport component with drag-drop file upload
- BIMDataViewer component for displaying imported metadata
- POST /buildings/{id}/import-bim endpoint
- BIMData, BIMImportResult, BIMFloorInfo types

### Sprint 6: Document & Photo Management ✅ (January 2025)
- **Backend Models**: BuildingDocument, BuildingPhoto, Inspection with relationships
- **API Endpoints**:
  - Documents: GET/POST /buildings/{id}/documents, PATCH/DELETE /documents/{id}
  - Photos: GET/POST /buildings/{id}/photos, DELETE /photos/{id}
  - Inspections: GET/POST /buildings/{id}/inspections, GET /inspections/upcoming|overdue, PATCH/DELETE /inspections/{id}
- **Frontend Stores**: documentStore, photoStore, inspectionStore (Zustand)
- **Components**:
  - DocumentManager: Document list, upload, category filtering, version tracking
  - PhotoGallery: Responsive grid, lightbox, tag filtering, upload
  - PhotoCapture: Camera access with geolocation, file fallback
  - InspectionTracker: Inspection list, create/edit forms, status management
- **BuildingDetailPage**: New tabs for Documents, Photos, Inspections with lazy loading
- **Tests**: 57 new tests (16 documents, 17 photos, 24 inspections)

### Sprint 7: Real-time Updates ✅ (January 2025)
- **Backend**: PresenceService for tracking users on floor plans
- **WebSocket Events**: Floor plan room management (join/leave/heartbeat)
- **Marker Sync**: marker:added/updated/deleted events with optimistic updates
- **Presence Tracking**: presence:joined/left/list/editing events
- **Device Status**: Real-time device position and status updates
- **Frontend Stores**:
  - presenceStore: User presence tracking with heartbeat
  - devicePositionStore: Real-time device position sync
  - markerStore: Extended with optimistic updates and conflict detection
- **Components**:
  - PresenceIndicator: Shows active users with avatars and editing state
  - DeviceStatusOverlay: Real-time device icons on floor plans
- **Hooks**: useFloorPlanSync orchestrates all real-time synchronization
- **Integration**: FloorPlanEditor and BuildingDetailPage with real-time features
- **Tests**: 14 presence service tests

---

*Last Updated: January 2025*
