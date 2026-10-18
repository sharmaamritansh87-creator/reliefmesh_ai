# 7-slide outline (PDF/PPT, file name: TeamName_ReliefMesh AI)

1. **Title + problem** - Floods/landslides in the North East (Assam, Arunachal, Meghalaya): hundreds of messy, duplicate, conflicting reports; limited supplies, boats, trucks; blocked roads. Slow, uncoordinated relief costs lives.
2. **Solution** - ReliefMesh AI: Reports -> Verify -> Allocate -> Plan -> Resolve -> Human approval -> Action. Multi-agent, human-in-the-loop.
3. **Agent architecture** - Intake, Verification, Resource, Routing, Coordinator (uAgents). Typed Models between agents; Coordinator on Agentverse with Chat Protocol, discoverable via ASI:One. Tools: NetworkX graph, optional ASI:One LLM.
4. **Live walkthrough** - Screens: 10 reports -> 8 unique (1 merged, 1 conflict) -> shortages -> truck conflict resolved by priority -> Approve Plan.
5. **Resilience demo** - Road to Dhemaji blocked -> agents recompute -> boat via river / helicopter last resort -> before/after ETAs -> re-approval.
6. **Tech stack + feasibility** - uAgents, Agentverse, ASI:One, FastAPI, NetworkX, React/Vite/Tailwind/Leaflet; runs with no paid keys; tests for dedupe, conflicts, rerouting, approval gate.
7. **Impact + roadmap** - Faster, fairer allocation; safer (human approval). Next: real alert feeds (IMD/ASDMA), SMS/WhatsApp intake, live road status, more regions via config (Odisha, Kerala, Bihar).
