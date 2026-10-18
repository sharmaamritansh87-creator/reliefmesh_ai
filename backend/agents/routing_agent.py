"""Routing Agent: AllocationBatch -> RoutedBatch (road/river/air options; honours blocked edges)."""
from uagents import Context

from ..graph import build_edges, load_config
from ..logic.routing import route_options
from ..models import AllocationBatch, RoutedBatch
from .common import address_of, make_agent

agent = make_agent("routing")
EDGES = build_edges(load_config()["ne_graph"])


@agent.on_message(model=AllocationBatch)
async def on_allocation(ctx: Context, sender: str, msg: AllocationBatch):
    routes = route_options(msg.requests, msg.fleet, EDGES, set(msg.blocked))
    ctx.logger.info(f"[routing] routes for {len(routes)} requests, {len(msg.blocked)} blocked edge(s) -> coordinator")
    await ctx.send(address_of("coordinator"), RoutedBatch(
        run_id=msg.run_id, requests=msg.requests, allocations=msg.allocations,
        fleet=msg.fleet, routes=routes, blocked=msg.blocked))


if __name__ == "__main__":
    agent.run()
