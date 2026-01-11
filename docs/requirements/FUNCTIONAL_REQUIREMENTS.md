# Functional Requirements

This document specifies the functional requirements for ERIOP.

## Table of Contents

1. [User Management](#1-user-management)
2. [Incident Management](#2-incident-management)
3. [Resource Tracking](#3-resource-tracking)
4. [Alert Management](#4-alert-management)
5. [Communication](#5-communication)
6. [Mapping and GIS](#6-mapping-and-gis)
7. [Reporting and Analytics](#7-reporting-and-analytics)
8. [Public Portal](#8-public-portal)
9. [Offline Operations](#9-offline-operations)
10. [External Integrations](#10-external-integrations)

---

## 1. User Management

### 1.1 Authentication

| ID | Requirement | Priority |
|----|-------------|----------|
| UM-001 | System SHALL support OAuth 2.0 / OIDC authentication | Must |
| UM-002 | System SHALL require MFA for command and admin users | Must |
| UM-003 | System SHALL enforce password complexity (min 12 chars, mixed) | Must |
| UM-004 | System SHALL lock accounts after 5 failed login attempts | Must |
| UM-005 | System SHALL support SSO integration for agencies | Should |
| UM-006 | System SHALL provide password reset via email/SMS | Must |
| UM-007 | System SHALL log all authentication events | Must |

### 1.2 Authorization

| ID | Requirement | Priority |
|----|-------------|----------|
| UM-010 | System SHALL implement Role-Based Access Control (RBAC) | Must |
| UM-011 | System SHALL support agency-level data isolation | Must |
| UM-012 | System SHALL allow fine-grained permission assignment | Must |
| UM-013 | System SHALL support temporary elevated permissions | Should |
| UM-014 | System SHALL log all authorization decisions | Must |

### 1.3 User Roles

| Role | Description | Access Level |
|------|-------------|--------------|
| System Admin | Platform administration | Full system |
| Agency Admin | Agency configuration and user management | Agency scope |
| Commander | Strategic overview, all agency data | Agency + subordinates |
| Dispatcher | Resource allocation, incident management | Assigned areas |
| Field Unit Leader | Team management, tactical decisions | Team scope |
| Responder | Field operations | Own assignments |
| Public User | Limited public information | Public data only |

---

## 2. Incident Management

### 2.1 Incident Lifecycle

| ID | Requirement | Priority |
|----|-------------|----------|
| IM-001 | System SHALL allow creation of incidents from alerts, manual entry, or external systems | Must |
| IM-002 | System SHALL assign unique incident numbers following agency format | Must |
| IM-003 | System SHALL support incident states: New, Assigned, En Route, On Scene, Resolved, Closed | Must |
| IM-004 | System SHALL capture incident location (GPS + address) | Must |
| IM-005 | System SHALL support incident categorization and typing | Must |
| IM-006 | System SHALL support priority levels 1-5 (1=Critical) | Must |
| IM-007 | System SHALL maintain complete timeline of all incident events | Must |
| IM-008 | System SHALL support incident linking (parent/child) | Should |
| IM-009 | System SHALL support incident merging | Should |
| IM-010 | System SHALL prevent unauthorized incident modification | Must |

### 2.2 Incident Types

The system SHALL support the following incident categories (expandable):

- **Emergency Services:** Fire, Medical, Police, Rescue
- **Public Safety:** Traffic, Weather, Hazmat, Utility
- **Security:** Intrusion, Assault, Theft, Threat
- **Administrative:** Welfare Check, Civil Assistance, Training

### 2.3 Assignment and Dispatch

| ID | Requirement | Priority |
|----|-------------|----------|
| IM-020 | System SHALL allow assignment of units to incidents | Must |
| IM-021 | System SHALL track unit response times | Must |
| IM-022 | System SHALL support automatic unit recommendation based on proximity and capabilities | Should |
| IM-023 | System SHALL support escalation workflows | Must |
| IM-024 | System SHALL notify assigned units in real-time | Must |
| IM-025 | System SHALL allow reassignment of units | Must |
| IM-026 | System SHALL track all assignment changes with reason | Must |

---

## 3. Resource Tracking

### 3.1 Personnel

| ID | Requirement | Priority |
|----|-------------|----------|
| RT-001 | System SHALL track personnel status (Available, Assigned, Off Duty) | Must |
| RT-002 | System SHALL track personnel location via GPS (with consent) | Must |
| RT-003 | System SHALL maintain personnel qualifications and certifications | Should |
| RT-004 | System SHALL track shift schedules | Should |
| RT-005 | System SHALL support status self-reporting from field | Must |

### 3.2 Vehicles

| ID | Requirement | Priority |
|----|-------------|----------|
| RT-010 | System SHALL track vehicle location in real-time | Must |
| RT-011 | System SHALL track vehicle status (Available, En Route, On Scene) | Must |
| RT-012 | System SHALL maintain vehicle equipment inventory | Should |
| RT-013 | System SHALL track vehicle maintenance schedules | Could |
| RT-014 | System SHALL support vehicle assignment to units | Must |

### 3.3 Equipment

| ID | Requirement | Priority |
|----|-------------|----------|
| RT-020 | System SHALL maintain equipment inventory | Should |
| RT-021 | System SHALL track equipment assignment to personnel/vehicles | Should |
| RT-022 | System SHALL support equipment check-out/check-in | Could |
| RT-023 | System SHALL track equipment maintenance | Could |

---

## 4. Alert Management

### 4.1 Alert Ingestion

| ID | Requirement | Priority |
|----|-------------|----------|
| AM-001 | System SHALL receive alerts from Fundamentum-connected devices | Must |
| AM-002 | System SHALL receive alerts from alarm systems via adapter | Must |
| AM-003 | System SHALL receive alerts from Axis IP Microphones (sound analysis) | Must |
| AM-004 | System SHALL normalize alerts to common format | Must |
| AM-005 | System SHALL deduplicate similar alerts within time window | Should |
| AM-006 | System SHALL store original alert payload for audit | Must |

### 4.2 Alert Processing

| ID | Requirement | Priority |
|----|-------------|----------|
| AM-010 | System SHALL classify alerts by type and severity | Must |
| AM-011 | System SHALL apply routing rules based on alert type and location | Must |
| AM-012 | System SHALL automatically create incidents for high-severity alerts | Should |
| AM-013 | System SHALL notify relevant personnel based on routing rules | Must |
| AM-014 | System SHALL process alerts within 500ms | Must |
| AM-015 | System SHALL support manual alert acknowledgment | Must |
| AM-016 | System SHALL support alert dismissal with reason | Must |

### 4.3 Alert Sources

| Source | Protocol | Direction |
|--------|----------|-----------|
| Fundamentum IoT Devices | MQTT | Inbound |
| Axis IP Microphones | MQTT/REST | Inbound |
| Alarm Systems | Various (adapted) | Inbound |
| Security Systems | REST/Webhooks | Bidirectional |
| Manual Entry | REST API | Inbound |

---

## 5. Communication

### 5.1 Messaging

| ID | Requirement | Priority |
|----|-------------|----------|
| CM-001 | System SHALL provide secure messaging between users | Must |
| CM-002 | System SHALL support incident-specific channels | Must |
| CM-003 | System SHALL support team/unit channels | Must |
| CM-004 | System SHALL support agency-wide broadcasts | Must |
| CM-005 | System SHALL persist all messages with timestamps | Must |
| CM-006 | System SHALL support message priority levels | Should |
| CM-007 | System SHALL support file attachments | Should |
| CM-008 | System SHALL support location sharing in messages | Should |

### 5.2 Notifications

| ID | Requirement | Priority |
|----|-------------|----------|
| CM-010 | System SHALL deliver push notifications to mobile apps | Must |
| CM-011 | System SHALL deliver real-time updates to web clients | Must |
| CM-012 | System SHALL support notification preferences per user | Should |
| CM-013 | System SHALL support quiet hours configuration | Could |
| CM-014 | System SHALL log all notification delivery attempts | Must |

---

## 6. Mapping and GIS

### 6.1 Map Display

| ID | Requirement | Priority |
|----|-------------|----------|
| GIS-001 | System SHALL display incidents on map | Must |
| GIS-002 | System SHALL display resource locations on map | Must |
| GIS-003 | System SHALL support multiple map layers | Should |
| GIS-004 | System SHALL support map clustering for dense areas | Should |
| GIS-005 | System SHALL display real-time location updates | Must |
| GIS-006 | System SHALL support address search and geocoding | Must |

### 6.2 Geospatial Features

| ID | Requirement | Priority |
|----|-------------|----------|
| GIS-010 | System SHALL support proximity-based resource search | Must |
| GIS-011 | System SHALL calculate estimated travel times | Should |
| GIS-012 | System SHALL support geofencing for alerts | Should |
| GIS-013 | System SHALL display building footprints where available | Could |
| GIS-014 | System SHALL display hydrant locations (fire service) | Should |

---

## 7. Reporting and Analytics

### 7.1 Operational Reports

| ID | Requirement | Priority |
|----|-------------|----------|
| RP-001 | System SHALL generate incident summary reports | Must |
| RP-002 | System SHALL generate response time reports | Must |
| RP-003 | System SHALL generate resource utilization reports | Should |
| RP-004 | System SHALL support custom date range filtering | Must |
| RP-005 | System SHALL export reports in PDF and CSV formats | Must |

### 7.2 Analytics Dashboard

| ID | Requirement | Priority |
|----|-------------|----------|
| RP-010 | System SHALL display real-time incident counts by status | Must |
| RP-011 | System SHALL display resource availability summary | Must |
| RP-012 | System SHALL display response time trends | Should |
| RP-013 | System SHALL display incident heat maps | Should |
| RP-014 | System SHALL support dashboard customization | Could |

---

## 8. Public Portal

### 8.1 Public Features

| ID | Requirement | Priority |
|----|-------------|----------|
| PP-001 | System SHALL display public emergency alerts | Must |
| PP-002 | System SHALL display general safety information | Should |
| PP-003 | System SHALL display non-sensitive incident status | Should |
| PP-004 | System SHALL NOT expose confidential information | Must |
| PP-005 | System SHALL support accessibility (WCAG 2.1 AA) | Must |

---

## 9. Offline Operations

### 9.1 Offline Capability

| ID | Requirement | Priority |
|----|-------------|----------|
| OF-001 | Mobile app SHALL function without network connectivity | Must |
| OF-002 | System SHALL sync local data when connectivity is restored | Must |
| OF-003 | System SHALL cache critical reference data locally | Must |
| OF-004 | System SHALL queue actions taken offline for later sync | Must |
| OF-005 | System SHALL resolve sync conflicts using defined rules | Must |
| OF-006 | System SHALL indicate sync status to user | Must |

### 9.2 Edge Computing

| ID | Requirement | Priority |
|----|-------------|----------|
| OF-010 | Local gateways SHALL process alerts independently | Should |
| OF-011 | Local gateways SHALL cache recent incident data | Should |
| OF-012 | Local gateways SHALL maintain local decision capability | Should |

---

## 10. External Integrations

### 10.1 Required Integrations

| ID | System | Direction | Priority |
|----|--------|-----------|----------|
| EI-001 | Fundamentum IoT Platform | Bidirectional | Must |
| EI-002 | Alarm Systems (various) | Inbound | Must |
| EI-003 | Axis IP Microphones | Inbound | Must |
| EI-004 | Security Camera Systems | Metadata only | Should |
| EI-005 | CAD Systems | Bidirectional | Should |
| EI-006 | GIS/Mapping Services | Inbound | Must |
| EI-007 | Weather Services | Inbound | Should |

### 10.2 Integration Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| EI-010 | System SHALL use adapters for protocol translation | Must |
| EI-011 | System SHALL implement circuit breakers for external calls | Must |
| EI-012 | System SHALL cache external data where appropriate | Should |
| EI-013 | System SHALL log all external system interactions | Must |
| EI-014 | System SHALL handle external system failures gracefully | Must |

---

## Open Questions

The following functional requirements need clarification:

1. What specific types of alerts will be integrated (fire alarms, intrusion alarms, panic buttons)?
2. What CAD (Computer-Aided Dispatch) systems are currently in use?
3. Are there existing protocols/standards for inter-agency communication?
4. What geographic area will the system cover initially?
5. What is the expected number of concurrent users?
6. What is the expected volume of IoT devices/sensors?

---

## Related Documents

- [Technical Requirements](TECHNICAL_REQUIREMENTS.md)
- [Security Requirements](SECURITY_REQUIREMENTS.md)
- [System Architecture](../architecture/SYSTEM_ARCHITECTURE.md)

---

*Document Version: 1.0 | Last Updated: January 2025 | Classification: Confidential*
