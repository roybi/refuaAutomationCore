"""
Standalone automation-login check for the MEDITIK / CPR-GO frontends.

Auth model (automation -> front -> back):
  The automation secret lives ONLY in the meditik backend .env and in this
  test's environment. The front no longer sends it. This script drives the
  browser to the front automation route and INJECTS the x-automation-secret
  header onto the outbound POST to the backend via request interception
  (Playwright page.route) -- the only place the secret is applied. The browser
  only ever holds the issued token, never the secret.

What it does:
  1. Reads AUTOMATION_SECRET from the environment / .env files.
  2. Builds the login URL dynamically: {root domain for TEST_ENV}/automation/login/<personalNumber>,
     using refua_core's EnvironmentManager (same TEST_ENV/TEST_APP resolution as the rest of
     the framework) when TEST_ENV is set, or BASE_URL / localhost:4200 otherwise.
  3. Intercepts **/automation/login/** and adds the x-automation-secret header.
  4. Opens the login URL in a real browser.
  5. Waits for the app to redirect to /home once the token is stored.
  6. Reports whether authentication succeeded.

This file is intentionally self-contained. It does NOT touch conftest.py or the auth-state files.

Usage (from the repo root):
    # AUTOMATION_SECRET must be set (env var or in .env.test / .env.local)
    python scripts/check_local_login.py                                   # localhost:4200, default personalNumber
    python scripts/check_local_login.py 4444401                            # explicit personalNumber
    python scripts/check_local_login.py 4444401 --headless
    python scripts/check_local_login.py 4444401 --app meditik --env test   # https://meditik.test.medical.idf.il
    python scripts/check_local_login.py 4444401 --app cpr --env preprod    # https://cpr-go.preprod.medical.idf.il
    TEST_APP=cpr-go TEST_ENV=test python scripts/check_local_login.py      # same, via env vars

Requires Playwright browsers to be installed:
    playwright install chromium
"""

import json
import os
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

from playwright.sync_api import sync_playwright

DEFAULT_BASE_URL = "http://localhost:4200"
DEFAULT_PERSONAL_NUMBER = "4444401"
AUTOMATION_SECRET_HEADER = "x-automation-secret"

REPO_ROOT = Path(__file__).resolve().parent.parent
# .env files are read only for values not already present in the real environment.
ENV_FILES = [".env.test", ".env.local"]


def _load_env_files():
    """Minimal, dependency-free .env loader.

    Populates os.environ for keys that aren't already set. Only KEY=VALUE lines
    are parsed; comments and blanks are ignored. Real environment variables
    (e.g. from CI) always win over .env file values.
    """
    for env_name in ENV_FILES:
        env_path = REPO_ROOT / env_name
        if not env_path.exists():
            continue
        try:
            for raw_line in env_path.read_text(encoding="utf-8").splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                # Strip inline comments on simple values.
                if " #" in value:
                    value = value.split(" #", 1)[0].strip()
                if key and key not in os.environ:
                    os.environ[key] = value
        except OSError:
            continue


def parse_args(argv):
    personal_number = DEFAULT_PERSONAL_NUMBER
    headless = False
    args = iter(argv[1:])
    for arg in args:
        if arg == "--headless":
            headless = True
        elif arg == "--app":
            os.environ["TEST_APP"] = next(args)
        elif arg == "--env":
            os.environ["TEST_ENV"] = next(args)
        elif arg.startswith("--app="):
            os.environ["TEST_APP"] = arg.split("=", 1)[1]
        elif arg.startswith("--env="):
            os.environ["TEST_ENV"] = arg.split("=", 1)[1]
        elif not arg.startswith("--"):
            personal_number = arg
    return personal_number, headless


def _build_login_url(personal_number: str) -> str:
    """Build the automation-login URL for personal_number.

    If TEST_ENV is set, resolves the root domain via refua_core's EnvironmentManager
    (test/preprod/prod, same as the rest of the framework) — TEST_APP selects the app
    (default meditek). Otherwise falls back to BASE_URL / localhost:4200 for pure
    local-frontend testing.
    """
    env_str = os.getenv("TEST_ENV")
    if env_str:
        from refua_core.config.environment import EnvType, get_env_manager

        env_mgr = get_env_manager()
        return env_mgr.get_automation_login_url(personal_number, EnvType(env_str.lower().strip()))

    base_url = (os.getenv("BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
    return f"{base_url}/automation/login/{personal_number}"


def main():
    _load_env_files()

    secret = os.getenv("AUTOMATION_SECRET")
    if not secret:
        print("[check] AUTOMATION_SECRET is not set in the test environment.")
        print("[check] Set it as an env var, or add it to .env.test / .env.local:")
        print("[check]     AUTOMATION_SECRET=<value matching the backend>")
        sys.exit(1)

    personal_number, headless = parse_args(sys.argv)
    login_url = _build_login_url(personal_number)

    print(f"[check] personalNumber = {personal_number}")
    print(f"[check] TEST_APP       = {os.getenv('TEST_APP') or 'meditek (default)'}")
    print(f"[check] TEST_ENV       = {os.getenv('TEST_ENV') or '(not set — using BASE_URL/localhost)'}")
    print(f"[check] opening        = {login_url}")
    print(f"[check] headless       = {headless}")
    print(f"[check] secret         = set ({len(secret)} chars), injected via page.route")


    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=headless)
        context = browser.new_context(locale="he-IL", timezone_id="Asia/Jerusalem")
        page = context.new_page()

        # --- The core of the new auth model ---
        # The front does NOT know the secret. We intercept the outbound
        # automation-login request and add the x-automation-secret header here.
        # Scoped to the login endpoint only, so no other request gets the secret.
        if os.getenv("TEST_ENV"):
            from refua_core.config.environment import get_env_manager

            get_env_manager().apply_automation_secret_header(page)
        else:
            def _inject_secret(route):
                headers = {**route.request.headers, AUTOMATION_SECRET_HEADER: secret}
                route.continue_(headers=headers)

            page.route("**/automation/login/**", _inject_secret)

        # --- Diagnostics: surface what the app is actually doing ---
        page.on("requestfailed", lambda req: print(f"[network] FAILED {req.method} {req.url}"))
        page.on("console", lambda msg: print(f"[console:{msg.type}] {msg.text}"))
        page.on("pageerror", lambda err: print(f"[pageerror] {err}"))

        # Log every request/response that touches the automation-login API or 5200.
        def _on_request(req):
            if "automation/login" in req.url or ":5200" in req.url or "5200" in req.url:
                print(f"[req] {req.method} {req.url}")
        def _on_response(resp):
            if "automation/login" in resp.url or "5200" in resp.url:
                print(f"[resp] {resp.status} {resp.url}")
        page.on("request", _on_request)
        page.on("response", _on_response)

        try:
            page.goto(login_url, wait_until="domcontentloaded", timeout=60000)
        except Exception as error:
            print(f"[check] FAILED to open the login URL: {error}")
            print(f"[check] Is the frontend running/reachable at {login_url} ?")
            context.close()
            browser.close()
            sys.exit(1)

        # The component navigates to /home on success. Wait for that redirect,
        # then let async calls / token storage settle.
        try:
            page.wait_for_url("**/home**", timeout=20000)
        except Exception:
            pass
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
        page.wait_for_timeout(3000)

        final_url = page.url
        print(f"\n[result] final URL     = {final_url}")

        # Inspect where the token might have landed.
        local_storage = page.evaluate(
            "() => Object.fromEntries(Object.entries(window.localStorage))"
        )
        cookies = context.cookies()

        token_keys = [
            k for k, v in local_storage.items()
            if isinstance(v, str) and (v.count(".") == 2 and len(v) > 40)
        ]

        print(f"[result] localStorage keys = {list(local_storage.keys())}")
        if token_keys:
            print(f"[result] JWT-looking key(s) in localStorage = {token_keys}")
        cookie_names = [c.get("name") for c in cookies]
        print(f"[result] cookie names      = {cookie_names}")

        # Verdict: login succeeded if we left the /automation/login/... route
        # (redirected to /home). A credential (token/cookie) is a bonus signal.
        left_login_route = "/automation/login/" not in final_url
        landed_on_home = "/home" in final_url

        try:
            body_snippet = page.locator("body").inner_text(timeout=3000)[:300]
        except Exception:
            body_snippet = "(could not read body text)"
        print(f"\n[result] page text snippet:\n{body_snippet}\n")

        if landed_on_home:
            print("[verdict] SUCCESS — authentication worked; landed on /home.")
            verdict = 0
        elif left_login_route:
            print("[verdict] LIKELY OK — left the login route, but not clearly on /home.")
            verdict = 0
        else:
            print("[verdict] FAILED — still on the login route; authentication did not complete.")
            verdict = 2

        # Dump the full state to a file for deeper inspection if needed.
        debug = {
            "final_url": final_url,
            "local_storage": local_storage,
            "cookies": cookies,
        }
        with open("local_login_debug.json", "w", encoding="utf-8") as f:
            json.dump(debug, f, ensure_ascii=False, indent=2)
        print("[check] full state written to local_login_debug.json")

        if not headless:
            input("\n[check] Browser left open for inspection — press Enter here to close it...")

        context.close()
        browser.close()
        sys.exit(verdict)


if __name__ == "__main__":
    main()
