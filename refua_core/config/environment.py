"""
Environment Configuration for MEDITEK Test Automation
Supports: test, preprod, prod environments with 2FA session bypass
Multi-browser support: chromium, firefox, webkit, safari
"""

import os
import logging
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
from enum import Enum
from functools import lru_cache

logger = logging.getLogger(__name__)


class EnvironmentNotSetError(Exception):
    """Raised when TEST_ENV is not set"""
    pass


class InvalidEnvironmentError(Exception):
    """Raised when TEST_ENV has invalid value"""
    pass


class BrowserType(str, Enum):
    """Supported browser types"""
    CHROMIUM = "chromium"
    FIREFOX = "firefox"
    WEBKIT = "webkit"
    SAFARI = "safari"

    @classmethod
    def values(cls) -> list[str]:
        """Get all valid browser values"""
        return [e.value for e in cls]


class EnvType(str, Enum):
    """Supported environment types"""
    TEST = "test"
    PREPROD = "preprod"
    PROD = "prod"

    @classmethod
    def values(cls) -> list[str]:
        """Get all valid environment values"""
        return [e.value for e in cls]


@dataclass(frozen=True)
class AuthConfig:
    """Authentication configuration"""
    use_2fa: bool
    bypass_2fa: bool
    session_timeout: int
    auth_method: str  # 'session_state' | 'manual'


@dataclass(frozen=True)
class Environment:
    """Environment configuration"""
    name: EnvType
    base_url: str
    api_url: str
    auth_config: AuthConfig
    session_state_dir: str = "auth_states"
    auth_state_file: Optional[str] = None  # Path to auth state JSON file

    @property
    def session_file_path(self) -> Path:
        """
        Get full path to session state file.

        Priority:
        1. auth_state_file if explicitly set (from ENV_AUTH_STATE_FILE)
        2. Default: {session_state_dir}/auth_state_{env}_chromium_latest.json
        """
        if self.auth_state_file:
            return Path(self.auth_state_file)

        filename = f"auth_state_{self.name.value}_chromium_latest.json"
        return Path(self.session_state_dir) / filename

    def can_bypass_2fa(self) -> bool:
        """Check if 2FA can be bypassed for this environment"""
        return self.auth_config.bypass_2fa and self.auth_config.auth_method == "session_state"


# Environment definitions - single source of truth
_ENV_CONFIGS: dict[EnvType, dict] = {
    EnvType.TEST: {
        "base_url": "https://meditik.test.medical.idf.il/home",
        "api_url": "https://meditik.test.medical.idf.il/api",
        "auth_config": AuthConfig(
            use_2fa=True,
            bypass_2fa=True,
            session_timeout=3600,
            auth_method="session_state"
        )
    },
    EnvType.PREPROD: {
        "base_url": "https://meditik.preprod.medical.idf.il",
        "api_url": "https://meditik.preprod.medical.idf.il/api",
        "auth_config": AuthConfig(
            use_2fa=True,
            bypass_2fa=True,
            session_timeout=3600,
            auth_method="session_state"
        )
    },
    EnvType.PROD: {
        "base_url": "https://meditik.medical.idf.il/home",
        "api_url": "https://meditik.medical.idf.il/api",
        "auth_config": AuthConfig(
            use_2fa=True,
            bypass_2fa=False,
            session_timeout=1800,
            auth_method="manual"
        )
    }
}


class EnvironmentManager:
    """
    Centralized environment management.
    Singleton pattern for consistent state across tests.
    """
    
    _instance: Optional['EnvironmentManager'] = None
    
    def __new__(cls) -> 'EnvironmentManager':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return

        self._current_env = self._resolve_env_from_system()
        self._session_states_dir = self._resolve_session_dir()
        self._session_states_dir.mkdir(parents=True, exist_ok=True)
        self._auth_state_file = self._resolve_auth_state_file()
        self._initialized = True

        logger.info(f"EnvironmentManager initialized: {self._current_env.value}")
        logger.debug(f"Session directory: {self._session_states_dir}")
        if self._auth_state_file:
            logger.debug(f"Auth state file: {self._auth_state_file}")
    
    def _resolve_env_from_system(self) -> EnvType:
        """
        Resolve environment from TEST_ENV variable.
        Raises error if not set or invalid.
        """
        env_str = os.getenv("TEST_ENV")

        # Require explicit environment
        if env_str is None:
            raise EnvironmentNotSetError(
                "TEST_ENV environment variable is required.\n"
                f"Valid values: {EnvType.values()}\n"
                "Example: TEST_ENV=test pytest tests/"
            )

        env_str = env_str.lower().strip()

        # Validate environment value
        if env_str not in EnvType.values():
            raise InvalidEnvironmentError(
                f"Invalid TEST_ENV value: '{env_str}'\n"
                f"Valid values: {EnvType.values()}"
            )

        return EnvType(env_str)

    def _resolve_session_dir(self) -> Path:
        """
        Resolve session storage directory from environment.

        Priority:
        1. SESSION_DIR environment variable (if set)
        2. Default: ~/.refua_sessions/ (external, outside project)

        Expands ~ to home directory. Creates directory if it doesn't exist.
        Must be outside project directory for security and portability.
        """
        session_dir = os.getenv("SESSION_DIR")

        if session_dir:
            # Use custom session directory from environment
            session_path = Path(session_dir).expanduser().resolve()
            logger.debug(f"Using custom session directory: {session_path}")
        else:
            # Use default external session directory
            session_path = Path.home() / ".refua_sessions"
            logger.debug(f"Using default session directory: {session_path}")

        return session_path

    def _resolve_auth_state_file(self) -> Optional[str]:
        """
        Resolve authentication state file path from environment variables.

        Priority (for each environment):
        1. {ENV}_AUTH_STATE_FILE env variable (e.g., TEST_AUTH_STATE_FILE)
        2. {ENV}_AUTH_STATE_{BROWSER} for specific browser (e.g., TEST_AUTH_STATE_CHROMIUM)
        3. None (use default session file path)

        Supports:
        - Absolute paths: C:\path\to\file.json or /path/to/file.json
        - Home directory: ~/auth_states/file.json
        - Environment variables: ${VAR_NAME}/file.json or $VAR_NAME/file.json

        Docker-compatible:
        - Can use /app/ paths for Docker containers
        - Can use environment variable substitution
        """
        env_name = self._current_env.value.upper()

        # Try environment-specific auth state file variable
        auth_state_file = os.getenv(f"{env_name}_AUTH_STATE_FILE")

        if auth_state_file:
            # Expand environment variables and home directory
            expanded_path = os.path.expandvars(auth_state_file)
            expanded_path = os.path.expanduser(expanded_path)
            logger.debug(f"Resolved auth state file: {expanded_path}")
            return expanded_path

        # Try browser-specific auth state file variable
        browser = self.get_browser_type().upper()
        browser_var = f"{env_name}_AUTH_STATE_{browser}"
        auth_state_file = os.getenv(browser_var)

        if auth_state_file:
            expanded_path = os.path.expandvars(auth_state_file)
            expanded_path = os.path.expanduser(expanded_path)
            logger.debug(f"Resolved browser-specific auth state file: {expanded_path}")
            return expanded_path

        return None

    @lru_cache(maxsize=3)
    def get_environment(self, env_type: Optional[EnvType] = None) -> Environment:
        """Get environment configuration (cached)"""
        env_type = env_type or self._current_env

        if env_type is None:
            raise EnvironmentNotSetError("Environment type is required")

        config = _ENV_CONFIGS[env_type]

        # Use auth_state_file if resolved during initialization
        # Otherwise, it will use the default session file path
        auth_state_file = self._auth_state_file if env_type == self._current_env else None

        return Environment(
            name=env_type,
            base_url=config["base_url"],
            api_url=config["api_url"],
            auth_config=config["auth_config"],
            session_state_dir=str(self._session_states_dir),
            auth_state_file=auth_state_file
        )
    
    @property
    def current_env(self) -> EnvType:
        """Get current environment type"""
        return self._current_env
    
    @current_env.setter
    def current_env(self, env_type: EnvType):
        """Set current environment"""
        if env_type is None:
            raise ValueError("Environment type cannot be None")
        
        if not isinstance(env_type, EnvType):
            raise TypeError(f"Expected EnvType, got {type(env_type)}")
        
        self._current_env = env_type
        self.get_environment.cache_clear()
        logger.info(f"Environment switched to: {env_type.value}")
    
    def get_base_url(self, env_type: Optional[EnvType] = None) -> str:
        """Get base URL for environment"""
        return self.get_environment(env_type).base_url
    
    def get_api_url(self, env_type: Optional[EnvType] = None) -> str:
        """Get API URL for environment"""
        return self.get_environment(env_type).api_url
    
    def should_bypass_2fa(self, env_type: Optional[EnvType] = None) -> bool:
        """Check if 2FA should be bypassed"""
        return self.get_environment(env_type).can_bypass_2fa()
    
    def get_session_dir(self) -> Path:
        """Get session storage directory (external, outside project)"""
        return self._session_states_dir

    @staticmethod
    def get_browser_type() -> str:
        """
        Get browser type from environment or use default.

        Priority:
        1. BROWSER environment variable (chromium, firefox, webkit, safari)
        2. Default: chromium

        Returns:
            Browser type: chromium, firefox, webkit, or safari

        Example:
            BROWSER=firefox TEST_ENV=test pytest tests/
        """
        browser = os.getenv("BROWSER", "chromium").lower().strip()

        if browser not in BrowserType.values():
            logger.warning(
                f"Unsupported browser: {browser}. "
                f"Supported: {BrowserType.values()}. Using chromium."
            )
            return "chromium"

        return browser

    def get_session_file_path(self, env_type: Optional[EnvType] = None) -> Path:
        """Get path to session state file"""
        return self.get_environment(env_type).session_file_path

    def get_auth_state_file(self, env_type: Optional[EnvType] = None) -> Optional[str]:
        """
        Get authentication state file path.

        Returns:
            - Resolved auth state file path if {ENV}_AUTH_STATE_FILE is set
            - None otherwise (will use default session file path)
        """
        return self.get_environment(env_type).auth_state_file

    def get_session_timeout(self, env_type: Optional[EnvType] = None) -> int:
        """Get session timeout in seconds"""
        return self.get_environment(env_type).auth_config.session_timeout
    
    def is_production(self, env_type: Optional[EnvType] = None) -> bool:
        """Check if environment is production"""
        env = env_type or self._current_env
        return env == EnvType.PROD
    
    def get_env_summary(self) -> str:
        """Get human-readable environment summary"""
        env = self.get_environment()
        session_exists = env.session_file_path.exists()
        session_dir = self.get_session_dir()

        return (
            f"\n{'='*60}\n"
            f"Environment: {env.name.value.upper()}\n"
            f"Base URL: {env.base_url}\n"
            f"API URL: {env.api_url}\n"
            f"2FA Bypass: {'Enabled' if env.can_bypass_2fa() else 'Disabled'}\n"
            f"Session Timeout: {env.auth_config.session_timeout}s\n"
            f"Session Directory: {session_dir}\n"
            f"Session File: {env.session_file_path}\n"
            f"Session Exists: {'Yes' if session_exists else 'No'}\n"
            f"{'='*60}"
        )
    
    @classmethod
    def reset_instance(cls):
        """Reset singleton instance (useful for testing)"""
        cls._instance = None


def get_env_manager() -> EnvironmentManager:
    """Get singleton EnvironmentManager instance"""
    return EnvironmentManager()


def validate_environment():
    """
    Validate environment setup before tests run.
    Call this early to fail fast if misconfigured.
    """
    try:
        manager = get_env_manager()
        env = manager.get_environment()
        
        # Validate session file exists if bypass is enabled
        if env.can_bypass_2fa() and not env.session_file_path.exists():
            logger.warning(
                f"2FA bypass enabled but session file missing: {env.session_file_path}\n"
                "Run session capture script first or disable 2FA bypass."
            )
        
        return True
        
    except (EnvironmentNotSetError, InvalidEnvironmentError) as e:
        logger.error(str(e))
        raise