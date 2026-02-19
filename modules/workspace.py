"""workspace.py — Caricamento dati, mappatura, import/export."""
import streamlit as st
import pandas as pd
from services.data_utils import smart_load, find_column, get_cliente, save_cliente, get_api_key
from services.riclassifica import get_label_map


# ── Helpers UI ────────────────────────────────────────────────────────────────
def _badge(text, color='#C9A84C', bg='rgba(201,168,76,0.12)'):
    return f"<span style='background:{bg};color:{color};padding:2px 10px;border-radius:4px;font-size:0.72rem;font-weight:700'>{text}</span>"

def _stat_card(col, label, value, color='#F1F5F9'):
    col.markdown(
        f"<div style='background:#0D1625;border:1px solid rgba(255,255,255,0.06);border-radius:12px;"
        f"padding:16px;text-align:center'>"
        f"<div style='font-size:0.65rem;text-transform:uppercase;letter-spacing:1.5px;color:#475569;margin-bottom:6px'>{label}</div>"
        f"<div style='font-size:1.6rem;font-weight:800;color:{color};font-variant-numeric:tabular-nums'>{value}</div>"
        f"</div>", unsafe_allow_html=True)


def render_workspace():
    ca = st.session_state.get('cliente_attivo')
    if not ca:
        st.warning("Seleziona o crea un cliente dalla sidebar."); return

    cliente = get_cliente()

    # Header
    st.markdown(f"""
    <div style='background:linear-gradient(135deg,#0D1625 0%,#0F2044 50%,#0D1625 100%);
                border:1px solid rgba(201,168,76,0.15);border-radius:16px;
                padding:24px 32px;margin-bottom:28px;position:relative;overflow:hidden'>
        <div style='position:absolute;top:0;right:0;width:200px;height:200px;
                    background:radial-gradient(circle,rgba(201,168,76,0.06),transparent 70%)'></div>
        <div style='font-size:9px;text-transform:uppercase;letter-spacing:4px;color:#C9A84C;font-weight:700;margin-bottom:6px'>Workspace</div>
        <div style='font-size:1.5rem;font-weight:800;color:#F1F5F9;letter-spacing:-0.3px'>🗂️ {ca}</div>
        <div style='font-size:0.8rem;color:#475569;margin-top:4px'>Caricamento dati contabili · Mappatura conti · Import/Export</div>
    </div>""", unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["📂 File & Dati", "🔗 Mappatura Conti", "🔑 API Key"])
    with tab1: _render_caricamento(ca, cliente)
    with tab2: _render_mappatura(ca, cliente)
    with tab3: _render_api_tab()


# ── TAB 1: CARICAMENTO ────────────────────────────────────────────────────────
def _render_caricamento(ca, cliente):
    def upload_block(col, num, label, hint, field):
        with col:
            has_data = cliente.get(field) is not None and not cliente[field].empty
            border_c = 'rgba(16,185,129,0.4)' if has_data else 'rgba(255,255,255,0.07)'
            icon = '✅' if has_data else '⬜'
            st.markdown(
                f"<div style='background:#0D1625;border:1px solid {border_c};border-radius:12px;"
                f"padding:16px 20px;margin-bottom:12px'>"
                f"<div style='font-size:0.7rem;font-weight:700;color:#C9A84C;text-transform:uppercase;"
                f"letter-spacing:1px;margin-bottom:8px'>{icon} {num}. {label}</div>"
                f"<div style='font-size:0.75rem;color:#475569;margin-bottom:10px'>{hint}</div>"
                f"</div>", unsafe_allow_html=True)
            f = st.file_uploader(label, type=["csv","xlsx","xls"],
                                  key=f"u_{field}_{ca}", label_visibility="collapsed")
            if f:
                df = smart_load(f)
                if df is not None and not df.empty:
                    save_cliente({field: df})
                    st.success(f"✅ {len(df)} righe caricate")
                    with st.expander("Anteprima"):
                        st.dataframe(df.head(5), use_container_width=True)
                else:
                    st.error("Errore lettura — verifica formato")
            elif has_data:
                df_cur = cliente[field]
                st.markdown(f"<div style='font-size:0.78rem;color:#10B981;padding:4px 0'>📋 {len(df_cur)} righe in memoria</div>",
                            unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    upload_block(c1, "1", "Piano dei Conti",    "Colonne: Codice, Descrizione",    "df_piano")
    upload_block(c2, "2", "DB Contabile",        "Colonne: Data, Conto, Saldo",     "df_db")
    upload_block(c3, "3", "Schema Riclassifica", "Colonne: Codice, Descrizione",    "df_ricl")

    # Status row
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    stati = [
        ("Piano dei Conti", 'df_piano', lambda c: f"{len(c.get('df_piano', pd.DataFrame()))} conti"),
        ("DB Contabile",    'df_db',    lambda c: f"{len(c.get('df_db',    pd.DataFrame()))} movimenti"),
        ("Schema Ricl.",    'df_ricl',  lambda c: f"{len(c.get('df_ricl',  pd.DataFrame()))} voci"),
    ]
    cols = st.columns(3)
    for i, (nome, field, det_fn) in enumerate(stati):
        ok = cliente.get(field) is not None and not cliente[field].empty
        color = '#10B981' if ok else '#F59E0B'
        detail = det_fn(cliente) if ok else 'Non caricato'
        _stat_card(cols[i], nome, detail if ok else '—', color)


# ── TAB 2: MAPPATURA ──────────────────────────────────────────────────────────
def _render_mappatura(ca, cliente):
    df_piano = cliente.get('df_piano')
    df_ricl  = cliente.get('df_ricl')

    if df_piano is None or df_ricl is None:
        st.warning("⚠️ Carica prima Piano dei Conti e Schema Riclassifica.")
        return

    col_cod_piano  = find_column(df_piano, ['Codice','codice','CodConto','Conto','conto','ID','cod'])
    col_desc_piano = find_column(df_piano, ['Descrizione','descrizione','Nome','nome','Conto','conto'])
    col_cod_ricl   = find_column(df_ricl,  ['Codice','codice','ID','id','Voce','voce'])
    col_desc_ricl  = find_column(df_ricl,  ['Descrizione','descrizione','Nome','nome','Voce','voce'])

    if not col_cod_piano:
        st.error(f"Colonna Codice non trovata nel piano. Colonne: {list(df_piano.columns)[:8]}"); return
    if not col_cod_ricl:
        st.error(f"Colonna Codice non trovata nello schema. Colonne: {list(df_ricl.columns)[:8]}"); return

    label_map = get_label_map(df_ricl)

    # Opzioni dropdown
    voci_options = ['— Non mappato —']
    desc_to_cod  = {}
    for _, row in df_ricl.iterrows():
        cod  = str(row[col_cod_ricl]).strip()
        desc = str(row[col_desc_ricl]).strip() if col_desc_ricl and col_desc_ricl != col_cod_ricl else cod
        if desc.lower() in ('nan','none','') or cod.lower() in ('nan','none',''): continue
        voci_options.append(desc)
        desc_to_cod[desc] = cod

    # ── LEGGI MAPPING DIRETTAMENTE DA SESSION STATE ────────────────────────
    # CRITICO: non usare cliente.get('mapping') perché è una copia — modifiche si perdono
    def _get_mapping():
        ca_ = st.session_state.get('cliente_attivo')
        return st.session_state.get('clienti', {}).get(ca_, {}).get('mapping', {})

    def _set_mapping(m):
        ca_ = st.session_state.get('cliente_attivo')
        if ca_ and ca_ in st.session_state.get('clienti', {}):
            st.session_state['clienti'][ca_]['mapping'] = m

    mapping = _get_mapping()

    n_tot     = len(df_piano)
    n_mappati = len([v for v in mapping.values() if v])
    pct       = n_mappati / n_tot * 100 if n_tot > 0 else 0

    # Stat cards
    cols4 = st.columns(4)
    _stat_card(cols4[0], "Totale Conti",    str(n_tot),                '#F1F5F9')
    _stat_card(cols4[1], "Mappati",         str(n_mappati),            '#10B981')
    _stat_card(cols4[2], "Da mappare",      str(n_tot - n_mappati),    '#F59E0B')
    _stat_card(cols4[3], "Completamento",   f"{pct:.0f}%",             '#C9A84C')

    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
    st.progress(pct / 100)

    # ── IMPORT / EXPORT ────────────────────────────────────────────────────
    with st.expander("📥 Import / Export Mappatura", expanded=(n_mappati == 0)):
        c_imp, c_exp = st.columns(2)

        with c_imp:
            st.markdown("<div style='font-size:0.82rem;color:#E2E8F0;font-weight:600;margin-bottom:6px'>Importa da CSV/Excel</div>", unsafe_allow_html=True)
            st.caption("Colonne richieste: **Codice** · **VoceCodice**")
            f_import = st.file_uploader("Import mappatura", type=["csv","xlsx","xls"],
                                         key=f"imp_map_{ca}", label_visibility="collapsed")
            if f_import:
                df_imp = smart_load(f_import)
                if df_imp is not None and not df_imp.empty:
                    col_c = find_column(df_imp, ['Codice','codice','CodConto','conto'])
                    col_v = find_column(df_imp, ['VoceCodice','voce_codice','CodiceVoce','Voce','voce','Mapping'])
                    if col_c and col_v:
                        m = dict(mapping)
                        nuovi = 0
                        for _, row in df_imp.iterrows():
                            conto = str(row[col_c]).strip()
                            voce  = str(row[col_v]).strip()
                            if conto and voce and voce.lower() not in ('nan','none',''):
                                m[conto] = voce
                                nuovi += 1
                        _set_mapping(m)
                        st.success(f"✅ {nuovi} mapping importati")
                        st.rerun()
                    else:
                        st.error(f"Colonne non trovate. Trovate: {list(df_imp.columns)}")

        with c_exp:
            st.markdown("<div style='font-size:0.82rem;color:#E2E8F0;font-weight:600;margin-bottom:6px'>Esporta / Template</div>", unsafe_allow_html=True)
            # Template vuoto
            tpl_rows = []
            for _, row in df_piano.iterrows():
                c_ = str(row[col_cod_piano]).strip()
                d_ = str(row.get(col_desc_piano,'')) if col_desc_piano else ''
                tpl_rows.append({'Codice': c_, 'DescrizioneConto': d_,
                                  'VoceCodice': mapping.get(c_,''), 'DescrizioneVoce': label_map.get(mapping.get(c_,''),'')})
            df_tpl = pd.DataFrame(tpl_rows)
            csv_tpl = df_tpl.to_csv(index=False, sep=';', decimal=',').encode('utf-8-sig')
            st.download_button("📋 Template / Export attuale", data=csv_tpl,
                               file_name=f"mappatura_{ca}.csv", mime="text/csv",
                               use_container_width=True)
            st.caption("Il file include la mappatura attuale. Compilalo e re-importalo.")

    # ── AI MAPPING ────────────────────────────────────────────────────────
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    st.markdown("<div style='font-size:0.82rem;font-weight:700;color:#C9A84C;text-transform:uppercase;letter-spacing:1px;margin-bottom:8px'>🤖 Mappatura AI</div>", unsafe_allow_html=True)
    c_ai1, c_ai2 = st.columns(2)
    with c_ai1:
        if st.button("🤖 Mappa TUTTI con AI", use_container_width=True):
            _run_ai_mapping(df_piano, df_ricl, mapping, full=True, set_fn=_set_mapping)
    with c_ai2:
        n_nuovi = n_tot - n_mappati
        if st.button(f"✨ Mappa {n_nuovi} non mappati (AI)", use_container_width=True, disabled=(n_nuovi == 0)):
            _run_ai_mapping(df_piano, df_ricl, mapping, full=False, set_fn=_set_mapping)

    # ── REVISIONE MANUALE ─────────────────────────────────────────────────
    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    st.markdown("<div style='font-size:0.82rem;font-weight:700;color:#C9A84C;text-transform:uppercase;letter-spacing:1px;margin-bottom:8px'>✏️ Revisione Manuale</div>", unsafe_allow_html=True)

    col_f1, col_f2, col_f3 = st.columns([2, 2, 3])
    with col_f1:
        filtro = st.radio("", ["Tutti", "Non mappati", "Mappati"], horizontal=True,
                           key="filt_map", label_visibility="collapsed")
    with col_f2:
        cerca = st.text_input("", placeholder="🔍 Cerca conto…",
                               key="cerca_conto_ws", label_visibility="collapsed")
    with col_f3:
        st.caption(f"🟢 {n_mappati} mappati · 🔴 {n_tot - n_mappati} da mappare")

    conti_df = df_piano.copy()
    mappati_set = {k for k, v in mapping.items() if v}
    if filtro == "Non mappati":
        conti_df = conti_df[~conti_df[col_cod_piano].astype(str).isin(mappati_set)]
    elif filtro == "Mappati":
        conti_df = conti_df[conti_df[col_cod_piano].astype(str).isin(mappati_set)]
    if cerca:
        q = cerca.lower()
        mask = conti_df[col_cod_piano].astype(str).str.lower().str.contains(q, na=False)
        if col_desc_piano and col_desc_piano != col_cod_piano:
            mask = mask | conti_df[col_desc_piano].astype(str).str.lower().str.contains(q, na=False)
        conti_df = conti_df[mask]

    if len(conti_df) > 100:
        st.info(f"Mostro 100/{len(conti_df)} conti. Usa il filtro per restringere.")
        conti_df = conti_df.head(100)

    # Header colonne
    h1, h2, h3 = st.columns([2, 1, 3])
    for col, txt in [(h1,"Conto"), (h2,"Stato"), (h3,"Voce Riclassifica")]:
        col.markdown(f"<div style='font-size:0.68rem;font-weight:700;color:#475569;text-transform:uppercase;"
                     f"letter-spacing:1px;padding:6px 4px;border-bottom:1px solid rgba(255,255,255,0.06)'>{txt}</div>",
                     unsafe_allow_html=True)

    # CRITICO: ogni selectbox aggiorna DIRETTAMENTE session_state tramite on_change
    for _, row in conti_df.iterrows():
        codice = str(row[col_cod_piano]).strip()
        desc   = str(row.get(col_desc_piano, '')).strip() if col_desc_piano and col_desc_piano != col_cod_piano else ''

        cod_att  = mapping.get(codice)
        desc_att = label_map.get(str(cod_att), str(cod_att)) if cod_att else None
        idx      = (voci_options.index(desc_att) if desc_att and desc_att in voci_options else 0)

        col_a, col_b, col_c = st.columns([2, 1, 3])
        with col_a:
            trunc = (desc[:40] + '…') if len(desc) > 40 else desc
            st.markdown(
                f"<div style='padding:8px 4px;font-size:0.82rem'>"
                f"<b style='color:#CBD5E1'>{codice}</b>"
                f"<span style='color:#475569;font-size:0.76rem'> {trunc}</span></div>",
                unsafe_allow_html=True)
        with col_b:
            dot = "🟢" if cod_att else "🔴"
            st.markdown(f"<div style='padding:8px 4px;text-align:center;font-size:1rem'>{dot}</div>",
                        unsafe_allow_html=True)
        with col_c:
            sel_key = f"mmap_{ca}_{codice}"
            sel = st.selectbox("", voci_options, index=idx,
                               label_visibility="collapsed", key=sel_key)
            # Aggiorna mapping direttamente in session_state ad ogni interazione
            current_map = _get_mapping()
            if sel == '— Non mappato —':
                current_map.pop(codice, None)
            else:
                current_map[codice] = desc_to_cod.get(sel, sel)
            _set_mapping(current_map)

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    if st.button("💾 Salva Mappatura", type="primary", use_container_width=False):
        final_map = _get_mapping()
        save_cliente({'mapping': final_map})
        n_ok = len([v for v in final_map.values() if v])
        st.success(f"✅ {n_ok} conti mappati salvati")


# ── TAB 3: API KEY ────────────────────────────────────────────────────────────
def _render_api_tab():
    st.markdown("### 🔑 Chiave API Anthropic")
    st.markdown("""
    <div style='background:rgba(245,158,11,0.08);border-left:3px solid #F59E0B;
                border-radius:0 10px 10px 0;padding:14px 18px;font-size:0.83rem;
                color:#94A3B8;margin-bottom:20px'>
    Necessaria per <b style='color:#E2E8F0'>mappatura AI</b> e <b style='color:#E2E8F0'>CFO Agent</b>.
    Ottienila su <a href='https://console.anthropic.com' target='_blank' style='color:#C9A84C'>console.anthropic.com</a>
    </div>""", unsafe_allow_html=True)

    current = st.session_state.get('anthropic_api_key', '')
    if not current:
        try:
            current = st.secrets.get('ANTHROPIC_API_KEY', '')
            if current: st.session_state['anthropic_api_key'] = current
        except Exception: pass

    if current:
        masked = current[:12] + '•' * 16 + current[-4:]
        st.markdown(f"<div style='color:#10B981;font-size:0.85rem;margin-bottom:12px'>✅ Attiva: <code style='color:#10B981'>{masked}</code></div>",
                    unsafe_allow_html=True)
    else:
        st.markdown("<div style='color:#EF4444;font-size:0.85rem;margin-bottom:12px'>🔴 Non configurata</div>",
                    unsafe_allow_html=True)

    new_key = st.text_input("Inserisci API Key:", type="password", placeholder="sk-ant-api03-…", key="ws_api_key_input")
    if st.button("Salva", type="primary") and new_key.strip():
        st.session_state['anthropic_api_key'] = new_key.strip()
        st.success("✅ Salvata")
        st.rerun()

    with st.expander("ℹ️ Configurazione permanente"):
        st.code('# .streamlit/secrets.toml\nANTHROPIC_API_KEY = "sk-ant-api03-..."', language="toml")


# ── AI MAPPING ────────────────────────────────────────────────────────────────
def _run_ai_mapping(df_piano, df_ricl, mapping_corrente, full=True, set_fn=None):
    api_key = get_api_key()
    if not api_key:
        st.error("Configura prima la API Key nel tab '🔑 API Key'."); return
    with st.spinner("🤖 Claude sta analizzando i conti…"):
        try:
            from services.ai_mapper import ai_suggest_mapping, ai_suggest_new_accounts
            nuovo = ai_suggest_mapping(df_piano, df_ricl, mapping_corrente) if full \
                    else ai_suggest_new_accounts(df_piano, df_ricl, mapping_corrente)
            m = dict(mapping_corrente)
            m.update(nuovo)
            if set_fn: set_fn(m)
            save_cliente({'mapping': m})
            st.success(f"✅ {len([v for v in nuovo.values() if v])} conti mappati")
            st.rerun()
        except Exception as e:
            err = str(e)
            if '401' in err or 'invalid x-api-key' in err.lower():
                st.error("🔑 API Key non valida.")
            else:
                st.error(f"Errore: {err}")
