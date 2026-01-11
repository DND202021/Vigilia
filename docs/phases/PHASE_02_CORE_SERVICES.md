# Phase 2: Core Services

**Timeline:** Weeks 5-10  
**Goal:** Build essential emergency response functionality

## Overview

Phase 2 implements the core business logic services that power emergency response operations. This includes incident management, resource tracking, alert processing, and the communication hub.

---

## Objectives

1. Build Incident Management Service
2. Build Resource Tracking Service
3. Build Alert Engine
4. Build Communication Hub
5. Implement real-time event streaming
6. Set up comprehensive testing

---

## Deliverables

### D2.1 Incident Management Service

| Component | Description |
|-----------|-------------|
| Incident CRUD | Create, read, update incidents |
| Lifecycle Management | State transitions with validation |
| Categorization | Type, category, priority assignment |
| Assignment Engine | Unit assignment and reassignment |
| Escalation | Priority escalation workflows |
| Timeline | Complete incident event history |

**API Endpoints:**
```
POST   /api/v1/incidents              # Create incident
GET    /api/v1/incidents              # List incidents (paginated, filtered)
GET    /api/v1/incidents/{id}         # Get incident details
PATCH  /api/v1/incidents/{id}         # Update incident
POST   /api/v1/incidents/{id}/assign  # Assign unit
POST   /api/v1/incidents/{id}/escalate # Escalate priority
GET    /api/v1/incidents/{id}/timeline # Get timeline
POST   /api/v1/incidents/{id}/close   # Close incident
```

**Acceptance Criteria:**
- [ ] Incident creation with auto-generated incident number
- [ ] State machine enforces valid transitions only
- [ ] Assignment notifies unit via real-time channel
- [ ] Full audit trail on all changes
- [ ] Geospatial queries work (find incidents near location)

### D2.2 Resource Tracking Service

| Component | Description |
|-----------|-------------|
| Personnel Tracking | Status and location of personnel |
| Vehicle Tracking | Real-time vehicle positions |
| Equipment Inventory | Equipment assignment tracking |
| Availability Engine | Calculate available resources |
| Capability Matching | Match resources to incident needs |

**API Endpoints:**
```
GET    /api/v1/resources/personnel          # List personnel
GET    /api/v1/resources/vehicles           # List vehicles
GET    /api/v1/resources/equipment          # List equipment
PATCH  /api/v1/resources/{type}/{id}/status # Update status
POST   /api/v1/resources/{type}/{id}/location # Update location
GET    /api/v1/resources/available          # Get available resources
GET    /api/v1/resources/nearby             # Find resources near location
```

**Acceptance Criteria:**
- [ ] Real-time status updates via WebSocket
- [ ] Location history stored in TimescaleDB
- [ ] Availability calculation considers status and assignments
- [ ] Proximity search returns nearest available resources
- [ ] Status changes logged for audit

### D2.3 Alert Engine

| Component | Description |
|-----------|-------------|
| Alert Ingestion | Receive alerts from multiple sources |
| Classification | Categorize and prioritize alerts |
| Deduplication | Identify duplicate alerts |
| Routing Engine | Route to appropriate recipients |
| Notification Dispatch | Trigger notifications |
| Auto-Incident Creation | Create incidents from critical alerts |

**Alert Sources:**
```
MQTT (Fundamentum) ──┐
                     │
API (External)    ───┼──▶ Alert Engine ──▶ Routing ──▶ Notifications
                     │                          │
Webhooks          ───┘                          └──▶ Incident Creation
```

**Acceptance Criteria:**
- [ ] Alerts processed within 500ms
- [ ] Duplicate alerts detected within 5-minute window
- [ ] Routing rules configurable per alert type
- [ ] High-severity alerts auto-create incidents
- [ ] All alerts logged with source information

### D2.4 Communication Hub

| Component | Description |
|-----------|-------------|
| Messaging | Secure message exchange |
| Channels | Incident, team, agency channels |
| Message Persistence | Full message history |
| Push Notifications | Mobile notification delivery |
| Presence | Online status tracking |

**API Endpoints:**
```
GET    /api/v1/channels                      # List user's channels
POST   /api/v1/channels                      # Create channel
GET    /api/v1/channels/{id}/messages        # Get messages
POST   /api/v1/channels/{id}/messages        # Send message
POST   /api/v1/channels/{id}/read            # Mark as read
```

**WebSocket Events:**
```
message.new       # New message received
message.read      # Message read receipt
channel.created   # New channel created
presence.update   # User online/offline
```

**Acceptance Criteria:**
- [ ] Messages delivered in real-time via WebSocket
- [ ] Message history persisted and searchable
- [ ] Push notifications work on mobile
- [ ] Incident channels created automatically
- [ ] Message encryption at rest

---

## Technical Specifications

### Service Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              API Gateway                                     │
└────────────────────────────────────┬────────────────────────────────────────┘
                                     │
         ┌───────────────────────────┼───────────────────────────┐
         │                           │                           │
         ▼                           ▼                           ▼
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│    Incident     │       │    Resource     │       │     Alert       │
│    Service      │◀─────▶│    Service      │◀─────▶│    Engine       │
└────────┬────────┘       └────────┬────────┘       └────────┬────────┘
         │                         │                         │
         │                         │                         │
         └─────────────────────────┼─────────────────────────┘
                                   │
                                   ▼
                         ┌─────────────────┐
                         │  Communication  │
                         │      Hub        │
                         └────────┬────────┘
                                  │
                    ┌─────────────┼─────────────┐
                    │             │             │
                    ▼             ▼             ▼
              ┌──────────┐ ┌──────────┐ ┌──────────┐
              │PostgreSQL│ │TimescaleDB│ │  Redis   │
              └──────────┘ └──────────┘ └──────────┘
```

### Event-Driven Communication

```python
# Event types for internal communication
class EventTypes(Enum):
    # Incident events
    INCIDENT_CREATED = "incident.created"
    INCIDENT_UPDATED = "incident.updated"
    INCIDENT_ASSIGNED = "incident.assigned"
    INCIDENT_ESCALATED = "incident.escalated"
    INCIDENT_CLOSED = "incident.closed"
    
    # Resource events
    RESOURCE_STATUS_CHANGED = "resource.status_changed"
    RESOURCE_LOCATION_UPDATED = "resource.location_updated"
    RESOURCE_ASSIGNED = "resource.assigned"
    
    # Alert events
    ALERT_RECEIVED = "alert.received"
    ALERT_ACKNOWLEDGED = "alert.acknowledged"
    ALERT_DISMISSED = "alert.dismissed"
    
    # Message events
    MESSAGE_SENT = "message.sent"
    MESSAGE_READ = "message.read"
```

### Data Models

```python
# Incident model
class Incident(Base):
    __tablename__ = "incidents"
    
    id = Column(UUID, primary_key=True, default=uuid4)
    incident_number = Column(String(50), unique=True, nullable=False)
    type = Column(String(50), nullable=False)
    category = Column(String(50), nullable=False)
    priority = Column(Integer, nullable=False, default=3)
    status = Column(String(30), nullable=False, default="new")
    title = Column(String(255), nullable=False)
    description = Column(Text)
    location = Column(Geography("POINT", srid=4326))
    address = Column(JSONB)
    reported_by_id = Column(UUID, ForeignKey("users.id"))
    assigned_to_id = Column(UUID, ForeignKey("units.id"))
    agency_id = Column(UUID, ForeignKey("agencies.id"), nullable=False)
    parent_id = Column(UUID, ForeignKey("incidents.id"))
    source_alert_id = Column(UUID, ForeignKey("alerts.id"))
    metadata = Column(JSONB, nullable=False, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    resolved_at = Column(DateTime(timezone=True))
    closed_at = Column(DateTime(timezone=True))
```

### State Machine (Incidents)

```
                    ┌─────────────────┐
                    │      NEW        │
                    └────────┬────────┘
                             │ assign
                             ▼
                    ┌─────────────────┐
              ┌────▶│    ASSIGNED     │◀────┐
              │     └────────┬────────┘     │
              │              │ depart       │
              │              ▼              │
              │     ┌─────────────────┐     │
              │     │    EN_ROUTE     │     │
              │     └────────┬────────┘     │
              │              │ arrive       │
   reassign   │              ▼              │ reassign
              │     ┌─────────────────┐     │
              └─────│    ON_SCENE     │─────┘
                    └────────┬────────┘
                             │ resolve
                             ▼
                    ┌─────────────────┐
                    │    RESOLVED     │
                    └────────┬────────┘
                             │ close
                             ▼
                    ┌─────────────────┐
                    │     CLOSED      │
                    └─────────────────┘
                    
Any state can transition to CANCELLED
```

---

## Testing Requirements

### Unit Tests

```python
# Example test structure
class TestIncidentService:
    async def test_create_incident_success(self):
        """Creating an incident with valid data returns incident with number."""
        pass
    
    async def test_create_incident_missing_required_fields(self):
        """Creating an incident without required fields returns 422."""
        pass
    
    async def test_incident_state_transition_valid(self):
        """Valid state transitions succeed."""
        pass
    
    async def test_incident_state_transition_invalid(self):
        """Invalid state transitions return 400."""
        pass
```

### Integration Tests

- API endpoint integration tests
- Database integration tests
- Redis pub/sub tests
- WebSocket connection tests

### Performance Tests

- Alert processing under load (1000 alerts/sec)
- Concurrent incident creation
- WebSocket scalability

---

## Success Criteria

| Criterion | Measure | Target |
|-----------|---------|--------|
| Incident API | All CRUD operations | Working |
| Resource Tracking | Real-time updates | < 1s latency |
| Alert Processing | End-to-end latency | < 500ms |
| Message Delivery | Real-time delivery | < 1s |
| Test Coverage | Unit test coverage | > 85% |
| API Documentation | All endpoints documented | Yes |

---

## Schedule

```
Week 5:
├── Incident model and basic CRUD
├── Incident state machine
└── Unit tests for incident service

Week 6:
├── Incident assignment logic
├── Incident timeline
└── Incident API endpoints

Week 7:
├── Resource models
├── Resource tracking service
└── Location update pipeline

Week 8:
├── Alert engine architecture
├── Alert ingestion pipeline
└── Classification and routing

Week 9:
├── Communication hub
├── Channel management
└── Message persistence

Week 10:
├── WebSocket implementation
├── Push notification integration
├── Integration testing
└── Documentation and review
```

---

## Related Documents

- [Phase 1: Foundation](PHASE_01_FOUNDATION.md)
- [Phase 3: Integration Layer](PHASE_03_INTEGRATION.md)
- [API Design](../architecture/API_DESIGN.md)
- [Database Design](../architecture/DATABASE_DESIGN.md)

---

*Document Version: 1.0 | Last Updated: January 2025*
