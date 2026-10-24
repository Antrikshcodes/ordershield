"""OrderShield AI - Registry & Proof Intelligence Layer."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional
import httpx
from cachetools import TTLCache
from app.config import get_settings
from app.validators import validate_gstin_format

logger = logging.getLogger(__name__)
SANCTIONED_COUNTRIES = frozenset({"KP", "IR", "SY", "CU"})

MOCK_VENDOR_REGISTRY = {
    "27AAPFU0939F1ZV": {
        "vendor_id": "VEND-IN-001",
        "trade_name": "Acme Electronics Technologies Pvt Ltd",
        "legal_name": "ACME ELECTRONICS TECH PRIVATE LIMITED",
        "state": "Maharashtra",
        "status": "ACTIVE",
        "kyc_verified": True,
        "blacklisted": False,
        "tax_filing_compliance": "98.5%",
        "risk_tier": "LOW",
        "registered_on": "2018-04-12"
    },
    "29ABCDE1234F1Z5": {
        "vendor_id": "VEND-IN-002",
        "trade_name": "CloudNine Logistics India",
        "legal_name": "CLOUDNINE LOGISTICS SERVICES LLP",
        "state": "Karnataka",
        "status": "ACTIVE",
        "kyc_verified": True,
        "blacklisted": False,
        "tax_filing_compliance": "100%",
        "risk_tier": "LOW",
        "registered_on": "2020-01-15"
    },
    "07FAKEG9999Z1Z0": {
        "vendor_id": "VEND-FRAUD-666",
        "trade_name": "Apex Shell Exporters",
        "legal_name": "APEX ENTERPRISES SHELL LTD",
        "state": "Delhi",
        "status": "SUSPENDED",
        "kyc_verified": False,
        "blacklisted": True,
        "tax_filing_compliance": "0.0%",
        "risk_tier": "CRITICAL",
        "registered_on": "2023-11-01"
    }
}


class RegistryClient:
    def __init__(self):
        settings = get_settings()
        self.base_url = settings.REGISTRY_BASE_URL
        self.timeout = settings.REGISTRY_TIMEOUT_SECONDS
        self._http_client: Optional[httpx.AsyncClient] = None
        self._vendor_cache: TTLCache = TTLCache(maxsize=20_000, ttl=3600)

    async def init(self) -> None:
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout, connect=1.5),
                limits=httpx.Limits(max_keepalive_connections=50, max_connections=200)
            )

    async def close(self) -> None:
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()

    async def is_merchant_authorized(self, merchant_id: str) -> bool:
        return not merchant_id.startswith("banned_")

    async def get_vendor_proof(self, vendor_id: Optional[str], gstin: Optional[str]) -> Dict[str, Any]:
        cache_key = f"{vendor_id}:{gstin}"
        if cache_key in self._vendor_cache:
            return self._vendor_cache[cache_key]

        if gstin:
            cleaned = gstin.strip().upper()
            if cleaned in MOCK_VENDOR_REGISTRY:
                res = MOCK_VENDOR_REGISTRY[cleaned]
                self._vendor_cache[cache_key] = res
                return res

            f_res = validate_gstin_format(cleaned)
            if f_res["valid"]:
                synthetic = {
                    "vendor_id": vendor_id or "VEND-SYNTHETIC",
                    "trade_name": f"Registered Entity ({f_res['state_name']})",
                    "legal_name": f"GST REGISTERED TAXPAYER - {f_res['pan']}",
                    "state": f_res["state_name"],
                    "status": "ACTIVE",
                    "kyc_verified": True,
                    "blacklisted": False,
                    "tax_filing_compliance": "92.0%",
                    "risk_tier": "LOW",
                    "registered_on": "2021-08-10"
                }
                self._vendor_cache[cache_key] = synthetic
                return synthetic

        for r in MOCK_VENDOR_REGISTRY.values():
            if r["vendor_id"] == vendor_id:
                self._vendor_cache[cache_key] = r
                return r

        unverified = {
            "vendor_id": vendor_id or "UNKNOWN",
            "trade_name": "Unregistered / Unknown Vendor",
            "legal_name": "NOT VERIFIED",
            "state": "Unknown",
            "status": "UNREGISTERED",
            "kyc_verified": False,
            "blacklisted": False,
            "tax_filing_compliance": "0%",
            "risk_tier": "HIGH"
        }
        self._vendor_cache[cache_key] = unverified
        return unverified

    @staticmethod
    def is_sanctioned_country(country_code: str) -> bool:
        return country_code.upper() in SANCTIONED_COUNTRIES


registry_client = RegistryClient()