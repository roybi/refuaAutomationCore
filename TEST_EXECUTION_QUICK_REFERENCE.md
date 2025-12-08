# Test Execution Quick Reference

## ✅ Correct Parameter Format

**ALL parameters at END of pytest command:**

```bash
pytest tests/ -v --alluredir=./allure-results --test-env=test --browser=firefox --device=iphone
└──────────────────────────────────────────────┘  └─────────────────────────────────────────┘
    Test Path + Pytest Options                    Framework Parameters (at END)
```

## ✅ Alternative: Environment Variables (Before pytest)

```bash
TEST_ENV=test BROWSER=firefox DEVICE=iphone pytest tests/ -v --alluredir=./allure-results
└────────────┬──────────────────────────────────┘  └────────────────────────────────────┘
    Environment Variables                         Pytest Command + Options
```

## 📋 Quick Commands

### Basic Execution
```bash
pytest tests/ --test-env=test
```

### With Browser
```bash
pytest tests/ --test-env=test --browser=firefox
pytest tests/ --test-env=test --browser=webkit
pytest tests/ --test-env=test --browser=safari
```

### With Device
```bash
pytest tests/ --test-env=test --device=iphone
pytest tests/ --test-env=test --device=android
pytest tests/ --test-env=test --device=iphone_14
```

### With Multiple Parameters
```bash
pytest tests/ --test-env=test --browser=webkit --device=iphone_14 --skip-2fa=true
```

### Parallel Execution
```bash
pytest tests/ -n auto --test-env=test
pytest tests/ -n 4 --dist=loadscope --test-env=test
```

### With Allure Reports
```bash
pytest tests/ --alluredir=./allure-results --test-env=test
allure serve ./allure-results
```

### With Verbose Output
```bash
pytest tests/ -v --test-env=test
pytest tests/ -v -s --test-env=test  # Show print output
```

### With Test Filtering
```bash
pytest tests/ -k "login" --test-env=test
pytest tests/ -m smoke --test-env=test
```

### Docker with Custom Session Directory
```bash
pytest tests/ --test-env=test --session-dir=/sessions
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
pytest tests/ -v --test-env=test
```

### 2. Run specific test file
```bash
pytest tests/test_auth.py --test-env=test
```

### 3. Run specific test function
```bash
pytest tests/test_auth.py::test_login_success --test-env=test
```

### 4. Run tests matching pattern
```bash
pytest tests/ -k "login" --test-env=test
pytest tests/ -k "test_auth and not slow" --test-env=test
```

### 5. Run with specific marker
```bash
pytest tests/ -m smoke --test-env=test
```

### 6. Run in parallel (4 workers)
```bash
pytest tests/ -n 4 --test-env=test
```

### 7. Run on mobile device
```bash
pytest tests/ --test-env=test --device=iphone
```

### 8. Run with specific browser
```bash
pytest tests/ --test-env=test --browser=firefox
```

### 9. Run with Allure reporting
```bash
pytest tests/ --alluredir=./allure-results --test-env=test
```

### 10. Full example with all options
```bash
pytest tests/ \
-v \
-n 4 \
--alluredir=./allure-results \
-m smoke \
--test-env=test \
--browser=webkit \
--device=iphone_14 \
--skip-2fa=true \
--record-video=true \
--capture-screenshots=true
```

## ❌ Common Mistakes

```bash
# WRONG - parameters before pytest options
pytest tests/ --test-env=test -v

# WRONG - mixing old env var format with new format
TEST_ENV=test pytest tests/ --browser=firefox

# WRONG - missing --test-env
pytest tests/ --browser=firefox

# WRONG - unsupported browser
pytest tests/ --test-env=test --browser=chrome

# WRONG - pytest options after parameters
pytest tests/ --test-env=test --browser=firefox -v
```

**CORRECT:**
```bash
# ✅ Parameters at end
pytest tests/ -v --test-env=test --browser=firefox

# ✅ OR use environment variables
TEST_ENV=test BROWSER=firefox pytest tests/ -v
```

## 🐳 Docker Execution

```bash
# With external session volume
docker run -v ~/.refua_sessions:/sessions myimage \
  sh -c "pytest tests/ --test-env=test --session-dir=/sessions"

# Docker compose
docker-compose run test-automation \
  sh -c "pytest tests/ -n auto --test-env=test"

# With all parameters
docker run -v ~/.refua_sessions:/sessions myimage \
  sh -c "pytest tests/ -v -n 4 --alluredir=./allure-results \
  --test-env=test --browser=firefox --device=iphone --session-dir=/sessions"
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
