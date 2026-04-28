import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import json
from shapely.geometry import shape, Point
from streamlit_gsheets import GSheetsConnection

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

    /* Menghilangkan Header Default */
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
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
    }
    
    hr { border: 0; border-top: 1px solid #30363d; margin: 25px 0; }
    </style>
    """, unsafe_allow_html=True)

# 2. KONSTANTA ACUAN
N_OPTIMAL = 80.0
PH_MIN = 5.5
PH_MAX = 6.8

if 'clicked_data' not in st.session_state:
    st.session_state.clicked_data = None

# 3. FUNGSI DATA (KONEKSI GOOGLE SHEETS)
@st.cache_data(ttl=60) # Refresh data setiap 60 detik
def load_data_from_sheets():
    # URL Google Sheet Mas Wildan
    url = "https://docs.google.com/spreadsheets/d/1tDeGWOU8EyLa7rgxCcRVXAu05CcezDFlI9K0SmIPN1Y/edit?usp=sharing"
    conn = st.connection("gsheets", type=GSheetsConnection)
    data = conn.read(spreadsheet=url)
    return data

@st.cache_data
def load_map_data():
    try:
        with open('peta_desa.json') as f:
            return json.load(f)
    except:
        return None

def ambil_info_lokasi(lat, lon, geo_data):
    if not geo_data: return "Unknown", "-"
    p = Point(lon, lat)
    for feat in geo_data['features']:
        if shape(feat['geometry']).contains(p):
            return feat['properties'].get('ds', 'Tidak Diketahui'), feat['properties'].get('kec', '-')
    return "Luar Wilayah", "-"

# --- PROSES DATA UTAMA (VERSI ANTI-ERROR) ---
try:
    # 1. Ambil data mentah dari Sheets
    df_raw = load_data_from_sheets()
    
    # 2. Paksa konversi kolom-kolom penting ke angka
    # Jika ada teks nyasar, akan diubah jadi NaN (kosong) agar tidak bikin crash
    cols_to_fix = ['lat', 'lon', 'n', 'p', 'k', 'ph', 'ec', 'temp', 'moist']
    for col in cols_to_fix:
        df_raw[col] = pd.to_numeric(df_raw[col], errors='coerce')
    
    # 3. Bersihkan baris yang koordinatnya kosong/rusak
    df = df_raw.dropna(subset=['lat', 'lon']).copy()
    
    # 4. Load data peta desa
    geo_desa = load_map_data()
    
    # 5. Cek apakah setelah dibersihkan masih ada datanya
    if df.empty:
        st.warning(" Data di Google Sheets belum valid. Pastikan lat/lon menggunakan titik (bukan koma).")
        st.stop()
        
except Exception as e:
    st.error(f" Gagal memproses data: {e}")
    st.stop()

# 4. SIDEBAR
with st.sidebar:
    st.markdown("<h2 style='color:white; margin-bottom:0;'>WILDANTECH</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color:#8b949e; font-size:12px;'>Intelijen Tanah & Pranoto Mongso</p>", unsafe_allow_html=True)
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
    st.info("Sistem ini siap diintegrasikan dengan kalender Pranoto Mongso untuk optimasi masa tanam.")

# 5. HEADER & METRIK
st.markdown("<h1 style='margin-bottom:0;'>Dashboard Pertanian Presisi Cabai</h1>", unsafe_allow_html=True)
st.markdown("<p style='color:#8b949e;'>Data Real-Time dari Google Sheets (Cloud Integrated)</p>", unsafe_allow_html=True)

# Memilih data tampil (klik atau baris terakhir)
d = st.session_state.clicked_data if st.session_state.clicked_data is not None else df.iloc[-1]

# Info Tanggal
if 'tanggal' in d:
    st.write(f"🕒 **Waktu Pengambilan Data:** {d['tanggal']}")

cols = st.columns(7)
m_items = [
    ("Nitrogen", 'n', 'mg/kg'), ("Fosfor", 'p', 'mg/kg'), ("Kalium", 'k', 'mg/kg'),
    ("Tingkat pH", 'ph', ''), ("Kelembaban", 'moist', '%'), ("Suhu", 'temp', '°C'), ("Salinitas", 'ec', '')
]

for i, (label, key, unit) in enumerate(m_items):
    cols[i].metric(label, f"{d[key]}{unit}")

st.markdown("---")

# 6. KONTEN UTAMA (PETA & ANALISIS)
col_kiri, col_kanan = st.columns([2.5, 1])

with col_kiri:
    st.markdown("<h3 style='font-size:18px; color:white;'>Pemetaan Geospasial Lahan</h3>", unsafe_allow_html=True)
    
    m = folium.Map(
        location=[d['lat'], d['lon']], 
        zoom_start=14, 
        tiles="CartoDB dark_matter",
        prefer_canvas=True
    )

    if geo_desa:
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

    for row in df.itertuples():
        # Logika warna titik
        is_opt = row.n >= N_OPTIMAL and PH_MIN <= row.ph <= PH_MAX
        
        folium.CircleMarker(
            location=[row.lat, row.lon],
            radius=14,
            color="#238636" if is_opt else "#da3633",
            fill=True,
            fill_opacity=0.4,
            popup=f"ID Titik: {int(row.id)}",
        ).add_to(m)

    m_out = st_folium(m, width="100%", height=520, key="map_engine", returned_objects=["last_object_clicked_popup"])

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
            <p style='color:#8b949e; font-size:12px; margin-bottom:4px;'>LOKASI ID #{int(sel['id'])}</p>
            <h2 style='color:white; margin:0;'>Desa {ds}</h2>
            <p style='color:#8b949e; font-size:14px;'>Kecamatan {kc}</p>
            <hr>
            <p style='font-size:14px;'>Status Lahan:</p>
            {"<span class='status-badge' style='background:#238636; color:#ffffff;'>Kondisi Optimal</span>" if sel['n'] >= N_OPTIMAL else "<span class='status-badge' style='background:#da3633; color:#ffffff;'>Perlu Perbaikan</span>"}
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        if sel['ph'] < PH_MIN:
            st.warning(f"pH Tanah ({sel['ph']}) terlalu asam. Tambahkan Kapur Dolomit.")
        if sel['n'] < N_OPTIMAL:
            st.error(f"Defisit Nitrogen: Butuh intervensi pupuk Urea/ZA.")
            
        if st.button("Reset Fokus"):
            st.session_state.clicked_data = None
            st.rerun()
    else:
        st.info("Klik titik pada peta untuk melihat data spesifik.")
        st.markdown("### Histori Terbaru")
        st.dataframe(df[['id', 'tanggal', 'n', 'ph']].tail(5), use_container_width=True)

# 7. FOOTER
st.markdown("<br><hr><center style='color:#8b949e; font-size:12px;'>WILDANTECH PRECISION AGRICULTURE | WONOSOBO 2026</center>", unsafe_allow_html=True)
