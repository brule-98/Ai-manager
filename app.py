import streamlit as st

st.set_page_config(
    page_title="AI-Manager | Intelligence Gestionale",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="📊"
)

from services.styles import GLOBAL_CSS
st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

from auth.login import render_login
from modules.onboarding import render_onboarding, is_onboarding_complete
from modules.workspace import render_workspace
from modules.dashboard import render_dashboard
from modules.rettifiche import render_rettifiche
from modules.configurazione import render_configurazione
from modules.sentinel import render_sentinel
from modules.ai_cfo import render_ai_cfo


# ─── INIT SESSION STATE ────────────────────────────────────────────────────────
def init_state():
    defaults = {
        'authenticated': False,
        'user': None,
        'tenant': None,
        'role': None,
        'clienti': {},
        'cliente_attivo': None,
        'page': 'Dashboard',
        'sito_attivo': 'Globale',
        'company_profile': {},
        'onboarding_done': False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# ─── AUTH GATE ────────────────────────────────────────────────────────────────
if not st.session_state['authenticated']:
    render_login()
    st.stop()

# ─── ONBOARDING GATE ──────────────────────────────────────────────────────────
if not st.session_state.get('onboarding_done'):
    render_onboarding()
    st.stop()

# ─── HELPERS ──────────────────────────────────────────────────────────────────
user   = st.session_state['user']
tenant = st.session_state['tenant']
role   = st.session_state['role']
ca     = st.session_state.get('cliente_attivo')
cliente = st.session_state.get('clienti', {}).get(ca, {}) if ca else {}

# Conta alert sentinel
n_alerts = 0
if cliente.get('df_db') is not None and cliente.get('mapping'):
    try:
        from modules.sentinel import _compute_alerts
        alerts = _compute_alerts(cliente)
        n_alerts = len(alerts)
    except Exception:
        pass

# ─── HEADER ───────────────────────────────────────────────────────────────────
profile = st.session_state.get('company_profile', {})
company_name = profile.get('nome_azienda', tenant)
role_label   = '🏢 Studio' if role == 'professionista' else '👔 Azienda'
alert_badge  = f'<span class="header-badge header-badge-alert">🔔 {n_alerts} alert</span>' if n_alerts > 0 else ''

st.markdown(f"""
<div class="app-header">
    <div class="app-header-brand">
        <h1>📊 AI-Manager</h1>
        <p class="tagline">Enterprise Intelligence Gestionale</p>
    </div>
    <div class="app-header-right">
        {alert_badge}
        <span class="header-badge">{role_label} · {company_name}</span>
        <span class="header-badge" style="opacity:0.7; font-size:0.68rem;">👤 {user}</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ─── SIDEBAR ──────────────────────────────────────────────────────────────────
with st.sidebar:

    # ── CLIENTE ──────────────────────────────────────────────────
    st.markdown("#### 📁 Cliente")
    clienti = list(st.session_state['clienti'].keys())

    if clienti:
        idx_default = clienti.index(ca) if ca in clienti else 0
        cliente_sel = st.selectbox("", clienti, index=idx_default, key="sel_cliente",
                                    label_visibility="collapsed")
        if cliente_sel != ca:
            st.session_state['cliente_attivo'] = cliente_sel
            st.session_state['sito_attivo'] = 'Globale'
            st.rerun()
    else:
        st.caption("Nessun cliente")

    if role == 'professionista':
        with st.expander("➕ Nuovo cliente"):
            nuovo = st.text_input("", placeholder="Nome cliente", key="nuovo_cliente_input",
                                   label_visibility="collapsed")
            if st.button("Crea", key="btn_crea"):
                nome = nuovo.strip()
                if nome and nome not in st.session_state['clienti']:
                    st.session_state['clienti'][nome] = {
                        'df_piano': None, 'df_db': None, 'df_ricl': None,
                        'rettifiche': [], 'mapping': {}, 'mapping_staging': None,
                        'schemi': {}, 'schema_attivo': None, 'budget': None
                    }
                    st.session_state['cliente_attivo'] = nome
                    st.rerun()
    else:
        if tenant not in st.session_state['clienti']:
            st.session_state['clienti'][tenant] = {
                'df_piano': None, 'df_db': None, 'df_ricl': None,
                'rettifiche': [], 'mapping': {}, 'mapping_staging': None,
                'schemi': {}, 'schema_attivo': None, 'budget': None
            }
            st.session_state['cliente_attivo'] = tenant

    # ── MULTI-SITE SELECTOR ───────────────────────────────────────
    cliente_data = st.session_state.get('clienti', {}).get(
        st.session_state.get('cliente_attivo', ''), {}
    )
    df_db_curr = cliente_data.get('df_db')

    siti_disponibili = ['Globale']
    if df_db_curr is not None:
        from services.data_utils import find_column
        col_sito = find_column(df_db_curr, ['Sito', 'sito', 'Stabilimento', 'stabilimento', 'Site', 'Plant'])
        if col_sito:
            siti = sorted(df_db_curr[col_sito].dropna().astype(str).unique().tolist())
            siti_disponibili = ['Globale'] + siti

    if len(siti_disponibili) > 1:
        st.markdown("#### 🏭 Sito / Stabilimento")
        sito_sel = st.selectbox("", siti_disponibili,
                                 index=siti_disponibili.index(st.session_state.get('sito_attivo', 'Globale'))
                                 if st.session_state.get('sito_attivo') in siti_disponibili else 0,
                                 key="sel_sito", label_visibility="collapsed")
        st.session_state['sito_attivo'] = sito_sel
        if sito_sel != 'Globale':
            st.markdown(f'<span class="sentinel-badge badge-info">🔍 Filtro: {sito_sel}</span>',
                        unsafe_allow_html=True)

    # ── NAVIGAZIONE ───────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 🧭 Navigazione")

    nav_items = [
        ("📊", "Dashboard"),
        ("🗂️", "Workspace"),
        ("🔔", f"Sentinel {'('+str(n_alerts)+')' if n_alerts else ''}"),
        ("🤖", "AI CFO"),
        ("✏️", "Rettifiche"),
        ("⚙️", "Configurazione"),
        ("🏢", "Profilo"),
    ]

    page = st.session_state.get('page', 'Dashboard')

    for icon, label in nav_items:
        base_key = label.split(' ')[0] if '(' in label else label
        is_active = page == base_key

        css_class = "nav-btn-active" if is_active else "nav-btn"
        st.markdown(f'<div class="{css_class}">', unsafe_allow_html=True)
        if st.button(f"{icon}  {label}", key=f"nav_{base_key}", use_container_width=True):
            st.session_state['page'] = base_key
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")
    if st.button("🚪 Logout", use_container_width=True, key="btn_logout"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()

    st.markdown("""
    <div style='padding: 12px 0; text-align:center;'>
        <span style='font-size:0.65rem; color:#4A5568; letter-spacing:1px;'>AI-MANAGER v2.0 ENTERPRISE</span>
    </div>
    """, unsafe_allow_html=True)

# ─── ROUTER ───────────────────────────────────────────────────────────────────
page = st.session_state.get('page', 'Dashboard')

if page == 'Dashboard':
    render_dashboard()
elif page == 'Workspace':
    render_workspace()
elif page == 'Sentinel':
    render_sentinel()
elif page == 'AI CFO':
    render_ai_cfo()
elif page == 'Rettifiche':
    render_rettifiche()
elif page == 'Configurazione':
    render_configurazione()
elif page == 'Profilo':
    render_onboarding(edit_mode=True)
