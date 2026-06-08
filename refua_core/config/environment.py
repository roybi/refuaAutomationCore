"""Environment configuration for MEDITEK test automation."""

import logging
import os
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class EnvironmentNotSetError(Exception):
    """Raised when TEST_ENV is not set"""

    pass


class InvalidEnvironmentError(Exception):
    """Raised when TEST_ENV has invalid value"""

    pass


class UnknownAppError(Exception):
    """Raised when TEST_APP references an unregistered application"""

    pass


class BrowserType(str, Enum):
    """Supported browser types"""

    CHROMIUM = "chromium"
    FIREFOX = "firefox"
    WEBKIT = "webkit"
    SAFARI = "safari"

    @classmethod
    def values(cls) -> list[str]:
        return [e.value for e in cls]


class EnvType(str, Enum):
    """Supported environment types"""

    TEST = "test"
    PREPROD = "preprod"
    PROD = "prod"

    @classmethod
    def values(cls) -> list[str]:
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
    app: str
    base_url: str
    api_url: str
    auth_config: AuthConfig
    session_state_dir: str = "auth_states"
    auth_state_file: Optional[str] = None  # Path to auth state JSON file

    @property
    def session_file_path(self) -> Path:
        """Path to session file. Uses auth_state_file override if set, otherwise default name."""
        if self.auth_state_file:
            return Path(self.auth_state_file)

        # Browser resolved dynamically; EnvironmentManager.get_session_file_path() is preferred
        filename = f"auth_state_{self.app}_{self.name.value}_chromium_latest.json"
        return Path(self.session_state_dir) / filename

    def can_bypass_2fa(self) -> bool:
        return (
            self.auth_config.bypass_2fa
            and self.auth_config.auth_method == "session_state"
        )


# Application registry: app_name → {EnvType → {base_url, api_url, auth_config}}
# Register additional apps via EnvironmentManager.register_app() before instantiation.
_APP_REGISTRY: dict[str, dict[EnvType, dict]] = {
    "meditek": {
        EnvType.TEST: {
            "base_url": "https://meditik.test.medical.idf.il/home",
            "api_url": "https://meditik.test.medical.idf.il/api",
            "auth_config": AuthConfig(
                use_2fa=True,
                bypass_2fa=True,
                session_timeout=3600,
                auth_method="session_state",
            ),
        },
        EnvType.PREPROD: {
            "base_url": "https://meditik.preprod.medical.idf.il",
            "api_url": "https://meditik.preprod.medical.idf.il/api",
            "auth_config": AuthConfig(
                use_2fa=True,
                bypass_2fa=True,
                session_timeout=3600,
                auth_method="session_state",
            ),
        },
        EnvType.PROD: {
            "base_url": "https://meditik.medical.idf.il/home",
            "api_url": "https://meditik.medical.idf.il/api",
            "auth_config": AuthConfig(
                use_2fa=True,
                bypass_2fa=False,
                session_timeout=1800,
                auth_method="manual",
            ),
        },
    },
    "cpr-go": {
        EnvType.TEST: {
            "base_url": "https://cpr-go.test.medical.idf.il",
            "api_url": "https://cpr-go.test.medical.idf.il/api",
            "auth_config": AuthConfig(
                use_2fa=True,
                bypass_2fa=True,
                session_timeout=3600,
                auth_method="session_state",
            ),
        },
        EnvType.PREPROD: {
            "base_url": "https://cpr-go.preprod.medical.idf.il",
            "api_url": "https://cpr-go.preprod.medical.idf.il/api",
            "auth_config": AuthConfig(
                use_2fa=True,
                bypass_2fa=True,
                session_timeout=3600,
                auth_method="session_state",
            ),
        },
        EnvType.PROD: {
            "base_url": "https://cpr-go.medical.idf.il",
            "api_url": "https://cpr-go.medical.idf.il/api",
            "auth_config": AuthConfig(
                use_2fa=True,
                bypass_2fa=False,
                session_timeout=1800,
                auth_method="manual",
            ),
        },
    },
}


class EnvironmentManager:
    """
    Centralized environment management.
    Singleton pattern for consistent state across tests.
    """

    _instance: Optional["EnvironmentManager"] = None

    def __new__(cls) -> "EnvironmentManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._current_app = self._resolve_app_from_system()
        self._current_env = self._resolve_env_from_system()
        self._session_states_dir = self._resolve_session_dir()
        self._session_states_dir.mkdir(parents=True, exist_ok=True)
        self._auth_state_file = self._resolve_auth_state_file()
        self._initialized = True

        logger.info(
            f"EnvironmentManager initialized: app={self._current_app} env={self._current_env.value}"
        )
        logger.debug(f"Session directory: {self._session_states_dir}")
        if self._auth_state_file:
            logger.debug(f"Auth state file: {self._auth_state_file}")

    @classmethod
    def register_app(cls, app_name: str, configs: dict) -> None:
        """Register a custom application in the app registry.

        Call this before EnvironmentManager is first instantiated (e.g. in conftest.py).

        Args:
            app_name: Identifier used in TEST_APP (e.g. "my-app")
            configs: Mapping of EnvType → {base_url, api_url, auth_config}
        """
        _APP_REGISTRY[app_name] = configs
        logger.debug(f"Registered app: {app_name}")

    def _resolve_app_from_system(self) -> str:
        """Resolve app name from TEST_APP; default to 'meditek' for backward compatibility."""
        app_str = os.getenv("TEST_APP", "meditek").lower().strip()

        if app_str not in _APP_REGISTRY:
            raise UnknownAppError(
                f"Unknown TEST_APP value: '{app_str}'\n"
                f"Known apps: {list(_APP_REGISTRY.keys())}\n"
                "Register custom apps with EnvironmentManager.register_app() before use."
            )

        return app_str

    def _resolve_env_from_system(self) -> EnvType:
        """Resolve EnvType from TEST_ENV; raise if missing or invalid."""
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
                f"Invalid TEST_ENV value: '{env_str}'\nValid values: {EnvType.values()}"
            )

        return EnvType(env_str)

    def _resolve_session_dir(self) -> Path:
        """Resolve where session files are stored.

        Priority order:
          1. SESSION_DIR env var — explicit override, always wins
          2. GitHub Actions  — $GITHUB_WORKSPACE/sessions
          3. Jenkins         — $WORKSPACE/sessions
          4. Local default   — ~/.refua_sessions
        """
        # 1. Explicit override
        if session_dir := os.getenv("SESSION_DIR"):
            session_path = Path(session_dir).expanduser().resolve()
            logger.debug("Session dir (SESSION_DIR): %s", session_path)
            return session_path

        # 2. GitHub Actions
        if github_ws := os.getenv("GITHUB_WORKSPACE"):
            session_path = Path(github_ws) / "sessions"
            logger.debug("Session dir (GitHub Actions): %s", session_path)
            return session_path

        # 3. Jenkins
        if jenkins_ws := os.getenv("WORKSPACE"):
            session_path = Path(jenkins_ws) / "sessions"
            logger.debug("Session dir (Jenkins): %s", session_path)
            return session_path

        # 4. Local development default
        session_path = Path.home() / ".refua_sessions"
        logger.debug("Session dir (local default): %s", session_path)
        return session_path

    def _resolve_auth_state_file(self) -> Optional[str]:
        """
        Resolve session file override from env vars.
        Priority: {ENV}_AUTH_STATE_FILE → {ENV}_AUTH_STATE_{BROWSER} → None
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

    @property
    def current_app(self) -> str:
        """Get current application name"""
        return self._current_app

    @lru_cache(maxsize=9)
    def get_environment(self, env_type: Optional[EnvType] = None) -> Environment:
        """Get environment configuration for the current app (cached)"""
        env_type = env_type or self._current_env

        if env_type is None:
            raise EnvironmentNotSetError("Environment type is required")

        app_configs = _APP_REGISTRY.get(self._current_app)
        if app_configs is None:
            raise UnknownAppError(f"App '{self._current_app}' not found in registry")

        config = app_configs[env_type]
        auth_state_file = (
            self._auth_state_file if env_type == self._current_env else None
        )

        return Environment(
            name=env_type,
            app=self._current_app,
            base_url=config["base_url"],
            api_url=config["api_url"],
            auth_config=config["auth_config"],
            session_state_dir=str(self._session_states_dir),
            auth_state_file=auth_state_file,
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
        """Return BROWSER env var value, defaulting to chromium."""
        browser = os.getenv("BROWSER", "chromium").lower().strip()

        if browser not in BrowserType.values():
            logger.warning(
                f"Unsupported browser: {browser}. "
                f"Supported: {BrowserType.values()}. Using chromium."
            )
            return "chromium"

        return browser

    def get_session_file_path(
        self, env_type: Optional[EnvType] = None, browser: Optional[str] = None
    ) -> Path:
        """Get path to session state file, namespaced by app, env, and browser."""
        env = self.get_environment(env_type)
        if env.auth_state_file:
            return Path(env.auth_state_file)
        resolved_browser = browser or self.get_browser_type()
        filename = f"auth_state_{self._current_app}_{env.name.value}_{resolved_browser}_latest.json"
        return self._session_states_dir / filename

    def get_auth_state_file(self, env_type: Optional[EnvType] = None) -> Optional[str]:
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
        session_file = self.get_session_file_path()
        session_exists = session_file.exists()
        session_dir = self.get_session_dir()

        return (
            f"\n{'=' * 60}\n"
            f"App:              {self._current_app}\n"
            f"Environment:      {env.name.value.upper()}\n"
            f"Base URL:         {env.base_url}\n"
            f"API URL:          {env.api_url}\n"
            f"2FA Bypass:       {'Enabled' if env.can_bypass_2fa() else 'Disabled'}\n"
            f"Session Timeout:  {env.auth_config.session_timeout}s\n"
            f"Session Dir:      {session_dir}\n"
            f"Session File:     {session_file}\n"
            f"Session Exists:   {'Yes' if session_exists else 'No'}\n"
            f"{'=' * 60}"
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
        session_file = manager.get_session_file_path()

        # Validate session file exists if bypass is enabled
        if env.can_bypass_2fa() and not session_file.exists():
            logger.warning(
                f"2FA bypass enabled but session file missing: {session_file}\n"
                "Run session capture script first or disable 2FA bypass."
            )

        return True

    except (EnvironmentNotSetError, InvalidEnvironmentError, UnknownAppError) as e:
        logger.error(str(e))
        raise
