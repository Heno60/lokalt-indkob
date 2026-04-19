"""
🛒 Lokalt Indkøb – Find de bedste priser i dit nærområde
Sammenligner priser fra Salling Group (Netto/Føtex/Bilka) + eTilbudsavis/Tjek (Rema/Lidl/Aldi m.fl.)
"""

import streamlit as st
import sys, os
import warnings
import html as _html_escape
warnings.filterwarnings("ignore", message=".*st.components.v1.html.*")
import streamlit.components.v1 as components

sys.path.insert(0, os.path.dirname(__file__))

from api.salling import search_all_nearby_stores
from api.tjek import search_offers, get_chain_coverage
from api.ai_filter import filter_and_enrich, get_anthropic_key

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="🛒 Lokalt Indkøb",
    page_icon="🛒",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.html("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&display=swap');

html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }

.app-header {
    text-align: center; padding: 1.4rem 0 0.4rem;
}
.app-header h1 {
    font-size: 2rem; font-weight: 700;
    color: #1B5E20; margin: 0; letter-spacing: -0.5px;
}
.app-header p { color: #666; font-size: 0.92rem; margin: 0.3rem 0 0; }

.coverage-bar {
    background: #F1F8E9; border-radius: 10px;
    padding: 0.55rem 1rem; font-size: 0.82rem;
    color: #33691E; text-align: center; margin: 0.3rem 0 0.8rem;
}

.item-card {
    background: white; border-radius: 14px;
    padding: 0.9rem 1.1rem; margin-bottom: 0.9rem;
    box-shadow: 0 2px 12px rgba(0,0,0,0.07);
    border-left: 4px solid #2E7D32;
}
.item-card.bought { border-left-color: #bbb; opacity: 0.55; }
.item-name { font-size: 1.05rem; font-weight: 600; color: #1A1A1A; }
.item-name.bought { text-decoration: line-through; color: #999; }

.price-row {
    display: flex; align-items: center;
    justify-content: space-between;
    padding: 0.4rem 0.55rem; border-radius: 8px;
    margin: 0.25rem 0; background: #F9FBF9;
    font-size: 0.86rem; gap: 8px;
}
.price-row:first-child { background: #E8F5E9; }
.store-info { display: flex; flex-direction: column; gap: 1px; flex: 1; min-width: 0; }
.store-name { font-weight: 600; color: #1A1A1A; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.product-desc { color: #777; font-size: 0.76rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.price-right { display: flex; align-items: center; gap: 5px; flex-shrink: 0; }
.price-tag { font-size: 0.98rem; font-weight: 700; color: #2E7D32; }
.price-tag.offer { color: #E65100; }
.orig-price { font-size: 0.73rem; color: #aaa; text-decoration: line-through; }
.badge {
    font-size: 0.65rem; font-weight: 700; padding: 2px 6px;
    border-radius: 20px; text-transform: uppercase; letter-spacing: 0.4px;
}
.badge-offer { background: #FFF3E0; color: #E65100; }
.badge-salling { background: #E8EAF6; color: #3949AB; }
.badge-tjek { background: #E0F2F1; color: #00695C; }
.dist-tag { font-size: 0.73rem; color: #aaa; }
.valid-tag { font-size: 0.7rem; color: #999; }
.unit-price { font-size: 0.72rem; color: #888; font-style: italic; }
.price-row-selected { background: #E8F5E9; border-left: 3px solid #2E7D32; }
.product-desc { color: #777; font-size: 0.76rem; white-space: normal !important; word-wrap: break-word; overflow-wrap: break-word; max-width: 100%; }
.kurv-box {
    background: #F9FBF9; border: 1.5px solid #A5D6A7; border-radius: 12px;
    padding: 0.8rem 1rem; margin-bottom: 1rem;
}
.kurv-header { font-weight: 700; font-size: 0.95rem; color: #1B5E20; margin-bottom: 0.5rem; }
.kurv-row {
    display: grid; grid-template-columns: 1fr auto auto;
    align-items: center; gap: 8px;
    padding: 0.3rem 0; border-bottom: 1px solid #E8F5E9; font-size: 0.88rem;
}
.kurv-row:last-of-type { border-bottom: none; }
.kurv-total {
    text-align: right; font-weight: 700; font-size: 1rem;
    color: #1B5E20; margin-top: 0.5rem; padding-top: 0.4rem;
    border-top: 2px solid #A5D6A7;
}

.gps-ok {
    background: linear-gradient(135deg,#E8F5E9,#DCEDC8);
    border-radius: 11px; padding: 0.65rem 1rem;
    margin: 0.4rem 0 0.9rem; font-size: 0.88rem;
    color: #1B5E20; font-weight: 500;
}
.no-results { color: #aaa; font-size: 0.83rem; padding: 0.35rem 0; font-style: italic; }
.not-searched { color: #bbb; font-size: 0.8rem; padding: 0.35rem 0; }
.list-stats { text-align: center; font-size: 0.82rem; color: #999; margin: 0.2rem 0 0.8rem; }

#MainMenu, footer { visibility: hidden; }
div.stButton > button { border-radius: 9px; font-family: 'DM Sans', sans-serif; font-weight: 600; }
.stTextInput input, .stTextArea textarea { border-radius: 9px !important; font-size: 0.95rem !important; }
</style>
""")


# ── Session state ─────────────────────────────────────────────────────────────
for k, v in {"shopping_items": [], "location": None}.items():
    if k not in st.session_state:
        st.session_state[k] = v


def get_salling_key():
    try:
        return st.secrets.get("SALLING_API_KEY", None)
    except Exception:
        return None


# ── GPS HTML ──────────────────────────────────────────────────────────────────
GPS_HTML = """
<div style="font-family:sans-serif;margin-top:4px">
  <button onclick="fetchGPS()" id="gpsbtn" style="
    background:#2E7D32;color:white;border:none;border-radius:9px;
    padding:8px 16px;font-size:13px;font-weight:600;cursor:pointer;">
    📍 Hent automatisk via browser
  </button>
  <span id="gpsmsg" style="font-size:12px;color:#666;margin-left:10px;"></span>
</div>
<script>
function fetchGPS(){
  var btn=document.getElementById('gpsbtn'),msg=document.getElementById('gpsmsg');
  btn.disabled=true;btn.textContent='⏳ Henter...';
  msg.textContent='Tillad lokation i browseren...';
  if(!navigator.geolocation){msg.textContent='❌ GPS ikke understøttet';btn.disabled=false;return;}
  navigator.geolocation.getCurrentPosition(function(p){
    msg.innerHTML='✅ <b>'+p.coords.latitude.toFixed(5)+'</b>, <b>'+p.coords.longitude.toFixed(5)+'</b> — kopiér til felterne ovenfor';
    btn.textContent='📍 Hentet';
  },function(e){msg.textContent='❌ '+e.message;btn.disabled=false;btn.textContent='📍 Prøv igen';},
  {enableHighAccuracy:true,timeout:10000});
}
</script>
"""

# ── Tale-input HTML ───────────────────────────────────────────────────────────
VOICE_HTML = """
<div style="font-family:sans-serif">
  <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
    <button id="vbtn" onclick="toggleVoice()" style="
      background:#E8F5E9;color:#2E7D32;border:2px solid #2E7D32;
      border-radius:9px;padding:8px 16px;font-size:13px;font-weight:600;cursor:pointer;">
      🎤 Start diktering
    </button>
    <span id="vstatus" style="font-size:12px;color:#888;">Virker bedst i Chrome</span>
  </div>
  <div id="vresult" style="margin-top:8px;padding:8px 10px;background:#f5f5f5;
    border-radius:8px;font-size:13px;color:#333;min-height:32px;display:none;
    white-space:pre-wrap;"></div>
</div>
<script>
var recog=null,rec=false,finalText='';
function toggleVoice(){rec?stopVoice():startVoice();}
function startVoice(){
  var SR=window.SpeechRecognition||window.webkitSpeechRecognition;
  if(!SR){document.getElementById('vstatus').textContent='❌ Brug Chrome';return;}
  recog=new SR();recog.lang='da-DK';recog.continuous=true;recog.interimResults=true;
  finalText='';
  recog.onstart=function(){rec=true;
    var b=document.getElementById('vbtn');
    b.style.background='#FFCDD2';b.style.borderColor='#C62828';b.style.color='#C62828';b.textContent='⏹ Stop';
    document.getElementById('vstatus').textContent='🔴 Optager — sig dine varer adskilt af pauser...';
    document.getElementById('vresult').style.display='block';};
  recog.onresult=function(e){var interim='';
    for(var i=e.resultIndex;i<e.results.length;i++){
      if(e.results[i].isFinal)finalText+=e.results[i][0].transcript+'\n';
      else interim=e.results[i][0].transcript;}
    document.getElementById('vresult').textContent=finalText+interim;};
  recog.onerror=function(e){document.getElementById('vstatus').textContent='❌ '+e.error;stopVoice();};
  recog.onend=stopVoice;recog.start();}
function stopVoice(){
  if(recog)recog.stop();rec=false;
  var b=document.getElementById('vbtn');
  b.style.background='#E8F5E9';b.style.borderColor='#2E7D32';b.style.color='#2E7D32';b.textContent='🎤 Start diktering';
  document.getElementById('vstatus').textContent=finalText.trim()?'✅ Færdig – kopiér teksten til listen nedenfor':'Klar';}
</script>
"""


# ── Hjælpefunktioner ──────────────────────────────────────────────────────────
def parse_list(text):
    for sep in ["\n", ",", ";"]:
        if sep in text:
            return [l.strip() for l in text.split(sep) if len(l.strip()) > 1]
    return [text.strip()] if len(text.strip()) > 1 else []


def add_items(names):
    existing = {i["name"].lower() for i in st.session_state["shopping_items"]}
    count = 0
    for n in names:
        if n.lower() not in existing:
            st.session_state["shopping_items"].append({"name": n, "bought": False, "prices": [], "searched": False, "selected_prices": [], "selected_price": None})
            count += 1
    return count


def fmt_valid(date_str):
    if not date_str:
        return ""
    try:
        from datetime import datetime
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return f"til {dt.strftime('%-d/%-m')}"
    except Exception:
        return ""


# ═══════════════════════════════════════════════════════════════════════════════
# UI
# ═══════════════════════════════════════════════════════════════════════════════

st.html("""
<div class="app-header">
  <h1>🛒 Lokalt Indkøb</h1>
  <p>Find og sammenlign dagligvarepriser i dit nærområde</p>
</div>
""")

chains = get_chain_coverage()
st.html(f'<div class="coverage-bar">📡 Dækker: {" &nbsp;·&nbsp; ".join(chains)}</div>')

salling_key = get_salling_key()

# ── API status ────────────────────────────────────────────────────────────────
with st.expander("⚙️ API-status", expanded=not salling_key):
    c1, c2, c3 = st.columns(3)
    with c1:
        if salling_key:
            st.success("✅ **Salling API**\nNetto · Føtex · Bilka\n*(realtidspriser)*")
        else:
            st.warning("⚠️ **Salling API mangler**\n[Hent gratis nøgle →](https://developer.sallinggroup.com)")
            manual = st.text_input("Nøgle (midlertidig):", type="password", key="ms")
            if manual:
                salling_key = manual
    with c2:
        st.success("✅ **eTilbudsavis/Tjek**\nRema · Lidl · Aldi m.fl.\n*(ugentlige tilbud, ingen nøgle)*")
    with c3:
        anthropic_key = get_anthropic_key()
        if anthropic_key:
            st.success("✅ **AI-filter aktiv**\nFiltrerer irrelevante\nresultater fra søgninger")
        else:
            st.info("🤖 **AI-filter inaktivt**\nTilføj ANTHROPIC_API_KEY\ni secrets for bedre søgning")
    st.caption("Permanent nøgle: .streamlit/secrets.toml med SALLING_API_KEY og ANTHROPIC_API_KEY")

st.divider()

# ── GPS ───────────────────────────────────────────────────────────────────────
st.markdown("### 📍 Position")

if st.session_state.location:
    lat = st.session_state.location["lat"]
    lng = st.session_state.location["lng"]
    st.html(f'<div class="gps-ok">📍 {lat:.4f}°N · {lng:.4f}°E &nbsp;&nbsp; Søger inden for valgt radius</div>')
    if st.button("🔄 Skift position"):
        st.session_state.location = None
        st.rerun()
else:
    c1, c2 = st.columns(2)
    with c1:
        lat_in = st.number_input("Breddegrad", value=55.9396, format="%.4f", step=0.0001)
    with c2:
        lng_in = st.number_input("Længdegrad", value=12.3079, format="%.4f", step=0.0001)
    components.html(GPS_HTML, height=44)
    b1, b2 = st.columns(2)
    with b1:
        if st.button("✅ Brug denne position", type="primary", use_container_width=True):
            st.session_state.location = {"lat": lat_in, "lng": lng_in}
            st.rerun()
    with b2:
        if st.button("🏠 Ullerød (standard)", use_container_width=True):
            st.session_state.location = {"lat": 55.9396, "lng": 12.3079}
            st.rerun()

st.divider()

# ── Tilføj varer ──────────────────────────────────────────────────────────────
st.markdown("### 📝 Indkøbsliste")

with st.expander("🎤 Dikter med stemme"):
    st.caption("Sig varerne med en kort pause imellem. Kopiér teksten til feltet nedenfor.")
    components.html(VOICE_HTML, height=110)

raw = st.text_area(
    "Skriv varer (én per linje eller kommasepareret):",
    placeholder="mælk\næg\nsmør\nkaffe\nhavregryn",
    height=120,
    key="raw",
)

ca, cb = st.columns([3, 1])
with ca:
    if st.button("➕ Tilføj til liste", type="primary", use_container_width=True):
        if raw.strip():
            n = add_items(parse_list(raw.strip()))
            st.success(f"✅ {n} vare(r) tilføjet") if n else st.info("Varerne er allerede på listen")
            st.rerun()
        else:
            st.warning("Skriv mindst én vare")
with cb:
    if st.button("🗑️ Ny liste", use_container_width=True):
        st.session_state["shopping_items"] = []
        st.rerun()

if st.session_state["shopping_items"]:
    bought = sum(1 for i in st.session_state["shopping_items"] if i["bought"])
    st.html(f'<div class="list-stats">✓ {bought} af {len(st.session_state["shopping_items"])} varer lagt i kurven</div>')

st.divider()

# ── Søg & vis ─────────────────────────────────────────────────────────────────
if st.session_state["shopping_items"]:
    st.markdown("### 🔍 Priser")

    unsearched = [it for it in st.session_state["shopping_items"] if not it["searched"]]

    if unsearched:
        if not st.session_state.location:
            st.warning("⚠️ Sæt din position ovenfor inden du søger.")
        else:
            radius_km = st.slider("Søgeradius (km)", 1, 15, 5)
            if st.button(f"🔍 Søg priser på {len(unsearched)} vare(r)", type="primary", use_container_width=True):
                loc = st.session_state.location
                lat, lng = loc["lat"], loc["lng"]

                prog = st.progress(0, text="Starter...")
                for step, item in enumerate(unsearched):
                    q = item["name"]
                    prog.progress(step / len(unsearched), text=f"Søger: {q}...")
                    all_p = []

                    if salling_key:
                        salling_res = search_all_nearby_stores(salling_key, q, lat, lng, radius_km)
                        for r in salling_res:
                            r["source"] = "salling"
                            all_p.append(r)
                        st.caption(f"🔵 Salling: {len(salling_res)} resultater for '{q}'")
                    else:
                        st.caption("⚠️ Salling API-nøgle mangler")

                    tjek_res = search_offers(q, lat, lng, radius_m=radius_km * 1000)
                    all_p.extend(tjek_res)
                    st.caption(f"🟢 Tjek/eTilbudsavis: {len(tjek_res)} resultater for '{q}'")

                    # Dedupliker
                    seen, deduped = set(), []
                    for r in all_p:
                        k = (r["store"].lower()[:20], round(r["price"], 2))
                        if k not in seen:
                            seen.add(k)
                            deduped.append(r)
                    deduped.sort(key=lambda x: x["price"])

                    # AI-filtrering (hvis Anthropic-nøgle findes)
                    prog.progress((step + 0.8) / len(unsearched), text=f"🤖 AI-filtrerer: {q}...")
                    filtered = filter_and_enrich(q, deduped)
                    # Fallback: hvis AI fjernede ALT, brug ufiltrerede resultater
                    if not filtered and deduped:
                        filtered = deduped

                    item_idx = next(i for i, it in enumerate(st.session_state["shopping_items"]) if it["name"] == item["name"])
                    st.session_state["shopping_items"][item_idx]["prices"] = filtered
                    st.session_state["shopping_items"][item_idx]["searched"] = True
                    prog.progress((step + 1) / len(unsearched), text=f"✅ {q}")

                prog.empty()
                st.rerun()
    else:
        if st.button("🔄 Opdater alle priser", use_container_width=True):
            for it in st.session_state["shopping_items"]:
                it["searched"] = False
            st.rerun()

    st.divider()
    st.markdown("### 🧺 Din liste")

    # ── Kurv-oversigt ──────────────────────────────────────────────────────────
    # Saml alle valgte og købte varer
    kurv_rows_list = []
    total = 0.0
    for it in st.session_state["shopping_items"]:
        bought_flag = it.get("bought", False)
        sps = it.get("selected_prices", []) or ([it["selected_price"]] if it.get("selected_price") else [])
        if not bought_flag and not sps:
            continue
        status = "✅" if bought_flag else "🛒"
        e_name = _html_escape.escape(it["name"])
        if sps:
            for sp in sps:
                e_store = _html_escape.escape(sp.get("store", ""))
                price = sp.get("price", 0)
                total += price
                kurv_rows_list.append(
                    f'<div class="kurv-row">' +
                    f'<span>{status} <b>{e_name}</b></span>' +
                    f'<span style="color:#555;font-size:.82rem">{e_store}</span>' +
                    f'<span class="price-tag" style="font-size:.9rem">{price:.2f} kr</span>' +
                    f'</div>'
                )
        else:
            kurv_rows_list.append(
                f'<div class="kurv-row">' +
                f'<span>{status} <b>{e_name}</b></span>' +
                f'<span style="color:#aaa;font-size:.82rem">Ingen butik valgt</span>' +
                f'<span></span></div>'
            )

    if kurv_rows_list:
        kurv_rows_html = "".join(kurv_rows_list)
        total_html = f'<div class="kurv-total">I alt: {total:.2f} kr</div>' if total > 0 else ""
        st.html(
            '<div class="kurv-box">' +
            f'<div class="kurv-header">🛒 Kurv ({len(kurv_rows_list)} valgte)</div>' +
            kurv_rows_html + total_html +
            '</div>'
        )
        st.markdown("")

    for idx, item in enumerate(st.session_state["shopping_items"]):
        bought = item["bought"]
        # selected_prices er nu en LISTE af valgte varer (multi-select)
        if "selected_prices" not in item:
            item["selected_prices"] = []
        selected_prices = item["selected_prices"]
        bc = "bought" if bought else ""
        e_item_name = _html_escape.escape(str(item["name"]))

        # ── Varekort header ──
        st.html(f'<div class="item-card {bc}"><div class="item-name {bc}">{e_item_name}</div></div>')

        if item["searched"] and item["prices"]:
            for pidx, p in enumerate(item["prices"][:6]):
                src        = p.get("source", "tjek")
                is_off     = p.get("is_offer", False)
                orig       = p.get("original_price")
                dist       = p.get("distance_km")
                valid      = fmt_valid(p.get("valid_until", ""))
                unit_price = p.get("unit_price")

                raw_brand = p.get("display_brand") or p.get("brand") or p["store"]
                raw_prod  = p.get("display_name") or p.get("product_name", "")
                raw_qty   = p.get("display_qty") or p.get("unit", "")
                if raw_qty in ("g", "kg", "ml", "l", "stk", "pk", ""):
                    raw_qty = ""

                desc_parts   = [raw_prod] + ([raw_qty] if raw_qty else [])
                display_desc = " · ".join(x for x in desc_parts if x)

                e_brand      = _html_escape.escape(str(raw_brand))
                e_store      = _html_escape.escape(str(p["store"]))
                e_prod       = _html_escape.escape(display_desc)
                e_unit_price = _html_escape.escape(str(unit_price)) if unit_price else ""

                badge_src  = "Salling" if src == "salling" else "Tilbudsavis"
                badge_cls  = "badge-salling" if src == "salling" else "badge-tjek"
                badge_off  = '<span class="badge badge-offer">Tilbud</span>' if is_off else ""
                orig_html  = f'<span class="orig-price">{orig:.2f} kr</span>' if orig else ""
                dist_html  = f'<span class="dist-tag">{dist} km</span>' if dist else ""
                valid_html = f'<span class="valid-tag">{valid}</span>' if valid else ""
                ptag       = "price-tag offer" if is_off else "price-tag"
                unit_html  = f'<span class="unit-price">{e_unit_price}</span>' if e_unit_price else ""

                # Er denne vare i de valgte?
                p_key = f'{p.get("store","")}_{p.get("price",0)}_{p.get("product_name","")}' 
                is_selected = any(
                    f'{s.get("store","")}_{s.get("price",0)}_{s.get("product_name","")}' == p_key
                    for s in selected_prices
                )
                row_cls = " price-row-selected" if is_selected else ""

                st.html(
                    f'<div class="price-row{row_cls}">' +
                    f'  <div class="store-info">' +
                    f'    <span class="store-name">{e_brand} — {e_store} {dist_html}</span>' +
                    f'    <span class="product-desc">{e_prod} {valid_html}</span>' +
                    f'  </div>' +
                    f'  <div class="price-right">' +
                    f'    <div style="display:flex;flex-direction:column;align-items:flex-end;gap:1px">' +
                    f'      <div>{orig_html}<span class="{ptag}">{p["price"]:.2f} kr</span>' +
                    f'        {badge_off}<span class="badge {badge_cls}">{badge_src}</span></div>' +
                    f'      {unit_html}' +
                    f'    </div>' +
                    f'  </div>' +
                    f'</div>'
                )

                cb_label = f"{'✅' if is_selected else '☐'} {p['store']} – {p['price']:.2f} kr"
                checked = st.checkbox(cb_label, value=is_selected, key=f"sel_{idx}_{pidx}")
                if checked and not is_selected:
                    st.session_state["shopping_items"][idx]["selected_prices"].append(p)
                    st.rerun()
                elif not checked and is_selected:
                    st.session_state["shopping_items"][idx]["selected_prices"] = [
                        s for s in selected_prices
                        if f'{s.get("store","")}_{s.get("price",0)}_{s.get("product_name","")}' != p_key
                    ]
                    st.rerun()

        elif item["searched"]:
            st.html('<div class="no-results" style="padding:0.4rem 0.6rem">Ingen resultater fundet</div>')
        else:
            st.html('<div class="not-searched" style="padding:0.4rem 0.6rem">Søg priser for at se resultater</div>')

        # ── Handlingsknapper ──
        k1, k2, k3 = st.columns([3, 2, 1])
        with k1:
            if bought:
                lbl = "✅ Lagt i kurv"
            elif selected_prices:
                lbl = f"🛒 Læg i kurv ({len(selected_prices)} valgt)"
            else:
                lbl = "☑️ Marker som købt"
            if st.button(lbl, key=f"b{idx}", use_container_width=True):
                st.session_state["shopping_items"][idx]["bought"] = not bought
                st.rerun()
        with k2:
            if item["searched"]:
                if st.button("🔄 Søg igen", key=f"r{idx}", use_container_width=True):
                    st.session_state["shopping_items"][idx]["searched"] = False
                    st.session_state["shopping_items"][idx]["selected_prices"] = []
                    st.rerun()
        with k3:
            if st.button("✕", key=f"d{idx}", use_container_width=True, help="Fjern"):
                st.session_state["shopping_items"].pop(idx)
                st.rerun()

        st.markdown("---")


else:
    st.html("""
    <div style="text-align:center;padding:2.5rem 0">
      <div style="font-size:3rem">🛒</div>
      <div style="margin-top:.5rem;font-size:.95rem;color:#aaa">Tilføj varer ovenfor for at komme i gang</div>
    </div>""")

st.markdown("---")
st.caption("🛒 Lokalt Indkøb · Salling Group API + eTilbudsavis/Tjek · Ingen persondata gemmes")
