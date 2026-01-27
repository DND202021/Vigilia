# Product Requirements Document (PRD)

# Sound Anomaly Detection & IoT Device Monitoring for ERIOP (Vigilia)

| Field | Value |
|-------|-------|
| **Document Version** | 1.0 |
| **Date** | January 27, 2026 |
| **Product** | ERIOP (Emergency Response IoT Platform) - Vigilia Division |
| **Feature** | Sound Anomaly Detection & IoT Device Monitoring |
| **Priority** | Critical - Prime Feature |
| **Classification** | Confidential |

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Background & Motivation](#2-background--motivation)
3. [Goals & Success Metrics](#3-goals--success-metrics)
4. [Reference System Analysis](#4-reference-system-analysis)
5. [Feature Requirements](#5-feature-requirements)
6. [Technical Architecture](#6-technical-architecture)
7. [Data Model Changes](#7-data-model-changes)
8. [API Endpoints](#8-api-endpoints)
9. [Frontend Components](#9-frontend-components)
10. [Implementation Phases](#10-implementation-phases)
11. [Acceptance Criteria](#11-acceptance-criteria)
12. [Risks & Mitigations](#12-risks--mitigations)
13. [Related Documents](#13-related-documents)

---

## 1. Executive Summary

ERIOP (Vigilia) is an Emergency Response IoT Platform designed to help first responders and tactical intervention units access detailed building systems information to better plan interventions. This PRD defines the integration of **Sound Anomaly Detection** as a prime feature, migrating and enhancing the capabilities currently demonstrated in the Dimonoff Security ThingsBoard dashboard into ERIOP's native platform.

The feature enables real-time detection of gunshots, explosions, glass breakage, aggression, and screams via Axis IP Microphones placed within buildings, visualized on interactive floor plans, and surfaced as actionable alerts with audio replay capabilities for first responders.

---

## 2. Background & Motivation

### 2.1 Current State

**ERIOP has existing backend integration code** (Phase 3 - completed) for:
- Axis audio analytics client (`app/integrations/axis/client.py`) - VAPIX API communication
- Audio event types and subscriber (`app/integrations/axis/events.py`) - Gunshot, glass break, aggression, scream, explosion, car alarm detection
- Alert generator (`app/integrations/axis/alert_generator.py`) - Confidence thresholds, severity mapping, auto-incident creation
- Building model with floor plans (`app/models/building.py`) - Full building data model with `FloorPlan` including `key_locations` JSON field

**What is missing:**
- No IoT device management (CRUD, registration, configuration)
- No device placement on floor plans (interactive positioning)
- No real-time sound anomaly alert visualization
- No device monitoring dashboard (online/offline status, battery, signal)
- No audio replay or audio clip download capabilities
- No building-specific alert views with floor-level filtering
- No notification contact management (call, SMS, email alerting)
- No alert history charts or trends per building/floor
- No connection between the Axis backend integration and the frontend

### 2.2 Reference System (ThingsBoard Demo)

The Dimonoff Security dashboard at `thingsboard.cloud` provides a working demo with:

| Feature | ThingsBoard Demo | ERIOP Status |
|---------|-----------------|--------------|
| Building map with alert indicators | Green/Red pins on map | Map exists, no alert pins |
| Building tree navigation | Hierarchical tree (Building > Floor) | Building list exists, no tree |
| Interactive floor plans | Floor plan with device icons overlaid | Floor plan upload exists, no device overlay |
| Device monitoring panel | Device list with status (name, type, color) | Not implemented |
| Floor-level alerts table | Alerts with replay, download, assignee | Not implemented |
| Alarms table (critical) | Risk level, severity, replay sound, download | Basic alerts page only |
| Noise warnings table | Peak level, background level, replay/download | Not implemented |
| Alert level history chart | Time-series chart (min, max, avg) | Not implemented |
| Building inventory with alert counts | Name, address, floors, active alerts | Building list exists, no alert counts |
| Administration contacts | Call/SMS/Email alerting per user | Users exist, no alerting preferences |

---

## 3. Goals & Success Metrics

### 3.1 Goals

1. **Provide real-time situational awareness** of sound threats within monitored buildings
2. **Enable rapid response** by auto-creating incidents from high-confidence audio events
3. **Support intervention planning** with device-on-floor-plan visualization showing exactly where threats are detected
4. **Maintain evidence chain** via audio clip recording, replay, and download
5. **Replace the ThingsBoard demo** with a fully native ERIOP experience that is richer and integrated with the existing incident/alert/resource workflow

### 3.2 Success Metrics

| Metric | Target |
|--------|--------|
| Alert processing latency (device event to UI) | < 2 seconds |
| Audio clip availability after event | < 5 seconds |
| Device status refresh rate | Every 30 seconds |
| System uptime for alert ingestion | 99.9% |
| Alert-to-incident auto-conversion accuracy | > 90% for gunshot/explosion at > 85% confidence |

---

## 4. Reference System Analysis

### 4.1 ThingsBoard Demo Feature Map

#### HOME Tab
- **Map View**: Buildings shown as pins (green = no alerts, red = active alerts) on a geographic map
- **Building Tree**: Left sidebar with hierarchical navigation: `My... > Building > Floor`
- **Floor Plan Viewer**: Interactive pan/zoom floor plan image with device icons overlaid at their physical locations
- **Device Icons**: Microphones (red icon when alert, green when OK), Cameras (blue icon)
- **Monitoring Panel**: Right sidebar listing devices with name, type, and status color
- **Floor Alerts**: Table at bottom with columns: Created time, Source, Type, Occurrence, Last occurrence, Severity, Replay, Download, Assignee

#### INVENTORY Tab
- **Buildings Table**: Name, Address, Floors number, Active alerts (count, red background when > 0)
- **CRUD Operations**: Add building via "+" button, edit via "..." menu

#### ALERTS Tab
- **Alarms Table**: Creation time, Source, Type, Occurrence, Last occurrence, Risk level, Severity, Replay sound, Download, Assignee
- **Noise Warnings Table**: Creation time, Source, Type, Peak Level, Background Level, Severity, Replay Sound, Download, Assignee
- **Alerts Level History Chart**: Time-series graph showing min/max/avg alert levels over a week

#### USERS Tab
- **Administration Contacts**: First name, Last name, Email, Phone, Call alerting (toggle), SMS alerting (toggle), Email alerting (toggle)
- **Warning Banner**: "For users to be alerted, be careful to allow alerts on the right buildings!"

---

## 5. Feature Requirements

### 5.1 IoT Device Management

| ID | Requirement | Priority |
|----|-------------|----------|
| DM-001 | System SHALL support CRUD operations for IoT devices (microphones, cameras) | Must |
| DM-002 | System SHALL store device metadata: name, type, serial number, IP address, model, firmware version | Must |
| DM-003 | System SHALL associate devices with a specific building and floor | Must |
| DM-004 | System SHALL track device status: online, offline, alert, maintenance | Must |
| DM-005 | System SHALL track device health: last seen, connection quality, battery (if applicable) | Should |
| DM-006 | System SHALL support device configuration (sensitivity thresholds per detection type) | Should |
| DM-007 | System SHALL support bulk device registration via CSV/JSON import | Could |
| DM-008 | System SHALL auto-discover Axis devices on the network | Could |

### 5.2 Device Placement on Floor Plans

| ID | Requirement | Priority |
|----|-------------|----------|
| DP-001 | System SHALL allow placing device icons on uploaded floor plan images | Must |
| DP-002 | System SHALL store device X/Y coordinates relative to the floor plan image | Must |
| DP-003 | System SHALL support drag-and-drop device placement in edit mode | Must |
| DP-004 | System SHALL display device icons with visual status indicators (green=OK, red=alert, gray=offline) | Must |
| DP-005 | System SHALL show device name labels on hover or always-on toggle | Must |
| DP-006 | System SHALL support pan/zoom on the floor plan viewer | Must |
| DP-007 | System SHALL distinguish device types visually (microphone icon, camera icon) | Must |
| DP-008 | System SHALL show a pulsing/animated indicator when a device has an active alert | Should |
| DP-009 | System SHALL support fullscreen floor plan view | Should |

### 5.3 Real-Time Sound Anomaly Alerts

| ID | Requirement | Priority |
|----|-------------|----------|
| SA-001 | System SHALL receive real-time audio events from Axis IP Microphones via the existing backend integration | Must |
| SA-002 | System SHALL classify audio events by type: gunshot, explosion, glass break, aggression, scream, car alarm | Must |
| SA-003 | System SHALL apply configurable confidence thresholds before creating alerts (per existing `alert_generator.py` thresholds) | Must |
| SA-004 | System SHALL create ERIOP alerts from audio events that exceed confidence thresholds | Must |
| SA-005 | System SHALL auto-create incidents for critical events (gunshot, explosion) exceeding auto-dispatch thresholds | Must |
| SA-006 | System SHALL push new alerts to connected web clients in real-time via WebSocket | Must |
| SA-007 | System SHALL display alert severity using color coding: critical=red, high=orange, medium=yellow, low=blue | Must |
| SA-008 | System SHALL include audio confidence percentage in alert details | Must |
| SA-009 | System SHALL deduplicate similar alerts from the same device within a configurable time window | Should |
| SA-010 | System SHALL support alert acknowledgment and assignment to personnel | Must |

### 5.4 Audio Replay & Evidence Management

| ID | Requirement | Priority |
|----|-------------|----------|
| AR-001 | System SHALL store audio clips captured around detection events | Must |
| AR-002 | System SHALL provide in-browser audio playback (replay) for each alert | Must |
| AR-003 | System SHALL support audio clip download as WAV files | Must |
| AR-004 | System SHALL retrieve audio clips from Axis devices via the existing `get_audio_clip()` method | Must |
| AR-005 | System SHALL store audio clips with metadata: device ID, timestamp, duration, event type | Must |
| AR-006 | System SHALL enforce access control on audio clip access (authorized personnel only) | Must |
| AR-007 | System SHALL retain audio clips for a configurable period (default: 90 days) | Should |

### 5.5 Building-Level Device Monitoring

| ID | Requirement | Priority |
|----|-------------|----------|
| BM-001 | System SHALL display a monitoring panel showing all devices on a given floor | Must |
| BM-002 | System SHALL show device status with color coding (green=OK, red=alert, gray=offline) | Must |
| BM-003 | System SHALL update device status in real-time (polling interval configurable, default 30s) | Must |
| BM-004 | System SHALL show active alert count per building on the Buildings list page | Must |
| BM-005 | System SHALL show active alert count per building on the Map page with colored pins | Must |
| BM-006 | System SHALL support filtering alerts by floor, device, type, and severity | Must |
| BM-007 | System SHALL provide a building tree view for hierarchical navigation (Building > Floor > Device) | Should |

### 5.6 Alert History & Analytics

| ID | Requirement | Priority |
|----|-------------|----------|
| AH-001 | System SHALL display an alert history table with: timestamp, source device, type, occurrence count, severity, replay, download, assignee | Must |
| AH-002 | System SHALL distinguish between critical alarms and noise warnings in separate views | Should |
| AH-003 | System SHALL display an alert level history time-series chart (min, max, avg over time) | Should |
| AH-004 | System SHALL support filtering alert history by date range, building, floor, device, type | Must |
| AH-005 | System SHALL display peak and background sound levels for noise warnings | Should |
| AH-006 | System SHALL integrate alert analytics into the existing Analytics page | Should |

### 5.7 Notification Contact Management

| ID | Requirement | Priority |
|----|-------------|----------|
| NC-001 | System SHALL allow configuring notification preferences per user: call, SMS, email alerting toggles | Must |
| NC-002 | System SHALL allow associating users with specific buildings for targeted alerting | Must |
| NC-003 | System SHALL send notifications via configured channels when critical alerts are created | Must |
| NC-004 | System SHALL display a warning when users have alerting enabled but no buildings assigned | Should |
| NC-005 | System SHALL log all notification delivery attempts and outcomes | Must |

---

## 6. Technical Architecture

### 6.1 Backend Components

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     Sound Anomaly Detection Pipeline                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   Axis IP Microphones                                                   │
│         │                                                                │
│         ▼                                                                │
│   ┌──────────────────┐     ┌──────────────────┐                        │
│   │  AxisDeviceClient │────▶│AxisEventSubscriber│                       │
│   │  (VAPIX API)      │     │ (HTTP long-poll)  │                       │
│   │  [EXISTING]       │     │ [EXISTING]        │                       │
│   └──────────────────┘     └────────┬─────────┘                        │
│                                      │                                   │
│                                      ▼                                   │
│                            ┌──────────────────┐                         │
│                            │AudioAlertGenerator│                        │
│                            │ [EXISTING]        │                        │
│                            └────────┬─────────┘                         │
│                                      │                                   │
│                    ┌─────────────────┼─────────────────┐                │
│                    ▼                 ▼                  ▼                │
│            ┌─────────────┐  ┌──────────────┐  ┌──────────────┐         │
│            │Alert Service│  │Audio Storage  │  │Notification  │         │
│            │ [EXISTING]  │  │ [NEW]         │  │Service [NEW] │         │
│            └──────┬──────┘  └──────────────┘  └──────────────┘         │
│                   │                                                      │
│                   ▼                                                      │
│           ┌──────────────┐                                              │
│           │WebSocket Push│                                              │
│           │ [NEW]        │                                              │
│           └──────────────┘                                              │
│                   │                                                      │
│                   ▼                                                      │
│           Connected Web/Mobile Clients                                  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 6.2 Key Backend Services

| Service | Status | Description |
|---------|--------|-------------|
| `AxisDeviceClient` | Existing | VAPIX API communication, audio clip retrieval |
| `AxisEventSubscriber` | Existing | Real-time event polling from Axis devices |
| `AudioAlertGenerator` | Existing | Event-to-alert conversion with thresholds |
| `DeviceService` | **New** | IoT device CRUD, status tracking, floor placement |
| `AudioStorageService` | **New** | Audio clip storage, retrieval, retention |
| `NotificationService` | **New** | Multi-channel notification delivery (call, SMS, email) |
| `DeviceMonitorService` | **New** | Device health monitoring, status polling |
| WebSocket broadcast | **New** | Real-time alert push to frontend clients |

### 6.3 Frontend Architecture

Built on the existing **React + TypeScript + Vite** stack with **Zustand** state management.

| Component | Status | Description |
|-----------|--------|-------------|
| `InteractiveFloorPlan` | **New** | Pan/zoom floor plan with device icon overlay |
| `DevicePlacementEditor` | **New** | Drag-and-drop device placement on floor plans |
| `DeviceMonitoringPanel` | **New** | Right sidebar showing device list with status |
| `AlertsFloorTable` | **New** | Floor-level alert table with replay/download |
| `AudioPlayer` | **New** | Inline audio clip playback component |
| `AlertHistoryChart` | **New** | Time-series chart for alert trends |
| `BuildingTreeNav` | **New** | Hierarchical building/floor tree navigation |
| `NotificationPreferences` | **New** | User alerting preferences (call/SMS/email) |
| `DeviceManagementPage` | **New** | Full device CRUD page |
| Enhanced `BuildingsPage` | Modified | Add alert counts, tree navigation |
| Enhanced `AlertsPage` | Modified | Add alarms vs noise warnings split, replay/download |
| Enhanced `MapPage` | Modified | Building pins with alert status coloring |
| Enhanced `DashboardPage` | Modified | Add device status widget, recent sound alerts |
| `deviceStore` | **New** | Zustand store for device state |
| `audioStore` | **New** | Zustand store for audio clips |

---

## 7. Data Model Changes

### 7.1 New Tables

#### `iot_devices`
```sql
CREATE TABLE iot_devices (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(200) NOT NULL,
    device_type     VARCHAR(50) NOT NULL,  -- 'microphone', 'camera', 'sensor'
    serial_number   VARCHAR(100) UNIQUE,
    ip_address      VARCHAR(45),
    mac_address     VARCHAR(17),
    model           VARCHAR(100),
    firmware_version VARCHAR(50),
    manufacturer    VARCHAR(100) DEFAULT 'Axis',

    -- Association
    building_id     UUID NOT NULL REFERENCES buildings(id) ON DELETE CASCADE,
    floor_plan_id   UUID REFERENCES floor_plans(id) ON DELETE SET NULL,

    -- Position on floor plan (percentage-based, 0-100)
    position_x      FLOAT,  -- X position as % of floor plan width
    position_y      FLOAT,  -- Y position as % of floor plan height

    -- Physical location
    latitude        FLOAT,
    longitude       FLOAT,
    location_name   VARCHAR(200),  -- e.g., "Room 428", "Hallway B"

    -- Status
    status          VARCHAR(30) NOT NULL DEFAULT 'offline',
    -- Values: 'online', 'offline', 'alert', 'maintenance', 'error'
    last_seen       TIMESTAMP WITH TIME ZONE,
    connection_quality INTEGER,  -- 0-100

    -- Configuration
    config          JSON DEFAULT '{}',
    -- For microphones: {"gunshot_enabled": true, "gunshot_sensitivity": 50, ...}

    -- Detection capabilities
    capabilities    VARCHAR(50)[] DEFAULT '{}',
    -- e.g., ['audio_analytics', 'gunshot', 'glass_break', 'aggression']

    -- Metadata
    metadata        JSON DEFAULT '{}',
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMP WITH TIME ZONE,

    CONSTRAINT device_type_check CHECK (device_type IN (
        'microphone', 'camera', 'sensor', 'gateway', 'other'
    )),
    CONSTRAINT device_status_check CHECK (status IN (
        'online', 'offline', 'alert', 'maintenance', 'error'
    ))
);

CREATE INDEX idx_devices_building ON iot_devices(building_id);
CREATE INDEX idx_devices_floor ON iot_devices(floor_plan_id);
CREATE INDEX idx_devices_status ON iot_devices(status);
CREATE INDEX idx_devices_type ON iot_devices(device_type);
CREATE INDEX idx_devices_serial ON iot_devices(serial_number);
```

#### `audio_clips`
```sql
CREATE TABLE audio_clips (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_id        UUID REFERENCES alerts(id) ON DELETE SET NULL,
    device_id       UUID NOT NULL REFERENCES iot_devices(id) ON DELETE CASCADE,

    -- Audio data
    file_path       VARCHAR(500) NOT NULL,  -- Storage path
    file_size_bytes INTEGER,
    duration_seconds FLOAT,
    format          VARCHAR(20) DEFAULT 'wav',
    sample_rate     INTEGER DEFAULT 16000,

    -- Event context
    event_type      VARCHAR(50) NOT NULL,  -- 'gunshot', 'glass_break', etc.
    confidence      FLOAT,
    peak_level_db   FLOAT,
    background_level_db FLOAT,

    -- Timestamps
    event_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    captured_at     TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    expires_at      TIMESTAMP WITH TIME ZONE,  -- For retention policy

    metadata        JSON DEFAULT '{}'
);

CREATE INDEX idx_audio_clips_alert ON audio_clips(alert_id);
CREATE INDEX idx_audio_clips_device ON audio_clips(device_id);
CREATE INDEX idx_audio_clips_event ON audio_clips(event_timestamp DESC);
CREATE INDEX idx_audio_clips_type ON audio_clips(event_type);
```

#### `notification_preferences`
```sql
CREATE TABLE notification_preferences (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Channels
    call_enabled    BOOLEAN DEFAULT FALSE,
    sms_enabled     BOOLEAN DEFAULT FALSE,
    email_enabled   BOOLEAN DEFAULT FALSE,
    push_enabled    BOOLEAN DEFAULT TRUE,

    -- Scope: which buildings to receive alerts for
    building_ids    UUID[] DEFAULT '{}',
    -- Empty means all buildings

    -- Severity filter
    min_severity    INTEGER DEFAULT 1,  -- 1=critical only, 5=all

    -- Quiet hours
    quiet_start     TIME,
    quiet_end       TIME,
    quiet_override_critical BOOLEAN DEFAULT TRUE,

    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

    CONSTRAINT unique_user_prefs UNIQUE(user_id)
);

CREATE INDEX idx_notif_prefs_user ON notification_preferences(user_id);
```

### 7.2 Modified Tables

#### `alerts` - Add columns
```sql
ALTER TABLE alerts ADD COLUMN device_id UUID REFERENCES iot_devices(id);
ALTER TABLE alerts ADD COLUMN building_id UUID REFERENCES buildings(id);
ALTER TABLE alerts ADD COLUMN floor_plan_id UUID REFERENCES floor_plans(id);
ALTER TABLE alerts ADD COLUMN audio_clip_id UUID REFERENCES audio_clips(id);
ALTER TABLE alerts ADD COLUMN peak_level_db FLOAT;
ALTER TABLE alerts ADD COLUMN background_level_db FLOAT;
ALTER TABLE alerts ADD COLUMN risk_level VARCHAR(20);
-- Values: 'critical', 'high', 'elevated', 'guarded', 'low'
ALTER TABLE alerts ADD COLUMN occurrence_count INTEGER DEFAULT 1;
ALTER TABLE alerts ADD COLUMN last_occurrence TIMESTAMP WITH TIME ZONE;
ALTER TABLE alerts ADD COLUMN assigned_to UUID REFERENCES users(id);
```

### 7.3 Alembic Migration

A new migration `003_add_iot_devices_and_audio.py` will be created to add these tables and columns.

---

## 8. API Endpoints

### 8.1 IoT Device Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/devices` | List devices (filter by building, floor, type, status) |
| `GET` | `/api/v1/devices/{id}` | Get device details |
| `POST` | `/api/v1/devices` | Register new device |
| `PATCH` | `/api/v1/devices/{id}` | Update device info |
| `DELETE` | `/api/v1/devices/{id}` | Remove device (soft delete) |
| `PATCH` | `/api/v1/devices/{id}/position` | Update device position on floor plan |
| `PATCH` | `/api/v1/devices/{id}/config` | Update device detection configuration |
| `GET` | `/api/v1/devices/{id}/status` | Get real-time device status |
| `GET` | `/api/v1/devices/{id}/health` | Get device health details |
| `GET` | `/api/v1/buildings/{id}/devices` | List all devices in a building |
| `GET` | `/api/v1/floor-plans/{id}/devices` | List all devices on a floor |

### 8.2 Audio Clips

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/audio-clips` | List audio clips (filter by device, alert, date) |
| `GET` | `/api/v1/audio-clips/{id}` | Get audio clip metadata |
| `GET` | `/api/v1/audio-clips/{id}/stream` | Stream audio for replay |
| `GET` | `/api/v1/audio-clips/{id}/download` | Download audio file |
| `GET` | `/api/v1/alerts/{id}/audio` | Get audio clip for a specific alert |

### 8.3 Enhanced Alerts

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/alerts/sound-anomalies` | List sound anomaly alerts specifically |
| `GET` | `/api/v1/alerts/alarms` | List critical alarms (high risk level) |
| `GET` | `/api/v1/alerts/noise-warnings` | List noise warning alerts |
| `GET` | `/api/v1/buildings/{id}/alerts` | List alerts for a building |
| `GET` | `/api/v1/floor-plans/{id}/alerts` | List alerts for a specific floor |
| `GET` | `/api/v1/alerts/history/chart` | Alert level history data for charting |
| `POST` | `/api/v1/alerts/{id}/assign` | Assign alert to a user |

### 8.4 Notification Preferences

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/users/{id}/notification-preferences` | Get user notification prefs |
| `PUT` | `/api/v1/users/{id}/notification-preferences` | Update notification prefs |
| `GET` | `/api/v1/buildings/{id}/notification-contacts` | List users alerted for building |

### 8.5 Real-Time (WebSocket)

| Channel | Event | Payload |
|---------|-------|---------|
| `ws://alerts` | `new_alert` | Full alert object with device and building context |
| `ws://alerts` | `alert_updated` | Updated alert (acknowledged, assigned, resolved) |
| `ws://devices` | `device_status` | Device ID, new status, timestamp |
| `ws://devices` | `device_alert` | Device in alert state with event details |

---

## 9. Frontend Components

### 9.1 New Pages

#### Device Management Page (`/devices`)
- Device list table with sortable columns: name, type, building, floor, status, last seen
- Filters: building, floor, type, status
- CRUD dialogs for add/edit/remove
- Bulk actions: register multiple devices

#### Building Detail View (Enhanced `/buildings/{id}`)
- **Tab: Building Info** (existing)
- **Tab: Floor Plans** (existing) - Enhanced with device overlay
- **Tab: Devices** (new) - List of devices in this building
- **Tab: Alerts** (new) - Building-specific alerts with floor drill-down
- **Tab: Upload Plan** (existing)

### 9.2 Key UI Components

#### Interactive Floor Plan Viewer
- Renders uploaded floor plan image as base layer
- Overlays device icons at their stored X/Y positions
- Device icons change color based on status (green/red/gray)
- Microphone icon for audio devices, camera icon for cameras
- Click device to see details popup (name, status, last event)
- Pan and zoom controls (mouse wheel + drag)
- Fullscreen toggle

#### Device Placement Editor (Admin)
- Extends Floor Plan Viewer with edit mode
- Drag-and-drop device placement
- Snap-to-grid option
- Device palette sidebar (available unplaced devices)
- Save/cancel buttons

#### Alert Table with Audio Controls
- Columns: Created time, Source (device name), Type, Occurrence, Last occurrence, Severity, Replay, Download, Assignee
- Replay button: opens inline audio player
- Download button: triggers WAV file download
- Severity badges with color coding
- Assignee dropdown

#### Device Monitoring Sidebar
- Compact list of devices on current floor
- Each row: device name, type icon, status indicator dot
- Red background for devices in alert state
- Click to center floor plan on device

#### Alert History Chart
- Recharts time-series line chart
- Shows alert count over time (daily/weekly)
- Filterable by building, floor, type
- Min/max/avg trend lines

---

## 10. Implementation Phases

### Phase A: IoT Device Data Model & Backend (Foundation)

**Scope:** Database schema, models, services, and API endpoints for device management.

**Tasks:**
1. Create Alembic migration `003_add_iot_devices_and_audio.py` with new tables
2. Create SQLAlchemy model `IoTDevice` in `app/models/device.py`
3. Create SQLAlchemy model `AudioClip` in `app/models/audio_clip.py`
4. Create SQLAlchemy model `NotificationPreference` in `app/models/notification_preference.py`
5. Add new columns to `Alert` model (device_id, building_id, audio_clip_id, etc.)
6. Create `DeviceService` in `app/services/device_service.py` (CRUD + status)
7. Create `AudioStorageService` in `app/services/audio_storage_service.py`
8. Create device API routes in `app/api/devices.py`
9. Create audio clip API routes in `app/api/audio_clips.py`
10. Write unit tests for all new services and endpoints

**Acceptance Criteria:**
- [ ] All new database tables created and migration runs without errors
- [ ] Device CRUD API returns correct responses (201, 200, 204)
- [ ] Device can be associated with building and floor plan
- [ ] Device position (X/Y) can be stored and retrieved
- [ ] Audio clips can be stored and streamed back
- [ ] Alert model has new columns for device/building/audio references
- [ ] Unit tests pass with > 90% coverage on new code
- [ ] API documentation (OpenAPI/Swagger) reflects all new endpoints

### Phase B: Alert Pipeline Integration (Connect Axis to ERIOP)

**Scope:** Wire the existing Axis integration to the alert service and add WebSocket push.

**Tasks:**
1. Create startup task that initializes `AxisEventSubscriber` with configured devices
2. Wire `AudioAlertGenerator` to `AlertService` for persistent alert creation
3. Wire `AudioAlertGenerator` to `AudioStorageService` for clip capture
4. Add device_id and building_id population to alert creation flow
5. Implement WebSocket endpoint for real-time alert broadcasting
6. Add WebSocket broadcast to alert creation pipeline
7. Implement device status polling service
8. Add occurrence count increment for repeated alerts from same device
9. Write integration tests for the full pipeline (event -> alert -> WebSocket)

**Acceptance Criteria:**
- [ ] Axis audio event creates an alert in the database within 2 seconds
- [ ] Audio clip is captured and stored for each alert event
- [ ] Alert is broadcast to connected WebSocket clients in real-time
- [ ] Auto-incident creation triggers for gunshot/explosion at > 85% confidence
- [ ] Device status updates are polled and stored every 30 seconds
- [ ] Occurrence count increments for repeat alerts from same device
- [ ] Alert has correct building_id and device_id references
- [ ] Integration test demonstrates end-to-end pipeline

### Phase C: Frontend - Device Management & Floor Plan Overlay

**Scope:** React components for device management and interactive floor plan viewer.

**Tasks:**
1. Create `deviceStore` Zustand store
2. Create `DeviceManagementPage` with CRUD table
3. Create `InteractiveFloorPlan` component (pan/zoom with device overlay)
4. Create `DevicePlacementEditor` component (drag-and-drop)
5. Create `DeviceMonitoringPanel` sidebar component
6. Enhance `BuildingsPage` to show alert counts per building
7. Enhance Building detail modal to add Devices and Alerts tabs
8. Add device API client methods to `api.ts`
9. Write frontend unit tests for new components

**Acceptance Criteria:**
- [ ] Device list page shows all registered devices with filters
- [ ] Device can be created, edited, and deleted via the UI
- [ ] Floor plan viewer renders with device icons at correct positions
- [ ] Device icons change color based on device status
- [ ] Device placement editor allows drag-and-drop positioning
- [ ] Device positions persist after save and reload
- [ ] Monitoring panel shows all devices on current floor
- [ ] Building cards show active alert count with red indicator
- [ ] All new components have unit tests

### Phase D: Frontend - Sound Alerts & Audio Playback

**Scope:** Real-time alert visualization, audio replay, and alert history.

**Tasks:**
1. Create `audioStore` Zustand store
2. Implement WebSocket client connection for real-time alerts
3. Create `AlertsFloorTable` component with replay/download columns
4. Create `AudioPlayer` component (inline playback)
5. Create alert download functionality
6. Enhance `AlertsPage` with Alarms vs Noise Warnings split view
7. Enhance `AlertsPage` with sound anomaly specific fields (peak/background level)
8. Create `AlertHistoryChart` component using Recharts
9. Add alert-on-floor-plan highlighting (pulse animation on alerting device)
10. Enhance `MapPage` to show building pins with alert status color
11. Enhance `DashboardPage` to show recent sound alerts widget and device status summary
12. Write frontend unit tests

**Acceptance Criteria:**
- [ ] New alerts appear in the UI in real-time without page refresh
- [ ] Alert table shows replay button that plays audio in-browser
- [ ] Alert table shows download button that downloads WAV file
- [ ] Alert device icon pulses red on floor plan during active alert
- [ ] Alerts page has separate Alarms and Noise Warnings views
- [ ] Alert history chart displays correctly with date range filtering
- [ ] Map shows buildings with red pins when they have active alerts
- [ ] Dashboard shows recent sound alerts and device status counts
- [ ] All components have unit tests

### Phase E: Notification System & User Preferences

**Scope:** Multi-channel notification delivery and user preference management.

**Tasks:**
1. Create `NotificationService` in `app/services/notification_service.py`
2. Implement email notification delivery (SMTP or SendGrid)
3. Implement SMS notification delivery (Twilio or similar)
4. Implement phone call notification (Twilio voice)
5. Create notification preferences API endpoints
6. Create `NotificationPreferences` frontend component
7. Enhance Users page to show notification alerting toggles
8. Add building assignment to notification preferences
9. Wire notification service to alert creation pipeline
10. Create notification delivery logs and audit trail
11. Write unit and integration tests

**Acceptance Criteria:**
- [ ] Users can configure call/SMS/email alerting preferences
- [ ] Users can select which buildings to receive alerts for
- [ ] Critical alerts trigger notifications via configured channels
- [ ] Notification delivery is logged with delivery status
- [ ] Quiet hours are respected (except critical alerts if override enabled)
- [ ] Warning displayed when user has alerting enabled but no buildings assigned
- [ ] All notification services have unit tests
- [ ] Email, SMS, and call delivery works end-to-end (integration test)

---

## 11. Acceptance Criteria (Overall Feature)

### 11.1 Functional Acceptance

| # | Criterion | Verification |
|---|-----------|-------------|
| 1 | Admin can register a new Axis microphone device and associate it with a building/floor | Manual test |
| 2 | Admin can place a device on a floor plan via drag-and-drop and save the position | Manual test |
| 3 | Floor plan viewer shows all placed devices with correct status colors | Manual test |
| 4 | When an Axis microphone detects a gunshot, an alert appears in ERIOP within 2 seconds | Integration test |
| 5 | The alert includes the audio clip which can be replayed in the browser | Manual test |
| 6 | The audio clip can be downloaded as a WAV file | Manual test |
| 7 | A critical alert (gunshot at >85% confidence) auto-creates an incident | Integration test |
| 8 | The building map shows a red pin for buildings with active alerts | Manual test |
| 9 | The building detail shows active alert count and per-floor alert tables | Manual test |
| 10 | Users with notification preferences configured receive alerts via their chosen channels | Integration test |
| 11 | Alert history chart shows trends over the past 7 days | Manual test |
| 12 | All existing ERIOP features (incidents, resources, users, roles) continue to work | Regression test |

### 11.2 Non-Functional Acceptance

| # | Criterion | Target |
|---|-----------|--------|
| 1 | Alert processing latency (device event to database) | < 500ms |
| 2 | Alert UI update latency (database to browser) | < 2s total |
| 3 | Audio clip retrieval time | < 5s |
| 4 | Concurrent WebSocket connections supported | 100+ |
| 5 | Device status polling does not exceed 5% CPU on backend | Monitoring |
| 6 | Audio clip storage does not exceed 100MB per device per month | Calculated |
| 7 | All new API endpoints respond within 200ms (p95) | Load test |
| 8 | Zero security vulnerabilities in new audio endpoints | Security scan |

---

## 12. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Axis devices not accessible from ERIOP server network | Medium | High | Support MQTT bridge via Fundamentum as alternative transport; test network connectivity early |
| Audio clip storage grows rapidly | Medium | Medium | Implement retention policy (90-day default), compress WAV to OPUS, configurable limits |
| WebSocket connections drop under network instability | Medium | Medium | Implement reconnection with exponential backoff, offline queue for missed alerts |
| False positive gunshot detections cause alert fatigue | Medium | High | Configurable confidence thresholds (currently 70% for alert, 85% for auto-dispatch); allow per-device tuning |
| Third-party notification APIs (Twilio) have outages | Low | Medium | Implement fallback channels, retry logic, circuit breaker pattern (already in codebase) |
| Floor plan coordinate system differs across image sizes | Medium | Low | Store positions as percentages (0-100) not pixels; re-calculate on render |
| Performance degradation with many concurrent alerts | Low | High | Batch WebSocket messages, debounce UI updates, paginate alert tables |

---

## 13. Related Documents

| Document | Path | Relevance |
|----------|------|-----------|
| System Architecture | `docs/architecture/SYSTEM_ARCHITECTURE.md` | Overall system design, service architecture |
| Database Design | `docs/architecture/DATABASE_DESIGN.md` | Existing schema, telemetry table (TimescaleDB) |
| API Design | `docs/architecture/API_DESIGN.md` | REST API conventions, auth patterns |
| Functional Requirements | `docs/requirements/FUNCTIONAL_REQUIREMENTS.md` | Alert Management (AM-001 to AM-016), especially AM-003 (Axis IP Microphones) |
| Security Requirements | `docs/requirements/SECURITY_REQUIREMENTS.md` | Data encryption, access control for audio |
| Phase 3: Integrations | `docs/phases/PHASE_03_INTEGRATIONS.md` | Axis integration implementation details |
| Axis Client Code | `src/backend/app/integrations/axis/client.py` | Existing VAPIX client with audio clip retrieval |
| Axis Events Code | `src/backend/app/integrations/axis/events.py` | Event types, subscriber, mock generator |
| Alert Generator Code | `src/backend/app/integrations/axis/alert_generator.py` | Threshold config, severity mapping |
| Building Model | `src/backend/app/models/building.py` | Building + FloorPlan models with key_locations |
| Alert Service | `src/backend/app/services/alert_service.py` | Existing alert ingestion pipeline |
| CLAUDE.md | `CLAUDE.md` | Full project context, tech stack, API endpoints |

---

*Document Version: 1.0 | Last Updated: January 27, 2026 | Classification: Confidential*
