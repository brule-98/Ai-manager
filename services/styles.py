GLOBAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;1,9..40,400&family=DM+Serif+Display:ital@0;1&family=JetBrains+Mono:wght@400;500&display=swap');

/* ── CSS VARIABLES ─────────────────────────────────────────────── */
:root {
    --navy-900: #050E1F;
    --navy-800: #0A1628;
    --navy-700: #0F2044;
    --navy-600: #1A3A7A;
    --navy-500: #2952A3;
    --navy-400: #4A72C4;
    --navy-100: #EEF4FF;
    --blue-500: #2563EB;
    --green-600: #059669;
    --green-100: #D1FAE5;
    --red-600:   #DC2626;
    --red-100:   #FEE2E2;
    --amber-500: #D97706;
    --amber-100: #FEF3C7;
    --purple-600: #7C3AED;
    --gray-900: #111827;
    --gray-700: #374151;
    --gray-500: #6B7280;
    --gray-300: #D1D5DB;
    --gray-100: #F3F4F6;
    --white:    #FFFFFF;
    --bg:       #F0F2F7;
    --card-shadow: 0 1px 3px rgba(0,0,0,0.08), 0 4px 16px rgba(0,0,0,0.04);
    --card-shadow-hover: 0 4px 12px rgba(0,0,0,0.12), 0 8px 32px rgba(0,0,0,0.06);
}

/* ── RESET & BASE ──────────────────────────────────────────────── */
html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif !important;
    background-color: var(--bg) !important;
    color: var(--gray-900);
}
.block-container {
    padding: 0 1.5rem 2rem 1.5rem !important;
    max-width: 100% !important;
}
#MainMenu, footer, header { visibility: hidden !important; }

/* ── SCROLLBAR ─────────────────────────────────────────────────── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--gray-100); }
::-webkit-scrollbar-thumb { background: var(--navy-400); border-radius: 3px; }

/* ── HEADER ────────────────────────────────────────────────────── */
.app-header {
    background: linear-gradient(135deg, var(--navy-900) 0%, var(--navy-700) 60%, var(--navy-600) 100%);
    padding: 0.9rem 2rem;
    margin: 0 -1.5rem 1.5rem -1.5rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    border-bottom: 1px solid rgba(255,255,255,0.06);
    position: sticky;
    top: 0;
    z-index: 100;
}
.app-header-brand { display: flex; flex-direction: column; }
.app-header-brand h1 {
    font-family: 'DM Serif Display', serif !important;
    font-size: 1.35rem;
    color: white !important;
    margin: 0;
    letter-spacing: 0.3px;
}
.app-header-brand .tagline {
    font-size: 0.68rem;
    color: #6B8EC9;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    margin: 0;
}
.app-header-right { display: flex; align-items: center; gap: 12px; }
.header-badge {
    background: rgba(255,255,255,0.09);
    border: 1px solid rgba(255,255,255,0.14);
    border-radius: 6px;
    padding: 5px 14px;
    font-size: 0.73rem;
    color: rgba(255,255,255,0.85);
    font-weight: 500;
}
.header-badge-alert {
    background: rgba(220,38,38,0.2);
    border-color: rgba(220,38,38,0.4);
    color: #FCA5A5;
    cursor: pointer;
    transition: all 0.2s;
}
.header-badge-alert:hover { background: rgba(220,38,38,0.3); }

/* ── SIDEBAR ───────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: var(--navy-800) !important;
    border-right: 1px solid rgba(255,255,255,0.05) !important;
}
[data-testid="stSidebar"] > div { padding-top: 1.2rem !important; }
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stCaption { color: #8BA3CC !important; }
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] h4 { color: #E2EBF6 !important; font-size: 0.7rem !important; text-transform: uppercase; letter-spacing: 1.5px; }

.nav-btn button {
    background: transparent !important;
    color: #8BA3CC !important;
    border: none !important;
    border-radius: 8px !important;
    font-size: 0.84rem !important;
    font-weight: 400 !important;
    text-align: left !important;
    padding: 9px 14px !important;
    transition: all 0.15s !important;
}
.nav-btn button:hover {
    background: rgba(255,255,255,0.07) !important;
    color: white !important;
    transform: none !important;
    box-shadow: none !important;
}
.nav-btn-active button {
    background: rgba(37,99,235,0.18) !important;
    color: #93C5FD !important;
    border-left: 3px solid #2563EB !important;
    border-radius: 0 8px 8px 0 !important;
    font-weight: 500 !important;
}

/* ── SITE SELECTOR ─────────────────────────────────────────────── */
.site-selector-wrap {
    background: rgba(255,255,255,0.05);
    border-radius: 8px;
    padding: 10px 12px;
    margin-bottom: 12px;
    border: 1px solid rgba(255,255,255,0.08);
}

/* ── CARDS ─────────────────────────────────────────────────────── */
.card {
    background: var(--white);
    border-radius: 12px;
    padding: 1.2rem 1.5rem;
    box-shadow: var(--card-shadow);
    margin-bottom: 1rem;
    transition: box-shadow 0.2s;
}
.card:hover { box-shadow: var(--card-shadow-hover); }
.card-tight { padding: 0.9rem 1.2rem; }

.kpi-card {
    background: var(--white);
    border-radius: 12px;
    padding: 1.1rem 1.4rem;
    box-shadow: var(--card-shadow);
    border-left: 4px solid var(--navy-600);
    position: relative;
    overflow: hidden;
}
.kpi-card::after {
    content: '';
    position: absolute;
    top: 0; right: 0;
    width: 60px; height: 60px;
    border-radius: 0 12px 0 60px;
    opacity: 0.06;
    background: var(--navy-600);
}
.kpi-label {
    font-size: 0.68rem;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    color: var(--gray-500);
    font-weight: 600;
    margin-bottom: 4px;
}
.kpi-value {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.5rem;
    font-weight: 500;
    color: var(--navy-700);
    line-height: 1.2;
}
.kpi-delta {
    font-size: 0.72rem;
    margin-top: 4px;
    display: flex;
    align-items: center;
    gap: 4px;
}
.delta-up { color: var(--green-600); }
.delta-down { color: var(--red-600); }
.delta-neutral { color: var(--gray-500); }

/* ── SENTINEL CARDS ────────────────────────────────────────────── */
.sentinel-card {
    background: var(--white);
    border-radius: 10px;
    padding: 1rem 1.3rem;
    box-shadow: var(--card-shadow);
    border-left: 4px solid var(--amber-500);
    margin-bottom: 10px;
    cursor: pointer;
    transition: all 0.2s;
}
.sentinel-card:hover { box-shadow: var(--card-shadow-hover); transform: translateX(2px); }
.sentinel-card.critical { border-left-color: var(--red-600); }
.sentinel-card.positive { border-left-color: var(--green-600); }
.sentinel-title { font-weight: 600; font-size: 0.9rem; color: var(--gray-900); }
.sentinel-body { font-size: 0.8rem; color: var(--gray-500); margin-top: 4px; }
.sentinel-badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 0.68rem;
    font-weight: 600;
    letter-spacing: 0.5px;
    text-transform: uppercase;
}
.badge-warn { background: var(--amber-100); color: #92400E; }
.badge-crit { background: var(--red-100); color: #991B1B; }
.badge-ok   { background: var(--green-100); color: #065F46; }
.badge-info { background: var(--navy-100); color: var(--navy-600); }

/* ── PROGRESS BAR ──────────────────────────────────────────────── */
.progress-wrap { background: #E5E7EB; border-radius: 999px; height: 6px; overflow: hidden; }
.progress-bar  { height: 100%; border-radius: 999px; transition: width 0.4s ease;
                 background: linear-gradient(90deg, var(--navy-600), var(--blue-500)); }
.progress-label { font-size: 0.72rem; color: var(--gray-500); margin-top: 4px; }

/* ── SECTION TITLE ─────────────────────────────────────────────── */
.section-title {
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 2px;
    color: var(--gray-500);
    font-weight: 700;
    margin: 1.4rem 0 0.7rem 0;
    padding-bottom: 6px;
    border-bottom: 1px solid var(--gray-300);
}

/* ── INFO BOXES ────────────────────────────────────────────────── */
.info-box {
    border-radius: 8px;
    padding: 10px 16px;
    font-size: 0.83rem;
    margin-bottom: 1rem;
    display: flex;
    align-items: flex-start;
    gap: 10px;
}
.info-box-blue   { background: var(--navy-100); border-left: 3px solid var(--navy-600); color: var(--navy-700); }
.info-box-amber  { background: var(--amber-100); border-left: 3px solid var(--amber-500); color: #78350F; }
.info-box-green  { background: var(--green-100); border-left: 3px solid var(--green-600); color: #064E3B; }
.info-box-red    { background: var(--red-100); border-left: 3px solid var(--red-600); color: #7F1D1D; }

/* ── TABLE OVERRIDES ───────────────────────────────────────────── */
.dataframe { font-size: 0.82rem !important; font-family: 'DM Sans', sans-serif !important; }
.dataframe th {
    background: var(--navy-700) !important;
    color: white !important;
    font-size: 0.72rem !important;
    letter-spacing: 0.5px;
    padding: 9px 12px !important;
    white-space: nowrap;
}
.dataframe td { padding: 7px 12px !important; }
.dataframe tr:hover td { background: #F5F7FF !important; }

/* ── BUTTONS ───────────────────────────────────────────────────── */
.stButton > button {
    background: var(--navy-600) !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 500 !important;
    font-size: 0.84rem !important;
    padding: 0.45rem 1.1rem !important;
    transition: all 0.18s !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.15) !important;
}
.stButton > button:hover {
    background: var(--navy-700) !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 12px rgba(15,32,68,0.25) !important;
}
button[kind="secondary"] {
    background: white !important;
    color: var(--navy-600) !important;
    border: 1.5px solid var(--navy-600) !important;
}
button[kind="secondary"]:hover {
    background: var(--navy-100) !important;
}

/* ── TABS ──────────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px;
    background: var(--gray-100);
    border-radius: 10px;
    padding: 4px;
    border: none !important;
}
.stTabs [data-baseweb="tab"] {
    background: transparent;
    border-radius: 7px;
    font-weight: 500;
    font-size: 0.82rem;
    color: var(--gray-500);
    padding: 8px 16px;
    border: none !important;
}
.stTabs [aria-selected="true"] {
    background: white !important;
    color: var(--navy-700) !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.1) !important;
}

/* ── FORMS ─────────────────────────────────────────────────────── */
.stTextInput > div > div > input,
.stSelectbox > div > div,
.stTextArea > div > div > textarea,
.stNumberInput > div > div > input {
    border-radius: 8px !important;
    border: 1.5px solid var(--gray-300) !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.84rem !important;
    transition: border-color 0.15s !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: var(--navy-600) !important;
    box-shadow: 0 0 0 3px rgba(26,58,122,0.1) !important;
}

/* ── CHAT ──────────────────────────────────────────────────────── */
.chat-message {
    display: flex;
    gap: 12px;
    margin-bottom: 16px;
    align-items: flex-start;
}
.chat-avatar {
    width: 36px; height: 36px;
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 1rem;
    flex-shrink: 0;
}
.chat-avatar-ai { background: linear-gradient(135deg, var(--navy-700), var(--navy-500)); color: white; }
.chat-avatar-user { background: var(--gray-100); }
.chat-bubble {
    background: var(--white);
    border-radius: 0 12px 12px 12px;
    padding: 10px 16px;
    font-size: 0.85rem;
    line-height: 1.6;
    box-shadow: var(--card-shadow);
    max-width: 85%;
}
.chat-bubble-user {
    background: var(--navy-100);
    border-radius: 12px 0 12px 12px;
    color: var(--navy-700);
}
.chat-time { font-size: 0.68rem; color: var(--gray-500); margin-top: 4px; }

/* ── TREE SCHEMA ───────────────────────────────────────────────── */
.tree-node {
    padding: 6px 10px 6px 20px;
    font-size: 0.82rem;
    border-left: 2px solid var(--gray-300);
    margin-left: 16px;
    color: var(--gray-700);
    position: relative;
}
.tree-node::before {
    content: '─';
    position: absolute;
    left: -8px;
    color: var(--gray-300);
}
.tree-root {
    padding: 8px 12px;
    font-weight: 600;
    font-size: 0.85rem;
    color: var(--navy-700);
    background: var(--navy-100);
    border-radius: 6px;
    margin-bottom: 4px;
}
.tree-subtotal {
    font-weight: 700;
    color: var(--navy-600);
    background: #EEF4FF;
    border-radius: 4px;
}

/* ── ONBOARDING ────────────────────────────────────────────────── */
.onboarding-step {
    background: white;
    border-radius: 16px;
    padding: 2rem;
    box-shadow: var(--card-shadow);
    max-width: 680px;
    margin: 0 auto;
}
.onboarding-header {
    text-align: center;
    margin-bottom: 2rem;
}
.onboarding-header h2 {
    font-family: 'DM Serif Display', serif;
    font-size: 1.8rem;
    color: var(--navy-700);
}
.step-indicator {
    display: flex;
    justify-content: center;
    gap: 8px;
    margin-bottom: 1.5rem;
}
.step-dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    background: var(--gray-300);
}
.step-dot-active { background: var(--navy-600); }

/* ── METRIC NUMBER FONT ────────────────────────────────────────── */
.mono { font-family: 'JetBrains Mono', monospace !important; }

/* ── EXPANDER ──────────────────────────────────────────────────── */
div[data-testid="stExpander"] {
    background: white;
    border-radius: 10px;
    border: 1px solid var(--gray-300);
    box-shadow: none;
}
</style>
"""
