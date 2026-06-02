"""
Session State Manager for MEDITEK Test Automation
Handles 2FA bypass by managing browser session states
"""

import json
import logging
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Optional
from playwright.sync_api import Page, BrowserContext

from .environment import get_env_manager, EnvType

logger = logging.getLogger(__name__)


class SessionExpiredError(Exception):
    """Raised when session state has expired"""
    pass


class SessionFileNotFoundError(Exception):
    """Raised when session file doesn't exist"""
    pass


class SessionStateManager:
    """
    Manages browser session states for 2FA bypass.

    Responsibilities:
    - Load saved session state from JSON files
    - Apply cookies and localStorage to browser context
    - Validate session expiration
    - Save new session states after manual login
    """

    def __init__(self):
        self._env_manager = get_env_manager()
        # Maps BrowserContext id → origins data, avoiding monkey-patching Playwright objects
        self._context_origins: dict[int, list] = {}
    
    def load_session_state(self, env_type: Optional[EnvType] = None) -> Optional[dict]:
        """
        Load session state from file.
        
        Args:
            env_type: Environment to load session for (default: current)
            
        Returns:
            Session state dict or None if bypass not allowed
            
        Raises:
            SessionFileNotFoundError: If session file doesn't exist
            SessionExpiredError: If session has expired
        """
        env_type = env_type or self._env_manager.current_env
        
        # Check if bypass is allowed
        if not self._env_manager.should_bypass_2fa(env_type):
            logger.info(f"2FA bypass not allowed for {env_type.value}")
            return None
        
        session_path = self._env_manager.get_session_file_path(env_type)
        
        if not session_path.exists():
            raise SessionFileNotFoundError(
                f"Session file not found: {session_path}\n"
                f"Run session capture script for {env_type.value} environment."
            )
        
        try:
            with open(session_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in session file: {e}")
        
        # Validate session
        if not self._is_session_valid(data):
            expires_at = data.get("metadata", {}).get("expires_at", "unknown")
            raise SessionExpiredError(
                f"Session expired at: {expires_at}\n"
                f"Run session capture script to refresh."
            )
        
        logger.info(f"Session loaded: {session_path}")
        return data
    
    def _is_session_valid(self, session_data: dict) -> bool:
        """Check if session hasn't expired"""
        if not session_data:
            return False
        
        metadata = session_data.get("metadata", {})
        expires_str = metadata.get("expires_at")
        
        if not expires_str:
            logger.warning("Session has no expiration date")
            return False
        
        try:
            expires_str = expires_str.replace('Z', '+00:00')
            expires_at = datetime.fromisoformat(expires_str)
            if expires_at.tzinfo is None:
                # Legacy sessions saved without timezone — treat as UTC
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)

            is_valid = now < expires_at
            
            if is_valid:
                remaining = expires_at - now
                logger.debug(f"Session valid for {remaining}")
            
            return is_valid
            
        except (ValueError, TypeError) as e:
            logger.error(f"Failed to parse expiration date: {e}")
            return False
    
    def apply_to_context(
        self, 
        context: BrowserContext, 
        env_type: Optional[EnvType] = None,
        raise_on_error: bool = False
    ) -> bool:
        """
        Apply saved session state to browser context.
        
        Args:
            context: Playwright browser context
            env_type: Environment (default: current)
            raise_on_error: If True, raise exceptions instead of returning False
            
        Returns:
            True if session applied successfully
        """
        env_type = env_type or self._env_manager.current_env
        
        try:
            session_data = self.load_session_state(env_type)
            
            if session_data is None:
                return False
            
            storage_state = session_data.get("storage_state", {})
            
            # Apply cookies
            cookies = storage_state.get("cookies", [])
            if cookies:
                # Filter out expired cookies
                valid_cookies = self._filter_valid_cookies(cookies)
                context.add_cookies(valid_cookies)
                logger.info(f"Applied {len(valid_cookies)} cookies")
            
            # Store origins data keyed by context id (avoids monkey-patching Playwright objects)
            self._context_origins[id(context)] = storage_state.get("origins", [])

            return True
            
        except (SessionFileNotFoundError, SessionExpiredError, ValueError) as e:
            logger.error(str(e))
            if raise_on_error:
                raise
            return False
    
    def _filter_valid_cookies(self, cookies: list[dict]) -> list[dict]:
        """Filter out expired cookies"""
        now = datetime.now().timestamp()
        valid = []
        
        for cookie in cookies:
            expires = cookie.get("expires", -1)
            # -1 means session cookie (no expiry)
            if expires == -1 or expires > now:
                valid.append(cookie)
            else:
                logger.debug(f"Skipping expired cookie: {cookie.get('name')}")
        
        return valid
    
    def apply_local_storage(self, page: Page) -> bool:
        """
        Apply localStorage to page after navigation.
        Must be called AFTER page.goto() since localStorage is origin-specific.
        
        Args:
            page: Playwright page object
            
        Returns:
            True if applied successfully
        """
        context = page.context
        origins_data = self._context_origins.get(id(context))

        if not origins_data:
            logger.debug("No origins data available")
            return False
        
        try:
            current_origin = page.evaluate("window.location.origin")
        except Exception as e:
            logger.error(f"Failed to get page origin: {e}")
            return False
        
        applied_count = 0
        
        for origin in origins_data:
            if origin.get("origin") != current_origin:
                continue
            
            # Apply localStorage
            local_storage = origin.get("localStorage", [])
            for item in local_storage:
                name = item.get("name", "")
                value = item.get("value", "")
                
                if not name:
                    continue
                
                try:
                    # Use JSON.stringify to handle special characters
                    page.evaluate(
                        """([key, val]) => localStorage.setItem(key, val)""",
                        [name, value]
                    )
                    applied_count += 1
                except Exception as e:
                    logger.warning(f"Failed to set localStorage '{name}': {e}")
        
        if applied_count > 0:
            logger.info(f"Applied {applied_count} localStorage items")
            return True
        
        return False
    
    def save_session_state(
        self, 
        context: BrowserContext, 
        page: Page,
        env_type: Optional[EnvType] = None,
        expires_in_days: int = 3
    ) -> Path:
        """
        Save current browser session to file.
        Use after manual login to capture session for future 2FA bypass.
        
        Args:
            context: Browser context with authenticated session
            page: Current page (must be on authenticated page)
            env_type: Environment (default: current)
            expires_in_days: Session validity period
            
        Returns:
            Path to saved session file
            
        Raises:
            ValueError: If page is not authenticated
        """
        if not context:
            raise ValueError("Browser context is required")
        
        if not page:
            raise ValueError("Page is required")
        
        env_type = env_type or self._env_manager.current_env
        
        # Verify we're on an authenticated page
        if not self.is_authenticated(page):
            raise ValueError(
                "Page does not appear to be authenticated.\n"
                "Complete login before saving session state."
            )
        
        session_path = self._env_manager.get_session_file_path(env_type)
        
        # Get Playwright's storage state
        storage_state = context.storage_state()
        
        # Build session data — always store as UTC so validation comparisons are unambiguous
        now = datetime.now(timezone.utc)
        session_data = {
            "storage_state": storage_state,
            "metadata": {
                "captured_at": now.isoformat(),
                "expires_at": (now + timedelta(days=expires_in_days)).isoformat(),
                "url": page.url,
                "title": page.title(),
                "environment": self._env_manager.get_base_url(env_type)
            },
            "headers": {
                "user_agent": page.evaluate("navigator.userAgent")
            }
        }
        
        # Extract tokens for reference
        tokens = self._extract_tokens(storage_state)
        if tokens:
            session_data["tokens"] = tokens
        
        # Save to file
        session_path.parent.mkdir(exist_ok=True)
        with open(session_path, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Session saved: {session_path}")
        logger.info(f"Expires: {session_data['metadata']['expires_at']}")
        
        return session_path
    
    def _extract_tokens(self, storage_state: dict) -> dict:
        """Extract token-related items from storage state"""
        tokens = {}
        
        for origin in storage_state.get("origins", []):
            for item in origin.get("localStorage", []):
                name = item.get("name", "").lower()
                if any(keyword in name for keyword in ["token", "refresh", "auth", "session"]):
                    tokens[item.get("name")] = item.get("value")
        
        return tokens
    
    def is_authenticated(self, page: Page) -> bool:
        """
        Check if current page shows authenticated state.
        
        Args:
            page: Playwright page
            
        Returns:
            True if user appears logged in
        """
        if not page:
            return False
        
        try:
            current_url = page.url.lower()
            
            # Check if on login page
            login_indicators = ["/login", "/signin", "/auth"]
            if any(indicator in current_url for indicator in login_indicators):
                return False
            
            # Check for authenticated UI elements (customize for MEDITEK)
            auth_selectors = [
                "[data-testid='user-menu']",
                "[data-testid='logout-button']",
                "[data-testid='user-profile']",
                ".user-menu",
                ".logout-btn",
                "#user-info",
                "[aria-label='User menu']"
            ]
            
            for selector in auth_selectors:
                try:
                    element = page.locator(selector)
                    if element.count() > 0 and element.first.is_visible(timeout=1000):
                        logger.debug(f"Auth indicator found: {selector}")
                        return True
                except Exception:
                    continue
            
            # Fallback: check if NOT redirected to login
            page.wait_for_load_state("networkidle", timeout=5000)
            final_url = page.url.lower()
            
            return not any(indicator in final_url for indicator in login_indicators)
            
        except Exception as e:
            logger.warning(f"Auth check failed: {e}")
            return False
    
    def get_session_info(self, env_type: Optional[EnvType] = None) -> Optional[dict]:
        """
        Get session metadata without loading full state.
        
        Returns:
            Session metadata dict or None
        """
        env_type = env_type or self._env_manager.current_env
        session_path = self._env_manager.get_session_file_path(env_type)
        
        if not session_path.exists():
            return None
        
        try:
            with open(session_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            metadata = data.get("metadata", {})
            metadata["is_valid"] = self._is_session_valid(data)
            metadata["file_path"] = str(session_path)
            
            return metadata
            
        except Exception:
            return None