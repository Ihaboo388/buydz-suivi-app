import streamlit as st
from suivi import build_suivi, save_call_result, CALL_RESULTS

SHEET, TAB = "Branded Store Orders", "Orders"

st.set_page_config(page_title="BuyDZ Suivi", page_icon="📞", layout="centered")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;900&display=swap');
* { font-family: 'Cairo', sans-serif !important; }
header[data-testid="stHeader"], footer, #MainMenu, [data-testid="stDecoration"],
[data-testid="stToolbar"], [data-testid="stStatusWidget"] { display: none !important; }
html, body, [data-testid="stApp"] { background-color: #F0F7F1 !important; }
[data-testid="stMainBlockContainer"], [data-testid="block-container"] {
    max-width: 560px !important; padding: 0 0 40px !important; margin: 0 auto !important; }
.header-bar { background:#00A651; padding:18px; text-align:center; color:#fff;
              font-size:1.25rem; font-weight:900; }
.summary { background:#fff; border:1px solid #B2DFBF; border-radius:14px; padding:14px;
           margin:14px 16px 6px; text-align:center; direction:rtl; }
.summary b { font-size:1.6rem; }
.card { border-radius:12px; padding:12px 14px; margin:14px 16px 6px; direction:rtl; text-align:right; }
.card .lvl { font-weight:900; font-size:1.05rem; }
.card .who { font-weight:800; color:#1A3C2A; }
.card .sit { color:#B71C1C; font-weight:700; }
.card .last { color:#455A64; font-size:0.9rem; }
div.stButton > button { background:#00A651 !important; color:#fff !important; font-weight:800 !important;
                        border:none !important; border-radius:8px !important; }
div.stButton > button p { color:#fff !important; }
[data-testid="stHorizontalBlock"] { padding: 0 16px !important; }
</style>
<div class="header-bar">📞&nbsp;&nbsp;متابعة الطلبيات — BuyDZ</div>
""", unsafe_allow_html=True)

# ── Access control: the app shows customer data, so it needs a password ──
def _password_ok():
    expected = ""
    try:
        if "APP_PASSWORD" in st.secrets:
            expected = str(st.secrets["APP_PASSWORD"]).strip()
        elif "APP_PASSWORD" in st.secrets.get("gcp_service_account", {}):
            # added at the end of the file, i.e. inside the [gcp_service_account] section
            expected = str(st.secrets["gcp_service_account"]["APP_PASSWORD"]).strip()
    except Exception:
        expected = ""
    if not expected:
        st.error("🔒 التطبيق غير مفعّل: أضف APP_PASSWORD في Settings → Secrets.")
        return False
    if st.session_state.get("auth_ok"):
        return True
    _, m, _ = st.columns([1, 3, 1])
    with m:
        pwd = st.text_input("🔒 كلمة السر", type="password")
        if st.button("دخول", use_container_width=True):
            import hmac
            if hmac.compare_digest(pwd.strip(), expected):
                st.session_state["auth_ok"] = True
                st.rerun()
            else:
                st.error("❌ كلمة السر خاطئة")
    return False


if not _password_ok():
    st.stop()

LEVELS = {
    "day3":    ("#D32F2F", "#FFEBEE", "🔴 اليوم 3 — آخر يوم!"),
    "late":    ("#212121", "#ECEFF1", "⚫ تجاوز 3 أيام — سيرجع"),
    "day2":    ("#F57C00", "#FFF3E0", "🟠 اليوم 2"),
    "day1":    ("#2E7D32", "#E8F5E9", "🟢 اليوم 1"),
    "stuck":   ("#6A1B9A", "#F3E5F5", "⚠️ لم تُشحن بعد (أكثر من 3 أيام)"),
    "transit": ("#546E7A", "#F5F7F8", "🚚 في الطريق"),
    "missing": ("#9E9E9E", "#FAFAFA", "❓ غير موجودة في ZR"),
}


def load():
    with st.spinner("⏳ جاري تحميل الطلبيات من ZR Express..."):
        try:
            st.session_state["cards"] = build_suivi(SHEET, TAB)
            st.session_state["error"] = None
        except Exception as e:
            st.session_state["cards"] = []
            st.session_state["error"] = str(e)[:200]


_, mid, _ = st.columns([1, 2, 1])
with mid:
    refresh = st.button("🔄 تحديث القائمة", use_container_width=True)
if refresh or "cards" not in st.session_state:
    load()

if st.session_state.get("error"):
    st.error("❌ " + st.session_state["error"])

cards = st.session_state.get("cards") or []
counts = {k: sum(c["level"] == k for c in cards) for k in LEVELS}
n_cancel = sum(bool(c.get("cancelled")) for c in cards)
st.markdown(f"""
<div class="summary">
  <div style="font-weight:800;color:#1A3C2A">الطلبيات التي تحتاج متابعة</div>
  <div>❌ <b>{n_cancel}</b> &nbsp; 🔴 <b>{counts['day3']}</b> &nbsp; 🟠 <b>{counts['day2']}</b> &nbsp;
       🟢 <b>{counts['day1']}</b> &nbsp; ⚫ <b>{counts['late']}</b> &nbsp; ⚠️ <b>{counts['stuck']}</b></div>
  <div style="color:#4A7A5A;font-size:0.85rem">ابدئي بالملغاة ❌ والأحمر 🔴 ثم البرتقالي 🟠 — شركة التوصيل ترجع الطلبية بعد 3 أيام</div>
</div>""", unsafe_allow_html=True)

show_transit = st.toggle(f"إظهار الطلبيات التي لم تصل بعد للتوصيل 🚚 ({counts['transit']})", value=False)

if not any(c["level"] != "transit" for c in cards) and not show_transit:
    st.success("✅ لا توجد طلبيات تحتاج متابعة الآن.")


def ring(day):
    """Circle that fills over the 3 delivery days: green 1/3, orange 2/3, red full."""
    color = {1: "#2E7D32", 2: "#F57C00"}.get(day, "#D32F2F" if day >= 3 else "#B0BEC5")
    frac = min(max(day, 0), 3) / 3
    r, circ = 26, 2 * 3.1416 * 26
    txt = str(day) if day else "–"
    return " ".join(line.strip() for line in f"""
    <svg width="66" height="66" viewBox="0 0 66 66" style="flex:none">
      <circle cx="33" cy="33" r="{r}" fill="#fff" stroke="#E0E0E0" stroke-width="7"/>
      <circle cx="33" cy="33" r="{r}" fill="none" stroke="{color}" stroke-width="7"
              stroke-dasharray="{circ * frac:.1f} {circ:.1f}" stroke-linecap="round"
              transform="rotate(-90 33 33)"/>
      <text x="33" y="35" text-anchor="middle" dominant-baseline="middle"
            font-size="20" font-weight="900" fill="{color}">{txt}</text>
    </svg>""".splitlines())


for c in cards:
    if c["level"] == "transit" and not show_transit:
        continue
    border, bg, label = LEVELS[c["level"]]
    if c.get("cancelled"):
        border, bg = "#B71C1C", "#FFEBEE"
    mode = f"🏢 StopDesk — {c['hub'] or c['commune']}" if c["stopdesk"] else f"🏠 للمنزل — {c['commune']}"
    cancel = (f"<div style='background:#B71C1C;color:#fff;border-radius:8px;padding:6px 10px;"
              f"margin:6px 0;font-weight:800'>❌ ملغاة — السبب: {c['cancel_reason'] or 'غير مذكور'}"
              f"<br>اتصلي بالزبون فوراً قبل أن ترجع الطلبية</div>") if c.get("cancelled") else ""
    sit = (f"<div class='sit'>📝 الليفرور: {c['situation_ar']}</div>"
           if c["situation_ar"] and not c.get("cancelled") else "")
    last = f"<div class='last'>آخر متابعة: {c['suivi']}</div>" if c["suivi"] else ""
    d = c.get("day") or 0
    day_txt = (f"اليوم {d} من 3" if 1 <= d <= 3 else
               f"⚫ تجاوز 3 أيام — اليوم {d}" if d > 3 else label)
    html = f"""
    <div class="card" style="background:{bg};border-right:8px solid {border}">
      <div style="display:flex;gap:12px;align-items:flex-start">
        {ring(c.get('day') or 0)}
        <div style="flex:1">
          <div class="lvl" style="color:{border}">{day_txt}</div>
          <div class="who">#{c['order']} — {c['name']}</div>
          {cancel}
          <div>📦 {c['product']} &nbsp;•&nbsp; 💰 {c['price']} دج</div>
          <div>📍 {c['wilaya']} &nbsp;•&nbsp; {mode}</div>
          <div>🚚 {c['state_ar']} &nbsp;•&nbsp; <span style="direction:ltr">{c['tracking']}</span></div>
          {sit}{last}
        </div>
      </div>
    </div>"""
    # one line, no indentation: blank lines/indents would turn into Markdown code blocks
    st.markdown(" ".join(line.strip() for line in html.splitlines()), unsafe_allow_html=True)
    a, b = st.columns(2)
    with a:
        st.link_button("📞 اتصال", c["tel"], use_container_width=True)
    with b:
        st.link_button("💬 واتساب", c["wa"], use_container_width=True)
    r1, r2 = st.columns([3, 1])
    with r1:
        choice = st.selectbox("نتيجة الاتصال", CALL_RESULTS, key=f"res_{c['row']}",
                              label_visibility="collapsed")
    with r2:
        if st.button("💾 حفظ", key=f"save_{c['row']}", use_container_width=True):
            try:
                c["suivi"] = save_call_result(c["row"], choice, SHEET, TAB)
                st.toast(f"✅ تم الحفظ: #{c['order']}")
                st.rerun()
            except Exception as e:
                st.error(f"❌ لم يتم الحفظ: {str(e)[:120]}")
