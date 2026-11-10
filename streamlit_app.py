"""
lookup_app.py
Same job as before: type a transaction ID, get an instant fraud
verdict from the API. This version adds the visual design from the
UI enhancement plan: risk-tiered colors, a circular confidence
gauge, color-coded layer pills, a clean detail table, and a
session search history.

Single-file version for Streamlit Cloud: scores straight from the
SQLite DB, no separate API server needed.

Run locally with:
    streamlit run streamlit_app.py
"""

import os
import sqlite3
import streamlit as st
from fraud_scoring import load_models, score_transaction


def _flatten(html):
    """Strip leading whitespace from each line. Without this, Streamlit's
    markdown parser treats indented HTML as a preformatted code block and
    renders it as literal text instead of parsing it."""
    return '\n'.join(line.strip() for line in html.strip().split('\n'))

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fraud_lookup.db')


@st.cache_resource
def get_models():
    """Load both models once per server process, not per click."""
    return load_models()


def fetch_transaction(tx_id):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute('SELECT * FROM transactions WHERE transaction_id = ?', (tx_id,)).fetchone()
    finally:
        conn.close()
    return dict(row) if row else None


@st.cache_data
def sample_ids():
    """A few real IDs (fraud + legit) so visitors can try the app instantly."""
    conn = sqlite3.connect(DB_FILE)
    try:
        fraud = [r[0] for r in conn.execute('SELECT transaction_id FROM transactions WHERE isFraud = 1 LIMIT 3')]
        legit = [r[0] for r in conn.execute('SELECT transaction_id FROM transactions WHERE isFraud = 0 LIMIT 3')]
    finally:
        conn.close()
    return {'fraud': fraud, 'legit': legit}

st.set_page_config(page_title='Fraud Transaction Lookup', layout='centered')

# ── Design tokens ─────────────────────────────────────────────────────────────
COLORS = {
    'high':   {'bg': '#FCEBEB', 'ring_track': '#F7C1C1', 'ring_fill': '#A32D2D', 'text': '#791F1F'},
    'medium': {'bg': '#FAEEDA', 'ring_track': '#FAC775', 'ring_fill': '#854F0B', 'text': '#633806'},
    'low':    {'bg': '#EAF3DE', 'ring_track': '#C0DD97', 'ring_fill': '#3B6D11', 'text': '#27500A'},
    'neutral':{'bg': '#F1EFE8', 'ring_track': '#D3D1C7', 'ring_fill': '#5F5E5A', 'text': '#444441'},
}

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.mono { font-family: 'JetBrains Mono', monospace; }

/* Text input */
div[data-testid="stTextInput"] input {
    border-radius: 10px !important;
    border: 1.5px solid #E2E8F0 !important;
    padding: 0.6rem 0.9rem !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 15px !important;
    transition: border-color 0.15s ease, box-shadow 0.15s ease;
}
div[data-testid="stTextInput"] input:focus {
    border-color: #3730A3 !important;
    box-shadow: 0 0 0 3px rgba(55, 48, 163, 0.12) !important;
}

/* Button */
div.stButton > button, button[kind="primary"], button[kind="formSubmit"] {
    background-color: #3730A3 !important; color: white !important; border: none !important;
    border-radius: 10px !important; padding: 0.55rem 1.4rem !important; font-weight: 600 !important;
    box-shadow: 0 1px 3px rgba(55, 48, 163, 0.25);
    transition: background-color 0.15s ease, transform 0.05s ease;
}
div.stButton > button:hover, button[kind="primary"]:hover, button[kind="formSubmit"]:hover {
    background-color: #2c2582 !important; color: white !important;
}
div.stButton > button:active, button[kind="primary"]:active, button[kind="formSubmit"]:active {
    transform: scale(0.98);
}

/* Result card */
.result-card {
    background: white; border: 1px solid #E2E8F0; border-radius: 14px;
    padding: 1.5rem 1.75rem; margin-top: 1.25rem;
    box-shadow: 0 2px 10px rgba(15, 23, 42, 0.06);
}

/* Layer pills */
.layer-pill {
    border-radius: 10px; padding: 12px 10px; text-align: center;
    transition: transform 0.15s ease;
}
.layer-pill:hover { transform: translateY(-2px); }

/* Detail table */
.detail-table { width: 100%; font-size: 14px; border-collapse: collapse; }
.detail-table td, .detail-table th { border: none !important; padding: 9px 2px !important; }
.detail-table tr { border-bottom: 1px solid #F1F5F9; }
.detail-table tr:last-child { border-bottom: none; }
.detail-label { color: #64748B; font-size: 13px; font-weight: 400; }
.detail-value { text-align: right; font-family: 'JetBrains Mono', monospace; font-size: 14px; font-weight: 500; color: #1E293B; }

/* Sidebar recent-lookup buttons */
[data-testid="stSidebar"] button {
    font-family: 'JetBrains Mono', monospace !important;
    border-radius: 8px !important;
    text-align: left !important;
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ── Session state for search history ────────────────────────────────────────
if 'history' not in st.session_state:
    st.session_state.history = []

# ── Sidebar: search history ─────────────────────────────────────────────────
with st.sidebar:
    st.subheader('Recent lookups')
    if not st.session_state.history:
        st.caption('No lookups yet this session.')
    else:
        for past_id in reversed(st.session_state.history[-10:]):
            if st.button(past_id, key=f'hist_{past_id}', use_container_width=True):
                st.session_state.pending_lookup = past_id
                st.rerun()

    st.subheader('Try an example')
    st.caption('This demo holds a sample of the dataset, so use these IDs.')
    for label, ids in sample_ids().items():
        for ex in ids:
            if st.button(f'{ex}  ({label})', key=f'ex_{ex}', use_container_width=True):
                st.session_state.pending_lookup = ex
                st.rerun()

# ── Header ───────────────────────────────────────────────────────────────────
st.markdown(
    "<div style=\"font-size:clamp(28px, 5vw, 44px); font-weight:700; "
    "line-height:1.15; margin-bottom:4px; white-space:nowrap;\">"
    "🛡️ Fraud Transaction Lookup</div>",
    unsafe_allow_html=True,
)
st.caption('PaySim fraud detection — CSIS 4260')
st.write('Enter a transaction ID to get an instant, 3-layer fraud assessment.')

# ── Input form (Enter-to-submit) ────────────────────────────────────────────
default_value = st.session_state.pop('pending_lookup', '')
with st.form('lookup_form', clear_on_submit=False):
    tx_id = st.text_input('Transaction ID', value=default_value, placeholder='e.g. T00001234')
    submitted = st.form_submit_button('Check Transaction', type='primary')

# ── Helper: reasoning sentence from layers_triggered ────────────────────────
def build_reasoning(result):
    layers = result['layer_detail']
    reasons = []
    if layers['rule_engine']:
        reasons.append('a large transfer drained the origin balance')
    if layers['random_forest']['flagged']:
        reasons.append(f"the model gave it a {layers['random_forest']['probability']*100:.0f}% fraud probability")
    if layers['isolation_forest']['flagged']:
        reasons.append('its pattern looks statistically unusual')
    if not reasons:
        return 'All three layers came back clear.'
    return 'Flagged because ' + '; '.join(reasons) + '.'


def risk_tier(result):
    if not result['is_flagged']:
        return 'low'
    conf = result['confidence']
    if conf >= 0.7:
        return 'high'
    if conf >= 0.4:
        return 'medium'
    return 'low'


def render_gauge_svg(pct, ring_fill, ring_track, text_color):
    circumference = 169.6
    offset = circumference * (1 - pct)
    return f'''
    <svg width="64" height="64" viewBox="0 0 64 64">
      <circle cx="32" cy="32" r="27" fill="none" stroke="{ring_track}" stroke-width="7"></circle>
      <circle cx="32" cy="32" r="27" fill="none" stroke="{ring_fill}" stroke-width="7"
              stroke-linecap="round" stroke-dasharray="{circumference}" stroke-dashoffset="{offset:.1f}"
              transform="rotate(-90 32 32)"></circle>
      <text x="32" y="37" text-anchor="middle" font-size="15" font-weight="500" fill="{text_color}">{pct*100:.0f}%</text>
    </svg>
    '''


def pill_html(label, icon_state_text, active, palette):
    bg = palette['bg'] if active else '#F1EFE8'
    text_color = palette['text'] if active else '#64748B'
    return f'''
    <div class="layer-pill" style="background:{bg};">
        <p style="font-size:12px;color:{text_color};margin:0 0 2px;">{label}</p>
        <p style="font-size:13px;font-weight:500;color:{text_color};margin:0;">{icon_state_text}</p>
    </div>
    '''


# ── Handle submission ────────────────────────────────────────────────────────
if submitted and tx_id:
    clean_id = tx_id.strip()
    with st.spinner('Scoring transaction...'):
        detail = fetch_transaction(clean_id)

    if detail is None:
        st.warning(f'No transaction found with ID "{clean_id}". This demo uses a sample of the dataset, so try an example ID from the sidebar.')
    else:
        if clean_id not in st.session_state.history:
            st.session_state.history.append(clean_id)

        result = score_transaction(detail, get_models())
        tier = risk_tier(result)
        palette = COLORS[tier]
        verdict_text = 'Flagged as suspicious' if result['is_flagged'] else 'No fraud indicators'

        gauge = render_gauge_svg(result['confidence'], palette['ring_fill'], palette['ring_track'], palette['text'])

        rule_active = result['layer_detail']['rule_engine']
        rf_active = result['layer_detail']['random_forest']['flagged']
        iso_active = result['layer_detail']['isolation_forest']['flagged']

        card_html = f'''
        <div class="result-card">
          <div style="display:flex;align-items:center;gap:16px;margin-bottom:16px;">
            {gauge}
            <div>
              <p style="font-size:16px;font-weight:500;color:{palette['text']};margin:0 0 4px;">{verdict_text}</p>
              <p style="font-size:13px;color:#64748B;margin:0;">{build_reasoning(result)}</p>
            </div>
          </div>
          <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:16px;">
            {pill_html('Rule engine', 'Hit' if rule_active else 'Clear', rule_active, palette)}
            {pill_html('Random forest', f"{result['layer_detail']['random_forest']['probability']*100:.0f}%", rf_active, palette)}
            {pill_html('Isolation forest', 'Anomaly' if iso_active else 'Normal', iso_active, palette)}
          </div>
          <div style="border-top:1px solid #E2E8F0;padding-top:12px;">
            <table class="detail-table">
              <tr><td class="detail-label">Type</td><td class="detail-value">{detail.get('type','')}</td></tr>
              <tr><td class="detail-label">Amount</td><td class="detail-value">${detail.get('amount',0):,.2f}</td></tr>
              <tr><td class="detail-label">Old origin balance</td><td class="detail-value">${detail.get('oldbalanceOrg',0):,.2f}</td></tr>
              <tr><td class="detail-label">New origin balance</td><td class="detail-value">${detail.get('newbalanceOrig',0):,.2f}</td></tr>
            </table>
          </div>
        </div>
        '''
        st.markdown(_flatten(card_html), unsafe_allow_html=True)

        if result['actual_label'] is not None:
            st.caption(f"Ground truth in dataset: {'FRAUD' if result['actual_label'] == 1 else 'Legitimate'}")

        with st.expander('View raw JSON'):
            st.json(detail)