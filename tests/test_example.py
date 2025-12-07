"""
Example test case for P1.2 validation
Tests basic BaseTest functionality
"""

import pytest
from refua_core.core.base_test import BaseTest


@pytest.mark.smoke
class TestExample(BaseTest):
    """Example test class demonstrating BaseTest usage"""

    def test_environment_configured(self):
        """Test that environment is properly configured"""
        assert self.env_mgr is not None
        assert self.page is not None
        assert self.context is not None

    def test_base_url_available(self):
        """Test that base URL is available"""
        base_url = self.env_mgr.get_base_url()
        assert base_url is not None
        assert "meditik" in base_url.lower()

    def test_environment_not_production(self):
        """Test environment detection"""
        # Tests run on test environment
        assert not self.is_production()

    def test_session_directory_exists(self):
        """Test session directory configuration"""
        session_dir = self.get_session_dir()
        assert session_dir is not None
        # Note: Directory may not exist until session captured


@pytest.mark.smoke
def test_with_fixtures(page, env_manager):
    """Test using fixtures instead of BaseTest class"""
    assert page is not None
    assert env_manager is not None
    
    base_url = env_manager.get_base_url()
    assert base_url is not None
