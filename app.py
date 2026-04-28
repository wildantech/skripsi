import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import json
from shapely.geometry import shape, Point

# 1. KONFIGURASI HALAMAN
st.set_page_config(
    page_title="Wildantech | Pertanian Presisi Cabai", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS: DESAIN PROFESIONAL HIJAU & DARK MODE ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
    
    /* Global Styles */
    .stApp { background-color: #0b0e11; color: #e1e4e8; }
    h1, h2, h3, p, span, div { font-family: 'Inter', sans-serif !important; }

    /* Menghilangkan Header Default & Bug Arrow */
    header {visibility: hidden;}
    button[kind="headerNoPadding"] { display: none; }
    
    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: #111418;
        border-right: 1px solid #1f2428;
    }

    /* Metric Card Custom (Aksen Hijau) */
    div[data-testid="stMetricContainer"] {
        background: linear-gradient(145deg, #161b22, #0d1117);
        border: 1px solid #238636;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.3);
    }
    div[data-testid="stMetricValue"] { color: #4caf50 !important; font-weight: 700; }
    div[data-testid="stMetricLabel"] { color: #8b949e !important; font-size: 13px; text-transform: uppercase; letter-spacing: 1px; }

    /* Card Analisis di Panel Kanan */
    .info-card {
        background: #0d1117;
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 24px;
    }
    .status-badge {
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        text-transform: uppercase;
    }
    
    hr { border: 0; border-top: 1px solid #30363d; margin: 25px 0; }
    </style>
    """, unsafe_allow_html=True)

# 2. KONSTANTA ACUAN (STANDAR CABAI)
N_OPTIMAL = 80.0
PH_MIN = 5.5
PH_MAX = 6.8

if 'clicked_data' not in st.session_state:
    st.session_state.clicked_data = None

# 3. FUNGSI DATA (DENGAN CACHE)
@st.cache_data
def load_map_data():
    with open('peta_desa.json') as f:
        return json.load(f)

@st.cache_data
def load_csv():
    try:
        return pd.read_csv('data_tanah.csv')
    except:
        return pd.DataFrame({
            'id': [1], 'lat': [-7.360], 'lon': [109.902],
            'n': [45.0], 'p': [30.0], 'k': [55.0], 'ph': [6.2], 
            'ec': [400], 'temp': [27.0], 'moist': [35.0]
        })

def ambil_info_lokasi(lat, lon, geo_data):
    p = Point(lon, lat)
    for feat in geo_data['features']:
        if shape(feat['geometry']).contains(p):
            return feat['properties'].get('ds', 'Tidak Diketahui'), feat['properties'].get('kec', '-')
    return "Luar Wilayah", "-"

# --- PROSES DATA UTAMA ---
df = load_csv()
geo_desa = load_map_data()

# 4. SIDEBAR: REFERENSI & INFO SISTEM
with st.sidebar:
    st.markdown("<h2 style='color:white; margin-bottom:0;'>WILDANTECH</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color:#8b949e; font-size:12px;'>Platform Intelijen Tanah</p>", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("### Standar Ideal Cabai")
    st.markdown("""
    <div style='font-size:14px; color:#c9d1d9;'>
    • Nitrogen: > 80 mg/kg<br>
    • pH Tanah: 5.5 - 6.8<br>
    • Kelembaban: 60 - 80%
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")
    st.caption("Lokasi Deployment: Wonosobo")

# 5. HEADER & RINGKASAN METRIK
st.markdown("<h1 style='margin-bottom:0;'>Dashboard Pertanian Presisi Cabai</h1>", unsafe_allow_html=True)
st.markdown("<p style='color:#8b949e;'>Monitoring Nutrisi Makro dan Mikro Tanah Real-Time</p>", unsafe_allow_html=True)

# Memilih data yang akan ditampilkan (klik atau terbaru)
d = st.session_state.clicked_data if st.session_state.clicked_data is not None else df.iloc[-1]

cols = st.columns(7)
m_items = [
    ("Nitrogen", 'n', 'mg/kg'), ("Fosfor", 'p', 'mg/kg'), ("Kalium", 'k', 'mg/kg'),
    ("Tingkat pH", 'ph', ''), ("Kelembaban", 'moist', '%'), ("Suhu", 'temp', '°C'), ("Salinitas (EC)", 'ec', '')
]

for i, (label, key, unit) in enumerate(m_items):
    cols[i].metric(label, f"{d[key]}{unit}")

st.markdown("---")

# 6. KONTEN UTAMA (PETA & ANALISIS)
col_kiri, col_kanan = st.columns([2.5, 1])

with col_kiri:
    st.markdown("<h3 style='font-size:18px; color:white;'>Pemetaan Geospasial Lahan</h3>", unsafe_allow_html=True)
    
    # Inisialisasi Peta
    m = folium.Map(
        location=[d['lat'], d['lon']], 
        zoom_start=14, 
        tiles="CartoDB dark_matter",
        prefer_canvas=True
    )

    # Layer Batas Desa (Warna Hijau Sesuai Request)
    folium.GeoJson(
        geo_desa, 
        smooth_factor=2.0,
        style_function=lambda x: {
            'fillColor': '#238636', 
            'color': '#4caf50', 
            'weight': 1.5, 
            'fillOpacity': 0.1
        }
    ).add_to(m)

    # Render Titik Sensor (Gunakan itertuples agar ringan di RAM 8GB)
    for row in df.itertuples():
        kondisi_oke = row.n >= N_OPTIMAL and PH_MIN <= row.ph <= PH_MAX
        warna_titik = "#238636" if kondisi_oke else "#da3633"
        
        folium.CircleMarker(
            location=[row.lat, row.lon],
            radius=14,
            color=warna_titik,
            fill=True,
            fill_opacity=0.4,
            popup=f"ID Titik: {int(row.id)}",
        ).add_to(m)

    # Menangkap Interaksi Peta
    m_out = st_folium(
        m, 
        width="100%", 
        height=520, 
        key="map_engine",
        returned_objects=["last_object_clicked_popup"]
    )

    # Logika Klik
    if m_out['last_object_clicked_popup']:
        try:
            target_id = int(m_out['last_object_clicked_popup'].split(": ")[1])
            st.session_state.clicked_data = df[df['id'] == target_id].iloc[0]
            st.rerun()
        except: pass

with col_kanan:
    st.markdown("<h3 style='font-size:18px; color:white;'>Analisis Teknis</h3>", unsafe_allow_html=True)
    
    if st.session_state.clicked_data is not None:
        sel = st.session_state.clicked_data
        ds, kc = ambil_info_lokasi(sel['lat'], sel['lon'], geo_desa)
        
        st.markdown(f"""
        <div class="info-card">
            <p style='color:#8b949e; font-size:12px; margin-bottom:4px;'>ID LOKASI #{int(sel['id'])}</p>
            <h2 style='color:white; margin:0;'>Desa {ds}</h2>
            <p style='color:#8b949e; font-size:14px;'>Kecamatan {kc}</p>
            <hr>
            <p style='font-size:14px;'>Status Lahan:</p>
            {"<span class='status-badge' style='background:#238636; color:#ffffff;'>Kondisi Optimal</span>" if sel['n'] >= N_OPTIMAL else "<span class='status-badge' style='background:#da3633; color:#ffffff;'>Perlu Perbaikan</span>"}
        </div>
        """, unsafe_allow_html=True)
        
        # Rekomendasi Berbasis Data
        st.markdown("<br>", unsafe_allow_html=True)
        if sel['ph'] < PH_MIN:
            st.warning(f"Anomali pH: Nilai {sel['ph']} terlalu asam. Disarankan aplikasi Kapur Dolomit.")
        if sel['n'] < N_OPTIMAL:
            st.error(f"Defisit Unsur N: Butuh intervensi pupuk Urea/ZA sebesar {round(N_OPTIMAL - sel['n'], 2)} mg/kg.")
            
        if st.button("Reset Fokus"):
            st.session_state.clicked_data = None
            st.rerun()
    else:
        st.info("Klik titik pada peta untuk melihat data teknis dan rekomendasi spesifik.")
        st.markdown("### Data Terbaru")
        st.dataframe(df[['id', 'n', 'ph', 'moist']].tail(4), use_container_width=True)

# 7. FOOTER
st.markdown("<br><hr><center style='color:#8b949e; font-size:12px;'>WILDANTECH PRECISION AGRICULTURE | WONOSOBO 2026</center>", unsafe_allow_html=True)