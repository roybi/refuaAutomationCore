# Deployment Prerequisites — Isolated Parallel Playwright Runs + Always-On Allure Server

Scope: what a VM/Docker host needs to (1) run this framework's Playwright tests in
isolated, parallel workers, and (2) host a persistent Allure report server that stays
up between runs (not just `allure serve`, which is a one-shot, single-viewer process).

This is an infrastructure checklist, not a `pip install` file — Python deps are
already declared in `requirements.txt` (this repo) and the test repo's
`requirements.txt`.

---

## 1. Codebases required on the host

| Repo | Role |
|---|---|
| `refuaAutomationCore` (this repo) | Framework: `EnvironmentManager`, `SessionStateManager`, `BasePage`, `DeviceManager`, `ArtifactManager` |
| `refuaAutomationTests` (separate repo) | Actual `tests/`, page objects, `pytest.ini` markers, `.env.*` credential files |

The test repo's `requirements.txt` is what pulls in `refua-automation-core` — install
from there, not from this repo alone.

---

## 2. Base OS / container image

- Linux (Ubuntu 22.04/24.04) — simplest for Playwright's browser dependencies.
- Docker: start from `mcr.microsoft.com/playwright/python:v<X>` pinned to the same
  version as the `playwright` pip package in `requirements.txt`. Version mismatch
  between the image's bundled browsers and the pip package is the most common
  "browser executable not found" failure.
- Python 3.9–3.12 (`setup.py`'s `python_requires`).

## 3. Playwright system dependencies

```bash
pip install -r requirements.txt          # from the test repo
playwright install --with-deps chromium firefox webkit
```

`--with-deps` installs OS shared libs (libnss3, libatk, libgbm, fonts, etc.). Skipping
it is fine on the Microsoft image (already baked in) but required on a bare Ubuntu VM.

## 4. Java runtime + Allure

- JRE 11+ — required by the Allure commandline/service regardless of which serving
  approach below is used.
- Allure commandline (`allure` CLI) if generating reports manually, **or** the
  `allure-docker-service` image if running the always-on server (recommended, see §7).

## 5. Isolation requirements for parallel workers

- `pytest-xdist` installed (test repo's `requirements.txt`).
- `--dist=loadscope` (safer default) or `--dist=loadgroup` (group by marker — useful
  for device-specific tests) so workers don't split a class/module's shared setup.
- Each Playwright test must get its own **browser context** (not a shared one) — the
  framework's `BasePage.setup_browser` fixture already does this per test function;
  don't hand-roll a module-scoped context across parallel tests.
- Session files: if multiple workers hit the same session JSON concurrently, use a
  read-only mount for `SESSION_DIR` (workers only read captured sessions, they don't
  write during test runs) — writing only happens in the separate `capture_session.py`
  step, which should never run concurrently with test workers.
- Artifacts: `ArtifactManager` already namespaces output per test name + timestamp,
  so parallel workers won't collide on video/screenshot paths — verify
  `ARTIFACTS_DIR` is a shared volume all workers can write to if running in separate
  containers.
- Mark any test with shared mutable state `@pytest.mark.sequential` and exclude it
  from the parallel run (`-m "not sequential"`), then run it separately.

## 6. Sizing

| Resource | Guidance |
|---|---|
| RAM | ~200MB per parallel worker/browser instance; reserve ~1GB for the OS. 4GB host → 2–4 workers, 8GB → 4–8 workers. |
| CPU | ~1 vCPU per 1–2 workers. |
| Disk (browsers) | ~1–2GB for chromium + firefox + webkit binaries. |
| Disk (artifacts) | Only failed-test videos/screenshots persist (passing-test artifacts auto-delete) — budget per failure rate, not per total test count. |
| Disk (Allure) | `allure-results` (raw, small JSON per test) + `allure-report` (generated static site) + `history/` (must persist across runs for trend graphs — see §7). |

## 7. Always-on Allure server

`allure serve` is not suitable here — it's a temporary process that exits when you
close it and serves only the last run. For a server that lives continuously and
accumulates trend history across runs, use one of:

**Option A — `allure-docker-service` (recommended for "always on")**
- Runs as a long-lived Docker service (`restart: always` in `docker-compose.yml`),
  exposing a REST API + UI on a fixed port.
- Watches a results directory per "project" and auto-regenerates the report when new
  results land — no manual `allure generate` step needed.
- Preserves `history/` automatically between runs, so trend/duration graphs work.
- Requires a persistent volume for `allure-results` per project and its own data dir.

**Option B — manual generate + static serve**
- After each test run: copy the previous `allure-report/history/` folder into the new
  `allure-results/history/` *before* running `allure generate` (this is what makes
  trend graphs continuous — skip it and every report starts from zero history).
- Serve the generated static `allure-report/` directory with nginx (or similar) as a
  persistent service, rather than `allure serve`.
- More manual wiring than Option A; only worth it if you don't want another daemon.

**Either option needs:**
- A fixed, firewalled port (don't rely on Allure's ephemeral random port from
  `allure serve`).
- If exposed beyond localhost: a reverse proxy (nginx/traefik) in front for HTTPS and
  basic auth/IP allowlisting — this report contains screenshots/videos of an internal
  medical system, treat it as sensitive.
- A process supervisor keeping it alive: `docker-compose` with `restart: always`, or a
  `systemd` unit if running outside Docker.

## 8. Persistent volumes (don't bake into the image)

| Volume | Contents | Notes |
|---|---|---|
| Session dir | `auth_state_{env}_{browser}_latest.json` | Written by `capture_session.py`, read-only for test runs |
| `.env.*` files | Credentials | Provisioned via secret manager/CI injection, never in the image |
| Artifacts dir | Failed-test videos/screenshots | Shared across parallel workers |
| `allure-results` | Raw per-test JSON | Fed continuously by test runs |
| `allure-report` / service data | Generated report + history | Must survive container restarts — this is the "lives all the time" state |

## 9. Networking

- The host must be able to resolve and reach `*.medical.idf.il` (test/preprod/prod) —
  this is an internal network requirement, not a "pick the nearest cloud region"
  decision. Confirm with whoever owns network access to that environment before
  provisioning; a generic public-cloud VM likely cannot reach it without VPN/direct
  connect/on-prem placement.
- The Allure server's port needs to be reachable by whoever views reports (team
  network/VPN), separately from the test-execution host's need to reach
  `*.medical.idf.il`. These are two different network paths — don't assume one
  covers the other.

## 10. Quick checklist

- [ ] Both repos present, deps installed from the **test repo's** requirements.txt
- [ ] `playwright install --with-deps` run (or Microsoft Playwright image used)
- [ ] JRE installed for Allure
- [ ] `pytest-xdist` installed, `--dist=loadscope` or `loadgroup` chosen
- [ ] Sequential-only tests marked and excluded from parallel run
- [ ] Session dir mounted read-only for test runs; capture step run separately
- [ ] `.env.*` provisioned via secrets, not baked into image
- [ ] Allure server running as a persistent service (`allure-docker-service` or
      nginx + history-preserving generate script), not `allure serve`
- [ ] `allure-results`/`allure-report`/history on a volume that survives restarts
- [ ] Network path to `*.medical.idf.il` confirmed with network/security owners
- [ ] Allure server port firewalled/proxied appropriately for internal viewers
