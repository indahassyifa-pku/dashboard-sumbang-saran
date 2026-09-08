import re
import time
import requests
import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go

# ----------------- CONFIGURASI HALAMAN -----------------
st.set_page_config(
    page_title="Dashboard Pemantauan Sumbang Saran",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling CSS
st.markdown("""
    <style>
    .main { background-color: #f4f6f9; }
    .stButton>button {
        background-color: #0D47A1;
        color: white;
        border-radius: 8px;
        font-weight: bold;
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
    
    f = clean_str(filter_val)
    t = clean_str(target_clean)

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
    val_str = str(val).strip().replace(',', '.')
    val_str = re.sub(r'[^0-9.]', '', val_str)
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
        st.error(f"Gagal mengunduh data dari URL ({url}): {e}")
        return []

def make_combo_chart(categories, target_vals, actual_vals, title):
    fig = go.Figure()
    
    # Bar Chart (Aktual)
    fig.add_trace(go.Bar(
        x=categories, 
        y=actual_vals, 
        name='Aktual', 
        marker_color='#81C784', 
        text=actual_vals, 
        textposition='auto',
        textfont=dict(weight="bold", color="#1b5e20")
    ))
    
    # Line Chart (Target)
    fig.add_trace(go.Scatter(
        x=categories, 
        y=target_vals, 
        name='Target', 
        mode='lines+markers+text',
        line=dict(color='#0D47A1', width=3),
        marker=dict(size=8, color='#0D47A1'),
        text=target_vals,
        textposition='top center',
        textfont=dict(weight="bold", color='#0D47A1')
    ))
    
    fig.update_layout(
        title=dict(text=f"<b>{title}</b>", font=dict(size=14)),
        margin=dict(l=30, r=20, t=45, b=40),
        height=350,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor='#e0e0e0')
    )
    return fig

# ----------------- HEADER & REFRESH -----------------
col_title, col_btn = st.columns([4, 1])

with col_title:
    st.title("📊 Dashboard Pemantauan Sumbang Saran")

with col_btn:
    st.write("")
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()

# ----------------- 1. LOAD & PARSE DATA -----------------
raw_data_rows = load_csv_generic(SHEET_URL_DATA)
raw_target_rows = load_csv_generic(SHEET_URL_TARGET)

# PARSING DATA UTAMA (KHUSUS KOLOM AL)
headers = []
df_raw = []
col_al_index = excel_col_to_index('AL')

if raw_data_rows:
    header_idx = 0
    for idx, row in enumerate(raw_data_rows):
        row_str = [str(val).lower().strip() for val in row]
        has_nama = any('nama' in item for item in row_str)
        has_dept = any(re.search(r'(dept|department|departement|bagian)', item) for item in row_str)
        if has_nama and has_dept:
            header_idx = idx
            break

    headers = [str(h).strip() for h in raw_data_rows[header_idx]]
    
    for i in range(header_idx + 1, len(raw_data_rows)):
        current_row = raw_data_rows[i]
        if any(current_row):
            row_assoc = {}
            for col_idx, col_name in enumerate(headers):
                row_assoc[col_name] = current_row[col_idx] if col_idx < len(current_row) else ''
            
            val_al = current_row[col_al_index].strip() if col_al_index < len(current_row) and current_row[col_al_index] else ''
            if not val_al:
                for h_key, h_val in row_assoc.items():
                    if h_key.upper() == 'AL' or 'line' in h_key.lower():
                        val_al = str(h_val).strip()
                        if val_al:
                            break
            
            row_assoc['__COL_AL_LINE__'] = val_al
            df_raw.append(row_assoc)

# Deteksi Kolom Utama Dinamis
col_status, col_tahapan, col_dept, col_bulan = None, None, None, None

if headers:
    for c in headers:
        c_lower = c.lower()
        if not col_status and 'status' in c_lower and 'tahap' not in c_lower and 'ide' not in c_lower:
            col_status = c
        if not col_tahapan and ('tahap' in c_lower or 'aktivitas' in c_lower):
            col_tahapan = c
        if not col_dept and re.search(r'(dept|department|departement|departemen|divisi)', c_lower):
            col_dept = c
        if not col_bulan and any(k in c_lower for k in ['bulan', 'tgl', 'tanggal', 'daftar']):
            col_bulan = c

# PARSING TARGET
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

    for row_idx, row in enumerate(raw_target_rows[1:], start=1):
        dept_val = str(row[idx_dept]).strip() if idx_dept < len(row) and row[idx_dept] else ''
        line_val = str(row[idx_line]).strip() if idx_line < len(row) and row[idx_line] else ''
        m1_raw = row[idx_m1] if idx_m1 < len(row) else ''
        m2_raw = row[idx_m2] if idx_m2 < len(row) else ''
        m3_raw = row[idx_m3] if idx_m3 < len(row) else ''

        if dept_val and dept_val.lower() not in ['dept', 'department', 'departemen']:
            current_dept = dept_val

        if line_val:
            line_targets_3m.append({
                'dept': current_dept,
                'line': line_val,
                'clean_dept': clean_str(current_dept),
                'clean_line': clean_str(line_val),
                'cum_m1': clean_num(m1_raw),
                'cum_m2': clean_num(m2_raw),
                'cum_m3': clean_num(m3_raw)
            })

# ----------------- 2. DROPDOWN & FILTERING DATA -----------------
opt_depts, opt_lines, opt_statuses = {}, {}, {}

for t_info in line_targets_3m:
    if t_info['dept']:
        opt_depts[t_info['clean_dept']] = t_info['dept']

for r in df_raw:
    if col_dept and str(r.get(col_dept, '')).strip():
        opt_depts[clean_str(r[col_dept])] = str(r[col_dept]).strip()
    
    val_al = str(r.get('__COL_AL_LINE__', '')).strip()
    if val_al:
        opt_lines[clean_str(val_al)] = val_al
        
    if col_status and str(r.get(col_status, '')).strip():
        opt_statuses[clean_str(r[col_status])] = str(r[col_status]).strip()

opt_depts = dict(sorted(opt_depts.items()))
opt_lines = dict(sorted(opt_lines.items()))
opt_statuses = dict(sorted(opt_statuses.items()))

f_col1, f_col2, f_col3 = st.columns(3)

with f_col1:
    dept_options = ["ALL"] + list(opt_depts.keys())
    filter_dept = st.selectbox("Departemen", dept_options, format_func=lambda x: "-- Semua Departemen --" if x == "ALL" else opt_depts[x])

with f_col2:
    line_options = ["ALL"] + list(opt_lines.keys())
    filter_line = st.selectbox("Line / Section", line_options, format_func=lambda x: "-- Semua Line/Section --" if x == "ALL" else opt_lines[x])

with f_col3:
    status_options = ["ALL"] + list(opt_statuses.keys())
    filter_status = st.selectbox("Status SS", status_options, format_func=lambda x: "-- Semua Status --" if x == "ALL" else opt_statuses[x])

# Filter Dataset
df_clean = []
for row in df_raw:
    if filter_dept != 'ALL' and col_dept and not is_flexible_match(filter_dept, clean_str(row.get(col_dept, ''))):
        continue
    if filter_line != 'ALL' and not is_flexible_match(filter_line, clean_str(row.get('__COL_AL_LINE__', ''))):
        continue
    if filter_status != 'ALL' and col_status and not is_flexible_match(filter_status, clean_str(row.get(col_status, ''))):
        continue
    df_clean.append(row)

# ----------------- 3. METRICS -----------------
total_all = len(df_clean)
cnt_close, cnt_open, cnt_notreg = 0, 0, 0

if col_status:
    for row in df_clean:
        val = clean_str(row.get(col_status, ''))
        if val == 'CLOSE':
            cnt_close += 1
        elif val == 'OPEN':
            cnt_open += 1
        elif 'NOT' in val:
            cnt_notreg += 1

m1, m2, m3, m4 = st.columns(4)
m1.metric("💡 Total Ide Masuk", f"{total_all} Ide")
m2.metric("✅ Status: CLOSE", f"{cnt_close} Ide")
m3.metric("⏳ Status: OPEN", f"{cnt_open} Ide")
m4.metric("⚠️ Status: NOT REGISTERED", f"{cnt_notreg} Ide")

st.markdown("---")

# ----------------- 4. TARGET CALCULATIONS -----------------
months_display = ["September", "October", "November", "December", "January", "February", "March", "April", "May", "June", "July", "August"]

sum_m1, sum_m2, sum_m3 = 0.0, 0.0, 0.0

for t_info in line_targets_3m:
    if filter_line != 'ALL':
        f_line = clean_str(filter_line)
        t_line = t_info['clean_line']
        if f_line == t_line or f_line in t_line or t_line in f_line:
            sum_m1 += t_info['cum_m1']
            sum_m2 += t_info['cum_m2']
            sum_m3 += t_info['cum_m3']
    else:
        if is_flexible_match(filter_dept, t_info['clean_dept']):
            sum_m1 += t_info['cum_m1']
            sum_m2 += t_info['cum_m2']
            sum_m3 += t_info['cum_m3']

delta1 = sum_m1
delta2 = max(0.0, sum_m2 - sum_m1)
delta3 = max(0.0, sum_m3 - sum_m2)

monthly_increments = [
    delta1, delta2, delta3,
    delta1, delta2, delta3,
    delta1, delta2, delta3,
    delta1, delta2, delta3
]

target_p1 = []
running_target = 0.0
for inc in monthly_increments:
    running_target += inc
    target_p1.append(int(round(running_target)))

target_p5 = [0] * 12
for i in range(2, 12):
    target_p5[i] = target_p1[i - 2]

# ----------------- 5. PARSING DATA AKTUAL BULANAN -----------------
act_p1_monthly = [0] * 12
act_p5_monthly = [0] * 12

month_map = {
    9: 0, 10: 1, 11: 2, 12: 3,
    1: 4, 2: 5, 3: 6, 4: 7,
    5: 8, 6: 9, 7: 10, 8: 11
}

for row in df_clean:
    b_val = str(row.get(col_bulan, '')).strip() if col_bulan else ''
    st_val = clean_str(row.get(col_status, '')) if col_status else ''
    m_num = None

    bln_lower = b_val.lower()
    if re.search(r'(sep|09|9/)', bln_lower): m_num = 9
    elif re.search(r'(okt|oct|10/)', bln_lower): m_num = 10
    elif re.search(r'(nov|11/)', bln_lower): m_num = 11
    elif re.search(r'(des|dec|12/)', bln_lower): m_num = 12
    elif re.search(r'(jan|01/|1/)', bln_lower): m_num = 1
    elif re.search(r'(feb|02/|2/)', bln_lower): m_num = 2
    elif re.search(r'(mar|03/|3/)', bln_lower): m_num = 3
    elif re.search(r'(apr|04/|4/)', bln_lower): m_num = 4
    elif re.search(r'(mei|may|05/|5/)', bln_lower): m_num = 5
    elif re.search(r'(jun|06/|6/)', bln_lower): m_num = 6
    elif re.search(r'(jul|07/|7/)', bln_lower): m_num = 7
    elif re.search(r'(agu|aug|08/|8/)', bln_lower): m_num = 8

    if m_num and m_num in month_map:
        idx = month_map[m_num]
        act_p1_monthly[idx] += 1
        if st_val == 'CLOSE':
            act_p5_monthly[idx] += 1

act_p1 = act_p1_monthly
act_p5 = act_p5_monthly

# ----------------- CHARTS DATA GENERATION -----------------
# Chart 3: Departemen
dept_targets, dept_actuals = {}, {}
for t_info in line_targets_3m:
    d_code = t_info['clean_dept']
    d_label = t_info['dept']

    if filter_dept != 'ALL' and not is_flexible_match(filter_dept, d_code):
        continue

    if d_label not in dept_targets:
        dept_targets[d_label] = 0
        dept_actuals[d_label] = 0
    dept_targets[d_label] += int(round(t_info['cum_m3'] * 4))

if col_dept:
    for row in df_clean:
        d_code = clean_str(row.get(col_dept, ''))
        for d_label in dept_targets.keys():
            if is_flexible_match(clean_str(d_label), d_code):
                dept_actuals[d_label] += 1
                break

depts = list(dept_targets.keys())
target_p3 = list(dept_targets.values())
act_p3 = list(dept_actuals.values())

# Chart 4: Line / Section
lines, target_p4, act_p4 = [], [], []

if filter_line != 'ALL':
    display_line_name = opt_lines.get(filter_line, filter_line)
    lines.append(display_line_name)
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
                for t_info in line_targets_3m:
                    if is_flexible_match(l_clean, t_info['clean_line']):
                        line_groups[l_clean]['target'] += int(round(t_info['cum_m3'] * 4))
            line_groups[l_clean]['actual'] += 1

    for grp in line_groups.values():
        lines.append(grp['name'])
        target_p4.append(grp['target'])
        act_p4.append(grp['actual'])

# Chart 2: Tahapan
steps = ["Pengajuan Ide", "Persetujuan Ide", "Registrasi Ide", "Pengerjaan Ide", "Pembuatan Laporan", "Penilaian", "Pencairan Dana"]
target_p2 = [0, 0, target_p1[2], 0, 0, 0, 0]
act_p2 = [0] * len(steps)

if col_tahapan:
    for row in df_clean:
        t_val = str(row.get(col_tahapan, '')).strip().lower()
        for s_idx, s_name in enumerate(steps):
            if s_name[:5].lower() in t_val:
                act_p2[s_idx] += 1

# ----------------- RENDER CHARTS -----------------
c1, c2 = st.columns(2)
with c1:
    st.plotly_chart(make_combo_chart(months_display, target_p1, act_p1, "1. Total Ide Terdaftar (Target Akumulatif vs Aktual)"), use_container_width=True)
with c2:
    st.plotly_chart(make_combo_chart(steps, target_p2, act_p2, "2. Target vs Aktual by Tahapan SS"), use_container_width=True)

c3, c4 = st.columns(2)
with c3:
    st.plotly_chart(make_combo_chart(depts, target_p3, act_p3, "3. Target vs Aktual by Departemen (Total 1 Thn)"), use_container_width=True)
with c4:
    st.plotly_chart(make_combo_chart(lines, target_p4, act_p4, "4. Target vs Aktual by Line/Section (Total 1 Thn)"), use_container_width=True)

st.plotly_chart(make_combo_chart(months_display, target_p5, act_p5, "5. Target Penyelesaian Aktivitas SS (Status Close)"), use_container_width=True)

# ----------------- TABEL ARAHAN -----------------
st.markdown("---")
st.subheader("🎯 Arahan Tindak Lanjut per Line / Section")

lines_filtered_table = []
for idx, l_name in enumerate(lines):
    actual_val = act_p4[idx] if idx < len(act_p4) else 0
    target_val = target_p4[idx] if idx < len(target_p4) else 0
    achieve_str = f"{(actual_val / target_val * 100):.1f}%" if target_val > 0 else "N/A"
    status_tag = "🟢 Tercapai" if (actual_val >= target_val and target_val > 0) else "🟡 Belum Tercapai"

    lines_filtered_table.append({
        "Line / Section": l_name,
        "Target (1 Thn)": target_val,
        "Aktual": actual_val,
        "Pencapaian": achieve_str,
        "Status": status_tag
    })

st.dataframe(pd.DataFrame(lines_filtered_table), use_container_width=True, hide_index=True)
