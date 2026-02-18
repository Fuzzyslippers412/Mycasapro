# MyCasa Pro Test Suite

Comprehensive test suite for MyCasa Pro with 70%+ target coverage.

## Directory Structure

```
tests/
├── unit/                   # Unit tests (fast, isolated)
│   ├── test_agents/       # Agent functionality tests
│   ├── test_connectors/   # Connector tests (mocked external services)
│   ├── test_core/         # Core functionality tests
│   └── test_api/          # API route tests
├── integration/           # Integration tests (agent coordination, workflows)
├── e2e/                   # End-to-end tests (full user workflows)
├── fixtures/              # Test data and utilities
└── conftest.py            # Shared fixtures and configuration
```

## Running Tests

### Run all tests
```bash
pytest
```

### Run with coverage report
```bash
pytest --cov=. --cov-report=html
```

### Run specific test categories
```bash
# Unit tests only (fast)
pytest -m unit

# Integration tests
pytest -m integration

# End-to-end tests
pytest -m e2e

# Agent-specific tests
pytest -m agent

# API tests
pytest -m api
```

### Run specific test files
```bash
# Test a specific file
pytest tests/unit/test_agents/test_manager.py

# Test a specific class
pytest tests/unit/test_agents/test_manager.py::TestManagerAgentInitialization

# Test a specific function
pytest tests/unit/test_agents/test_manager.py::TestManagerAgentInitialization::test_agent_initializes_with_session
```

### Run tests with verbose output
```bash
pytest -v
```

### Run tests in parallel (requires pytest-xdist)
```bash
pip install pytest-xdist
pytest -n auto
```

## Test Markers

Tests are organized using pytest markers:

- `@pytest.mark.unit` - Fast, isolated unit tests
- `@pytest.mark.integration` - Integration tests with multiple components
- `@pytest.mark.e2e` - End-to-end workflow tests
- `@pytest.mark.slow` - Slow-running tests
- `@pytest.mark.agent` - Agent functionality tests
- `@pytest.mark.connector` - Connector tests
- `@pytest.mark.api` - API route tests
- `@pytest.mark.secondbrain` - SecondBrain/knowledge management tests
- `@pytest.mark.security` - Security/authentication tests
- `@pytest.mark.database` - Tests requiring database access

## Writing Tests

### Test File Naming
- Unit tests: `test_<module>.py`
- Test classes: `Test<Feature>`
- Test functions: `test_<description>`

### Using Fixtures

Common fixtures available in `conftest.py`:

```python
def test_example(db_session, api_client, sample_property):
    """Test with database session, API client, and sample data."""
    # db_session - Database session
    # api_client - FastAPI TestClient
    # sample_property - Sample property fixture
    pass
```

### Example Unit Test

```python
import pytest

@pytest.mark.unit
@pytest.mark.agent
def test_agent_initialization(db_session):
    """Test agent initializes correctly."""
    from agents.manager import ManagerAgent

    agent = ManagerAgent(db_session, tenant_id="test-tenant")
    assert agent.tenant_id == "test-tenant"
```

### Example Integration Test

```python
import pytest

@pytest.mark.integration
@pytest.mark.agent
def test_agent_coordination(all_agents, db_session):
    """Test multiple agents working together."""
    manager = all_agents["manager"]
    finance = all_agents["finance"]

    # Test coordination logic
    pass
```

## Coverage Reports

After running tests with coverage:

```bash
pytest --cov=. --cov-report=html
```

Open `htmlcov/index.html` in your browser to view the coverage report.

### Coverage Goals

- **Overall**: 70%+ coverage
- **Agents**: 80%+ coverage (core business logic)
- **API Routes**: 85%+ coverage
- **Core Utilities**: 75%+ coverage
- **Connectors**: 60%+ coverage (many rely on external services)

## Continuous Integration

Tests are designed to run in CI/CD pipelines. Key considerations:

1. **Fast Execution**: Unit tests complete in <30 seconds
2. **Isolated**: Tests use in-memory SQLite, no external dependencies
3. **Deterministic**: No flaky tests, consistent results
4. **Parallel**: Can run tests in parallel safely

## Troubleshooting

### Import Errors

If you get import errors, ensure you're running from the project root:

```bash
cd /path/to/mycasa-pro
pytest
```

### Database Issues

Tests use in-memory SQLite. If you see database errors:

```bash
# Recreate virtual environment
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Async Test Issues

If async tests fail:

```bash
# Ensure pytest-asyncio is installed
pip install pytest-asyncio

# Check pytest.ini has asyncio_mode = auto
```

### Coverage Not Working

```bash
# Reinstall pytest-cov
pip install --upgrade pytest-cov

# Run with explicit coverage config
pytest --cov=. --cov-config=.coveragerc
```

## Best Practices

1. **Keep Tests Fast**: Unit tests should complete in milliseconds
2. **One Assert Per Test**: Tests should verify one specific behavior
3. **Use Descriptive Names**: Test names should describe what they verify
4. **Mock External Services**: Don't call real APIs in tests
5. **Clean Up**: Use fixtures for setup/teardown
6. **Test Edge Cases**: Don't just test the happy path
7. **Avoid Test Interdependence**: Each test should be independent

## Adding New Tests

When adding new features:

1. Write tests first (TDD approach)
2. Add unit tests for new functions/classes
3. Add integration tests for workflows
4. Update fixtures if new data types are needed
5. Run full test suite before committing

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Pytest-asyncio Documentation](https://pytest-asyncio.readthedocs.io/)
- [FastAPI Testing Documentation](https://fastapi.tiangolo.com/tutorial/testing/)
- [SQLAlchemy Testing Documentation](https://docs.sqlalchemy.org/en/14/orm/session_transaction.html#joining-a-session-into-an-external-transaction-such-as-for-test-suites)
