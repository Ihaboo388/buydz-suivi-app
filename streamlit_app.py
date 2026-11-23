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
st.markdown(f"""
<div class="summary">
  <div style="font-weight:800;color:#1A3C2A">الطلبيات التي تحتاج متابعة</div>
  <div>🔴 <b>{counts['day3']}</b> &nbsp; 🟠 <b>{counts['day2']}</b> &nbsp; 🟢 <b>{counts['day1']}</b>
       &nbsp; ⚫ <b>{counts['late']}</b> &nbsp; ⚠️ <b>{counts['stuck']}</b></div>
  <div style="color:#4A7A5A;font-size:0.85rem">ابدئي بالأحمر 🔴 ثم البرتقالي 🟠 — شركة التوصيل ترجع الطلبية بعد 3 أيام</div>
</div>""", unsafe_allow_html=True)

show_transit = st.toggle(f"إظهار الطلبيات التي لم تصل بعد للتوصيل 🚚 ({counts['transit'] + counts['missing']})",
                         value=False)

if not any(c["level"] not in ("transit", "missing") for c in cards) and not show_transit:
    st.success("✅ لا توجد طلبيات تحتاج متابعة الآن.")

for c in cards:
    if c["level"] in ("transit", "missing") and not show_transit:
        continue
    border, bg, label = LEVELS[c["level"]]
    mode = f"🏢 StopDesk — {c['hub'] or c['commune']}" if c["stopdesk"] else f"🏠 للمنزل — {c['commune']}"
    sit = f"<div class='sit'>📝 الليفرور: {c['situation_ar']}</div>" if c["situation_ar"] else ""
    last = f"<div class='last'>آخر متابعة: {c['suivi']}</div>" if c["suivi"] else ""
    st.markdown(f"""
    <div class="card" style="background:{bg};border-right:8px solid {border}">
        <div class="lvl" style="color:{border}">{label}</div>
        <div class="who">#{c['order']} — {c['name']}</div>
        <div>📦 {c['product']} &nbsp;•&nbsp; 💰 {c['price']} دج</div>
        <div>📍 {c['wilaya']} &nbsp;•&nbsp; {mode}</div>
        <div>🚚 {c['state_ar']} &nbsp;•&nbsp; <span style="direction:ltr">{c['tracking']}</span></div>
        {sit}{last}
    </div>""", unsafe_allow_html=True)
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
