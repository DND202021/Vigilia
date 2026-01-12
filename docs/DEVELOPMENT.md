# ERIOP Development Guide

## Getting Started

### Prerequisites

- **Python 3.11+** - Backend runtime
- **Node.js 18+** - Frontend build tools
- **PostgreSQL 14+** - Production database (SQLite for development)
- **Redis** - Caching and session storage (optional for development)

### Environment Setup

#### Backend

```bash
cd src/backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Install dependencies (including dev)
pip install -e ".[dev]"

# Create environment file
cp .env.example .env

# For development with SQLite:
# Edit .env and set:
# DATABASE_URL=sqlite+aiosqlite:///./dev.db
```

#### Frontend

```bash
cd src/frontend

# Install dependencies
npm install

# Create environment file (optional)
echo "VITE_API_URL=http://localhost:8000/api/v1" > .env.local
```

### Running the Application

#### Start Backend

```bash
cd src/backend
source venv/bin/activate

# Development with auto-reload
uvicorn app.main:app --reload --port 8000

# With debug logging
DEBUG=true uvicorn app.main:app --reload --port 8000
```

#### Start Frontend

```bash
cd src/frontend

# Development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

### Database Setup

#### Create Tables (Development)

```bash
cd src/backend
python -c "
import asyncio
from app.core.deps import engine
from app.models import Base

async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print('Tables created')

asyncio.run(create_tables())
"
```

#### Run Migrations (Production)

```bash
cd src/backend
alembic upgrade head
```

#### Create Test User

```bash
cd src/backend
python scripts/create_admin.py
# Creates admin@test.com / admin123
```

---

## Architecture

### Backend Structure

```
app/
├── api/                 # FastAPI route handlers
│   ├── __init__.py     # Router aggregation
│   ├── auth.py         # Authentication endpoints
│   ├── incidents.py    # Incident CRUD
│   ├── resources.py    # Resource management
│   ├── alerts.py       # Alert processing
│   ├── analytics.py    # Analytics & reporting
│   ├── dashboard.py    # Dashboard data
│   ├── audit.py        # Audit log access
│   ├── communications.py # Messaging
│   ├── notifications.py  # Push notifications
│   ├── geospatial.py   # Location queries
│   ├── alarm_receiver.py # Alarm protocols
│   ├── devices.py      # Axis devices
│   ├── cad.py          # CAD integration
│   ├── gis.py          # GIS layers
│   └── streaming.py    # Media streaming
│
├── core/               # Core utilities
│   ├── config.py       # Pydantic settings
│   ├── deps.py         # Dependency injection
│   └── security.py     # Password/token handling
│
├── models/             # SQLAlchemy ORM models
│   ├── base.py         # Base model with mixins
│   ├── user.py         # User & roles
│   ├── agency.py       # Multi-tenancy
│   ├── incident.py     # Incident management
│   ├── resource.py     # Resources (personnel, vehicles)
│   ├── alert.py        # Alert processing
│   └── audit.py        # Audit logging
│
├── services/           # Business logic layer
│   ├── auth_service.py        # Authentication
│   ├── mfa_service.py         # Multi-factor auth
│   ├── assignment_service.py  # Resource assignment
│   ├── communication_hub.py   # Messaging
│   ├── push_notifications.py  # WebPush
│   ├── socketio.py            # Real-time events
│   ├── analytics.py           # Metrics & reports
│   └── fundamentum_mqtt.py    # MQTT integration
│
└── integrations/       # External systems
    ├── alarms/         # Alarm receivers
    │   ├── sia_dc07.py
    │   ├── contact_id.py
    │   └── sia_dc09.py
    ├── axis/           # Axis VAPIX
    │   └── vapix_client.py
    └── cad/            # CAD adapters
        └── base_adapter.py
```

### Frontend Structure

```
src/
├── components/
│   ├── ui/             # Base components
│   │   ├── Button.tsx
│   │   ├── Card.tsx
│   │   ├── Modal.tsx
│   │   ├── Badge.tsx
│   │   ├── Spinner.tsx
│   │   ├── Input.tsx
│   │   └── Select.tsx
│   └── layout/         # Layout components
│       ├── Layout.tsx
│       ├── Navbar.tsx
│       ├── ProtectedRoute.tsx
│       └── OfflineIndicator.tsx
│
├── pages/              # Page components (lazy-loaded)
│   ├── DashboardPage.tsx
│   ├── IncidentsPage.tsx
│   ├── IncidentDetailPage.tsx
│   ├── AlertsPage.tsx
│   ├── ResourcesPage.tsx
│   ├── MapPage.tsx
│   ├── AnalyticsPage.tsx
│   └── LoginPage.tsx
│
├── stores/             # Zustand state management
│   ├── authStore.ts
│   ├── incidentStore.ts
│   ├── alertStore.ts
│   └── resourceStore.ts
│
├── services/           # API & utilities
│   ├── api.ts          # Axios client
│   ├── syncService.ts  # Offline sync
│   └── offlineDb.ts    # IndexedDB
│
├── hooks/              # Custom hooks
│   ├── useWebSocket.ts
│   ├── useOffline.ts
│   └── useInterval.ts
│
├── types/              # TypeScript definitions
│   └── index.ts
│
└── utils/              # Helper functions
    └── index.ts
```

---

## Key Patterns

### Backend Patterns

#### Dependency Injection

```python
# app/core/deps.py
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session

# Usage in routes
@router.get("/items")
async def list_items(db: AsyncSession = Depends(get_db)):
    ...
```

#### Permission-Based Access

```python
from app.core.deps import require_permission, Permission

@router.post("/incidents")
async def create_incident(
    data: IncidentCreate,
    current_user: User = Depends(require_permission(Permission.INCIDENT_CREATE)),
):
    ...
```

#### Role-Based Access

```python
from app.core.deps import require_role
from app.models.user import UserRole

@router.delete("/users/{id}")
async def delete_user(
    id: str,
    current_user: User = Depends(require_role(UserRole.SYSTEM_ADMIN)),
):
    ...
```

### Frontend Patterns

#### State Management (Zustand)

```typescript
// stores/incidentStore.ts
import { create } from 'zustand';

interface IncidentStore {
  incidents: Incident[];
  isLoading: boolean;
  fetchIncidents: () => Promise<void>;
}

export const useIncidentStore = create<IncidentStore>((set) => ({
  incidents: [],
  isLoading: false,
  fetchIncidents: async () => {
    set({ isLoading: true });
    const data = await incidentsApi.list();
    set({ incidents: data.items, isLoading: false });
  },
}));
```

#### Protected Routes

```typescript
// components/layout/ProtectedRoute.tsx
export function ProtectedRoute({ children }: { children: ReactNode }) {
  const { isAuthenticated, isLoading } = useAuthStore();

  if (isLoading) return <Spinner />;
  if (!isAuthenticated) return <Navigate to="/login" />;

  return <>{children}</>;
}
```

#### Code Splitting

```typescript
// App.tsx
const DashboardPage = lazy(() =>
  import('./pages/DashboardPage').then(m => ({ default: m.DashboardPage }))
);

<Suspense fallback={<PageLoader />}>
  <Routes>
    <Route path="/" element={<DashboardPage />} />
  </Routes>
</Suspense>
```

---

## Testing

### Backend Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=app --cov-report=html

# Specific test file
pytest tests/test_auth.py -v

# Run with markers
pytest -m "not slow" -v
```

#### Test Structure

```python
# tests/test_auth.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, test_user):
    response = await client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "testpass"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()
```

### Frontend Testing

```bash
# Run tests
npm test

# With coverage
npm run test:coverage

# Watch mode
npm run test:watch
```

#### Test Structure

```typescript
// src/__tests__/stores.test.ts
import { renderHook, act } from '@testing-library/react';
import { useAuthStore } from '../stores/authStore';

describe('AuthStore', () => {
  it('should login successfully', async () => {
    const { result } = renderHook(() => useAuthStore());

    await act(async () => {
      await result.current.login('test@example.com', 'password');
    });

    expect(result.current.isAuthenticated).toBe(true);
  });
});
```

---

## Database Migrations

### Creating Migrations

```bash
cd src/backend

# Auto-generate migration
alembic revision --autogenerate -m "Add new_field to incidents"

# Create empty migration
alembic revision -m "Custom migration"
```

### Running Migrations

```bash
# Upgrade to latest
alembic upgrade head

# Upgrade to specific revision
alembic upgrade abc123

# Downgrade one step
alembic downgrade -1

# Show current revision
alembic current
```

---

## Common Tasks

### Adding a New API Endpoint

1. Create/update model in `app/models/`
2. Create Pydantic schemas in `app/api/` route file
3. Add route handler
4. Register in `app/api/__init__.py` if new file
5. Write tests

### Adding a New Frontend Page

1. Create page component in `src/pages/`
2. Export from `src/pages/index.ts`
3. Add lazy import in `App.tsx`
4. Add route in `App.tsx`
5. Add navigation link in `Navbar.tsx`

### Adding a New Permission

1. Add to `Permission` enum in `app/core/deps.py`
2. Add to relevant role mappings in `ROLE_PERMISSIONS`
3. Use with `require_permission()` decorator

---

## Debugging

### Backend Logging

```python
import structlog
logger = structlog.get_logger()

logger.info("Processing request", user_id=user.id, action="create")
logger.error("Operation failed", error=str(e), traceback=True)
```

### Frontend Debugging

```typescript
// Enable debug logging
console.debug('API Response:', response);

// React DevTools
// Install browser extension for component inspection

// Network debugging
// Use browser DevTools Network tab
```

### Database Debugging

```python
# Enable SQL logging
# In .env: DEBUG=true

# Or in code:
engine = create_async_engine(url, echo=True)
```

---

## Performance Tips

### Backend

- Use `select_in_load` for related objects
- Index frequently queried columns
- Use Redis for caching
- Implement pagination for lists

### Frontend

- Use React.lazy for code splitting
- Implement virtual scrolling for long lists
- Memoize expensive computations
- Use SWR/React Query for data caching

---

## Security Checklist

- [ ] Strong SECRET_KEY in production
- [ ] HTTPS only in production
- [ ] CORS configured for production domain
- [ ] Rate limiting enabled
- [ ] Input validation on all endpoints
- [ ] SQL injection prevention (use ORM)
- [ ] XSS prevention (React escaping)
- [ ] CSRF protection enabled
- [ ] Secure cookie settings
- [ ] Audit logging enabled

---

*Document Version: 1.0 | Last Updated: January 2025*
