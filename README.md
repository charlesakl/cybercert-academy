# Phase 4: AI Tutor + Gamification

See [PHASE4_SETUP.md](PHASE4_SETUP.md) for upgrade, configuration, security limitations and testing.

# CyberCert Academy — Phase 3

Independent ISC2 Certified in Cybersecurity (CC) study companion. This version builds on Phase 2.1 and adds **email/password accounts and durable per-student progress** using Supabase Auth + PostgreSQL with row-level security (RLS).

## What's new in Phase 3

- Email/password sign-up, sign-in and sign-out using Supabase Auth.
- Per-student durable progress: completed lesson pages, current lesson, **completed** practice and mock-exam scores, and flashcard due dates/steps.
- Account-scoped analytics, plus a confirmation-gated **Clear my learning progress** option under Settings.
- Short-lived access tokens are refreshed while the Streamlit session is active. After browser reload or Streamlit session loss, sign in again; your completed work will load from Supabase.
- Safe startup behavior: when Supabase is not configured, the app **does not silently run as a public anonymous app**. An explicit local-only demo mode is available for testing.
- Preserves Phase 2.1 navigation, lesson formatting, source links, 110-question bank, mock exam and flashcards.

**Not yet in Phase 3:** AI tutor integration, XP/streaks/badges, resumable unfinished quizzes or in-progress mock exams, and an automated full-account deletion workflow. The mock exam remains a practice simulation, not the official ISC2 exam.

## 1. Run locally in VS Code (Windows)

1. Back up the old folder. Unzip the Phase 3 package and open the **inner `cybercert-academy` folder** in VS Code.
2. Double-click **`start.bat`**, or from the VS Code PowerShell terminal run:

   ```powershell
   .\start.bat
   ```

3. The launcher creates `.venv` (tries Python 3.12, then another Python 3), installs dependencies, and launches Streamlit at http://localhost:8501. No PowerShell script activation is needed.
4. Run tests, if desired:

   ```powershell
   .\.venv\Scripts\python.exe -m pytest -q
   ```

**Without Supabase:** to test the old session-only experience on your own PC, run:

```powershell
$env:CYBERCERT_DEMO_MODE = "1"
.\start.bat
```

Close that terminal to clear the environment variable. **Never enable `CYBERCERT_DEMO_MODE` on a public deployment.**

## 2. Create and configure Supabase

1. Visit https://supabase.com/dashboard and create a project. Keep the database password secure.
2. Open **SQL Editor** in the Supabase project. Paste and run the complete contents of `supabase/schema.sql`. It creates the `user_progress` table, enables RLS, and restricts every read/write to the signed-in student's `auth.uid()`.
3. In **Authentication → Providers**, enable Email authentication. For a public app, keep **email confirmation enabled** and configure an appropriate Site URL and allowed redirect URLs under **Authentication → URL Configuration**. For local testing, include `http://localhost:8501`. Configure SMTP before production to ensure reliable email delivery.
4. In **Project Settings → API Keys** (names may vary), copy the **project URL** and the **publishable / anon key**. Use **only the public key**. **NEVER use the `service_role` or secret API key** in the application.
5. Create `.streamlit/secrets.toml` from `.streamlit/secrets.toml.example` and fill in:

   ```toml
   [supabase]
   url = "https://YOUR_PROJECT.supabase.co"
   anon_key = "YOUR_PUBLISHABLE_OR_ANON_KEY"
   ```

6. Restart `start.bat`. Create a student account and follow the email confirmation instructions if enabled. Sign in, complete a lesson and a quiz, sign out, sign in again and check Analytics.

**Password recovery note:** The app can request Supabase's recovery email, but completing the password change requires configuring a supported recovery redirect/handler. Do not advertise password reset as production-ready until this flow is tested end-to-end.

## 3. Privacy and security

- `secrets.toml` and `.venv/` are excluded by `.gitignore`; do not commit secrets or paste them into screenshots/issues.
- The app uses the **public Supabase key plus each user's own access token**. It never needs privileged database credentials.
- **Database RLS is essential**: client-side filters are not a substitute. Run `supabase/schema.sql` before testing.
- Do not put `CYBERCERT_DEMO_MODE=1` into Streamlit Cloud secrets or environment variables.
- Tokens are kept in Streamlit session memory, not written to the progress database. Reauthentication is required when that session is lost.
- Supabase stores student email addresses and learning history. Before opening registration publicly, publish a privacy notice, decide a retention/deletion policy, and validate signup, account recovery, abuse protection and RLS with real test accounts.
- The source PDF is included for **local provenance** and is served via Streamlit's static endpoint. **Confirm redistribution permission or remove public access to it before publishing a public deployment or repository.**

## 4. Public deployment (after security review)

1. Push to a **private GitHub repository** first.
2. Deploy via Streamlit Community Cloud. Add the `[supabase]` secrets through the Streamlit app's secrets management, **not GitHub**.
3. Set your public Streamlit app URL in Supabase's Auth Site URL and allowed redirect URLs; configure email confirmation and a complete password recovery path.
4. Test signup, confirmation, sign-in, progress persistence, logout, access isolation between two accounts, and lost-network save errors.
5. Confirm licensing for the included guide and source text before public launch.

## Project structure

- `app.py` — Streamlit interface and account gate.
- `services/accounts.py` — Supabase Auth + user-scoped REST calls.
- `services/progress.py` — versioned JSON serialization of saved learning history.
- `supabase/schema.sql` — SQL schema and RLS policies.
- `data/` — structured source lessons, questions, flashcards, study plan.
- `tests/` — content, quiz and persistence unit tests.
- `start.bat` — Windows VS Code startup launcher.

## Troubleshooting

- **Missing `.venv`**: use `start.bat` from the inner `cybercert-academy` folder.
- **`Supabase is not configured`**: add `.streamlit/secrets.toml` or use explicit local demo mode.
- **`relation user_progress does not exist` / `permission denied`**: run `supabase/schema.sql` in the correct project and check RLS.
- **Email not confirmed**: check your inbox/spam, Supabase Email provider and URL configuration.
- **Progress not saved**: check the on-screen save warning and the browser/network connection. Completed work is not considered persisted until the save succeeds.

CyberCert Academy is an independent resource and is not affiliated with or endorsed by ISC2.
