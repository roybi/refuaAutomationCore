__version__ = "1.0.1"
__framework_name__ = "Refua Automation Core"
__framework_author__ = "Refua Team"


def check_version_compatibility(required_version: str) -> bool:
    """Check if the current version is compatible with the required version."""
    from packaging import version
    return version.parse(__version__) >= version.parse(required_version)
