"""OrderShield AI - Validation Rules & GSTIN Engine."""
from __future__ import annotations

import re
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, IPvAnyAddress

GSTIN_REGEX = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$")
DISPOSABLE_DOMAINS = frozenset({
    "tempmail.com", "throwawaymail.com", "guerrillamail.com",
    "10minutemail.com", "mailinator.com", "yopmail.com", "sharklasers.com"
})

INDIAN_STATE_CODES = {
    "01": "Jammu & Kashmir", "02": "Himachal Pradesh", "03": "Punjab", "04": "Chandigarh",
    "06": "Haryana", "07": "Delhi", "08": "Rajasthan", "09": "Uttar Pradesh", "10": "Bihar",
    "19": "West Bengal", "24": "Gujarat", "27": "Maharashtra", "29": "Karnataka",
    "32": "Kerala", "33": "Tamil Nadu", "36": "Telangana", "37": "Andhra Pradesh"
}


def validate_gstin_format(gstin: str) -> Dict[str, Any]:
    cleaned = gstin.strip().upper()
    if not GSTIN_REGEX.match(cleaned):
        return {"valid": False, "reason": "Invalid 15-character GSTIN structure."}

    state_code = cleaned[:2]
    pan = cleaned[2:12]
    entity_code = cleaned[12]
    state_name = INDIAN_STATE_CODES.get(state_code, "Territory / Other State")

    return {
        "valid": True,
        "gstin": cleaned,
        "state_code": state_code,
        "state_name": state_name,
        "pan": pan,
        "entity_code": entity_code
    }


class VerificationDecision(str, Enum):
    APPROVED = "APPROVED"
    MANUAL_REVIEW = "MANUAL_REVIEW"
    REJECTED = "REJECTED"


class OrderItem(BaseModel):
    sku: str = Field(..., min_length=1, max_length=64)
    quantity: int = Field(..., gt=0)
    unit_price: float = Field(..., ge=0.0)


class OrderPayload(BaseModel):
    order_id: str = Field(..., min_length=3, max_length=64)
    merchant_id: str = Field(..., min_length=3, max_length=64)
    customer_id: str = Field(..., min_length=3, max_length=64)
    customer_email: str = Field(...)
    vendor_id: Optional[str] = Field(None, max_length=64)
    vendor_gstin: Optional[str] = Field(None, max_length=15)
    client_ip: Optional[IPvAnyAddress] = None
    currency: str = Field("USD", min_length=3, max_length=3)
    total_amount: float = Field(..., gt=0.0)
    items: List[OrderItem] = Field(..., min_length=1)
    shipping_country: str = Field(..., min_length=2, max_length=2)
    billing_country: str = Field(..., min_length=2, max_length=2)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RuleResult(BaseModel):
    rule_name: str
    passed: bool
    risk_score_delta: float
    reason: Optional[str] = None


class BaseRule(ABC):
    name: str = "BaseRule"
    weight: float = 1.0

    @abstractmethod
    async def evaluate(self, order: OrderPayload, context: Dict[str, Any]) -> RuleResult:
        pass


class GSTINComplianceRule(BaseRule):
    name = "GSTINComplianceCheck"
    weight = 0.45

    async def evaluate(self, order: OrderPayload, context: Dict[str, Any]) -> RuleResult:
        if not order.vendor_gstin:
            if order.billing_country.upper() == "IN" or order.shipping_country.upper() == "IN":
                return RuleResult(
                    rule_name=self.name,
                    passed=False,
                    risk_score_delta=self.weight,
                    reason="Missing mandatory GSTIN for Indian commercial routing."
                )
            return RuleResult(rule_name=self.name, passed=True, risk_score_delta=0.0)

        info = validate_gstin_format(order.vendor_gstin)
        if not info["valid"]:
            return RuleResult(
                rule_name=self.name,
                passed=False,
                risk_score_delta=self.weight,
                reason=f"Malformed GSTIN checksum: {info['reason']}"
            )
        return RuleResult(rule_name=self.name, passed=True, risk_score_delta=0.0)


class VendorProofRule(BaseRule):
    name = "VendorProofAudit"
    weight = 0.50

    async def evaluate(self, order: OrderPayload, context: Dict[str, Any]) -> RuleResult:
        vendor_status = context.get("vendor_status")
        if not vendor_status:
            return RuleResult(rule_name=self.name, passed=True, risk_score_delta=0.0)

        if vendor_status.get("blacklisted", False):
            return RuleResult(
                rule_name=self.name,
                passed=False,
                risk_score_delta=1.0,
                reason="Vendor identified in fraudulent shell entity register."
            )

        if not vendor_status.get("kyc_verified", False):
            return RuleResult(
                rule_name=self.name,
                passed=False,
                risk_score_delta=self.weight,
                reason="Vendor proof unverified: Missing audited tax certificate."
            )

        return RuleResult(rule_name=self.name, passed=True, risk_score_delta=0.0)


class AddressMatchRule(BaseRule):
    name = "BillingShippingCountryMatch"
    weight = 0.35

    async def evaluate(self, order: OrderPayload, context: Dict[str, Any]) -> RuleResult:
        if order.billing_country.upper() != order.shipping_country.upper():
            return RuleResult(
                rule_name=self.name,
                passed=False,
                risk_score_delta=self.weight,
                reason="Billing and shipping jurisdiction mismatch."
            )
        return RuleResult(rule_name=self.name, passed=True, risk_score_delta=0.0)


class HighValueOrderRule(BaseRule):
    name = "HighValueThreshold"

    def __init__(self, threshold: float = 5000.0, weight: float = 0.35):
        self.threshold = threshold
        self.weight = weight

    async def evaluate(self, order: OrderPayload, context: Dict[str, Any]) -> RuleResult:
        if order.total_amount > self.threshold:
            return RuleResult(
                rule_name=self.name,
                passed=False,
                risk_score_delta=self.weight,
                reason=f"Amount ${order.total_amount:,.2f} exceeds threshold (${self.threshold:,.2f})."
            )
        return RuleResult(rule_name=self.name, passed=True, risk_score_delta=0.0)


class CustomerVelocityRule(BaseRule):
    name = "CustomerVelocityCheck"
    weight = 0.40

    async def evaluate(self, order: OrderPayload, context: Dict[str, Any]) -> RuleResult:
        velocity = context.get("customer_recent_order_count", 0)
        if velocity > 5:
            return RuleResult(
                rule_name=self.name,
                passed=False,
                risk_score_delta=self.weight,
                reason=f"Abnormal velocity: {velocity} orders within recent evaluation window."
            )
        return RuleResult(rule_name=self.name, passed=True, risk_score_delta=0.0)


class DisposableEmailDomainRule(BaseRule):
    name = "DisposableEmailCheck"
    weight = 0.30

    async def evaluate(self, order: OrderPayload, context: Dict[str, Any]) -> RuleResult:
        parts = order.customer_email.split("@")
        if len(parts) == 2 and parts[1].lower() in DISPOSABLE_DOMAINS:
            return RuleResult(
                rule_name=self.name,
                passed=False,
                risk_score_delta=self.weight,
                reason=f"Disposable provider detected: @{parts[1].lower()}"
            )
        return RuleResult(rule_name=self.name, passed=True, risk_score_delta=0.0)