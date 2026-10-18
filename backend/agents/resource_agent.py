"""Resource Agent: VerifiedBatch -> AllocationBatch (supplies, volunteers, fleet, shortages)."""
from uagents import Context

from ..graph import load_config
from ..logic.resources import allocate, fleet_from_inventory
from ..models import AllocationBatch, VerifiedBatch
from .common import address_of, make_agent

agent = make_agent("resource")
INVENTORY = load_config()["inventory"]


@agent.on_message(model=VerifiedBatch)
async def on_verified(ctx: Context, sender: str, msg: VerifiedBatch):
    allocs, left = allocate(msg.requests, INVENTORY)
    ctx.logger.info(f"[resource] allocated; remaining stock {left} -> routing")
    await ctx.send(address_of("routing"), AllocationBatch(
        run_id=msg.run_id, requests=msg.requests, allocations=allocs, fleet=fleet_from_inventory(INVENTORY)))


if __name__ == "__main__":
    agent.run()
