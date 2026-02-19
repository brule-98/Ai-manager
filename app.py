"""
app.py — AI-Manager: Piattaforma Professionale di Controllo di Gestione.
Entry point Streamlit con routing multi-pagina e design corporate premium.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import streamlit as st

st.set_page_config(
    page_title="AI-Manager | Controllo di Gestione",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="📊"
)

# ── GLOBAL CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&family=DM+Serif+Display:ital@0;1&display=swap');

/* ── Root & Body ── */
html, body, [class*="css"] {
    font-family: 'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
    background: #F8F9FB !important;
}

/* ── Main Area ── */
.main .block-container {
    padding: 0 2rem 2rem !important;
    max-width: 1280px;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0A1220 0%, #0F1E36 60%, #0A1220 100%) !important;
    border-right: 1px solid rgba(201,168,76,0.1) !important;
}
[data-testid="stSidebar"] * { color: #CBD5E8 !important; }
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 { color: #F1F5F9 !important; }
[data-testid="stSidebar"] .stSelectbox > div > div {
    background: rgba(255,255,255,0.06) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    color: #E2E8F0 !important;
}

/* ── Sidebar nav buttons ── */
[data-testid="stSidebar"] .stButton > button {
    background: transparent !important;
    color: #94A3B8 !important;
    border: 1px solid transparent !important;
    border-radius: 8px !important;
    font-size: 0.84rem !important;
    text-align: left !important;
    transition: all 0.15s ease !important;
    width: 100% !important;
    margin-bottom: 3px !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(255,255,255,0.07) !important;
    border-color: rgba(255,255,255,0.12) !important;
    color: #E2E8F0 !important;
}

/* ── Main buttons ── */
.stButton > button {
    background: #1A3A7A;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 500 !important;
    transition: all 0.2s ease !important;
}
.stButton > button:hover {
    background: #0F2044 !important;
    transform: translateY(-1px);
    box-shadow: 0 4px 14px rgba(15,32,68,0.25) !important;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #1A3A7A, #0F2044) !important;
    box-shadow: 0 2px 8px rgba(15,32,68,0.2) !important;
}
.stButton > button[kind="primary"]:hover {
    background: linear-gradient(135deg, #0F2044, #071426) !important;
    transform: translateY(-1px) !important;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px;
    border-bottom: 2px solid #E2E8F0;
    background: transparent;
}
.stTabs [data-baseweb="tab"] {
    background: transparent;
    border-radius: 8px 8px 0 0;
    font-weight: 500;
    font-size: 0.83rem;
    color: #6B7280;
    padding: 9px 16px;
    border: none;
}
.stTabs [aria-selected="true"] {
    background: #EEF2FF !important;
    color: #1A3A7A !important;
    border-bottom: 3px solid #1A3A7A !important;
    font-weight: 600 !important;
}

/* ── Expanders ── */
div[data-testid="stExpander"] {
    background: white;
    border-radius: 10px;
    border: 1px solid #E2E8F0;
    margin-bottom: 8px;
    overflow: hidden;
}
div[data-testid="stExpander"]:hover {
    border-color: #C7D2FE;
}

/* ── Metrics ── */
[data-testid="stMetric"] {
    background: white;
    border-radius: 10px;
    padding: 14px 18px;
    box-shadow: 0 1px 6px rgba(0,0,0,.06);
}

/* ── Progress bar ── */
.stProgress > div > div > div {
    background: linear-gradient(90deg, #1A3A7A, #059669) !important;
}

/* ── Dataframes ── */
[data-testid="stDataFrame"] {
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    overflow: hidden;
}

/* ── Input fields ── */
.stTextInput input, .stTextArea textarea, .stNumberInput input {
    border: 1px solid #E2E8F0 !important;
    border-radius: 8px !important;
    font-family: 'DM Sans', sans-serif !important;
    transition: border-color 0.15s !important;
}
.stTextInput input:focus, .stTextArea textarea:focus, .stNumberInput input:focus {
    border-color: #1A3A7A !important;
    box-shadow: 0 0 0 3px rgba(26,58,122,0.1) !important;
}

/* ── Hide Streamlit branding ── */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 0 !important; }

/* ── Scrollbars (webkit) ── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #CBD5E8; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #94A3B8; }
</style>
""", unsafe_allow_html=True)

# ── IMPORTS ───────────────────────────────────────────────────────────────────
from auth.login import render_login
from modules.workspace import render_workspace
from modules.dashboard import render_dashboard
from modules.cfo_agent import render_cfo_agent
from modules.rettifiche import render_rettifiche
from modules.configurazione import render_configurazione
from modules.budget import render_budget
from services.data_utils import cliente_vuoto


def init_state():
    defaults = {
        'authenticated': False, 'user': None, 'tenant': None, 'role': None,
        'clienti': {}, 'cliente_attivo': None, 'page': 'Dashboard',
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


init_state()

# ── AUTH ─────────────────────────────────────────────────────────────────────
if not st.session_state['authenticated']:
    render_login()
    st.stop()

user   = st.session_state['user']
tenant = st.session_state['tenant']
role   = st.session_state['role']

# ── HEADER ───────────────────────────────────────────────────────────────────
role_badge = '🏢 Studio' if role == 'professionista' else '👔 Azienda'
st.markdown(f"""
<div style='background:linear-gradient(135deg,#0A1220 0%,#1A3A7A 60%,#0A1220 100%);
            color:white;padding:14px 28px;border-radius:0 0 16px 16px;margin-bottom:20px;
            display:flex;align-items:center;justify-content:space-between;
            box-shadow:0 2px 12px rgba(10,18,32,0.15)'>
    <div>
        <span style='font-size:10px;text-transform:uppercase;letter-spacing:3px;
                     color:#C9A84C;font-weight:700;margin-right:12px'>AI-Manager</span>
        <span style='font-size:1.1rem;font-weight:700;letter-spacing:-0.3px'>
            📊 Piattaforma di Controllo di Gestione
        </span>
    </div>
    <div style='font-size:0.75rem;color:#90AEE8;background:rgba(255,255,255,0.08);
                padding:5px 14px;border-radius:20px;border:1px solid rgba(255,255,255,0.1)'>
        👤 {user} &nbsp;·&nbsp; {tenant} &nbsp;·&nbsp; {role_badge}
    </div>
</div>
""", unsafe_allow_html=True)

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    # Logo
    st.markdown(f"""
    <div style='text-align:center;padding:16px 0 20px'>
        <div style='font-size:9px;text-transform:uppercase;letter-spacing:4px;
                    color:#C9A84C;font-weight:700;margin-bottom:4px'>
            AI-Manager
        </div>
        <div style='font-size:0.7rem;color:#475569'>Virtual CFO Platform</div>
        <div style='width:40px;height:1px;background:rgba(201,168,76,0.3);margin:10px auto 0'></div>
    </div>
    """, unsafe_allow_html=True)

    # ── Gestione clienti ─────────────────────────────────────────────────────
    st.markdown("**📁 Cliente**")
    clienti = list(st.session_state['clienti'].keys())

    if not clienti and role != 'professionista':
        # Auto-crea cliente per utente azienda
        if tenant not in st.session_state['clienti']:
            st.session_state['clienti'][tenant] = cliente_vuoto()
            st.session_state['cliente_attivo'] = tenant
            clienti = [tenant]

    if clienti:
        idx_def = 0
        ca_cur  = st.session_state.get('cliente_attivo')
        if ca_cur in clienti:
            idx_def = clienti.index(ca_cur)
        sel = st.selectbox("Attivo:", clienti, index=idx_def, label_visibility="collapsed")
        st.session_state['cliente_attivo'] = sel
    else:
        st.markdown("<div style='font-size:0.78rem;color:#475569;font-style:italic;padding:4px 0'>Nessun cliente</div>", unsafe_allow_html=True)
        st.session_state['cliente_attivo'] = None

    if role == 'professionista':
        with st.expander("➕ Nuovo cliente"):
            nome_n = st.text_input("Nome cliente:", key="new_cli_name", label_visibility="collapsed",
                                    placeholder="Es. Rossi Srl")
            if st.button("✚ Crea", key="btn_new_cli"):
                nome_n = nome_n.strip()
                if nome_n and nome_n not in st.session_state['clienti']:
                    st.session_state['clienti'][nome_n] = cliente_vuoto()
                    st.session_state['cliente_attivo'] = nome_n
                    st.rerun()

    st.markdown("<hr style='border-color:rgba(255,255,255,0.06);margin:16px 0 12px'>", unsafe_allow_html=True)

    # ── Navigazione ──────────────────────────────────────────────────────────
    st.markdown("**🧭 Navigazione**")

    nav = [
        ("📊", "Dashboard",       "Dashboard",       "Vista KPI, CE, Grafici"),
        ("🗂️", "Workspace",       "Workspace",       "Carica dati e mappatura"),
        ("🏦", "CFO Agent",       "CFO Agent",       "AI • Chat • Report • Alert"),
        ("🎯", "Budget",          "Budget",          "Budget e scostamenti"),
        ("✏️", "Rettifiche",     "Rettifiche",      "Rettifiche extra-contabili"),
        ("⚙️", "Configurazione", "Configurazione",  "Schema di riclassifica"),
    ]

    page_cur = st.session_state.get('page', 'Dashboard')
    for icon, label, key, hint in nav:
        is_active = page_cur == key
        prefix = "▶ " if is_active else "    "
        style = "font-weight:600;" if is_active else ""
        if st.button(f"{prefix}{icon} {label}", key=f"nav_{key}", use_container_width=True,
                     help=hint):
            st.session_state['page'] = key
            st.rerun()

    st.markdown("<hr style='border-color:rgba(255,255,255,0.06);margin:12px 0'>", unsafe_allow_html=True)

    # ── Info cliente attivo ────────────────────────────────────────────────
    ca = st.session_state.get('cliente_attivo')
    if ca:
        from services.data_utils import get_cliente
        cl = get_cliente()
        if cl:
            has_data   = cl.get('df_db') is not None
            has_map    = bool(cl.get('mapping'))
            has_budget = bool(cl.get('budget'))
            has_ai     = bool(st.session_state.get('anthropic_api_key') or
                              (hasattr(st, 'secrets') and st.secrets.get('ANTHROPIC_API_KEY','')))

            stati = [
                ("Dati caricati",  has_data),
                ("Mapping OK",     has_map),
                ("Budget attivo",  has_budget),
                ("CFO AI pronto",  has_ai),
            ]
            def _stato_row(nome, ok):
                clr = '#10B981' if ok else '#EF4444'
                sym = '✓' if ok else '○'
                return (f"<div style='display:flex;justify-content:space-between;font-size:0.72rem;"
                        f"padding:3px 0;color:#475569'>"
                        f"<span>{nome}</span>"
                        f"<span style='color:{clr}'>{sym}</span></div>")
            righe = "".join(_stato_row(n, o) for n, o in stati)
            st.markdown(f"""
            <div style='background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06);
                        border-radius:8px;padding:10px 12px;margin-bottom:12px'>
                <div style='font-size:9px;text-transform:uppercase;letter-spacing:1.5px;
                            color:#C9A84C;font-weight:700;margin-bottom:8px'>{ca}</div>
                {righe}
            </div>""", unsafe_allow_html=True)

    if st.button("🚪 Logout", use_container_width=True, key="btn_logout"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()

    # ── API Key auto-load ──────────────────────────────────────────────────
    if not st.session_state.get('anthropic_api_key'):
        try:
            k = st.secrets.get('ANTHROPIC_API_KEY', '')
            if k:
                st.session_state['anthropic_api_key'] = k
        except Exception:
            pass


# ── ROUTER ───────────────────────────────────────────────────────────────────
page = st.session_state.get('page', 'Dashboard')

if   page == 'Dashboard':     render_dashboard()
elif page == 'Workspace':     render_workspace()
elif page == 'CFO Agent':     render_cfo_agent()
elif page == 'Budget':        render_budget()
elif page == 'Rettifiche':    render_rettifiche()
elif page == 'Configurazione':render_configurazione()
