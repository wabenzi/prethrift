# Optional OpenAI End-to-End Test

The repository includes an optional integration test `test_e2e_openai_search.py` that exercises the full retrieval + ranking pipeline using real OpenAI API calls.

## What It Does
1. Spins up a temporary SQLite database.
2. Ingests a subset of design images (band tee, dress, jeans) via the public `/garments/ingest` endpoint.
3. Generates a real description + embedding for the band tee using `/garments/refresh-description` (vision->text + text->embedding).
4. Issues a natural language query intended to match the band tee.
5. Asserts the band tee ranks first (or at least matches via band/queen tokens).

## Why It’s Skipped By Default
Real OpenAI calls introduce cost, latency, and potential flakiness. The test is guarded by two environment variables:

- `OPENAI_API_KEY`: Your valid key.
- `RUN_OPENAI_E2E=1`: Explicit opt-in signal.

If either is missing, the test is skipped.

## How To Run Locally
```bash
export OPENAI_API_KEY=sk-...
export RUN_OPENAI_E2E=1
pytest -q backend/tests/test_e2e_openai_search.py
```

## Adding To CI (Matrix Strategy)
You can extend the GitHub Actions workflow to include an optional job (manual dispatch or nightly) that sets `RUN_OPENAI_E2E=1` and provides the secret key. Example snippet:

```yaml
jobs:
  e2e-openai:
    if: github.event_name == 'workflow_dispatch'
    runs-on: ubuntu-latest
    env:
      RUN_OPENAI_E2E: '1'
      OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: make install
      - run: pytest -q backend/tests/test_e2e_openai_search.py
```

## Troubleshooting
| Issue | Likely Cause | Fix |
|-------|--------------|-----|
| Test skipped | Missing env vars | Export both vars |
| 429 / Rate limit | Key over quota | Retry later / upgrade plan |
| Empty description | Vision model not accessible | Ensure model name valid & key has access |
| Ranking unexpected | Random model variance | Re-run / tighten assertion or add more distractors |

## Future Enhancements
- Add negative feedback simulation to measure penalty impact.
- Capture latency metrics and assert upper bounds.
- Cache generated descriptions in a fixture to reduce repeated costs.

---
Keep this test optional; rely on deterministic unit tests for core logic.
