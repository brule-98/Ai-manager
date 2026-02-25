"""clienti.py — Gestione parco clienti."""
import streamlit as st
from services.data_utils import get_cliente, save_cliente


def render_clienti():
    st.markdown("## 🏢 Gestione Clienti")

    clienti = st.session_state.get('clienti', {})

    # ── Aggiungi cliente ──────────────────────────────────────────────────────
    with st.expander("➕ Nuovo cliente", expanded=not bool(clienti)):
        c1, c2 = st.columns([3, 1])
        nome = c1.text_input("Ragione sociale", placeholder="es. Acme Srl", key="new_cl_nome")
        if c2.button("Aggiungi", type="primary", key="add_cl_btn"):
            if nome.strip():
                if nome.strip() not in clienti:
                    st.session_state['clienti'][nome.strip()] = {}
                    st.session_state['cliente_attivo'] = nome.strip()
                    st.success(f"✅ Cliente '{nome.strip()}' aggiunto.")
                    st.rerun()
                else:
                    st.warning("Cliente già presente.")
            else:
                st.error("Inserisci la ragione sociale.")

    if not clienti:
        st.info("Nessun cliente ancora. Aggiungine uno qui sopra.")
        return

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── Lista clienti ─────────────────────────────────────────────────────────
    ca = st.session_state.get('cliente_attivo')
    for nome, dati in clienti.items():
        has_db   = dati.get('df_db') is not None
        has_map  = bool(dati.get('mapping'))
        has_schema = bool(dati.get('schema_attivo'))
        status = "✅ Pronto" if (has_db and has_map) else ("🔄 Parziale" if has_db else "⭕ Vuoto")
        sc = "#10B981" if (has_db and has_map) else ("#F59E0B" if has_db else "#EF4444")
        active = nome == ca

        border = "2px solid rgba(201,168,76,0.5)" if active else "1px solid rgba(255,255,255,0.07)"
        bg     = "rgba(201,168,76,0.06)" if active else "rgba(13,22,37,0.8)"

        col_n, col_s, col_sc, col_a, col_d = st.columns([3, 2, 2, 1, 1])
        col_n.markdown(
            f"<div style='padding:10px 0;font-weight:{'700' if active else '500'};"
            f"color:{'#C9A84C' if active else '#F1F5F9'}'>"
            f"{'▶ ' if active else ''}{nome}</div>", unsafe_allow_html=True)
        col_s.markdown(f"<div style='padding:10px 0;font-size:0.82rem;color:{sc}'>{status}</div>",
                       unsafe_allow_html=True)
        col_sc.markdown(f"<div style='padding:10px 0;font-size:0.8rem;color:#64748B'>"
                        f"{dati.get('schema_attivo','—')}</div>", unsafe_allow_html=True)
        if col_a.button("Seleziona", key=f"sel_{nome}", type="primary" if active else "secondary"):
            st.session_state['cliente_attivo'] = nome
            st.session_state['page'] = 'Dashboard'
            st.rerun()
        if col_d.button("✕", key=f"del_{nome}", help="Elimina cliente"):
            del st.session_state['clienti'][nome]
            if ca == nome:
                remaining = list(st.session_state['clienti'].keys())
                st.session_state['cliente_attivo'] = remaining[0] if remaining else None
            st.rerun()

        st.markdown(f"<hr style='border:none;border-top:1px solid rgba(255,255,255,0.04);margin:2px 0'>",
                    unsafe_allow_html=True)
