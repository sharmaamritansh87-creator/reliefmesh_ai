"""Shared helpers for the five uAgents: creation, deterministic addresses, local vs Agentverse mode."""
import os

from uagents import Agent
from uagents.crypto import Identity

PORTS = {"intake": 8101, "verification": 8102, "resource": 8103, "routing": 8104, "coordinator": 8105}


def seed_of(name: str) -> str:
    """Seed phrase per agent. Override with <NAME>_SEED in .env for real deployments."""
    return os.getenv(f"{name.upper()}_SEED", f"reliefmesh-{name}-demo-seed-change-me")


def address_of(name: str) -> str:
    """Peer address. In Agentverse set <NAME>_ADDRESS; locally it is derived from the seed."""
    return os.getenv(f"{name.upper()}_ADDRESS") or Identity.from_seed(seed_of(name), 0).address


def make_agent(name: str) -> Agent:
    """MAILBOX=1 -> Agentverse mailbox agent; otherwise a local agent with an HTTP endpoint."""
    if os.getenv("MAILBOX", "0") == "1":
        return Agent(name=f"reliefmesh-{name}", seed=seed_of(name), mailbox=True)
    port = PORTS[name]
    return Agent(name=f"reliefmesh-{name}", seed=seed_of(name), port=port,
                 endpoint=[f"http://127.0.0.1:{port}/submit"])
