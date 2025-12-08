# Test Execution Quick Reference

## ✅ Correct Parameter Format

**ALL environment variables BEFORE `pytest` command:**

```bash
TEST_ENV=test BROWSER=firefox DEVICE=iphone pytest tests/ -v --alluredir=./allure-results
└────────────┬──────────────────────────────────┘  └────────────────────────────────────┘
    Environment Variables                         Pytest Command + Options
```

## 📋 Quick Commands

### Basic Execution
```bash
TEST_ENV=test pytest tests/
```

### With Browser
```bash
BROWSER=firefox TEST_ENV=test pytest tests/
BROWSER=webkit TEST_ENV=test pytest tests/
BROWSER=safari TEST_ENV=test pytest tests/
```

### With Device
```bash
DEVICE=iphone TEST_ENV=test pytest tests/
DEVICE=android TEST_ENV=test pytest tests/
DEVICE=iphone_14 TEST_ENV=test pytest tests/
```

### With Multiple Parameters
```bash
BROWSER=webkit DEVICE=iphone_14 SKIP_2FA=true TEST_ENV=test pytest tests/
```

### Parallel Execution
```bash
TEST_ENV=test pytest -n auto tests/
TEST_ENV=test pytest -n 4 --dist=loadscope tests/
```

### With Allure Reports
```bash
TEST_ENV=test pytest --alluredir=./allure-results tests/
allure serve ./allure-results
```

### With Verbose Output
```bash
TEST_ENV=test pytest -v tests/
TEST_ENV=test pytest -v -s tests/  # Show print output
```

### With Test Filtering
```bash
TEST_ENV=test pytest -k "login" tests/
TEST_ENV=test pytest -m smoke tests/
```

### Docker with Custom Session Directory
```bash
SESSION_DIR=/sessions TEST_ENV=test pytest tests/
```

## 🔧 Environment Variables

| Variable | Values | Default | Usage |
|----------|--------|---------|-------|
| **TEST_ENV** | test, preprod, prod | REQUIRED | `TEST_ENV=test` |
| BROWSER | chromium, firefox, webkit, safari | chromium | `BROWSER=firefox` |
| DEVICE | desktop, iphone, android, etc. | desktop | `DEVICE=iphone` |
| SKIP_2FA | true, false | true | `SKIP_2FA=true` |
| SESSION_DIR | /path/to/sessions | ~/.refua_sessions | `SESSION_DIR=/sessions` |
| RECORD_VIDEO | true, false | true | `RECORD_VIDEO=true` |
| CAPTURE_SCREENSHOTS | true, false | true | `CAPTURE_SCREENSHOTS=true` |

## ⚡ Common Pytest Options

| Option | Purpose | Example |
|--------|---------|---------|
| -v | Verbose output | `pytest -v tests/` |
| -s | Show print statements | `pytest -s tests/` |
| -k PATTERN | Filter tests | `pytest -k "login" tests/` |
| -m MARKER | Filter by marker | `pytest -m smoke tests/` |
| -x | Stop on first failure | `pytest -x tests/` |
| --tb=short | Short traceback | `pytest --tb=short tests/` |
| -n auto | Parallel (all cores) | `pytest -n auto tests/` |
| -n 4 | 4 parallel workers | `pytest -n 4 tests/` |
| --alluredir=PATH | Allure reports | `pytest --alluredir=./allure-results tests/` |

## 🎯 Most Common Examples

### 1. Run all tests with verbose output
```bash
TEST_ENV=test pytest -v tests/
```

### 2. Run specific test file
```bash
TEST_ENV=test pytest tests/test_auth.py
```

### 3. Run specific test function
```bash
TEST_ENV=test pytest tests/test_auth.py::test_login_success
```

### 4. Run tests matching pattern
```bash
TEST_ENV=test pytest -k "login" tests/
TEST_ENV=test pytest -k "test_auth and not slow" tests/
```

### 5. Run with specific marker
```bash
TEST_ENV=test pytest -m smoke tests/
```

### 6. Run in parallel (4 workers)
```bash
TEST_ENV=test pytest -n 4 tests/
```

### 7. Run on mobile device
```bash
DEVICE=iphone TEST_ENV=test pytest tests/
```

### 8. Run with specific browser
```bash
BROWSER=firefox TEST_ENV=test pytest tests/
```

### 9. Run with Allure reporting
```bash
TEST_ENV=test pytest --alluredir=./allure-results tests/
```

### 10. Full example with all options
```bash
TEST_ENV=test \
BROWSER=webkit \
DEVICE=iphone_14 \
SKIP_2FA=true \
RECORD_VIDEO=true \
CAPTURE_SCREENSHOTS=true \
pytest tests/ \
-v \
-n 4 \
--alluredir=./allure-results \
-m smoke
```

## ❌ Common Mistakes

```bash
# WRONG - env vars after pytest
pytest tests/ TEST_ENV=test BROWSER=firefox

# WRONG - pytest options mixed with env vars
TEST_ENV=test pytest -v DEVICE=iphone tests/

# WRONG - env vars at the end
pytest tests/ -v TEST_ENV=test

# WRONG - missing TEST_ENV
pytest tests/

# WRONG - unsupported browser
BROWSER=chrome TEST_ENV=test pytest tests/
```

## 🐳 Docker Execution

```bash
# With external session volume
docker run -v ~/.refua_sessions:/sessions myimage \
  sh -c "SESSION_DIR=/sessions TEST_ENV=test pytest tests/"

# Docker compose
docker-compose run test-automation \
  sh -c "TEST_ENV=test pytest -n auto tests/"
```

## 📊 What Gets Logged

When tests run, the framework logs all parameters:

```
================================================================================
TEST EXECUTION PARAMETERS
================================================================================
Environment Variables:
  TEST_ENV             = test
  BROWSER              = firefox
  DEVICE               = iphone
  SKIP_2FA             = true (default for test/preprod)
  SESSION_DIR          = ~/.refua_sessions (default)
  RECORD_VIDEO         = true (default)
  CAPTURE_SCREENSHOTS  = true (default)
================================================================================
✓ Using browser: firefox
✓ Browser launched: firefox
✓ 2FA bypass enabled (SKIP_2FA=true)
✓ Session loaded from: /home/user/.refua_sessions/auth_state_test_firefox_latest.json
✓ Device: iphone
✓ Recording: video=True, screenshots=True
✓ Browser context created for test environment
================================================================================
```

## 🔗 See Also

- **PARAMETER_GUIDE.md** - Comprehensive parameter documentation
- **refua_core/conftest.py** - Pytest configuration and parameter handling
- **refua_core/core/base_test.py** - Base test class with parameter logging
- **CLAUDE.md** - Framework architecture and documentation

## 📝 Notes

1. **TEST_ENV is REQUIRED** - Always set this, no default
2. **Environment variables go BEFORE pytest** - Not after
3. **Pytest options go AFTER pytest** - Not before
4. **Parameters are logged** - Check logs to verify what's being used
5. **Sessions are browser-specific** - Different file per browser
6. **Session files expire** - Recapture after 3 days
7. **Test artifacts cleanup** - Passing tests auto-delete artifacts
