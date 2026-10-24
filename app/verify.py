"""OrderShield AI - Core Verification Pipeline."""
from __future__ import annotations

import asyncio
import time
from typing import List, Tuple
from pydantic import BaseModel

from app.config import get_settings
from app.registries import registry_client
from app.validators import (
    BaseRule,
    OrderPayload,
    RuleResult,
    VerificationDecision,
    AddressMatchRule,
    HighValueOrderRule,
    CustomerVelocityRule,
    DisposableEmailDomainRule,
    GSTINComplianceRule,
    VendorProofRule
)


class VerificationSummary(BaseModel):
    order_id: str
    decision: VerificationDecision
    total_risk_score: float
    evaluated_rules: int
    rule_results: List[RuleResult]
    vendor_audit: dict
    latency_ms: float


class VerificationEngine:
    def __init__(self):
        s = get_settings()
        self.review_threshold = s.REVIEW_THRESHOLD
        self.reject_threshold = s.REJECT_THRESHOLD
        self.rules: Tuple[BaseRule, ...] = (
            AddressMatchRule(),
            HighValueOrderRule(threshold=s.HIGH_VALUE_THRESHOLD),
            CustomerVelocityRule(),
            DisposableEmailDomainRule(),
            GSTINComplianceRule(),
            VendorProofRule()
        )

    async def evaluate_order(self, order: OrderPayload) -> VerificationSummary:
        start = time.perf_counter()

        if not await registry_client.is_merchant_authorized(order.merchant_id):
            return VerificationSummary(
                order_id=order.order_id,
                decision=VerificationDecision.REJECTED,
                total_risk_score=1.0,
                evaluated_rules=0,
                rule_results=[RuleResult(
                    rule_name="MerchantRegistryCheck",
                    passed=False,
                    risk_score_delta=1.0,
                    reason="Unauthorized or suspended merchant ID."
                )],
                vendor_audit={},
                latency_ms=round((time.perf_counter() - start) * 1000, 2)
            )

        if registry_client.is_sanctioned_country(order.shipping_country) or \
           registry_client.is_sanctioned_country(order.billing_country):
            return VerificationSummary(
                order_id=order.order_id,
                decision=VerificationDecision.REJECTED,
                total_risk_score=1.0,
                evaluated_rules=0,
                rule_results=[RuleResult(
                    rule_name="SanctionComplianceCheck",
                    passed=False,
                    risk_score_delta=1.0,
                    reason="Destination or origin under trade sanctions."
                )],
                vendor_audit={},
                latency_ms=round((time.perf_counter() - start) * 1000, 2)
            )

        vendor_info = await registry_client.get_vendor_proof(order.vendor_id, order.vendor_gstin)

        context = {
            "customer_recent_order_count": 1,
            "vendor_status": vendor_info
        }

        raw_results = await asyncio.gather(
            *[asyncio.wait_for(rule.evaluate(order, context), timeout=1.5) for rule in self.rules],
            return_exceptions=True
        )

        results: List[RuleResult] = []
        accumulated_risk = 0.0

        for idx, res in enumerate(raw_results):
            if isinstance(res, Exception):
                results.append(RuleResult(
                    rule_name=self.rules[idx].name,
                    passed=False,
                    risk_score_delta=0.1,
                    reason=f"Rule error: {str(res)}"
                ))
                accumulated_risk += 0.1
            else:
                results.append(res)
                accumulated_risk += res.risk_score_delta

        final_score = min(round(accumulated_risk, 3), 1.0)
        decision = (
            VerificationDecision.REJECTED if final_score >= self.reject_threshold else
            VerificationDecision.MANUAL_REVIEW if final_score >= self.review_threshold else
            VerificationDecision.APPROVED
        )

        return VerificationSummary(
            order_id=order.order_id,
            decision=decision,
            total_risk_score=final_score,
            evaluated_rules=len(results),
            rule_results=results,
            vendor_audit=vendor_info,
            latency_ms=round((time.perf_counter() - start) * 1000, 2)
        )


engine = VerificationEngine()