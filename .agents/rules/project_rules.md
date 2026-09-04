# Permanent Project Rules

- This is an existing hackathon project.
- Primary working branch is `frontend-backendintegration`.
- Preserve existing backend architecture.
- Preserve the existing anomaly detector.
- Do not create duplicate anomaly detection logic.
- Preserve useful existing frontend functionality.
- Do not create a second dashboard.
- `frontend/index2.html` is the existing dashboard/anomaly UI unless inspection proves otherwise.
- Backend anomaly results are the source of truth.
- Frontend must eventually display REAL results from the backend rather than hardcoded/mock anomaly values.
- Authentication will be implemented only after the basic frontend/backend/anomaly integration works.
- Never commit secrets or `.env` files.
- Never force push.
- Never reset or destroy existing work.
- Never guess API routes or JSON fields when they can be inspected from the code.
- Work checkpoint-by-checkpoint.
- At the end of every checkpoint: test, update `ANTIGRAVITY_HANDOFF.md`, commit, push, and stop.
