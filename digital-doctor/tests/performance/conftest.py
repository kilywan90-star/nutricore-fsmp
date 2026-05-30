"""
Locust configuration for digital-doctor performance testing.

Usage:
    cd digital-doctor
    locust -f tests/performance/locustfile.py --host=http://localhost:8000
"""

# Host will be overridden by --host CLI flag or set in Locust web UI.
# Default for local development.
host = "http://localhost:8000"

# Wait between 1 and 3 seconds between tasks to simulate realistic user pacing.
wait_time = None  # Set in locustfile.py via wait_time attribute on HttpUser classes
