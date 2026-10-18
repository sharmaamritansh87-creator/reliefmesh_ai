"""Verification Agent: ParsedBatch -> VerifiedBatch (dedupe, merge, conflicts, confidence)."""
from uagents import Context

from ..logic.verification import verify
from ..models import ParsedBatch, VerifiedBatch
from .common import address_of, make_agent

agent = make_agent("verification")


@agent.on_message(model=ParsedBatch)
async def on_parsed(ctx: Context, sender: str, msg: ParsedBatch):
    reqs, status, log = verify(msg.reports)
    ctx.logger.info(f"[verification] {len(reqs)} unique requests; {len(log)} merge/conflict events -> resource")
    await ctx.send(address_of("resource"),
                   VerifiedBatch(run_id=msg.run_id, requests=reqs, report_status=status, merge_log=log))


if __name__ == "__main__":
    agent.run()
