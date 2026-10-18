"""Intake Agent: RawBatch -> ParsedBatch (LLM if configured, else rules)."""
from uagents import Context

from ..logic.intake import parse_batch
from ..models import ParsedBatch, RawBatch
from .common import address_of, make_agent

agent = make_agent("intake")


@agent.on_message(model=RawBatch)
async def on_raw(ctx: Context, sender: str, msg: RawBatch):
    parsed = parse_batch(msg.reports)
    ctx.logger.info(f"[intake] {len(parsed)} reports parsed (run {msg.run_id}) -> verification")
    await ctx.send(address_of("verification"), ParsedBatch(run_id=msg.run_id, reports=parsed))


if __name__ == "__main__":
    agent.run()
