# CyberCert Academy — Phase 4

## Upgrade from Phase 3

1. Back up the Phase 3 folder and keep its `.streamlit/secrets.toml` safe.
2. Extract this ZIP and open the inner `cybercert-academy` folder in VS Code.
3. Copy **only your existing** `.streamlit/secrets.toml` from Phase 3 into the new folder. Do not share or commit this file.
4. Run `start.bat` from the new folder. The launcher creates `.venv` when needed and starts Streamlit.
5. Sign in with your **existing** Supabase student account. No new database project or schema migration is required.
6. Complete a lesson and check the dashboard XP/achievements. Sign out and back in to verify persistence.

## Optional AI tutor setup

The AI tutor is provider-agnostic. Add the following section to `.streamlit/secrets.toml` **alongside** the existing `[supabase]` section:

```toml
[ai]
provider = "openai"  # or "anthropic"
api_key = "YOUR_API_KEY"
model = "YOUR_PROVIDER_MODEL_ID"
daily_limit = 10
```

Use a model name your provider account supports. Provider API billing is separate from ChatGPT subscriptions and Supabase. The API key must remain server-side in Streamlit secrets. The tutor uses keyword retrieval from the existing lesson pages and identifies retrieved page IDs. It is **not** an authoritative certification reference and can make mistakes.

## Limits and public launch warning

The in-app daily request counter is **best-effort** and stored in the student's existing progress record. It is **not a security-grade, atomic or abuse-proof rate limiter**. Before opening a public AI-enabled site, put a trusted server-side gateway in front of the AI provider with atomic per-account quotas, global spending caps, request throttling and logging. Also review the rights to redistribute the bundled source PDF. Do not deploy the public app with `CYBERCERT_DEMO_MODE=1`.

The tutor chat itself is session-only and not stored in Supabase; daily request counts are stored. Legacy Phase 3 progress records remain readable. Historical activity predating Phase 4 cannot be used to reconstruct study streaks, so streak tracking begins with Phase 4 activity.

## Local tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## Security

Never commit `.streamlit/secrets.toml`, never paste credentials in chat, and never put service-role keys in the Streamlit app. The existing Supabase `user_progress` row-level security remains in place.
