# System Architecture

This document describes the high-level architecture of the Emergency Response IoT Platform (ERIOP).

## Table of Contents

1. [Overview](#overview)
2. [Architecture Principles](#architecture-principles)
3. [System Context](#system-context)
4. [Container Architecture](#container-architecture)
5. [Component Architecture](#component-architecture)
6. [Data Flow](#data-flow)
7. [Deployment Architecture](#deployment-architecture)
8. [Security Architecture](#security-architecture)

---

## Overview

ERIOP is a distributed, cloud-native platform designed to provide real-time tactical and strategic information to emergency responders. The architecture prioritizes security, high availability, and offline capability.

### Architecture Style

The system follows a **microservices architecture** pattern with the following characteristics:

- Event-driven communication via MQTT (Fundamentum) and Redis pub/sub
- API Gateway pattern for external access
- CQRS for read-heavy operations
- Offline-first mobile design with sync capabilities

---

## Architecture Principles

| Principle | Implementation |
|-----------|----------------|
| **Security First** | Zero-trust model, encryption everywhere, audit logging |
| **High Availability** | Multi-zone deployment, no single points of failure |
| **Offline Capable** | Local data stores, sync engine, conflict resolution |
| **Real-time** | WebSocket connections, event streaming, push notifications |
| **Scalable** | Horizontal scaling, stateless services, caching layers |
| **Observable** | Distributed tracing, metrics, centralized logging |

---

## System Context

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              External Systems                                 │
├─────────────────┬─────────────────┬─────────────────┬─────────────────────────┤
│   Alarm         │   Security      │   CAD           │   Weather/GIS           │
│   Systems       │   Systems       │   Systems       │   Services              │
└────────┬────────┴────────┬────────┴────────┬────────┴────────────┬────────────┘
         │                 │                 │                     │
         ▼                 ▼                 ▼                     ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                               │
│                    ┌─────────────────────────────────────┐                   │
│                    │         ERIOP Platform              │                   │
│                    │                                     │                   │
│                    │  ┌─────────────────────────────┐   │                   │
│                    │  │     Fundamentum IoT PaaS    │   │                   │
│                    │  └─────────────────────────────┘   │                   │
│                    │                                     │                   │
│                    └─────────────────────────────────────┘                   │
│                                                                               │
└──────────────────────────────────────────────────────────────────────────────┘
         │                 │                 │                     │
         ▼                 ▼                 ▼                     ▼
┌─────────────────┬─────────────────┬─────────────────┬─────────────────────────┐
│   Field Units   │   Command       │   Dispatchers   │   Public                │
│   (Mobile)      │   Center        │   (Web)         │   Portal                │
└─────────────────┴─────────────────┴─────────────────┴─────────────────────────┘
```

### External System Integrations

| System | Direction | Protocol | Purpose |
|--------|-----------|----------|---------|
| Alarm Systems | Inbound | Various (adapted) | Receive alerts from monitored premises |
| Security Systems | Bidirectional | API/Webhooks | Camera feeds, access control status |
| CAD Systems | Bidirectional | HL7/API | Computer-Aided Dispatch integration |
| GIS/Mapping | Inbound | WMS/WFS/API | Geographic data, building information |
| Hospital Systems | Outbound | HL7 FHIR | Patient status, capacity queries |
| Weather Services | Inbound | REST API | Environmental conditions |
| Axis IP Microphones | Inbound | MQTT | Sound environment analysis |

---

## Container Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                   ERIOP Platform                                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │                          API Gateway (Kong/NGINX)                        │    │
│  │  • Rate limiting  • Authentication  • Routing  • TLS termination        │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                       │                                          │
│       ┌───────────────────────────────┼───────────────────────────────┐         │
│       │                               │                               │         │
│       ▼                               ▼                               ▼         │
│  ┌──────────────┐              ┌──────────────┐              ┌──────────────┐   │
│  │   Auth       │              │   Incident   │              │   Resource   │   │
│  │   Service    │              │   Service    │              │   Service    │   │
│  └──────────────┘              └──────────────┘              └──────────────┘   │
│       │                               │                               │         │
│       │                               │                               │         │
│       ▼                               ▼                               ▼         │
│  ┌──────────────┐              ┌──────────────┐              ┌──────────────┐   │
│  │   Alert      │              │   Comm       │              │   Integration│   │
│  │   Engine     │              │   Hub        │              │   Service    │   │
│  └──────────────┘              └──────────────┘              └──────────────┘   │
│       │                               │                               │         │
│       └───────────────────────────────┼───────────────────────────────┘         │
│                                       │                                          │
│                                       ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │                        Fundamentum Integration Layer                     │    │
│  │         • MQTT Client  • Device Registry  • Telemetry Processing        │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                       │                                          │
│                                       ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │                           Data Layer                                     │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                   │    │
│  │  │  PostgreSQL  │  │  TimescaleDB │  │    Redis     │                   │    │
│  │  │  (Primary)   │  │  (Telemetry) │  │  (Cache/PubSub)│                 │    │
│  │  └──────────────┘  └──────────────┘  └──────────────┘                   │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Component Architecture

### Core Services

#### 1. Authentication Service
```
┌─────────────────────────────────────────────────────┐
│                 Auth Service                         │
├─────────────────────────────────────────────────────┤
│  Responsibilities:                                   │
│  • User authentication (OAuth 2.0 / OIDC)           │
│  • Token issuance and validation                    │
│  • MFA management                                    │
│  • Session management                               │
│  • Password policies                                │
├─────────────────────────────────────────────────────┤
│  Dependencies:                                       │
│  • PostgreSQL (user store)                          │
│  • Redis (session cache)                            │
│  • HashiCorp Vault (secrets)                        │
├─────────────────────────────────────────────────────┤
│  APIs:                                               │
│  • POST /auth/login                                 │
│  • POST /auth/logout                                │
│  • POST /auth/refresh                               │
│  • POST /auth/mfa/verify                            │
│  • GET  /auth/user                                  │
└─────────────────────────────────────────────────────┘
```

#### 2. Incident Management Service
```
┌─────────────────────────────────────────────────────┐
│              Incident Service                        │
├─────────────────────────────────────────────────────┤
│  Responsibilities:                                   │
│  • Incident lifecycle (create, update, close)       │
│  • Categorization and priority assignment           │
│  • Unit assignment and escalation                   │
│  • Timeline and audit trail                         │
├─────────────────────────────────────────────────────┤
│  Dependencies:                                       │
│  • PostgreSQL (incident store)                      │
│  • Redis (pub/sub for real-time updates)            │
│  • Resource Service (unit availability)             │
│  • Alert Engine (incident triggers)                 │
├─────────────────────────────────────────────────────┤
│  APIs:                                               │
│  • POST   /incidents                                │
│  • GET    /incidents/{id}                           │
│  • PATCH  /incidents/{id}                           │
│  • POST   /incidents/{id}/assign                    │
│  • POST   /incidents/{id}/escalate                  │
│  • GET    /incidents/{id}/timeline                  │
└─────────────────────────────────────────────────────┘
```

#### 3. Resource Tracking Service
```
┌─────────────────────────────────────────────────────┐
│              Resource Service                        │
├─────────────────────────────────────────────────────┤
│  Responsibilities:                                   │
│  • Personnel location and status tracking           │
│  • Vehicle tracking and assignment                  │
│  • Equipment inventory management                   │
│  • Availability calculations                        │
├─────────────────────────────────────────────────────┤
│  Dependencies:                                       │
│  • PostgreSQL (resource registry)                   │
│  • TimescaleDB (location history)                   │
│  • Fundamentum (GPS telemetry)                      │
│  • Redis (real-time status cache)                   │
├─────────────────────────────────────────────────────┤
│  APIs:                                               │
│  • GET    /resources/personnel                      │
│  • GET    /resources/vehicles                       │
│  • GET    /resources/equipment                      │
│  • PATCH  /resources/{type}/{id}/status             │
│  • GET    /resources/available                      │
└─────────────────────────────────────────────────────┘
```

#### 4. Alert Engine
```
┌─────────────────────────────────────────────────────┐
│                Alert Engine                          │
├─────────────────────────────────────────────────────┤
│  Responsibilities:                                   │
│  • Alert ingestion from external systems            │
│  • Classification and priority assignment           │
│  • Routing rules engine                             │
│  • Notification delivery orchestration              │
├─────────────────────────────────────────────────────┤
│  Dependencies:                                       │
│  • Fundamentum (MQTT alerts from devices)           │
│  • Integration Service (external systems)           │
│  • Redis (alert queue)                              │
│  • Communication Hub (notifications)                │
├─────────────────────────────────────────────────────┤
│  Event Flows:                                        │
│  • MQTT → Alert Ingestion → Classification          │
│  • Classification → Routing → Notification          │
│  • Alert → Incident Creation (automatic)            │
└─────────────────────────────────────────────────────┘
```

#### 5. Communication Hub
```
┌─────────────────────────────────────────────────────┐
│              Communication Hub                       │
├─────────────────────────────────────────────────────┤
│  Responsibilities:                                   │
│  • Secure messaging between users/units             │
│  • Channel management (incident-specific, team)     │
│  • Message persistence and history                  │
│  • Push notification delivery                       │
├─────────────────────────────────────────────────────┤
│  Dependencies:                                       │
│  • PostgreSQL (message store)                       │
│  • Redis (pub/sub, presence)                        │
│  • FCM/APNs (mobile push)                           │
│  • WebSocket (real-time web)                        │
├─────────────────────────────────────────────────────┤
│  Protocols:                                          │
│  • WebSocket (web clients)                          │
│  • FCM/APNs (mobile push)                           │
│  • REST API (message history)                       │
└─────────────────────────────────────────────────────┘
```

#### 6. Integration Service
```
┌─────────────────────────────────────────────────────┐
│             Integration Service                      │
├─────────────────────────────────────────────────────┤
│  Responsibilities:                                   │
│  • External system adapters                         │
│  • Protocol translation and normalization           │
│  • Rate limiting and caching                        │
│  • Circuit breaker patterns                         │
├─────────────────────────────────────────────────────┤
│  Adapters:                                           │
│  • Alarm System Adapter                             │
│  • Security System Adapter (cameras, access)        │
│  • CAD System Adapter                               │
│  • GIS/Mapping Adapter                              │
│  • Weather Service Adapter                          │
│  • Hospital System Adapter                          │
├─────────────────────────────────────────────────────┤
│  Patterns:                                           │
│  • Adapter Pattern (protocol translation)           │
│  • Circuit Breaker (fault tolerance)                │
│  • Retry with exponential backoff                   │
└─────────────────────────────────────────────────────┘
```

---

## Data Flow

### Alert Processing Flow

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   External  │    │ Integration │    │   Alert     │    │  Incident   │
│   System    │───▶│   Service   │───▶│   Engine    │───▶│   Service   │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
                                             │                   │
                                             ▼                   ▼
                                      ┌─────────────┐    ┌─────────────┐
                                      │    Comm     │    │  Resource   │
                                      │    Hub      │    │   Service   │
                                      └─────────────┘    └─────────────┘
                                             │                   │
                                             ▼                   ▼
                                      ┌─────────────────────────────────┐
                                      │         Mobile/Web Clients       │
                                      └─────────────────────────────────┘
```

### Real-time Update Flow

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                               │
│   Service Event ──▶ Redis Pub/Sub ──▶ WebSocket Server ──▶ Connected Clients │
│                                                                               │
│   Examples:                                                                   │
│   • Incident status change                                                   │
│   • Resource location update                                                 │
│   • New alert received                                                       │
│   • Message received                                                         │
│                                                                               │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Deployment Architecture

### Cloud Deployment

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              Cloud Provider                                      │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │                         Kubernetes Cluster                               │   │
│   │                                                                          │   │
│   │   ┌──────────────────────────────────────────────────────────────────┐  │   │
│   │   │  Ingress Controller (NGINX) + WAF                                │  │   │
│   │   └──────────────────────────────────────────────────────────────────┘  │   │
│   │                                   │                                      │   │
│   │   ┌───────────────────────────────┼───────────────────────────────┐     │   │
│   │   │                               │                               │     │   │
│   │   ▼                               ▼                               ▼     │   │
│   │   ┌───────────────┐  ┌───────────────┐  ┌───────────────┐            │   │
│   │   │   Namespace:  │  │   Namespace:  │  │   Namespace:  │            │   │
│   │   │   eriop-prod  │  │  eriop-stage  │  │   eriop-dev   │            │   │
│   │   └───────────────┘  └───────────────┘  └───────────────┘            │   │
│   │                                                                          │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │                       Managed Services                                   │   │
│   │                                                                          │   │
│   │   ┌───────────────┐  ┌───────────────┐  ┌───────────────┐               │   │
│   │   │  PostgreSQL   │  │  TimescaleDB  │  │    Redis      │               │   │
│   │   │  (HA Cluster) │  │  (HA Cluster) │  │   (Cluster)   │               │   │
│   │   └───────────────┘  └───────────────┘  └───────────────┘               │   │
│   │                                                                          │   │
│   │   ┌───────────────┐  ┌───────────────┐                                  │   │
│   │   │  Object       │  │   Secrets     │                                  │   │
│   │   │  Storage      │  │   Manager     │                                  │   │
│   │   └───────────────┘  └───────────────┘                                  │   │
│   │                                                                          │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Edge/Offline Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            Local Gateway (Field)                                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │                      Edge Computing Module                               │   │
│   │                                                                          │   │
│   │   ┌───────────────┐  ┌───────────────┐  ┌───────────────┐               │   │
│   │   │   Local       │  │   Sync        │  │   Decision    │               │   │
│   │   │   SQLite      │  │   Engine      │  │   Engine      │               │   │
│   │   └───────────────┘  └───────────────┘  └───────────────┘               │   │
│   │                                                                          │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│                                       │                                          │
│                                       │ (When connected)                        │
│                                       ▼                                          │
│                              ┌─────────────────┐                                │
│                              │   Cloud ERIOP   │                                │
│                              └─────────────────┘                                │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Security Architecture

### Network Security

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                  Internet                                        │
└──────────────────────────────────────┬──────────────────────────────────────────┘
                                       │
                              ┌────────▼────────┐
                              │       WAF       │
                              │  (CloudFlare)   │
                              └────────┬────────┘
                                       │
                              ┌────────▼────────┐
                              │  Load Balancer  │
                              │   (TLS 1.3)     │
                              └────────┬────────┘
                                       │
┌──────────────────────────────────────┼──────────────────────────────────────────┐
│                              DMZ Network                                         │
│                                      │                                           │
│                             ┌────────▼────────┐                                 │
│                             │   API Gateway   │                                 │
│                             └────────┬────────┘                                 │
│                                      │                                           │
└──────────────────────────────────────┼──────────────────────────────────────────┘
                                       │
┌──────────────────────────────────────┼──────────────────────────────────────────┐
│                           Application Network                                    │
│                                      │                                           │
│     ┌────────────────────────────────┼────────────────────────────────┐         │
│     │                                │                                │         │
│     ▼                                ▼                                ▼         │
│ ┌─────────┐                    ┌─────────┐                    ┌─────────┐       │
│ │Services │                    │Services │                    │Services │       │
│ └─────────┘                    └─────────┘                    └─────────┘       │
│                                                                                  │
└──────────────────────────────────────┬──────────────────────────────────────────┘
                                       │
┌──────────────────────────────────────┼──────────────────────────────────────────┐
│                              Data Network                                        │
│                                      │                                           │
│     ┌────────────────────────────────┼────────────────────────────────┐         │
│     │                                │                                │         │
│     ▼                                ▼                                ▼         │
│ ┌─────────┐                    ┌─────────┐                    ┌─────────┐       │
│ │PostgreSQL│                   │TimescaleDB│                  │  Redis  │       │
│ └─────────┘                    └─────────┘                    └─────────┘       │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Related Documents

- [Database Design](DATABASE_DESIGN.md)
- [API Design](API_DESIGN.md)
- [Integration Architecture](INTEGRATION_ARCHITECTURE.md)
- [Security Framework](../security/SECURITY_FRAMEWORK.md)
- [ADR Index](../adr/INDEX.md)

---

*Document Version: 1.0 | Last Updated: January 2025 | Classification: Confidential*
