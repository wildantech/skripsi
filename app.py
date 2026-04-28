import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import json
from shapely.geometry import shape, Point
from streamlit_gsheets import GSheetsConnection

# 1. KONFIGURASI HALAMAN UTAMA
st.set_page_config(
    page_title="Wildantech | Intelligence Dashboard",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- CSS: DESAIN MODERN FORMAL (MENCEGAH KEBOCORAN KODE) ---
st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] > section:nth-child(2) { padding: 0 !important; }
    .block-container { padding: 0 !important; max-width: 100% !important; }
    header, footer { visibility: hidden; }
    
    .floating-card {
        position: fixed;
        top: 20px;
        right: 20px;
        width: 350px;
        background: rgba(13, 17, 23, 0.95);
        backdrop-filter: blur(15px);
        border: 1px solid rgba(222, 255, 154, 0.3);
        border-radius: 15px;
        padding: 20px;
        z-index: 10000;
        color: white;
        box-shadow: 0 10px 30px rgba(0,0,0,0.5);
    }
    
    .grid-metrics {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 10px;
        margin-top: 10px;
    }
    
    .metric-small {
        background: rgba(255,255,255,0.05);
        padding: 8px;
        border-radius: 8px;
        border-left: 3px solid #deff9a;
    }
    </style>
    """, unsafe_allow_html=True)

# 2. FUNGSI PENGAMBILAN DATA
@st.cache_data(ttl=60)
def get_data():
    url = "https://docs.google.com/spreadsheets/d/1tDeGWOU8EyLa7rgxCcRVXAu05CcezDFlI9K0SmIPN1Y/edit?usp=sharing"
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(spreadsheet=url)
        df.columns = df.columns.str.strip().str.lower()
        # Memastikan semua variabel sensor terkonversi ke angka
        cols = ['lat', 'lon', 'n', 'p', 'k', 'ph', 'ec', 'temp', 'moist']
        for c in cols:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c].astype(str).str.replace(',', '.'), errors='coerce')
        return df.dropna(subset=['lat', 'lon'])
    except:
        return pd.DataFrame()

@st.cache_data
def get_geojson():
    try:
        with open('peta_desa.json', 'r') as f:
            return json.load(f)
    except:
        return None

# 3. LOGIKA STATE MANAJEMEN
if 'selected_id' not in st.session_state:
    st.session_state.selected_id = None

df = get_data()
geo_desa = get_geojson()

def get_village_info(lat, lon, g_data):
    if not g_data: return "Wonosobo", "Jawa Tengah"
    p = Point(lon, lat)
    for feat in g_data['features']:
        if shape(feat['geometry']).contains(p):
            return feat['properties'].get('ds', 'Wilayah Terdeteksi'), feat['properties'].get('kec', '-')
    return "Luar Area", "-"

# --- SIDEBAR NAVIGASI ---
with st.sidebar:
    st.title("Panel Kontrol")
    if st.button("Reset / Bersihkan Tampilan"):
        st.session_state.selected_id = None
        st.rerun()

# --- VISUALISASI PETA UTAMA ---
# Titik fokus awal peta (rata-rata koordinat sensor)
center_lat = df['lat'].mean() if not df.empty else -7.35
center_lon = df['lon'].mean() if not df.empty else 109.9

m = folium.Map(location=[center_lat, center_lon], zoom_start=13, tiles="CartoDB dark_matter", zoom_control=False)

# Menampilkan Batas Desa dari GeoJSON
if geo_desa:
    folium.GeoJson(
        geo_desa, 
        style_function=lambda x: {
            'fillColor': '#238636', 
            'color': '#deff9a', 
            'weight': 1, 
            'fillOpacity': 0.1
        }
    ).add_to(m)

# Menampilkan Titik-Titik Sensor
for row in df.itertuples():
    # Warna titik berubah merah jika Nitrogen rendah atau pH tidak ideal
    status_warna = "#deff9a" if (5.5 <= row.ph <= 7.0 and row.n >= 80) else "#ff4b4b"
    folium.CircleMarker(
        location=[row.lat, row.lon],
        radius=12,
        color=status_warna,
        fill=True,
        fill_opacity=0.8,
        popup=f"ID:{int(row.id)}"
    ).add_to(m)

# Render Peta ke Streamlit
out = st_folium(m, width="100%", height=850, returned_objects=["last_object_clicked_popup"])

# Deteksi Interaksi Klik
if out and out.get("last_object_clicked_popup"):
    try:
        new_id = int(out["last_object_clicked_popup"].split(":")[1])
        if st.session_state.selected_id != new_id:
            st.session_state.selected_id = new_id
            st.rerun()
    except:
        pass

# --- TAMPILAN SISTEM PENDUKUNG KEPUTUSAN (KARTU INFORMASI) ---
if st.session_state.selected_id:
    s = df[df['id'] == st.session_state.selected_id].iloc[0]
    ds, kc = get_village_info(s['lat'], s['lon'], geo_desa)
    
    # Render Bagian Atas Kartu (HTML Statis + Variabel)
    st.markdown(f"""
    <div class="floating-card">
        <div style="margin-bottom: 10px;">
            <span style="color:#deff9a; font-size:10px; font-weight:bold; letter-spacing:1px;">WILDANTECH MONITORING</span>
            <h2 style="margin:2px 0 0 0; font-size:22px;">Desa {ds}</h2>
            <p style="margin:0; opacity:0.6; font-size:12px;">Kecamatan {kc} | ID Sensor: {int(s['id'])}</p>
        </div>
        <div style="border-top:1px solid rgba(255,255,255,0.1); padding-top:10px;">
            <div class="grid-metrics">
                <div class="metric-small"><small>Nitrogen (N)</small><br><b>{s['n']} mg/kg</b></div>
                <div class="metric-small"><small>Phosphor (P)</small><br><b>{s['p']} mg/kg</b></div>
                <div class="metric-small"><small>Kalium (K)</small><br><b>{s['k']} mg/kg</b></div>
                <div class="metric-small"><small>Tingkat pH</small><br><b>{s['ph']}</b></div>
                <div class="metric-small"><small>Suhu Tanah</small><br><b>{s['temp']}°C</b></div>
                <div class="metric-small"><small>Kelembapan</small><br><b>{s['moist']}%</b></div>
                <div class="metric-small" style="grid-column: span 2;"><small>Konduktivitas Listrik (EC)</small><br><b>{s['ec']} us/cm</b></div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Bagian Analisis (Decision Support System)
    with st.expander("ANALISIS DAN REKOMENDASI TEKNIS"):
        # Logika Nutrisi
        if s['n'] < 80:
            st.error("Rekomendasi: Kadar Nitrogen rendah. Diperlukan aplikasi pupuk Urea atau ZA.")
        if s['p'] < 50:
            st.error("Rekomendasi: Kadar Phosphor rendah. Diperlukan aplikasi pupuk SP-36.")
        
        # Logika Keasaman
        if s['ph'] < 5.5:
            st.warning("Kondisi: Tanah terlalu asam. Disarankan pemberian Kapur Dolomit.")
        elif s['ph'] > 7.5:
            st.warning("Kondisi: Tanah cenderung basa. Disarankan pemberian Belerang.")
        else:
            st.success("Kondisi: pH tanah berada pada rentang optimal untuk tanaman.")
            
        st.divider()
        st.write("**Laporan Analisis Strategis:**")
        prioritas = "Tinggi" if (s['n'] < 50 or s['ph'] < 5.0) else "Normal"
        st.write(f"Prioritas Alokasi Bantuan Nutrisi: **{prioritas}**")

    # Penutup Divisi Kartu
    st.markdown("</div>", unsafe_allow_html=True)
