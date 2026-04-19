"""
AI-filtrering af søgeresultater via Claude API.

Regler:
- Claude må KUN bruge information der faktisk står i produktnavnet/beskrivelsen
- Mængde/vægt SKAL udtrækkes præcist fra teksten - aldrig gættes
- Beregn kilopris hvis mængde kendes - gør sammenligning nemmere
- Ingen hallucination – hellere vis_raw=true end forkert info
"""

import json
import re
import requests
import streamlit as st

CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"
CLAUDE_MODEL   = "claude-sonnet-4-20250514"


def get_anthropic_key() -> str | None:
    try:
        return st.secrets.get("ANTHROPIC_API_KEY", None)
    except Exception:
        return None


# ── Simpel regex-baseret mængde-udtræk (kører altid, ingen AI nødvendig) ──────
_QTY_PATTERNS = [
    # "500 g", "1,5 kg", "250g", "1.5kg", "2 x 500g", "6 x 330 ml"
    (r'(\d+)\s*[xX×]\s*(\d+(?:[.,]\d+)?)\s*(kg|g|ml|l|cl|stk|pk|pak)\b', "multi"),
    (r'(\d+(?:[.,]\d+)?)\s*(kg|g|ml|l|cl|stk|pk|pak)\b', "single"),
    # "1 liter", "2 liter"
    (r'(\d+(?:[.,]\d+)?)\s*(liter|liters)\b', "liter"),
]

def extract_qty_regex(text: str) -> str | None:
    """Forsøg at udtrække mængde med regex fra produktnavn/beskrivelse."""
    text_lower = text.lower()
    for pat, ptype in _QTY_PATTERNS:
        m = re.search(pat, text_lower, re.IGNORECASE)
        if m:
            if ptype == "multi":
                count, amount, unit = m.group(1), m.group(2).replace(",", "."), m.group(3)
                return f"{count} × {amount} {unit}"
            elif ptype == "single":
                amount, unit = m.group(1).replace(",", "."), m.group(2)
                return f"{amount} {unit}"
            elif ptype == "liter":
                return f"{m.group(1)} l"
    return None


def calc_unit_price(price: float, qty_str: str | None) -> str | None:
    """
    Beregn kilopris eller literpris ud fra pris og mængde-streng.
    Returnerer f.eks. "49,80 kr/kg" eller None.
    """
    if not qty_str:
        return None
    try:
        # Multi: "2 × 500 g"
        m = re.match(r'(\d+)\s*[×x]\s*(\d+(?:\.\d+)?)\s*(kg|g|ml|l)', qty_str, re.IGNORECASE)
        if m:
            count  = float(m.group(1))
            amount = float(m.group(2))
            unit   = m.group(3).lower()
        else:
            m = re.match(r'(\d+(?:\.\d+)?)\s*(kg|g|ml|l)', qty_str, re.IGNORECASE)
            if not m:
                return None
            count  = 1
            amount = float(m.group(1))
            unit   = m.group(2).lower()

        total_g = count * amount
        if unit == "kg":
            total_g *= 1000
        elif unit == "l":
            total_g *= 1000  # ml
        elif unit == "ml":
            pass  # allerede ml
        # else: g

        if total_g <= 0:
            return None

        if unit in ("l", "ml"):
            per_unit = price / (total_g / 1000)
            return f"{per_unit:.2f} kr/l"
        else:
            per_kg = price / (total_g / 1000)
            return f"{per_kg:.2f} kr/kg"
    except Exception:
        return None


# ── Hoved-funktion ─────────────────────────────────────────────────────────────
def filter_and_enrich(query: str, results: list[dict]) -> list[dict]:
    """
    1. Kør regex-udtræk af mængde på alle resultater.
    2. Send til Claude for relevansfiltrering og mængde-validering.
    3. Beregn kilopris.
    Returnerer berigede, filtrerede resultater.
    """
    if not results:
        return results

    # Trin 1: Regex-mængde på alle (koster ingen API-kald)
    for r in results:
        combined = f"{r.get('product_name','')} {r.get('description','')}"
        r["_regex_qty"] = extract_qty_regex(combined)

    api_key = get_anthropic_key()
    if not api_key:
        # Ingen AI – vis med regex-mængde og kilopris
        for r in results:
            r["display_name"] = r.get("product_name", "")
            r["display_qty"]  = r.get("_regex_qty") or r.get("unit", "")
            r["display_brand"] = None
            r["unit_price"]   = calc_unit_price(r["price"], r.get("_regex_qty"))
            r["ai_enriched"]  = False
        return results

    # Trin 2: AI-filtrering og berigelse
    items_for_claude = []
    for i, r in enumerate(results):
        items_for_claude.append({
            "idx":        i,
            "navn":       r.get("product_name", ""),
            "beskrivelse": r.get("description", ""),
            "butik":      r.get("store", ""),
            "pris":       r.get("price", 0),
            "regex_maengde": r.get("_regex_qty"),  # Hvad regex fandt
        })

    prompt = f"""Du filtrerer supermarkedstilbud for en dansk indkøbsapp.

Søgning: "{query}"

{len(items_for_claude)} resultater:
{json.dumps(items_for_claude, ensure_ascii=False, indent=2)}

For hvert resultat:
1. relevant: Er dette faktisk "{query}"? (true/false) — vær streng: "kakaomælk" er IKKE relevant for "mælk", "kaffekapsler" er IKKE relevant for "hele kaffebønner"
2. produkt_navn: Præcist navn fra "navn"-feltet. Kun ord der faktisk står der.
3. maengde: Mængde/vægt/volumen. Regler:
   - Brug regex_maengde hvis den ser korrekt ud
   - Søg ellers i "navn" og "beskrivelse" efter tal + enhed (g, kg, ml, l, stk, pak)
   - Eksempler: "500 g", "1 kg", "2 × 330 ml", "6-pak"
   - Sæt null hvis du ikke kan finde det præcist i teksten — gæt ALDRIG
4. maerke: Brand/mærke hvis det fremgår tydeligt. Ellers null.
5. vis_raw: true kun hvis produktnavnet er meget uklart

VIGTIGT: Opfind eller gæt ALDRIG mængde. Null er bedre end forkert.

Svar KUN med JSON-array, ingen markdown:
[{{"idx":0,"relevant":true,"produkt_navn":"...","maengde":"500 g","maerke":"Arla","vis_raw":false}}]"""

    try:
        resp = requests.post(
            CLAUDE_API_URL,
            headers={
                "x-api-key":          api_key,
                "anthropic-version":  "2023-06-01",
                "content-type":       "application/json",
            },
            json={
                "model":      CLAUDE_MODEL,
                "max_tokens": 1500,
                "messages":   [{"role": "user", "content": prompt}],
            },
            timeout=20,
        )
        resp.raise_for_status()
        raw_text = resp.json()["content"][0]["text"].strip()

        # Strip markdown-backticks
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]
        raw_text = raw_text.strip()

        claude_results = json.loads(raw_text)

        enriched = []
        for cr in claude_results:
            if not cr.get("relevant", False):
                continue
            idx = cr["idx"]
            if idx >= len(results):
                continue

            r = results[idx].copy()

            if cr.get("vis_raw", False):
                r["display_name"]  = r.get("product_name", "")
                r["display_qty"]   = r.get("_regex_qty") or r.get("unit", "")
                r["display_brand"] = None
                r["ai_enriched"]   = False
            else:
                r["display_name"]  = cr.get("produkt_navn") or r.get("product_name", "")
                r["display_qty"]   = cr.get("maengde") or r.get("_regex_qty") or r.get("unit", "")
                r["display_brand"] = cr.get("maerke")
                r["ai_enriched"]   = True

            # Beregn kilopris
            r["unit_price"] = calc_unit_price(r["price"], r.get("display_qty"))
            enriched.append(r)

        # Debug: vis hvad Claude faktisk returnerede
        with st.expander("🔍 AI-filter debug", expanded=False):
            st.caption("Råt svar fra Claude:")
            st.code(raw_text, language="json")
            st.caption("Berigede resultater:")
            for r in enriched:
                st.write({
                    "navn": r.get("display_name"),
                    "mængde": r.get("display_qty"),
                    "regex_qty": r.get("_regex_qty"),
                    "unit_price": r.get("unit_price"),
                    "relevant": True,
                })

        return enriched

    except requests.exceptions.HTTPError as e:
        st.warning(f"⚠️ AI-filter fejl ({e.response.status_code})")
        # Fallback med regex-mængde
        for r in results:
            r["display_name"]  = r.get("product_name", "")
            r["display_qty"]   = r.get("_regex_qty") or r.get("unit", "")
            r["display_brand"] = None
            r["unit_price"]    = calc_unit_price(r["price"], r.get("_regex_qty"))
            r["ai_enriched"]   = False
        return results
    except json.JSONDecodeError:
        st.warning("⚠️ AI-filter: uventet svar-format")
        return results
    except Exception as e:
        st.warning(f"⚠️ AI-filter: {e}")
        return results
