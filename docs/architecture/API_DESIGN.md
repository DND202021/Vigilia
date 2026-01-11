# API Design

This document describes the REST API design for ERIOP.

## Table of Contents

1. [Overview](#overview)
2. [API Conventions](#api-conventions)
3. [Authentication](#authentication)
4. [Endpoints](#endpoints)
5. [Error Handling](#error-handling)
6. [Rate Limiting](#rate-limiting)
7. [Versioning](#versioning)
8. [WebSocket API](#websocket-api)

---

## Overview

ERIOP exposes a RESTful API for all client interactions. The API follows industry best practices for security, consistency, and developer experience.

### Base URL

```
Production:  https://api.eriop.example.com/v1
Staging:     https://api-staging.eriop.example.com/v1
Development: http://localhost:8000/v1
```

### Content Type

All requests and responses use JSON:

```
Content-Type: application/json
Accept: application/json
```

---

## API Conventions

### URL Structure

```
/{resource}/{id}/{sub-resource}
```

**Examples:**
- `GET /incidents` — List incidents
- `GET /incidents/{id}` — Get specific incident
- `GET /incidents/{id}/timeline` — Get incident timeline
- `POST /incidents/{id}/assign` — Action on incident

### HTTP Methods

| Method | Usage | Idempotent |
|--------|-------|------------|
| `GET` | Retrieve resource(s) | Yes |
| `POST` | Create resource or action | No |
| `PUT` | Full update | Yes |
| `PATCH` | Partial update | Yes |
| `DELETE` | Remove resource | Yes |

### Naming Conventions

- **Resources:** Plural nouns, lowercase, hyphenated (`/incidents`, `/audit-logs`)
- **Actions:** Verbs for non-CRUD operations (`/incidents/{id}/escalate`)
- **Query parameters:** snake_case (`?page_size=20&sort_by=created_at`)
- **Request/Response fields:** snake_case

### Pagination

```json
// Request
GET /incidents?page=2&page_size=20

// Response
{
  "data": [...],
  "pagination": {
    "page": 2,
    "page_size": 20,
    "total_items": 150,
    "total_pages": 8,
    "has_next": true,
    "has_previous": true
  }
}
```

### Filtering

```
GET /incidents?status=active&priority=1,2&agency_id=uuid
GET /incidents?created_after=2025-01-01T00:00:00Z
GET /incidents?search=downtown
```

### Sorting

```
GET /incidents?sort_by=created_at&sort_order=desc
GET /incidents?sort_by=-priority,created_at  # Shorthand: - for desc
```

### Field Selection

```
GET /incidents?fields=id,incident_number,status,title
GET /incidents?expand=assigned_unit,reported_by
```

---

## Authentication

### OAuth 2.0 / JWT

All API requests require a valid JWT token in the Authorization header:

```
Authorization: Bearer <jwt_token>
```

### Token Structure

```json
{
  "sub": "user_uuid",
  "email": "user@example.com",
  "roles": ["responder", "field_unit"],
  "agency_id": "agency_uuid",
  "permissions": ["incidents:read", "incidents:create"],
  "exp": 1704067200,
  "iat": 1704063600,
  "jti": "unique_token_id"
}
```

### Token Endpoints

```
POST /auth/login          # Get access + refresh tokens
POST /auth/refresh        # Refresh access token
POST /auth/logout         # Invalidate tokens
POST /auth/mfa/verify     # Complete MFA challenge
```

### Login Flow

```http
POST /auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "secure_password"
}
```

**Response (MFA Required):**
```json
{
  "mfa_required": true,
  "mfa_token": "temp_token_for_mfa",
  "mfa_methods": ["totp", "sms"]
}
```

**Response (Success):**
```json
{
  "access_token": "eyJhbG...",
  "refresh_token": "eyJhbG...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "name": "John Doe",
    "roles": ["responder"]
  }
}
```

---

## Endpoints

### Incidents

#### List Incidents

```http
GET /incidents
Authorization: Bearer <token>
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `status` | string | Filter by status (comma-separated) |
| `priority` | integer | Filter by priority (comma-separated) |
| `agency_id` | uuid | Filter by agency |
| `assigned_to` | uuid | Filter by assigned unit |
| `created_after` | datetime | Filter by creation date |
| `created_before` | datetime | Filter by creation date |
| `search` | string | Full-text search |
| `near` | string | Lat,lng,radius_km for geo search |

**Response:**
```json
{
  "data": [
    {
      "id": "uuid",
      "incident_number": "INC-2025-0001",
      "type": "fire",
      "category": "structure_fire",
      "priority": 1,
      "status": "assigned",
      "title": "Structure Fire - 123 Main St",
      "location": {
        "latitude": 45.5017,
        "longitude": -73.5673
      },
      "address": {
        "street": "123 Main St",
        "city": "Montreal",
        "province": "QC"
      },
      "created_at": "2025-01-11T10:30:00Z",
      "updated_at": "2025-01-11T10:35:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_items": 45,
    "total_pages": 3
  }
}
```

#### Create Incident

```http
POST /incidents
Authorization: Bearer <token>
Content-Type: application/json

{
  "type": "fire",
  "category": "structure_fire",
  "priority": 1,
  "title": "Structure Fire - 123 Main St",
  "description": "Smoke visible from third floor",
  "location": {
    "latitude": 45.5017,
    "longitude": -73.5673
  },
  "address": {
    "street": "123 Main St",
    "city": "Montreal",
    "province": "QC",
    "postal_code": "H2X 1Y1"
  }
}
```

**Response:** `201 Created`
```json
{
  "id": "uuid",
  "incident_number": "INC-2025-0042",
  "status": "new",
  "created_at": "2025-01-11T12:00:00Z",
  "_links": {
    "self": "/incidents/uuid",
    "timeline": "/incidents/uuid/timeline",
    "assign": "/incidents/uuid/assign"
  }
}
```

#### Get Incident

```http
GET /incidents/{id}
Authorization: Bearer <token>
```

**Response:**
```json
{
  "id": "uuid",
  "incident_number": "INC-2025-0042",
  "type": "fire",
  "category": "structure_fire",
  "priority": 1,
  "status": "on_scene",
  "title": "Structure Fire - 123 Main St",
  "description": "Smoke visible from third floor",
  "location": {
    "latitude": 45.5017,
    "longitude": -73.5673
  },
  "address": {
    "street": "123 Main St",
    "city": "Montreal",
    "province": "QC",
    "postal_code": "H2X 1Y1"
  },
  "reported_by": {
    "id": "uuid",
    "name": "John Doe"
  },
  "assigned_unit": {
    "id": "uuid",
    "name": "Engine 12"
  },
  "agency": {
    "id": "uuid",
    "name": "Montreal Fire Department"
  },
  "timeline": [
    {
      "timestamp": "2025-01-11T12:00:00Z",
      "event": "created",
      "user": "John Doe"
    },
    {
      "timestamp": "2025-01-11T12:02:00Z",
      "event": "assigned",
      "details": "Assigned to Engine 12"
    }
  ],
  "created_at": "2025-01-11T12:00:00Z",
  "updated_at": "2025-01-11T12:15:00Z"
}
```

#### Update Incident

```http
PATCH /incidents/{id}
Authorization: Bearer <token>
Content-Type: application/json

{
  "status": "on_scene",
  "description": "Updated: Fire contained to third floor"
}
```

#### Assign Incident

```http
POST /incidents/{id}/assign
Authorization: Bearer <token>
Content-Type: application/json

{
  "unit_id": "uuid",
  "notes": "Closest available unit"
}
```

#### Escalate Incident

```http
POST /incidents/{id}/escalate
Authorization: Bearer <token>
Content-Type: application/json

{
  "new_priority": 1,
  "reason": "Fire spreading to adjacent building"
}
```

### Resources

#### List Resources

```http
GET /resources
Authorization: Bearer <token>
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `type` | string | personnel, vehicle, equipment |
| `status` | string | available, assigned, off_duty |
| `agency_id` | uuid | Filter by agency |
| `capabilities` | string | Filter by capability (comma-separated) |
| `near` | string | Lat,lng,radius_km for geo search |

#### Update Resource Status

```http
PATCH /resources/{id}/status
Authorization: Bearer <token>
Content-Type: application/json

{
  "status": "available",
  "location": {
    "latitude": 45.5017,
    "longitude": -73.5673
  }
}
```

### Alerts

#### List Alerts

```http
GET /alerts
Authorization: Bearer <token>
```

#### Acknowledge Alert

```http
POST /alerts/{id}/acknowledge
Authorization: Bearer <token>
```

#### Convert Alert to Incident

```http
POST /alerts/{id}/convert
Authorization: Bearer <token>
Content-Type: application/json

{
  "incident_type": "burglary",
  "priority": 2,
  "additional_info": "Optional extra details"
}
```

### Messages

#### Send Message

```http
POST /channels/{channel_id}/messages
Authorization: Bearer <token>
Content-Type: application/json

{
  "content": "Message text",
  "priority": "normal",
  "attachments": []
}
```

#### Get Channel Messages

```http
GET /channels/{channel_id}/messages
Authorization: Bearer <token>
```

---

## Error Handling

### Error Response Format

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": [
      {
        "field": "priority",
        "message": "Must be between 1 and 5"
      }
    ],
    "request_id": "req_abc123",
    "documentation_url": "https://docs.eriop.example.com/errors/VALIDATION_ERROR"
  }
}
```

### HTTP Status Codes

| Code | Meaning | When Used |
|------|---------|-----------|
| `200` | OK | Successful GET, PATCH |
| `201` | Created | Successful POST (creation) |
| `204` | No Content | Successful DELETE |
| `400` | Bad Request | Invalid request format |
| `401` | Unauthorized | Missing/invalid token |
| `403` | Forbidden | Insufficient permissions |
| `404` | Not Found | Resource doesn't exist |
| `409` | Conflict | Resource conflict (e.g., duplicate) |
| `422` | Unprocessable Entity | Validation error |
| `429` | Too Many Requests | Rate limit exceeded |
| `500` | Internal Server Error | Server error |
| `503` | Service Unavailable | Maintenance/overload |

### Error Codes

| Code | Description |
|------|-------------|
| `AUTHENTICATION_REQUIRED` | No token provided |
| `INVALID_TOKEN` | Token invalid or expired |
| `INSUFFICIENT_PERMISSIONS` | User lacks required permission |
| `RESOURCE_NOT_FOUND` | Resource doesn't exist |
| `VALIDATION_ERROR` | Request validation failed |
| `DUPLICATE_RESOURCE` | Resource already exists |
| `RATE_LIMIT_EXCEEDED` | Too many requests |
| `INTERNAL_ERROR` | Server error |

---

## Rate Limiting

### Limits

| Endpoint Type | Rate Limit |
|---------------|------------|
| Standard API | 1000 req/min per user |
| Authentication | 10 req/min per IP |
| File Upload | 100 req/min per user |
| Public Portal | 100 req/min per IP |

### Headers

```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 950
X-RateLimit-Reset: 1704067200
```

### Rate Limit Exceeded Response

```http
HTTP/1.1 429 Too Many Requests
Retry-After: 30

{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests. Retry after 30 seconds.",
    "retry_after": 30
  }
}
```

---

## Versioning

### URL Versioning

```
/v1/incidents
/v2/incidents
```

### Version Lifecycle

| Version | Status | Sunset Date |
|---------|--------|-------------|
| v1 | Current | - |
| v2 | Beta | - |

### Deprecation Headers

```http
Deprecation: true
Sunset: Sat, 01 Jan 2026 00:00:00 GMT
Link: </v2/incidents>; rel="successor-version"
```

---

## WebSocket API

### Connection

```javascript
const ws = new WebSocket('wss://api.eriop.example.com/ws');

// Authenticate
ws.send(JSON.stringify({
  type: 'auth',
  token: 'jwt_token'
}));
```

### Message Format

```json
{
  "type": "event_type",
  "payload": { ... },
  "timestamp": "2025-01-11T12:00:00Z"
}
```

### Event Types

| Type | Direction | Description |
|------|-----------|-------------|
| `auth` | Client → Server | Authentication |
| `subscribe` | Client → Server | Subscribe to channel |
| `unsubscribe` | Client → Server | Unsubscribe from channel |
| `ping` | Bidirectional | Keep-alive |
| `incident.created` | Server → Client | New incident |
| `incident.updated` | Server → Client | Incident update |
| `alert.received` | Server → Client | New alert |
| `resource.status` | Server → Client | Resource status change |
| `message.received` | Server → Client | New message |

### Subscription Example

```json
// Subscribe to incident updates for agency
{
  "type": "subscribe",
  "channel": "agency.uuid.incidents"
}

// Subscribe to specific incident
{
  "type": "subscribe",
  "channel": "incident.uuid"
}
```

---

## Related Documents

- [System Architecture](SYSTEM_ARCHITECTURE.md)
- [Security Framework](../security/SECURITY_FRAMEWORK.md)
- [OpenAPI Specification](../api/openapi.yaml)

---

*Document Version: 1.0 | Last Updated: January 2025 | Classification: Confidential*
