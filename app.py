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
            st.session_state["shopping_items"].append({"name": n, "bought": False, "prices": [], "searched": False})
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
    c1, c2 = st.columns(2)
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
    st.caption("Permanent nøgle: opret `.streamlit/secrets.toml` med `SALLING_API_KEY = \"...\"`")

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

                    # Dedupliker & sortér
                    seen, deduped = set(), []
                    for r in all_p:
                        k = (r["store"].lower()[:20], round(r["price"], 2))
                        if k not in seen:
                            seen.add(k)
                            deduped.append(r)
                    deduped.sort(key=lambda x: x["price"])

                    idx = next(i for i, it in enumerate(st.session_state["shopping_items"]) if it["name"] == item["name"])
                    st.session_state["shopping_items"][idx]["prices"] = deduped
                    st.session_state["shopping_items"][idx]["searched"] = True
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

    for idx, item in enumerate(st.session_state["shopping_items"]):
        bc = "bought" if item["bought"] else ""

        rows_html = ""
        if item["searched"] and item["prices"]:
            for p in item["prices"][:6]:
                src = p.get("source", "tjek")
                is_off = p.get("is_offer", False)
                orig = p.get("original_price")
                dist = p.get("distance_km")
                valid = fmt_valid(p.get("valid_until", ""))

                # Escape dynamisk indhold for at undgå HTML-brud
                e_brand = _html_escape.escape(str(p.get("brand") or p["store"]))
                e_store = _html_escape.escape(str(p["store"]))
                e_prod  = _html_escape.escape(str(p["product_name"]))
                e_name  = _html_escape.escape(str(item["name"]))

                badge_src = ('<span class="badge badge-salling">Salling</span>'
                             if src == "salling"
                             else '<span class="badge badge-tjek">Tilbudsavis</span>')
                badge_off = '<span class="badge badge-offer">Tilbud</span>' if is_off else ""
                orig_html = f'<span class="orig-price">{orig:.2f} kr</span>' if orig else ""
                dist_html = f'<span class="dist-tag">{dist} km</span>' if dist else ""
                valid_html = f'<span class="valid-tag">{valid}</span>' if valid else ""
                ptag = "price-tag offer" if is_off else "price-tag"

                rows_html += f"""
                <div class="price-row">
                  <div class="store-info">
                    <span class="store-name">{e_brand} — {e_store} {dist_html}</span>
                    <span class="product-desc">{e_prod} {valid_html}</span>
                  </div>
                  <div class="price-right">
                    {orig_html}<span class="{ptag}">{p['price']:.2f} kr</span>{badge_off}{badge_src}
                  </div>
                </div>"""
        elif item["searched"]:
            rows_html = '<div class="no-results">Ingen resultater fundet i dit område</div>'
        else:
            rows_html = '<div class="not-searched">Søg priser for at se resultater</div>'

        e_item_name = _html_escape.escape(str(item['name']))
        card_html = f'<div class="item-card {bc}"><div class="item-name {bc}">{e_item_name}</div>{rows_html}</div>'
        st.html(card_html)

        k1, k2, k3 = st.columns([3, 2, 1])
        with k1:
            lbl = "✅ Lagt i kurv" if item["bought"] else "☑️ Læg i kurv"
            if st.button(lbl, key=f"b{idx}", use_container_width=True):
                st.session_state["shopping_items"][idx]["bought"] = not item["bought"]
                st.rerun()
        with k2:
            if item["searched"]:
                if st.button("🔄 Søg igen", key=f"r{idx}", use_container_width=True):
                    st.session_state["shopping_items"][idx]["searched"] = False
                    st.rerun()
        with k3:
            if st.button("✕", key=f"d{idx}", use_container_width=True, help="Fjern"):
                st.session_state["shopping_items"].pop(idx)
                st.rerun()

else:
    st.html("""
    <div style="text-align:center;padding:2.5rem 0">
      <div style="font-size:3rem">🛒</div>
      <div style="margin-top:.5rem;font-size:.95rem;color:#aaa">Tilføj varer ovenfor for at komme i gang</div>
    </div>""")

st.markdown("---")
st.caption("🛒 Lokalt Indkøb · Salling Group API + eTilbudsavis/Tjek · Ingen persondata gemmes")
