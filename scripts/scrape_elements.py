#!/usr/bin/env python
"""
scrape_elements.py - Catalog every meaningful UI element of the MEDITIK app.

Walks the app page-by-page (home + each navbar menu item) and, optionally, opens
each speed-dial action form, recording for every element:

    * name of the element   (accessible name / text / placeholder / tag)
    * have data-testid       (yes / no)
    * identification         (short, prioritized xpath)

Two ways to reach an authenticated session:

  1. ATTACH to a Chrome you already logged into (recommended - handles 2FA):
       # start Chrome once with a debug port, log in to MEDITIK, then:
       chrome.exe --remote-debugging-port=9222 --user-data-dir=%USERPROFILE%\\.meditik_debug_profile
       python scripts/scrape_elements.py --cdp http://127.0.0.1:9222

  2. HEADLESS with a stored Playwright storage_state (bypasses 2FA if fresh):
       python scripts/scrape_elements.py --session %USERPROFILE%\\.refua_sessions\\auth_state_meditek_test_chromium_latest.json

Outputs (into --out-dir, default ./meditik_scrape_output):
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
from pathlib import Path

from playwright.sync_api import sync_playwright

DEFAULT_BASE = "https://meditik.test.medical.idf.il"
HOME_PATH = "/home"
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
  const seen=new Set(),rows=[];
  document.querySelectorAll(SELECTOR).forEach(el=>{if(!isVisible(el))return;const xp=shortXPath(el);
    const key=el.tagName+'|'+name(el)+'|'+xp;if(seen.has(key))return;seen.add(key);
    rows.push({tag:el.tagName.toLowerCase(),name:name(el),
      has_testid:el.hasAttribute('data-testid')?'yes':'no',
      testid:el.getAttribute('data-testid')||'',xpath:xp});});
  return rows;
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


def write_outputs(results, out_dir):
    csv_path = out_dir / "elements.csv"
    json_path = out_dir / "elements.json"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["page", "name of the element", "have data-testid", "identification (short xpath)"])
        for pg, d in results.items():
            if d.get("off_domain"):
                continue
            for r in d["rows"]:
                w.writerow([pg, r["name"], r["has_testid"], r["xpath"]])
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


def main(argv=None):
    ap = argparse.ArgumentParser(description="Scrape MEDITIK UI elements into a data-testid / xpath catalog.")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--cdp", help="Attach to a running Chrome, e.g. http://127.0.0.1:9222")
    src.add_argument("--session", help="Path to a Playwright storage_state JSON (headless launch)")
    ap.add_argument("--base", default=DEFAULT_BASE, help="App base URL")
    ap.add_argument("--out-dir", default="meditik_scrape_output", help="Output directory")
    ap.add_argument("--forms", action="store_true", help="Also open each speed-dial action form")
    ap.add_argument("--screenshots", action="store_true", help="Save a screenshot per page/form")
    ap.add_argument("--headful", action="store_true", help="With --session, show the browser window")
    args = ap.parse_args(argv)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    shots_dir = out_dir / "shots"
    if args.screenshots:
        shots_dir.mkdir(exist_ok=True)

    with sync_playwright() as p:
        if args.cdp:
            browser = p.chromium.connect_over_cdp(args.cdp)
            ctx = browser.contexts[0]
            page = next((pg for pg in ctx.pages if "meditik" in pg.url), ctx.pages[0])
            page.bring_to_front()
            results = crawl(page, args.base, args.forms, args.screenshots, shots_dir)
        else:
            sess = Path(args.session)
            if not sess.exists():
                print(f"Session file not found: {sess}", file=sys.stderr)
                return 2
            browser = p.chromium.launch(headless=not args.headful)
            ctx = browser.new_context(storage_state=str(sess), ignore_https_errors=True)
            page = ctx.new_page()
            page.goto(args.base + HOME_PATH, wait_until="domcontentloaded", timeout=60000)
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
