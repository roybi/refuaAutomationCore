#!/usr/bin/env python
"""
scrape_elements.py - Catalog every meaningful UI element of the MEDITIK app.

Walks the app page-by-page (home + each navbar menu item) and, optionally, opens
each speed-dial action form, recording for every element:

    * name of the element   (accessible name / text / placeholder / tag)
    * have data-testid       (yes / no)
    * identification         (short, prioritized xpath)

Three ways to reach an authenticated session:

The target URL is built from --app (meditek/meditik, cpr-go/cpr) and --env
(test/preprod/prod) via refua_core's EnvironmentManager registry.

  1. ATTACH to a Chrome you already logged into (recommended - handles 2FA):
       chrome.exe --remote-debugging-port=9222 --user-data-dir=%USERPROFILE%\\.meditik_debug_profile
       python scripts/scrape_elements.py --app meditek --env test --cdp http://127.0.0.1:9222

  2. With a stored session (auto-resolved from app+env when no path is given):
       python scripts/scrape_elements.py --app meditek --env test --session
       python scripts/scrape_elements.py --app cpr --env test --session --headful

  3. LIVE: open a fresh browser, log in manually, crawl once the start path is reached:
       python scripts/scrape_elements.py --app cpr --env preprod --live

Outputs (into --out-dir, default ./{app}_{env}_scrape_output):
    elements.csv     flat table: page,name,have_data-testid,xpath
    elements.json    grouped by page/form
    shots/*.png      one full-page screenshot per page (with --screenshots)

Off-domain speed-dial actions (WhatsApp, torim.*) are recorded but flagged
`off_domain` and excluded from the CSV so the catalog stays MEDITIK-only.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

from refua_core.config.environment import (get_app_base_url, known_app_names,
                                           resolve_app_name)

HOME_PATH = "/home"
# Per-app landing path after login; apps not listed fall back to HOME_PATH.
APP_START_PATHS = {"meditek": "/home", "cpr-go": "/visit"}
FAB_SELECTOR = "button[aria-label='SpeedDial']"
MENU_BTN = "#menu-button"
CLOSE_BTN = "#close-menu-button"
HOME_BTN = "#home-menu-button"

# --- in-page JS -------------------------------------------------------------

EXTRACT_JS = r"""
() => {
  const SELECTOR = ['a','button','input','select','textarea','label','[role]',
    '[data-testid]','[onclick]','h1','h2','h3','h4','h5','h6','img',
    '[contenteditable="true"]','summary','[tabindex]'].join(',');
  function isVisible(el){const r=el.getBoundingClientRect();if(r.width===0&&r.height===0)return false;
    const s=getComputedStyle(el);if(s.display==='none'||s.visibility==='hidden'||s.opacity==='0')return false;return true;}
  function shortXPath(el){const tag=el.tagName.toLowerCase();const tid=el.getAttribute('data-testid');
    if(tid)return `//${tag}[@data-testid='${tid}']`;
    if(el.id&&!/^[0-9]/.test(el.id)&&!/[:.]/.test(el.id))return `//${tag}[@id='${el.id}']`;
    for(const a of ['name','aria-label','placeholder','title','type']){const v=el.getAttribute(a);
      if(v&&v.length<40)return `//${tag}[@${a}='${v.replace(/'/g,"")}']`;}
    const txt=(el.textContent||'').trim().replace(/\s+/g,' ');
    if(txt&&txt.length<30&&!el.querySelector('*'))return `//${tag}[normalize-space(.)='${txt.replace(/'/g,"")}']`;
    let idx=1,sib=el;while((sib=sib.previousElementSibling))if(sib.tagName===el.tagName)idx++;
    const parent=el.parentElement;const ptag=parent?parent.tagName.toLowerCase():'';return `//${ptag}/${tag}[${idx}]`;}
  function name(el){const tag=el.tagName.toLowerCase();const al=el.getAttribute('aria-label');if(al)return al.trim();
    if(tag==='input'||tag==='textarea'||tag==='select')return el.getAttribute('placeholder')||el.getAttribute('name')||el.getAttribute('type')||tag;
    if(tag==='img')return el.getAttribute('alt')||'(image)';
    const t=(el.textContent||'').trim().replace(/\s+/g,' ');if(t)return t.slice(0,60);
    return el.getAttribute('title')||el.getAttribute('name')||tag;}
  function elementType(el){const tag=el.tagName.toLowerCase();const role=(el.getAttribute('role')||'').toLowerCase();
    const inputType=(el.getAttribute('type')||'').toLowerCase();
    if(role==='dialog'||role==='alertdialog')return 'Message Box';
    if(role==='alert'||role==='status')return 'Alert Message';
    if(role==='tooltip')return 'Tooltip';
    if(role==='progressbar')return 'Progress Bar';
    if(role==='switch')return 'Toggle Switch';
    if(role==='tab')return 'Tab';
    if(role==='menuitem'||role==='menu')return 'Menu Item';
    if(role==='combobox'||role==='listbox')return 'Dropdown';
    if(role==='checkbox')return 'Checkbox';
    if(role==='radio')return 'Radio Button';
    if(role==='button')return 'Button';
    if(role==='link')return 'Link';
    if(tag==='img')return 'Image';
    if(tag==='a')return 'Link';
    if(tag==='button')return 'Button';
    if(tag==='select')return 'Dropdown';
    if(tag==='textarea')return 'Text Area';
    if(tag==='label')return 'Label';
    if(tag==='summary')return 'Expandable Section';
    if(/^h[1-6]$/.test(tag))return 'Heading';
    if(tag==='input'){
      if(inputType==='checkbox')return 'Checkbox';
      if(inputType==='radio')return 'Radio Button';
      if(inputType==='button'||inputType==='submit'||inputType==='reset')return 'Button';
      if(inputType==='file')return 'File Upload';
      if(inputType==='range')return 'Slider';
      return 'Text Input';}
    if(el.hasAttribute('contenteditable'))return 'Text Area';
    if(el.hasAttribute('onclick'))return 'Clickable Element';
    if(el.hasAttribute('tabindex'))return 'Focusable Element';
    return tag.charAt(0).toUpperCase()+tag.slice(1);}
  const seen=new Set(),rows=[];
  document.querySelectorAll(SELECTOR).forEach(el=>{if(!isVisible(el))return;const xp=shortXPath(el);
    const key=el.tagName+'|'+name(el)+'|'+xp;if(seen.has(key))return;seen.add(key);
    rows.push({tag:el.tagName.toLowerCase(),name:name(el),type:elementType(el),
      has_testid:el.hasAttribute('data-testid')?'yes':'no',
      testid:el.getAttribute('data-testid')||'',xpath:xp});});
  return rows;
}
"""

DISCOVER_NAV_JS = r"""
() => {
  function isVisible(el){const r=el.getBoundingClientRect();if(r.width===0&&r.height===0)return false;
    const s=getComputedStyle(el);if(s.display==='none'||s.visibility==='hidden'||s.opacity==='0')return false;return true;}
  function label(el){const al=el.getAttribute('aria-label');if(al)return al.trim();
    const t=(el.textContent||'').trim().replace(/\s+/g,' ');if(t)return t.slice(0,60);
    return el.getAttribute('title')||el.getAttribute('placeholder')||el.tagName.toLowerCase();}
  function selector(el){const tid=el.getAttribute('data-testid');if(tid)return `[data-testid='${tid}']`;
    if(el.id&&!/^[0-9]/.test(el.id))return `#${el.id}`;return null;}
  const containers=document.querySelectorAll("nav,[role='navigation'],aside,header,.sidebar,.menu,.nav,.navbar");
  const scope=containers.length?Array.from(containers):[document.body];
  const seen=new Set(),items=[];
  scope.forEach(c=>{c.querySelectorAll("a[href],button,[role='menuitem'],[role='button']").forEach(el=>{
    if(!isVisible(el))return;const lb=label(el);if(!lb)return;
    const href=el.tagName.toLowerCase()==='a'?el.getAttribute('href'):null;
    const key=lb+'|'+(href||'');if(seen.has(key))return;seen.add(key);
    items.push({label:lb,href,selector:selector(el),testid:el.getAttribute('data-testid')||''});});});
  return items;
}
"""

MENU_JS = r"""
() => {const items=[];document.querySelectorAll("[id^='menu-item-']").forEach(b=>{
  items.push({id:b.id,testid:b.getAttribute('data-testid')||'',label:(b.textContent||'').trim().slice(0,40)});});
  return items;}
"""

ACTIONS_JS = r"""
() => {const acts=[];document.querySelectorAll("[data-testid^='meditik-speed-dial-btn-']").forEach(b=>{
  const tid=b.getAttribute('data-testid');
  if(tid&&tid!=='meditik-speed-dial-btn-trigger')
    acts.push({testid:tid,label:(b.textContent||b.getAttribute('aria-label')||'').trim().slice(0,50)});});
  return acts;}
"""


def slug(s: str) -> str:
    s = re.sub(r"[^\w\u0590-\u05FF]+", "_", s).strip("_")
    return s or "page"


def extract(page):
    page.wait_for_timeout(1500)
    return page.evaluate(EXTRACT_JS)


def open_home(page, base):
    try:
        page.locator(HOME_BTN).first.click(timeout=4000)
    except Exception:
        page.goto(base + HOME_PATH, wait_until="domcontentloaded", timeout=20000)
    page.wait_for_selector(FAB_SELECTOR, timeout=15000)
    page.wait_for_timeout(1200)


def open_speed_dial(page):
    fab = page.locator(FAB_SELECTOR).first
    try:
        fab.click(timeout=6000)
    except Exception:
        fab.click(timeout=6000, force=True)
    page.wait_for_timeout(900)


def crawl(page, base, do_forms, do_shots, shots_dir):
    results = {}

    open_home(page, base)
    rows = extract(page)
    if do_shots:
        page.screenshot(path=str(shots_dir / "00_home.png"), full_page=True)
    results["בית (Home)"] = {"url": page.url, "kind": "page", "rows": rows}
    print(f"PAGE Home -> {len(rows)} elements")

    # menu manifest
    page.locator(MENU_BTN).first.click(timeout=5000)
    page.wait_for_timeout(800)
    menu = page.evaluate(MENU_JS)
    page.locator(CLOSE_BTN).first.click(timeout=5000)
    page.wait_for_timeout(500)

    for idx, item in enumerate(menu, start=1):
        label = item["label"] or item["id"]
        try:
            page.locator(MENU_BTN).first.click(timeout=5000)
            page.wait_for_timeout(700)
            page.locator("#" + item["id"]).first.click(timeout=6000)
            page.wait_for_load_state("domcontentloaded", timeout=15000)
            page.wait_for_timeout(1500)
            rows = extract(page)
            if do_shots:
                page.screenshot(path=str(shots_dir / f"{idx:02d}_{slug(label)}.png"), full_page=True)
            results[label] = {"url": page.url, "kind": "page", "rows": rows}
            print(f"PAGE {label} -> {len(rows)} elements | {page.url}")
        except Exception as e:
            results[label] = {"url": page.url, "kind": "page", "rows": [], "error": f"{type(e).__name__}: {str(e)[:120]}"}
            print(f"PAGE {label} -> ERROR {type(e).__name__}")

    if do_forms:
        open_home(page, base)
        open_speed_dial(page)
        actions = page.evaluate(ACTIONS_JS)
        page.keyboard.press("Escape")
        page.wait_for_timeout(400)
        for i, act in enumerate(actions, start=1):
            label = act["label"] or act["testid"]
            try:
                open_home(page, base)
                open_speed_dial(page)
                page.locator(f"[data-testid='{act['testid']}']").first.click(timeout=6000)
                page.wait_for_timeout(2500)
                off_domain = base not in page.url
                rows = [] if off_domain else extract(page)
                if do_shots and not off_domain:
                    page.screenshot(path=str(shots_dir / f"form_{i:02d}_{slug(label)}.png"), full_page=True)
                results[f"[form] {label}"] = {
                    "url": page.url, "kind": "form", "off_domain": off_domain, "rows": rows,
                }
                flag = " (off-domain, skipped)" if off_domain else ""
                print(f"FORM {label} -> {len(rows)} elements | {page.url}{flag}")
            except Exception as e:
                results[f"[form] {label}"] = {"url": page.url, "kind": "form", "rows": [], "error": f"{type(e).__name__}: {str(e)[:120]}"}
                print(f"FORM {label} -> ERROR {type(e).__name__}")

    return results


def crawl_generic(page, base, do_shots, shots_dir, max_pages=25):
    """App-agnostic crawl: extracts the current page, then discovers and
    follows nav/sidebar links generically (no assumptions about menu markup).
    """
    results = {}
    start_url = page.url

    def snapshot(label, idx):
        page.wait_for_timeout(1200)
        rows = extract(page)
        if do_shots:
            page.screenshot(path=str(shots_dir / f"{idx:02d}_{slug(label)}.png"), full_page=True)
        results[label] = {"url": page.url, "kind": "page", "rows": rows}
        print(f"PAGE {label} -> {len(rows)} elements | {page.url}")

    snapshot("visit (start)", 0)
    nav_items = page.evaluate(DISCOVER_NAV_JS)
    print(f"Discovered {len(nav_items)} candidate nav items")

    visited_urls = {page.url}
    for idx, item in enumerate(nav_items[:max_pages], start=1):
        label = item["label"]
        dedup_key = label + "|" + (item.get("href") or item.get("testid") or item.get("selector") or str(idx))
        if dedup_key in results:
            continue
        try:
            page.goto(start_url, wait_until="domcontentloaded", timeout=20000)
            page.wait_for_timeout(600)
            href = item.get("href")
            if href and (href.startswith("http") or href.startswith("/")):
                target = href if href.startswith("http") else base + href
                if target in visited_urls:
                    continue
                page.goto(target, wait_until="domcontentloaded", timeout=20000)
            else:
                if item.get("testid"):
                    locator = page.locator(f"[data-testid='{item['testid']}']").first
                elif item.get("selector"):
                    locator = page.locator(item["selector"]).first
                else:
                    locator = page.get_by_text(label, exact=False).first
                locator.click(timeout=6000)
                page.wait_for_load_state("domcontentloaded", timeout=15000)
            if page.url in visited_urls:
                continue
            visited_urls.add(page.url)
            snapshot(dedup_key, idx)
        except Exception as e:
            results[dedup_key] = {"url": page.url, "kind": "page", "rows": [], "error": f"{type(e).__name__}: {str(e)[:120]}"}
            print(f"PAGE {dedup_key} -> ERROR {type(e).__name__}")

    return results


def write_outputs(results, out_dir):
    csv_path = out_dir / "elements.csv"
    json_path = out_dir / "elements.json"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["page", "name of the element", "type of element", "have data-testid", "identification (short xpath)"])
        for pg, d in results.items():
            if d.get("off_domain"):
                continue
            for r in d["rows"]:
                w.writerow([pg, r["name"], r.get("type", ""), r["has_testid"], r["xpath"]])
    json_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    summary = []
    for pg, d in results.items():
        rows = d["rows"]
        summary.append({
            "page": pg, "kind": d.get("kind"),
            "reached": "no" if d.get("error") or d.get("off_domain") or not rows else "yes",
            "url": d["url"], "elements": len(rows),
            "with_testid": sum(1 for r in rows if r["has_testid"] == "yes"),
            "note": ("off_domain" if d.get("off_domain") else d.get("error", "")),
        })
    return csv_path, json_path, summary


def wait_for_path(pages, ctx, target_path, wait_timeout, report_every=5, mark=False):
    """Poll all known tabs (tracking new ones via ctx's 'page' event) until
    one reaches a URL containing target_path (and not 'login'). Returns the
    matched Page, or None on timeout. If mark=True, keeps re-injecting a
    visible banner on every tracked tab (survives navigations) so a human
    can confirm they're looking at the automation-controlled window.
    """
    ctx.on("page", lambda new_pg: pages.append(new_pg))
    deadline = time.monotonic() + wait_timeout
    last_report = 0.0
    banner_js = (
        "() => { if (document.getElementById('__automation_marker__')) return; "
        "const d=document.createElement('div'); d.id='__automation_marker__'; "
        "d.textContent='AUTOMATION WINDOW \u2014 SCRAPE_ELEMENTS.PY'; "
        "d.style.cssText='position:fixed;top:0;left:0;right:0;z-index:2147483647;background:#ff00ff;"
        "color:#fff;font-size:20px;font-weight:bold;text-align:center;padding:8px;'; document.body.appendChild(d); }"
    )
    while time.monotonic() < deadline:
        for pg in list(pages):
            try:
                u = pg.url
                if mark:
                    pg.evaluate(banner_js)
            except Exception:
                continue
            if target_path in u and "login" not in u.lower():
                return pg
        now = time.monotonic()
        if now - last_report > report_every:
            urls = []
            for pg in list(pages):
                try:
                    urls.append(pg.url)
                except Exception:
                    urls.append("<closed>")
            print(f"[debug] {len(pages)} tab(s): {urls}", flush=True)
            last_report = now
        time.sleep(1)
    return None


def main(argv=None):
    ap = argparse.ArgumentParser(description="Scrape MEDITIK UI elements into a data-testid / xpath catalog.")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--cdp", help="Attach to a running Chrome, e.g. http://127.0.0.1:9222")
    src.add_argument("--session", nargs="?", const="auto",
                     help="Path to a storage_state JSON; pass without a value to use ~/.refua_sessions/auth_state_{app}_{env}_chromium_latest.json")
    src.add_argument("--live", action="store_true", help="Launch a fresh headed browser, wait for manual login to reach --start-path, then crawl")
    ap.add_argument("--app", default="meditek", choices=known_app_names(), help="System to scrape (meditek/meditik, cpr-go/cpr)")
    ap.add_argument("--env", default="test", choices=["test", "preprod", "prod"], help="Environment")
    ap.add_argument("--base", default=None, help="Override the base URL resolved from --app/--env")
    ap.add_argument("--out-dir", default=None, help="Output directory (default: {app}_{env}_scrape_output)")
    ap.add_argument("--forms", action="store_true", help="Also open each speed-dial action form")
    ap.add_argument("--screenshots", action="store_true", help="Save a screenshot per page/form")
    ap.add_argument("--headful", action="store_true", help="With --session, show the browser window")
    ap.add_argument("--generic", action="store_true", help="Use app-agnostic nav discovery instead of the MEDITEK-specific crawl (for other apps, e.g. cpr-go)")
    ap.add_argument("--start-path", default=None, help="Path to land on after login (default: per app, e.g. /home for meditek, /visit for cpr-go)")
    ap.add_argument("--wait-timeout", type=int, default=900, help="With --live, max seconds to wait for manual login (default 900)")
    args = ap.parse_args(argv)

    args.app = resolve_app_name(args.app)
    args.base = (args.base or get_app_base_url(args.app, args.env)).rstrip("/")
    if args.start_path is None:
        args.start_path = APP_START_PATHS.get(args.app, HOME_PATH)
    # The default crawl() is hardcoded to MEDITEK's menu/FAB markup.
    if args.app != "meditek":
        args.generic = True
    if args.session == "auto":
        args.session = str(Path.home() / ".refua_sessions" / f"auth_state_{args.app}_{args.env}_chromium_latest.json")
    if args.out_dir is None:
        args.out_dir = f"{args.app}_{args.env}_scrape_output"
    print(f"App={args.app} Env={args.env} Base={args.base} StartPath={args.start_path}")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    shots_dir = out_dir / "shots"
    if args.screenshots:
        shots_dir.mkdir(exist_ok=True)

    with sync_playwright() as p:
        if args.cdp:
            browser = p.chromium.connect_over_cdp(args.cdp)
            ctx = browser.contexts[0]
            host_hint = urlparse(args.base).hostname or ""
            page = next((pg for pg in ctx.pages if host_hint and host_hint in pg.url), ctx.pages[0])
            page.bring_to_front()
            if args.generic:
                results = crawl_generic(page, args.base, args.screenshots, shots_dir)
            else:
                results = crawl(page, args.base, args.forms, args.screenshots, shots_dir)
        elif args.live:
            browser = p.chromium.launch(headless=False, args=["--start-maximized"])
            ctx = browser.new_context(no_viewport=True, ignore_https_errors=True)
            pages = [ctx.new_page()]
            pages[0].goto(args.base, wait_until="domcontentloaded", timeout=60000)
            print(f"Live browser opened at {pages[0].url}")
            target_path = args.start_path
            print(f"Waiting up to {args.wait_timeout}s for manual login — reach a URL containing '{target_path}' ...")
            page = wait_for_path(pages, ctx, target_path, args.wait_timeout, mark=True)
            if page is None:
                print(f"Timed out waiting for login. Open tabs: {[pg.url for pg in pages]}", file=sys.stderr)
                browser.close()
                return 3
            page.bring_to_front()
            print(f"Reached {page.url} — starting crawl")
            if args.generic:
                results = crawl_generic(page, args.base, args.screenshots, shots_dir)
            else:
                results = crawl(page, args.base, args.forms, args.screenshots, shots_dir)
            browser.close()
        else:
            sess = Path(args.session)
            if not sess.exists():
                print(f"Session file not found: {sess}", file=sys.stderr)
                return 2
            # Our session files wrap Playwright's storage_state under a
            # "storage_state" key (plus "metadata"/"tokens"); unwrap it here
            # since new_context() expects the native top-level schema.
            session_json = json.loads(sess.read_text(encoding="utf-8"))
            storage_state = session_json.get("storage_state", session_json)
            browser = p.chromium.launch(headless=not args.headful, args=["--start-maximized"] if args.headful else None)
            ctx = browser.new_context(storage_state=storage_state, ignore_https_errors=True, no_viewport=args.headful)
            pages = [ctx.new_page()]
            start_path = args.start_path
            pages[0].goto(args.base + start_path, wait_until="domcontentloaded", timeout=60000)
            page = pages[0]
            # The SPA can briefly show start_path then client-side redirect
            # (e.g. to a "select active user" step) a moment after load —
            # wait for that to settle before deciding whether we're really there.
            page.wait_for_timeout(2000)
            print(f"[debug] headful={args.headful} start_path={start_path!r} landed_on={page.url!r}", flush=True)
            if args.headful:
                try:
                    page.evaluate(
                        "() => { const d=document.createElement('div'); d.textContent='AUTOMATION WINDOW \u2014 SCRAPE_ELEMENTS.PY'; "
                        "d.style.cssText='position:fixed;top:0;left:0;right:0;z-index:2147483647;background:#ff00ff;"
                        "color:#fff;font-size:20px;font-weight:bold;text-align:center;padding:8px;'; document.body.appendChild(d); }"
                    )
                except Exception:
                    pass
            if args.headful and start_path not in page.url:
                print(f"Session landed on {page.url} instead of {start_path} — complete the remaining manual step in the browser.")
                print(f"Waiting up to {args.wait_timeout}s for a URL containing '{start_path}' ...")
                matched = wait_for_path(pages, ctx, start_path, args.wait_timeout, mark=True)
                if matched is None:
                    print(f"Timed out waiting. Open tabs: {[pg.url for pg in pages]}", file=sys.stderr)
                    browser.close()
                    return 3
                page = matched
                page.bring_to_front()
            if args.generic:
                results = crawl_generic(page, args.base, args.screenshots, shots_dir)
            else:
                results = crawl(page, args.base, args.forms, args.screenshots, shots_dir)
            browser.close()

    csv_path, json_path, summary = write_outputs(results, out_dir)
    print("SUMMARY", json.dumps(summary, ensure_ascii=False, indent=2))
    print("CSV", csv_path)
    print("JSON", json_path)
    total = sum(len(d["rows"]) for d in results.values() if not d.get("off_domain"))
    print(f"TOTAL_PAGES {len(results)} TOTAL_ELEMENTS {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
