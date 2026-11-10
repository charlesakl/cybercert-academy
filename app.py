"""CyberCert Academy — Phase 4 AI tutor and gamification."""
import re
import time
from datetime import date
from services.quiz import prepare, score
from services.flashcards import next_review
import streamlit as st
from services.content import load, domain_lessons
from services.ai import ask_tutor, TutorError
from services.gamification import calculate
from services.accounts import AccountClient, AccountError, get_config
from services.progress import serialize, deserialize
import os

st.set_page_config(page_title="CyberCert Academy", page_icon="🛡️", layout="wide")
st.markdown("""<style>
.block-container{padding-top:1.8rem;max-width:1250px}
div[data-testid='stMetric']{background:#192338;border:1px solid #30435d;border-radius:12px;padding:14px}
div[data-testid='stVerticalBlockBorderWrapper']{border-radius:12px}
.lesson-section{margin-top:0.4rem}
.source-readable{white-space:pre-wrap;overflow-wrap:anywhere;word-break:normal;line-height:1.7;font-family:inherit;font-size:0.95rem;max-width:100%;overflow-x:hidden;background:#121d31;border:1px solid #30435d;border-radius:10px;padding:1rem}
</style>""", unsafe_allow_html=True)

NAV = ["Dashboard", "Domains", "Continue Learning", "14-Day Plan", "Practice", "Mock Exam", "AI Cyber Tutor", "Flashcards", "Analytics", "Settings", "View Original Study Guide"]
domains, lessons, plan = load("domains"), load("lessons"), load("study_plan")
questions, flashcards = load("questions"), load("flashcards")
lesson_by_id = {item["id"]: item for item in lessons}
lesson_ids = list(lesson_by_id)

if "current_lesson" not in st.session_state or st.session_state.current_lesson not in lesson_by_id:
    st.session_state.current_lesson = lesson_ids[0]
if "completed" not in st.session_state:
    st.session_state.completed = set()
for state_key, default in [("practice_history", []), ("flashcard_reviews", {}), ("flashcard_index", 0), ("activity_days", []), ("ai_daily_usage", {})]:
    if state_key not in st.session_state:
        st.session_state[state_key] = default
if "nav" not in st.session_state:
    st.session_state.nav = "Dashboard"

def navigate_to(page, lesson_id=None, domain_id=None):
    """Called before widgets are instantiated, avoiding Streamlit state errors."""
    if lesson_id in lesson_by_id:
        st.session_state.current_lesson = lesson_id
        save_progress()
    if domain_id is not None:
        st.session_state.practice_domain = domain_id
    st.session_state.nav = page
    if page == "Continue Learning" and lesson_id in lesson_by_id:
        st.session_state.lesson_selector = lesson_id

def on_lesson_change():
    st.session_state.current_lesson = st.session_state.lesson_selector
    save_progress()

def set_lesson(lesson_id):
    st.session_state.current_lesson = lesson_id
    st.session_state.lesson_selector = lesson_id
    save_progress()

def lesson_title(lesson):
    """Extract a meaningful title when the PDF's source title is only a page label."""
    raw = lesson["body"]
    lines = [re.sub(r"\s+", " ", x).strip() for x in raw.splitlines() if x.strip()]
    for line in lines:
        if re.match(r"^(D\s*O\s*M\s*A\s*I\s*N|of exam|What the exam wants:)", line, re.I):
            continue
        if 5 <= len(line) <= 85 and not line.endswith(('.', ':')) and not re.match(r"^\d+\s", line):
            return line
    return f"Source page {lesson['source_page']}"

def readable_source_text(raw):
    """Normalize PDF layout whitespace for display without altering the saved source."""
    normalized = []
    for line in raw.expandtabs(4).splitlines():
        # Collapse PDF column spacing only in the *readable* presentation.
        normalized.append(re.sub(r"[ \t]{2,}", " ", line).strip())
    return "\n".join(normalized).strip()


def render_readable_source(raw):
    """Responsive source viewer; keep untouched text available as a download."""
    import html
    readable = html.escape(readable_source_text(raw))
    st.markdown(
        '<div class="source-readable">' + readable + '</div>',
        unsafe_allow_html=True,
    )


def render_source_table(lines):
    """Show PDF-spaced comparison blocks as aligned text rather than broken prose.

    Some PDF rows wrap over multiple lines, so forcing them into dataframe cells
    would silently misassociate content. Keep exact alignment until structured
    table data has been verified against the source.
    """
    st.code("\n".join(line.rstrip() for line in lines), language=None)

def render_lesson(body):
    """Readable paragraphs/headings plus aligned comparison blocks; source intact."""
    blocks = re.split(r"\n\s*\n", body.strip())
    i = 0
    while i < len(blocks):
        block = blocks[i]
        # Verified comparison tables on source page D1-P05. The PDF wraps
        # individual cells across lines, so render these as genuine tables.
        if "Objective        Protects against" in block and i + 3 < len(blocks):
            st.table({
                "Objective": ["Confidentiality", "Integrity", "Availability"],
                "Protects against": ["Unauthorized disclosure", "Unauthorized or accidental change", "Disruption of authorized access"],
                "Typical controls": ["Encryption, access control, data classification, masking", "Hashing, digital signatures, change control, input validation", "Redundancy, failover, backups, DDoS protection, capacity"],
                "Example failure": ["Public cloud bucket exposes customer records", "Attacker alters a payment amount in transit", "Ransomware or DDoS takes the site offline"],
            })
            i += 4
            continue
        if "Step                         Question it answers" in block and i + 4 < len(blocks):
            st.table({
                "Step": ["Identification", "Authentication", "Authorization", "Accounting / Auditing"],
                "Question it answers": ["Who do you claim to be?", "Prove it.", "What are you allowed to do?", "What did you do?"],
                "Example": ["Username, badge number, email", "Password + authenticator app", "Read-only access to the HR folder", "Protected audit log entry"],
            })
            i += 5
            continue
        i += 1
        lines = [line.rstrip() for line in block.splitlines() if line.strip()]
        if not lines:
            continue
        clean = [re.sub(r"\s+", " ", x).strip() for x in lines]
        # PDF column spacing is semantic. Never collapse it into running prose.
        spaced = sum(bool(re.search(r"\S {3,}\S", x)) for x in lines)
        if len(lines) >= 3 and spaced >= 2:
            render_source_table(lines)
            continue
        if len(lines) == 1:
            line = clean[0]
            if re.search(r"D\s*O\s*M\s*A\s*I\s*N", line, re.I):
                st.caption(line)
            elif len(line) <= 90 and not line.endswith((".", "?", "!")):
                st.markdown(f"#### {line}")
            else:
                st.write(line)
            continue
        # Multiple lines of ordinary PDF prose are one wrapped paragraph.
        st.write(" ".join(clean))

# Phase 3: require a valid account in connected mode. Local demo mode is explicit
# and must not be enabled for a public deployment.
def _client():
    config = get_config(st.secrets)
    return AccountClient(config) if config else None


def _ensure_token():
    auth = st.session_state.get("auth")
    if not auth:
        return None
    if time.time() >= auth.get("expires_at", 0) - 90:
        fresh = _client().refresh(auth["refresh_token"])
        auth.update(access_token=fresh["access_token"],
                    refresh_token=fresh.get("refresh_token", auth["refresh_token"]),
                    expires_at=time.time() + fresh.get("expires_in", 3600))
    return auth["access_token"]


def record_activity():
    today = date.today().isoformat()
    if today not in st.session_state.activity_days:
        st.session_state.activity_days.append(today)

def save_progress():
    if st.session_state.get("demo_mode"):
        return
    auth = st.session_state.get("auth")
    if not auth or not st.session_state.get("progress_loaded"):
        return
    try:
        _client().save_progress(_ensure_token(), auth["user_id"], serialize(st.session_state))
        st.session_state.save_error = None
    except (AccountError, ValueError, KeyError) as exc:
        st.session_state.save_error = str(exc)


def _sign_out():
    # Do not allow progress from one account to appear in another account.
    for key in ("auth", "progress_loaded", "completed", "current_lesson", "practice_history",
                "flashcard_reviews", "practice", "mock", "flashcard_index", "flashcard_revealed",
                "lesson_selector", "save_error", "activity_days", "ai_daily_usage", "tutor_messages"):
        st.session_state.pop(key, None)
    st.session_state.nav = "Dashboard"


client = _client()
if client is None:
    if os.getenv("CYBERCERT_DEMO_MODE") == "1":
        st.session_state.demo_mode = True
        st.warning("LOCAL DEMO MODE — progress is not saved. Do not enable demo mode on a public site.")
    else:
        st.error("Supabase is not configured. Add [supabase] url and anon_key to .streamlit/secrets.toml. See README.md.")
        st.stop()
else:
    st.session_state.demo_mode = False
    if not st.session_state.get("auth"):
        st.title("🛡️ CyberCert Academy")
        st.caption("Sign in to save your study progress securely across sessions and devices.")
        tab_login, tab_signup, tab_reset = st.tabs(["Sign in", "Create account", "Reset password"])
        with tab_login:
            with st.form("sign_in_form"):
                email = st.text_input("Email", key="login_email")
                password = st.text_input("Password", type="password", key="login_password")
                submit = st.form_submit_button("Sign in", type="primary", use_container_width=True)
            if submit:
                try:
                    result = client.sign_in(email.strip(), password)
                    if not result.get("access_token") or not result.get("user", {}).get("id"):
                        raise AccountError("Sign-in response was incomplete.")
                    st.session_state.auth = {
                        "user_id": result["user"]["id"],
                        "email": result["user"].get("email", email.strip()),
                        "access_token": result["access_token"],
                        "refresh_token": result["refresh_token"],
                        "expires_at": time.time() + result.get("expires_in", 3600),
                    }
                    st.session_state.progress_loaded = False
                    st.rerun()
                except (AccountError, ValueError, KeyError) as exc:
                    st.error(str(exc))
        with tab_signup:
            with st.form("sign_up_form"):
                signup_email = st.text_input("Email", key="signup_email")
                signup_password = st.text_input("Password (at least 8 characters)", type="password", key="signup_password")
                create = st.form_submit_button("Create account", use_container_width=True)
            if create:
                if len(signup_password) < 8:
                    st.error("Choose a password of at least 8 characters.")
                else:
                    try:
                        client.sign_up(signup_email.strip(), signup_password)
                        st.success("Account request received. Check your email for a confirmation link if email verification is enabled, then sign in.")
                    except AccountError as exc:
                        st.error(str(exc))
        with tab_reset:
            with st.form("reset_form"):
                reset_email = st.text_input("Account email")
                reset = st.form_submit_button("Send password reset email")
            if reset:
                try:
                    client.send_reset(reset_email.strip())
                    st.info("If the address is registered, a reset email will be sent. Configure your Supabase redirect URL before using this feature.")
                except AccountError:
                    st.info("If the address is registered, a reset email will be sent.")
        st.stop()

    # Load the student's record only once per authenticated Streamlit session.
    if not st.session_state.get("progress_loaded"):
        try:
            saved = deserialize(client.load_progress(_ensure_token(), st.session_state.auth["user_id"]))
        except (AccountError, ValueError, KeyError) as exc:
            st.error(f"Unable to load your saved progress: {exc}. Try signing in again.")
            st.button("Sign out", on_click=_sign_out)
            st.stop()
        st.session_state.completed = saved["completed"]
        st.session_state.practice_history = saved["practice_history"]
        st.session_state.flashcard_reviews = saved["flashcard_reviews"]
        st.session_state.activity_days = saved["activity_days"]
        st.session_state.ai_daily_usage = saved["ai_daily_usage"]
        if saved.get("current_lesson") in lesson_by_id:
            st.session_state.current_lesson = saved["current_lesson"]
        st.session_state.progress_loaded = True
    st.sidebar.caption(f"Signed in: {st.session_state.auth['email']}")
    st.sidebar.button("Sign out", on_click=_sign_out, use_container_width=True)
    if st.session_state.get("save_error"):
        st.warning(f"Your latest progress could not be saved: {st.session_state.save_error}. Retry after checking your connection.")
        st.button("Retry save", on_click=save_progress)

st.title("🛡️ CyberCert Academy")
st.caption("ISC2 CC · Independent study companion · Phase 4")
nav = st.sidebar.radio("Navigation", NAV, key="nav")

if nav == "Dashboard":
    st.subheader("Your study command center")
    stats = calculate(st.session_state.completed, st.session_state.practice_history, st.session_state.flashcard_reviews, st.session_state.activity_days)
    x1,x2,x3,x4=st.columns(4)
    x1.metric("⚡ XP",stats["xp"])
    x2.metric("🏅 Level",stats["level"])
    x3.metric("🔥 Study streak",f'{stats["streak"]} days')
    x4.metric("🏆 Badges",len(stats["badges"]))
    with st.expander("View earned achievements"):
        if stats["badges"]:
            for badge, description in stats["badges"]: st.write(f"🏆 **{badge}** — {description}")
        else: st.caption("Complete a lesson or quiz to earn your first badge.")
    a, b, c, d = st.columns(4)
    a.metric("Source domains", len(domains))
    b.metric("Extracted lesson pages", len(lessons))
    c.metric("Completed this session", len(st.session_state.completed))
    d.metric("Question bank imported", f"{len(questions)} / 110")
    st.info("Signed-in progress, XP, and achievements are saved to your account." if not st.session_state.demo_mode else "Local demo mode: progress is session-only.")
    st.button("▶ Continue Learning", type="primary", use_container_width=True, on_click=navigate_to, args=("Continue Learning",))
    st.subheader("Domain weights")
    for item in domains:
        st.progress(item["exam_weight_percent"] / 100, text=f'{item["id"]} · {item["title"]} · {item["exam_weight_percent"]}%')

elif nav == "Continue Learning":
    st.subheader("Continue Learning")
    selected = st.selectbox(
        "Choose a lesson", lesson_ids,
        index=lesson_ids.index(st.session_state.current_lesson),
        format_func=lambda lid: f"{lid} · {lesson_title(lesson_by_id[lid])}",
        key="lesson_selector",
        on_change=on_lesson_change,
    )
    # A domain link sets current_lesson before this page is rendered.
    lesson = lesson_by_id[selected]
    st.caption(f'{lesson["domain_id"]} · Source PDF page {lesson["source_page"]} · {lesson["id"]}')
    st.markdown(f"### {lesson_title(lesson)}")
    with st.container(border=True):
        render_lesson(lesson["body"])
    st.caption(f'Source: Claude study guide, page {lesson["source_page"]}. The original PDF is available under View Original Study Guide.')
    st.divider()
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        st.button("← Previous page", disabled=selected == lesson_ids[0],
                  on_click=set_lesson, args=(lesson_ids[max(0, lesson_ids.index(selected)-1)],),
                  use_container_width=True)
    with col2:
        if st.button("✓ Mark page reviewed", use_container_width=True):
            st.session_state.completed.add(selected)
            record_activity()
            save_progress()
            st.success("Lesson marked reviewed and saved." if not st.session_state.demo_mode else "Marked reviewed for this browser session.")
    with col3:
        st.button("Next page →", disabled=selected == lesson_ids[-1],
                  on_click=set_lesson, args=(lesson_ids[min(len(lesson_ids)-1, lesson_ids.index(selected)+1)],),
                  use_container_width=True)
    if selected in st.session_state.completed:
        st.caption("✓ Reviewed this session")

elif nav == "Domains":
    st.subheader("Five exam domains")
    st.write("Open a domain and select a lesson to jump directly to its learning page.")
    for d in domains:
        domain_items = domain_lessons(d["id"])
        with st.expander(f'{d["id"]} · {d["title"]} ({d["exam_weight_percent"]}%)'):
            for item in domain_items:
                left, right = st.columns([5, 1], vertical_alignment="center")
                with left:
                    st.markdown(f"**{lesson_title(item)}**")
                    st.caption(f'Source page {item["source_page"]} · {item["id"]}')
                with right:
                    st.button("Open →", key=f'open_{item["id"]}',
                              on_click=navigate_to, args=("Continue Learning", item["id"]),
                              use_container_width=True)
                st.divider()

elif nav == "14-Day Plan":
    st.subheader("14-day study plan")
    st.caption("Each day links to the relevant learning material and its original PDF source.")
    # Days with multiple domains default to the first relevant domain; users can browse the rest under Domains.
    day_domains = {1:"D1", 2:"D1", 3:"D2", 4:"D2", 5:"D3", 6:"D3", 7:"D1", 8:"D4", 9:"D4", 10:"D4", 11:"D5", 12:"D5", 13:"D5", 14:"D1"}
    for day in plan:
        day_num = day["day"]
        domain_id = day_domains.get(day_num, "D1")
        relevant = domain_lessons(domain_id)
        with st.expander(f'Day {day_num}: {day["focus"]}'):
            st.write(day["task"])
            st.caption(f'Original study guide · PDF page {day["source_page"]}')
            col1, col2, col3 = st.columns(3)
            with col1:
                if day_num == 13:
                    st.button("⏱ Open mock exam", key=f'day_study_{day_num}',
                              on_click=navigate_to, args=("Mock Exam",), use_container_width=True)
                elif relevant:
                    st.button("📖 Start studying", key=f'day_study_{day_num}',
                              on_click=navigate_to, args=("Continue Learning", relevant[0]["id"]),
                              use_container_width=True)
            with col2:
                if day_num == 13:
                    st.button("📊 View analytics", key=f'day_practice_{day_num}',
                              on_click=navigate_to, args=("Analytics",), use_container_width=True)
                else:
                    st.button("🧩 Practice domain", key=f'day_practice_{day_num}',
                              on_click=navigate_to, args=("Practice", None, domain_id),
                              use_container_width=True)
            with col3:
                st.link_button("📄 View source PDF", f'app/static/study_guide.pdf#page={day["source_page"]}',
                               use_container_width=True)
    st.info("For mixed-domain checkpoint days, the links open a starting domain; use Domains and Practice to access the others. Day 13 opens the timed mock exam.")

elif nav == "View Original Study Guide":
    st.subheader("Original study guide")
    st.write("Open the source PDF in your browser or download it for offline reference. Page references in lessons and the 14-day plan correspond to this document.")
    st.link_button("📄 Open original PDF", "app/static/study_guide.pdf#page=1", use_container_width=True)
    with open("data/source/cc_baseline_claude_2026.pdf", "rb") as pdf_file:
        st.download_button("⬇ Download original PDF", pdf_file, file_name="ISC2_CC_2026_Study_Guide.pdf", mime="application/pdf", use_container_width=True)
    st.warning("For local personal study. Confirm redistribution permission before deploying this source PDF on a public site.")

elif nav == "AI Cyber Tutor":
    st.subheader("🤖 AI Cyber Tutor")
    st.caption("Ask questions grounded in the study guide. Extra AI explanations are not official ISC2 material.")
    config = dict(st.secrets.get("ai", {})) if "ai" in st.secrets else {}
    configured = config.get("provider") in ("openai", "anthropic") and bool(config.get("api_key")) and bool(config.get("model"))
    if not configured:
        st.info("Connect an OpenAI or Anthropic API key under .streamlit/secrets.toml to enable tutoring. See README.md. No AI request has been sent.")
    today = date.today().isoformat()
    # This is a convenience cap per account, not a hard billing/security guarantee.
    daily_limit = min(30, max(1, int(config.get("daily_limit", 10))))
    used = int(st.session_state.ai_daily_usage.get(today, 0))
    st.caption(f"Daily tutor requests: {used}/{daily_limit}. Calls may incur provider charges.")
    if "tutor_messages" not in st.session_state:
        st.session_state.tutor_messages = []
    for message in st.session_state.tutor_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    question = st.chat_input("Ask about RTO, RBAC, CIA, incident response…", disabled=not configured or used >= daily_limit)
    if question:
        # Reserve quota before the call, so failed calls do not lead to unbounded retries.
        st.session_state.ai_daily_usage[today] = used + 1
        save_progress()
        st.session_state.tutor_messages.append({"role":"user", "content":question})
        with st.chat_message("user"): st.write(question)
        with st.chat_message("assistant"):
            try:
                result = ask_tutor(question, lessons, config)
                citations = ", ".join(result["sources"]) or "No matching source pages"
                response = result["answer"] + f"\n\n*Retrieved study-guide pages: {citations}*"
                st.markdown(response)
                st.session_state.tutor_messages.append({"role":"assistant", "content":response})
            except TutorError as exc:
                st.error(str(exc))
    st.caption("Tutor conversations are session-only. Do not enter passwords, personal records, or confidential information.")
elif nav == "Practice":
    st.subheader("🧩 Domain Practice")
    st.caption("60 source-based drill questions · explanations after each submission · results saved to your account")
    domain_labels = {d['id']: d['title'] for d in domains}
    chosen_domain = st.selectbox("Choose a domain", list(domain_labels), format_func=lambda d: f"{d} · {domain_labels[d]}", key="practice_domain")
    pool = [q for q in questions if q['mode']=='drill' and q['domain_id']==chosen_domain]
    count = st.select_slider("Questions this session", options=[5, 10, 12], value=12)
    if st.button("Start new practice session", type="primary"):
        st.session_state.practice = {'items':prepare(pool,shuffle_questions=False)[:count], 'index':0, 'answers':{}, 'checked':False, 'finished':False,'domain':chosen_domain}
        st.rerun()
    session = st.session_state.get('practice')
    if session and session['items']:
        if session['finished']:
            result=score(session['items'],session['answers'])
            st.success(f"Practice complete: {result['correct']} / {result['total']} ({result['percent']}%)")
            for q in session['items']:
                selected=session['answers'].get(q['id'])
                if selected != q['correct_option_id']:
                    with st.expander(f"Review · {q['id']}: {q['stem'][:85]}"):
                        st.write(q['stem'])
                        st.write(f"Correct answer: {q['correct_option_id']}")
                        st.write(q['explanation'])
        else:
            i=session['index'];q=session['items'][i]
            st.progress((i+1)/len(session['items']),text=f"Question {i+1} of {len(session['items'])} · {q['domain_id']}")
            st.markdown(f"#### {q['stem']}")
            selected=st.radio("Select your answer",[o['id'] for o in q['options']],index=None,
                format_func=lambda k:next(o['text'] for o in q['options'] if o['id']==k),
                key=f"practice_choice_{id(session)}_{q['id']}",disabled=session['checked'])
            if not session['checked']:
                if st.button("Check answer",type="primary",disabled=selected is None):
                    session['answers'][q['id']]=selected
                    session['checked']=True
                    st.rerun()
            else:
                correct=session['answers'][q['id']]==q['correct_option_id']
                if correct:st.success("Correct!")
                else:st.error(f"Not quite. Correct answer: {q['correct_option_id']}")
                st.info(q['explanation'])
                st.caption(f"Source question {q['source_question_number']} · PDF pages {q['source_page']}, {q['answer_page']}")
                if st.button("Next question →",type="primary"):
                    if i+1==len(session['items']):
                        session['finished']=True
                        st.session_state.practice_history.append({'mode':'practice','domain':session['domain'],'result':score(session['items'],session['answers']),'date':date.today().isoformat()})
                        record_activity()
                        save_progress()
                    else:session['index']+=1;session['checked']=False
                    st.rerun()

elif nav == "Mock Exam":
    st.subheader("⏱️ 50-Question Mock Exam")
    st.caption("60 minutes · one question at a time · no backtracking · answers and explanations after submission")
    mock=st.session_state.get('mock')
    if not mock or mock['finished']:
        if mock and mock['finished']:
            result=score(mock['items'],mock['answers'])
            st.metric("Your mock score",f"{result['correct']} / 50 ({result['percent']}%)")
            if result['percent']>=80:st.success("You reached the guide's 80% overall target.")
            else:st.warning("Below the guide's 80% overall target. Review missed concepts and try again.")
            for d in domains:
                got,total=result['domains'].get(d['id'],[0,0])
                st.progress(got/total if total else 0,text=f"{d['id']} · {got}/{total} ({got/total:.0%})" if total else d['id'])
            for q in mock['items']:
                if mock['answers'].get(q['id'])!=q['correct_option_id']:
                    with st.expander(f"{q['id']} · {q['stem'][:85]}"):
                        st.write(q['stem'])
                        st.write(f"Your answer: {mock['answers'].get(q['id'],'Unanswered')}")
                        st.write(f"Correct answer: {q['correct_option_id']}")
                        st.info(q['explanation'])
        st.warning("This is a practice simulation based on the guide, not the official ISC2 adaptive exam.")
        if st.button("Start 60-minute mock exam",type="primary"):
            for key in list(st.session_state):
                if key.startswith("mock_MOCK-"):
                    del st.session_state[key]
            st.session_state.mock={'items':prepare([q for q in questions if q['mode']=='mock'],shuffle_questions=False),
                'answers':{},'index':0,'deadline':time.time()+3600,'finished':False}
            st.rerun()
    else:
        remaining=max(0,int(mock['deadline']-time.time()))
        if remaining<=0:
            mock['finished']=True
            st.session_state.practice_history.append({'mode':'mock','result':score(mock['items'],mock['answers']),'date':date.today().isoformat()})
            record_activity()
            save_progress()
            st.rerun()
        @st.fragment(run_every="1s")
        def timer_display():
            seconds=max(0,int(st.session_state.mock['deadline']-time.time()))
            st.metric("Time remaining",f"{seconds//60:02d}:{seconds%60:02d}")
            if seconds==0:st.warning("Time expired. Submit or navigate to refresh your results.")
        timer_display()
        i=mock['index'];q=mock['items'][i]
        st.progress((i+1)/50,text=f"Question {i+1} / 50 · {q['domain_id']}")
        st.markdown(f"#### {q['stem']}")
        choice=st.radio("Choose one answer",[o['id'] for o in q['options']],index=None,
            format_func=lambda k:next(o['text'] for o in q['options'] if o['id']==k),key=f"mock_{q['id']}")
        left,right=st.columns([3,1])
        with left:
            if st.button("Save answer and continue →" if i<49 else "Submit exam",type="primary",disabled=choice is None,use_container_width=True):
                if time.time()>=mock['deadline']:
                    mock['finished']=True
                else:
                    mock['answers'][q['id']]=choice
                    if i==49:mock['finished']=True
                    else:mock['index']+=1
                if mock['finished']:
                    st.session_state.practice_history.append({'mode':'mock','result':score(mock['items'],mock['answers']),'date':date.today().isoformat()})
                    record_activity()
                    save_progress()
                st.rerun()
        with right:
            if st.button("Finish early",use_container_width=True):
                mock['finished']=True
                st.session_state.practice_history.append({'mode':'mock','result':score(mock['items'],mock['answers']),'date':date.today().isoformat()})
                record_activity()
                save_progress()
                st.rerun()

elif nav == "Flashcards":
    st.subheader("🗂️ Flashcards")
    st.caption("25 source-based concept cards · review intervals: 1, 3, and 7 days · saved to your account")
    selected_domain=st.selectbox("Filter domain",['All']+[d['id'] for d in domains],key='flashcard_domain')
    cards=[f for f in flashcards if selected_domain=='All' or f['domain_id']==selected_domain]
    due=[f for f in cards if st.session_state.flashcard_reviews.get(f['id'],{}).get('due',date.today())<=date.today()]
    st.metric("Cards due today",len(due))
    if not due:st.success("You're caught up! Change the domain filter or return tomorrow.")
    else:
        pos=st.session_state.get('flashcard_index',0)%len(due)
        card=due[pos]
        st.caption(f"{card['domain_id']} · Card {pos+1} of {len(due)} · PDF source page {card['source_page']}")
        with st.container(border=True):
            st.markdown(f"### {card['front']}")
            if st.session_state.get('flashcard_revealed')==card['id']:
                st.info(card['back'])
            else:
                if st.button("Reveal answer",type="primary",use_container_width=True):
                    st.session_state.flashcard_revealed=card['id'];st.rerun()
        if st.session_state.get('flashcard_revealed')==card['id']:
            c1,c2=st.columns(2)
            for col,label,remembered in [(c1,'Review again',False),(c2,'I remembered',True)]:
                with col:
                    if st.button(label,use_container_width=True):
                        old=st.session_state.flashcard_reviews.get(card['id'],{})
                        due_date,step=next_review(date.today(),old.get('step',0),remembered)
                        st.session_state.flashcard_reviews[card['id']]={'due':due_date,'step':step}
                        record_activity()
                        save_progress()
                        st.session_state.flashcard_revealed=None
                        st.session_state.flashcard_index=0
                        st.rerun()
        if st.button("Skip card →"):
            st.session_state.flashcard_revealed=None
            st.session_state.flashcard_index=pos+1
            st.rerun()

elif nav == "Analytics":
    st.subheader("📊 Learning Analytics")
    stats=calculate(st.session_state.completed, st.session_state.practice_history, st.session_state.flashcard_reviews, st.session_state.activity_days)
    st.write(f'**Level {stats["level"]}** · {stats["xp"]} XP · {stats["streak"]}-day streak · {len(stats["badges"])} badges')
    st.info("Your completed quiz results and flashcard review schedules are saved to your account." if not st.session_state.demo_mode else "Local demo mode: progress is session-only.")
    history=st.session_state.practice_history
    a,b,c=st.columns(3)
    a.metric("Completed quizzes",sum(x['mode']=='practice' for x in history))
    b.metric("Completed mock exams",sum(x['mode']=='mock' for x in history))
    c.metric("Flashcards reviewed",len(st.session_state.flashcard_reviews))
    if history:
        st.dataframe([{'Type':x['mode'],'Domain':x.get('domain','All'),'Score':f"{x['result']['correct']}/{x['result']['total']}", 'Accuracy':f"{x['result']['percent']}%"} for x in history],hide_index=True,use_container_width=True)
    else:st.caption("Finish a practice quiz or mock exam to see results here.")
elif nav == "Settings":
    st.subheader("Settings")
    st.write("AI provider: configured in Streamlit secrets. Theme: dark. Progress persistence: Supabase." if not st.session_state.demo_mode else "Local demo mode: progress is session-only.")
    st.markdown("#### Your learning data")
    st.caption("Clear completed lessons, quiz history and flashcard schedules. This does not delete your Supabase login account.")
    confirm_clear = st.checkbox("I understand that clearing my progress cannot be undone")
    if st.button("Clear my learning progress", disabled=not confirm_clear):
        st.session_state.completed = set()
        st.session_state.practice_history = []
        st.session_state.flashcard_reviews = {}
        st.session_state.activity_days = []
        st.session_state.ai_daily_usage = {}
        st.session_state.current_lesson = lesson_ids[0]
        st.session_state.pop("practice", None)
        st.session_state.pop("mock", None)
        save_progress()
        st.success("Your learning progress was cleared." if not st.session_state.get("save_error") else "Local progress cleared, but cloud save failed. Retry saving before signing out.")
else:
    st.error("Unknown navigation destination.")
st.divider()
st.caption("Independent study resource; not affiliated with or endorsed by ISC2. Source questions are original practice items, not live exam questions.")
