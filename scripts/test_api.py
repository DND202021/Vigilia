#!/usr/bin/env python3
"""
ERIOP API Test Suite
Run: python scripts/test_api.py [base_url]
"""

import sys
import json
import httpx
from dataclasses import dataclass
from typing import Any


@dataclass
class TestResult:
    name: str
    passed: bool
    status_code: int
    message: str = ""


class APITester:
    def __init__(self, base_url: str = "http://10.0.0.13:83"):
        self.base_url = base_url.rstrip("/")
        self.api_url = f"{self.base_url}/api/v1"
        self.token: str | None = None
        self.results: list[TestResult] = []
        self.created_incident_id: str | None = None
        self.client = httpx.Client(timeout=30.0)

    def _request(
        self,
        method: str,
        endpoint: str,
        data: dict | None = None,
        expected_status: int = 200,
        auth: bool = True,
    ) -> tuple[int, dict | str]:
        """Make API request and return (status_code, response_data)."""
        headers = {"Content-Type": "application/json"}
        if auth and self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        url = f"{self.api_url}{endpoint}"
        try:
            resp = self.client.request(
                method,
                url,
                json=data,
                headers=headers,
            )
            try:
                return resp.status_code, resp.json()
            except json.JSONDecodeError:
                return resp.status_code, resp.text
        except httpx.RequestError as e:
            return 0, str(e)

    def test(
        self,
        name: str,
        method: str,
        endpoint: str,
        data: dict | None = None,
        expected_status: int = 200,
        auth: bool = True,
    ) -> dict | str | None:
        """Run a test and record result."""
        status, response = self._request(method, endpoint, data, expected_status, auth)
        passed = status == expected_status

        result = TestResult(
            name=name,
            passed=passed,
            status_code=status,
            message=str(response)[:200] if not passed else "",
        )
        self.results.append(result)

        symbol = "✓" if passed else "✗"
        print(f"  {symbol} {name} (HTTP {status})")
        if not passed:
            print(f"    Expected: {expected_status}, Got: {status}")
            print(f"    Response: {result.message}")

        return response if passed else None

    def run_all_tests(self):
        """Run complete test suite."""
        print("=" * 50)
        print("ERIOP API Test Suite")
        print(f"Base URL: {self.base_url}")
        print("=" * 50)

        # Health check
        print("\n[Health Check]")
        resp = self.client.get(f"{self.base_url}/health")
        if resp.status_code == 200:
            print(f"  ✓ Health check passed")
            self.results.append(TestResult("Health", True, 200))
        else:
            print(f"  ✗ Health check failed (HTTP {resp.status_code})")
            self.results.append(TestResult("Health", False, resp.status_code))
            return

        # Authentication
        print("\n[Authentication]")
        response = self.test(
            "Login",
            "POST",
            "/auth/login",
            {"email": "admin@vigilia.com", "password": "admin123"},
            auth=False,
        )
        if response and isinstance(response, dict):
            self.token = response.get("access_token")
            if self.token:
                print(f"    Token acquired: {self.token[:30]}...")

        if not self.token:
            print("  ✗ Failed to acquire token, stopping tests")
            return

        self.test("Get current user", "GET", "/auth/me")

        # Incidents
        print("\n[Incidents]")

        # Create incident
        incident_data = {
            "category": "medical",
            "priority": 2,
            "title": "API Test Medical Emergency",
            "description": "Automated test incident",
            "location": {
                "latitude": 45.5088,
                "longitude": -73.5878,
                "address": "456 Test Avenue, Montreal",
            },
        }
        response = self.test(
            "Create incident",
            "POST",
            "/incidents",
            incident_data,
            expected_status=201,
        )
        if response and isinstance(response, dict):
            self.created_incident_id = response.get("id")
            print(f"    Created: {self.created_incident_id}")

        # List incidents
        response = self.test("List incidents", "GET", "/incidents")
        if response and isinstance(response, dict):
            print(f"    Total: {response.get('total', 0)}")

        # Get by ID
        if self.created_incident_id:
            self.test(
                "Get incident by ID",
                "GET",
                f"/incidents/{self.created_incident_id}",
            )

            # Update incident
            self.test(
                "Update incident status",
                "PATCH",
                f"/incidents/{self.created_incident_id}",
                {"status": "assigned"},
            )

        # Active incidents
        self.test("List active incidents", "GET", "/incidents/active")

        # Resources
        print("\n[Resources]")
        self.test("List resources", "GET", "/resources")
        self.test("List available resources", "GET", "/resources/available")

        # Alerts
        print("\n[Alerts]")
        self.test("List alerts", "GET", "/alerts")
        self.test("List unacknowledged alerts", "GET", "/alerts/unacknowledged")

        # Dashboard
        print("\n[Dashboard]")
        self.test("Get dashboard stats", "GET", "/dashboard/stats")

        # Summary
        print("\n" + "=" * 50)
        passed = sum(1 for r in self.results if r.passed)
        total = len(self.results)
        print(f"Results: {passed}/{total} tests passed")

        if passed == total:
            print("✓ All tests passed!")
            return 0
        else:
            print("✗ Some tests failed")
            for r in self.results:
                if not r.passed:
                    print(f"  - {r.name}: HTTP {r.status_code}")
            return 1


def main():
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://10.0.0.13:83"
    tester = APITester(base_url)
    sys.exit(tester.run_all_tests())


if __name__ == "__main__":
    main()
