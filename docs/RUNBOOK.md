# Runbook — DevOpsPilot demo

1. `pip install -r requirements.txt && pytest`
2. `python -m uvicorn backend.main:app --port 8000`
3. Investigate checkout-api 500 after deploy
4. Authorize rollback with `ROLLBACK_TOKEN`
5. Confirm metrics recovered

If rollback is refused: ESCALATE TO HUMAN — missing auth, evidence, or rollback target.
