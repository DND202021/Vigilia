# Contributing to ERIOP

This document outlines the standards and processes for contributing to the Emergency Response IoT Platform.

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Development Environment](#development-environment)
3. [Code Quality Standards](#code-quality-standards)
4. [Git Workflow](#git-workflow)
5. [Pull Request Process](#pull-request-process)
6. [Testing Requirements](#testing-requirements)
7. [Documentation Standards](#documentation-standards)

---

## Code of Conduct

All contributors must maintain professionalism and respect. This is a mission-critical platform for emergency services — quality and reliability are paramount.

---

## Development Environment

### Prerequisites

- Python 3.11+
- Node.js 18+ (LTS)
- Docker & Docker Compose
- PostgreSQL 15+
- Redis 7+

### Setup

```bash
# Clone repository
git clone https://github.com/your-org/eriop-project.git
cd eriop-project

# Create Python virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install Python dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Install Node dependencies
cd src/frontend && npm install
cd ../mobile && npm install

# Set up pre-commit hooks
pre-commit install

# Copy environment template
cp .env.example .env
# Edit .env with your local configuration

# Start infrastructure services
docker-compose up -d postgres redis

# Run database migrations
alembic upgrade head
```

---

## Code Quality Standards

### Python (Backend)

| Tool | Purpose | Configuration |
|------|---------|---------------|
| **Black** | Code formatting | `pyproject.toml` |
| **isort** | Import sorting | `pyproject.toml` |
| **Ruff** | Linting (replaces flake8) | `pyproject.toml` |
| **mypy** | Static type checking | `mypy.ini` |
| **Bandit** | Security scanning | `bandit.yaml` |

#### Style Guidelines

```python
"""
Module docstring describing the module's purpose.

This module handles [specific functionality].
"""

from typing import Optional, List
from dataclasses import dataclass
from datetime import datetime

# Constants in SCREAMING_SNAKE_CASE
MAX_RETRY_ATTEMPTS: int = 3
DEFAULT_TIMEOUT_SECONDS: int = 30


@dataclass
class IncidentReport:
    """
    Represents an emergency incident report.
    
    Attributes:
        incident_id: Unique identifier for the incident
        severity: Severity level (1-5, where 5 is critical)
        location: GPS coordinates or address
        created_at: Timestamp of incident creation
    """
    incident_id: str
    severity: int
    location: str
    created_at: datetime
    description: Optional[str] = None


async def process_incident(
    incident: IncidentReport,
    notify_units: bool = True
) -> dict:
    """
    Process an incoming incident report.
    
    Args:
        incident: The incident report to process
        notify_units: Whether to notify available units
        
    Returns:
        Dictionary containing processing result and assigned units
        
    Raises:
        ValidationError: If incident data is invalid
        DispatchError: If no units are available
    """
    # Implementation here
    pass
```

### TypeScript/React (Frontend)

| Tool | Purpose | Configuration |
|------|---------|---------------|
| **ESLint** | Linting | `.eslintrc.js` |
| **Prettier** | Code formatting | `.prettierrc` |
| **TypeScript** | Type checking | `tsconfig.json` |

#### Component Guidelines

```typescript
/**
 * IncidentCard displays a summary of an emergency incident.
 * 
 * @component
 * @example
 * <IncidentCard 
 *   incident={incidentData} 
 *   onSelect={handleSelect} 
 * />
 */

import React, { FC, memo, useCallback } from 'react';
import { Incident, IncidentSeverity } from '@/types/incident';

interface IncidentCardProps {
  /** The incident data to display */
  incident: Incident;
  /** Callback when the card is selected */
  onSelect: (id: string) => void;
  /** Whether the card is currently selected */
  isSelected?: boolean;
}

export const IncidentCard: FC<IncidentCardProps> = memo(({
  incident,
  onSelect,
  isSelected = false,
}) => {
  const handleClick = useCallback(() => {
    onSelect(incident.id);
  }, [incident.id, onSelect]);

  return (
    <div 
      className={`incident-card ${isSelected ? 'selected' : ''}`}
      onClick={handleClick}
      role="button"
      tabIndex={0}
      aria-pressed={isSelected}
    >
      {/* Component content */}
    </div>
  );
});

IncidentCard.displayName = 'IncidentCard';
```

---

## Git Workflow

### Branch Naming Convention

```
<type>/<ticket-id>-<short-description>
```

| Type | Purpose |
|------|---------|
| `feature/` | New features |
| `bugfix/` | Bug fixes |
| `hotfix/` | Production hotfixes |
| `security/` | Security patches |
| `docs/` | Documentation updates |
| `refactor/` | Code refactoring |
| `test/` | Test additions/modifications |

**Examples:**
- `feature/ERIOP-123-incident-management-api`
- `bugfix/ERIOP-456-fix-sync-conflict`
- `security/ERIOP-789-patch-auth-vulnerability`

### Commit Message Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:** `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `security`

**Example:**
```
feat(incidents): add real-time incident status updates

- Implement WebSocket connection for live updates
- Add status change notifications
- Update incident card component

Closes ERIOP-123
```

### Protected Branches

| Branch | Protection | Purpose |
|--------|------------|---------|
| `main` | Full protection, requires 2 approvers | Production code |
| `develop` | Requires 1 approver | Integration branch |
| `release/*` | Requires 1 approver | Release candidates |

---

## Pull Request Process

### Before Submitting

1. **Run all checks locally:**
   ```bash
   # Python
   black src/backend
   isort src/backend
   ruff check src/backend
   mypy src/backend
   bandit -r src/backend
   pytest tests/ -v --cov=src/backend
   
   # Frontend
   cd src/frontend
   npm run lint
   npm run type-check
   npm run test
   ```

2. **Ensure documentation is updated**

3. **Update CHANGELOG.md if applicable**

### PR Template

```markdown
## Description
[Describe the changes made]

## Type of Change
- [ ] Bug fix (non-breaking change fixing an issue)
- [ ] New feature (non-breaking change adding functionality)
- [ ] Breaking change (fix or feature causing existing functionality to change)
- [ ] Security patch
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing completed

## Security Checklist
- [ ] No sensitive data exposed
- [ ] Input validation implemented
- [ ] Authentication/authorization verified
- [ ] Audit logging added for sensitive operations

## Documentation
- [ ] Code comments added
- [ ] API documentation updated
- [ ] README updated (if applicable)

## Related Issues
Closes #[issue number]
```

### Review Criteria

Reviewers will check for:

1. **Functionality:** Does the code do what it's supposed to?
2. **Security:** Are there any security vulnerabilities?
3. **Performance:** Are there any performance concerns?
4. **Maintainability:** Is the code readable and maintainable?
5. **Testing:** Is there adequate test coverage?
6. **Documentation:** Is the code properly documented?

---

## Testing Requirements

### Coverage Targets

| Test Type | Coverage Target | Automation |
|-----------|-----------------|------------|
| Unit Tests | 85%+ | Full |
| Integration Tests | Critical paths | Full |
| End-to-End Tests | Main workflows | Full |
| Performance Tests | Key operations | Semi-automated |
| Security Tests | OWASP Top 10 | Full |

### Running Tests

```bash
# Unit tests with coverage
pytest tests/unit -v --cov=src/backend --cov-report=html

# Integration tests
pytest tests/integration -v

# Security tests
bandit -r src/backend -f json -o security-report.json

# Frontend tests
cd src/frontend && npm run test:coverage

# E2E tests
npm run test:e2e
```

### Test Naming Convention

```python
def test_<unit>_<scenario>_<expected_result>():
    """Test description."""
    pass

# Examples:
def test_incident_create_with_valid_data_returns_201():
    """Creating an incident with valid data should return HTTP 201."""
    pass

def test_incident_create_without_auth_returns_401():
    """Creating an incident without authentication should return HTTP 401."""
    pass
```

---

## Documentation Standards

### Inline Comments

- Explain **why**, not **what**
- Complex algorithms must be documented
- Security-sensitive code must be clearly marked

```python
# SECURITY: Rate limiting prevents brute-force attacks on login endpoint
# See ADR-003 for rate limiting architecture decision
@rate_limit(max_requests=5, window_seconds=60)
async def login(credentials: LoginRequest) -> TokenResponse:
    pass
```

### API Documentation

All API endpoints must include:

- Description
- Request/response schemas
- Authentication requirements
- Rate limits
- Example requests/responses
- Error codes

### Architecture Decision Records

Major technical decisions must be documented in `docs/adr/` using the template in `docs/adr/TEMPLATE.md`.

---

## Questions?

Contact the development team lead or open a discussion in the repository.

---

*Document Version: 1.0 | Last Updated: January 2025*
