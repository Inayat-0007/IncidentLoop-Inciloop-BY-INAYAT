# Architecture

C4 context: on-call engineer → DevOpsPilot API + AgentOps UI → simulated production tools + knowledge corpus + optional LLM vendor.

Containers: FastAPI process (graph + sim + memory), Vite static UI, MCP stdio (same tools).

Graph: Planner → Incident → Knowledge → Release → Decision → Verification.

Policy: execution is outside the graph.
