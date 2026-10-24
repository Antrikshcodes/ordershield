"""Unit tests for uAgent message handler logic."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.validators import OrderPayload, OrderItem
from uagent_service import handle_verification, OrderVerificationRequest, OrderVerificationResponse


@pytest.mark.asyncio
async def test_uagent_message_handler_dispatches_response():
    mock_ctx = MagicMock()
    mock_ctx.send = AsyncMock()
    mock_ctx.logger = MagicMock()

    order = OrderPayload(
        order_id="ORD-AGENT-01",
        merchant_id="merchant_acme",
        customer_id="cust_001",
        customer_email="agent_user@example.com",
        total_amount=50.0,
        items=[OrderItem(sku="SKU-AG", quantity=1, unit_price=50.0)],
        shipping_country="US",
        billing_country="US"
    )

    request = OrderVerificationRequest(order=order)
    sender_address = "agent1q2dxxxxxxxx"

    await handle_verification(mock_ctx, sender_address, request)

    mock_ctx.send.assert_awaited_once()
    target_addr, sent_payload = mock_ctx.send.call_args[0]
    assert target_addr == sender_address
    assert isinstance(sent_payload, OrderVerificationResponse)
    assert sent_payload.order_id == "ORD-AGENT-01"