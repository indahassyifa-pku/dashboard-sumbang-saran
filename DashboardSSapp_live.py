import re
import requests
import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px

# ----------------- CONFIGURASI HALAMAN -----------------
st.set_page_config(
    page_title="Dashboard Executif - Sumbang Saran",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling CSS (Modern Glassmorphism & Visual Aesthetics)
st.markdown("""
    <style>
    .main { background-color: #f8fafc; }
    
    .header-container {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        padding: 24px;
        border-radius: 16px;
        color: white;
        margin-bottom: 20px;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
    }
    
    .executive-box {
        background: #ffffff;
        border-left: 5px solid #2563eb;
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
    }

    .metric-card {
        background-color: #ffffff;
        border-radius: 14px;
        padding: 18px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        border-left: 6px solid #2563eb;
        transition: transform 0.2s ease;
    }
    .metric-card:hover { transform: translateY(-2px); }
    .metric-card.close { border-left-color: #10b981; }
    .metric-card.open { border-left-color: #f59e0b; }
    .metric-card.notreg { border-left-color: #ef4444; }
    
    .metric-title { font-size: 0.8rem; font-weight: 700; text-transform: uppercase; color: #64748b; }
    .metric-value { font-size: 1.8rem; font-weight: 800; color: #0f172a; margin-top: 6px; }
    .metric-sub { font-size: 0.8rem; color: #94a3b8; margin-top: 4px; }

    .chart-card {
        background: #ffffff;
        border-radius: 16px;
        padding: 18px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        margin-bottom: 20px;
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

def make_styled_combo_chart(categories, target_vals, actual_vals, title):
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=categories, y=actual_vals, name='Aktual', 
        marker_color='#3b82f6', opacity=0.85, text=actual_vals, textposition='auto'
    ))
    fig.add_trace(go.Scatter(
        x=categories, y=target_vals, name='Target', mode='lines+markers+text',
        line=dict(color='#0f172a', width=3), marker=dict(size=7, color='#0f172a'),
        text=target_vals, textposition='top center'
    ))
    fig.update_layout(
        title=dict(text=f"<b>{title}</b>", font=dict(size=14, color='#0f172a')),
        margin=dict(l=20, r=20, t=40, b=20), height=320,
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor='#f1f5f9')
    )
    return fig

# ----------------- HEADER SECTION -----------------
head_col1, head_col2 = st.columns([3, 1])
with head_col1:
    st.markdown("""
        <div class="header-container">
            <h1 style="margin:0; font-size: 1.8rem;">🚀 Dashboard Executive Sumbang Saran</h1>
            <p style="margin:4px 0 0 0; color: #94a3b8; font-size: 0.9rem;">Monitoring Real-time Pencapaian Ide Karyawan & Implementasi</p>
        </div>
    """, unsafe_allow_html=True)
with head_col2:
    st.write("")
    if st.button("🔄 Refresh Data Real-Time", use_container_width=True):
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
st.sidebar.header("🔍 Filter Dashboard")
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
        <b style="color: #0f172a; font-size: 1.05rem;">📌 Executive Summary & Operational Health</b>
        <div style="color: #475569; font-size: 0.9rem; margin-top: 6px;">
            • Total <b>{total_all:,} ide</b> terkumpul dalam sistem.<br>
            • Tingkat penyelesaian ide hingga tahap akhir (Status Close) mencapai <b>{rate_close:.1f}%</b> ({cnt_close} ide selesai).<br>
            • Terdapat <b>{cnt_open} ide berkategori Open</b> dan <b>{cnt_notreg} berkategori Not Registered</b> yang membutuhkan follow-up dari Supervisor/Manager area.
        </div>
    </div>
""", unsafe_allow_html=True)

kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">💡 Total Ide Masuk</div>
        <div class="metric-value">{total_all:,}</div>
        <div class="metric-sub">Usulan terdaftar</div>
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
        <div class="metric-sub">Dalam proses</div>
    </div>
""", unsafe_allow_html=True)

kpi4.markdown(f"""
    <div class="metric-card notreg">
        <div class="metric-title" style="color: #ef4444;">⚠️ Not Registered</div>
        <div class="metric-value">{cnt_notreg:,}</div>
        <div class="metric-sub">Perlu tindakan</div>
    </div>
""", unsafe_allow_html=True)

st.write("")

# ----------------- MODUL TAMBAHAN: LEADERBOARD & DISTRIBUSI -----------------
col_lead, col_pie, col_bot = st.columns([1, 1, 1])

with col_lead:
    st.markdown('<div class="chart-card">', unsafe_allow_html=True)
    st.markdown("<b>🏆 Top 5 Contributor</b>", unsafe_allow_html=True)
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
        fig_pie = px.pie(df_st, names="Status", values="Jumlah", hole=0.55, color_discrete_sequence=px.colors.qualitative.Bold)
        fig_pie.update_layout(title="<b>Proporsi Status Ide</b>", margin=dict(l=10, r=10, t=35, b=10), height=200)
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("Data status tidak tersedia.")
    st.markdown('</div>', unsafe_allow_html=True)

with col_bot:
    st.markdown('<div class="chart-card">', unsafe_allow_html=True)
    st.markdown("<b>⚠️ Top Bottleneck Area (Ide Tertahan)</b>", unsafe_allow_html=True)
    df_open_only = [r for r in df_clean if clean_str(r.get(col_status, '')) == 'OPEN']
    if df_open_only:
        df_bot = pd.DataFrame(df_open_only)['__COL_AL_LINE__'].value_counts().reset_index().head(5)
        df_bot.columns = ["Line / Section", "Pending (Open)"]
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
tab_overview, tab_details = st.tabs(["📊 Analisis Visual & Tren", "📋 Ringkasan & Arahan Tindak Lanjut"])

with tab_overview:
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.plotly_chart(make_styled_combo_chart(months_display, target_p1, act_p1, "1. Total Ide Terdaftar (Target Akumulatif vs Aktual)"), use_container_width=True)
        tot_act_p1 = sum(act_p1)
        tot_tgt_p1 = target_p1[-1] if target_p1 else 0
        gap_p1 = tot_act_p1 - tot_tgt_p1
        p1_status = "menembus target" if gap_p1 >= 0 else f"kurang {abs(gap_p1)} ide dari target"
        st.info(f"📌 **Analisis Grafik 1:** Total terdaftar **{tot_act_p1} ide** dari target akhir tahun **{tot_tgt_p1} ide**. Status saat ini **{p1_status}**.")
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
        st.plotly_chart(make_styled_combo_chart(steps, target_p2, act_p2, "2. Target vs Aktual per Tahapan SS"), use_container_width=True)
        max_step_idx = int(np.argmax(act_p2)) if max(act_p2) > 0 else 0
        st.info(f"📌 **Analisis Grafik 2:** Konsentrasi ide terbanyak tertahan pada tahap **{steps[max_step_idx]}** ({act_p2[max_step_idx]} ide).")
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
        st.plotly_chart(make_styled_combo_chart(list(dept_targets.keys()), list(dept_targets.values()), list(dept_actuals.values()), "3. Target vs Aktual per Departemen (1 Tahun)"), use_container_width=True)
        best_dept = max(dept_actuals, key=dept_actuals.get) if dept_actuals else "-"
        st.info(f"📌 **Analisis Grafik 3:** Kontributor terbanyak berasal dari Departemen **{best_dept}** ({dept_actuals.get(best_dept, 0)} ide).")
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
        st.plotly_chart(make_styled_combo_chart(lines, target_p4, act_p4, "4. Target vs Aktual per Line / Section (1 Tahun)"), use_container_width=True)
        achieved_lines = sum(1 for a, t in zip(act_p4, target_p4) if a >= t and t > 0)
        st.info(f"📌 **Analisis Grafik 4:** Sebanyak **{achieved_lines} dari {len(lines)} Line/Section** sudah memenuhi target tahunan.")
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="chart-card">', unsafe_allow_html=True)
    st.plotly_chart(make_styled_combo_chart(months_display, target_p5, act_p5, "5. Target Penyelesaian Aktivitas SS (Status Close)"), use_container_width=True)
    st.info(f"📌 **Analisis Grafik 5:** Sebanyak **{sum(act_p5)} ide** telah berstatus CLOSE ({rate_close:.1f}% tingkat penyelesaian).")
    st.markdown('</div>', unsafe_allow_html=True)

# ----------------- TAB 2: TABEL DETIL BULANAN -----------------
with tab_details:
    st.subheader("🎯 Ringkasan Pencapaian Bulanan & Action Plan")
    
    table_data = []
    for idx, l_name in enumerate(lines):
        actual_val = act_p4[idx] if idx < len(act_p4) else 0
        target_yearly = target_p4[idx] if idx < len(target_p4) else 0
        target_monthly = int(round(target_yearly / 12)) if target_yearly > 0 else 0
        achieve_monthly_pct = (actual_val / target_monthly * 100) if target_monthly > 0 else (100.0 if actual_val > 0 else 0.0)
        
        if target_monthly == 0:
            status_tag = "🟢 Melampaui Target" if actual_val > 0 else "⚪ Tanpa Target"
            arahan = "Kontribusi ide sangat baik." if actual_val > 0 else "Belum ada alokasi target bulanan."
        elif actual_val == 0:
            status_tag = "🔴 Belum Ada Ide"
            arahan = f"Target bulanan ({target_monthly} ide) belum terpenuhi. Perlu koordinasi Supervisor."
        elif actual_val < target_monthly:
            gap_m = target_monthly - actual_val
            status_tag = "🟡 Kurang Target"
            arahan = f"Kurang {gap_m} ide untuk memenuhi target bulan ini."
        else:
            status_tag = "🟢 Target Bulanan Tercapai"
            arahan = "Target bulanan terpenuhi. Pertahankan ritme tim."

        table_data.append({
            "Line / Section": l_name,
            "Target Bulanan": target_monthly,
            "Aktual": actual_val,
            "Pencapaian Bulanan (%)": min(achieve_monthly_pct, 100.0),
            "Status": status_tag,
            "Rekomendasi Tindak Lanjut": arahan
        })

    df_summary = pd.DataFrame(table_data)
    st.dataframe(
        df_summary,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Pencapaian Bulanan (%)": st.column_config.ProgressColumn(
                "Progress Pencapaian", format="%.1f%%", min_value=0, max_value=100
            )
        }
    )

    with st.expander("📂 Preview Mentah Data Google Sheets"):
        st.dataframe(pd.DataFrame(df_clean), use_container_width=True)
