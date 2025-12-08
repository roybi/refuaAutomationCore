# Repository Separation Plan: refuaAutomationCore

**Objective:** Separate the test automation framework into two repositories:
1. **refuaAutomationCore** (this repo) - Reusable framework package
2. **refuaAutomationTests** (new repo) - Test implementation

---

## Summary of Changes

### ✅ Completed: CLAUDE.md Documentation

The main CLAUDE.md file has been updated to reflect the new repository structure:

**Updated Sections:**
- Project Overview: Clarified that tests are in a separate repo
- Repository Architecture: Documented both repos with visual structure
- Core Framework Structure: Details only the framework components
- For Different Roles: Added guidance for Framework Developers, Test Authors, and Architects
- Documentation Organization: Clear separation of what docs apply to each repo
- Setup & Installation: Separate sections for framework developers vs. test authors
- Package Configuration: Added setup.py guidance for distributing as a pip package
- Publishing: Guide for releasing framework versions

---

## Code Changes Needed (In This Repository)

### Phase 1: Remove Test Implementation Files

**Files to DELETE from refuaAutomationCore:**
```
tests/                                    # Entire test directory
├── conftest.py
├── test_*.py                            # All test files
└── ... (all test files)

refua_core/pages/                        # Remove app-specific page objects
├── mainPage.py
├── pwa_popup.py
├── common_actions.py
└── __pycache__/

refua_core/core/pwa_popup_handler.py     # App-specific handlers
refua_core/core/pwa_popup_hooks.py       # App-specific hooks
```

**Reason:** These are test implementation details, not framework code. They belong in refuaAutomationTests.

### Phase 2: Clean Up Framework Structure

**Keep ONLY Framework Components:**
```
refua_core/
├── __init__.py
├── config/
│   ├── __init__.py
│   ├── environment.py          # Keep: Framework component
│   ├── session_manager.py      # Keep: Framework component
│   └── devices.json            # Keep: Framework component
├── core/
│   ├── __init__.py
│   ├── base_test.py            # Keep: Framework component
│   ├── device_manager.py       # Keep: Framework component
│   ├── artifact_manager.py     # Keep: Framework component
│   └── visual_regression.py    # Keep: Framework component
└── pages/                       # DELETE or convert to template
    └── base_page.py            # Keep: Base POM class (template)
```

### Phase 3: Create setup.py for Package Distribution

**Create:** `setup.py`
```python
from setuptools import setup, find_packages

setup(
    name="refua-automation-core",
    version="1.0.0",
    description="Reusable test automation framework for MEDITEK",
    author="Your Team",
    author_email="your-team@example.com",
    url="https://github.com/org/refuaAutomationCore",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[
        "playwright>=1.40.0",
        "python-dotenv>=1.0.0",
        "requests>=2.31.0",
    ],
    extras_require={
        "figma": ["pillow>=9.0.0"],
        "dev": [
            "pytest>=7.0.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
        ],
    },
    include_package_data=True,
    package_data={
        "refua_core": ["config/devices.json"],
    },
)
```

### Phase 4: Update requirements.txt (Framework Only)

**Update:** `requirements.txt`
```
playwright>=1.40.0
python-dotenv>=1.0.0
requests>=2.31.0
pytest>=7.0.0
pytest-allure-adaptor>=1.0.0
```

**Remove:**
- Test-specific packages
- Application-specific dependencies

### Phase 5: Remove Test Configuration Files

**Files to DELETE:**
- `pytest.ini` (will be in test repo)
- `.env*` files (will be in test repo)
- `conftest.py` (will be in test repo)

### Phase 6: Update Root Files

**Update .gitignore:**
- Remove test-specific patterns
- Keep framework-specific patterns only
- Focus on development artifacts

**Update README.md:**
- Describe this as the core framework package
- Link to refuaAutomationTests repo for test examples
- Add PyPI installation instructions

---

## New Repository: refuaAutomationTests

This separate repository needs to be created with the following structure:

### Directory Structure
```
refuaAutomationTests/
├── refua_tests/
│   ├── __init__.py
│   ├── pages/
│   │   ├── __init__.py
│   │   ├── base_page.py          # Inherit from refua_core
│   │   ├── login_page.py
│   │   ├── dashboard_page.py
│   │   └── main_page.py
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py           # Pytest fixtures
│   │   ├── test_auth.py
│   │   ├── test_smoke.py
│   │   └── test_pwa_popup.py
│   └── fixtures/
│       └── (test helpers)
├── .env.test
├── .env.preprod
├── .env.prod
├── pytest.ini
├── requirements.txt
├── setup.py (optional - if packaging tests)
├── CLAUDE.md
└── README.md
```

### refuaAutomationTests/requirements.txt
```
# Framework dependency
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

## Migration Steps (In Order)

### Step 1: Code Changes in This Repository
1. Delete test files from `tests/`
2. Delete app-specific code from `refua_core/`
3. Create `setup.py` for package distribution
4. Update `requirements.txt` to framework-only deps
5. Update `CLAUDE.md` (already done)
6. Update `README.md` to describe as framework

### Step 2: Set Up New Test Repository
1. Create new git repository: `refuaAutomationTests`
2. Copy test files and app-specific page objects
3. Create test-specific configuration files
4. Add `refua-automation-core` to requirements.txt
5. Create test-specific `CLAUDE.md`

### Step 3: Testing & Validation
1. Verify refuaAutomationCore can be installed as package
2. Verify refuaAutomationTests imports framework correctly
3. Run test suite from test repository
4. Update CI/CD pipelines for both repos

### Step 4: Publishing & Documentation
1. Release version 1.0.0 of refuaAutomationCore
2. Update README files in both repos with links
3. Create GitHub release notes
4. Update team documentation

---

## Dependencies Between Repositories

### refuaAutomationCore Dependencies
- Framework only dependencies
- NO test-specific code
- NO page objects
- NO test cases

### refuaAutomationTests Dependencies
- Imports: `from refua_core import ...`
- Depends on: `refua-automation-core` package
- Contains: Tests, page objects, test fixtures

### Breaking Changes to Avoid
- Changes to core API signature (EnvironmentManager, SessionStateManager)
- Changes to base classes (BaseTest)
- Changes to device configuration schema
- Changes to session file format

---

## Benefits of This Architecture

✅ **Core Framework Benefits:**
- Can be versioned independently
- Can be reused by multiple test suites
- Cleaner codebase for framework development
- Clear API contracts
- Easier to publish and distribute

✅ **Test Implementation Benefits:**
- Focused on business logic and tests
- Clear dependency on framework
- Can upgrade framework independently
- No need to manage framework code

✅ **Organizational Benefits:**
- Separation of concerns
- Different release cycles
- Multiple teams can work independently
- Easier to onboard new test suites

---

## Files to Delete (Final Checklist)

- [ ] `tests/` directory (entire)
- [ ] `refua_core/pages/mainPage.py`
- [ ] `refua_core/pages/pwa_popup.py`
- [ ] `refua_core/pages/common_actions.py`
- [ ] `refua_core/core/pwa_popup_handler.py`
- [ ] `refua_core/core/pwa_popup_hooks.py`
- [ ] `pytest.ini` (if exists)
- [ ] `.env.test`, `.env.preprod`, `.env.prod`
- [ ] Test-related documentation files

## Files to Create (Final Checklist)

- [ ] `setup.py` (package configuration)
- [ ] Update `requirements.txt`
- [ ] Update `.gitignore`
- [ ] Update `README.md`
- [ ] Update `CLAUDE.md` (done)
- [ ] Create new `refuaAutomationTests` repository

---

## Timeline

**Week 1:**
- Code cleanup in this repo (delete test files)
- Create setup.py
- Update documentation

**Week 2:**
- Create refuaAutomationTests repository
- Migrate test files
- Update CI/CD for both repos

**Week 3:**
- Release v1.0.0 of refuaAutomationCore
- Update team documentation
- Onboard team on new structure
