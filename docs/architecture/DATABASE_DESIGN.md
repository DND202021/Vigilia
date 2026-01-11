# Database Design

This document describes the database architecture and schema design for ERIOP.

## Table of Contents

1. [Overview](#overview)
2. [Database Selection](#database-selection)
3. [Schema Design](#schema-design)
4. [Data Models](#data-models)
5. [Indexing Strategy](#indexing-strategy)
6. [Data Retention](#data-retention)
7. [Backup and Recovery](#backup-and-recovery)

---

## Overview

ERIOP uses a polyglot persistence approach with multiple databases optimized for specific use cases:

| Database | Purpose | Data Types |
|----------|---------|------------|
| **PostgreSQL** | Primary relational data | Users, incidents, resources, configurations |
| **TimescaleDB** | Time-series data | Telemetry, location history, metrics |
| **Redis** | Caching and real-time | Sessions, pub/sub, rate limiting, real-time state |
| **SQLite** | Offline storage | Mobile app local data |

---

## Database Selection

### PostgreSQL (Primary)

**Version:** 15+

**Rationale:**
- ACID compliance for critical data
- Robust security features
- Excellent JSON support for flexible schemas
- Proven reliability in mission-critical systems
- Native support for row-level security

**Use Cases:**
- User accounts and authentication
- Incident records
- Resource inventory
- Audit logs
- Configuration data

### TimescaleDB (Time-Series)

**Version:** 2.x (PostgreSQL extension)

**Rationale:**
- Optimized for time-series data
- Automatic partitioning (hypertables)
- Compression for storage efficiency
- Compatible with PostgreSQL tools

**Use Cases:**
- Device telemetry
- Location tracking history
- System metrics
- Alert history

### Redis (Cache/Real-time)

**Version:** 7+

**Rationale:**
- Sub-millisecond latency
- Pub/sub for real-time updates
- Native data structures
- Cluster support for HA

**Use Cases:**
- Session storage
- Real-time presence
- Rate limiting
- Caching frequently accessed data
- Pub/sub messaging

---

## Schema Design

### Entity Relationship Overview

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                               │
│   ┌─────────────┐         ┌─────────────┐         ┌─────────────┐           │
│   │    Users    │────────▶│   Roles     │◀────────│ Permissions │           │
│   └─────────────┘         └─────────────┘         └─────────────┘           │
│          │                                                                    │
│          │                                                                    │
│          ▼                                                                    │
│   ┌─────────────┐         ┌─────────────┐         ┌─────────────┐           │
│   │  Agencies   │◀────────│   Units     │────────▶│  Resources  │           │
│   └─────────────┘         └─────────────┘         └─────────────┘           │
│          │                       │                       │                    │
│          │                       │                       │                    │
│          ▼                       ▼                       ▼                    │
│   ┌─────────────┐         ┌─────────────┐         ┌─────────────┐           │
│   │  Incidents  │◀────────│ Assignments │────────▶│   Alerts    │           │
│   └─────────────┘         └─────────────┘         └─────────────┘           │
│          │                                                                    │
│          ▼                                                                    │
│   ┌─────────────┐         ┌─────────────┐                                    │
│   │  Messages   │         │ Audit Logs  │                                    │
│   └─────────────┘         └─────────────┘                                    │
│                                                                               │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Data Models

### Core Entities

#### Users

```sql
-- Users table: Core user identity
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(255) NOT NULL UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,
    first_name      VARCHAR(100) NOT NULL,
    last_name       VARCHAR(100) NOT NULL,
    phone           VARCHAR(20),
    badge_number    VARCHAR(50),
    agency_id       UUID REFERENCES agencies(id),
    status          VARCHAR(20) NOT NULL DEFAULT 'active',
    mfa_enabled     BOOLEAN NOT NULL DEFAULT FALSE,
    mfa_secret      VARCHAR(255),  -- Encrypted
    last_login      TIMESTAMP WITH TIME ZONE,
    failed_attempts INTEGER NOT NULL DEFAULT 0,
    locked_until    TIMESTAMP WITH TIME ZONE,
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    CONSTRAINT users_status_check CHECK (status IN ('active', 'inactive', 'suspended', 'pending'))
);

-- Indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_agency ON users(agency_id);
CREATE INDEX idx_users_status ON users(status);
```

#### Agencies

```sql
-- Agencies table: Organizations using the system
CREATE TABLE agencies (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(255) NOT NULL,
    code            VARCHAR(20) NOT NULL UNIQUE,  -- e.g., "SWAT-01", "FD-NORTH"
    type            VARCHAR(50) NOT NULL,
    jurisdiction    VARCHAR(255),
    parent_id       UUID REFERENCES agencies(id),
    contact_email   VARCHAR(255),
    contact_phone   VARCHAR(20),
    address         JSONB,
    settings        JSONB NOT NULL DEFAULT '{}',
    status          VARCHAR(20) NOT NULL DEFAULT 'active',
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    CONSTRAINT agencies_type_check CHECK (type IN ('police', 'fire', 'ems', 'swat', 'dispatch', 'military', 'other'))
);

-- Indexes
CREATE INDEX idx_agencies_code ON agencies(code);
CREATE INDEX idx_agencies_type ON agencies(type);
CREATE INDEX idx_agencies_parent ON agencies(parent_id);
```

#### Incidents

```sql
-- Incidents table: Emergency incidents
CREATE TABLE incidents (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    incident_number VARCHAR(50) NOT NULL UNIQUE,  -- Human-readable ID
    type            VARCHAR(50) NOT NULL,
    category        VARCHAR(50) NOT NULL,
    priority        INTEGER NOT NULL DEFAULT 3,   -- 1=Critical, 5=Low
    status          VARCHAR(30) NOT NULL DEFAULT 'new',
    title           VARCHAR(255) NOT NULL,
    description     TEXT,
    location        GEOGRAPHY(POINT, 4326),       -- PostGIS geometry
    address         JSONB,
    reported_by     UUID REFERENCES users(id),
    assigned_to     UUID REFERENCES units(id),
    agency_id       UUID NOT NULL REFERENCES agencies(id),
    parent_id       UUID REFERENCES incidents(id), -- For linked incidents
    source_alert_id UUID REFERENCES alerts(id),
    metadata        JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    resolved_at     TIMESTAMP WITH TIME ZONE,
    closed_at       TIMESTAMP WITH TIME ZONE,
    
    CONSTRAINT incidents_priority_check CHECK (priority BETWEEN 1 AND 5),
    CONSTRAINT incidents_status_check CHECK (status IN (
        'new', 'assigned', 'en_route', 'on_scene', 
        'resolved', 'closed', 'cancelled'
    ))
);

-- Indexes
CREATE INDEX idx_incidents_number ON incidents(incident_number);
CREATE INDEX idx_incidents_status ON incidents(status);
CREATE INDEX idx_incidents_priority ON incidents(priority);
CREATE INDEX idx_incidents_agency ON incidents(agency_id);
CREATE INDEX idx_incidents_created ON incidents(created_at DESC);
CREATE INDEX idx_incidents_location ON incidents USING GIST(location);
```

#### Resources

```sql
-- Resources table: Personnel, vehicles, equipment
CREATE TABLE resources (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type            VARCHAR(30) NOT NULL,
    subtype         VARCHAR(50),
    name            VARCHAR(255) NOT NULL,
    identifier      VARCHAR(100) NOT NULL,  -- Badge#, vehicle#, serial#
    agency_id       UUID NOT NULL REFERENCES agencies(id),
    unit_id         UUID REFERENCES units(id),
    status          VARCHAR(30) NOT NULL DEFAULT 'available',
    current_location GEOGRAPHY(POINT, 4326),
    capabilities    VARCHAR(50)[] DEFAULT '{}',
    specifications  JSONB NOT NULL DEFAULT '{}',
    last_maintenance TIMESTAMP WITH TIME ZONE,
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    CONSTRAINT resources_type_check CHECK (type IN ('personnel', 'vehicle', 'equipment')),
    CONSTRAINT resources_status_check CHECK (status IN (
        'available', 'assigned', 'en_route', 'on_scene',
        'off_duty', 'maintenance', 'out_of_service'
    ))
);

-- Indexes
CREATE INDEX idx_resources_type ON resources(type);
CREATE INDEX idx_resources_agency ON resources(agency_id);
CREATE INDEX idx_resources_unit ON resources(unit_id);
CREATE INDEX idx_resources_status ON resources(status);
CREATE INDEX idx_resources_location ON resources USING GIST(current_location);
```

#### Alerts

```sql
-- Alerts table: Incoming alerts from external systems
CREATE TABLE alerts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id     VARCHAR(255),           -- ID from source system
    source          VARCHAR(100) NOT NULL,  -- e.g., "alarm_system", "axis_mic"
    type            VARCHAR(50) NOT NULL,
    severity        INTEGER NOT NULL DEFAULT 3,
    status          VARCHAR(30) NOT NULL DEFAULT 'new',
    title           VARCHAR(255) NOT NULL,
    description     TEXT,
    location        GEOGRAPHY(POINT, 4326),
    address         JSONB,
    raw_payload     JSONB,                  -- Original data from source
    processed_at    TIMESTAMP WITH TIME ZONE,
    acknowledged_by UUID REFERENCES users(id),
    acknowledged_at TIMESTAMP WITH TIME ZONE,
    incident_id     UUID REFERENCES incidents(id),  -- If converted to incident
    metadata        JSONB NOT NULL DEFAULT '{}',
    received_at     TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    CONSTRAINT alerts_severity_check CHECK (severity BETWEEN 1 AND 5),
    CONSTRAINT alerts_status_check CHECK (status IN (
        'new', 'processing', 'acknowledged', 'converted', 
        'dismissed', 'expired'
    ))
);

-- Indexes
CREATE INDEX idx_alerts_source ON alerts(source);
CREATE INDEX idx_alerts_status ON alerts(status);
CREATE INDEX idx_alerts_severity ON alerts(severity);
CREATE INDEX idx_alerts_received ON alerts(received_at DESC);
CREATE INDEX idx_alerts_external ON alerts(source, external_id);
```

#### Messages

```sql
-- Messages table: Communication hub messages
CREATE TABLE messages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    channel_id      UUID NOT NULL REFERENCES channels(id),
    sender_id       UUID NOT NULL REFERENCES users(id),
    message_type    VARCHAR(30) NOT NULL DEFAULT 'text',
    content         TEXT NOT NULL,
    content_encrypted BYTEA,  -- For field-level encryption
    attachments     JSONB DEFAULT '[]',
    reply_to        UUID REFERENCES messages(id),
    status          VARCHAR(20) NOT NULL DEFAULT 'sent',
    priority        VARCHAR(20) NOT NULL DEFAULT 'normal',
    metadata        JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    edited_at       TIMESTAMP WITH TIME ZONE,
    deleted_at      TIMESTAMP WITH TIME ZONE,
    
    CONSTRAINT messages_type_check CHECK (message_type IN ('text', 'alert', 'status', 'file', 'location')),
    CONSTRAINT messages_priority_check CHECK (priority IN ('low', 'normal', 'high', 'urgent'))
);

-- Indexes
CREATE INDEX idx_messages_channel ON messages(channel_id);
CREATE INDEX idx_messages_sender ON messages(sender_id);
CREATE INDEX idx_messages_created ON messages(created_at DESC);
CREATE INDEX idx_messages_channel_created ON messages(channel_id, created_at DESC);
```

#### Audit Logs

```sql
-- Audit logs table: Immutable audit trail
CREATE TABLE audit_logs (
    id              BIGSERIAL PRIMARY KEY,
    timestamp       TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    user_id         UUID REFERENCES users(id),
    session_id      VARCHAR(255),
    action          VARCHAR(100) NOT NULL,
    resource_type   VARCHAR(100) NOT NULL,
    resource_id     VARCHAR(255),
    agency_id       UUID REFERENCES agencies(id),
    ip_address      INET,
    user_agent      VARCHAR(500),
    request_id      VARCHAR(100),
    old_values      JSONB,  -- Sanitized, no PII
    new_values      JSONB,  -- Sanitized, no PII
    metadata        JSONB NOT NULL DEFAULT '{}',
    
    -- No UPDATE or DELETE allowed on this table
    CONSTRAINT audit_logs_action_check CHECK (action IS NOT NULL)
);

-- Indexes for query performance
CREATE INDEX idx_audit_logs_timestamp ON audit_logs(timestamp DESC);
CREATE INDEX idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX idx_audit_logs_agency ON audit_logs(agency_id);

-- Partitioning by month for performance and retention
-- (Implementation depends on PostgreSQL version)
```

### Time-Series Tables (TimescaleDB)

#### Telemetry

```sql
-- Telemetry hypertable: Device/sensor data
CREATE TABLE telemetry (
    time            TIMESTAMP WITH TIME ZONE NOT NULL,
    device_id       UUID NOT NULL,
    device_type     VARCHAR(50) NOT NULL,
    metric_name     VARCHAR(100) NOT NULL,
    metric_value    DOUBLE PRECISION,
    metric_text     VARCHAR(255),
    location        GEOGRAPHY(POINT, 4326),
    metadata        JSONB NOT NULL DEFAULT '{}'
);

-- Convert to hypertable
SELECT create_hypertable('telemetry', 'time');

-- Indexes
CREATE INDEX idx_telemetry_device ON telemetry(device_id, time DESC);
CREATE INDEX idx_telemetry_metric ON telemetry(metric_name, time DESC);
CREATE INDEX idx_telemetry_location ON telemetry USING GIST(location);

-- Compression policy (compress chunks older than 7 days)
SELECT add_compression_policy('telemetry', INTERVAL '7 days');

-- Retention policy (drop data older than 2 years)
SELECT add_retention_policy('telemetry', INTERVAL '2 years');
```

#### Location History

```sql
-- Location history hypertable: Resource tracking
CREATE TABLE location_history (
    time            TIMESTAMP WITH TIME ZONE NOT NULL,
    resource_id     UUID NOT NULL,
    resource_type   VARCHAR(30) NOT NULL,
    location        GEOGRAPHY(POINT, 4326) NOT NULL,
    speed           DOUBLE PRECISION,
    heading         DOUBLE PRECISION,
    accuracy        DOUBLE PRECISION,
    source          VARCHAR(50) NOT NULL DEFAULT 'gps',
    metadata        JSONB NOT NULL DEFAULT '{}'
);

-- Convert to hypertable
SELECT create_hypertable('location_history', 'time');

-- Indexes
CREATE INDEX idx_location_resource ON location_history(resource_id, time DESC);
CREATE INDEX idx_location_geo ON location_history USING GIST(location);

-- Compression and retention
SELECT add_compression_policy('location_history', INTERVAL '7 days');
SELECT add_retention_policy('location_history', INTERVAL '1 year');
```

---

## Indexing Strategy

### Index Types

| Type | Use Case | Example |
|------|----------|---------|
| B-tree (default) | Equality, range queries | `status`, `created_at` |
| GIST | Spatial queries | `location` |
| GIN | JSONB, full-text | `metadata`, `description` |
| Hash | Equality only (rare) | `external_id` |

### Performance Considerations

1. **Composite indexes** for common query patterns
2. **Partial indexes** for filtered queries
3. **Covering indexes** to avoid table lookups
4. **Monitor and prune** unused indexes

```sql
-- Example: Partial index for active incidents only
CREATE INDEX idx_incidents_active 
ON incidents(priority, created_at DESC) 
WHERE status NOT IN ('closed', 'cancelled');

-- Example: Covering index for incident list
CREATE INDEX idx_incidents_list 
ON incidents(agency_id, status, created_at DESC) 
INCLUDE (incident_number, title, priority);
```

---

## Data Retention

| Data Type | Retention Period | Storage Tier |
|-----------|------------------|--------------|
| Incidents | 7 years | Primary |
| Audit Logs | 7 years | Primary → Archive |
| Messages | 2 years | Primary → Archive |
| Telemetry | 2 years | TimescaleDB (compressed) |
| Location History | 1 year | TimescaleDB (compressed) |
| Sessions | 30 days | Redis |
| Cache | Variable | Redis (TTL) |

### Archival Strategy

```sql
-- Archive old audit logs to cold storage
-- Run monthly via scheduled job
INSERT INTO audit_logs_archive 
SELECT * FROM audit_logs 
WHERE timestamp < NOW() - INTERVAL '1 year';

DELETE FROM audit_logs 
WHERE timestamp < NOW() - INTERVAL '1 year';
```

---

## Backup and Recovery

### Backup Strategy

| Type | Frequency | Retention | Method |
|------|-----------|-----------|--------|
| Full Backup | Daily | 30 days | pg_dump / pg_basebackup |
| Incremental | Hourly | 7 days | WAL archiving |
| Point-in-Time | Continuous | 7 days | WAL + base backup |

### Recovery Objectives

| Metric | Target |
|--------|--------|
| **RPO** (Recovery Point Objective) | < 5 minutes |
| **RTO** (Recovery Time Objective) | < 30 minutes |

### Backup Commands

```bash
# Full backup
pg_dump -Fc -f eriop_backup_$(date +%Y%m%d).dump eriop

# Restore
pg_restore -d eriop eriop_backup_20250101.dump

# Point-in-time recovery
# Requires proper WAL archiving configuration
```

---

## Related Documents

- [System Architecture](SYSTEM_ARCHITECTURE.md)
- [API Design](API_DESIGN.md)
- [Security Framework](../security/SECURITY_FRAMEWORK.md)
- [ADR-002: Database Selection](../adr/002-database-selection.md)

---

*Document Version: 1.0 | Last Updated: January 2025 | Classification: Confidential*
