"""
configurazione.py — Configurazione Schema di Riclassificazione.
Design: Bloomberg Terminal dark theme.
"""
import streamlit as st
import pandas as pd
from services.data_utils import get_cliente, save_cliente, find_column
from services.riclassifica import get_label_map

C = {
    'gold':   '#C9A84C',
    'navy':   '#0A1628',
    'blue':   '#1E3A6E',
    'green':  '#10B981',
    'red':    '#EF4444',
    'amber':  '#F59E0B',
    'text':   '#E2E8F0',
    'muted':  '#64748B',
    'surf':   '#111827',
    'surf2':  '#1A2744',
    'border': 'rgba(255,255,255,0.06)',
}


def _card(content: str, border_color: str = None) -> str:
    bc = border_color or C['border']
    return f"""<div style='background:{C["surf"]};border:1px solid {bc};border-radius:12px;
                            padding:20px 24px;margin-bottom:16px'>{content}</div>"""


def render_configurazione():
    ca = st.session_state.get('cliente_attivo')
    if not ca:
        st.warning("⚠️ Seleziona un cliente dalla sidebar.")
        return

    cliente = get_cliente()
    df_ricl  = cliente.get('df_ricl')
    schemi   = cliente.get('schemi', {})
    schema_att = cliente.get('schema_attivo', '')

    # Header
    st.markdown(f"""
    <div style='background:linear-gradient(135deg,#0A1628 0%,#1E3A6E 100%);
                border-radius:14px;padding:20px 28px;margin-bottom:24px;
                border:1px solid rgba(201,168,76,0.15)'>
        <div style='font-size:10px;text-transform:uppercase;letter-spacing:3px;
                    color:{C["gold"]};font-weight:700;margin-bottom:6px'>CONFIGURAZIONE</div>
        <h2 style='color:{C["text"]};margin:0;font-size:1.4rem;font-weight:700'>
            ⚙️ Schema di Riclassificazione — {ca}
        </h2>
        <p style='color:{C["muted"]};margin:6px 0 0 0;font-size:0.82rem'>
            Gestisci schemi multipli, ordine voci, segni contabili e subtotali
        </p>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["🗂️ Gestione Schemi", "⚙️ Configurazione Voci"])

    # ═══════════════════════════════════════════════════════════════════════
    # TAB 1: GESTIONE SCHEMI
    # ═══════════════════════════════════════════════════════════════════════
    with tab1:
        st.markdown("### Schemi Disponibili")
        st.markdown(f"""
        <div style='background:rgba(201,168,76,0.08);border-left:3px solid {C["gold"]};
                    border-radius:0 8px 8px 0;padding:12px 16px;font-size:0.83rem;
                    color:{C["muted"]};margin-bottom:20px'>
        Puoi avere più schemi per lo stesso cliente (es. CE Gestionale, CE Civilistico, CE per SBU).
        Ogni schema mantiene il proprio ordine di voci, segni e subtotali. Solo uno è attivo alla volta.
        </div>""", unsafe_allow_html=True)

        if schemi:
            for nome_schema, config in schemi.items():
                is_active = nome_schema == schema_att
                border_c = C['gold'] if is_active else C['border']
                badge_html = f"<span style='background:rgba(201,168,76,0.15);color:{C['gold']};padding:2px 10px;border-radius:4px;font-size:0.72rem;font-weight:700'>● ATTIVO</span>" if is_active else ""

                col_a, col_b, col_c, col_d = st.columns([4, 1, 1, 1])
                with col_a:
                    st.markdown(
                        f"<div style='background:{C['surf']};border:1px solid {border_c};"
                        f"border-radius:10px;padding:12px 16px;display:flex;align-items:center;gap:12px'>"
                        f"<b style='color:{C['text']};font-size:0.92rem'>{nome_schema}</b>"
                        f"&nbsp;&nbsp;{badge_html}"
                        f"<span style='color:{C['muted']};font-size:0.78rem;margin-left:auto'>{len(config)} voci</span>"
                        f"</div>",
                        unsafe_allow_html=True
                    )
                with col_b:
                    if not is_active and st.button("Attiva", key=f"act_{nome_schema}"):
                        save_cliente({'schema_attivo': nome_schema})
                        st.success(f"Schema '{nome_schema}' attivato")
                        st.rerun()
                with col_c:
                    if st.button("Copia", key=f"copy_{nome_schema}"):
                        nuovo_nome = f"{nome_schema} (copia)"
                        schemi[nuovo_nome] = dict(config)
                        save_cliente({'schemi': schemi})
                        st.rerun()
                with col_d:
                    if st.button("🗑️", key=f"del_{nome_schema}"):
                        del schemi[nome_schema]
                        new_att = schema_att if schema_att != nome_schema else ''
                        save_cliente({'schemi': schemi, 'schema_attivo': new_att})
                        st.rerun()
        else:
            st.markdown(f"""
            <div style='background:{C["surf"]};border:1px dashed {C["border"]};border-radius:12px;
                        padding:30px;text-align:center;color:{C["muted"]}'>
                Nessuno schema configurato. Creane uno qui sotto.
            </div>""", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("#### ➕ Crea Nuovo Schema")

        with st.form("form_nuovo_schema"):
            c1, c2 = st.columns([3, 1])
            with c1:
                nome_nuovo = st.text_input("Nome schema:", placeholder="es. CE Gestionale 2024")
            with c2:
                st.markdown("<br>", unsafe_allow_html=True)
                crea = st.form_submit_button("Crea Schema", type="primary")

            if crea:
                n = nome_nuovo.strip()
                if not n:
                    st.error("Inserisci un nome.")
                elif n in schemi:
                    st.error("Nome già esistente.")
                else:
                    config_init = {}
                    if df_ricl is not None:
                        label_map = get_label_map(df_ricl)
                        col_cod = find_column(df_ricl, ['Codice', 'codice', 'ID', 'id', 'Voce', 'voce'])
                        for i, (cod, desc) in enumerate(label_map.items()):
                            config_init[cod] = {
                                'ordine': i * 10,
                                'segno': 1,
                                'subtotale': False,
                                'descrizione_override': desc
                            }
                    schemi[n] = config_init
                    save_cliente({'schemi': schemi, 'schema_attivo': n})
                    st.success(f"✅ Schema '{n}' creato con {len(config_init)} voci")
                    st.rerun()

    # ═══════════════════════════════════════════════════════════════════════
    # TAB 2: CONFIGURAZIONE VOCI
    # ═══════════════════════════════════════════════════════════════════════
    with tab2:
        if not schemi:
            st.info("Crea prima uno schema nel tab 'Gestione Schemi'.")
            return

        schema_sel = st.selectbox(
            "Schema da configurare:",
            list(schemi.keys()),
            index=list(schemi.keys()).index(schema_att) if schema_att in schemi else 0,
            key="conf_schema_sel"
        )
        config = schemi.get(schema_sel, {})
        label_map = get_label_map(df_ricl) if df_ricl is not None else {}

        if not config:
            st.info("Schema vuoto. Carica lo Schema di Riclassifica nel Workspace, poi ricrea lo schema.")
            _form_aggiungi_voce_standalone(schema_sel, config, schemi)
            return

        st.markdown(f"""
        <div style='background:rgba(16,185,129,0.06);border:1px solid rgba(16,185,129,0.15);
                    border-radius:8px;padding:12px 16px;font-size:0.82rem;color:{C["muted"]};margin-bottom:16px'>
        ⚙️ <b style='color:{C["text"]}'>Segno:</b> +1 = mantieni segno contabile &nbsp;·&nbsp;
        -1 = inverti (per mostrare i costi come positivi)<br>
        📌 <b style='color:{C["text"]}'>Subtotale:</b> evidenziato in grassetto nel report (es. EBITDA, Utile Operativo)
        </div>""", unsafe_allow_html=True)

        # Header colonne
        cols_h = st.columns([1, 3, 2, 1, 1, 1])
        for col, label in zip(cols_h, ['Ordine', 'Codice Voce', 'Etichetta Display', 'Segno', 'Subtot.', 'Del.']):
            col.markdown(f"<div style='font-size:0.7rem;font-weight:700;color:{C['muted']};text-transform:uppercase;letter-spacing:0.8px;padding:4px 0'>{label}</div>", unsafe_allow_html=True)

        config_updated = {}
        voci_ordinate = sorted(config.keys(), key=lambda v: config[v].get('ordine', 999))

        for voce in voci_ordinate:
            cfg = config[voce]
            desc_display = label_map.get(voce, cfg.get('descrizione_override', voce))

            cols = st.columns([1, 3, 2, 1, 1, 1])
            config_updated[voce] = dict(cfg)

            with cols[0]:
                new_ord = st.number_input("", value=int(cfg.get('ordine', 0)), step=10,
                                           label_visibility="collapsed", key=f"ord_{schema_sel}_{voce}")
                config_updated[voce]['ordine'] = new_ord

            with cols[1]:
                st.markdown(f"<div style='padding:10px 4px;font-size:0.82rem;color:{C['text']}'>{voce}</div>",
                            unsafe_allow_html=True)

            with cols[2]:
                label_ov = st.text_input("", value=cfg.get('descrizione_override', desc_display),
                                          label_visibility="collapsed", key=f"lbl_{schema_sel}_{voce}")
                config_updated[voce]['descrizione_override'] = label_ov

            with cols[3]:
                segno = st.selectbox("", [1, -1],
                                      index=0 if cfg.get('segno', 1) == 1 else 1,
                                      format_func=lambda x: "+1" if x == 1 else "-1",
                                      label_visibility="collapsed", key=f"sgn_{schema_sel}_{voce}")
                config_updated[voce]['segno'] = segno

            with cols[4]:
                sub = st.checkbox("", value=cfg.get('subtotale', False),
                                   label_visibility="collapsed", key=f"sub_{schema_sel}_{voce}")
                config_updated[voce]['subtotale'] = sub

            with cols[5]:
                if st.button("✕", key=f"del_voce_{schema_sel}_{voce}"):
                    del config_updated[voce]
                    schemi[schema_sel] = {k: v for k, v in config_updated.items() if k != voce}
                    save_cliente({'schemi': schemi})
                    st.rerun()

        st.markdown("---")
        col_s1, col_s2 = st.columns([1, 4])
        with col_s1:
            if st.button("💾 Salva Configurazione", type="primary"):
                schemi[schema_sel] = config_updated
                save_cliente({'schemi': schemi, 'schema_attivo': schema_sel})
                st.success(f"✅ Schema '{schema_sel}' salvato")
                st.rerun()

        st.markdown("---")
        _form_aggiungi_voce_standalone(schema_sel, config_updated, schemi)


def _form_aggiungi_voce_standalone(schema_sel, config, schemi):
    with st.expander("➕ Aggiungi voce manualmente"):
        with st.form(f"form_add_voce_{schema_sel}"):
            c1, c2, c3, c4 = st.columns(4)
            cod_v   = c1.text_input("Codice voce *", placeholder="es. RIC001")
            label_v = c2.text_input("Etichetta display", placeholder="es. Ricavi delle Vendite")
            segno_v = c3.selectbox("Segno", [1, -1], format_func=lambda x: "+1 mantieni" if x == 1 else "-1 inverti")
            sub_v   = c4.checkbox("Subtotale")

            if st.form_submit_button("➕ Aggiungi"):
                cod = cod_v.strip()
                if not cod:
                    st.error("Codice obbligatorio.")
                elif cod in config:
                    st.error("Codice già presente nello schema.")
                else:
                    max_ord = max([v.get('ordine', 0) for v in config.values()], default=0) + 10
                    config[cod] = {
                        'ordine': max_ord,
                        'segno': segno_v,
                        'subtotale': sub_v,
                        'descrizione_override': label_v.strip() or cod
                    }
                    schemi[schema_sel] = config
                    save_cliente({'schemi': schemi})
                    st.success(f"✅ Voce '{cod}' aggiunta.")
                    st.rerun()
