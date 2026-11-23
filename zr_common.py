# zr_common.py — shared helpers: settings, Google Sheets client, ZR Express API.
import re
import time
from datetime import datetime, timedelta

import gspread
import requests


def _load_zr_config():
    try:
        import streamlit as st
        return (str(st.secrets["ZR_API_KEY"]), str(st.secrets["ZR_TENANT_ID"]),
                str(st.secrets.get("ZR_BASE_URL", "https://api.zrexpress.app/api/v1")))
    except Exception:
        from config import ZR_API_KEY, ZR_TENANT_ID, ZR_BASE_URL  # local runs only
        return ZR_API_KEY, ZR_TENANT_ID, ZR_BASE_URL


def _get_gspread_client():
    try:
        import streamlit as st
        from google.oauth2.service_account import Credentials
        info = {k: v for k, v in dict(st.secrets["gcp_service_account"]).items() if k != "APP_PASSWORD"}
        creds = Credentials.from_service_account_info(
            info,
            scopes=["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"])
        return gspread.authorize(creds)
    except Exception:
        return gspread.service_account(filename="credentials.json")


ZR_API_KEY, ZR_TENANT_ID, ZR_BASE_URL = _load_zr_config()

DELIVERED_STATES = {"livre", "encaisse", "recouvert"}
RETURNED_STATES = {"recupere_par_fournisseur", "retourne", "retour_fournisseur"}
PENDING_STATE = "action"
MAX_PAGES = 40
API_DELAY = 0.2


def _headers():
    return {"accept": "application/json", "Content-Type": "application/json",
            "X-Api-Key": ZR_API_KEY, "X-Tenant": ZR_TENANT_ID}


def _base():
    return ZR_BASE_URL.rstrip("/")


def _phone9(value):
    digits = re.sub(r"\D", "", str(value or ""))
    return digits[-9:] if len(digits) >= 9 else ""


def _parcel_phones(parcel):
    return {m[-9:] for m in re.findall(r"\d{9,13}", str(parcel.get("customer") or {}))}


def _state(parcel):
    return str((parcel.get("state") or {}).get("name", "")).lower().strip()


def _is_delivered(parcel):
    return _state(parcel) in DELIVERED_STATES


def _is_return(parcel):
    st = _state(parcel)
    return bool(parcel.get("isReturn")) or st in RETURNED_STATES or "retour" in st


def _parse_date(value):
    try:
        return datetime.strptime(str(value).strip()[:10], "%Y-%m-%d")
    except Exception:
        return None


def _fetch_hubs():
    """ZR offices: {hub_id: {name, phone, phone2, street, city, hours, lat, lng}}."""
    hubs = {}
    for page in range(1, 6):
        r = requests.post(f"{_base()}/hubs/search", headers=_headers(),
                          json={"pageNumber": page, "pageSize": 100}, timeout=30)
        if r.status_code != 200:
            break
        data = r.json()
        for h in data.get("items", []):
            phone = h.get("phone") or {}
            addr = h.get("address") or {}
            coords = addr.get("coordinates") or {}
            hubs[h.get("id")] = {
                "name": h.get("name") or "",
                "phone": phone.get("number1") or phone.get("number2") or "",
                "phone2": phone.get("number2") if phone.get("number2") != phone.get("number1") else "",
                "street": addr.get("street") or "",
                "city": addr.get("city") or addr.get("district") or "",
                "hours": h.get("openingHours") or "",
                "lat": coords.get("lat"), "lng": coords.get("lng"),
            }
        if not data.get("hasNext"):
            break
    return hubs


def _fetch_parcels(oldest_date):
    """All parcels (normal + returns) created after oldest_date - 7 days."""
    limit = (oldest_date - timedelta(days=7)) if oldest_date else None
    parcels = {}
    for is_return in ("false", "true"):
        for page in range(1, MAX_PAGES + 1):
            body = {"pageNumber": page, "pageSize": 100, "orderBy": ["createdAt desc"],
                    "advancedFilter": {"filters": [{"field": "isReturn", "operator": "eq",
                                                    "value": is_return}], "logic": "and"}}
            r = requests.post(f"{_base()}/parcels/search", headers=_headers(), json=body, timeout=30)
            if r.status_code != 200:
                raise RuntimeError(f"ZR search failed ({r.status_code}): {r.text[:200]}")
            data = r.json()
            items = data.get("items", [])
            for it in items:
                if it.get("id"):
                    parcels[it["id"]] = it
            last = _parse_date(items[-1].get("createdAt")) if items else None
            if not data.get("hasNext") or (limit and last and last < limit):
                break
            time.sleep(API_DELAY)
    return parcels
