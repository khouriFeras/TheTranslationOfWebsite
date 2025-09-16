#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations
import os, re, sys, json, time, argparse, hashlib, atexit
from pathlib import Path
from typing import Dict, Any, List, Optional

# --- OpenAI client (new or old SDK) ---
_NEW_SDK = False
try:
    from openai import OpenAI  # new SDK
    _NEW_SDK = True
except Exception:
    pass

if _NEW_SDK:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
else:
    import openai
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Please set OPENAI_API_KEY.", file=sys.stderr)
    openai.api_key = os.getenv("OPENAI_API_KEY")
    client = openai

DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# --- Disk cache ---
_CACHE: Dict[str, str] = {}
_CACHE_PATH: Optional[str] = None

def _sha_key(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()

def load_cache(path: Optional[str]) -> None:
    global _CACHE, _CACHE_PATH
    _CACHE_PATH = path
    if not path: return
    p = Path(path)
    if p.exists():
        try: _CACHE = json.load(p.open("r", encoding="utf-8"))
        except Exception: _CACHE = {}

def save_cache() -> None:
    if not _CACHE_PATH: return
    try:
        with open(_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(_CACHE, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"⚠️ Cache save failed: {e}", file=sys.stderr)

atexit.register(save_cache)

def cached_call(key: Dict[str, Any], fn):
    k = _sha_key(key)
    if k in _CACHE:
        return _CACHE[k]
    out = fn()
    _CACHE[k] = out
    return out

# --- Chat wrapper with retries ---
def _chat(messages: List[Dict[str, str]], model: str, temperature: float, max_tokens: int) -> str:
    if _NEW_SDK:
        # GPT-5 mini has different parameter requirements
        if "gpt-5" in model.lower():
            # GPT-5 mini uses max_completion_tokens and only supports temperature=1
            r = client.chat.completions.create(
                model=model, 
                messages=messages, 
                temperature=1.0,  # GPT-5 mini only supports default temperature
                max_completion_tokens=max_tokens
            )
        else:
            r = client.chat.completions.create(model=model, messages=messages, temperature=temperature, max_tokens=max_tokens)
        return r.choices[0].message.content or ""
    else:
        r = client.ChatCompletion.create(model=model, messages=messages, temperature=temperature, max_tokens=max_tokens)
        return r["choices"][0]["message"]["content"] or ""

def chat_retry(messages, model=DEFAULT_MODEL, temperature=0.0, max_tokens=2000, attempts=6, backoff_min=1.0, backoff_max=20.0):
    for i in range(1, attempts+1):
        try:
            return _chat(messages, model, temperature, max_tokens)
        except Exception as e:
            msg = str(e)
            if any(x in msg for x in ("429", "500", "502", "503", "504", "ServiceUnavailable")) and i < attempts:
                sleep = min(backoff_max, backoff_min * (2 ** (i-1)))
                print(f"⏳ transient error {i}/{attempts} — retry in {sleep:.1f}s", file=sys.stderr)
                time.sleep(sleep)
                continue
            raise

# --- Translation primitives ---
def translate_html_in_place(ar_html: str, model: str = DEFAULT_MODEL) -> str:
    """
    Arabic → English. Preserve HTML tags/attributes/order.
    No invented info. Keep numbers/units. Keep brand/model verbatim.
    """
    system = (
        "You are a precise technical translator.\n"
        "Translate Arabic to English.\n"
        "RULES:\n"
        "• Translate ONLY human-visible text. Preserve ALL HTML tags/attributes/order exactly.\n"
        "• Do NOT add, remove, or infer features/specs.\n"
        "• Keep numbers/units/measurements exactly.\n"
        "• Do NOT translate brand names or model codes; leave them verbatim.\n"
        "• Return ONLY the translated HTML string."
    )
    user = (
        "Task: Translate the inner text of this HTML snippet from Arabic to English.\n"
        "Return only the translated HTML (same tags & attributes):\n\n"
        f"{ar_html}"
    )
    key = {"t": "translate_html", "m": model, "sys": system, "usr": user}
    def _do():
        return chat_retry(
            messages=[{"role":"system","content":system},{"role":"user","content":user}],
            model=model, temperature=0.0, max_tokens=2000
        ).strip()
    return cached_call(key, _do)

def translate_text(ar_text: str, model: str = DEFAULT_MODEL, max_tokens: int = 400) -> str:
    system = "Translate Arabic to English precisely. No additions. Keep numbers/units. Do not translate brands/models."
    user = f"{ar_text}"
    key = {"t": "translate_text", "m": model, "sys": system, "usr": user}
    def _do():
        return chat_retry(
            messages=[{"role":"system","content":system},{"role":"user","content":user}],
            model=model, temperature=0.0, max_tokens=max_tokens
        ).strip()
    return cached_call(key, _do)

def html_to_text(html_str: str) -> str:
    txt = re.sub(r"<[^>]+>", " ", html_str)
    return re.sub(r"\s+", " ", txt).strip()

# --- Post-processing (auto-clean) ---
BRAND_MAP = {
    "شاومي": "Xiaomi",
    "سامسونج": "Samsung",
    "ابل": "Apple",
    "أبل": "Apple",
    "هواوي": "Huawei",
    "انكر": "Anker",
}

def _replace_case_insensitive(s: str, pat: str, repl: str) -> str:
    return re.sub(pat, repl, s, flags=re.I)

def normalize_units_symbols(s: str) -> str:
    # 360 degrees → 360°
    s = re.sub(r"\b360\s*degrees?\b", "360°", s, flags=re.I)
    #  -10 degrees Celsius → -10°C
    s = re.sub(r"(\-?\d+)\s*degrees\s*Celsius", r"\1°C", s, flags=re.I)
    # grams → g
    s = re.sub(r"\b(\d+)\s*grams?\b", r"\1 g", s, flags=re.I)
    # millimeters → mm
    s = re.sub(r"\b(\d+)\s*millimeters?\b", r"\1 mm", s, flags=re.I)
    # ensure mm spacing like 78 mm vs 78mm (optional)
    s = re.sub(r"(\d)(mm)\b", r"\1 mm", s, flags=re.I)
    return s

def normalize_brand_names(html: str) -> str:
    for ar, en in BRAND_MAP.items():
        # Fix "Brand: شاومي" patterns
        html = re.sub(rf"Brand:\s*{re.escape(ar)}\b", f"Brand: {en}", html, flags=re.I)
    # Also fix any 'Brand: شاومي' inside tags
    for ar, en in BRAND_MAP.items():
        html = html.replace(f"<strong>Brand:</strong> {ar}", f"<strong>Brand:</strong> {en}")
    return html

def drop_meta_lines(html: str) -> str:
    # Remove paragraphs like "Product name in Arabic/English: ..."
    patterns = [
        r"<p[^>]*>\s*(?:<strong>)?\s*Product name in Arabic\s*:[\s\S]*?</p>",
        r"<p[^>]*>\s*(?:<strong>)?\s*Product name in English\s*:[\s\S]*?</p>",
        r"<p[^>]*>\s*(?:<strong>)?\s*اسم المنتج بالعربي\s*:[\s\S]*?</p>",
        r"<p[^>]*>\s*(?:<strong>)?\s*اسم المنتج بالإنجليزي\s*:[\s\S]*?</p>",
    ]
    for pat in patterns:
        html = re.sub(pat, "", html, flags=re.I)
    # Clean multiple blank lines created
    html = re.sub(r"\n{2,}", "\n", html)
    return html

def normalize_phrasing(html: str) -> str:
    # and → & between model codes
    html = re.sub(r"\b(C400)\s+and\s+(C200)\b", r"\1 & \2", html)
    # Works with Google Home and Alexa → Works with Google Home & Amazon Alexa
    html = re.sub(r"Works with Google Home\s+and\s+Alexa", "Works with Google Home & Amazon Alexa", html, flags=re.I)
    # Assumed… → Not specified
    html = re.sub(r"\((?:Assumed|Not mentioned)[^)]*\)", "Not specified", html, flags=re.I)
    # Input → Power input (table headings/cells)
    html = re.sub(r">(Input)<", r">Power input<", html)
    html = re.sub(r">Wireless connection<", r">Wireless<", html, flags=re.I)
    html = re.sub(r">Item dimensions<", r">Dimensions<", html, flags=re.I)
    return html

def strip_translate_no_attr(html: str) -> str:
    return re.sub(r'\s*translate\s*=\s*"(?:no|false)"', "", html, flags=re.I)

def postprocess_english_html(html: str, *, drop_meta=True, normalize_units=True, normalize_brands=True, fix_phrasing=True, strip_translate_no=False) -> str:
    if normalize_units:  html = normalize_units_symbols(html)
    if normalize_brands: html = normalize_brand_names(html)
    if fix_phrasing:     html = normalize_phrasing(html)
    if drop_meta:        html = drop_meta_lines(html)
    if strip_translate_no: html = strip_translate_no_attr(html)
    # Trim stray spaces inside tags
    html = re.sub(r">\s+</", "></", html)
    return html

# --- Title helpers ---
def make_title_en(title_ar: str, model: str) -> str:
    ar_txt = html_to_text(title_ar)
    en = translate_text(ar_txt, model=model)
    en = re.sub(r"\b(C400)\s+and\s+(C200)\b", r"\1 & \2", en)  # small polish
    return re.sub(r"\s+", " ", en).strip()[:150]

# --- Main processing ---
def process_products(products, *, model, force=False, marketing=False,
                     strip_translate_no=False, brand_normalize="en"):
    """
    Process products for translation with the given options.
    """
    out: List[Dict[str, Any]] = []
    for i, p in enumerate(products, 1):
        title_ar = p.get("title_ar", "") or ""
        desc_ar  = p.get("descriptionHtml_ar", "") or ""

        if p.get("title_en") and p.get("descriptionHtml_en") and not force:
            print(f"• {i}/{len(products)} SKIP (already translated)")
            out.append(p); continue

        print(f"• {i}/{len(products)} Translating…")

        # Title
        if title_ar:
            try:
                p["title_en"] = make_title_en(title_ar, model=model)
            except Exception as e:
                print(f"  ⚠️ Title translation failed: {e}")
                p["title_en"] = html_to_text(title_ar)

        # Description (faithful, then auto-clean)
        if desc_ar:
            try:
                desc_en = translate_html_in_place(desc_ar, model=model)
                # If translation returned empty or just whitespace, try fallback
                if not desc_en or desc_en.strip() == "":
                    print(f"  ⚠️ HTML translation returned empty, trying text fallback")
                    plain = translate_text(html_to_text(desc_ar), model=model) if desc_ar else ""
                    desc_en = f"<p>{plain}</p>" if plain else ""
            except Exception as e:
                print(f"  ⚠️ Description translation failed: {e}")
                plain = translate_text(html_to_text(desc_ar), model=model) if desc_ar else ""
                desc_en = f"<p>{plain}</p>" if plain else ""

            # Auto-clean for shop-ready EN
            desc_en = postprocess_english_html(
                desc_en,
                drop_meta=True,
                normalize_units=True,
                normalize_brands=(brand_normalize == "en"),
                fix_phrasing=True,
                strip_translate_no=strip_translate_no
            )
            p["descriptionHtml_en"] = desc_en

        out.append(p)
    return out

# --- CLI ---
def main():
    ap = argparse.ArgumentParser(description="Arabic → English translator (HTML-preserving) + auto-clean for shop-ready EN.")
    ap.add_argument("--in", dest="inp", required=True, help="Input JSON file (list of products).")
    ap.add_argument("--out", dest="out", help="Output JSON file (default: *_translated.json).")
    ap.add_argument("--model", default=DEFAULT_MODEL, help=f"OpenAI model (default: {DEFAULT_MODEL}).")
    ap.add_argument("--force", action="store_true", help="Re-translate even if English fields already exist.")
    ap.add_argument("--strip-translate-no", action="store_true", help='Remove translate="no" from output HTML.')
    ap.add_argument("--cache", default=".translation_cache.json", help="Disk cache path ('' to disable).")
    # in main() argparse section
    ap.add_argument("--brand-normalize", choices=["en", "none"], default="en",
                help="Normalize brand to Latin only in English output (default: en).")

    args = ap.parse_args()

    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Please set OPENAI_API_KEY.", file=sys.stderr)
        sys.exit(1)

    inp = Path(args.inp)
    if not inp.exists():
        print(f"❌ Input not found: {inp}", file=sys.stderr); sys.exit(1)
    out = Path(args.out) if args.out else Path(inp.with_name(inp.stem + "_translated.json"))

    load_cache(args.cache if args.cache else None)

    products = json.load(inp.open("r", encoding="utf-8"))
    if not isinstance(products, list):
        print("❌ Input must be a JSON list of product objects.", file=sys.stderr); sys.exit(1)

    print(f"🔤 Model: {args.model}")
    print(f"📦 Items: {len(products)}")
    print(f"♻️ Cache: {'ON' if args.cache else 'OFF'}")
    print("—" * 50)

    updated = process_products(
    products,
    model=args.model,
    force=args.force,
    strip_translate_no=args.strip_translate_no,
    brand_normalize=args.brand_normalize
)

    with out.open("w", encoding="utf-8") as f:
        json.dump(updated, f, ensure_ascii=False, indent=2)

    print(f"✅ Saved: {out}")

if __name__ == "__main__":
    main()
