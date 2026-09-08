import re
import requests
import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px

# ----------------- CONFIGURASI HALAMAN -----------------
st.set_page_config(
    page_title="Executive Dashboard - Sumbang Saran",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling CSS (Modern Glassmorphism, Micro-Interactions, Adaptif Dark/Light Mode)
st.markdown("""
    <style>
    /* Google Fonts Import */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }

    /* Gradient Hero Banner */
    .hero-container {
        background: linear-gradient(135deg, #1e1b4b 0%, #312e81 50%, #4338ca 100%);
        padding: 28px 32px;
        border-radius: 20px;
        color: #ffffff;
        margin-bottom: 24px;
        box-shadow: 0 20px 25px -5px rgba(49, 46, 129, 0.25);
        border: 1px solid rgba(255, 255, 255, 0.1);
        position: relative;
        overflow: hidden;
    }
    
    .hero-title {
        font-size: 2rem !important;
        font-weight: 800 !important;
        letter-spacing: -0.025em;
        color: #ffffff !important;
        margin: 0 !important;
    }

    .hero-subtitle {
        font-size: 0.95rem;
        color: #c7d2fe;
        margin-top: 6px;
        font-weight: 400;
    }

    /* Executive Executive Box */
    .executive-box {
        background: var(--background-secondary-color, rgba(255, 255, 255, 0.03));
        border-left: 6px solid #6366f1;
        border-radius: 16px;
        padding: 20px 24px;
        margin-bottom: 24px;
        backdrop-filter: blur(10px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05);
        border-top: 1px solid rgba(128, 128, 128, 0.1);
        border-right: 1px solid rgba(128, 128, 128, 0.1);
        border-bottom: 1px solid rgba(128, 128, 128, 0.1);
    }

    /* Metric Cards Modern Styling */
    .metric-card {
        background: var(--background-secondary-color, rgba(255, 255, 255, 0.03));
        border-radius: 18px;
        padding: 22px;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05);
        border: 1px solid rgba(128, 128, 128, 0.15);
        position: relative;
        overflow: hidden;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    .metric-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
    }

    /* Card Glow Lines Top */
    .metric-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 4px;
        background: linear-gradient(90deg, #6366f1, #818cf8);
    }
    .metric-card.close::before { background: linear-gradient(90deg, #10b981, #34d399); }
    .metric-card.open::before { background: linear-gradient(90deg, #f59e0b, #fbbf24); }
    .metric-card.notreg::before { background: linear-gradient(90deg, #ef4444, #f87171); }

    .metric-title {
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        opacity: 0.7;
    }
    .metric-value {
        font-size: 2.1rem;
        font-weight: 800;
        margin-top: 8px;
        letter-spacing: -0.02em;
    }
    .metric-sub {
        font-size: 0.8rem;
        margin-top: 6px;
        opacity: 0.7;
        display: flex;
        align-items: center;
        gap: 4px;
    }

    /* Chart Container Modern */
    .chart-card {
        background: var(--background-secondary-color, rgba(255, 255, 255, 0.03));
        border-radius: 20px;
        padding: 22px;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05);
        border: 1px solid rgba(128, 128, 128, 0.12);
        margin-bottom: 24px;
    }

    /* Custom Title Inside Cards */
    .card-header-title {
        font-size: 1rem;
        font-weight: 700;
        margin-bottom: 14px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    </style>
""", unsafe_allow_html=True)

# ----------------- CONSTANTS & UTILS -----------------
SHEET_URL_DATA = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRoRFG_w4aDY6_umLj3VOE7Tt_lswjQp2Lz0UOpTXAVCBXt97CEOU1x_bqS_Qeu4Q/pub?gid=654391933&single=true&output=csv"
SHEET_URL_TARGET = "https://docs.google.com/spreadsheets/d/1msjcr5f3WIMvKpW9jJU52Jns-V5Xx3VM/export?format=csv&gid=507573436"

def clean_str(val):
    if pd.isna(val) or val is None: return ""
    return re.sub(r'[^a-zA-Z0-9]', '', str(val)).upper().strip()

def excel_col_to_index(col):
    col = col.upper()
    idx = 0
    for char in col: idx = idx * 26 + (ord(char) - ord('A') + 1)
    return idx - 1

def is_flexible_match(filter_val, target_clean):
    if filter_val == 'ALL' or not filter_val or not target_clean: return True
    f, t = clean_str(filter_val), clean_str(target_clean)
    if f == t: return True
    if '/' in f or '/' in t:
        parts_f = set(filter(None, f.split('/')))
        parts_t = set(filter(None, t.split('/')))
        return len(parts_f.intersection(parts_t)) > 0
    return (f in t) or (t in f)

def clean_num(val):
    if pd.isna(val) or val is None or val == '': return 0.0
    val_str = re.sub(r'[^0-9.]', '', str(val).strip().replace(',', '.'))
    try: return float(val_str)
    except ValueError: return 0.0

@st.cache_data(ttl=60)
def load_csv_generic(url):
    try:
        df = pd.read_csv(url, header=None, dtype=str)
        return df.values.tolist()
    except Exception as e:
        st.error(f"Gagal mengunduh data dari URL: {e}")
        return []

# Dynamic Modern Plotly Chart Styling
def make_styled_combo_chart(categories, target_vals, actual_vals, title):
    fig = go.Figure()
    
    # Modern Gradient Bar
    fig.add_trace(go.Bar(
        x=categories, y=actual_vals, name='Aktual', 
        marker=dict(
            color='#6366f1',
            line=dict(color='#4f46e5', width=1)
        ), 
        opacity=0.9, 
        text=actual_vals, textposition='auto'
    ))
    
    # Glowing Line Target
    fig.add_trace(go.Scatter(
        x=categories, y=target_vals, name='Target', mode='lines+markers+text',
        line=dict(color='#f59e0b', width=3, shape='spline'), 
        marker=dict(size=8, color='#fbbf24', line=dict(color='#d97706', width=2)),
        text=target_vals, textposition='top center'
    ))
    
    fig.update_layout(
        title=dict(text=f"<b>{title}</b>", font=dict(size=14, family='Plus Jakarta Sans')),
        margin=dict(l=15, r=15, t=45, b=15), 
        height=330,
        paper_bgcolor='rgba(0,0,0,0)', 
        plot_bgcolor='rgba(0,0,0,0)',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis=dict(showgrid=False), 
        yaxis=dict(showgrid=True, gridcolor='rgba(128, 128, 128, 0.15)')
    )
    return fig

# ----------------- HEADER HERO BANNER -----------------
head_col1, head_col2 = st.columns([3.5, 1])
with head_col1:
    st.markdown("""
        <div class="hero-container">
            <h1 class="hero-title">⚡ Executive Dashboard Sumbang Saran</h1>
            <div class="hero-subtitle">Real-time Performance Metrics & Operational Improvement Analytics</div>
        </div>
    """, unsafe_allow_html=True)
with head_col2:
    st.write("")
    if st.button("🔄 Sync Real-Time Data", use_container_width=True):
        st.cache_data.clear()

# ----------------- DATA LOADING & PARSING -----------------
raw_data_rows = load_csv_generic(SHEET_URL_DATA)
raw_target_rows = load_csv_generic(SHEET_URL_TARGET)

df_raw, headers = [], []
col_al_index = excel_col_to_index('AL')

if raw_data_rows:
    header_idx = 0
    for idx, row in enumerate(raw_data_rows):
        row_str = [str(val).lower().strip() for val in row]
        if any('nama' in item for item in row_str) and any(re.search(r'(dept|department|departement|bagian)', item) for item in row_str):
            header_idx = idx; break

    headers = [str(h).strip() for h in raw_data_rows[header_idx]]
    for i in range(header_idx + 1, len(raw_data_rows)):
        current_row = raw_data_rows[i]
        if any(current_row):
            row_assoc = {col_name: current_row[col_idx] if col_idx < len(current_row) else '' for col_idx, col_name in enumerate(headers)}
            val_al = current_row[col_al_index].strip() if col_al_index < len(current_row) and current_row[col_al_index] else ''
            if not val_al:
                for h_key, h_val in row_assoc.items():
                    if h_key.upper() == 'AL' or 'line' in h_key.lower():
                        val_al = str(h_val).strip()
                        if val_al: break
            row_assoc['__COL_AL_LINE__'] = val_al
            df_raw.append(row_assoc)

col_status, col_tahapan, col_dept, col_bulan = None, None, None, None
if headers:
    for c in headers:
        c_lower = c.lower()
        if not col_status and 'status' in c_lower and 'tahap' not in c_lower and 'ide' not in c_lower: col_status = c
        if not col_tahapan and ('tahap' in c_lower or 'aktivitas' in c_lower): col_tahapan = c
        if not col_dept and re.search(r'(dept|department|departement|departemen|divisi)', c_lower): col_dept = c
        if not col_bulan and any(k in c_lower for k in ['bulan', 'tgl', 'tanggal', 'daftar']): col_bulan = c

line_targets_3m = []
current_dept = ''
if raw_target_rows:
    header_row = raw_target_rows[0]
    idx_dept, idx_line, idx_m1, idx_m2, idx_m3 = 0, 1, 2, 3, 4
    for col_i, cell in enumerate(header_row):
        cell_l = str(cell).lower().strip()
        if 'dept' in cell_l: idx_dept = col_i
        if 'line' in cell_l or 'bagian' in cell_l: idx_line = col_i
        if 'bulan 1' in cell_l or cell_l == 'm1': idx_m1 = col_i
        if 'bulan 2' in cell_l or cell_l == 'm2': idx_m2 = col_i
        if 'bulan 3' in cell_l or cell_l == 'm3': idx_m3 = col_i

    for row in raw_target_rows[1:]:
        dept_val = str(row[idx_dept]).strip() if idx_dept < len(row) and row[idx_dept] else ''
        line_val = str(row[idx_line]).strip() if idx_line < len(row) and row[idx_line] else ''
        if dept_val and dept_val.lower() not in ['dept', 'department', 'departemen']: current_dept = dept_val
        if line_val:
            line_targets_3m.append({
                'dept': current_dept, 'line': line_val,
                'clean_dept': clean_str(current_dept), 'clean_line': clean_str(line_val),
                'cum_m1': clean_num(row[idx_m1] if idx_m1 < len(row) else ''),
                'cum_m2': clean_num(row[idx_m2] if idx_m2 < len(row) else ''),
                'cum_m3': clean_num(row[idx_m3] if idx_m3 < len(row) else '')
            })

# ----------------- SIDEBAR FILTERS -----------------
st.sidebar.markdown("### 🎛️ Filter Parameters")
opt_depts, opt_lines, opt_statuses = {}, {}, {}
for t in line_targets_3m:
    if t['dept']: opt_depts[t['clean_dept']] = t['dept']
for r in df_raw:
    if col_dept and str(r.get(col_dept, '')).strip(): opt_depts[clean_str(r[col_dept])] = str(r[col_dept]).strip()
    val_al = str(r.get('__COL_AL_LINE__', '')).strip()
    if val_al: opt_lines[clean_str(val_al)] = val_al
    if col_status and str(r.get(col_status, '')).strip(): opt_statuses[clean_str(r[col_status])] = str(r[col_status]).strip()

filter_dept = st.sidebar.selectbox("Departemen", ["ALL"] + list(dict(sorted(opt_depts.items())).keys()), format_func=lambda x: "Semua Departemen" if x == "ALL" else opt_depts[x])
filter_line = st.sidebar.selectbox("Line / Section", ["ALL"] + list(dict(sorted(opt_lines.items())).keys()), format_func=lambda x: "Semua Line/Section" if x == "ALL" else opt_lines[x])
filter_status = st.sidebar.selectbox("Status Ide", ["ALL"] + list(dict(sorted(opt_statuses.items())).keys()), format_func=lambda x: "Semua Status" if x == "ALL" else opt_statuses[x])

df_clean = [row for row in df_raw if 
    (filter_dept == 'ALL' or not col_dept or is_flexible_match(filter_dept, clean_str(row.get(col_dept, '')))) and
    (filter_line == 'ALL' or is_flexible_match(filter_line, clean_str(row.get('__COL_AL_LINE__', '')))) and
    (filter_status == 'ALL' or not col_status or is_flexible_match(filter_status, clean_str(row.get(col_status, ''))))
]

# ----------------- KPI METRICS -----------------
total_all = len(df_clean)
cnt_close, cnt_open, cnt_notreg = 0, 0, 0
if col_status:
    for row in df_clean:
        val = clean_str(row.get(col_status, ''))
        if val == 'CLOSE': cnt_close += 1
        elif val == 'OPEN': cnt_open += 1
        elif 'NOT' in val: cnt_notreg += 1

rate_close = (cnt_close / total_all * 100) if total_all > 0 else 0

# ----------------- EXECUTIVE SUMMARY NARATIF -----------------
st.markdown(f"""
    <div class="executive-box">
        <div style="font-size: 1.1rem; font-weight: 700; display: flex; align-items: center; gap: 8px;">
            📌 Executive Health Summary
        </div>
        <div style="font-size: 0.92rem; margin-top: 8px; opacity: 0.9; line-height: 1.6;">
            • Total <b>{total_all:,} usulan ide</b> telah berhasil dihimpun dari seluruh divisi.<br>
            • Tingkat eksekusi selesai (*Completion Rate*) berada di angka <b>{rate_close:.1f}%</b> dengan total <b>{cnt_close} ide terimplementasi</b>.<br>
            • Diperlukan eskalasi pada <b>{cnt_open} ide berstatus Open</b> dan <b>{cnt_notreg} ide Not Registered</b> untuk mempercepat efisiensi operasional.
        </div>
    </div>
""", unsafe_allow_html=True)

# KPI Cards Line Up
kpi1, kpi2, kpi3, kpi4 = st.columns(4)

kpi1.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">💡 Total Ide Masuk</div>
        <div class="metric-value">{total_all:,}</div>
        <div class="metric-sub">Usulan Terdaftar</div>
    </div>
""", unsafe_allow_html=True)

kpi2.markdown(f"""
    <div class="metric-card close">
        <div class="metric-title" style="color: #10b981;">✅ Status Close</div>
        <div class="metric-value">{cnt_close:,}</div>
        <div class="metric-sub">Penyelesaian {rate_close:.1f}%</div>
    </div>
""", unsafe_allow_html=True)

kpi3.markdown(f"""
    <div class="metric-card open">
        <div class="metric-title" style="color: #f59e0b;">⏳ Status Open</div>
        <div class="metric-value">{cnt_open:,}</div>
        <div class="metric-sub">Dalam Review/Proses</div>
    </div>
""", unsafe_allow_html=True)

kpi4.markdown(f"""
    <div class="metric-card notreg">
        <div class="metric-title" style="color: #ef4444;">⚠️ Not Registered</div>
        <div class="metric-value">{cnt_notreg:,}</div>
        <div class="metric-sub">Perlu Follow-up</div>
    </div>
""", unsafe_allow_html=True)

st.write("")

# ----------------- MODUL LEADERBOARD & BOTTLENECK -----------------
col_lead, col_pie, col_bot = st.columns([1.1, 1, 1.1])

with col_lead:
    st.markdown('<div class="chart-card">', unsafe_allow_html=True)
    st.markdown('<div class="card-header-title">🏆 Top 5 Contributor Karyawan</div>', unsafe_allow_html=True)
    col_nama = next((c for c in headers if 'nama' in c.lower()), None)
    if col_nama and df_clean:
        df_lb = pd.DataFrame(df_clean)[col_nama].value_counts().reset_index().head(5)
        df_lb.columns = ["Nama Karyawan", "Jumlah Ide"]
        st.dataframe(df_lb, use_container_width=True, hide_index=True)
    else:
        st.info("Data kontributor tidak tersedia.")
    st.markdown('</div>', unsafe_allow_html=True)

with col_pie:
    st.markdown('<div class="chart-card">', unsafe_allow_html=True)
    if col_status and df_clean:
        df_st = pd.DataFrame(df_clean)[col_status].value_counts().reset_index()
        df_st.columns = ["Status", "Jumlah"]
        fig_pie = px.pie(
            df_st, names="Status", values="Jumlah", hole=0.6,
            color_discrete_sequence=['#10b981', '#f59e0b', '#ef4444', '#6366f1']
        )
        fig_pie.update_layout(
            title="<b>Proporsi Status</b>", 
            margin=dict(l=10, r=10, t=35, b=10), 
            height=205,
            paper_bgcolor='rgba(0,0,0,0)', 
            plot_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("Data status tidak tersedia.")
    st.markdown('</div>', unsafe_allow_html=True)

with col_bot:
    st.markdown('<div class="chart-card">', unsafe_allow_html=True)
    st.markdown('<div class="card-header-title">⚠️ Bottleneck Area (Ide Open)</div>', unsafe_allow_html=True)
    df_open_only = [r for r in df_clean if clean_str(r.get(col_status, '')) == 'OPEN']
    if df_open_only:
        df_bot = pd.DataFrame(df_open_only)['__COL_AL_LINE__'].value_counts().reset_index().head(5)
        df_bot.columns = ["Line / Section", "Pending"]
        st.dataframe(df_bot, use_container_width=True, hide_index=True)
    else:
        st.success("Tidak ada ide terpending pada area ini.")
    st.markdown('</div>', unsafe_allow_html=True)

# ----------------- PROCESSING TARGET & DATA GRAFIK -----------------
months_display = ["September", "October", "November", "December", "January", "February", "March", "April", "May", "June", "July", "August"]
sum_m1, sum_m2, sum_m3 = 0.0, 0.0, 0.0

for t in line_targets_3m:
    if filter_line != 'ALL':
        if filter_line == t['clean_line'] or filter_line in t['clean_line'] or t['clean_line'] in filter_line:
            sum_m1 += t['cum_m1']; sum_m2 += t['cum_m2']; sum_m3 += t['cum_m3']
    else:
        if is_flexible_match(filter_dept, t['clean_dept']):
            sum_m1 += t['cum_m1']; sum_m2 += t['cum_m2']; sum_m3 += t['cum_m3']

delta1, delta2, delta3 = sum_m1, max(0.0, sum_m2 - sum_m1), max(0.0, sum_m3 - sum_m2)
monthly_increments = [delta1, delta2, delta3] * 4

target_p1, running_target = [], 0.0
for inc in monthly_increments:
    running_target += inc
    target_p1.append(int(round(running_target)))

target_p5 = [0]*2 + target_p1[:-2]
act_p1, act_p5 = [0]*12, [0]*12
month_map = {9:0, 10:1, 11:2, 12:3, 1:4, 2:5, 3:6, 4:7, 5:8, 6:9, 7:10, 8:11}

for row in df_clean:
    b_val = str(row.get(col_bulan, '')).strip().lower() if col_bulan else ''
    st_val = clean_str(row.get(col_status, '')) if col_status else ''
    m_num = None
    for pattern, m in [('sep|09|9/',9), ('okt|oct|10/',10), ('nov|11/',11), ('des|dec|12/',12), ('jan|01/|1/',1), ('feb|02/|2/',2), ('mar|03/|3/',3), ('apr|04/|4/',4), ('mei|may|05/|5/',5), ('jun|06/|6/',6), ('jul|07/|7/',7), ('agu|aug|08/|8/',8)]:
        if re.search(pattern, b_val):
            m_num = m; break
    if m_num in month_map:
        idx = month_map[m_num]
        act_p1[idx] += 1
        if st_val == 'CLOSE': act_p5[idx] += 1

# ----------------- TABS SETUP & VISUALISASI -----------------
tab_overview, tab_details = st.tabs(["📈 Dynamic Visual Analytics", "📋 Detailed Performance Breakdown"])

with tab_overview:
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.plotly_chart(make_styled_combo_chart(months_display, target_p1, act_p1, "1. Akumulasi Total Ide Terdaftar vs Target"), use_container_width=True)
        tot_act_p1 = sum(act_p1)
        tot_tgt_p1 = target_p1[-1] if target_p1 else 0
        gap_p1 = tot_act_p1 - tot_tgt_p1
        p1_status = "melampaui target" if gap_p1 >= 0 else f"kurang {abs(gap_p1)} ide"
        st.info(f"📌 **Insight:** Total terdaftar **{tot_act_p1} ide** dari target tahunan **{tot_tgt_p1} ide** ({p1_status}).")
        st.markdown('</div>', unsafe_allow_html=True)

    with c2:
        steps = ["Pengajuan Ide", "Persetujuan Ide", "Registrasi Ide", "Pengerjaan Ide", "Pembuatan Laporan", "Penilaian", "Pencairan Dana"]
        target_p2 = [0, 0, target_p1[2], 0, 0, 0, 0]
        act_p2 = [0] * len(steps)
        if col_tahapan:
            for row in df_clean:
                t_val = str(row.get(col_tahapan, '')).strip().lower()
                for s_idx, s_name in enumerate(steps):
                    if s_name[:5].lower() in t_val: act_p2[s_idx] += 1
        
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.plotly_chart(make_styled_combo_chart(steps, target_p2, act_p2, "2. Sebaran Ide per Tahapan Workflow SS"), use_container_width=True)
        max_step_idx = int(np.argmax(act_p2)) if max(act_p2) > 0 else 0
        st.info(f"📌 **Insight:** Konsentrasi ide terbanyak saat ini berada pada tahap **{steps[max_step_idx]}** ({act_p2[max_step_idx]} ide).")
        st.markdown('</div>', unsafe_allow_html=True)

    c3, c4 = st.columns(2)
    with c3:
        dept_targets, dept_actuals = {}, {}
        for t in line_targets_3m:
            if filter_dept == 'ALL' or is_flexible_match(filter_dept, t['clean_dept']):
                d_label = t['dept']
                dept_targets[d_label] = dept_targets.get(d_label, 0) + int(round(t['cum_m3'] * 4))
                dept_actuals[d_label] = dept_actuals.get(d_label, 0)
        if col_dept:
            for row in df_clean:
                d_code = clean_str(row.get(col_dept, ''))
                for d_label in dept_targets.keys():
                    if is_flexible_match(clean_str(d_label), d_code):
                        dept_actuals[d_label] += 1; break
        
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.plotly_chart(make_styled_combo_chart(list(dept_targets.keys()), list(dept_targets.values()), list(dept_actuals.values()), "3. Perbandingan Target vs Aktual per Departemen"), use_container_width=True)
        best_dept = max(dept_actuals, key=dept_actuals.get) if dept_actuals else "-"
        st.info(f"📌 **Insight:** Kontributor terbanyak diraih oleh **Departemen {best_dept}** ({dept_actuals.get(best_dept, 0)} ide).")
        st.markdown('</div>', unsafe_allow_html=True)

    with c4:
        lines, target_p4, act_p4 = [], [], []
        if filter_line != 'ALL':
            lines.append(opt_lines.get(filter_line, filter_line))
            target_p4.append(int(round(sum_m3 * 4)))
            act_p4.append(len(df_clean))
        else:
            line_groups = {}
            for row in df_clean:
                l_val = str(row.get('__COL_AL_LINE__', '')).strip()
                if l_val:
                    l_clean = clean_str(l_val)
                    if l_clean not in line_groups:
                        line_groups[l_clean] = {'name': l_val, 'actual': 0, 'target': 0}
                        for t in line_targets_3m:
                            if is_flexible_match(l_clean, t['clean_line']):
                                line_groups[l_clean]['target'] += int(round(t['cum_m3'] * 4))
                    line_groups[l_clean]['actual'] += 1
            for grp in line_groups.values():
                lines.append(grp['name']); target_p4.append(grp['target']); act_p4.append(grp['actual'])

        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.plotly_chart(make_styled_combo_chart(lines, target_p4, act_p4, "4. Pencapaian Target per Line / Section"), use_container_width=True)
        achieved_lines = sum(1 for a, t in zip(act_p4, target_p4) if a >= t and t > 0)
        st.info(f"📌 **Insight:** **{achieved_lines} dari {len(lines)} Line/Section** telah sukses mencapai/melampaui target.")
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="chart-card">', unsafe_allow_html=True)
    st.plotly_chart(make_styled_combo_chart(months_display, target_p5, act_p5, "5. Akumulasi Ide Berstatus CLOSE (Selesai Implementasi)"), use_container_width=True)
    st.info(f"📌 **Insight:** Total **{sum(act_p5)} ide** telah sepenuhnya selesai diimplementasikan (*Status Close*).")
    st.markdown('</div>', unsafe_allow_html=True)

# ----------------- TAB 2: TABEL DETIL BULANAN -----------------
with tab_details:
    st.subheader("🎯 Operational Action Plan & Root Cause Analysis")
    
    # ----------------- SUMMARY TABLE TARGET VS AKTUAL -----------------
    table_data = []
    for idx, l_name in enumerate(lines):
        actual_val = act_p4[idx] if idx < len(act_p4) else 0
        target_yearly = target_p4[idx] if idx < len(target_p4) else 0
        target_monthly = int(round(target_yearly / 12)) if target_yearly > 0 else 0
        achieve_monthly_pct = (actual_val / target_monthly * 100) if target_monthly > 0 else (100.0 if actual_val > 0 else 0.0)
        
        if target_monthly == 0:
            status_tag = "🟢 On Track" if actual_val > 0 else "⚪ No Target"
            arahan = "Kontribusi ide sangat baik." if actual_val > 0 else "Belum ada alokasi target bulanan."
        elif actual_val == 0:
            status_tag = "🔴 Critical"
            arahan = f"Target bulanan ({target_monthly} ide) belum terpenuhi. Perlu evaluasi 4M & 5 Why."
        elif actual_val < target_monthly:
            gap_m = target_monthly - actual_val
            status_tag = "🟡 Warning"
            arahan = f"Kurang {gap_m} ide untuk memenuhi target bulan ini."
        else:
            status_tag = "🟢 Target Achieved"
            arahan = "Target bulanan terpenuhi. Pertahankan ritme tim."

        table_data.append({
            "Line / Section": l_name,
            "Target Bulanan": target_monthly,
            "Aktual": actual_val,
            "Pencapaian Bulanan (%)": min(achieve_monthly_pct, 100.0),
            "Status": status_tag,
            "Rekomendasi Action Plan": arahan
        })

    df_summary = pd.DataFrame(table_data)
    st.dataframe(
        df_summary,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Pencapaian Bulanan (%)": st.column_config.ProgressColumn(
                "Progress Bar", format="%.1f%%", min_value=0, max_value=100
            )
        }
    )

    st.markdown("---")

    # =========================================================================
    # ELEMEN 1: ANALISA KONDISI YANG ADA (4M ANALYSIS - GAMBAR 1)
    # =========================================================================
    st.markdown("### 🔍 1. Analisa Kondisi Yang Ada (4M Analysis)")
    st.caption("Evaluasi faktor Man, Machine, Material, dan Method terkait ketidaktercapaian target usulan SS.")
    
    data_4m = [
        {
            "No": 1, "Man": "✓", "Mc": "", "Mat": "", "Met": "",
            "Control Item": "Pemahaman & Motivasi Karyawan",
            "Control Point": "Tingkat Partisipasi Pengajuan SS",
            "Standard": "100% Karyawan mengajukan min. 1 SS/bulan",
            "Actual": "Hanya 35% karyawan yang aktif mengirimkan ide SS",
            "Illustration": "-", "Judge": "NG"
        },
        {
            "No": 2, "Man": "", "Mc": "", "Mat": "", "Met": "✓",
            "Control Item": "Sistem Monitoring & Follow Up",
            "Control Point": "Review Berkala Ide oleh Spv/Foreman",
            "Standard": "Meeting review ide SS dilakukan 1x seminggu",
            "Actual": "Belum ada agenda khusus review SS mingguan di Line",
            "Illustration": "-", "Judge": "NG"
        },
        {
            "No": 3, "Man": "", "Mc": "✓", "Mat": "", "Met": "",
            "Control Item": "Akses Media Pendaftaran SS",
            "Control Point": "Kemudahan Input Ide SS",
            "Standard": "Input ide < 3 menit via Form/Portal",
            "Actual": "Operator kesulitan akses PC/Portal saat jam kerja",
            "Illustration": "-", "Judge": "NG"
        },
        {
            "No": 4, "Man": "", "Mc": "", "Mat": "✓", "Met": "",
            "Control Item": "Ketersediaan Media Fisik/Form",
            "Control Point": "Stok Form Ide SS di Area Line",
            "Standard": "Form cetak selalu tersedia di Dropbox SS",
            "Actual": "Dropbox SS sering kosong dan tidak ter-update",
            "Illustration": "-", "Judge": "NG"
        }
    ]
    
    st.dataframe(pd.DataFrame(data_4m), use_container_width=True, hide_index=True)

    st.markdown("---")

    # =========================================================================
    # ELEMEN 2: ANALISA SEBAB AKIBAT (5 WHY ANALYSIS - GAMBAR 2)
    # =========================================================================
    st.markdown("### ❓ 2. Analisa Sebab Akibat (5 Why Analysis)")
    st.caption("Penelusuran akar masalah secara mendalam berdasarkan hasil temuan 4M Analysis.")

    data_5why = [
        {
            "NO": 1,
            "PROBLEM DESCRIPTION": "Partisipasi Karyawan Rendah",
            "STD": "100% Karyawan Submit SS",
            "ACT": "Hanya 35% Karyawan Submit",
            "4 M": "Man",
            "WHY 1": "Karyawan ragu dan bingung cara menuliskan ide SS",
            "WHY 2": "Tidak pernah mendapat bimbingan pembuatan SS",
            "WHY 3": "Foreman/Spv belum pernah mengadakan sosialisasi penulisan SS",
            "WHY 4": "Belum ada KPI/Target sosialisasi SS yang dibebankan ke Spv",
            "WHY 5": "Belum ada standardisasi role WOS/SS untuk jajaran Leader"
        },
        {
            "NO": 2,
            "PROBLEM DESCRIPTION": "Review Ide di Line Terhambat",
            "STD": "Review Mingguan (1x/Minggu)",
            "ACT": "Review tidak berjalan rutin",
            "4 M": "Method",
            "WHY 1": "Spv menyatu dengan aktivitas pengerjaan rutin harian",
            "WHY 2": "Tidak ada slot waktu khusus untuk evaluasi usulan ide",
            "WHY 3": "Jadwal review SS belum masuk dalam Standar Kerja Mingguan Spv",
            "WHY 4": "Belum ada kontrol dari Management/Dept Head terkait progress SS",
            "WHY 5": "Sistem monitoring progress SS belum terintegrasi ke Daily Meeting"
        }
    ]
    
    st.dataframe(pd.DataFrame(data_5why), use_container_width=True, hide_index=True)

    # ----------------- DIAGRAM ISHIKAWA / FISHBONE -----------------
    st.markdown("#### 🐟 Diagram Tulang Ikan (Ishikawa Diagram)")
    
    fig_fishbone = go.Figure()

    # Tulang Utama (Spine)
    fig_fishbone.add_trace(go.Scatter(x=[0, 10], y=[0, 0], mode='lines+markers', line=dict(color='#1e1b4b', width=5), showlegend=False))
    # Kepala Ikan
    fig_fishbone.add_annotation(x=10, y=0, text="<b>TARGET SS<br>TIDAK TERCAPAI</b>", showarrow=True, arrowhead=2, arrowsize=1.5, arrowcolor="#ef4444", ax=40, ay=0, font=dict(size=12, color="#ffffff"), bgcolor="#ef4444", borderpad=6)

    # Cabang 4M
    # MAN (Atas Kiri)
    fig_fishbone.add_trace(go.Scatter(x=[2, 3.5], y=[2, 0], mode='lines', line=dict(color='#6366f1', width=3), showlegend=False))
    fig_fishbone.add_annotation(x=2, y=2, text="<b>MAN</b>", showarrow=False, font=dict(size=13, color="#4338ca"))
    fig_fishbone.add_annotation(x=2.3, y=1.2, text="Kurang Bimbingan Spv", showarrow=False, font=dict(size=10))

    # MACHINE (Atas Kanan)
    fig_fishbone.add_trace(go.Scatter(x=[6, 7.5], y=[2, 0], mode='lines', line=dict(color='#6366f1', width=3), showlegend=False))
    fig_fishbone.add_annotation(x=6, y=2, text="<b>MACHINE / TOOL</b>", showarrow=False, font=dict(size=13, color="#4338ca"))
    fig_fishbone.add_annotation(x=6.3, y=1.2, text="Akses Portal/PC Terbatas", showarrow=False, font=dict(size=10))

    # MATERIAL (Bawah Kiri)
    fig_fishbone.add_trace(go.Scatter(x=[2, 3.5], y=[-2, 0], mode='lines', line=dict(color='#6366f1', width=3), showlegend=False))
    fig_fishbone.add_annotation(x=2, y=-2, text="<b>MATERIAL</b>", showarrow=False, font=dict(size=13, color="#4338ca"))
    fig_fishbone.add_annotation(x=2.3, y=-1.2, text="Form Fisik Sering Kosong", showarrow=False, font=dict(size=10))

    # METHOD (Bawah Kanan)
    fig_fishbone.add_trace(go.Scatter(x=[6, 7.5], y=[-2, 0], mode='lines', line=dict(color='#6366f1', width=3), showlegend=False))
    fig_fishbone.add_annotation(x=6, y=-2, text="<b>METHOD</b>", showarrow=False, font=dict(size=13, color="#4338ca"))
    fig_fishbone.add_annotation(x=6.3, y=-1.2, text="Tidak Ada Review Rutin", showarrow=False, font=dict(size=10))

    fig_fishbone.update_layout(
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-0.5, 12]),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-3, 3]),
        height=320,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    st.plotly_chart(fig_fishbone, use_container_width=True)

    st.markdown("---")

    # =========================================================================
    # ELEMEN 3: RENCANA PERBAIKAN (COUNTERMEASURE PLAN - GAMBAR 3)
    # =========================================================================
    st.markdown("### 📅 3. Rencana Perbaikan (Countermeasure Schedule)")
    st.caption("Action plan terstruktur untuk mengatasi akar masalah lengkap dengan waktu pelaksanaan dan PIC.")

    # Data Gantt Chart / Schedule
    data_plan = [
        {"No": 1, "Item Problem": "Partisipasi Karyawan Rendah (Man)", "Activity": "Sosialisasi & Coaching Penulisan SS", "Detail Activity": "Penyusunan Modul Simple SS", "PIC": "OS, Produksi", "W1": "Plan", "W2": "", "W3": "", "W4": ""},
        {"No": 2, "Item Problem": "Partisipasi Karyawan Rendah (Man)", "Activity": "Sosialisasi & Coaching Penulisan SS", "Detail Activity": "Coaching Klinik SS per Line", "PIC": "Spv Line", "W1": "", "W2": "Plan", "W3": "Plan", "W4": ""},
        {"No": 3, "Item Problem": "Review Ide Terhambat (Method)", "Activity": "Standardisasi System Monitoring", "Detail Activity": "Integrasi Review SS di Meeting LKG", "PIC": "Dept Head", "W1": "", "W2": "Plan", "W3": "", "W4": ""},
        {"No": 4, "Item Problem": "Akses Portal Terbatas (Machine)", "Activity": "Penyediaan Digital & Physical Kiosk", "Detail Activity": "Pengadaan QR-Code Input SS via HP", "PIC": "IT / OS", "W1": "", "W2": "", "W3": "Plan", "W4": "Plan"},
        {"No": 5, "Item Problem": "Evaluasi & Sustaining", "Activity": "Monitoring Pencapaian Target", "Detail Activity": "Evaluasi Pencapaian SS Bulanan", "PIC": "ALL", "W1": "", "W2": "", "W3": "", "W4": "Plan"}
    ]

    df_plan = pd.DataFrame(data_plan)
    
    # Kustomisasi Tampilan Tabel Rencana Perbaikan
    st.dataframe(
        df_plan,
        use_container_width=True,
        hide_index=True,
        column_config={
            "W1": st.column_config.TextColumn("M1 - W1"),
            "W2": st.column_config.TextColumn("M1 - W2"),
            "W3": st.column_config.TextColumn("M1 - W3"),
            "W4": st.column_config.TextColumn("M1 - W4")
        }
    )

    with st.expander("📂 Raw Data Inspection"):
        st.dataframe(pd.DataFrame(df_clean), use_container_width=True)
