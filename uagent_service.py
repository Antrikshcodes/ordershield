"""OrderShield AI - Fetch.ai uAgent Protocol Service."""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Union
from app.config import get_settings
from app.validators import OrderPayload
from app.verify import engine

logger = logging.getLogger("ordershield.uagent")
settings = get_settings()

try:
    asyncio.get_running_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

try:
    from uagents import Agent, Context, Model

    class OrderVerificationRequest(Model):
        order: Dict[str, Any]

        def __init__(self, **data: Any):
            if "order" in data and hasattr(data["order"], "model_dump"):
                data["order"] = data["order"].model_dump()
            super().__init__(**data)

    class OrderVerificationResponse(Model):
        order_id: str
        decision: str
        risk_score: float
        reason: str

    shield_agent = Agent(
        name=settings.AGENT_NAME,
        port=settings.AGENT_PORT,
        seed=settings.AGENT_SEED,
        endpoint=[settings.AGENT_ENDPOINT]
    )

    @shield_agent.on_event("startup")
    async def handle_startup(ctx: Context):
        ctx.logger.info(f"OrderShield Agent active at address: {ctx.agent.address}")

    @shield_agent.on_message(model=OrderVerificationRequest, replies=OrderVerificationResponse)
    async def handle_verification(ctx: Context, sender: str, msg: OrderVerificationRequest):
        order_raw = msg.order
        if isinstance(order_raw, dict):
            order = OrderPayload.model_validate(order_raw)
        else:
            order = order_raw
        summary = await engine.evaluate_order(order)
        reasons = [r.reason for r in summary.rule_results if not r.passed and r.reason]
        await ctx.send(
            sender,
            OrderVerificationResponse(
                order_id=summary.order_id,
                decision=summary.decision.value,
                risk_score=summary.total_risk_score,
                reason="; ".join(reasons) or "All rules satisfied."
            )
        )

    _orig_run_async = shield_agent.run_async

    async def run_agent_async():
        shield_agent._loop = asyncio.get_running_loop()
        return await _orig_run_async()

    shield_agent.run_async = run_agent_async

except Exception as e:
    logger.warning(f"uAgents native driver disabled ({e}). Running in lightweight fallback mode.")

    class OrderVerificationRequest:
        def __init__(self, order: Union[OrderPayload, Dict[str, Any]]):
            if hasattr(order, "model_dump"):
                self.order = order.model_dump()
            else:
                self.order = order

    class OrderVerificationResponse:
        def __init__(self, order_id: str, decision: str, risk_score: float, reason: str):
            self.order_id = order_id
            self.decision = decision
            self.risk_score = risk_score
            self.reason = reason

    async def handle_verification(ctx, sender: str, msg: OrderVerificationRequest):
        order_raw = msg.order
        if isinstance(order_raw, dict):
            order = OrderPayload.model_validate(order_raw)
        else:
            order = order_raw
        summary = await engine.evaluate_order(order)
        reasons = [r.reason for r in summary.rule_results if not r.passed and r.reason]
        await ctx.send(
            sender,
            OrderVerificationResponse(
                order_id=summary.order_id,
                decision=summary.decision.value,
                risk_score=summary.total_risk_score,
                reason="; ".join(reasons) or "All rules satisfied."
            )
        )

    class FallbackAgent:
        address = "agent1q_ordershield_local_node"
        async def run_async(self):
            while True:
                await asyncio.sleep(3600)

        def run(self):
            asyncio.run(self.run_async())

    shield_agent = FallbackAgent()


if __name__ == "__main__":
    shield_agent.run()