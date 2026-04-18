"""
Salling Group API client
Dækker: Netto, Føtex, Bilka
Gratis API-nøgle: https://developer.sallinggroup.com
"""

import requests
import streamlit as st
from typing import Optional

SALLING_BASE = "https://api.sallinggroup.com"

STORE_TYPE_LABELS = {
    "netto": "Netto",
    "foetex": "Føtex",
    "bilka": "Bilka",
    "salling": "Salling",
}


def get_headers(api_key: str) -> dict:
    return {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    }


def find_nearby_stores(api_key: str, lat: float, lng: float, radius_km: int = 5) -> list[dict]:
    """Find Salling Group butikker inden for radius (km)."""
    try:
        url = f"{SALLING_BASE}/v2/stores"
        params = {
            "geo": f"{lat},{lng}",
            "radius": radius_km,
            "per_page": 20,
        }
        resp = requests.get(url, headers=get_headers(api_key), params=params, timeout=8)
        resp.raise_for_status()
        stores = resp.json()
        # Returnér relevante felter
        return [
            {
                "id": s.get("id", ""),
                "name": s.get("name", ""),
                "brand": STORE_TYPE_LABELS.get(s.get("type", "").lower(), s.get("type", "")),
                "address": s.get("address", {}).get("street", "") + ", " + s.get("address", {}).get("city", ""),
                "distance_km": round(s.get("distance", 0) / 1000, 1),
            }
            for s in stores
        ]
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            st.error("❌ Salling API-nøgle er ugyldig. Tjek din nøgle på developer.sallinggroup.com")
        else:
            st.warning(f"Salling API fejl: {e}")
        return []
    except Exception as e:
        st.warning(f"Kunne ikke hente Salling butikker: {e}")
        return []


def search_product_in_store(api_key: str, query: str, store_id: str, store_name: str, store_brand: str) -> list[dict]:
    """Søg efter en vare i en specifik butik via Salling API."""
    try:
        url = f"{SALLING_BASE}/v1/product-suggestions/relevant-products"
        params = {
            "query": query,
            "store_id": store_id,
        }
        resp = requests.get(url, headers=get_headers(api_key), params=params, timeout=8)
        resp.raise_for_status()
        data = resp.json()

        results = []
        suggestions = data.get("suggestions", [])
        for item in suggestions[:3]:  # Maks 3 resultater per butik
            price = item.get("price", {})
            original = price.get("original", None)
            current = price.get("price", None)
            is_offer = price.get("isOffer", False)

            if current is None:
                continue

            results.append({
                "store": store_name,
                "brand": store_brand,
                "store_id": store_id,
                "product_name": item.get("description", query),
                "price": float(current),
                "original_price": float(original) if original else None,
                "is_offer": is_offer,
                "unit": item.get("unitSize", ""),
            })
        return results

    except requests.exceptions.HTTPError as e:
        st.warning(f"Produktsøgning fejlede for {store_name}: {e}")
        return []
    except Exception:
        return []


def search_all_nearby_stores(api_key: str, query: str, lat: float, lng: float, radius_km: int = 5) -> list[dict]:
    """Søg efter en vare i alle Salling-butikker i nærheden."""
    stores = find_nearby_stores(api_key, lat, lng, radius_km)
    if not stores:
        return []

    all_results = []
    for store in stores:
        results = search_product_in_store(api_key, query, store["id"], store["name"], store["brand"])
        for r in results:
            r["distance_km"] = store["distance_km"]
            r["store_address"] = store["address"]
        all_results.extend(results)

    # Sortér stigende pris
    all_results.sort(key=lambda x: x["price"])
    return all_results
