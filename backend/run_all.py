"""Run everything locally: FastAPI dashboard API (thread) + all five agents in one uAgents Bureau.

    python -m backend.run_all
"""
import os
import threading

import uvicorn

API_PORT = int(os.getenv("API_PORT", "8080"))


def _api() -> None:
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=API_PORT, log_level="info")


def main() -> None:
    try:
        from uagents import Bureau
    except ImportError:
        print("uagents is not installed - running the API only (pip install -r requirements.txt).")
        _api()
        return
    threading.Thread(target=_api, daemon=True).start()
    from .agents import (coordinator_agent, intake_agent, resource_agent, routing_agent, verification_agent)
    bureau = Bureau(port=8001, endpoint=["http://127.0.0.1:8001/submit"])
    for m in (intake_agent, verification_agent, resource_agent, routing_agent, coordinator_agent):
        bureau.add(m.agent)
    print(f"API on http://localhost:{API_PORT}  |  Coordinator address: {coordinator_agent.agent.address}")
    bureau.run()


if __name__ == "__main__":
    main()
