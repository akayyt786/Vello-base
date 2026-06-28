import pytest

# Make pytest-asyncio auto-mode work for async test methods
def pytest_configure(config):
    config.addinivalue_line("markers", "asyncio: mark test as async")
