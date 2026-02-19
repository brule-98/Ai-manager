"""
login.py — Autenticazione multi-utente con design premium.
"""
import streamlit as st

UTENTI_DEMO = {
    "studio_rossi": {
        "password": "demo123",
        "nome": "Studio Rossi & Associati",
        "tenant": "Studio Rossi",
        "role": "professionista"
    },
    "mario.bianchi": {
        "password": "demo123",
        "nome": "Mario Bianchi",
        "tenant": "Bianchi Srl",
        "role": "azienda"
    },
    "admin": {
        "password": "admin",
        "nome": "Admin Demo",
        "tenant": "Demo Corp",
        "role": "professionista"
    }
}


def render_login():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=Playfair+Display:wght@700&display=swap');

    html, body, [class*="css"] {
        background: #0A1628 !important;
        font-family: 'DM Sans', sans-serif !important;
    }
    .login-bg {
        min-height: 100vh;
        background: radial-gradient(ellipse at 20% 50%, rgba(30,58,110,0.4) 0%, transparent 60%),
                    radial-gradient(ellipse at 80% 20%, rgba(201,168,76,0.1) 0%, transparent 40%),
                    #0A1628;
    }
    .login-card {
        background: rgba(17, 24, 39, 0.9);
        border: 1px solid rgba(201,168,76,0.2);
        border-radius: 20px;
        padding: 44px 48px;
        backdrop-filter: blur(20px);
        box-shadow: 0 25px 80px rgba(0,0,0,0.5);
        max-width: 440px;
        margin: 0 auto;
    }
    .login-brand {
        font-size: 10px;
        text-transform: uppercase;
        letter-spacing: 4px;
        color: #C9A84C;
        font-weight: 700;
        margin-bottom: 8px;
        text-align: center;
    }
    .login-title {
        font-family: 'Playfair Display', serif;
        font-size: 2.2rem;
        color: #F1F5F9;
        text-align: center;
        margin-bottom: 4px;
        letter-spacing: -0.5px;
    }
    .login-sub {
        text-align: center;
        font-size: 0.82rem;
        color: #475569;
        margin-bottom: 36px;
        letter-spacing: 0.5px;
    }
    .demo-box {
        background: rgba(30,58,110,0.3);
        border: 1px solid rgba(59,130,246,0.2);
        border-radius: 10px;
        padding: 12px 16px;
        margin-top: 20px;
        font-size: 0.78rem;
        color: #64748B;
        text-align: center;
    }
    .demo-box strong { color: #94A3B8; }
    </style>

    <div class="login-bg">
    """, unsafe_allow_html=True)

    st.markdown("<br><br>", unsafe_allow_html=True)

    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.markdown("""
        <div class="login-card">
            <div class="login-brand">AI-Manager Platform</div>
            <div class="login-title">📊 Accedi</div>
            <div class="login-sub">Piattaforma di Controllo di Gestione</div>
        </div>
        """, unsafe_allow_html=True)

        with st.form("form_login", clear_on_submit=False):
            username = st.text_input("Username", placeholder="es. studio_rossi",
                                      key="login_user")
            password = st.text_input("Password", type="password",
                                      placeholder="••••••••", key="login_pass")
            st.markdown("<br>", unsafe_allow_html=True)
            submitted = st.form_submit_button("→ Accedi alla Piattaforma",
                                               use_container_width=True)

            if submitted:
                if username in UTENTI_DEMO and UTENTI_DEMO[username]["password"] == password:
                    u = UTENTI_DEMO[username]
                    st.session_state.update({
                        'authenticated': True,
                        'user': u['nome'],
                        'tenant': u['tenant'],
                        'role': u['role'],
                        'clienti': {},
                        'cliente_attivo': None,
                        'page': 'Workspace',
                    })
                    st.rerun()
                else:
                    st.error("Credenziali non valide. Riprova.")

        st.markdown("""
        <div class="demo-box">
            🔐 <strong>Account demo:</strong><br>
            studio_rossi / demo123 &nbsp;·&nbsp; mario.bianchi / demo123
        </div>
        <br>
        """, unsafe_allow_html=True)
