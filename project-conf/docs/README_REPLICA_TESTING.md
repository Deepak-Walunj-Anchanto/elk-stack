# Read Replica Testing Guide

This guide explains how to test the read replica functionality in the multi-tenant Django application using **pytest**.

## Overview

The application now supports read replicas for each tenant, which allows:

- **Read operations** → Automatically routed to replica databases (load balanced)
- **Write operations** → Always routed to primary database (data consistency)
- **Fallback behavior** → Uses primary if no replicas configured

## Test Environment Setup

### 1. Docker Compose Setup

The test environment includes:

- `postgres` (port 5432) - Primary database
- `postgres-replica` (port 5433) - Simulated read replica
- `django` - Application container
- `redis` - Cache/session storage

Start the test environment:

```bash
docker-compose -f docker-compose.test.yml up -d
```

### 2. Database Configuration

Test databases are configured with replica support in `config/settings/base.py`:

```json
{
  "default": {
    "HOST": "postgres",
    "PORT": 5432,
    "replicas": [
      {
        "HOST": "postgres-replica",
        "PORT": 5432,  # Internal port
        "USER": "readonly_user"
      }
    ]
  }
}
```

## Running Tests with Pytest

### 1. Complete Test Suite

Run all tests:

```bash
# Run all tests with coverage
docker-compose -f docker-compose.test.yml run django pytest -v

# Run tests with coverage report
docker-compose -f docker-compose.test.yml run django pytest --cov=apps.tenant_manager
```

### 2. Tenant Manager Specific Tests

Run only tenant manager tests:

```bash
# All tenant manager tests
docker-compose -f docker-compose.test.yml run django pytest -v apps/tenant_manager/tests.py

# Specific test classes
docker-compose -f docker-compose.test.yml run django pytest -v apps/tenant_manager/tests.py::TestTenantContext
docker-compose -f docker-compose.test.yml run django pytest -v apps/tenant_manager/tests.py::TestTenantDatabaseRouter
docker-compose -f docker-compose.test.yml run django pytest -v apps/tenant_manager/tests.py::TestIntegration
```

### 3. Using Pytest Markers

Run tests by category:

```bash
# Run only tenant manager related tests
docker-compose -f docker-compose.test.yml run django pytest -m tenant_manager

# Run integration tests only
docker-compose -f docker-compose.test.yml run django pytest -m integration

# Skip slow tests
docker-compose -f docker-compose.test.yml run django pytest -m "not slow"

# Run only replica-related tests
docker-compose -f docker-compose.test.yml run django pytest -m replica
```

### 4. Parametrized Tests

The tests include parametrized test cases for comprehensive coverage:

```bash
# Test ID normalization with multiple scenarios
docker-compose -f docker-compose.test.yml run django pytest -v apps/tenant_manager/tests.py::TestTenantContext::test_from_id_normalization

# Test error handling with various exception types
docker-compose -f docker-compose.test.yml run django pytest -v apps/tenant_manager/tests.py::TestTenantDatabaseRouter::test_routing_with_context_errors

# Test load balancing with different replica counts
docker-compose -f docker-compose.test.yml run django pytest -v apps/tenant_manager/tests.py::TestIntegration::test_replica_load_balancing
```

### 5. Manual Testing Command

Use the custom management command to test in real environment:

```bash
# Test with default tenant
docker-compose -f docker-compose.test.yml run django python manage.py test_replica_routing

# Test with specific tenant
docker-compose -f docker-compose.test.yml run django python manage.py test_replica_routing --tenant-id localhost

# Test with more iterations for load balancing
docker-compose -f docker-compose.test.yml run django python manage.py test_replica_routing --tenant-id localhost --iterations 20
```

## Pytest Features Used

### 1. Fixtures

The tests use pytest fixtures for clean, reusable test data:

```python
@pytest.fixture
def tenant_context_with_replicas():
    """Fixture providing tenant context with replicas."""
    return TenantContext(
        "test-tenant",
        "test_tenant",
        ["test_tenant_replica_1", "test_tenant_replica_2"]
    )

def test_read_routing_with_replicas(database_router, tenant_context_with_replicas):
    """Test using fixture for clean setup."""
    # Test implementation
```

### 2. Parametrized Tests

Multiple test scenarios with single test function:

```python
@pytest.mark.parametrize("tenant_id,expected_alias", [
    ("test.tenant-id", "test_tenant_id"),
    ("simple", "simple"),
    ("complex-tenant.name", "complex_tenant_name"),
])
def test_from_id_normalization(self, tenant_id, expected_alias):
    """Test multiple ID normalization scenarios."""
```

### 3. Markers

Custom markers for test organization:

```python
@pytest.mark.django_db
class TestTenantDatabaseRouter:
    """Database tests with automatic DB access."""

@pytest.mark.parametrize("error_scenario", [...])
def test_graceful_degradation_on_various_errors(self, error_scenario):
    """Test error handling scenarios."""
```

### 4. Assertions

Clean pytest-style assertions:

```python
# Pytest style (used)
assert context.id == "test-tenant"
assert result in expected_values

# Django TestCase style (not used)
# self.assertEqual(context.id, "test-tenant")
# self.assertIn(result, expected_values)
```

## Test Cases Covered

### 1. TenantContext Tests

- ✅ Context creation with/without replicas (fixtures)
- ✅ Read alias selection (replica vs primary)
- ✅ Write alias always returns primary
- ✅ ID normalization (parametrized)
- ✅ Load balancing across multiple replicas

### 2. Database Router Tests

- ✅ Read routing to replicas when available
- ✅ Read routing fallback to primary
- ✅ Write routing always to primary
- ✅ Error handling (parametrized exception types)
- ✅ Routing history tracking
- ✅ Celery beat model routing

### 3. ORM Manager Tests

- ✅ Replica config inheritance from primary
- ✅ Multiple replica registration
- ✅ Tenant replica alias mapping (parametrized)

### 4. Integration Tests

- ✅ End-to-end routing flow
- ✅ Load balancing verification (parametrized)
- ✅ Error handling and fallbacks

### 5. Context Management Tests

- ✅ Decorator and context manager functionality
- ✅ Proper context push/pop operations
- ✅ Error handling in context binding

## Pytest Configuration

### pytest.ini

```ini
[tool:pytest]
DJANGO_SETTINGS_MODULE = config.settings.local
python_files = tests.py test_*.py *_tests.py *test*.py
addopts = --cov --cov-report term-missing --tb=short --strict-markers
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    tenant_manager: marks tests as tenant manager related
    integration: marks tests as integration tests
    replica: marks tests as read replica related
    django_db: marks tests that require database access
```

### conftest.py Features

- Automatic Django setup
- Database access for all tests
- Tenant context cleanup after each test
- Custom marker registration

## CI Integration

The GitHub Actions workflow includes specific read replica testing:

```yaml
- name: Test Tenant Manager Read Replica Functionality
  run: |
    docker compose -f docker-compose.test.yml run django pytest -v apps/tenant_manager/tests.py::TestTenantContext -m "not slow"
    docker compose -f docker-compose.test.yml run django pytest -v apps/tenant_manager/tests.py::TestTenantDatabaseRouter -m "not slow"
    docker compose -f docker-compose.test.yml run django pytest -v apps/tenant_manager/tests.py::TestIntegration -m "not slow"

- name: Test Read Replica Routing Command
  run: |
    docker compose -f docker-compose.test.yml run django python manage.py test_replica_routing --tenant-id default --iterations 20
```

## Debugging with Pytest

### 1. Verbose Output

```bash
# See detailed test output
docker-compose -f docker-compose.test.yml run django pytest -v -s

# See test duration
docker-compose -f docker-compose.test.yml run django pytest --durations=10
```

### 2. Debugging Failed Tests

```bash
# Stop on first failure
docker-compose -f docker-compose.test.yml run django pytest -x

# Enter debugger on failure (if pdb available)
docker-compose -f docker-compose.test.yml run django pytest --pdb
```

### 3. Test Discovery

```bash
# List all tests without running
docker-compose -f docker-compose.test.yml run django pytest --collect-only

# Show available markers
docker-compose -f docker-compose.test.yml run django pytest --markers
```

## Verifying Read Replica Functionality

### 1. Quick Verification

```bash
# Run key integration tests
docker-compose -f docker-compose.test.yml run django pytest -v apps/tenant_manager/tests.py::TestIntegration::test_end_to_end_replica_routing

# Test load balancing
docker-compose -f docker-compose.test.yml run django pytest -v apps/tenant_manager/tests.py::TestIntegration::test_replica_load_balancing
```

### 2. Check Routing History

```python
from apps.tenant_manager.database_router import TenantDatabaseRouter
router = TenantDatabaseRouter()
history = router.get_routing_history()
for decision in history:
    print(f"{decision['operation']} -> {decision['alias']}")
```

### 3. Manual Test in Shell

```bash
docker-compose -f docker-compose.test.yml run django python manage.py shell

# In shell:
from apps.tenant_manager.with_tenant_context import tenant_context_bind
from apps.tenant_manager.database_router import TenantDatabaseRouter
from django.contrib.auth.models import User

router = TenantDatabaseRouter()
with tenant_context_bind('default'):
    read_db = router.db_for_read(User)   # Should use replica
    write_db = router.db_for_write(User) # Should use primary
    print(f"Read: {read_db}, Write: {write_db}")
```

## Performance Testing with Pytest

### 1. Timing Tests

```python
import pytest
import time

@pytest.mark.slow
def test_load_balancing_performance():
    """Test load balancing performance over many operations."""
    start_time = time.time()
    # Perform many routing operations
    duration = time.time() - start_time
    assert duration < 1.0  # Should complete in under 1 second
```

### 2. Memory Usage

```bash
# Run with memory profiling (if memory_profiler installed)
docker-compose -f docker-compose.test.yml run django pytest --profile-svg
```

## Common Pytest Patterns

### 1. Setup and Teardown

```python
class TestSomething:
    def setup_method(self):
        """Run before each test method."""
        self.router = TenantDatabaseRouter()

    def teardown_method(self):
        """Run after each test method."""
        self.router.clear_routing_history()
```

### 2. Skipping Tests

```python
@pytest.mark.skip(reason="Feature not implemented yet")
def test_future_feature():
    pass

@pytest.mark.skipif(condition, reason="Skip on certain conditions")
def test_conditional():
    pass
```

### 3. Expected Failures

```python
@pytest.mark.xfail(reason="Known issue with load balancing")
def test_load_balancing_edge_case():
    # Test that's expected to fail
    pass
```

This comprehensive pytest setup ensures your read replica functionality is thoroughly tested with modern Python testing practices!
