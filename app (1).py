"""
JCESOM Student Journey Decision Lab
A Streamlit app for leadership policy refresher training.

Marshall University Joan C. Edwards School of Medicine
Source policy: SOM Student Handbook (July 2024)
"""

import base64
import csv
import io
import random
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st

# =============================================================================
# PAGE CONFIG  (must be first Streamlit call)
# =============================================================================
st.set_page_config(
    page_title="JCESOM Decision Lab",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =============================================================================
# SCORE STORAGE  (SQLite — local file, survives in-session and across users on
#                 the same Streamlit instance; resets on redeploy unless you
#                 add a persistent volume or swap in Google Sheets)
# =============================================================================
DB_PATH = Path(__file__).parent / "scores.db"

# Facilitator password — hardcoded for Dr. Johnson
FACILITATOR_PASSWORD = "DrPJOHNSONBuilds1!"

def _db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            participant_name TEXT,
            started_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS scenario_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            scenario_id TEXT NOT NULL,
            scenario_name TEXT NOT NULL,
            correct INTEGER NOT NULL,
            total INTEGER NOT NULL,
            completed_at TEXT NOT NULL,
            UNIQUE(session_id, scenario_id)
        )
    """)
    return conn

def save_participant(session_id: str, name: str):
    with _db() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO sessions (session_id, participant_name, started_at) VALUES (?, ?, ?)",
            (session_id, name or "Anonymous", datetime.now(timezone.utc).isoformat()),
        )

def save_scenario_result(session_id: str, scenario_id: str, scenario_name: str, correct: int, total: int):
    with _db() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO scenario_results
               (session_id, scenario_id, scenario_name, correct, total, completed_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (session_id, scenario_id, scenario_name, correct, total, datetime.now(timezone.utc).isoformat()),
        )

def fetch_all_results():
    with _db() as conn:
        rows = conn.execute("""
            SELECT s.participant_name, s.started_at, r.scenario_name,
                   r.correct, r.total, r.completed_at, s.session_id
            FROM scenario_results r
            JOIN sessions s ON r.session_id = s.session_id
            ORDER BY r.completed_at DESC
        """).fetchall()
    return rows

def fetch_scenario_average(scenario_id: str):
    with _db() as conn:
        row = conn.execute(
            "SELECT AVG(1.0*correct/total)*100 FROM scenario_results WHERE scenario_id = ?",
            (scenario_id,),
        ).fetchone()
    return row[0] if row and row[0] is not None else None

def fetch_overall_stats():
    with _db() as conn:
        total_sessions = conn.execute("SELECT COUNT(DISTINCT session_id) FROM sessions").fetchone()[0]
        total_attempts = conn.execute("SELECT COUNT(*) FROM scenario_results").fetchone()[0]
        avg_pct = conn.execute(
            "SELECT AVG(1.0*correct/total)*100 FROM scenario_results"
        ).fetchone()[0]
    return total_sessions, total_attempts, (avg_pct or 0)

# =============================================================================
# LOGO LOADER  — embeds marshall_seal.png as a base64 data URI if present
# =============================================================================
def _load_logo_data_uri():
    p = Path(__file__).parent / "marshall_seal.png"
    if p.exists():
        b64 = base64.b64encode(p.read_bytes()).decode()
        return f"data:image/png;base64,{b64}"
    return None

LOGO_DATA_URI = _load_logo_data_uri()

# =============================================================================
# DESIGN TOKENS — Marshall University Brand Palette
# Marshall Green (Kelly), Deep Green, Black, White, neutral grays
# =============================================================================
KELLY = "#00B140"           # Marshall primary kelly green
GREEN_DEEP = "#007934"      # Deeper green for headers / banners
GREEN_DARKER = "#005a26"    # Deepest accent
KELLY_SOFT = "#33C25E"      # Lighter kelly for hovers / highlights
BLACK = "#000000"           # Marshall black (Phase 3 banner echo)
INK = "#1A1A1A"             # Body text near-black
WHITE = "#FFFFFF"
BONE = "#FAFAFA"            # Page background
CREAM = "#F2F2F2"           # Subtle fill
GRAY_LIGHT = "#E8E8E8"      # Borders / dividers
GRAY_MID = "#666666"        # Secondary text
GRAY_DARK = "#333333"       # Strong secondary text
WARN = "#B14A2C"            # Incorrect-answer red, muted

# Aliases used by legacy markup (keep identifiers stable)
FOREST = GREEN_DEEP
FOREST_DEEP = GREEN_DARKER
MOSS = KELLY
GOLD = KELLY
GOLD_LIGHT = KELLY_SOFT
GOLD_DARK = GREEN_DARKER
SLATE = GRAY_MID
RUST = WARN

# =============================================================================
# CUSTOM CSS
# =============================================================================
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400;0,9..144,600;0,9..144,800;1,9..144,400;1,9..144,600&family=Cormorant+Garamond:ital,wght@0,400;0,600;0,700;1,400;1,600&family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {{
    font-family: 'Inter', sans-serif;
}}

.main {{
    background: {BONE};
}}

.app-banner {{
    background: {GREEN_DEEP};
    color: {WHITE};
    padding: 1.4rem 1.6rem 1.5rem;
    border-bottom: 6px solid {KELLY};
    margin: -1rem -1rem 1.5rem -1rem;
    border-radius: 0;
    display: flex;
    align-items: center;
    gap: 1.4rem;
    position: relative;
    flex-wrap: wrap;
}}
.app-banner .logo-mark {{
    flex: 0 0 auto;
    background: transparent;
    padding: 0;
    border: none;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: none;
}}
.app-banner .logo-mark img {{
    display: block;
    height: 96px;
    width: 96px;
    border-radius: 50%;
}}
.app-banner .logo-mark .m-letter {{
    font-family: 'Cormorant Garamond', 'Georgia', serif;
    font-weight: 700;
    font-size: 3rem;
    color: {KELLY};
    line-height: 1;
    text-shadow: 1px 1px 0 {BLACK};
    letter-spacing: -0.03em;
}}
.app-banner .banner-text {{
    flex: 1 1 320px;
    min-width: 0;
}}
.app-banner h1 {{
    font-family: 'Fraunces', serif;
    font-style: italic;
    font-weight: 600;
    font-size: 2.4rem;
    line-height: 1.05;
    margin: 0;
    color: {WHITE};
    letter-spacing: -0.01em;
}}
.app-banner h1 .accent {{
    color: {KELLY};
    font-style: normal;
    font-weight: 800;
}}
.app-banner .source {{
    font-size: 0.78rem;
    color: rgba(255,255,255,0.75);
    letter-spacing: 0.02em;
    margin-top: 0.55rem;
    font-style: italic;
    line-height: 1.4;
}}
@media (max-width: 640px) {{
    .app-banner {{
        flex-direction: column;
        align-items: flex-start;
        gap: 0.9rem;
        padding: 1.2rem 1.2rem 1.4rem;
    }}
    .app-banner .logo-mark img {{
        height: 80px;
        width: 80px;
    }}
    .app-banner h1 {{
        font-size: 1.8rem;
    }}
    .app-banner .source {{
        font-size: 0.72rem;
    }}
}}

.scenario-card {{
    background: {WHITE};
    border: 1px solid {GRAY_LIGHT};
    border-left: 5px solid {KELLY};
    padding: 1.4rem 1.6rem;
    margin-bottom: 1.2rem;
    border-radius: 3px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}}
.scenario-card .name {{
    font-family: 'Fraunces', serif;
    font-weight: 600;
    font-style: italic;
    font-size: 1.5rem;
    color: {BLACK};
    margin-bottom: 0.2rem;
}}
.scenario-card .meta {{
    font-size: 0.72rem;
    color: {GREEN_DEEP};
    letter-spacing: 0.16em;
    text-transform: uppercase;
    font-weight: 700;
    margin-bottom: 0.6rem;
}}
.scenario-card .tagline {{
    color: {GRAY_DARK};
    font-size: 0.94rem;
    line-height: 1.5;
}}

.step-header {{
    background: {BLACK};
    color: {WHITE};
    padding: 1rem 1.4rem;
    border-left: 5px solid {KELLY};
    margin-bottom: 1rem;
    border-radius: 3px;
}}
.step-header .step-num {{
    font-family: 'Fraunces', serif;
    font-style: italic;
    font-size: 0.82rem;
    color: {KELLY};
    letter-spacing: 0.18em;
    text-transform: uppercase;
    font-weight: 600;
}}
.step-header .step-title {{
    font-family: 'Fraunces', serif;
    font-weight: 600;
    font-size: 1.4rem;
    line-height: 1.25;
    margin-top: 0.25rem;
    color: {WHITE};
}}

.situation-box {{
    background: {WHITE};
    border: 1px solid {GRAY_LIGHT};
    padding: 1.2rem 1.4rem;
    border-radius: 3px;
    margin-bottom: 1.2rem;
    border-left: 4px solid {KELLY};
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}}
.situation-box .label {{
    font-size: 0.7rem;
    color: {GREEN_DEEP};
    letter-spacing: 0.2em;
    text-transform: uppercase;
    font-weight: 700;
    margin-bottom: 0.5rem;
}}
.situation-box .text {{
    color: {INK};
    line-height: 1.55;
    font-size: 0.98rem;
}}

.feedback-correct {{
    background: {GREEN_DEEP};
    color: {WHITE};
    padding: 1.2rem 1.4rem;
    border-radius: 3px;
    margin-top: 0.8rem;
    border-left: 5px solid {KELLY};
}}
.feedback-incorrect {{
    background: {BLACK};
    color: {WHITE};
    padding: 1.2rem 1.4rem;
    border-radius: 3px;
    margin-top: 0.8rem;
    border-left: 5px solid {WARN};
}}
.feedback-title {{
    font-family: 'Fraunces', serif;
    font-style: italic;
    font-weight: 600;
    font-size: 1.15rem;
    margin-bottom: 0.5rem;
    color: {WHITE};
}}
.feedback-incorrect .feedback-title {{
    color: {WARN};
}}
.feedback-body {{
    line-height: 1.55;
    font-size: 0.95rem;
    color: {WHITE};
}}
.policy-box {{
    background: rgba(255,255,255,0.10);
    padding: 0.8rem 1rem;
    margin-top: 0.8rem;
    border-radius: 3px;
    border-left: 3px solid {KELLY};
}}
.policy-box .policy-label {{
    font-size: 0.65rem;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: {KELLY_SOFT};
    font-weight: 700;
    margin-bottom: 0.3rem;
}}
.policy-box .policy-text {{
    font-size: 0.88rem;
    line-height: 1.5;
    color: {WHITE};
}}

.summary-card {{
    background: {WHITE};
    border: 1px solid {GRAY_LIGHT};
    border-top: 5px solid {KELLY};
    padding: 1.6rem 1.8rem;
    border-radius: 3px;
    margin-bottom: 1rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}}

.scoreband {{
    display: inline-block;
    padding: 0.3rem 0.9rem;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
}}
.score-high {{ background: {KELLY}; color: {BLACK}; }}
.score-mid {{ background: {BLACK}; color: {KELLY}; }}
.score-low {{ background: {WARN}; color: {WHITE}; }}

.stake-pill {{
    display: inline-block;
    background: {CREAM};
    border: 1px solid {GREEN_DEEP};
    color: {INK};
    padding: 0.2rem 0.6rem;
    border-radius: 3px;
    font-size: 0.75rem;
    font-weight: 600;
    margin-right: 0.4rem;
}}

div[data-testid="stSidebar"] {{
    background: {BLACK};
}}
div[data-testid="stSidebar"] * {{
    color: {WHITE};
}}
div[data-testid="stSidebar"] h2, div[data-testid="stSidebar"] h3 {{
    color: {KELLY} !important;
    font-family: 'Fraunces', serif;
    font-style: italic;
}}
div[data-testid="stSidebar"] .stButton button {{
    background: {GREEN_DEEP};
    color: {WHITE};
    border: 1px solid {KELLY};
}}
div[data-testid="stSidebar"] .stButton button:hover {{
    background: {KELLY};
    color: {BLACK};
    border-color: {KELLY};
}}

.stButton button {{
    background: {KELLY};
    color: {BLACK};
    border: 2px solid {BLACK};
    border-radius: 3px;
    padding: 0.5rem 1.2rem;
    font-weight: 700;
    letter-spacing: 0.04em;
}}
.stButton button:hover {{
    background: {BLACK};
    color: {KELLY};
    border-color: {KELLY};
}}
.stButton button[kind="primary"] {{
    background: {BLACK};
    color: {KELLY};
    border-color: {KELLY};
}}

.stRadio > label {{
    font-weight: 600;
    color: {INK};
}}
</style>
""", unsafe_allow_html=True)

# =============================================================================
# STAKEHOLDER REFERENCE  (full names for every code used in answers)
# =============================================================================
STAKEHOLDERS = {
    "ADM": ("Office of Admissions", "Owns pre-matriculation pipeline, applicant screening, CastleBranch background checks, Technical Standards attestation at acceptance."),
    "OSA": ("Office of Student Affairs", "Confidential first stop for wellness, personal hardship, career advising, MSPE author. Owns the protective wall between wellness disclosure and academic record."),
    "OAA": ("Office of Academic Affairs", "Owns curricular progress, remediation plans, academic deficiencies, leave-of-absence academic logistics, re-entry plans."),
    "OME": ("Office of Medical Education", "Owns curriculum architecture, transitions between phases, CBSE/Step preparation logistics."),
    "APSC": ("Academic & Professional Standards Committee", "Faculty/student committee that reviews academic deficiencies, Honor Code complaints, professionalism concerns; recommends remediation, repeat, or dismissal to the Dean."),
    "WHMD": ("WellHerdMD Wellness Program", "Confidential counseling and wellness — separate from academic record. Limits of confidentiality apply only for imminent safety."),
    "FIN": ("Office of Financial Aid (incl. H$RD MD)", "Emergency aid, satisfactory academic progress, loan deferral during LOA, H$RD MD financial-wellness program."),
    "LC": ("Learning Community Advisor", "Longitudinal faculty mentor; often first informal touchpoint and warm handoff to OSA/WHMD."),
    "CD": ("Course or Clerkship Director", "Owns course-level decisions, immediate fitness-for-duty calls on rotation, escalation to OAA/OSA/APSC."),
    "DSV": ("Disability Services / Accommodations Office", "University-level accommodations review for documented disabilities; coordinates with NBME for licensing exam accommodations."),
    "TIX": ("Title IX Coordinator", "Sex- and gender-based discrimination, harassment, pregnancy accommodations; separate from OSA wellness pathway."),
    "WVMPHP": ("WV Medical Professionals Health Program", "External monitored-recovery program for substance use disorder in trainees and physicians; partners with OSA on confidential treatment compliance."),
    "DEAN": ("Dean of the School of Medicine", "Final authority on dismissal, MSPE non-routine content, technical-standards adjudication; signs APSC outcomes."),
}

# =============================================================================
# SCENARIO DATA
# Each step:  situation, question, options (dict tag→label), correct tag,
# why_right, why_wrongs (dict), policy citation
# =============================================================================

SCENARIOS = [
    # ------------------------------------------------------------------
    {
        "id": "sarah",
        "name": "Sarah B.",
        "level": "Levels 1 → 4 · Full Arc",
        "tagline": "Project PreMed alum. Matriculated 2019 under the legacy curriculum, restarted under the new curriculum, navigated a lapse between Pre-Clerkship and Clerkship, and finished Phases 2 and 3 cleanly.",
        "background": "Sarah completed Project PreMed in undergrad, matriculated to JCESOM in Fall 2019 under the legacy block curriculum, was caught by an institutional curriculum redesign, and chose to restart Phase 1 in the new curriculum. A non-academic life event created a months-long lapse between her Pre-Clerkship Curriculum (PCC) and Clerkship entry. She completed Phase 2 and 3 without academic deficiencies and matched.",
        "steps": [
            {
                "situation": "It's the spring before Sarah's senior year of college. She is in her second summer of Project PreMed and her assigned faculty mentor wants to formalize the relationship for letters of recommendation and a holistic-admissions narrative.",
                "question": "Which JCESOM office owns the pre-matriculation pipeline relationship and is the right home for this work?",
                "options": {
                    "ADM": "Office of Admissions",
                    "OSA": "Office of Student Affairs",
                    "OME": "Office of Medical Education",
                    "LC": "Learning Community Advisor",
                },
                "correct": "ADM",
                "why_right": "Admissions owns every pre-matriculation pathway, including Project PreMed and other pipeline programs. They coordinate with the pipeline faculty mentor, manage the holistic application materials, and trigger CastleBranch background checks and Technical Standards attestation once Sarah is accepted.",
                "why_wrong": {
                    "OSA": "OSA picks up the relationship at matriculation, not before. They author the MSPE three years later, but they don't own the applicant pipeline.",
                    "OME": "OME owns curriculum architecture, not applicant relationships. They wouldn't engage Sarah until orientation.",
                    "LC": "Learning Community advisors are assigned at matriculation, after the acceptance letter."
                },
                "policy": "Per JCESOM admissions policy, all pre-matriculation programming (including Project PreMed) is administered through the Office of Admissions in coordination with named pipeline faculty.",
            },
            {
                "situation": "Sarah is two weeks into her M1 year in Fall 2019. The Dean's office announces a multi-year transition to a new integrated curriculum, with Sarah's class as one of the last to begin under the legacy structure.",
                "question": "Which office is responsible for communicating the transition plan and Sarah's continuation options to her cohort?",
                "options": {
                    "OME": "Office of Medical Education",
                    "OAA": "Office of Academic Affairs",
                    "APSC": "Academic & Professional Standards Committee",
                    "DEAN": "Dean of the School of Medicine",
                },
                "correct": "OME",
                "why_right": "Curricular architecture and phase-to-phase transitions are owned by the Office of Medical Education in partnership with the Curriculum Committee. OME publishes the parallel-tracks comparison and the elective-restart pathway.",
                "why_wrong": {
                    "OAA": "OAA handles individual student academic progress, not class-wide curricular communication.",
                    "APSC": "APSC reviews individual deficiencies and professionalism cases — not curriculum design changes.",
                    "DEAN": "The Dean signs off, but the operational communication runs through OME."
                },
                "policy": "Curriculum redesign is recommended by the Curriculum Committee and executed by OME, with Dean approval for major structural changes.",
            },
            {
                "situation": "Sarah decides to restart Phase 1 under the new curriculum. She needs a formal academic plan that recognizes prior credit but resets her pacing.",
                "question": "Who develops and owns Sarah's individualized academic plan for the restart?",
                "options": {
                    "OAA": "Office of Academic Affairs",
                    "APSC": "Academic & Professional Standards Committee",
                    "OME": "Office of Medical Education",
                    "CD": "Each Course Director independently",
                },
                "correct": "OAA",
                "why_right": "Individualized academic plans — whether for restart, deceleration, or re-entry after leave — are developed and tracked by OAA. OAA coordinates with course directors but holds the master plan.",
                "why_wrong": {
                    "APSC": "APSC reviews the plan if it follows a deficiency, but Sarah's restart is curricular, not disciplinary.",
                    "OME": "OME owns the curriculum framework; OAA owns each student's path through it.",
                    "CD": "Course directors implement; they don't design the cross-course plan."
                },
                "policy": "Per the Pre-Clerkship Academic Progress Policy, OAA develops individualized academic plans and presents them to the student for written acknowledgment.",
            },
            {
                "situation": "Sarah finishes Pre-Clerkship Curriculum (PCC) on schedule. A non-academic family event then requires her to step away for several months before starting Clerkship. She is not on a formal leave but is delayed.",
                "question": "Which office must Sarah engage to convert this lapse into a documented, protective status rather than an unexplained absence?",
                "options": {
                    "OSA": "Office of Student Affairs (with OAA for academic logistics)",
                    "CD": "The first clerkship director she's scheduled for",
                    "APSC": "APSC, since any absence is a professionalism flag",
                    "WHMD": "WellHerdMD, in confidence only",
                },
                "correct": "OSA",
                "why_right": "OSA is the right first stop for any personal hardship that affects pacing. OSA, with OAA, converts the lapse into a documented Personal Leave of Absence, which protects financial aid status, technical standards re-attestation timing, and clerkship eligibility.",
                "why_wrong": {
                    "CD": "Clerkship directors aren't equipped to adjudicate leave; they need OSA to brief them with appropriate confidentiality.",
                    "APSC": "An undocumented absence might draw APSC review later, but the right move is to prevent that by going through OSA first.",
                    "WHMD": "WHMD provides confidential wellness support but cannot convert academic status. Sarah needs the formal LOA pathway."
                },
                "policy": "Personal Leave of Absence is approved by the Dean of Student Affairs (OSA) with OAA coordination. Technical Standards must be re-attested upon return from any LOA.",
            },
            {
                "situation": "Sarah returns and is ready to begin Clerkship rotations. The handbook requires a specific re-entry step before she can see patients.",
                "question": "What must happen before Sarah can begin a clerkship rotation post-LOA?",
                "options": {
                    "OSA": "Re-attestation of Technical Standards plus updated CastleBranch and immunizations",
                    "APSC": "Mandatory APSC hearing for all returning students",
                    "WHMD": "Mandatory mental health clearance from WellHerdMD",
                    "CD": "The clerkship director's individual approval is sufficient",
                },
                "correct": "OSA",
                "why_right": "Per the Technical Standards policy, students must re-attest at acceptance, matriculation, M2, M3, M4, and upon return from any LOA. OSA coordinates the re-attestation packet along with CastleBranch and immunization verification.",
                "why_wrong": {
                    "APSC": "APSC review is not triggered by routine LOA return.",
                    "WHMD": "WHMD doesn't gate-keep clinical re-entry. That would breach the wellness/academic firewall.",
                    "CD": "The clerkship director cannot waive institutional re-entry requirements."
                },
                "policy": "Technical Standards re-attestation is required at acceptance, matriculation, and at the start of each subsequent academic year, and post-LOA.",
            },
            {
                "situation": "Sarah is mid-Phase 2. She has completed four of six clerkship rotations with strong evaluations. No academic concerns.",
                "question": "Who is preparing the documentation that will eventually become the most consequential narrative document of Sarah's career — the MSPE (Medical Student Performance Evaluation)?",
                "options": {
                    "OSA": "Office of Student Affairs (the Dean of OSA is the MSPE author)",
                    "CD": "Each clerkship director writes the MSPE section for their rotation",
                    "LC": "The Learning Community advisor",
                    "OAA": "Office of Academic Affairs",
                },
                "correct": "OSA",
                "why_right": "The Dean of OSA is the named author of the MSPE. Clerkship directors contribute rotation evaluations that become source material, but OSA synthesizes the letter and owns what is — and is not — included.",
                "why_wrong": {
                    "CD": "CDs write rotation evaluations; they do not write the MSPE.",
                    "LC": "LC advisors are referenced in some MSPE structures but don't author the letter.",
                    "OAA": "OAA holds the academic record; OSA writes the narrative."
                },
                "policy": "The MSPE is authored by the Office of Student Affairs and reflects academic performance, professional development, and noteworthy characteristics per AAMC MSPE guidelines.",
            },
            {
                "situation": "It's Spring 4. Sarah has completed her required and away rotations, taken Step 2 CK, and is preparing for Match Day.",
                "question": "Who certifies that Sarah has met all graduation requirements and is eligible to enter residency?",
                "options": {
                    "OAA": "OAA verifies graduation requirements; the Dean confers the degree",
                    "APSC": "APSC must approve every graduating student individually",
                    "OSA": "OSA, as the MSPE author",
                    "CD": "The student's final clerkship director",
                },
                "correct": "OAA",
                "why_right": "OAA owns the academic record and certifies completion of every curricular requirement. The faculty votes to recommend graduation, and the Dean confers the MD degree.",
                "why_wrong": {
                    "APSC": "APSC reviews students with deficiencies, not the routine graduating class.",
                    "OSA": "OSA writes the MSPE but does not certify graduation requirements.",
                    "CD": "Individual clerkship directors submit grades; they don't certify overall completion."
                },
                "policy": "Graduation requires faculty recommendation following OAA verification of all curricular, professionalism, and licensure requirements per JCESOM bylaws.",
            },
        ],
    },
    # ------------------------------------------------------------------
    {
        "id": "marcus",
        "name": "Arjun D.",
        "level": "MD/PhD Program · Phase 1 → Research → Phase 2/3",
        "tagline": "Dual-degree student who completes Phase 1, transfers into the PhD research years, defends, and re-enters Phase 2 with a multi-year gap from clinical training.",
        "background": "Arjun matriculated into the JCESOM/Graduate School MD/PhD program. He completed Phase 1, transitioned into his PhD program for four years, defended his dissertation, and is now returning for Phase 2 clerkships and Phase 3 — with significant time away from clinical exposure.",
        "steps": [
            {
                "situation": "Arjun is accepted to both the MD program and the graduate program. He needs an integrated academic plan that spans both schools, including how Phase 1 USMLE prep aligns with his PhD timeline.",
                "question": "Which JCESOM office is responsible for the integrated MD/PhD academic plan?",
                "options": {
                    "OAA": "OAA in partnership with the MD/PhD Program Director and Graduate School",
                    "ADM": "Admissions, since they admitted him",
                    "OME": "OME, since both programs touch curriculum",
                    "DEAN": "The Dean's office handles all dual-degree plans",
                },
                "correct": "OAA",
                "why_right": "OAA owns the individualized academic plan for any non-standard pathway. For MD/PhD students, OAA partners with the MD/PhD Program Director and the Graduate School to formalize the cross-school timeline.",
                "why_wrong": {
                    "ADM": "Admissions closes its file at matriculation.",
                    "OME": "OME owns the curriculum framework, but OAA owns Arjun's specific pathway through it.",
                    "DEAN": "The Dean signs off on the structure, but operational planning is OAA's lane."
                },
                "policy": "Individualized academic plans for dual-degree students are managed by OAA per the Pre-Clerkship Academic Progress Policy.",
            },
            {
                "situation": "Arjun finishes Phase 1 successfully. He is about to enter his PhD program, which is housed in the Graduate School with its own faculty and timeline.",
                "question": "Who maintains Arjun's status as an active medical student during the research years?",
                "options": {
                    "OSA": "OSA, with the MD/PhD Program Director",
                    "OAA": "OAA alone",
                    "APSC": "APSC, since any departure from standard pacing requires committee review",
                    "DEAN": "The Dean's office issues an annual extension",
                },
                "correct": "OSA",
                "why_right": "OSA holds the active-student status of every MD candidate, including those in approved research pathways. They coordinate with the MD/PhD Program Director to maintain enrollment, financial aid continuity, and Technical Standards tracking.",
                "why_wrong": {
                    "OAA": "OAA tracks academic progress within the MD curriculum; OSA owns student status across both schools.",
                    "APSC": "APSC is not engaged unless there's a deficiency or professionalism issue.",
                    "DEAN": "The Dean approves the program structure; OSA does the operational maintenance."
                },
                "policy": "Active student status during approved research training is maintained by OSA in coordination with named dual-degree program directors.",
            },
            {
                "situation": "Arjun defends his dissertation. He is approximately four years removed from clinical training. He's nervous about Phase 2 re-entry.",
                "question": "Who designs Arjun's clinical re-entry refresher before he begins his first M3 clerkship?",
                "options": {
                    "OME": "OME with input from the MD/PhD Program Director and clerkship directors",
                    "CD": "His first clerkship director alone",
                    "OAA": "OAA assigns him to a standard clerkship sequence with no refresher",
                    "WHMD": "WHMD, to manage re-entry anxiety",
                },
                "correct": "OME",
                "why_right": "OME owns curricular transitions and is best positioned to design a refresher — typically including a Patient Care and Clinical Skills (PCCS) review, simulation sessions, and selected lecture content. The MD/PhD Director and incoming clerkship directors advise on content.",
                "why_wrong": {
                    "CD": "A single CD can orient Arjun to one rotation, not refresh four years of clinical knowledge.",
                    "OAA": "Skipping a refresher exposes Arjun and patients to avoidable risk.",
                    "WHMD": "Anxiety support is appropriate, but it's not a curriculum solution."
                },
                "policy": "Curriculum transitions and re-entry refreshers are designed by OME per its responsibility for curricular continuity.",
            },
            {
                "situation": "Arjun completes the refresher and begins his Internal Medicine rotation. His first preceptor expresses concern that Arjun is uncertain on basic bedside procedures expected of an early M3.",
                "question": "What is the appropriate first response from the clerkship director?",
                "options": {
                    "CD": "Document the observation, notify OAA, and arrange targeted skills coaching — without converting it to a deficiency",
                    "APSC": "Refer immediately to APSC for academic deficiency review",
                    "OSA": "Send Arjun to OSA for a wellness conversation only",
                    "OME": "Restart Phase 1 from the beginning",
                },
                "correct": "CD",
                "why_right": "Early observation of a skill gap in a returning dual-degree student is not a deficiency — it's a predictable transition gap. The CD documents the observation, partners with OAA to add coaching, and reserves APSC for actual policy thresholds (failed assessment, professionalism breach).",
                "why_wrong": {
                    "APSC": "APSC is triggered by formal academic deficiencies or professionalism complaints, not by predictable transition gaps.",
                    "OSA": "Wellness support is welcome but doesn't address the skills gap.",
                    "OME": "Phase 1 restart is wildly disproportionate and not supported by any policy."
                },
                "policy": "Per the Clerkship Assessment, Grading, and Remediation Policy, formative concerns are addressed at the rotation level with OAA support before formal remediation is invoked.",
            },
            {
                "situation": "Arjun completes Phase 2 successfully. During Phase 3 he is preparing his ERAS application and wants the MSPE to acknowledge his dual-degree pathway and research productivity.",
                "question": "Who decides what research credentials and pathway notes appear in the MSPE?",
                "options": {
                    "OSA": "OSA (the MSPE author), with student input",
                    "OAA": "OAA, since they hold the academic record",
                    "DEAN": "The Dean signs off on every individual MSPE",
                    "CD": "Arjun's last clerkship director writes that section",
                },
                "correct": "OSA",
                "why_right": "OSA, as the MSPE author, decides MSPE content including the pathway summary, research narrative, and noteworthy characteristics. Students review a draft for factual accuracy but do not control the framing.",
                "why_wrong": {
                    "OAA": "OAA supplies academic record data to OSA but does not author MSPE narrative.",
                    "DEAN": "The Dean signs only non-routine MSPE content, not every letter.",
                    "CD": "CDs submit rotation evaluations; they don't write MSPE sections."
                },
                "policy": "The MSPE is authored by the Dean of OSA per AAMC MSPE guidelines; students review for factual accuracy.",
            },
            {
                "situation": "Arjun matches into a competitive specialty. He needs to complete final graduation logistics.",
                "question": "Who is responsible for certifying that Arjun has completed both degrees and is eligible for the MD?",
                "options": {
                    "OAA": "OAA, working with the Graduate School and MD/PhD Program Director",
                    "OSA": "OSA",
                    "DEAN": "The Dean alone",
                    "APSC": "APSC",
                },
                "correct": "OAA",
                "why_right": "OAA verifies MD graduation requirements. For MD/PhD students, OAA confirms the PhD has been conferred (or will be conferred in the same cycle) via coordination with the Graduate School. The Dean confers the degree based on faculty recommendation.",
                "why_wrong": {
                    "OSA": "OSA owns the MSPE and student affairs, not graduation certification.",
                    "DEAN": "The Dean signs; OAA verifies.",
                    "APSC": "APSC has no role in routine graduation."
                },
                "policy": "Dual-degree graduation is certified by OAA in partnership with the Graduate School and MD/PhD Program Director.",
            },
        ],
    },
    # ------------------------------------------------------------------
    {
        "id": "aaliyah",
        "name": "Aaliyah J.",
        "level": "Academic Level 1 · M1 · Food Insecurity (Open Disclosure)",
        "tagline": "M1 student facing food insecurity who chose to disclose to her Learning Community advisor early in the year.",
        "background": "Aaliyah is six weeks into MCF. She lives off-campus, sends part of her loan disbursement home to family, and has been skipping meals. She mentions to her LC advisor that she's been 'tired and not eating much' during a routine check-in. She is performing academically but visibly struggling.",
        "steps": [
            {
                "situation": "Aaliyah hints at food insecurity during a casual LC check-in. The advisor recognizes the signal but Aaliyah hasn't named it directly.",
                "question": "What is the LC advisor's right next move?",
                "options": {
                    "LC": "Name the concern gently and offer a warm handoff to OSA — without forcing disclosure",
                    "APSC": "Report to APSC as a professionalism concern (self-care failure)",
                    "CD": "Notify her course director so accommodations can be made",
                    "WHMD": "Schedule her for WellHerdMD without telling her why",
                },
                "correct": "LC",
                "why_right": "LC advisors are the warm-handoff layer. Their job is to name the concern with empathy, offer the OSA pathway, and let the student choose how to proceed. No reporting, no scheduling without consent.",
                "why_wrong": {
                    "APSC": "Food insecurity is a hardship, not a professionalism breach. Routing it to APSC would breach trust and chill future disclosures across the cohort.",
                    "CD": "Notifying the CD without Aaliyah's consent breaks the wellness/academic firewall and embarrasses her with no benefit.",
                    "WHMD": "Scheduling care without informed consent is paternalistic and may damage the LC relationship."
                },
                "policy": "Learning Community advisors operate as confidential mentors; disclosure to other offices requires student consent absent imminent safety concerns.",
            },
            {
                "situation": "Aaliyah agrees to meet with OSA. The Associate Dean asks what she'd like the meeting to accomplish.",
                "question": "What does OSA own at this intake?",
                "options": {
                    "OSA": "Confidential assessment, resource navigation, and decision authority on what (if anything) is documented",
                    "APSC": "Mandatory referral to APSC for any disclosed hardship",
                    "FIN": "Direct referral to Financial Aid before any OSA conversation",
                    "WHMD": "Mandatory WHMD intake before any other support is offered",
                },
                "correct": "OSA",
                "why_right": "OSA is the gatekeeper of the wellness/academic firewall. They assess holistically, navigate resources (FIN, food pantry, WHMD), and decide — with the student — whether anything enters a record.",
                "why_wrong": {
                    "APSC": "APSC has no role in hardship navigation.",
                    "FIN": "OSA coordinates the FIN referral with context; sending Aaliyah cold to FIN misses the wellness layer.",
                    "WHMD": "WHMD is offered, not mandated. Wellness referrals must respect autonomy."
                },
                "policy": "OSA owns confidential intake of non-academic concerns and resource navigation per the Student Affairs framework.",
            },
            {
                "situation": "OSA identifies that Aaliyah qualifies for emergency aid and the H$RD MD financial wellness program.",
                "question": "Which office administers emergency aid and H$RD MD?",
                "options": {
                    "FIN": "Financial Aid Office (administers H$RD MD)",
                    "OSA": "OSA, since they identified the need",
                    "DEAN": "The Dean's discretionary fund only",
                    "LC": "The Learning Community has its own emergency fund",
                },
                "correct": "FIN",
                "why_right": "Financial Aid administers emergency aid, satisfactory academic progress decisions, and the H$RD MD program. OSA makes the warm referral and ensures Aaliyah knows the disclosure to FIN is administrative, not academic.",
                "why_wrong": {
                    "OSA": "OSA identifies the need; FIN delivers the dollars.",
                    "DEAN": "Discretionary funds may exist but aren't the structured pathway.",
                    "LC": "LCs do not administer financial aid."
                },
                "policy": "Emergency aid and H$RD MD are administered by Financial Aid; eligibility is independent of academic standing.",
            },
            {
                "situation": "Aaliyah's MCF course director has noticed she missed two small-group sessions in the past week. He is preparing to ask her about it directly.",
                "question": "What may OSA share with the course director without Aaliyah's explicit per-detail consent?",
                "options": {
                    "OSA": "General 'student is engaged with OSA on a non-academic concern; please coordinate absences through OSA' — no detail",
                    "WHMD": "Full disclosure of her financial situation to help the CD plan",
                    "APSC": "Reroute the CD's concern to APSC to keep OSA out of academics",
                    "LC": "Let the LC handle the CD conversation",
                },
                "correct": "OSA",
                "why_right": "OSA's role is to give the CD the minimum information needed to coordinate — typically a general 'engaged with OSA, route absences through us' — without disclosing the underlying hardship. This preserves the firewall while keeping the CD able to act.",
                "why_wrong": {
                    "WHMD": "Disclosure of financial detail without Aaliyah's consent is a confidentiality breach.",
                    "APSC": "Avoiding the CD by routing to APSC is worse, not better — it puts the hardship into a disciplinary track.",
                    "LC": "LCs aren't equipped to manage the absence-coordination conversation."
                },
                "policy": "OSA may share that a student is engaged with their office for general coordination purposes without disclosing protected wellness details.",
            },
            {
                "situation": "Six weeks later, Aaliyah is eating regularly, performing well, and asks OSA whether any of this 'goes on her record.'",
                "question": "What is the accurate answer?",
                "options": {
                    "OSA": "Wellness engagement and emergency aid are not part of the academic record or MSPE",
                    "APSC": "Yes — all OSA engagement is reportable to APSC at the end of M1",
                    "DEAN": "The Dean reviews every emergency aid recipient at promotion",
                    "WHMD": "Counseling notes follow her into MSPE",
                },
                "correct": "OSA",
                "why_right": "Wellness engagement, emergency aid, and counseling are not part of the academic record. The MSPE reflects academic performance and professional development — not financial hardship navigation.",
                "why_wrong": {
                    "APSC": "False. APSC reviews academic and professionalism cases — not wellness engagement.",
                    "DEAN": "False. The Dean does not review aid recipients at promotion.",
                    "WHMD": "False. WHMD records are confidential and protected."
                },
                "policy": "The MSPE reflects academic and professional performance; wellness, counseling, and financial support are not included.",
            },
        ],
    },
    # ------------------------------------------------------------------
    {
        "id": "jamal",
        "name": "Jamal R.",
        "level": "Academic Level 3 · M3 · New Parent",
        "tagline": "M3 with a newborn and no childcare support, considering a part-time job to make rent.",
        "background": "Jamal is two rotations into his M3 year. His partner returned to shift work; their newborn is six weeks old. Childcare options have fallen through. Loan disbursements aren't covering both rent and infant supplies. He is exhausted, missing study time, and has begun looking at evening part-time work.",
        "steps": [
            {
                "situation": "Jamal is preparing to talk to someone at JCESOM. He's worried that disclosing the situation will make people think he can't hack M3.",
                "question": "Where should Jamal start?",
                "options": {
                    "OSA": "Office of Student Affairs — confidential first conversation",
                    "CD": "His current clerkship director, since they manage his schedule",
                    "APSC": "APSC, to get ahead of any professionalism concern",
                    "FIN": "Financial Aid, since rent is the immediate pressure",
                },
                "correct": "OSA",
                "why_right": "OSA is the right first stop for any life event affecting a student's training. They assess the whole picture — financial, wellness, academic pacing — and orchestrate the right resources without forcing premature disclosure to the CD.",
                "why_wrong": {
                    "CD": "Going to the CD first leaks personal hardship into a clinical evaluation context without OSA's protective framing.",
                    "APSC": "APSC has no preventive role; engaging them frames hardship as a disciplinary risk.",
                    "FIN": "Financial Aid can help with funds, but OSA orchestrates the whole response and protects the academic record."
                },
                "policy": "OSA is the confidential first stop for personal hardship affecting medical training.",
            },
            {
                "situation": "OSA asks Jamal whether he is sleeping, eating, and connected to mental-health support. He admits he is not.",
                "question": "Which resource does OSA refer him to for confidential mental health support?",
                "options": {
                    "WHMD": "WellHerdMD",
                    "APSC": "APSC mental-health committee",
                    "DEAN": "The Dean's personal chaplaincy office",
                    "CD": "A peer support group run by his clerkship director",
                },
                "correct": "WHMD",
                "why_right": "WellHerdMD is the confidential wellness arm of student services. WHMD records are kept separate from the academic file. Limits of confidentiality apply only when there is imminent safety risk.",
                "why_wrong": {
                    "APSC": "APSC reviews academic and professionalism cases, not mental health support.",
                    "DEAN": "Pastoral support may exist but isn't the structured wellness pathway.",
                    "CD": "Clerkship directors don't run mental health programs and shouldn't have therapeutic relationships with their evaluees."
                },
                "policy": "WellHerdMD provides confidential mental health services; records are kept separate from academic records absent imminent safety concerns.",
            },
            {
                "situation": "Jamal raises the part-time job idea. OSA flags that the student workload policy addresses this.",
                "question": "Who governs the workload-and-outside-employment expectation, and what is the typical answer for an M3?",
                "options": {
                    "OME": "OME owns the workload policy; outside employment during clerkships is strongly discouraged, but a personal LOA is an alternative",
                    "OSA": "OSA approves part-time jobs case by case",
                    "CD": "The clerkship director decides per rotation",
                    "APSC": "APSC must approve any outside employment",
                },
                "correct": "OME",
                "why_right": "Student workload is governed by OME under the Student Workload Policy. Clerkship years carry full-time clinical obligations including call; sustained outside employment is inconsistent with that workload. A personal LOA or deceleration is the structurally supported alternative.",
                "why_wrong": {
                    "OSA": "OSA navigates the conversation but the workload policy itself is OME's.",
                    "CD": "Individual CDs implement but don't write the workload policy.",
                    "APSC": "APSC reviews deficiencies, not employment requests."
                },
                "policy": "Per the Student Workload Policy, outside employment during clerkship rotations is generally discouraged given full-time clinical responsibilities including call obligations.",
            },
            {
                "situation": "Jamal decides he'd rather take a Personal LOA for one semester than try to work and stay enrolled.",
                "question": "Who approves the Personal Leave of Absence?",
                "options": {
                    "OSA": "The Dean of Student Affairs approves with APSC notification and OAA coordination on academic plan",
                    "DEAN": "Only the Dean of the School of Medicine",
                    "APSC": "APSC must vote on every LOA",
                    "OAA": "OAA approves all leaves alone",
                },
                "correct": "OSA",
                "why_right": "Personal LOAs are approved by the Dean of Student Affairs, with APSC notification and OAA coordinating the academic plan and re-entry timeline.",
                "why_wrong": {
                    "DEAN": "The School Dean is informed but doesn't approve routine personal LOAs.",
                    "APSC": "APSC is notified, not asked to vote, on personal LOAs.",
                    "OAA": "OAA coordinates the academic plan but doesn't approve the leave itself."
                },
                "policy": "Personal LOA approval rests with the Dean of OSA, with APSC notification and OAA academic-plan coordination.",
            },
            {
                "situation": "Jamal returns from his LOA five months later. He is ready for clerkship re-entry.",
                "question": "What re-entry requirements does OSA coordinate before Jamal can see patients again?",
                "options": {
                    "OSA": "Technical Standards re-attestation, CastleBranch and immunization update, and a re-entry briefing",
                    "APSC": "Mandatory APSC hearing before re-entry",
                    "WHMD": "WHMD clearance letter required before re-entry",
                    "CD": "Sole approval by the next clerkship director",
                },
                "correct": "OSA",
                "why_right": "Post-LOA re-entry follows the standard Technical Standards re-attestation pathway plus updated CastleBranch and immunization records, coordinated by OSA. No APSC hearing is required for routine personal LOA return.",
                "why_wrong": {
                    "APSC": "Personal LOA return does not trigger APSC.",
                    "WHMD": "WHMD does not gate-keep clinical re-entry.",
                    "CD": "CDs welcome students back; they don't override institutional re-entry requirements."
                },
                "policy": "Re-entry from any LOA requires Technical Standards re-attestation per the Technical Standards policy.",
            },
            {
                "situation": "Jamal is now preparing his residency applications. He's worried his LOA will be visible.",
                "question": "What does the MSPE actually say about a personal LOA?",
                "options": {
                    "OSA": "A leave of absence is acknowledged in the MSPE; the reason for a personal LOA is not detailed",
                    "APSC": "All LOAs trigger an MSPE flag visible to programs",
                    "DEAN": "The Dean writes a personal letter explaining every LOA",
                    "WHMD": "WHMD engagement is reported in the MSPE",
                },
                "correct": "OSA",
                "why_right": "Per AAMC MSPE guidelines, a leave of absence is acknowledged but the underlying reason for a personal LOA is not detailed. OSA controls the framing and reviews it with the student.",
                "why_wrong": {
                    "APSC": "There is no special APSC flag for personal LOAs.",
                    "DEAN": "The Dean signs the MSPE; there is no separate Dean's letter for routine LOAs.",
                    "WHMD": "WHMD engagement is confidential and not disclosed in the MSPE."
                },
                "policy": "Per AAMC MSPE guidelines, leaves of absence are noted; reasons for personal LOAs are not detailed.",
            },
        ],
    },
    # ------------------------------------------------------------------
    {
        "id": "david",
        "name": "Daniel K.",
        "level": "Academic Level 2 · M2 · Sole-Breadwinner Family",
        "tagline": "M2 student supporting a wife and three children on loan disbursements alone; first exam failure triggers a structured remediation pathway.",
        "background": "Daniel is the financial center of his household — his wife stopped working when he matriculated, they have three young children, and they live on loan disbursements. Eight weeks into REIGN he fails his first CBSE-style block exam. This is his first academic deficiency.",
        "steps": [
            {
                "situation": "REIGN exam results post. Daniel has failed below the threshold for the block.",
                "question": "What is the policy-mandated next step?",
                "options": {
                    "CD": "Course director documents the deficiency and initiates the remediation pathway with OAA",
                    "APSC": "Automatic APSC hearing within 48 hours",
                    "OSA": "OSA convenes a wellness-only review",
                    "DEAN": "The Dean reviews every individual failure",
                },
                "correct": "CD",
                "why_right": "A single failed exam triggers the Pre-Clerkship Academic Progress pathway: the CD documents, OAA opens an individualized remediation plan, and APSC is engaged only at policy thresholds (e.g., multiple deficiencies, failed remediation).",
                "why_wrong": {
                    "APSC": "APSC is not automatically convened for a first single deficiency.",
                    "OSA": "OSA is engaged in parallel for wellness, but the academic pathway is CD→OAA.",
                    "DEAN": "The Dean approves APSC recommendations, not individual exam failures."
                },
                "policy": "Per the Pre-Clerkship Academic Progress Policy, a single deficiency triggers a documented remediation plan with OAA; APSC is engaged at policy thresholds.",
            },
            {
                "situation": "OAA opens Daniel's remediation plan. They also recognize that financial stress may be contributing.",
                "question": "What parallel referral does OAA make?",
                "options": {
                    "OSA": "Warm referral to OSA for whole-student support (wellness + FIN coordination)",
                    "APSC": "Direct referral to APSC for a financial-hardship review",
                    "FIN": "Direct to FIN, skipping OSA",
                    "DEAN": "The Dean's office for a discretionary loan",
                },
                "correct": "OSA",
                "why_right": "OAA owns the academic plan but does not navigate wellness or finances directly. A warm referral to OSA opens the door to WHMD, FIN, and emergency aid without forcing Daniel to assemble those resources himself.",
                "why_wrong": {
                    "APSC": "APSC has no role in financial hardship.",
                    "FIN": "Skipping OSA loses the wellness layer and the coordinated framing.",
                    "DEAN": "Discretionary funds aren't the structured pathway."
                },
                "policy": "OAA coordinates with OSA for non-academic factors affecting academic progress.",
            },
            {
                "situation": "Daniel's remediation plan includes monthly check-ins with his LC advisor and a tutor through the academic support unit.",
                "question": "Who provides the longitudinal mentoring touchpoint that complements OAA's structured plan?",
                "options": {
                    "LC": "Learning Community advisor",
                    "APSC": "An APSC-assigned monitor",
                    "WHMD": "WHMD assigns a peer mentor",
                    "DEAN": "Dean-assigned executive mentor",
                },
                "correct": "LC",
                "why_right": "Learning Communities provide longitudinal faculty mentorship that runs parallel to formal remediation. The LC advisor is the relational anchor — they notice trends and warm-hand-off to OSA/OAA when needed.",
                "why_wrong": {
                    "APSC": "APSC monitors compliance with formal remediation; they don't mentor.",
                    "WHMD": "WHMD provides counseling, not academic mentorship.",
                    "DEAN": "The Dean doesn't run mentorship pairings."
                },
                "policy": "Learning Community advisors provide longitudinal mentorship as part of JCESOM's student support architecture.",
            },
            {
                "situation": "Daniel successfully remediates REIGN. He completes the rest of M2 with no further deficiencies and is preparing for CBSE.",
                "question": "Who owns the CBSE preparation framework?",
                "options": {
                    "OME": "OME — CBSE Prep is the named final block of Phase 1",
                    "APSC": "APSC monitors all M2 students through CBSE",
                    "CD": "Each course director runs their own CBSE prep",
                    "OSA": "OSA owns CBSE strategy",
                },
                "correct": "OME",
                "why_right": "CBSE Prep is a named six-week block in the Phase 1 curriculum, owned by OME. OAA tracks individual readiness; APSC engages only if a student fails to meet promotion thresholds.",
                "why_wrong": {
                    "APSC": "APSC doesn't monitor routine CBSE preparation.",
                    "CD": "CDs contribute to content but don't own the framework.",
                    "OSA": "OSA supports wellness, not exam preparation."
                },
                "policy": "CBSE Prep is the final six-week block of Phase 1 and is owned by OME.",
            },
            {
                "situation": "Daniel clears CBSE and is on track to enter Phase 2. His earlier deficiency is now historical.",
                "question": "Does the single REIGN deficiency appear in Daniel's MSPE?",
                "options": {
                    "OSA": "Per AAMC MSPE guidelines, course failures appear in the academic history; OSA frames the narrative including remediation and recovery",
                    "APSC": "APSC removes it from the record at promotion",
                    "OAA": "OAA can purge the deficiency once remediated",
                    "DEAN": "The Dean redacts first failures",
                },
                "correct": "OSA",
                "why_right": "MSPE academic history reflects the record, including a course failure with remediation. OSA, as the MSPE author, frames the narrative — including the successful remediation, completion of CBSE, and clean Phase 2 entry.",
                "why_wrong": {
                    "APSC": "APSC does not edit the academic record at promotion.",
                    "OAA": "Remediation is documented; the original deficiency is part of the academic history.",
                    "DEAN": "The Dean signs the MSPE; redaction of factual content is not standard."
                },
                "policy": "MSPE academic history reflects the academic record per AAMC MSPE guidelines.",
            },
        ],
    },
    # ------------------------------------------------------------------
    # NEW SCENARIO 6: Honor Code — AI on assessment
    # ------------------------------------------------------------------
    {
        "id": "sasha",
        "name": "Priya S.",
        "level": "Academic Level 2 · M2 · Honor Code Investigation",
        "tagline": "M2 reported by a peer for using generative AI on a take-home reflection assignment with a stated no-AI policy.",
        "background": "During the REIGN block, a take-home reflection assignment carries an explicit course policy prohibiting use of generative AI. A classmate notices that Priya's submitted reflection has hallmarks of AI generation and reports the concern. This is the test of Marshall's Honor Code process at the assignment level — a place leadership often defaults to the wrong office.",
        "steps": [
            {
                "situation": "A classmate decides to formally report the suspected AI use. They are unsure where to send it.",
                "question": "Where does an Honor Code complaint enter the system?",
                "options": {
                    "APSC": "Academic & Professional Standards Committee — APSC owns Honor Code complaints",
                    "CD": "The course director, who decides whether to escalate",
                    "OSA": "OSA, as the confidential first stop",
                    "DEAN": "Directly to the Dean of the School of Medicine",
                },
                "correct": "APSC",
                "why_right": "Honor Code and professionalism complaints enter through APSC. APSC has a defined intake, fact-finding, and hearing structure for these cases. Routing through the CD or OSA first muddies the process.",
                "why_wrong": {
                    "CD": "The CD may be a witness or have written the policy at stake — they should not adjudicate. They may be informed but are not the intake point.",
                    "OSA": "OSA's wellness role conflicts with disciplinary intake. They support the student, they do not adjudicate the complaint.",
                    "DEAN": "The Dean is the final reviewer of APSC recommendations, not the intake point."
                },
                "policy": "Per the Honor Code, allegations of professionalism violations are reviewed by APSC under its published procedures.",
            },
            {
                "situation": "APSC opens a fact-finding review. Priya needs to be formally notified.",
                "question": "Who notifies Priya and explains her procedural rights?",
                "options": {
                    "APSC": "The APSC chair, in writing, with copies to OSA so wellness support can be activated",
                    "DEAN": "The Dean, personally, in a meeting",
                    "CD": "The course director who flagged the assignment",
                    "OSA": "OSA, on behalf of APSC, to keep the disciplinary tone soft",
                },
                "correct": "APSC",
                "why_right": "APSC owns the notification because they own the process and the procedural rights. OSA is copied so they can offer wellness support and procedural advising — but the notification itself comes from APSC to keep the academic and wellness functions clearly separated.",
                "why_wrong": {
                    "DEAN": "The Dean enters at the recommendation stage, not the notification stage.",
                    "CD": "The CD is fact-witness-adjacent and should not own notification.",
                    "OSA": "OSA cannot send the notification without conflating wellness and discipline."
                },
                "policy": "APSC procedures specify that the committee chair issues formal notification of investigation and hearing.",
            },
            {
                "situation": "Priya is preparing for the APSC hearing. She's overwhelmed and doesn't know whether she's allowed to bring anyone with her.",
                "question": "What support is available to a student facing an APSC hearing?",
                "options": {
                    "OSA": "OSA provides confidential procedural advising and wellness support; the student may bring a faculty advocate per APSC procedure",
                    "APSC": "Students appear alone — that's the rule",
                    "WHMD": "WHMD attends the hearing as her advocate",
                    "DEAN": "Only the Dean can advise her",
                },
                "correct": "OSA",
                "why_right": "OSA is the right confidential coach for a student facing APSC — they explain the procedure, prepare the student, and connect her to wellness resources. APSC procedure also typically permits a faculty advocate. WHMD is not an advocate.",
                "why_wrong": {
                    "APSC": "APSC procedure allows for an advocate; students do not appear unsupported.",
                    "WHMD": "WHMD provides therapy, not procedural advocacy.",
                    "DEAN": "The Dean is the reviewer of APSC's recommendation; advising the accused would create a conflict."
                },
                "policy": "APSC procedure permits a faculty advocate; OSA provides confidential procedural advising.",
            },
            {
                "situation": "APSC concludes that the policy was violated and recommends remediation (a professionalism development plan and an unsatisfactory grade on the assignment) rather than dismissal.",
                "question": "Who renders the final decision on APSC recommendations?",
                "options": {
                    "DEAN": "The Dean of the School of Medicine",
                    "APSC": "APSC's recommendation is itself the final decision",
                    "OSA": "OSA, since they author the MSPE",
                    "OAA": "OAA, since they own academic progress",
                },
                "correct": "DEAN",
                "why_right": "APSC recommends; the Dean of the School of Medicine renders the final decision and signs the outcome letter. The Dean may accept, modify, or reject the recommendation.",
                "why_wrong": {
                    "APSC": "APSC recommends. They do not have unilateral authority over student status.",
                    "OSA": "OSA writes the MSPE but does not adjudicate APSC outcomes.",
                    "OAA": "OAA implements the academic-progress consequences but does not render the disciplinary decision."
                },
                "policy": "APSC submits recommendations to the Dean of the School of Medicine for final adjudication.",
            },
            {
                "situation": "Priya completes the professionalism development plan. She wants to know how this will appear in her MSPE.",
                "question": "Who decides what — if anything — appears in the MSPE about this incident?",
                "options": {
                    "OSA": "OSA decides MSPE content per AAMC guidance; Honor Code adverse actions may be reportable depending on outcome severity, with Dean review for non-routine content",
                    "APSC": "APSC dictates the MSPE language",
                    "DEAN": "The Dean writes the MSPE himself",
                    "CD": "The course director includes a line in the rotation evaluation",
                },
                "correct": "OSA",
                "why_right": "OSA authors the MSPE and decides what appears, guided by AAMC guidance. A formal adverse action may be reportable; an internal professionalism development plan is handled with care. The Dean reviews non-routine MSPE content.",
                "why_wrong": {
                    "APSC": "APSC's recommendation may influence MSPE content but does not dictate the language.",
                    "DEAN": "The Dean reviews non-routine content; he does not author the letter.",
                    "CD": "CDs write rotation evaluations, not MSPE sections."
                },
                "policy": "Per AAMC MSPE guidelines, reportable adverse actions are disclosed; OSA, as MSPE author, frames content with Dean review for non-routine matters.",
            },
            {
                "situation": "Priya returns to coursework. The course director and her LC advisor want guidance on how to engage her without re-traumatizing her or appearing biased.",
                "question": "Who briefs the CD and LC on what they need to know — and don't need to know — to support Priya?",
                "options": {
                    "OSA": "OSA — they brief in general terms appropriate to each role",
                    "APSC": "APSC briefs the CD with the full case file",
                    "DEAN": "The Dean briefs both personally",
                    "WHMD": "WHMD reaches out to both since they hold the wellness lens",
                },
                "correct": "OSA",
                "why_right": "OSA owns the re-entry briefing. They give the CD the minimum information to function — typically a 'student has completed an APSC process and is supported in reintegration; please coordinate with us on any concerns.' Specific case detail is not shared.",
                "why_wrong": {
                    "APSC": "Sharing the full case file with the CD prejudices future evaluation.",
                    "DEAN": "This is not a Dean-level operational task.",
                    "WHMD": "WHMD does not brief academic faculty."
                },
                "policy": "OSA coordinates appropriate, minimum-necessary information sharing with faculty involved in a student's reintegration.",
            },
        ],
    },
    # ------------------------------------------------------------------
    # NEW SCENARIO 7: Hidden food insecurity surfacing through hunger
    #                 affecting studying and clinical performance
    # ------------------------------------------------------------------
    {
        "id": "devon",
        "name": "Devon P.",
        "level": "Academic Level 3 · M3 · Hidden Food Insecurity",
        "tagline": "M3 quietly skipping meals to stretch his refund — hunger and exhaustion are eroding his study time, his shelf scores, and his presence on rounds. No one knows.",
        "background": "Devon is on his Internal Medicine clerkship. He is the first in his family to attend medical school. He has been food insecure since M1 but has never disclosed it. His refund covers rent and his share of family expenses back home; what's left has not stretched to a full grocery week in months. He eats one real meal a day, drinks coffee through the rest. Studying after a 12-hour clinical day on an empty stomach has become impossible. His first shelf exam came back below the cohort mean. His clerkship director has noticed he looks pale and withdrawn on rounds and rarely speaks up. Devon is ashamed and has told no one. This scenario tests how leadership identifies and supports a student whose hardship is showing up as academic and clinical drift — not as misconduct.",
        "steps": [
            {
                "situation": "Devon's clerkship director has noticed three signals over four weeks: a borderline first shelf exam, quiet withdrawal on rounds, and visible exhaustion. There is no professionalism concern — just a worry that something is wrong. The CD wants to do the right thing.",
                "question": "What is the policy-aligned first move?",
                "options": {
                    "OSA": "Place a confidential call to OSA describing the pattern, ask OSA to reach out to Devon, and continue normal clinical supervision",
                    "APSC": "File a professionalism concern with APSC to get the case on record",
                    "CD": "Pull Devon into a private debrief and ask him directly what's wrong",
                    "OAA": "Open an academic remediation file with OAA based on the shelf score alone",
                },
                "correct": "OSA",
                "why_right": "When a faculty member sees a struggling student without a clear academic deficiency or professionalism breach, OSA is the right first call. OSA can reach Devon as a wellness check, separate from his clinical evaluation, and invite disclosure without putting his record at risk. The CD keeps supervising; OSA opens the door.",
                "why_wrong": {
                    "APSC": "There is no professionalism concern — only a worry. Filing with APSC routes a struggling student into a disciplinary track and chills future disclosure.",
                    "CD": "A direct CD conversation collapses the firewall between evaluation and personal life. Devon may feel his honest answer will affect his grade.",
                    "OAA": "A single borderline shelf is not a deficiency threshold. Opening an OAA file prematurely labels Devon academically without addressing the underlying cause."
                },
                "policy": "JCESOM's student support framework directs faculty observations of non-academic concern to OSA before academic or disciplinary processes are engaged.",
            },
            {
                "situation": "OSA invites Devon to a confidential check-in. Devon is wary — he assumes he is in trouble. He sits down across from the Associate Dean.",
                "question": "What is OSA's right opening?",
                "options": {
                    "OSA": "Frame the meeting as a wellness check-in; share that a faculty member cares about how he is doing; do not lead with the shelf score",
                    "OAA": "Open with the shelf score and ask him to explain it",
                    "APSC": "Tell Devon a concern has been raised and read the observations aloud",
                    "CD": "Have the CD join so Devon hears it from both",
                },
                "correct": "OSA",
                "why_right": "OSA's job is to make disclosure safe. Leading with the shelf score positions Devon as the accused. Leading with 'a faculty member who thinks highly of you wanted us to check in — clerkships are hard, how are you actually doing?' opens the conversation. Devon needs to know this conversation does not feed his academic file.",
                "why_wrong": {
                    "OAA": "Leading with the shelf score is leading with the symptom; Devon will defend and deflect.",
                    "APSC": "Framing this as a concern-being-raised invokes the disciplinary register and shuts the conversation down.",
                    "CD": "The CD's presence collapses the wellness/evaluation firewall."
                },
                "policy": "OSA conducts confidential wellness intake separate from academic and disciplinary processes.",
            },
            {
                "situation": "Devon discloses. He has been food insecure since M1. He sends part of every loan refund home to his mother and a younger sibling. What is left does not cover groceries for a full month. He eats one meal a day, has lost fifteen pounds, can't focus to study after rounds, and is ashamed because he believes asking for help means he doesn't belong here.",
                "question": "Who is responsible for delivering the financial resources Devon needs, and how does the referral happen?",
                "options": {
                    "FIN": "Financial Aid administers emergency aid and H$RD MD enrollment; OSA makes a warm referral the same week with framing about confidentiality and that this is administrative, not academic",
                    "OSA": "OSA writes Devon a check from a discretionary fund and closes the loop",
                    "DEAN": "The Dean's office handles all financial hardship personally",
                    "LC": "The Learning Community has its own emergency fund",
                },
                "correct": "FIN",
                "why_right": "Financial Aid administers emergency aid, the H$RD MD financial wellness program, and any satisfactory-academic-progress decisions that may follow. OSA makes the warm referral and ensures Devon understands the disclosure to FIN is purely administrative and does not enter his academic record.",
                "why_wrong": {
                    "OSA": "OSA navigates and warm-refers but does not administer aid. A back-channel check sidesteps the structured pathway and the longer-term H$RD MD enrollment that gives Devon ongoing footing.",
                    "DEAN": "Dean-level discretionary funds exist but are not the structured pathway and don't create the ongoing H$RD MD relationship.",
                    "LC": "Learning Communities mentor; they do not administer financial aid."
                },
                "policy": "Emergency aid and H$RD MD are administered by Financial Aid; eligibility is independent of academic standing.",
            },
            {
                "situation": "Devon also tells OSA he has not slept more than five hours a night in three months and has been crying in the parking garage before rotations. He is not suicidal but he is exhausted to the bone.",
                "question": "Where does the emotional and mental health support pathway live?",
                "options": {
                    "WHMD": "WellHerdMD — confidential mental health support; OSA makes the warm referral with consent",
                    "OSA": "OSA continues to be the only point of contact",
                    "APSC": "APSC reviews any student in distress",
                    "CD": "His clerkship director provides supportive supervision",
                },
                "correct": "WHMD",
                "why_right": "WellHerdMD is the confidential wellness arm. Records are kept separate from the academic record. OSA's job is to make the warm referral with Devon's consent — not to be the therapist. Limits of confidentiality apply only for imminent safety; Devon's distress, while serious, is not at that threshold.",
                "why_wrong": {
                    "OSA": "OSA is not a clinical provider. Concentrating all support in OSA leaves Devon without the longitudinal clinical relationship he needs.",
                    "APSC": "APSC is not a mental-health pathway.",
                    "CD": "Clerkship directors should not have therapeutic relationships with their evaluees."
                },
                "policy": "WellHerdMD provides confidential mental health services; records are kept separate from academic records absent imminent safety concerns.",
            },
            {
                "situation": "Devon's next shelf is in six weeks. With emergency aid in place, regular meals, and WHMD engagement starting, he wants to recover his academic footing. He's worried about whether his first shelf score will follow him.",
                "question": "Who designs and owns Devon's academic recovery plan if one is needed?",
                "options": {
                    "OAA": "OAA — an individualized academic plan with study support, with OSA's wellness context coordinated in the background",
                    "APSC": "APSC must approve any individualized plan",
                    "OSA": "OSA designs the academic plan alongside the wellness plan",
                    "CD": "The clerkship director writes the plan unilaterally",
                },
                "correct": "OAA",
                "why_right": "OAA owns individualized academic plans, including academic support and tutoring. OSA shares the relevant wellness context with Devon's consent so the plan is realistic. APSC is reserved for formal deficiencies and remediations beyond what an academic plan handles.",
                "why_wrong": {
                    "APSC": "APSC engages at policy thresholds (e.g., failed shelf, multiple deficiencies), not for proactive academic plans.",
                    "OSA": "OSA owns wellness coordination; OAA owns academic plans. Each respects the other's lane.",
                    "CD": "Single-rotation CDs cannot design a cross-clerkship academic plan."
                },
                "policy": "Per the Pre-Clerkship and Clerkship Academic Progress Policies, OAA designs individualized academic plans, with OSA coordinating on non-academic factors.",
            },
            {
                "situation": "Devon finishes Internal Medicine with a passing shelf and a solid clinical evaluation. He has two years of training ahead of him. OSA wants to make sure he is not standing alone again.",
                "question": "Who anchors the longitudinal relationship across the rest of clerkships and Phase 3?",
                "options": {
                    "LC": "Learning Community advisor — longitudinal mentorship through the remaining curriculum, with OSA holding the file and FIN keeping H$RD MD active",
                    "APSC": "APSC monitors him for two years",
                    "OSA": "OSA does monthly check-ins indefinitely",
                    "CD": "His next clerkship director carries the handoff",
                },
                "correct": "LC",
                "why_right": "LC advisors are the longitudinal layer of Marshall's student support architecture. They check in informally, notice trends, and warm-hand-off when needed. OSA holds the file in the background. FIN keeps H$RD MD active. CDs change rotation by rotation; the LC stays.",
                "why_wrong": {
                    "APSC": "APSC monitors disciplinary outcomes, not wellness recovery.",
                    "OSA": "OSA is the safety net, not the everyday relationship.",
                    "CD": "CDs are rotation-bound."
                },
                "policy": "Learning Communities provide longitudinal faculty mentorship across all four years of the curriculum.",
            },
            {
                "situation": "Devon is applying for residency. He is preparing to talk to a program about his first-shelf score and asks OSA how the year will appear in his MSPE.",
                "question": "What is the accurate answer?",
                "options": {
                    "OSA": "Wellness engagement, emergency aid, and H$RD MD enrollment are not part of the MSPE; the MSPE reflects his strong recovery and clinical evaluations, and OSA — as the MSPE author — frames the academic trajectory honestly without disclosing financial hardship or mental health care",
                    "APSC": "All financial hardship is reported in the MSPE",
                    "DEAN": "The Dean writes a separate disclosure letter",
                    "WHMD": "WHMD engagement appears in the MSPE"
                },
                "correct": "OSA",
                "why_right": "Per AAMC MSPE guidance, the MSPE reflects academic and professional performance. Wellness engagement, emergency aid, and counseling are not disclosed. OSA, as the MSPE author, frames Devon's academic trajectory — including the early-shelf dip and strong subsequent performance — without disclosing the underlying hardship.",
                "why_wrong": {
                    "APSC": "Financial hardship is not reportable content under AAMC MSPE guidelines.",
                    "DEAN": "Dean's letters are reserved for non-routine adverse content; this is not that.",
                    "WHMD": "WHMD engagement is confidential and not in the MSPE."
                },
                "policy": "Per AAMC MSPE guidelines, only academic and professional performance content appears; wellness engagement, emergency aid, and counseling are confidential.",
            },
        ],
    },
    # ------------------------------------------------------------------
    # NEW SCENARIO 8: Pregnancy + postpartum complications during the curriculum
    # ------------------------------------------------------------------
    {
        "id": "maya",
        "name": "Maya T.",
        "level": "Academic Level 1 → 2 · M1/M2 · Pregnancy, Delivery, Postpartum",
        "tagline": "M1 who becomes pregnant in NN, delivers during CPR, and develops postpartum depression in early M2 — testing every pregnancy, lactation, technical-standards, and leave pathway in sequence.",
        "background": "Maya is in the second half of M1. She becomes pregnant late in NN, delivers during CPR (early M2 fall), plans to continue with modified pacing, and develops postpartum depression that intensifies six weeks postpartum. She is partnered but lives far from family. This scenario tests the full pregnancy-through-postpartum policy landscape — including the Title IX pathway that leadership often misses.",
        "steps": [
            {
                "situation": "Maya discovers she is pregnant. She wants to continue her training. She is unsure whether to tell OSA first or whether this is a Title IX matter.",
                "question": "Where does the pregnancy-accommodations pathway begin at JCESOM?",
                "options": {
                    "OSA": "OSA owns the confidential intake and coordinates with the Title IX Coordinator for pregnancy accommodations under Title IX",
                    "TIX": "Title IX Coordinator directly — without OSA involvement",
                    "CD": "Her current course director",
                    "WHMD": "WHMD only — pregnancy is a wellness matter"
                },
                "correct": "OSA",
                "why_right": "Pregnancy accommodations are protected under Title IX, but the practical pathway at JCESOM starts with OSA: they triage the situation, coordinate with the Title IX Coordinator for protected accommodations, and orchestrate academic and clinical adjustments. OSA does not displace Title IX — they connect the student to it.",
                "why_wrong": {
                    "TIX": "Title IX is essential for protections but is not equipped to design Maya's individualized academic plan. OSA partners with TIX.",
                    "CD": "CDs implement accommodations but do not own the intake.",
                    "WHMD": "WHMD is part of the support stack but does not own the accommodation pathway."
                },
                "policy": "Pregnancy is a protected status under Title IX; OSA coordinates accommodations with the Title IX Coordinator and OAA.",
            },
            {
                "situation": "Maya wants to continue and finish Phase 1 on time. Her due date falls early in CPR. She'll need flexibility on attendance and assessments for several weeks.",
                "question": "Who designs the modified academic plan?",
                "options": {
                    "OAA": "OAA designs the individualized academic plan with input from CPR's course director, OSA, and the Title IX Coordinator",
                    "APSC": "APSC must approve any deviation from standard pacing",
                    "CD": "The CPR course director decides alone",
                    "DEAN": "The Dean rewrites her schedule"
                },
                "correct": "OAA",
                "why_right": "Individualized academic plans are OAA's lane. For pregnancy-related modifications, OAA coordinates with the CPR course director (for assessment and attendance specifics), OSA (for the overall student-status picture), and Title IX (for protected accommodations).",
                "why_wrong": {
                    "APSC": "APSC reviews deficiencies; pregnancy accommodations are not a deficiency.",
                    "CD": "Single-course decisions miss the cross-curricular picture OAA holds.",
                    "DEAN": "The Dean approves the structural pathway; OAA implements."
                },
                "policy": "OAA owns individualized academic plans under the Pre-Clerkship Academic Progress Policy, in coordination with OSA and Title IX for protected categories.",
            },
            {
                "situation": "Maya is preparing to return six weeks after delivery. She will need lactation accommodations on campus and during long lecture blocks.",
                "question": "Who arranges lactation accommodations?",
                "options": {
                    "OSA": "OSA, with the Title IX Coordinator and Facilities, identifies lactation space and integrates breaks into the schedule",
                    "CD": "Each individual course director arranges per session",
                    "WHMD": "WHMD owns lactation logistics",
                    "DEAN": "The Dean's office has a designated lactation suite"
                },
                "correct": "OSA",
                "why_right": "Lactation accommodations are coordinated by OSA in partnership with the Title IX Coordinator and Facilities — they identify space and integrate breaks across course schedules. Course directors implement the per-session piece but don't have visibility across the curriculum.",
                "why_wrong": {
                    "CD": "Course-by-course coordination leaves gaps; the protection is cross-curricular.",
                    "WHMD": "WHMD provides wellness support, not facilities coordination.",
                    "DEAN": "The Dean does not run space allocation."
                },
                "policy": "Lactation accommodations are protected under Title IX and coordinated by OSA with Title IX and Facilities.",
            },
            {
                "situation": "Six weeks back, Maya is struggling with postpartum depression. She is missing small groups, crying in clinic, and not sleeping.",
                "question": "Where does the postpartum mental health support pathway live?",
                "options": {
                    "WHMD": "WellHerdMD — confidential mental health support, coordinated with OSA on academic implications",
                    "APSC": "APSC, since attendance is being affected",
                    "TIX": "Title IX, since this stems from pregnancy",
                    "DEAN": "The Dean's office, for a personal touch"
                },
                "correct": "WHMD",
                "why_right": "WHMD is the confidential mental health pathway. They engage Maya clinically and, with her consent, OSA coordinates any academic implications. Title IX protections remain in the background but the active care is WHMD.",
                "why_wrong": {
                    "APSC": "Missing small groups in postpartum recovery is a wellness signal, not professionalism.",
                    "TIX": "Title IX gives the protected status; it does not deliver clinical care.",
                    "DEAN": "Dean involvement is unnecessary at this stage."
                },
                "policy": "WellHerdMD provides confidential mental health care; coordination with OSA occurs with student consent absent imminent safety risk.",
            },
            {
                "situation": "WHMD and Maya decide together that a short personal LOA — six weeks — would let her stabilize and return strong. Maya wants to take it.",
                "question": "Who approves the personal LOA?",
                "options": {
                    "OSA": "The Dean of Student Affairs approves the personal LOA with APSC notification and OAA academic-plan coordination",
                    "WHMD": "WHMD approves medical-related leaves",
                    "APSC": "APSC votes on every leave",
                    "DEAN": "The School Dean approves all leaves personally"
                },
                "correct": "OSA",
                "why_right": "Personal LOAs are approved by the Dean of Student Affairs. APSC is notified, not asked to vote. OAA coordinates the academic plan and re-entry timeline.",
                "why_wrong": {
                    "WHMD": "WHMD recommends; OSA approves.",
                    "APSC": "APSC is notified, not the decision-maker on personal LOAs.",
                    "DEAN": "The School Dean is informed but doesn't approve routine personal LOAs."
                },
                "policy": "Personal LOA approval rests with the Dean of OSA, with APSC notification and OAA academic-plan coordination.",
            },
            {
                "situation": "Maya returns six weeks later. She's been re-evaluated by WHMD and feels stable.",
                "question": "What must happen before Maya resumes the curriculum?",
                "options": {
                    "OSA": "Technical Standards re-attestation per the policy applicable post-LOA, plus updated CastleBranch and immunizations",
                    "WHMD": "A WHMD clearance letter",
                    "APSC": "Mandatory APSC hearing",
                    "TIX": "Title IX re-approval of accommodations"
                },
                "correct": "OSA",
                "why_right": "Per the Technical Standards policy, students re-attest at acceptance, matriculation, M2, M3, M4, and upon return from any LOA. CastleBranch and immunization records are also updated. OSA coordinates.",
                "why_wrong": {
                    "WHMD": "WHMD doesn't gate-keep re-entry; the wellness/academic firewall holds.",
                    "APSC": "APSC is not triggered by routine personal LOA return.",
                    "TIX": "Title IX accommodations remain in force; they don't require re-approval at return."
                },
                "policy": "Technical Standards re-attestation is required post-LOA per the Technical Standards policy.",
            },
            {
                "situation": "Maya is now a healthy mother and a strong M2. She asks how the pregnancy and LOA will appear in her MSPE.",
                "question": "What appears in the MSPE?",
                "options": {
                    "OSA": "A leave of absence is acknowledged in the MSPE; reasons for personal LOAs are not detailed; pregnancy and postpartum care are not disclosed",
                    "APSC": "The LOA is flagged with reason",
                    "DEAN": "A Dean's note describes the circumstances",
                    "WHMD": "WHMD engagement is summarized"
                },
                "correct": "OSA",
                "why_right": "Per AAMC MSPE guidance, a leave of absence is acknowledged; the reason for a personal LOA is not detailed. Pregnancy and postpartum care are confidential. The MSPE will reflect Maya's strong academic record and continued progress.",
                "why_wrong": {
                    "APSC": "There is no policy that requires flagging the reason for a personal LOA in the MSPE.",
                    "DEAN": "Dean notes are reserved for non-routine content; routine LOAs don't qualify.",
                    "WHMD": "WHMD engagement is confidential and not in the MSPE."
                },
                "policy": "Per AAMC MSPE guidelines, leaves of absence are noted; personal LOA reasons are not detailed.",
            },
        ],
    },
    # ------------------------------------------------------------------
    # NEW SCENARIO 9: Substance use disorder — surfaces on clerkship
    # ------------------------------------------------------------------
    {
        "id": "tyler",
        "name": "Tyler M.",
        "level": "Academic Level 3 · M3 · Substance Use Disorder",
        "tagline": "M3 on clerkship; clerkship director smells alcohol on him during morning rounds. This tests the wellness/safety/policy intersection that leadership most often gets wrong.",
        "background": "Tyler is on his Surgery clerkship. During morning rounds, the clerkship director smells alcohol on his breath. He is pulled aside. He has been drinking heavily for several months; M3 stress accelerated it. This scenario tests the substance-use-disorder pathway — which combines immediate safety, confidentiality, and a long-term recovery-monitoring relationship that most leaders aren't familiar with.",
        "steps": [
            {
                "situation": "The clerkship director removes Tyler from rounds and patient care immediately. What is the very next call?",
                "question": "Who does the CD call first?",
                "options": {
                    "OSA": "The Dean of Student Affairs (OSA) — immediate fitness-for-duty + wellness coordination",
                    "APSC": "APSC, to start a professionalism case",
                    "WVMPHP": "WV Medical Professionals Health Program directly",
                    "DEAN": "The School Dean"
                },
                "correct": "OSA",
                "why_right": "OSA is the immediate call. They coordinate the fitness-for-duty assessment, refer to WV Medical Professionals Health Program, and orchestrate the wellness pathway in parallel with any academic decisions. Going straight to APSC routes a treatable disorder into discipline; going straight to WVMPHP skips the JCESOM coordination layer.",
                "why_wrong": {
                    "APSC": "Substance use disorder is not handled at intake as a professionalism case; it's handled as a health condition.",
                    "WVMPHP": "WVMPHP is essential, but OSA owns the referral relationship and the JCESOM-side coordination.",
                    "DEAN": "The Dean is informed; the operational call is OSA."
                },
                "policy": "OSA coordinates fitness-for-duty assessment and substance-use referrals through WV Medical Professionals Health Program in alignment with WV practice.",
            },
            {
                "situation": "OSA refers Tyler to the WV Medical Professionals Health Program (WVMPHP). Tyler is scared this means his career is over.",
                "question": "What does the WVMPHP pathway actually offer?",
                "options": {
                    "WVMPHP": "Confidential, monitored treatment with structured return-to-training protocols; designed to preserve careers, not end them",
                    "APSC": "A required professionalism file",
                    "DEAN": "Mandatory withdrawal from JCESOM",
                    "OSA": "Permanent flag on his MSPE"
                },
                "correct": "WVMPHP",
                "why_right": "WVMPHP (and analogous state Physician Health Programs) exist precisely to preserve careers by providing confidential, monitored treatment with structured re-entry. They partner with OSA on the JCESOM-side coordination.",
                "why_wrong": {
                    "APSC": "WVMPHP is not an APSC pathway.",
                    "DEAN": "Withdrawal is not the default; treatment is.",
                    "OSA": "MSPE flagging is not automatic; it depends on outcome and AAMC reportability rules, decided by OSA case by case."
                },
                "policy": "WV Medical Professionals Health Program provides confidential monitored treatment for trainees and physicians.",
            },
            {
                "situation": "Tyler needs to step away from clerkship to enter treatment. Which kind of leave?",
                "question": "Medical or personal LOA?",
                "options": {
                    "OAA": "Medical LOA — coordinated by OAA and OSA, with WVMPHP as the treatment partner",
                    "OSA": "Personal LOA, to keep the reason private",
                    "APSC": "APSC-mandated leave",
                    "DEAN": "Dean's leave"
                },
                "correct": "OAA",
                "why_right": "A medical LOA is the structurally correct vehicle because the leave is for treatment of a medical condition (SUD). OAA coordinates the academic plan; OSA coordinates wellness and WVMPHP; the reason — 'medical' — is recognized in policy without further specification.",
                "why_wrong": {
                    "OSA": "Personal LOAs are for non-medical reasons. Medical LOAs are the structurally correct vehicle for SUD treatment.",
                    "APSC": "APSC does not mandate leaves.",
                    "DEAN": "There is no separate Dean's leave category."
                },
                "policy": "Medical LOA is the structurally appropriate vehicle for documented health conditions requiring treatment.",
            },
            {
                "situation": "Tyler enters treatment. WVMPHP monitors compliance and reports to OSA per its protocol. The clerkship director is asking what to tell the team.",
                "question": "What does OSA tell the clerkship director?",
                "options": {
                    "OSA": "Tyler is on a medical LOA; coordinate any future scheduling through OSA; no clinical concerns to convey to the team",
                    "WVMPHP": "Full WVMPHP treatment plan and compliance status",
                    "APSC": "Refer the CD to APSC for case access",
                    "DEAN": "Have the CD escalate to the Dean for briefing"
                },
                "correct": "OSA",
                "why_right": "OSA shares the minimum necessary: 'medical LOA, coordinate through OSA.' The treatment plan, the substance, the compliance reports — none of that goes to the CD. This protects Tyler's recovery and respects the confidentiality of health information.",
                "why_wrong": {
                    "WVMPHP": "Treatment detail is confidential; the CD does not need it.",
                    "APSC": "APSC has no role in the medical LOA pathway.",
                    "DEAN": "Dean escalation is not necessary; the framework handles it."
                },
                "policy": "OSA shares minimum necessary information with academic faculty during medical LOAs.",
            },
            {
                "situation": "Tyler is in active recovery after 90 days. WVMPHP signs off on a re-entry plan. He is medically cleared.",
                "question": "What does JCESOM require for re-entry to clerkship?",
                "options": {
                    "OSA": "Technical Standards re-attestation, CastleBranch update, immunizations, and a coordinated re-entry plan with the next clerkship director (briefed minimally)",
                    "APSC": "An APSC hearing before re-entry",
                    "WVMPHP": "WVMPHP completion alone, no JCESOM steps",
                    "DEAN": "Dean approval of re-entry case by case"
                },
                "correct": "OSA",
                "why_right": "Re-entry from any LOA — including medical LOA for SUD — follows the standard Technical Standards re-attestation + CastleBranch + immunization update pathway, plus OSA's minimal briefing of the next CD. WVMPHP continues to monitor in the background.",
                "why_wrong": {
                    "APSC": "Medical LOA return does not trigger APSC.",
                    "WVMPHP": "WVMPHP clearance is necessary but not sufficient — JCESOM's re-entry steps still apply.",
                    "DEAN": "Routine medical LOA re-entry does not require Dean case review."
                },
                "policy": "Technical Standards re-attestation is required post-LOA per the Technical Standards policy.",
            },
            {
                "situation": "Tyler completes M3 and M4 with strong evaluations. He matches. He asks OSA whether residency programs will see this.",
                "question": "What does OSA tell him about MSPE disclosure?",
                "options": {
                    "OSA": "A leave is acknowledged in the MSPE; the underlying medical reason is not detailed; ongoing recovery monitoring is between Tyler and his future state PHP at residency, not the MSPE",
                    "WVMPHP": "WVMPHP automatically reports to all residency programs",
                    "DEAN": "The Dean writes a substance-use disclosure letter",
                    "APSC": "APSC adds a flag to the academic file"
                },
                "correct": "OSA",
                "why_right": "Per AAMC MSPE guidance, the leave is acknowledged but the medical reason is not detailed. Tyler's ongoing recovery monitoring at residency is handled through his future state's PHP — that's a Tyler-and-his-employer matter, not an MSPE matter.",
                "why_wrong": {
                    "WVMPHP": "WVMPHP doesn't auto-report to residency programs.",
                    "DEAN": "The Dean does not write disclosure letters for routine medical LOAs.",
                    "APSC": "APSC was not the pathway; there is no APSC flag."
                },
                "policy": "Per AAMC MSPE guidelines, leaves are acknowledged; medical reasons are not detailed.",
            },
        ],
    },
]

SCENARIO_BY_ID = {s["id"]: s for s in SCENARIOS}

# =============================================================================
# SESSION STATE
# =============================================================================
def init_state():
    defaults = {
        "active_scenario": None,        # str id or None (home)
        "step_index": 0,                # int
        "answers": {},                  # {(scenario_id, step_idx): selected_tag}
        "submitted": {},                # {(scenario_id, step_idx): bool}
        "session_id": str(uuid.uuid4()),
        "participant_name": "",
        "saved_scenarios": set(),       # which scenarios have been persisted to DB
        # option_orders cache:  {(scenario_id, step_idx): [tag1, tag2, ...]}
        # built once per step so the radio order is stable across reruns.
        "option_orders": {},
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# Stable shuffled option order for a given step
def get_option_order(scenario_id: str, step_idx: int, option_tags: list) -> list:
    key = (scenario_id, step_idx)
    if key not in st.session_state["option_orders"]:
        # Seed combines participant session + scenario + step so a given
        # participant always sees the same order for the same step (but
        # different participants get different orders, and different steps
        # within a scenario get independent shuffles).
        seed_str = f"{st.session_state['session_id']}|{scenario_id}|{step_idx}"
        rng = random.Random(seed_str)
        shuffled = list(option_tags)
        rng.shuffle(shuffled)
        st.session_state["option_orders"][key] = shuffled
    return st.session_state["option_orders"][key]

# =============================================================================
# HELPERS
# =============================================================================
def score_for_scenario(sid: str):
    sc = SCENARIO_BY_ID[sid]
    correct = 0
    total_submitted = 0
    for i, step in enumerate(sc["steps"]):
        key = (sid, i)
        if st.session_state["submitted"].get(key):
            total_submitted += 1
            if st.session_state["answers"].get(key) == step["correct"]:
                correct += 1
    return correct, total_submitted, len(sc["steps"])

def overall_score():
    total_correct = 0
    total_steps = 0
    for sid in SCENARIO_BY_ID:
        c, _, n = score_for_scenario(sid)
        total_correct += c
        total_steps += n
    return total_correct, total_steps

def reset_scenario(sid: str):
    keys_to_clear = [k for k in st.session_state["answers"] if k[0] == sid]
    for k in keys_to_clear:
        st.session_state["answers"].pop(k, None)
        st.session_state["submitted"].pop(k, None)
    # Clear shuffled option cache for this scenario so the retry gets a fresh shuffle
    order_keys = [k for k in st.session_state["option_orders"] if k[0] == sid]
    for k in order_keys:
        st.session_state["option_orders"].pop(k, None)
    # Allow a fresh DB save when the user re-reaches debrief
    st.session_state["saved_scenarios"].discard((sid,))
    st.session_state["step_index"] = 0

# =============================================================================
# HEADER
# =============================================================================
_logo_html = (
    f'<img src="{LOGO_DATA_URI}" alt="Marshall University Joan C. Edwards School of Medicine" />'
    if LOGO_DATA_URI else '<span class="m-letter">M</span>'
)

st.markdown(f"""
<div class="app-banner">
  <div class="logo-mark">
    {_logo_html}
  </div>
  <div class="banner-text">
    <h1><span class="accent">Student Journey</span> <em>Decision Lab</em></h1>
    <div class="source">A leadership policy refresher built around nine real-world student scenarios · Source: JCESOM Student Handbook (July 2024)</div>
  </div>
</div>
""", unsafe_allow_html=True)

# =============================================================================
# FACILITATOR VIEW  — reached by appending ?facilitator=1 to the URL
# Password-protected, shows every participant's scores with CSV download.
# =============================================================================
_qp = st.query_params
if _qp.get("facilitator") == "1" or _qp.get("admin") == "1":
    st.markdown("### Facilitator · Participant scores")

    if "facilitator_authed" not in st.session_state:
        st.session_state["facilitator_authed"] = False

    if not st.session_state["facilitator_authed"]:
        pwd = st.text_input("Facilitator password", type="password", key="facilitator_pwd")
        col_a, col_b = st.columns([1, 5])
        with col_a:
            if st.button("Sign in", key="facilitator_signin"):
                if pwd == FACILITATOR_PASSWORD:
                    st.session_state["facilitator_authed"] = True
                    st.rerun()
                else:
                    st.error("Incorrect password.")
        with col_b:
            st.caption("Facilitator access is restricted. Contact the program lead for the password.")
        st.stop()

    # Authenticated facilitator view
    sessions, attempts, avg_pct = fetch_overall_stats()
    c1, c2, c3 = st.columns(3)
    c1.metric("Unique participants", sessions)
    c2.metric("Scenarios completed", attempts)
    c3.metric("Average score", f"{avg_pct:.0f}%" if attempts else "—")

    rows = fetch_all_results()
    if not rows:
        st.info("No participant data recorded yet. Once staff complete scenarios, results will appear here.")
    else:
        # Build a list of dicts for display + CSV
        records = []
        for name, started, sc_name, correct, total, completed, sid in rows:
            pct = round(100 * correct / total) if total else 0
            records.append({
                "Participant": name or "Anonymous",
                "Scenario": sc_name,
                "Score": f"{correct}/{total}",
                "Percent": f"{pct}%",
                "Completed": completed.replace("T", " ").split(".")[0] + " UTC",
                "Session": sid[:8],
            })

        # Streamlit-rendered table
        st.markdown("#### All results (most recent first)")
        st.dataframe(records, use_container_width=True, hide_index=True)

        # CSV download
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=["Participant", "Scenario", "Score", "Percent", "Completed", "Session"])
        writer.writeheader()
        for r in records:
            writer.writerow(r)
        st.download_button(
            "Download CSV",
            data=buf.getvalue(),
            file_name=f"jcesom_decision_lab_scores_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
        )

    st.markdown("---")
    if st.button("← Back to the Decision Lab"):
        st.query_params.clear()
        st.rerun()
    if st.button("Sign out of facilitator mode"):
        st.session_state["facilitator_authed"] = False
        st.rerun()

    st.stop()

# =============================================================================
# SIDEBAR — Scenario picker + score
# =============================================================================
with st.sidebar:
    st.markdown("### Scenarios")
    st.caption("Pick a case. Each step asks you to identify who is responsible.")

    if st.button("← Home / All Scenarios", use_container_width=True):
        st.session_state["active_scenario"] = None
        st.session_state["step_index"] = 0
        st.rerun()

    st.markdown("---")

    for sc in SCENARIOS:
        c, submitted_count, total = score_for_scenario(sc["id"])
        progress_label = f"{submitted_count}/{total}"
        emoji = "✅" if submitted_count == total else ("◧" if submitted_count > 0 else "○")
        btn_label = f"{emoji}  {sc['name']}  ·  {progress_label}"
        if st.button(btn_label, key=f"pick_{sc['id']}", use_container_width=True):
            st.session_state["active_scenario"] = sc["id"]
            st.session_state["step_index"] = 0
            st.rerun()

    st.markdown("---")
    st.markdown("### Overall Score")
    total_c, total_n = overall_score()
    if total_n > 0:
        pct = round(100 * total_c / total_n)
        st.metric("Correct decisions", f"{total_c}/{total_n}", f"{pct}%")
    else:
        st.caption("No questions answered yet.")

    st.markdown("---")
    with st.expander("Stakeholder legend"):
        for tag, (name, role) in STAKEHOLDERS.items():
            st.markdown(f"**{tag}** — {name}  \n<span style='font-size:0.8rem; color:{GOLD_LIGHT}'>{role}</span>", unsafe_allow_html=True)

# =============================================================================
# HOME VIEW (no scenario picked)
# =============================================================================
if st.session_state["active_scenario"] is None:
    # Optional participant name capture
    with st.container():
        cn1, cn2 = st.columns([2, 3])
        with cn1:
            name_val = st.text_input(
                "Your name or nickname (optional)",
                value=st.session_state.get("participant_name", ""),
                placeholder="e.g. Dr. Smith — or leave blank to stay anonymous",
                key="participant_name_input",
            )
            if name_val != st.session_state.get("participant_name", ""):
                st.session_state["participant_name"] = name_val
        with cn2:
            st.caption("This is used to track your scores across the scenarios you complete in this session. Leave blank to participate anonymously.")

    st.markdown("### Choose a scenario")
    st.markdown("Each scenario walks through a real decision sequence — admissions, matriculation, clinical training, leave, return, MSPE, residency. At every step you'll choose the office or person responsible, then see whether your answer aligns with policy and why.")

    col1, col2 = st.columns(2)
    for idx, sc in enumerate(SCENARIOS):
        col = col1 if idx % 2 == 0 else col2
        with col:
            st.markdown(f"""
            <div class="scenario-card">
              <div class="meta">{sc['level']}</div>
              <div class="name">{sc['name']}</div>
              <div class="tagline">{sc['tagline']}</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button(f"Enter scenario →", key=f"enter_{sc['id']}", use_container_width=True):
                st.session_state["active_scenario"] = sc["id"]
                st.session_state["step_index"] = 0
                st.rerun()

# =============================================================================
# SCENARIO VIEW
# =============================================================================
else:
    sc = SCENARIO_BY_ID[st.session_state["active_scenario"]]
    step_idx = st.session_state["step_index"]
    total_steps = len(sc["steps"])

    # Scenario header
    st.markdown(f"""
    <div class="scenario-card" style="border-left-color: {FOREST};">
      <div class="meta">{sc['level']}</div>
      <div class="name">{sc['name']}</div>
      <div class="tagline">{sc['background']}</div>
    </div>
    """, unsafe_allow_html=True)

    # Progress bar
    submitted_count = sum(
        1 for i in range(total_steps)
        if st.session_state["submitted"].get((sc["id"], i))
    )
    st.progress(submitted_count / total_steps, text=f"Progress: {submitted_count} of {total_steps} decisions made")

    if step_idx < total_steps:
        # Current step
        step = sc["steps"][step_idx]
        step_key = (sc["id"], step_idx)

        st.markdown(f"""
        <div class="step-header">
          <div class="step-num">Decision {step_idx + 1} of {total_steps}</div>
          <div class="step-title">{step['question']}</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="situation-box">
          <div class="label">Situation</div>
          <div class="text">{step['situation']}</div>
        </div>
        """, unsafe_allow_html=True)

        # Answer choices
        submitted = st.session_state["submitted"].get(step_key, False)
        # Per-participant shuffled order — stable across reruns for one user,
        # but different users get different orderings.
        base_tags = list(step["options"].keys())
        option_tags = get_option_order(sc["id"], step_idx, base_tags)
        option_labels = [f"{tag} — {step['options'][tag]}" for tag in option_tags]

        if not submitted:
            # Show radio + submit
            prior = st.session_state["answers"].get(step_key)
            default_index = option_tags.index(prior) if prior in option_tags else 0
            chosen_label = st.radio(
                "Who is responsible / what is the right move?",
                option_labels,
                index=default_index,
                key=f"radio_{sc['id']}_{step_idx}",
            )
            chosen_tag = option_tags[option_labels.index(chosen_label)]

            col_a, col_b, col_c = st.columns([1, 1, 4])
            with col_a:
                if st.button("Submit answer", key=f"submit_{sc['id']}_{step_idx}"):
                    st.session_state["answers"][step_key] = chosen_tag
                    st.session_state["submitted"][step_key] = True
                    st.rerun()
            with col_b:
                if step_idx > 0 and st.button("← Back", key=f"back_unsub_{sc['id']}_{step_idx}"):
                    st.session_state["step_index"] -= 1
                    st.rerun()

        else:
            # Show feedback
            chosen_tag = st.session_state["answers"].get(step_key)
            is_correct = chosen_tag == step["correct"]

            # Show what was chosen
            chosen_label = step["options"].get(chosen_tag, chosen_tag)
            correct_label = step["options"].get(step["correct"], step["correct"])

            if is_correct:
                st.markdown(f"""
                <div class="feedback-correct">
                  <div class="feedback-title">✓ Correct — {step['correct']} · {correct_label}</div>
                  <div class="feedback-body">{step['why_right']}</div>
                  <div class="policy-box">
                    <div class="policy-label">Policy basis</div>
                    <div class="policy-text">{step['policy']}</div>
                  </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="feedback-incorrect">
                  <div class="feedback-title">Not quite — you chose {chosen_tag}. The policy-aligned answer is {step['correct']} · {correct_label}.</div>
                  <div class="feedback-body"><strong>Why {step['correct']} is right:</strong> {step['why_right']}</div>
                  <div class="feedback-body" style="margin-top:0.6rem;"><strong>Why {chosen_tag} is not the right call here:</strong> {step['why_wrong'].get(chosen_tag, '—')}</div>
                  <div class="policy-box">
                    <div class="policy-label">Policy basis</div>
                    <div class="policy-text">{step['policy']}</div>
                  </div>
                </div>
                """, unsafe_allow_html=True)

            # Navigation
            col_a, col_b, col_c, col_d = st.columns([1, 1, 1, 3])
            with col_a:
                if step_idx > 0 and st.button("← Previous", key=f"prev_{sc['id']}_{step_idx}"):
                    st.session_state["step_index"] -= 1
                    st.rerun()
            with col_b:
                if step_idx < total_steps - 1:
                    if st.button("Next →", key=f"next_{sc['id']}_{step_idx}", type="primary"):
                        st.session_state["step_index"] += 1
                        st.rerun()
                else:
                    if st.button("See debrief", key=f"debrief_{sc['id']}", type="primary"):
                        st.session_state["step_index"] = total_steps  # virtual end-screen marker
                        st.rerun()
            with col_c:
                if st.button("Reset this scenario", key=f"reset_{sc['id']}_{step_idx}"):
                    reset_scenario(sc["id"])
                    st.rerun()

    # End-of-scenario debrief
    if step_idx >= total_steps:
        c, sub_n, n = score_for_scenario(sc["id"])
        pct = round(100 * c / n) if n else 0
        if pct >= 80:
            band_class, band_text = "score-high", "Policy-aligned"
        elif pct >= 60:
            band_class, band_text = "score-mid", "Mostly aligned"
        else:
            band_class, band_text = "score-low", "Refresher recommended"

        # Persist score (idempotent — only on first arrival at debrief)
        save_key = (sc["id"],)
        if save_key not in st.session_state["saved_scenarios"]:
            participant_label = st.session_state.get("participant_name", "") or "Anonymous"
            save_participant(st.session_state["session_id"], participant_label)
            save_scenario_result(
                st.session_state["session_id"], sc["id"], sc["name"], c, n,
            )
            st.session_state["saved_scenarios"].add(save_key)

        st.markdown(f"""
        <div class="summary-card">
          <div style="font-family:'Fraunces',serif; font-style:italic; font-size:1.8rem; color:{INK};">Scenario debrief · <em>{sc['name']}</em></div>
          <div style="margin-top:0.5rem;"><span class="scoreband {band_class}">{band_text}</span> &nbsp; {c} of {n} decisions aligned with policy ({pct}%)</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("#### Decision-by-decision review")
        for i, step in enumerate(sc["steps"]):
            key = (sc["id"], i)
            chosen = st.session_state["answers"].get(key, "—")
            correct = step["correct"]
            mark = "✓" if chosen == correct else "✗"
            color = FOREST if chosen == correct else RUST
            st.markdown(
                f"<div style='padding:0.6rem 0.9rem; margin-bottom:0.4rem; "
                f"background:white; border-left:4px solid {color}; border-radius:3px;'>"
                f"<strong style='color:{color};'>{mark}</strong> &nbsp; "
                f"<strong>Decision {i+1}:</strong> {step['question']} &nbsp; "
                f"<span style='color:{SLATE};'>(You: {chosen} · Correct: {correct})</span>"
                f"</div>",
                unsafe_allow_html=True
            )

        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("Retry this scenario", use_container_width=True):
                reset_scenario(sc["id"])
                st.rerun()
        with col_b:
            if st.button("Back to all scenarios", use_container_width=True):
                st.session_state["active_scenario"] = None
                st.session_state["step_index"] = 0
                st.rerun()
