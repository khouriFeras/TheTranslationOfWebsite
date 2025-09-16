#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
register_translations.py
- Safe Shopify translations register (products) with digest handling.
- Input: Excel (.xlsx/.xls), CSV, or JSON.
- Map your columns via CLI flags.
- Uses 'body_html' for the translation description (correct key).
- Optional --ensure-base seeds primary content + polls for digests.

Env (.env):
  SHOPIFY_STORE_DOMAIN=your-shop.myshopify.com
  SHOPIFY_ADMIN_ACCESS_TOKEN=shpat_XXXXXXXXXXXXXXXX
  SHOPIFY_API_VERSION=2025-07
  TARGET_LANGUAGE=en           # or en-GB, etc. (can be overridden with --locale)

Scopes:
  read_translations, write_translations
  write_products (only if you use --ensure-base)

Examples:
  python register_translations.py --in products.xlsx --sheet Sheet1 --id-col id --title-col title_en --desc-col descriptionHtml_en --locale en --ensure-base
  python register_translations.py --in products.json --locale en-GB --ensure-base
  python register_translations.py --id gid://shopify/Product/8923... --title-en "Title EN" --desc-en "<p>Desc EN</p>" --locale en
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Any

import requests
from dotenv import load_dotenv

# -------- env --------
load_dotenv()
SHOPIFY_STORE_DOMAIN = os.getenv("SHOPIFY_STORE_DOMAIN", "").strip()
SHOPIFY_ADMIN_ACCESS_TOKEN = os.getenv("SHOPIFY_ADMIN_ACCESS_TOKEN", "").strip()
SHOPIFY_API_VERSION = os.getenv("SHOPIFY_API_VERSION", "2025-07").strip()
TARGET_LANGUAGE_DEFAULT = os.getenv("TARGET_LANGUAGE", "en").strip()

# -------- GraphQL helpers --------
def endpoint() -> str:
    return f"https://{SHOPIFY_STORE_DOMAIN}/admin/api/{SHOPIFY_API_VERSION}/graphql.json"

def headers() -> Dict[str, str]:
    return {"X-Shopify-Access-Token": SHOPIFY_ADMIN_ACCESS_TOKEN, "Content-Type": "application/json"}

def gql(query: str, variables: dict) -> dict:
    r = requests.post(endpoint(), headers=headers(),
                      data=json.dumps({"query": query, "variables": variables}),
                      timeout=60)
    r.raise_for_status()
    data = r.json()
    if data.get("errors"):
        raise RuntimeError(json.dumps(data["errors"], ensure_ascii=False))
    return data

def ensure_gid(product_id: str) -> str:
    return product_id if product_id.startswith("gid://shopify/Product/") else f"gid://shopify/Product/{product_id}"

def normalize_cell(v: Any) -> str:
    if v is None:
        return ""
    # Excel often gives floats for numeric ids; coerce cleanly
    if isinstance(v, (int,)) and not isinstance(v, bool):
        return str(v)
    if isinstance(v, float):
        if v.is_integer():
            return str(int(v))
        return str(v)
    return str(v).strip()

# -------- GraphQL documents --------
QUERY_DIGESTS = """
query($id: ID!) {
  translatableResource(resourceId: $id) {
    translatableContent { key digest }
  }
}
""".strip()

QUERY_VERIFY = """
query($id: ID!, $locale: String!) {
  translatableResource(resourceId: $id) {
    translations(locale: $locale) { key value locale outdated }
  }
}
""".strip()

MUT_REGISTER = """
mutation RegisterTranslations($resourceId: ID!, $translations: [TranslationInput!]!) {
  translationsRegister(resourceId: $resourceId, translations: $translations) {
    userErrors { field message }
    translations { key locale }
  }
}
""".strip()

MUT_UPDATE_PRIMARY = """
mutation UpdatePrimary($input: ProductInput!) {
  productUpdate(input: $input) {
    product { id title descriptionHtml }
    userErrors { field message }
  }
}
""".strip()

# -------- core functions --------
def fetch_digests(product_gid: str) -> Dict[str, str]:
    data = gql(QUERY_DIGESTS, {"id": product_gid})
    items = (data.get("data", {}).get("translatableResource", {}) or {}).get("translatableContent", []) or []
    # keys commonly include: title, handle, body_html, product_type
    return {it["key"]: it.get("digest", "") for it in items if it.get("key")}

def verify_locale(product_gid: str, locale: str) -> List[dict]:
    data = gql(QUERY_VERIFY, {"id": product_gid, "locale": locale})
    return (data.get("data", {}).get("translatableResource", {}) or {}).get("translations", []) or []

def update_primary(product_gid: str, base_title: Optional[str], base_desc_html: Optional[str]) -> None:
    inp: Dict[str, str] = {"id": product_gid}
    if base_title is not None:
        inp["title"] = base_title
    if base_desc_html is not None:
        inp["descriptionHtml"] = base_desc_html
    data = gql(MUT_UPDATE_PRIMARY, {"input": inp})
    errs = (data["data"]["productUpdate"]["userErrors"] or [])
    if errs:
        raise RuntimeError(f"productUpdate errors: {errs}")

def build_translations(row: Dict[str, str], locale: str, digests: Dict[str, str]) -> List[Dict[str, str]]:
    """
    Translation keys for Product:
      - 'title'
      - 'body_html'   (NOT descriptionHtml)
    """
    out: List[Dict[str, str]] = []
    title_en = normalize_cell(row.get("title_en"))
    desc_en  = normalize_cell(row.get("descriptionHtml_en"))

    if title_en:
        if not digests.get("title"):
            raise RuntimeError("Missing digest for 'title' (primary title empty or not indexed yet).")
        out.append({"key": "title", "value": title_en, "locale": locale,
                    "translatableContentDigest": digests["title"]})

    if desc_en:
        if not digests.get("body_html"):
            raise RuntimeError("Missing digest for 'body_html' (primary description empty or not indexed yet).")
        out.append({"key": "body_html", "value": desc_en, "locale": locale,
                    "translatableContentDigest": digests["body_html"]})

    return out

def register(product_gid: str, translations: List[Dict[str, str]]) -> dict:
    data = gql(MUT_REGISTER, {"resourceId": product_gid, "translations": translations})
    reg = data["data"]["translationsRegister"]
    if reg["userErrors"]:
        raise RuntimeError(f"translationsRegister errors: {reg['userErrors']}")
    return reg

# -------- input loaders --------
def load_rows_csv(p: Path, id_col: str, title_col: str, desc_col: str) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    with p.open("r", encoding="utf-8", newline="") as f:
        rdr = csv.DictReader(f)
        for r in rdr:
            rows.append({
                "id": normalize_cell(r.get(id_col)),
                "title_en": normalize_cell(r.get(title_col)),
                "descriptionHtml_en": normalize_cell(r.get(desc_col)),
            })
    return rows

def load_rows_json(p: Path, id_col: str, title_col: str, desc_col: str) -> List[Dict[str, str]]:
    data = json.loads(p.read_text(encoding="utf-8"))
    items = data if isinstance(data, list) else [data]
    rows: List[Dict[str, str]] = []
    for r in items:
        rows.append({
            "id": normalize_cell(r.get(id_col) if isinstance(r, dict) else ""),
            "title_en": normalize_cell(r.get(title_col) if isinstance(r, dict) else ""),
            "descriptionHtml_en": normalize_cell(r.get(desc_col) if isinstance(r, dict) else ""),
        })
    return rows

def load_rows_excel(p: Path, sheet: Optional[str], id_col: str, title_col: str, desc_col: str) -> List[Dict[str, str]]:
    try:
        import pandas as pd  # requires openpyxl installed
    except ImportError:
        raise SystemExit("Missing dependency: install with `pip install pandas openpyxl`")
    df = pd.read_excel(p, sheet_name=sheet if sheet else 0, dtype=object)
    df = df.fillna("")
    rows: List[Dict[str, str]] = []
    for _, r in df.iterrows():
        rows.append({
            "id": normalize_cell(r.get(id_col)),
            "title_en": normalize_cell(r.get(title_col)),
            "descriptionHtml_en": normalize_cell(r.get(desc_col)),
        })
    return rows

def load_rows_any(p: Path, sheet: Optional[str], id_col: str, title_col: str, desc_col: str) -> List[Dict[str, str]]:
    ext = p.suffix.lower()
    if ext in (".xlsx", ".xls"):
        return load_rows_excel(p, sheet, id_col, title_col, desc_col)
    if ext == ".csv":
        return load_rows_csv(p, id_col, title_col, desc_col)
    if ext == ".json":
        return load_rows_json(p, id_col, title_col, desc_col)
    raise SystemExit(f"Unsupported input type: {ext}. Use .xlsx/.xls, .csv, or .json")

# -------- main --------
def main():
    ap = argparse.ArgumentParser(description="Register product translations safely (with digests) and verify.")
    ap.add_argument("--in", dest="inp", help="Excel/CSV/JSON file with product rows", required=False)
    ap.add_argument("--sheet", help="Worksheet name (Excel only). Defaults to first sheet.", default=None)
    ap.add_argument("--id-col", default="id", help="Column name for product id/GID in your file (default: id)")
    ap.add_argument("--title-col", default="title_en", help="Column name for EN title (default: title_en)")
    ap.add_argument("--desc-col", default="descriptionHtml_en", help="Column name for EN HTML description (default: descriptionHtml_en)")

    ap.add_argument("--id", help="Single product GID or numeric id (alternative to --in)", required=False)
    ap.add_argument("--title-en", help="English title (for --id mode)", required=False)
    ap.add_argument("--desc-en", help="English description HTML (for --id mode)", required=False)

    ap.add_argument("--locale", default=TARGET_LANGUAGE_DEFAULT, help="Target locale code (e.g. en, en-GB)")
    ap.add_argument("--ensure-base", action="store_true",
                    help="If digests missing, set minimal primary content then poll for digests (needs write_products).")
    ap.add_argument("--base-title", default="—", help="Primary/base title to set if needed with --ensure-base")
    ap.add_argument("--base-desc", default="<p>—</p>", help="Primary/base descriptionHtml to set if needed with --ensure-base")
    args = ap.parse_args()

    if not SHOPIFY_STORE_DOMAIN or not SHOPIFY_ADMIN_ACCESS_TOKEN:
        raise SystemExit("Missing SHOPIFY_STORE_DOMAIN or SHOPIFY_ADMIN_ACCESS_TOKEN")

    # Prepare jobs
    jobs: List[Dict[str, str]] = []
    if args.inp:
        p = Path(args.inp)
        print(f"[Input] {p.name} (sheet={args.sheet or 'default'})  columns: id='{args.id_col}', title='{args.title_col}', desc='{args.desc_col}'")
        jobs = load_rows_any(p, args.sheet, args.id_col, args.title_col, args.desc_col)
    elif args.id and (args.title_en or args.desc_en):
        jobs = [{"id": args.id, "title_en": args.title_en or "", "descriptionHtml_en": args.desc_en or ""}]
    else:
        ap.error("Provide --in <file> OR --id + (--title-en and/or --desc-en)")

    ok, fail = 0, 0
    for i, row in enumerate(jobs, 1):
        pid = normalize_cell(row.get("id"))
        if not pid:
            print(f"[{i}] SKIP: missing id")
            fail += 1; continue

        gid = ensure_gid(pid)
        print(f"[{i}] Product: {gid}  →  locale={args.locale}")

        # 1) fetch current digests
        digests = fetch_digests(gid)
        need_title = (normalize_cell(row.get("title_en")) != "") and not digests.get("title")
        need_desc  = (normalize_cell(row.get("descriptionHtml_en")) != "") and not digests.get("body_html")

        # 2) optionally seed primary content and poll for digests
        if (need_title or need_desc) and args.ensure_base:
            print(f"    Missing digest(s) → seeding primary content (title? {need_title}, desc? {need_desc})")
            update_primary(gid,
                           args.base_title if need_title else None,
                           args.base_desc  if need_desc  else None)

            # Poll for digests (Shopify can take a moment to index)
            for attempt in range(20):  # ~14s
                time.sleep(0.7)
                digests = fetch_digests(gid)
                if (not need_title or digests.get("title")) and (not need_desc or digests.get("body_html")):
                    break
            else:
                print("    FAIL: digests not ready yet; try again in ~30–60s")
                fail += 1
                continue

        # 3) build and register translations
        try:
            translations = build_translations(row, args.locale, digests)
        except RuntimeError as e:
            print(f"    FAIL (build): {e}")
            fail += 1
            continue

        if not translations:
            print("    Nothing to register (empty title_en/descriptionHtml_en).")
            ok += 1
            continue

        try:
            reg = register(gid, translations)
        except RuntimeError as e:
            print(f"    FAIL (register): {e}")
            fail += 1
            continue

        stored = [f"{t.get('key')}@{t.get('locale')}" for t in (reg.get("translations") or [])]
        print(f"    Stored: {', '.join(stored) if stored else '(none reported)'}")

        # 4) verify
        out = verify_locale(gid, args.locale)
        if out:
            print("    Verify →")
            for t in out:
                val = (t.get("value") or "")[:120].replace("\n", " ")
                print(f"      {t['key']} [{t['locale']}]{' (outdated)' if t.get('outdated') else ''}: {val}")
        else:
            print("    Verify → (no rows). Check exact published locale code in Settings → Languages.")

        ok += 1

    print(f"\nDone. OK={ok} FAIL={fail}")

if __name__ == "__main__":
    main()
