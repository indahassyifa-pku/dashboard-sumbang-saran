import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# ----------------- CONFIGURASI HALAMAN -----------------
st.set_page_config(
    page_title="Dashboard Pemantauan Sumbang Saran",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button {
        background-color: #0D47A1;
        color: white;
        border-radius: 8px;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRoRFG_w4aDY6_umLj3VOE7Tt_lswjQp2Lz0UOpTXAVCBXt97CEOU1x_bqS_Qeu4Q/pub?gid=654391933&single=true&output=csv"

@st.cache_data(ttl=10)
def load_data(url):
    try:
        df_raw = pd.read_csv(url, header=None)
        header_idx = None
        
        # Cari baris yang menjadi header tabel
        for idx, row in df_raw.iterrows():
            row_str = [str(val).lower() for val in row.values]
            if any('nama' in val_item for val_item in row_str) and any(k in val_item for val_item in row_str for k in ['dept', 'department', 'departement', 'bagian']):
                header_idx = idx
                break
                
        if header_idx is not None:
            df = pd.read_csv(url, skiprows=header_idx)
        else:
            df = pd.read_csv(url)
        return df
    except Exception as e:
        st.error(f"Gagal mengunduh data dari Google Sheets: {e}")
        return pd.DataFrame()

# Fungsi Pembuat Grafik Kombinasi (Batang = Hijau Muda #81C784, Garis = Biru Tua #0D47A1)
def make_combo_chart(categories, target_vals, actual_vals, title):
    fig = go.Figure()
    
    # 1. Grafik Batang untuk Aktual
    fig.add_trace(go.Bar(
        x=categories, 
        y=actual_vals, 
        name='Aktual', 
        marker_color='#81C784', 
        text=actual_vals, 
        textposition='auto',
        textfont=dict(weight="bold", color="#1b5e20")
    ))
    
    # 2. Grafik Garis untuk Target
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
        title=f"<b>{title}</b>",
        margin=dict(l=20, r=20, t=45, b=20),
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
    st.title("📊 Dashboard Pemantauan Sumbang Saran (Live)")
    st.caption("Data terhubung langsung secara real-time dengan Google Sheets Komite SS")

with col_btn:
    st.write("")
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()

st.markdown("---")

try:
    df = load_data(SHEET_URL)

    if not df.empty:
        df.columns = df.columns.astype(str).str.strip()

        # Deteksi Nama Kolom Fleksibel
        col_status = next((c for c in df.columns if 'status' in c.lower() and 'tahap' not in c.lower() and 'ide' not in c.lower()), None)
        col_status_ide = next((c for c in df.columns if 'status ide' in c.lower() or 'status_ide' in c.lower()), None)
        col_tahapan = next((c for c in df.columns if 'tahap' in c.lower() or 'aktivitas' in c.lower()), None)
        col_dept = next((c for c in df.columns if any(k in c.lower() for k in ['dept', 'department', 'departement', 'departemen', 'divisi', 'bagian'])), None)
        col_line = next((c for c in df.columns if any(k in c.lower() for k in ['line', 'section', 'seksi', 'area'])), None)
        col_bulan = next((c for c in df.columns if 'bulan' in c.lower() or 'daftar' in c.lower()), None)

        df_clean = df.dropna(how='all').copy()

        # STATUS SS (KPI CARDS)
        if col_status and col_status in df_clean.columns:
            s_clean = df_clean[col_status].astype(str).str.strip().str.upper()
            cnt_close = (s_clean == 'CLOSE').sum()
            cnt_open = (s_clean == 'OPEN').sum()
            cnt_notreg = (s_clean == 'NOT REGISTERED').sum()
        else:
            cnt_close, cnt_open, cnt_notreg = 0, 0, 0

        total_all = len(df_clean)

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("💡 Total Ide Masuk", f"{total_all} Ide")
        k2.metric("✅ Status: CLOSE", f"{cnt_close} Ide")
        k3.metric("⏳ Status: OPEN", f"{cnt_open} Ide")
        k4.metric("⚠️ Status: NOT REGISTERED", f"{cnt_notreg} Ide")

        st.markdown("---")

        months_display = ["September", "October", "November", "December", "January", "February", "March", "April", "May", "June", "July", "August"]
        month_keys = [
            ["sep"], ["oct", "okt"], ["nov"], ["dec", "des"], 
            ["jan"], ["feb"], ["mar"], ["apr"], 
            ["may", "mei"], ["jun"], ["jul"], ["aug", "agu"]
        ]

        # ----------------- GRAFIK 1 & 2 -----------------
        c1, c2 = st.columns(2)

        with c1:
            # 1. Total Ide Terdaftar
            target_p1 = [34, 64, 93, 127, 157, 186, 220, 250, 279, 313, 343, 372]
            act_p1 = []
            if col_bulan and col_bulan in df_clean.columns:
                s_bulan = df_clean[col_bulan].astype(str).str.strip().str.lower()
                for keys in month_keys:
                    count_m = s_bulan.apply(lambda x: any(k in x for k in keys)).sum()
                    act_p1.append(count_m)
            else:
                act_p1 = [0] * 12
            st.plotly_chart(make_combo_chart(months_display, target_p1, act_p1, "1. Total Ide Terdaftar (Target vs Aktual)"), use_container_width=True)

        with c2:
            # 2. Target vs Aktual by Tahapan SS
            steps = ["Pengajuan Ide", "Persetujuan Ide", "Registrasi Ide", "Pengerjaan Ide", "Pembuatan Laporan", "Penilaian", "Pencairan Dana"]
            target_p2 = [0, 0, 34, 0, 0, 0, 0]
            if col_tahapan and col_tahapan in df_clean.columns:
                s_tahap = df_clean[col_tahapan].astype(str).str.strip().str.lower()
                act_p2 = [s_tahap.str.contains(s.lower()[:5], na=False).sum() for s in steps]
            else:
                act_p2 = [0] * len(steps)
            st.plotly_chart(make_combo_chart(steps, target_p2, act_p2, "2. Target vs Aktual by Tahapan SS"), use_container_width=True)

        # ----------------- GRAFIK 3 & 4 -----------------
        c3, c4 = st.columns(2)

        with c3:
            # 3. Target vs Aktual by Departemen
            depts = ["Production", "Logistic", "QA/QC", "HR"]
            target_p3 = [16, 12, 3, 3]
            act_p3 = []
            if col_dept and col_dept in df_clean.columns:
                s_dept = df_clean[col_dept].astype(str).str.strip().str.lower()
                cnt_prod = s_dept.str.contains('prod|pbr|produksi|production', regex=True, na=False).sum()
                cnt_log = s_dept.str.contains('log|wh|ware|gudang|logistik|logistic', regex=True, na=False).sum()
                cnt_qa = s_dept.str.contains('qa|qc|quality', regex=True, na=False).sum()
                cnt_hr = s_dept.str.contains('hr|ga|person|human|personalia', regex=True, na=False).sum()
                act_p3 = [cnt_prod, cnt_log, cnt_qa, cnt_hr]
            else:
                act_p3 = [0] * len(depts)
            st.plotly_chart(make_combo_chart(depts, target_p3, act_p3, "3. Target vs Aktual by Departemen"), use_container_width=True)

        with c4:
            # 4. Target vs Aktual by Line/Section
            lines_cfg = [
                {"name": "SHP", "target": 7, "keys": "shp"},
                {"name": "WH", "target": 5, "keys": "wh|ware|gudang"},
                {"name": "STEX", "target": 4, "keys": "stex"},
                {"name": "PPEX/DFAS", "target": 4, "keys": "ppex|dfas"},
                {"name": "PVMX", "target": 3, "keys": "pvmx"},
                {"name": "QA/QC", "target": 3, "keys": "qa|qc"},
                {"name": "BTEX", "target": 3, "keys": "btex"},
                {"name": "MTC", "target": 3, "keys": "mtc|maint|maintenance"},
                {"name": "ORMX", "target": 2, "keys": "ormx"}
            ]
            lines = [item_cfg["name"] for item_cfg in lines_cfg]
            target_p4 = [item_cfg["target"] for item_cfg in lines_cfg]
            act_p4 = []
            if col_line and col_line in df_clean.columns:
                s_line = df_clean[col_line].astype(str).str.strip().str.lower()
                for item_cfg in lines_cfg:
                    cnt = s_line.str.contains(item_cfg["keys"], regex=True, na=False).sum()
                    act_p4.append(cnt)
            else:
                act_p4 = [0] * len(lines)
            st.plotly_chart(make_combo_chart(lines, target_p4, act_p4, "4. Target vs Aktual by Line/Section"), use_container_width=True)

        # ----------------- GRAFIK 5 -----------------
        # 5. Target Penyelesaian Aktivitas SS (Status Close)
        target_p5 = [0, 0, 34, 64, 93, 127, 157, 186, 220, 250, 279, 313]
        act_p5 = []
        if col_status and col_bulan and col_status in df_clean.columns and col_bulan in df_clean.columns:
            df_close_only = df_clean[df_clean[col_status].astype(str).str.strip().str.upper() == 'CLOSE'].copy()
            s_close_bulan = df_close_only[col_bulan].astype(str).str.strip().str.lower()
            for keys in month_keys:
                c_cnt = s_close_bulan.apply(lambda x: any(k in x for k in keys)).sum()
                act_p5.append(c_cnt)
        else:
            act_p5 = [0] * 12
        st.plotly_chart(make_combo_chart(months_display, target_p5, act_p5, "5. Target Penyelesaian Aktivitas SS (Status Close)"), use_container_width=True)

        # ----------------- KESIMPULAN OTOMATIS & ARAHAN -----------------
        st.markdown("---")
        st.subheader("💡 Kesimpulan Otomatis & Arahan Tindak Lanjut")

        pct_close = (cnt_close / total_all * 100) if total_all > 0 else 0

        if col_tahapan and col_tahapan in df_clean.columns and total_all > 0:
            tahapan_pct = (df_clean[col_tahapan].dropna().value_counts(normalize=True) * 100).round(1)
            rincian_list = [f"**{val}%** berada di tahap *{idx}*" for idx, val in tahapan_pct.items()]
            rincian_str = ", ".join(rincian_list)
            
            st.info(f"""
            📌 **RINGKASAN PERFORMANSA UMUM:**
            * **Pencapaian Penyelesaian:** Saat ini baru **{pct_close:.1f}%** dari total usulan sumbang saran yang berstatus **Close**.
            * **Rincian Sebaran Tahapan SS:** {rincian_str}.
            """)

        # TABEL ARAHAN PER LINE/SECTION
        st.markdown("### 🎯 Kesimpulan & Arahan per Line/Section")
        line_summary_data = []
        for idx, item_cfg in enumerate(lines_cfg):
            actual_val = act_p4[idx]
            target_val = item_cfg["target"]
            achieve_pct = (actual_val / target_val * 100) if target_val > 0 else 0
            
            if actual_val == 0:
                status_tag = "🔴 Belum Ada Ide"
                arahan = "Wajib mengadakan briefing harian/mingguan untuk menggali ide di area kerja."
            elif actual_val < target_val:
                status_tag = "🟡 Belum Mencapai Target"
                arahan = f"Kurang {target_val - actual_val} ide. Supervisor diminta mengawal pengajuan ide."
            else:
                status_tag = "🟢 Target Tercapai"
                arahan = "Pencapaian sangat baik. Kawal implementasi hingga status Close."

            line_summary_data.append({
                "Line / Section": item_cfg["name"],
                "Target": target_val,
                "Aktual": actual_val,
                "Pencapaian (%)": f"{achieve_pct:.1f}%",
                "Status": status_tag,
                "Arahan Tindak Lanjut": arahan
            })

        st.dataframe(pd.DataFrame(line_summary_data), use_container_width=True, hide_index=True)

        # MENU LIPAT TABEL DATA LIVE
        st.markdown("---")
        with st.expander("📋 Lihat Menu Lipat Tabel Data Live dari Google Sheets"):
            st.dataframe(df_clean, use_container_width=True)

    else:
        st.warning("Data dari Google Sheets kosong atau tidak dapat diakses.")

except Exception as e:
    st.error(f"Gagal memproses data. Detail Error: {e}")