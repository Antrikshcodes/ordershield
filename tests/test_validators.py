"""Test suite for OrderShield AI validation pipeline."""
import pytest
from app.validators import OrderPayload, OrderItem, VerificationDecision
from app.verify import engine


@pytest.fixture
def base_order():
    return OrderPayload(
        order_id="ORD-00123",
        merchant_id="merchant_acme_corp",
        customer_id="cust_9876",
        customer_email="buyer@validcustomer.org",
        vendor_gstin="27AAPFU0939F1ZV",
        total_amount=199.99,
        items=[OrderItem(sku="SKU-ABC", quantity=1, unit_price=199.99)],
        shipping_country="IN",
        billing_country="IN"
    )


@pytest.mark.asyncio
async def test_standard_order_approves(base_order):
    summary = await engine.evaluate_order(base_order)
    assert summary.decision == VerificationDecision.APPROVED
    assert summary.total_risk_score == 0.0


@pytest.mark.asyncio
async def test_country_mismatch_flags_manual_review(base_order):
    base_order.shipping_country = "GB"
    summary = await engine.evaluate_order(base_order)
    assert summary.decision == VerificationDecision.MANUAL_REVIEW
    mismatch_rule = next(r for r in summary.rule_results if r.rule_name == "BillingShippingCountryMatch")
    assert mismatch_rule.passed is False


@pytest.mark.asyncio
async def test_sanctioned_destination_triggers_hard_rejection(base_order):
    base_order.shipping_country = "IR"
    summary = await engine.evaluate_order(base_order)
    assert summary.decision == VerificationDecision.REJECTED
    assert summary.total_risk_score == 1.0