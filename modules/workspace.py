import streamlit as st
import pandas as pd
import io
from services.data_utils import smart_load, find_column, get_cliente, save_cliente
from services.ai_mapper import ai_suggest_mapping, ai_suggest_new_accounts


def render_workspace():
    ca = st.session_state.get('cliente_attivo')
    if not ca:
        st.warning("⚠️ Seleziona o crea un cliente dalla sidebar.")
        return

    cliente = get_cliente()
    st.markdown(f"## 🗂️ Workspace Dati — {ca}")

    tab1, tab2, tab3 = st.tabs(["📂 Dati & File", "🔗 Mappatura Conti", "🔑 API Key"])

    with tab1:
        _render_caricamento(ca, cliente)
    with tab2:
        _render_mappatura(ca, cliente)
    with tab3:
        _render_api_tab()


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1: CARICAMENTO
# ══════════════════════════════════════════════════════════════════════════════
def _render_caricamento(ca, cliente):
    st.markdown("""
    <div class="info-box info-box-blue">
    📌 Carica i tre file richiesti in formato <b>CSV</b> (sep ; o ,) o <b>Excel (.xlsx)</b>.
    I caratteri italiani e gli encoding vengono gestiti automaticamente.
    Per la gestione multi-sito, assicurati che il DB contenga una colonna <b>"Sito"</b> o <b>"Stabilimento"</b>.
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown("**1. Piano dei Conti**")
        st.caption("Colonne: Codice, Descrizione")
        u = st.file_uploader("Piano dei Conti", type=["csv","xlsx","xls"],
                              key=f"u_piano_{ca}", label_visibility="collapsed")
        if u:
            df = smart_load(u)
            if df is not None:
                save_cliente({'df_piano': df})
                st.success(f"✅ {len(df)} conti")
                with st.expander("Anteprima"):
                    st.dataframe(df.head(6), use_container_width=True)
        elif cliente.get('df_piano') is not None:
            _stato_file(f"{len(cliente['df_piano'])} conti in memoria", cliente['df_piano'])

    with c2:
        st.markdown("**2. DB Contabile / Movimenti**")
        st.caption("Colonne: Data, Conto, Saldo [, Sito]")
        u = st.file_uploader("DB Contabile", type=["csv","xlsx","xls"],
                              key=f"u_db_{ca}", label_visibility="collapsed")
        if u:
            df = smart_load(u)
            if df is not None:
                save_cliente({'df_db': df})
                # Rilevamento colonna sito
                col_sito = find_column(df, ['Sito','sito','Stabilimento','stabilimento','Site'])
                siti_msg = ""
                if col_sito:
                    siti = df[col_sito].dropna().unique()
                    siti_msg = f" · {len(siti)} siti rilevati"
                st.success(f"✅ {len(df)} movimenti{siti_msg}")
                with st.expander("Anteprima"):
                    st.dataframe(df.head(6), use_container_width=True)
        elif cliente.get('df_db') is not None:
            _stato_file(f"{len(cliente['df_db'])} movimenti in memoria", cliente['df_db'])

    with c3:
        st.markdown("**3. Schema di Riclassifica**")
        st.caption("Colonne: Codice, Descrizione")
        u = st.file_uploader("Schema", type=["csv","xlsx","xls"],
                              key=f"u_ricl_{ca}", label_visibility="collapsed")
        if u:
            df = smart_load(u)
            if df is not None:
                save_cliente({'df_ricl': df})
                st.success(f"✅ {len(df)} voci")
                with st.expander("Anteprima"):
                    st.dataframe(df.head(6), use_container_width=True)
        elif cliente.get('df_ricl') is not None:
            _stato_file(f"{len(cliente['df_ricl'])} voci schema", cliente['df_ricl'])

    # Memory Mapping: caricamento CSV storico
    st.markdown("---")
    st.markdown("#### 💾 Memory Mapping — Carica Abbinamenti Storici")
    st.markdown("""
    <div class="info-box info-box-amber">
    ⚡ Hai già un file CSV con gli abbinamenti <b>Codice Conto → Codice Riclassifica</b> da un periodo precedente?
    Caricalo qui per pre-compilare automaticamente la mappatura.
    </div>
    """, unsafe_allow_html=True)

    u_mem = st.file_uploader(
        "CSV Memory Mapping (colonne: codice_conto, codice_voce_ricl)",
        type=["csv","xlsx","xls"], key=f"u_mem_{ca}"
    )
    if u_mem:
        df_mem = smart_load(u_mem)
        if df_mem is not None:
            col_c = find_column(df_mem, ['codice_conto','Codice Conto','conto','Codice','codice'])
            col_v = find_column(df_mem, ['codice_voce_ricl','voce_ricl','Voce','codice_voce','mapping'])
            if col_c and col_v:
                mapping_mem = dict(zip(
                    df_mem[col_c].astype(str),
                    df_mem[col_v].astype(str)
                ))
                mapping_curr = cliente.get('mapping', {})
                n_nuovi = sum(1 for k, v in mapping_mem.items() if k not in mapping_curr)
                n_aggiornati = sum(1 for k, v in mapping_mem.items() if k in mapping_curr)
                mapping_curr.update(mapping_mem)
                save_cliente({'mapping': mapping_curr})
                st.success(f"✅ Memory Mapping applicato: {n_nuovi} nuovi abbinamenti, {n_aggiornati} aggiornati.")
                st.rerun()
            else:
                st.error("Colonne non trovate. Serve: 'codice_conto' e 'codice_voce_ricl'.")

    # Status bar
    stati = {
        'Piano dei Conti': cliente.get('df_piano') is not None,
        'DB Contabile':    cliente.get('df_db') is not None,
        'Schema Riclassifica': cliente.get('df_ricl') is not None,
    }
    st.markdown("---")
    cols = st.columns(3)
    for i, (nome, ok) in enumerate(stati.items()):
        with cols[i]:
            c, bg, ic = ('#065F46','#D1FAE5','✅') if ok else ('#92400E','#FEF3C7','⏳')
            st.markdown(
                f"<div style='text-align:center;padding:10px;background:{bg};border-radius:8px;"
                f"color:{c};font-weight:500;font-size:0.83rem;'>{ic} {nome}</div>",
                unsafe_allow_html=True
            )


def _stato_file(msg, df):
    st.markdown(f"<div class='info-box info-box-blue'>📋 {msg}</div>", unsafe_allow_html=True)
    with st.expander("Anteprima"):
        st.dataframe(df.head(6), use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2: MAPPATURA
# ══════════════════════════════════════════════════════════════════════════════
def _render_mappatura(ca, cliente):
    df_piano = cliente.get('df_piano')
    df_ricl  = cliente.get('df_ricl')
    mapping  = cliente.get('mapping', {})
    staging  = cliente.get('mapping_staging')  # None = nessuna staging attiva

    if df_piano is None or df_ricl is None:
        st.warning("⚠️ Carica prima Piano dei Conti e Schema di Riclassifica (Tab 1).")
        return

    col_cod_piano = find_column(df_piano, ['Codice','codice','codice conto','Codice Conto','CODICE','Conto','conto','ID'])
    col_desc_piano = find_column(df_piano, ['Descrizione','descrizione','conto','Conto','Nome','nome'])
    col_cod_ricl   = find_column(df_ricl, ['Codice','codice','Voce','voce','ID','id'])
    col_desc_ricl  = find_column(df_ricl, ['Descrizione','descrizione','voce','Voce','Nome','nome'])

    if not col_cod_piano or not col_cod_ricl:
        st.error("Colonna 'Codice' non trovata in uno dei file. Verifica le intestazioni.")
        return

    # Costruisci opzioni dropdown: "A1 — Ricavi Vendite"
    voci_ricl = df_ricl[col_cod_ricl].astype(str).tolist()
    if col_desc_ricl:
        voci_ricl_label = {
            str(r[col_cod_ricl]): f"{r[col_cod_ricl]} — {r[col_desc_ricl]}"
            for _, r in df_ricl.iterrows()
        }
    else:
        voci_ricl_label = {v: v for v in voci_ricl}

    # ── PROGRESS BADGE ───────────────────────────────────────────
    n_tot  = len(df_piano)
    n_mapp = len([v for v in mapping.values() if v and str(v) != 'nan'])
    n_rest = n_tot - n_mapp
    pct    = round(n_mapp / n_tot * 100) if n_tot > 0 else 0

    col_p1, col_p2, col_p3 = st.columns([2, 2, 1])
    with col_p1:
        st.markdown(f"""
        <div style="margin-bottom:4px;">
            <span style="font-size:0.72rem; color:#6B7280; text-transform:uppercase; letter-spacing:1px;">
                Progresso mappatura
            </span>
            <span style="margin-left:8px; font-weight:700; color:{'#059669' if pct == 100 else '#1A3A7A'};">
                {pct}%
            </span>
        </div>
        <div class="progress-wrap">
            <div class="progress-bar" style="width:{pct}%"></div>
        </div>
        <div class="progress-label">{n_mapp}/{n_tot} conti mappati · {n_rest} rimanenti</div>
        """, unsafe_allow_html=True)
    with col_p2:
        st.markdown(f"""
        <div style="display:flex; gap:8px; align-items:center; margin-top:8px;">
            <span class="sentinel-badge badge-ok">✅ Mappati: {n_mapp}</span>
            <span class="sentinel-badge badge-warn">⏳ Da fare: {n_rest}</span>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # ── SEZIONE AI CON STAGING ───────────────────────────────────
    st.markdown("#### 🤖 Mappatura AI con Staging")

    # Banner staging attivo
    if staging is not None:
        n_staging = len([v for v in staging.values() if v])
        st.markdown(f"""
        <div class="info-box info-box-amber">
        <div>
        ⚡ <b>Staging AI attivo</b> — {n_staging} conti suggeriti dall'AI in attesa di conferma.<br>
        <span style="font-size:0.78rem;">Revisiona i suggerimenti sotto, poi <b>Accetta</b> o <b>Ripristina manuale</b>.</span>
        </div>
        </div>
        """, unsafe_allow_html=True)

        col_acc, col_reset = st.columns(2)
        with col_acc:
            if st.button("✅ Accetta tutti i suggerimenti AI", type="primary", key="btn_accetta_staging"):
                mapping.update(staging)
                save_cliente({'mapping': mapping, 'mapping_staging': None})
                st.success("Mapping AI accettato e salvato!")
                st.rerun()
        with col_reset:
            if st.button("↩️ Ripristina a Manuale", key="btn_reset_staging"):
                save_cliente({'mapping_staging': None})
                st.info("Staging rimosso. Il mapping manuale è invariato.")
                st.rerun()
    else:
        col_ai1, col_ai2 = st.columns(2)
        with col_ai1:
            if st.button("🤖 Suggerisci TUTTI i conti (AI)", use_container_width=True, key="btn_ai_all"):
                _esegui_ai_staging(df_piano, df_ricl, mapping, full=True)
        with col_ai2:
            if st.button("✨ Suggerisci solo NUOVI (AI)", use_container_width=True,
                          key="btn_ai_new", disabled=(n_rest == 0)):
                _esegui_ai_staging(df_piano, df_ricl, mapping, full=False)

    # ── MAPPATURA MANUALE ────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### ✏️ Revisione Manuale")

    # Filtro
    c_f1, c_f2 = st.columns([2, 1])
    with c_f1:
        filtro = st.radio("Mostra:", ["Tutti", "Solo non mappati", "Solo mappati"],
                           horizontal=True, key="mapp_filtro_main")
    with c_f2:
        cerca = st.text_input("🔍 Cerca conto:", placeholder="codice o descrizione...",
                               key="mapp_cerca", label_visibility="collapsed")

    conti_df = df_piano.copy()

    # Filtra per stato
    if filtro == "Solo non mappati":
        conti_df = conti_df[~conti_df[col_cod_piano].astype(str).isin(
            [k for k, v in mapping.items() if v and str(v) != 'nan'])]
    elif filtro == "Solo mappati":
        conti_df = conti_df[conti_df[col_cod_piano].astype(str).isin(
            [k for k, v in mapping.items() if v and str(v) != 'nan'])]

    # Filtra per testo
    if cerca.strip():
        mask_cod = conti_df[col_cod_piano].astype(str).str.contains(cerca, case=False, na=False)
        if col_desc_piano:
            mask_desc = conti_df[col_desc_piano].astype(str).str.contains(cerca, case=False, na=False)
            conti_df = conti_df[mask_cod | mask_desc]
        else:
            conti_df = conti_df[mask_cod]

    if len(conti_df) > 60:
        st.caption(f"Mostrando 60 di {len(conti_df)} conti. Usa i filtri per restringere.")
        conti_df = conti_df.head(60)

    voci_options = ['— Non mappato —'] + [
        f"{cod} — {desc}" for cod, desc in voci_ricl_label.items()
    ]

    # Mapping staging sovrapposto visivamente
    mapping_display = dict(mapping)
    if staging:
        mapping_display.update(staging)

    for _, row in conti_df.iterrows():
        codice = str(row[col_cod_piano])
        desc   = str(row.get(col_desc_piano, '')) if col_desc_piano else ''
        voce_cod = mapping_display.get(codice)

        # Trova label attuale
        if voce_cod and voce_cod in voci_ricl_label:
            label_att = voci_ricl_label[voce_cod]
            full_opt  = f"{voce_cod} — {df_ricl[df_ricl[col_cod_ricl].astype(str)==voce_cod][col_desc_ricl].values[0]}" if col_desc_ricl else voce_cod
            idx = next((i for i, o in enumerate(voci_options) if o.startswith(voce_cod)), 0)
        else:
            idx = 0

        is_from_staging = staging and codice in staging
        dot = "🟡" if is_from_staging else ("🟢" if voce_cod else "🔴")

        col_a, col_b = st.columns([2, 3])
        with col_a:
            staging_hint = " <span style='font-size:0.68rem;color:#D97706;'>(AI)</span>" if is_from_staging else ""
            st.markdown(
                f"<div style='padding:9px 4px; font-size:0.83rem; color:#374151;'>"
                f"{dot} <b>{codice}</b>{staging_hint} &nbsp; {desc}</div>",
                unsafe_allow_html=True
            )
        with col_b:
            sel = st.selectbox("x", voci_options, index=idx,
                               label_visibility="collapsed", key=f"ms_{ca}_{codice}")
            if sel == '— Non mappato —':
                mapping.pop(codice, None)
            else:
                for opt in voci_options[1:]:
                    if sel == opt:
                        cod_sel = opt.split(' — ')[0]
                        mapping[codice] = cod_sel
                        break

    save_cliente({'mapping': mapping})

    st.markdown("---")
    colf1, colf2 = st.columns([1, 4])
    with colf1:
        if st.button("💾 Salva Mappatura", type="primary", key="btn_salva_map"):
            save_cliente({'mapping': mapping, 'mapping_staging': None})
            # Genera CSV esportabile come memory mapping
            rows = [{'codice_conto': k, 'codice_voce_ricl': v} for k, v in mapping.items() if v]
            csv = pd.DataFrame(rows).to_csv(index=False, sep=';').encode('utf-8-sig')
            st.success(f"✅ {len([v for v in mapping.values() if v])} conti mappati")
            st.download_button(
                "⬇️ Esporta Memory Mapping",
                data=csv,
                file_name=f"memory_mapping_{ca}.csv",
                mime="text/csv",
                key="dl_mem"
            )


def _esegui_ai_staging(df_piano, df_ricl, mapping_corrente, full=True):
    """Esegue la mappatura AI e mette il risultato in staging (non sovrascrive)."""
    ca = st.session_state.get('cliente_attivo')
    api_key = st.session_state.get('anthropic_api_key', '')
    if not api_key:
        try:
            import streamlit as st
            api_key = st.secrets.get("ANTHROPIC_API_KEY", "")
        except Exception:
            pass
    if not api_key:
        st.error("⚠️ Configura la API Key Anthropic nel Tab 'API Key'.")
        return

    with st.spinner("🤖 AI in elaborazione... ~20-40 secondi"):
        try:
            if full:
                nuovo = ai_suggest_mapping(df_piano, df_ricl, mapping_corrente)
            else:
                nuovo = ai_suggest_new_accounts(df_piano, df_ricl, mapping_corrente)

            if nuovo:
                save_cliente({'mapping_staging': nuovo})
                st.success(f"✅ AI ha suggerito {len(nuovo)} abbinamenti. Revisionali e accetta.")
                st.rerun()
            else:
                st.warning("L'AI non ha prodotto suggerimenti. Verifica i file caricati.")
        except Exception as e:
            st.error(f"Errore AI: {e}")


def _render_api_tab():
    st.markdown("### 🔑 Configurazione API Anthropic")
    st.markdown("""
    <div class="info-box info-box-amber">
    🔑 La API Key è necessaria per la mappatura AI, Sentinel intelligente e AI CFO.
    Puoi ottenerla su <a href="https://console.anthropic.com" target="_blank">console.anthropic.com</a>.
    In produzione, inseriscila nel file <code>.streamlit/secrets.toml</code>.
    </div>
    """, unsafe_allow_html=True)

    curr = st.session_state.get('anthropic_api_key', '')
    if curr:
        masked = curr[:10] + '...' + curr[-4:]
        st.markdown(f"""
        <div class="info-box info-box-green">
        ✅ API Key configurata: <code>{masked}</code>
        </div>
        """, unsafe_allow_html=True)

    new_key = st.text_input("Inserisci o aggiorna API Key:",
                             type="password", placeholder="sk-ant-api03-...")
    if st.button("Salva", key="btn_salva_apikey") and new_key.strip():
        st.session_state['anthropic_api_key'] = new_key.strip()
        st.success("✅ API Key salvata per questa sessione.")
        st.rerun()

    st.markdown("---")
    st.markdown("### 📋 Secrets.toml (per deploy su Streamlit Cloud)")
    st.code('ANTHROPIC_API_KEY = "sk-ant-api03-la-tua-chiave"', language='toml')
    st.caption("Incolla questo contenuto in: App Settings → Secrets su share.streamlit.io")
