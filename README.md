# BuyDZ Suivi — delivery follow-up board

Streamlit app for the confirmation agent. It lists every "Action" order from the
**Branded Store Orders** sheet that is out for delivery with ZR Express, coloured by
delivery day (ZR returns a parcel after 3 days):

- 🟢 day 1 · 🟠 day 2 · 🔴 day 3 (last chance) · ⚫ past day 3
- ⚠️ parcels stuck in "prêt à expédier" for more than 3 days

Each order shows the driver's last note (not answering, postponed, cancelled…),
call / WhatsApp buttons with a ready message, and saves the call result with a
timestamp in the sheet's **Suivi** column.

## Deploy (Streamlit Community Cloud)
1. New app → this repo → `main` → `streamlit_app.py`.
2. Settings → Secrets: same format as `secrets.toml.example` (ZR keys + Google service account).
3. Settings → Sharing: keep the app **private** and invite only the people who need it —
   the app shows customer names and phone numbers.
