import os
from dataclasses import dataclass, field


@dataclass
class LocatorConfig:
  "Smart locator config"
  
  max_locator_attempts: int = 3
  locator_timeout: int = 5000  # Default timeout in milliseconds
  screenshot_on_failure: bool = True


# Default configuration
settings = LocatorConfig()