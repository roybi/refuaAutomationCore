# Repository Separation Summary

## Overview

The refuaAutomationCore project has been restructured to separate the **reusable framework** from **test implementation**. This enables:
- Independent versioning and distribution of the framework
- Multiple test suites reusing the same framework
- Clear separation of concerns
- Easier dependency management

---

## What Has Been Completed ✅

### 1. Documentation Updates (CLAUDE.md)

**Updated Sections:**
- ✅ Project Overview - Clarified test-framework separation
- ✅ Repository Architecture - Documented both repos
- ✅ For Different Roles - Guidance for Framework Developers, Test Authors, Architects
- ✅ Setup & Installation - Separate procedures for framework vs. test repos
- ✅ Package Configuration - setup.py guidance
- ✅ Publishing - Release and distribution guide

**Key Change:** CLAUDE.md now clearly states this is the **framework repository only** and references a separate test repository for actual test implementation.

### 2. Created setup.py

**File:** `setup.py`
- ✅ Package name: `refua-automation-core`
- ✅ Version: 1.0.0
- ✅ Dependencies: playwright, python-dotenv, requests
- ✅ Optional features: figma, dev
- ✅ Ready for PyPI or internal registry distribution
- ✅ Includes device configuration packaging

### 3. Created Detailed Plan

**File:** `REPOSITORY_SEPARATION_PLAN.md`
- ✅ Complete checklist of code changes needed
- ✅ Files to delete (tests, app-specific code)
- ✅ New test repository structure
- ✅ Migration steps in order
- ✅ Timeline and benefits

---

## What Needs to Be Done Next

### Phase 1: Code Cleanup (This Repository)

**Delete Test Files** (move to refuaAutomationTests):
```
❌ tests/conftest.py
❌ tests/test_*.py (all test files)
❌ FIRST_TEST_SUMMARY.md
❌ RUN_FIRST_TEST.md
❌ PWA_POPUP_QUICK_START.md
❌ PWA_POPUP_SETUP_SUMMARY.md
```

**Delete App-Specific Code** (move to refuaAutomationTests):
```
❌ refua_core/pages/mainPage.py
❌ refua_core/pages/pwa_popup.py
❌ refua_core/pages/common_actions.py
❌ refua_core/core/pwa_popup_handler.py
❌ refua_core/core/pwa_popup_hooks.py
```

**Delete Test Configuration** (move to refuaAutomationTests):
```
❌ pytest.ini (if exists)
❌ .env.test
❌ .env.preprod
❌ .env.prod
```

**Keep - Framework Components:**
```
✅ refua_core/config/environment.py
✅ refua_core/config/session_manager.py
✅ refua_core/config/devices.json
✅ refua_core/core/base_test.py
✅ refua_core/core/device_manager.py
✅ refua_core/core/artifact_manager.py
✅ refua_core/core/visual_regression.py
✅ scripts/capture_session.py
```

### Phase 2: Update Requirements

**Update:** `requirements.txt`

**Should contain (framework only):**
```
playwright>=1.40.0
python-dotenv>=1.0.0
requests>=2.31.0
pytest>=7.0.0
```

**Should NOT contain:**
- Test-specific packages (allure, xdist)
- Application-specific dependencies
- Test tools

### Phase 3: Create Base Page Object Template

**Create:** `refua_core/pages/base_page.py`
```python
from playwright.sync_api import Page
from refua_core.config.environment import get_env_manager

class BasePage:
    """Base page object for inheritance by test page objects."""

    def __init__(self, page: Page):
        self.page = page

    def goto(self, path: str):
        """Navigate to path on current environment."""
        env_mgr = get_env_manager()
        self.page.goto(f"{env_mgr.get_base_url()}{path}")

    def wait_for_url(self, path: str, timeout: int = 30000):
        """Wait for URL navigation."""
        env_mgr = get_env_manager()
        full_url = f"{env_mgr.get_base_url()}{path}"
        self.page.wait_for_url(full_url, timeout=timeout)
```

### Phase 4: Create New Test Repository

**New Repository Structure:**

```
refuaAutomationTests/
├── refua_tests/
│   ├── __init__.py
│   ├── pages/
│   │   ├── __init__.py
│   │   ├── login_page.py          # Move from refuaAutomationCore
│   │   ├── dashboard_page.py      # New
│   │   └── main_page.py           # Move from refuaAutomationCore
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py            # Move from refuaAutomationCore
│   │   ├── test_auth.py           # Move from refuaAutomationCore
│   │   └── test_smoke.py          # Move from refuaAutomationCore
│   └── fixtures/
│       └── __init__.py
├── .env.test
├── .env.preprod
├── .env.prod
├── pytest.ini
├── requirements.txt
├── setup.py (optional)
├── CLAUDE.md
├── README.md
└── .gitignore
```

**refuaAutomationTests/requirements.txt:**
```
# Framework (from PyPI or git)
refua-automation-core>=1.0.0
# OR for development:
# refua-automation-core @ git+https://github.com/org/refuaAutomationCore.git@main

# Test dependencies
pytest>=7.0.0
pytest-xdist>=3.0.0
pytest-allure-adaptor>=1.0.0
playwright>=1.40.0
python-dotenv>=1.0.0
```

---

## Repository Roles After Separation

### refuaAutomationCore (Framework Library)

**Purpose:** Reusable testing framework
**Responsibility:** Framework development, features, bug fixes
**Users:** Multiple test repositories, internal packages
**Release:** Semantic versioning (v1.0.0, v1.1.0, v2.0.0)
**Package:** Published to PyPI or internal registry

**Contains:**
- ✅ Configuration management (EnvironmentManager)
- ✅ Session management (SessionStateManager)
- ✅ Device configuration and management
- ✅ Base test classes
- ✅ Artifact management
- ✅ Visual regression support
- ✅ Utility scripts

**Does NOT contain:**
- ❌ Application page objects
- ❌ Test cases
- ❌ Test fixtures
- ❌ Application credentials

---

### refuaAutomationTests (Test Implementation)

**Purpose:** Test automation for MEDITEK application
**Responsibility:** Test development, page objects, test organization
**Users:** QA team, CI/CD pipeline
**Release:** Project versioning (tied to application)
**Dependency:** Imports framework via `refua-automation-core` package

**Contains:**
- ✅ Page objects for MEDITEK UI
- ✅ Test cases
- ✅ Test fixtures and configuration
- ✅ Application credentials (.env files)
- ✅ Test-specific tools (pytest.ini, allure config)

**Does NOT contain:**
- ❌ Framework code
- ❌ Core infrastructure
- ❌ Package management (setup.py is optional)

---

## Migration Checklist

### Step 1: Code Cleanup (This Repository)
- [ ] Backup current test files (save before deleting)
- [ ] Delete `tests/` directory
- [ ] Delete app-specific page objects (`mainPage.py`, `pwa_popup.py`, `common_actions.py`)
- [ ] Delete app-specific handlers (`pwa_popup_handler.py`, `pwa_popup_hooks.py`)
- [ ] Delete test documentation files
- [ ] Create `refua_core/pages/base_page.py` template
- [ ] Update `requirements.txt` to framework-only
- [ ] Commit changes: "refactor: separate test framework from implementation"

### Step 2: New Test Repository Setup
- [ ] Create new GitHub repository: `refuaAutomationTests`
- [ ] Initialize git repo with proper structure
- [ ] Copy test files from backup
- [ ] Copy app-specific page objects
- [ ] Create `.env.*` files
- [ ] Create `pytest.ini`
- [ ] Add `requirements.txt` with framework dependency
- [ ] Create `CLAUDE.md` for test-specific guidance
- [ ] First commit: "initial: test implementation for MEDITEK"

### Step 3: Testing & Validation
- [ ] Test refuaAutomationCore can be installed: `pip install -e .`
- [ ] Test refuaAutomationTests can import framework: `from refua_core import ...`
- [ ] Run tests from refuaAutomationTests: `TEST_ENV=test pytest`
- [ ] Verify all tests pass
- [ ] Check CI/CD still works (if configured)

### Step 4: Release & Documentation
- [ ] Tag release in refuaAutomationCore: `git tag v1.0.0`
- [ ] Update both README files with clear role descriptions
- [ ] Add links between repositories
- [ ] Create GitHub release notes
- [ ] Document package installation steps
- [ ] Update team wiki/documentation

---

## Files Modified vs. Created

### ✅ Modified
- `CLAUDE.md` - Updated with separation architecture

### ✅ Created
- `setup.py` - Package configuration
- `REPOSITORY_SEPARATION_PLAN.md` - Detailed migration plan
- `SEPARATION_SUMMARY.md` - This file

### ⏳ Pending (Manual Steps)
- Delete test files (need to back up first)
- Delete app-specific code
- Create new test repository
- Update requirements.txt
- Create base_page.py template

---

## Important Notes

### ⚠️ Breaking Changes

When separating, ensure no breaking changes to:
- `EnvironmentManager` API
- `SessionStateManager` API
- `BaseTest` class signature
- Device configuration format
- Session file format

### 📦 Package Distribution

Framework can be distributed via:
1. **PyPI** - `pip install refua-automation-core` (public)
2. **Internal Registry** - Private package registry
3. **Git Installation** - `pip install git+https://github.com/org/refuaAutomationCore.git`
4. **Editable Install** - `pip install -e .` (for development)

### 🔄 Version Management

Framework should use **semantic versioning**:
- `1.0.0` - Initial release
- `1.1.0` - Minor feature addition
- `2.0.0` - Breaking changes
- Test repository can use different versioning

### 🔗 Dependency Updates

Test repository can:
- Pin specific framework version: `refua-automation-core==1.0.0`
- Use version ranges: `refua-automation-core>=1.0.0,<2.0.0`
- Use latest: `refua-automation-core` (not recommended)
- Pin git branch: `refua-automation-core @ git+https://...@main`

---

## Quick Start Commands (After Separation)

### Framework Development
```bash
cd refuaAutomationCore
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
# Make framework improvements
```

### Test Development
```bash
cd refuaAutomationTests
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
mkdir -p ~/.refua_sessions
python scripts/capture_session.py --env test --user <username>
TEST_ENV=test pytest --alluredir=./allure-results
```

### Framework Release
```bash
cd refuaAutomationCore
# Update version in setup.py
git add -A
git commit -m "release: v1.1.0"
git tag v1.1.0
git push origin v1.1.0
# Build and publish
python -m build
twine upload dist/*
```

---

## Next Steps

1. **Review this plan** - Ensure you agree with the structure
2. **Back up test files** - Save before deletion
3. **Execute Phase 1** - Clean up this repository
4. **Create test repo** - Set up refuaAutomationTests
5. **Validate setup** - Run tests from new repo
6. **Release** - Tag v1.0.0 and publish

**Questions?** Refer to CLAUDE.md or REPOSITORY_SEPARATION_PLAN.md
