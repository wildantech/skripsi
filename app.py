import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import json
from shapely.geometry import shape, Point
from streamlit_gsheets import GSheetsConnection

# 1. KONFIGURASI HALAMAN
st.set_page_config(
    page_title="Wildantech | Pertanian Presisi", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS: DESAIN DARK MODE (TANPA EMOJI) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
    .stApp { background-color: #0b0e11; color: #e1e4e8; }
    h1, h2, h3, p, span, div { font-family: 'Inter', sans-serif !important; }
    header {visibility: hidden;}
    button[kind="headerNoPadding"] { display: none; }
    [data-testid="stSidebar"] { background-color: #111418; border-right: 1px solid #1f2428; }
    div[data-testid="stMetricContainer"] {
        background: linear-gradient(145deg, #161b22, #0d1117);
        border: 1px solid #238636;
        border-radius: 12px;
        padding: 20px;
    }
    div[data-testid="stMetricValue"] { color: #4caf50 !important; font-weight: 700; }
    .info-card { background: #0d1117; border: 1px solid #30363d; border-radius: 12px; padding: 24px; }
    .status-badge { padding: 6px 14px; border-radius: 20px; font-size: 11px; font-weight: 600; text-transform: uppercase; }
    hr { border: 0; border-top: 1px solid #30363d; margin: 25px 0; }
    </style>
    """, unsafe_allow_html=True)

# 2. KONSTANTA ACUAN
N_OPTIMAL = 80.0
PH_MIN = 5.5
PH_MAX = 6.8

# 3. FUNGSI DATA
@st.cache_data(ttl=60)
def load_gsheets_data():
    url = "https://docs.google.com/spreadsheets/d/1tDeGWOU8EyLa7rgxCcRVXAu05CcezDFlI9K0SmIPN1Y/edit?usp=sharing"
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_raw = conn.read(spreadsheet=url)
        # Konversi kolom ke angka secara paksa
        cols = ['lat', 'lon', 'n', 'p', 'k', 'ph', 'ec', 'temp', 'moist']
        for col in cols:
            if col in df_raw.columns:
                df_raw[col] = pd.to_numeric(df_raw[col], errors='coerce')
        return df_raw.dropna(subset=['lat', 'lon']).reset_index(drop=True)
    except:
        return pd.DataFrame()

@st.cache_data
def load_map_json():
    try:
        with open('peta_desa.json') as f:
            return json.load(f)
    except:
        return None

def ambil_info_lokasi(lat, lon, geo_data):
    if not geo_data: return "Luar Wilayah", "-"
    try:
        p = Point(lon, lat)
        for feat in geo_data['features']:
            if shape(feat['geometry']).contains(p):
                return feat['properties'].get('ds', 'Tidak Diketahui'), feat['properties'].get('kec', '-')
    except: pass
    return "Luar Wilayah", "-"

# --- PROSES DATA ---
df = load_gsheets_data()
geo_desa = load_map_json()

if df.empty:
    st.error("Gagal memuat data dari Google Sheets atau data kosong.")
    st.stop()

if 'clicked_id' not in st.session_state:
    st.session_state.clicked_id = df.iloc[-1]['id']

# Data yang dipilih untuk ditampilkan di metrik
selected_row = df[df['id'] == st.session_state.clicked_id].iloc[0]

# 4. SIDEBAR
with st.sidebar:
    st.markdown("<h2 style='color:white; margin-bottom:0;'>WILDANTECH</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color:#8b949e; font-size:12px;'>Platform Intelijen Tanah</p>", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("### Standar Ideal Cabai")
    st.markdown("<div style='font-size:14px; color:#c9d1d9;'>• Nitrogen: > 80 mg/kg<br>• pH Tanah: 5.5 - 6.8</div>", unsafe_allow_html=True)
    st.markdown("---")
    st.caption("Lokasi: Wonosobo")

# 5. HEADER & METRIK
st.markdown("<h1 style='margin-bottom:0;'>Dashboard Pertanian Presisi Cabai</h1>", unsafe_allow_html=True)
st.markdown("<p style='color:#8b949e;'>Monitoring Nutrisi Tanah Berbasis Google Sheets Cloud</p>", unsafe_allow_html=True)

m_cols = st.columns(7)
m_items = [("Nitrogen", 'n', ' mg/kg'), ("Fosfor", 'p', ' mg/kg'), ("Kalium", 'k', ' mg/kg'),
           ("pH Tanah", 'ph', ''), ("Lembap", 'moist', '%'), ("Suhu", 'temp', '°C'), ("EC", 'ec', '')]

for i, (label, key, unit) in enumerate(m_items):
    val = round(selected_row[key], 1) if not pd.isna(selected_row[key]) else 0
    m_cols[i].metric(label, f"{val}{unit}")

st.markdown("---")

# 6. PETA & ANALISIS
col_kiri, col_kanan = st.columns([2.5, 1])

with col_kiri:
    st.markdown("<h3 style='font-size:18px; color:white;'>Pemetaan Geospasial Lahan</h3>", unsafe_allow_html=True)
    
    m = folium.Map(location=[selected_row['lat'], selected_row['lon']], zoom_start=13, tiles="CartoDB dark_matter")

    if geo_desa:
        folium.GeoJson(
            geo_desa, 
            style_function=lambda x: {'fillColor': '#238636', 'color': '#4caf50', 'weight': 1.5, 'fillOpacity': 0.1}
        ).add_to(m)

    # Render Semua Titik
    for row in df.itertuples():
        is_opt = row.n >= N_OPTIMAL and PH_MIN <= row.ph <= PH_MAX
        folium.CircleMarker(
            location=[row.lat, row.lon],
            radius=12,
            color="#238636" if is_opt else "#da3633",
            fill=True,
            fill_opacity=0.6,
            popup=f"ID:{int(row.id)}",
        ).add_to(m)

    m_out = st_folium(m, width="100%", height=520, key="map_engine")

    # Logika Klik
    if m_out and m_out.get("last_object_clicked_popup"):
        try:
            new_id = int(m_out["last_object_clicked_popup"].split(":")[1])
            if new_id != st.session_state.clicked_id:
                st.session_state.clicked_id = new_id
                st.rerun()
        except: pass

with col_kanan:
    st.markdown("<h3 style='font-size:18px; color:white;'>Analisis Teknis</h3>", unsafe_allow_html=True)
    ds, kc = ambil_info_lokasi(selected_row['lat'], selected_row['lon'], geo_desa)
    
    st.markdown(f"""
    <div class="info-card">
        <p style='color:#8b949e; font-size:12px; margin-bottom:4px;'>LOKASI ID #{int(selected_row['id'])}</p>
        <h2 style='color:white; margin:0;'>Desa {ds}</h2>
        <p style='color:#8b949e; font-size:14px;'>Kecamatan {kc}</p>
        <hr>
        {"<span class='status-badge' style='background:#238636;'>Kondisi Optimal</span>" if selected_row['n'] >= N_OPTIMAL else "<span class='status-badge' style='background:#da3633;'>Perlu Perbaikan</span>"}
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    if selected_row['ph'] < PH_MIN:
        st.warning(f"pH Tanah rendah ({selected_row['ph']}). Aplikasi Kapur Dolomit diperlukan.")
    if selected_row['n'] < N_OPTIMAL:
        st.error(f"Defisit Nitrogen. Diperlukan aplikasi pupuk N tambahan.")
        
    if st.button("Tampilkan Data Terbaru"):
        st.session_state.clicked_id = df.iloc[-1]['id']
        st.rerun()

st.markdown("<br><hr><center style='color:#8b949e; font-size:12px;'>WILDANTECH PRECISION AGRICULTURE | WONOSOBO 2026</center>", unsafe_allow_html=True)
