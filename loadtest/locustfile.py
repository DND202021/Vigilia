"""Locust load test suite for ERIOP backend.

Tests three user personas:
- ERIOPDispatcher (30%): Creates incidents, views alerts, manages resources
- ERIOPResponder (50%): Primarily reads - active incidents, alerts, resources
- AlertIngestion (20%): High-frequency alert POST for throughput testing

Target metrics:
- 1000 alerts/sec throughput
- 10,000 concurrent API requests
- p95 latency < 200ms
"""

import random
import uuid
from datetime import datetime, timezone
from locust import HttpUser, task, between, events
from locust.contrib.fasthttp import FastHttpUser


# ==================== Test Data Generators ====================

def generate_login_credentials(user_type: str) -> dict:
    """Generate login credentials for different user types."""
    credentials = {
        "dispatcher": {
            "email": f"dispatcher{random.randint(1, 100)}@test.eriop.local",
            "password": "TestPass123456!"
        },
        "responder": {
            "email": f"responder{random.randint(1, 200)}@test.eriop.local",
            "password": "TestPass123456!"
        },
        "alert_system": {
            "email": f"alertsystem{random.randint(1, 50)}@test.eriop.local",
            "password": "TestPass123456!"
        }
    }
    return credentials.get(user_type, credentials["responder"])


def generate_incident_payload() -> dict:
    """Generate realistic incident creation payload."""
    categories = ["fire", "medical", "police", "rescue", "traffic", "hazmat", "intrusion"]
    priorities = [1, 2, 3, 4, 5]  # 1=Critical, 5=Minimal

    return {
        "category": random.choice(categories),
        "priority": random.choice(priorities),
        "title": f"Incident {datetime.now(timezone.utc).isoformat()}",
        "description": f"Test incident created during load test",
        "location": {
            "latitude": 45.5017 + random.uniform(-0.5, 0.5),  # Montreal area
            "longitude": -73.5673 + random.uniform(-0.5, 0.5),
            "address": f"{random.randint(100, 9999)} Test Street",
            "building_info": None
        }
    }


def generate_alert_payload() -> dict:
    """Generate realistic alert ingestion payload."""
    alert_types = ["gunshot", "explosion", "glass_break", "aggression", "scream", "car_alarm"]
    severities = ["critical", "high", "medium", "low", "info"]
    sources = ["fundamentum", "alarm_system", "axis_microphone", "security_system"]

    return {
        "source": random.choice(sources),
        "source_id": f"device_{random.randint(1000, 9999)}",
        "severity": random.choice(severities),
        "alert_type": random.choice(alert_types),
        "title": f"Alert {datetime.now(timezone.utc).isoformat()}",
        "description": "Load test alert",
        "location": {
            "latitude": 45.5017 + random.uniform(-0.5, 0.5),
            "longitude": -73.5673 + random.uniform(-0.5, 0.5),
            "address": f"{random.randint(100, 9999)} Alert Street",
            "zone": f"Zone {random.randint(1, 10)}"
        },
        "raw_payload": {
            "test": True,
            "timestamp": datetime.now(timezone.utc).isoformat()
        },
        "confidence": random.uniform(0.7, 1.0),
        "peak_level_db": random.uniform(80, 120),
        "background_level_db": random.uniform(40, 60)
    }


def generate_resource_payload() -> dict:
    """Generate resource creation payload."""
    resource_types = ["personnel", "vehicle", "equipment"]
    statuses = ["available", "assigned", "en_route", "on_scene", "off_duty"]

    return {
        "resource_type": random.choice(resource_types),
        "name": f"Resource-{random.randint(1000, 9999)}",
        "call_sign": f"UNIT-{random.randint(100, 999)}",
        "status": random.choice(statuses),
        "latitude": 45.5017 + random.uniform(-0.5, 0.5),
        "longitude": -73.5673 + random.uniform(-0.5, 0.5),
        "agency_id": "00000000-0000-0000-0000-000000000001"  # Test agency ID
    }


# ==================== User Classes ====================

class ERIOPDispatcher(FastHttpUser):
    """Dispatcher user - creates incidents, manages resources, views alerts.

    Weight: 30% of traffic
    Behavior:
    - Actively creates incidents from alerts
    - Views and acknowledges alerts
    - Assigns resources to incidents
    - Views dashboard data
    """

    weight = 3
    wait_time = between(2, 5)  # 2-5 seconds between tasks

    def on_start(self):
        """Authenticate on session start."""
        credentials = generate_login_credentials("dispatcher")
        response = self.client.post("/api/v1/auth/login", json=credentials)

        if response.status_code == 200:
            data = response.json()
            self.token = data.get("access_token")
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            # If auth fails, use empty headers (will fail gracefully)
            self.headers = {}

    @task(5)
    def view_active_incidents(self):
        """View active incidents list."""
        self.client.get("/api/v1/incidents/active", headers=self.headers, name="GET /incidents/active")

    @task(4)
    def view_pending_alerts(self):
        """View pending alerts requiring action."""
        self.client.get("/api/v1/alerts/pending", headers=self.headers, name="GET /alerts/pending")

    @task(3)
    def view_available_resources(self):
        """View available resources."""
        self.client.get("/api/v1/resources/available", headers=self.headers, name="GET /resources/available")

    @task(2)
    def create_incident(self):
        """Create a new incident."""
        payload = generate_incident_payload()
        self.client.post("/api/v1/incidents", json=payload, headers=self.headers, name="POST /incidents")

    @task(2)
    def acknowledge_alert(self):
        """Acknowledge a random alert."""
        # First get pending alerts
        response = self.client.get("/api/v1/alerts/pending", headers=self.headers, name="GET /alerts/pending (for ack)")

        if response.status_code == 200 and response.json():
            alerts = response.json()
            if alerts:
                alert_id = alerts[0]["id"]
                self.client.post(
                    f"/api/v1/alerts/{alert_id}/acknowledge",
                    json={"notes": "Acknowledged during load test"},
                    headers=self.headers,
                    name="POST /alerts/{id}/acknowledge"
                )

    @task(1)
    def view_incident_list(self):
        """View paginated incident list."""
        self.client.get("/api/v1/incidents?page=1&page_size=50", headers=self.headers, name="GET /incidents (paginated)")

    @task(1)
    def view_alert_list(self):
        """View paginated alert list."""
        self.client.get("/api/v1/alerts?page=1&page_size=50", headers=self.headers, name="GET /alerts (paginated)")


class ERIOPResponder(FastHttpUser):
    """Field responder user - primarily reads data.

    Weight: 50% of traffic
    Behavior:
    - Views active incidents
    - Views alerts
    - Checks resource status
    - Views building information
    """

    weight = 5
    wait_time = between(3, 8)  # 3-8 seconds between tasks (less active)

    def on_start(self):
        """Authenticate on session start."""
        credentials = generate_login_credentials("responder")
        response = self.client.post("/api/v1/auth/login", json=credentials)

        if response.status_code == 200:
            data = response.json()
            self.token = data.get("access_token")
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            self.headers = {}

    @task(8)
    def view_active_incidents(self):
        """View active incidents - most common action."""
        self.client.get("/api/v1/incidents/active", headers=self.headers, name="GET /incidents/active")

    @task(5)
    def view_pending_alerts(self):
        """View pending alerts."""
        self.client.get("/api/v1/alerts/pending", headers=self.headers, name="GET /alerts/pending")

    @task(4)
    def view_available_resources(self):
        """View available resources."""
        self.client.get("/api/v1/resources/available", headers=self.headers, name="GET /resources/available")

    @task(3)
    def view_incident_details(self):
        """View specific incident details."""
        # First get active incidents
        response = self.client.get("/api/v1/incidents/active", headers=self.headers, name="GET /incidents/active (for detail)")

        if response.status_code == 200 and response.json():
            incidents = response.json()
            if incidents:
                incident_id = incidents[0]["id"]
                self.client.get(f"/api/v1/incidents/{incident_id}", headers=self.headers, name="GET /incidents/{id}")

    @task(2)
    def view_alert_details(self):
        """View specific alert details."""
        response = self.client.get("/api/v1/alerts/pending", headers=self.headers, name="GET /alerts/pending (for detail)")

        if response.status_code == 200 and response.json():
            alerts = response.json()
            if alerts:
                alert_id = alerts[0]["id"]
                self.client.get(f"/api/v1/alerts/{alert_id}", headers=self.headers, name="GET /alerts/{id}")

    @task(2)
    def view_resource_list(self):
        """View resource list."""
        self.client.get("/api/v1/resources?page=1&page_size=50", headers=self.headers, name="GET /resources (paginated)")

    @task(1)
    def check_profile(self):
        """Check own user profile."""
        self.client.get("/api/v1/auth/me", headers=self.headers, name="GET /auth/me")


class AlertIngestion(FastHttpUser):
    """Alert ingestion system - high-frequency alert posting.

    Weight: 20% of traffic
    Behavior:
    - Continuously posts alerts at high rate
    - Simulates IoT devices, alarm systems, microphones
    - Tests throughput target of 1000 alerts/sec
    """

    weight = 2
    wait_time = between(0.1, 0.5)  # Very short wait time for high throughput

    def on_start(self):
        """Authenticate on session start."""
        credentials = generate_login_credentials("alert_system")
        response = self.client.post("/api/v1/auth/login", json=credentials)

        if response.status_code == 200:
            data = response.json()
            self.token = data.get("access_token")
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            self.headers = {}

    @task(10)
    def ingest_alert(self):
        """Ingest a new alert - primary task."""
        payload = generate_alert_payload()

        # Note: This endpoint needs to be created in the backend
        # Using POST /api/v1/alerts or a dedicated ingestion endpoint
        self.client.post("/api/v1/alerts/ingest", json=payload, headers=self.headers, name="POST /alerts/ingest")


# ==================== Event Handlers ====================

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Print test configuration at start."""
    print("\n" + "="*80)
    print("ERIOP Load Test Starting")
    print("="*80)
    print(f"Target host: {environment.host}")
    print(f"User classes: ERIOPDispatcher (30%), ERIOPResponder (50%), AlertIngestion (20%)")
    print(f"Target metrics:")
    print(f"  - 1000 alerts/sec throughput")
    print(f"  - 10,000 concurrent API requests")
    print(f"  - p95 latency < 200ms")
    print("="*80 + "\n")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Print test summary at completion."""
    print("\n" + "="*80)
    print("ERIOP Load Test Complete")
    print("="*80)

    stats = environment.stats
    print(f"Total requests: {stats.total.num_requests}")
    print(f"Total failures: {stats.total.num_failures}")
    print(f"Average response time: {stats.total.avg_response_time:.2f}ms")
    print(f"Max response time: {stats.total.max_response_time:.2f}ms")
    print(f"Requests/sec: {stats.total.total_rps:.2f}")

    if stats.total.num_requests > 0:
        print(f"\nResponse Time Percentiles:")
        print(f"  50th: {stats.total.get_response_time_percentile(0.5):.2f}ms")
        print(f"  75th: {stats.total.get_response_time_percentile(0.75):.2f}ms")
        print(f"  90th: {stats.total.get_response_time_percentile(0.90):.2f}ms")
        print(f"  95th: {stats.total.get_response_time_percentile(0.95):.2f}ms")
        print(f"  99th: {stats.total.get_response_time_percentile(0.99):.2f}ms")

    print("="*80 + "\n")
