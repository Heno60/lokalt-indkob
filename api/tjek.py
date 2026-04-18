"""
Tjek / eTilbudsavis API client
Dækker: Rema 1000, Lidl, Aldi, Fakta m.fl.
API: api.etilbudsavis.dk/v2  (gratis, ingen nøgle nødvendig)
"""

import requests
import math
import streamlit as st

TJEK_BASE = "https://api.etilbudsavis.dk"


def search_offers(
    query: str,
    lat: float,
    lng: float,
    radius_m: int = 5000,
    limit: int = 24,
) -> list[dict]:
    """
    Søg efter tilbud via eTilbudsavis v2 API uden login.
    """
    try:
        url = f"{TJEK_BASE}/v2/offers/search"
        params = {
            "query": query,
            "r_lat": lat,
            "r_lng": lng,
            "r_radius": radius_m,
            "r_locale": "da_DK",
            "api_av": "0.3.0",
            "offset": 0,
            "limit": limit,
        }
        headers = {
            "Accept": "application/json",
            "User-Agent": "LokalIndkoeb/1.0",
        }
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        resp.raise_for_status()
        offers = resp.json()

        if not isinstance(offers, list):
            return []

        results = []
        for offer in offers:
            pricing = offer.get("pricing", {})
            price = pricing.get("price")
            pre_price = pricing.get("pre_price")
            if price is None:
                continue

            store = offer.get("store", {})
            branding = offer.get("branding", {})
            dealer = offer.get("dealer", {})
            store_name = store.get("name") or dealer.get("name", "Ukendt")
            brand_name = branding.get("name") or dealer.get("name", store_name)

            store_lat = store.get("latitude")
            store_lng = store.get("longitude")
            distance_km = None
            if store_lat and store_lng:
                distance_km = round(_haversine_km(lat, lng, float(store_lat), float(store_lng)), 1)

            results.append({
                "store": store_name,
                "brand": brand_name,
                "store_id": store.get("id", ""),
                "product_name": offer.get("heading", query),
                "price": float(price),
                "original_price": float(pre_price) if pre_price else None,
                "is_offer": bool(pre_price and float(pre_price) > float(price)),
                "unit": offer.get("quantity", {}).get("unit", {}).get("symbol", ""),
                "distance_km": distance_km,
                "store_address": store.get("street", ""),
                "valid_until": offer.get("run_till", ""),
                "source": "tjek",
            })

        results.sort(key=lambda x: x["price"])
        return results

    except requests.exceptions.ConnectionError:
        st.warning("⚠️ Tjek: Ingen forbindelse.")
        return []
    except requests.exceptions.HTTPError as e:
        st.warning(f"⚠️ Tjek API fejl ({e.response.status_code}): {e.response.text[:200]}")
        return []
    except Exception as e:
        st.warning(f"⚠️ Tjek fejl: {e}")
        return []


def _haversine_km(lat1, lng1, lat2, lng2) -> float:
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1))
         * math.cos(math.radians(lat2))
         * math.sin(dlng / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def get_chain_coverage() -> list[str]:
    return ["Rema 1000", "Lidl", "Aldi", "Fakta/365discount", "Kvickly", "Dagli'Brugsen"]
