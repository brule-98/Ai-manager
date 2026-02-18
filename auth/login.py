import streamlit as st

# ─── UTENTI DEMO (in produzione: sostituire con Supabase auth) ────────────────
# Struttura: {username: {password, nome, tenant, role}}
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
        "tenant": "Demo Tenant",
        "role": "professionista"
    }
}

def render_login():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Serif+Display&display=swap');

    .login-wrap {
        min-height: 100vh;
        display: flex;
        align-items: center;
        justify-content: center;
        background: linear-gradient(160deg, #0F2044 0%, #1A3A7A 60%, #2952A3 100%);
    }
    .login-box {
        background: white;
        border-radius: 20px;
        padding: 3rem 3rem 2.5rem;
        max-width: 420px;
        width: 100%;
        box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        text-align: center;
    }
    .login-logo {
        font-family: 'DM Serif Display', serif;
        font-size: 2rem;
        color: #0F2044;
        margin-bottom: 0.3rem;
    }
    .login-sub {
        font-size: 0.78rem;
        color: #8896AB;
        margin-bottom: 2rem;
        letter-spacing: 0.5px;
        text-transform: uppercase;
    }
    .login-divider {
        border: none;
        border-top: 1px solid #E2E8F0;
        margin: 1.5rem 0;
    }
    .login-footer {
        font-size: 0.72rem;
        color: #8896AB;
        margin-top: 1.5rem;
    }
    </style>
    """, unsafe_allow_html=True)

    # Layout centrato
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <div style="text-align:center; padding: 3rem 0 1rem 0;">
            <div style="font-family:'DM Serif Display',serif; font-size:2.2rem; color:#0F2044;">📊 AI-Manager</div>
            <div style="font-size:0.78rem; color:#8896AB; text-transform:uppercase; letter-spacing:1px; margin-top:4px;">
                Piattaforma di Controllo di Gestione
            </div>
        </div>
        """, unsafe_allow_html=True)

        with st.container():
            st.markdown("<br>", unsafe_allow_html=True)

            with st.form("login_form"):
                st.markdown("#### Accedi al tuo account")
                username = st.text_input("Username", placeholder="es. studio_rossi")
                password = st.text_input("Password", type="password", placeholder="••••••••")

                st.markdown("<br>", unsafe_allow_html=True)
                submitted = st.form_submit_button("Accedi →", use_container_width=True)

                if submitted:
                    if username in UTENTI_DEMO and UTENTI_DEMO[username]["password"] == password:
                        u = UTENTI_DEMO[username]
                        st.session_state['authenticated'] = True
                        st.session_state['user'] = u['nome']
                        st.session_state['tenant'] = u['tenant']
                        st.session_state['role'] = u['role']
                        st.session_state['clienti'] = {}
                        st.session_state['page'] = 'Workspace'
                        st.rerun()
                    else:
                        st.error("Credenziali non valide. Riprova.")

            st.markdown("""
            <div style="text-align:center; margin-top:1.5rem;">
                <hr style="border:none; border-top:1px solid #E2E8F0; margin-bottom:1rem;">
                <p style="font-size:0.72rem; color:#8896AB;">
                    <b>Demo:</b> studio_rossi / demo123 &nbsp;·&nbsp; mario.bianchi / demo123
                </p>
                <p style="font-size:0.68rem; color:#B0BAC9;">
                    AI-Manager MVP v1.0 · Sessione locale
                </p>
            </div>
            """, unsafe_allow_html=True)
