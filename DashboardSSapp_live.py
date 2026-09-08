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
    /* Global Styling */
    .main { background-color: #f8fafc; }
    
    /* Header Styling */
    .header-container {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        padding: 24px;
        border-radius: 16px;
        color: white;
        margin-bottom: 25px;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
    }
    
    /* Metric Card Styling */
    .metric-card {
        background-color: #ffffff;
        border-radius: 14px;
        padding: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
        border-left: 6px solid #2563eb;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
    }
    .metric-card.close { border-left-color: #10b981; }
    .metric-card.open { border-left-color: #f59e0b; }
    .metric-card.notreg { border-left-color: #ef4444; }
    
    .metric-title {
        font-size: 0.825rem;
        font-weight: 700;
        text-transform: uppercase;
        color: #64748b;
        letter-spacing: 0.5px;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: 800;
        color: #0f172a;
        margin-top: 8px;
    }
    .metric-sub {
        font-size: 0.8rem;
        color: #94a3b8;
        margin-top: 4px;
    }

    /* Container Box for Charts */
    .chart-card {
        background: #ffffff;
        border-radius: 16px;
        padding: 16px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        margin-bottom: 20px;
    }

    /* Primary Button Customization */
    .stButton>button {
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
        color: white;
        border-radius: 10px;
        border: none;
        font-weight: 600;
        padding: 10px 20px;
        box-shadow: 0 4px 6px -1px rgba(37, 99, 235, 0.3);
    }
    </style>
""", unsafe_allow_html=True)

# ----------------- CONSTANTS & UTILS -----------------
SHEET_URL_DATA = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRoRFG_w4aDY6_umLj3VOE7Tt_lswjQp2Lz0UOpTXAVCBXt97CEOU1x_bqS_Qeu4Q/pub?gid=654391933&single=true&output=csv"
SHEET_URL_TARGET = "https://docs.google.com/spreadsheets/d/1msjcr5f3WIMvKpW9jJU52Jns-V5Xx3VM/export?format=csv&gid=507573436"

def clean_str(val):
    if pd.isna(val) or val is None:
        return ""
    return re.sub(r'[^a-zA-Z0-9]', '', str(val)).upper().strip()

def excel_col_to_index(col):
    col = col.upper()
    idx = 0
    for char in col:
        idx = idx * 26 + (ord(char) - ord('A') + 1)
    return idx - 1

def is_flexible_match(filter_val, target_clean):
    if filter_val == 'ALL' or not filter_val or not target_clean:
        return True
    f, t = clean_str(filter_val), clean_str(target_clean)
    if f == t:
        return True
    if '/' in f or '/' in t:
        parts_f = set(filter(None, f.split('/')))
        parts_t = set(filter(None, t.split('/')))
        return len(parts_f.intersection(parts_t)) > 0
    return (f in t) or (t in f)

def clean_num(val):
    if pd.isna(val) or val is None or val == '':
        return 0.0
    val_str = re.sub(r'[^0-9.]', '', str(val).strip().replace(',', '.'))
    try:
        return float(val_str)
    except ValueError:
        return 0.0

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
    
    # Gradient Bar Chart
    fig.add_trace(go.Bar(
        x=categories, 
        y=actual_vals, 
        name='Aktual', 
        marker_color='#3b82f6',
        marker_line_color='#2563eb',
        marker_line_width=1.5,
        opacity=0.85,
        text=actual_vals, 
        textposition='auto',
        textfont=dict(weight="bold", color="#ffffff")
    ))
    
    # Styled Line Chart
    fig.add_trace(go.Scatter(
        x=categories, 
        y=target_vals, 
        name='Target', 
        mode='lines+markers+text',
        line=dict(color='#0f172a', width=3, dash='solid'),
        marker=dict(size=8, color='#0f172a', symbol='circle'),
        text=target_vals,
        textposition='top center',
        textfont=dict(weight="bold", color='#0f172a')
    ))
    
    fig.update_layout(
        title=dict(text=f"<b>{title}</b>", font=dict(size=15, color='#0f172a', family="sans-serif")),
        margin=dict(l=20, r=20, t=50, b=30),
        height=340,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis=dict(showgrid=False, tickfont=dict(color='#64748b')),
        yaxis=dict(showgrid=True, gridcolor='#f1f5f9', tickfont=dict(color='#64748b'))
    )
    return fig

# ----------------- HEADER SECTION -----------------
head_col1, head_col2 = st.columns([3, 1])
with head_col1:
    st.markdown("""
        <div class="header-container">
            <h1 style="margin:0; font-size: 1.8rem;">🚀 Dashboard Pemantauan Sumbang Saran</h1>
            <p style="margin:4px 0 0 0; color: #94a3b8; font-size: 0.95rem;">Monitoring Real-time Pencapaian Ide Karyawan & Implementasi</p>
        </div>
    """, unsafe_allow_html=True)
with head_col2:
    st.write("")
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
            header_idx = idx
            break

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

# Apply Filter
df_clean = [row for row in df_raw if 
    (filter_dept == 'ALL' or not col_dept or is_flexible_match(filter_dept, clean_str(row.get(col_dept, '')))) and
    (filter_line == 'ALL' or is_flexible_match(filter_line, clean_str(row.get('__COL_AL_LINE__', '')))) and
    (filter_status == 'ALL' or not col_status or is_flexible_match(filter_status, clean_str(row.get(col_status, ''))))
]

# ----------------- EXECUTIVE KPI CARDS -----------------
total_all = len(df_clean)
cnt_close, cnt_open, cnt_notreg = 0, 0, 0
if col_status:
    for row in df_clean:
        val = clean_str(row.get(col_status, ''))
        if val == 'CLOSE': cnt_close += 1
        elif val == 'OPEN': cnt_open += 1
        elif 'NOT' in val: cnt_notreg += 1

rate_close = (cnt_close / total_all * 100) if total_all > 0 else 0

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
        <div class="metric-sub">Perlu penanganan</div>
    </div>
""", unsafe_allow_html=True)

st.write("")

# Tambahkan bagian ini di bawah KPI Cards yang sudah ada

st.write("")
st.subheader("💡 Highlight & Distribusi Kualitas Ide")

col_lead, col_pie = st.columns([1, 1])

with col_lead:
    st.markdown('<div class="chart-card">', unsafe_allow_html=True)
    st.markdown("<b>🏆 Top 5 Contributor (Sumbang Saran Terbanyak)</b>", unsafe_allow_html=True)
    
    # Hitung ranking pembuat ide terbanyak
    col_nama = next((c for c in headers if 'nama' in c.lower()), None)
    if col_nama:
        df_leaderboard = (
            pd.DataFrame(df_clean)[col_nama]
            .value_counts()
            .reset_index()
            .head(5)
        )
        df_leaderboard.columns = ["Nama Karyawan", "Jumlah Ide"]
        st.dataframe(df_leaderboard, use_container_width=True, hide_index=True)
    else:
        st.info("Kolom 'Nama' tidak ditemukan di dataset untuk menghitung Leaderboard.")
    st.markdown('</div>', unsafe_allow_html=True)

with col_pie:
    st.markdown('<div class="chart-card">', unsafe_allow_html=True)
    # Donut Chart untuk Komposisi Status Ide
    if col_status:
        df_status_count = pd.DataFrame(df_clean)[col_status].value_counts().reset_index()
        df_status_count.columns = ["Status", "Jumlah"]
        
        fig_pie = px.pie(
            df_status_count, 
            names="Status", 
            values="Jumlah", 
            hole=0.5,
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        fig_pie.update_layout(
            title="<b>Komposisi Proporsi Status Ide</b>",
            margin=dict(l=20, r=20, t=40, b=20),
            height=260
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ----------------- TARGET & ACTUAL DATA PROCESSING -----------------
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

# ----------------- VISUAL CHARTS LAYOUT & KESIMPULAN -----------------

# Pastikan baris ini ada SEBELUM masuk ke with tab_overview!
tab_overview, tab_details = st.tabs(["📊 Analisis Visual & Tren", "📋 Ringkasan & Arahan Tindak Lanjut"])

# Baru jalankan blok with tab_overview
with tab_overview:
    # ----------------- ROW 1 -----------------
    c1, c2 = st.columns(2)
    
    with c1:
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.plotly_chart(make_styled_combo_chart(months_display, target_p1, act_p1, "1. Total Ide Terdaftar (Target Akumulatif vs Aktual)"), use_container_width=True)
        
        # Kesimpulan Grafik 1
        tot_act_p1 = sum(act_p1)
        tot_tgt_p1 = target_p1[-1] if target_p1 else 0
        gap_p1 = tot_act_p1 - tot_tgt_p1
        p1_status = "menembus target" if gap_p1 >= 0 else f"kurang {abs(gap_p1)} ide dari target"
        
        st.info(f"""
        📌 **Analisis Grafik 1:**
        * **Total Terdaftar:** **{tot_act_p1} ide** dari target akhir tahun **{tot_tgt_p1} ide**.
        * **Status:** Akumulasi ide terdaftar saat ini **{p1_status}**.
        """)
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
        
        # Kesimpulan Grafik 2
        max_step_idx = int(np.argmax(act_p2)) if max(act_p2) > 0 else 0
        steng_step = steps[max_step_idx]
        steng_val = act_p2[max_step_idx]
        
        st.info(f"""
        📌 **Analisis Grafik 2:**
        * **Penumpukan Berkas:** Konsentrasi ide terbanyak saat ini ada pada tahap **{steng_step}** ({steng_val} ide).
        * **Catatan:** Perlu akselerasi proses agar ide tidak tertahan di tahap awal dan bisa segera diimplementasikan.
        """)
        st.markdown('</div>', unsafe_allow_html=True)

    # ----------------- ROW 2 -----------------
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
        
        # Kesimpulan Grafik 3
        best_dept = max(dept_actuals, key=dept_actuals.get) if dept_actuals else "-"
        best_dept_val = dept_actuals.get(best_dept, 0)
        
        st.info(f"""
        📌 **Analisis Grafik 3:**
        * **Kontributor Tertinggi:** Departemen **{best_dept}** memimpin pengajuan ide terbanyak (**{best_dept_val} ide**).
        * **Evaluasi:** Dorong departemen lain yang kontribusinya masih jauh dari target tahunan.
        """)
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
        
        # Kesimpulan Grafik 4
        achieved_lines = sum(1 for a, t in zip(act_p4, target_p4) if a >= t and t > 0)
        tot_lines = len(lines)
        
        st.info(f"""
        📌 **Analisis Grafik 4:**
        * **Pencapaian Area:** **{achieved_lines} dari {tot_lines} Line/Section** sudah memenuhi target ide tahunan.
        * **Area Kritis:** Line yang belum ada kontribusi ide sama sekali perlu mendapat pengawasan langsung dari Supervisor.
        """)
        st.markdown('</div>', unsafe_allow_html=True)

    # ----------------- ROW 3 -----------------
    st.markdown('<div class="chart-card">', unsafe_allow_html=True)
    st.plotly_chart(make_styled_combo_chart(months_display, target_p5, act_p5, "5. Target Penyelesaian Aktivitas SS (Status Close)"), use_container_width=True)
    
    # Kesimpulan Grafik 5
    tot_close_act = sum(act_p5)
    tot_close_tgt = target_p5[-1] if target_p5 else 0
    close_pct = (tot_close_act / total_all * 100) if total_all > 0 else 0.0
    
    st.info(f"""
    📌 **Analisis Grafik 5 (Status Close):**
    * **Penyelesaian Akhir:** Sebanyak **{tot_close_act} ide** telah berstatus **CLOSE** dari total **{total_all} ide** masuk ({close_pct:.1f}% penyelesaian).
    * **Target Eksekusi:** Diperlukan penyelesaian hingga tahap implementasi agar ide yang diajukan tidak hanya berhenti pada tahap pendaftaran.
    """)
    st.markdown('</div>', unsafe_allow_html=True)

# ----------------- TABEL & ARAHAN EXECUTIVE (TAB 2) -----------------
with tab_details:
    st.subheader("🎯 Ringkasan Pencapaian Bulanan & Action Plan")
    
    table_data = []
    for idx, l_name in enumerate(lines):
        actual_val = act_p4[idx] if idx < len(act_p4) else 0
        target_yearly = target_p4[idx] if idx < len(target_p4) else 0
        
        # Perhitungan Target Bulanan (Target Tahunan dibagi 12 bulan)
        target_monthly = int(round(target_yearly / 12)) if target_yearly > 0 else 0
        
        # Hitung Persentase Pencapaian Terhadap Target Bulanan
        achieve_monthly_pct = (actual_val / target_monthly * 100) if target_monthly > 0 else (100.0 if actual_val > 0 else 0.0)
        
        # Logika Status & Rekomendasi berdasarkan Target Bulanan
        if target_monthly == 0:
            if actual_val > 0:
                status_tag = "🟢 Melampaui Target"
                arahan = "Sangat baik, terdapat kontribusi ide meskipun tidak ada target spesifik."
            else:
                status_tag = "⚪ Tanpa Target"
                arahan = "Belum ada alokasi target bulanan untuk area ini."
        elif actual_val == 0:
            status_tag = "🔴 Belum Ada Ide"
            arahan = f"Target bulanan ({target_monthly} ide) belum terpenuhi. Perlu sosialisasi dari Supervisor."
        elif actual_val < target_monthly:
            gap_m = target_monthly - actual_val
            status_tag = "🟡 Kurang Target"
            arahan = f"Kurang {gap_m} ide untuk memenuhi target bulan ini ({target_monthly} ide)."
        else:
            status_tag = "🟢 Target Bulanan Tercapai"
            arahan = "Target bulanan terpenuhi. Pertahankan ritme pengajuan ide."

        table_data.append({
            "Line / Section": l_name,
            "Target Bulanan": target_monthly,
            "Aktual": actual_val,
            "Pencapaian Bulanan (%)": min(achieve_monthly_pct, 100.0), # Di-cap ke 100% untuk progress bar
            "Status": status_tag,
            "Rekomendasi Tindak Lanjut": arahan
        })

    df_summary = pd.DataFrame(table_data)
    
    # Render Tabel Interaktif Streamlit
    st.dataframe(
        df_summary,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Target Bulanan": st.column_config.NumberColumn(
                "Target Bulanan",
                help="Target ide bulanan (Target Tahunan / 12)",
                format="%d"
            ),
            "Aktual": st.column_config.NumberColumn(
                "Aktual Ide",
                help="Jumlah ide yang masuk saat ini",
                format="%d"
            ),
            "Pencapaian Bulanan (%)": st.column_config.ProgressColumn(
                "Progress Pencapaian",
                help="Persentase ketercapaian terhadap target bulanan",
                format="%.1f%%",
                min_value=0,
                max_value=100,
            ),
            "Status": st.column_config.TextColumn(
                "Status",
                help="Indikator ketercapaian target bulanan"
            ),
            "Rekomendasi Tindak Lanjut": st.column_config.TextColumn(
                "Rekomendasi Tindak Lanjut",
                width="large"
            )
        }
    )

    with st.expander("📂 Preview Mentah Data Google Sheets"):
        st.dataframe(pd.DataFrame(df_clean), use_container_width=True)
