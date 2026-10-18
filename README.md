# ReliefMesh AI - Multi-Agent Disaster Response (North East India)

> **SIMULATED DEMO DATA - NOT A REAL EMERGENCY.** Decision-support only. A human must approve the plan before any real-world dispatch.

Flood/landslide reports arrive messy and duplicated while supplies, vehicles and volunteers are limited.
ReliefMesh AI turns them into a coordinated, human-approved plan:
**Reports -> Verify -> Allocate -> Plan routes -> Resolve conflicts -> Human approval -> Action.**

Five Fetch.ai **uAgents** (Intake, Verification, Resource, Routing, Coordinator) pass typed Models to each other.
The Coordinator speaks the **Chat Protocol**, so it can be deployed to **Agentverse** and used from **ASI:One**.
Runs locally with **no paid API keys** (an LLM is optional).

## Quick start
```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                   # optional
python -m backend.run_all                              # API on :8080 + all 5 agents in one Bureau

# second terminal
cd frontend && npm i && npm run dev                    # http://localhost:5173
```
Tests: `python -m pytest -q` (dedupe, conflicts, rerouting on a blocked edge, approval gate).

## Demo (3 minutes)
Open the dashboard -> **Start Demo** -> **Next Step** x7. Or click **Simulate Road Blocked** for the replanning moment,
then **Approve Plan**. Script: `docs/demo_script.md`. Architecture: `docs/architecture.md`.

## API
| Method | Path | Purpose |
|---|---|---|
| POST | /reports | add a report and re-run the pipeline |
| POST | /reports/seed | load the 10 seed reports and run all agents |
| GET | /state | full dashboard state |
| GET | /graph | nodes and road/river edges |
| POST | /events/road-blocked | `{"village":"Dhemaji"}` or `{"from":"Lakhimpur","to":"Dhemaji"}` |
| POST | /plan/approve | the **only** way anything becomes "dispatched" |
| POST | /plan/request-changes | `{"note":"...","exclude_vehicles":["Heli-1"]}` |
| POST | /demo/start, /demo/step, /demo/reset | scripted 8-step demo |
| GET | /agents/log | inter-agent message feed |
| GET | /stream | SSE snapshots |

## Deploy to Agentverse and test via ASI:One
1. `pip install uagents` and make sure `uagents_core.contrib.protocols.chat` imports (docs: https://innovationlab.fetch.ai/events/hackathons/fetch-a-thon-3/hackpack).
2. Set unique seeds in `.env` (`COORDINATOR_SEED=...` etc.) and `MAILBOX=1`.
3. Run each agent in its own terminal (they find each other by seed-derived address, or set `<NAME>_ADDRESS`):
   ```bash
   python -m backend.agents.intake_agent
   python -m backend.agents.verification_agent
   python -m backend.agents.resource_agent
   python -m backend.agents.routing_agent
   python -m backend.agents.coordinator_agent
   ```
4. Each agent prints an **Agent inspector** link. Open the Coordinator's, click **Connect -> Mailbox**, and finish in Agentverse.
5. Give the Coordinator a README/description in Agentverse so ASI:One can discover it.
6. In ASI:One (Agent mode) try: `report flooding in Majuli, 150 people need food`, `show current plan`, `road to Dhemaji blocked`, `approve plan`.

Note: chat-driven state lives in the Coordinator process; the dashboard shows it only when the Coordinator runs in the same process (`python -m backend.run_all`).

## Optional LLM
Set `LLM_API_KEY` (ASI:One: base `https://api.asi1.ai/v1`, model `asi1-mini`, or any OpenAI-compatible API) to improve report parsing and plan explanations. Without it, deterministic keyword/regex rules are used.

## Add another region (Odisha, Kerala, Bihar...)
Copy `data/` to `data_odisha/`, edit `ne_graph.json` (nodes, road/river edges, air hubs), `reports.json`, `inventory.json`, `teams.json`, then `RELIEF_DATA_DIR=./data_odisha python -m backend.run_all`. No code changes.

## Layout
```
backend/  models.py graph.py scoring.py llm.py state.py pipeline.py demo.py run_all.py
          logic/   (pure, testable agent logic)   agents/ (uAgents wrappers)   app/main.py (FastAPI)   tests/
data/     reports.json inventory.json teams.json ne_graph.json
frontend/ React + Vite + Tailwind + Leaflet dashboard
docs/     architecture.md slides_outline.md demo_script.md
```

## Known limitations
- Dashboard API runs the pipeline synchronously through `backend/pipeline.py`; the real uAgents run the same logic over messages (used by the chat/ASI:One path). Both share one state in-process.
- Road distances/speeds are approximate demo values, not live traffic or real flood data.
- Vehicle scheduling is greedy (priority order), not a global optimiser; one truck stationed at Jorhat makes far-south sites wait or be deferred.
- uAgents chat-protocol imports can differ between versions - adjust `coordinator_agent.py` if needed.
- The frontend was not built in the authoring sandbox (no network); run `npm i` once.
- Round 2 of Fetch-A-Thon requires code written during the event; use this prototype for Round 1 only.
