import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import json
import requests
from shapely.geometry import shape, Point
from streamlit_gsheets import GSheetsConnection

# 1. KONFIGURASI HALAMAN
st.set_page_config(
    page_title="Wildantech | Intelligence Dashboard",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- CSS: DESAIN MODERN (SESUAI REQUEST MOBILE STABLE) ---
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

# 2. FUNGSI PENGAMBILAN DATA & ELEVASI
def get_elevation(lat, lon):
    """Mengambil data MDPL secara otomatis via API Open-Topo"""
    try:
        url = f"https://api.opentopodata.org/v1/srtm30m?locations={lat},{lon}"
        response = requests.get(url, timeout=3)
        if response.status_code == 200:
            elev = response.json()['results'][0]['elevation']
            return f"{int(elev)} MDPL" if elev else "Wonosobo"
        return "Wonosobo"
    except:
        return "Wonosobo"

@st.cache_data(ttl=10) # Set kecil 10 detik agar data kiriman ESP32 cepat muncul saat di-refresh
def get_data():
    url = "https://docs.google.com/spreadsheets/d/1tDeGWOU8EyLa7rgxCcRVXAu05CcezDFlI9K0SmIPN1Y/edit?usp=sharing"
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(spreadsheet=url)
        df.columns = df.columns.str.strip().str.lower()
        
        # SINKRONISASI KOLOM INTI
        cols = ['lat', 'lon', 'n', 'p', 'k', 'ph', 'ec', 'temp', 'moist']
        for c in cols:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c].astype(str).str.replace(',', '.'), errors='coerce')
        return df.dropna(subset=['lat', 'lon'])
    except Exception as e:
        st.error(f"Gagal memuat Google Sheets: {e}")
        return pd.DataFrame()

@st.cache_data
def get_geojson():
    try:
        with open('peta_desa.json', 'r') as f:
            return json.load(f)
    except:
        return None

# 3. LOGIKA WILAYAH
def get_village_info(lat, lon, g_data):
    if not g_data: return "Wonosobo", "Jawa Tengah"
    p = Point(lon, lat)
    for feat in g_data['features']:
        if shape(feat['geometry']).contains(p):
            return feat['properties'].get('ds', 'Terdeteksi'), feat['properties'].get('kec', '-')
    return "Luar Area", "-"

# 4. STATE MANAGEMENT
if 'selected_id' not in st.session_state:
    st.session_state.selected_id = None

df = get_data()
geo_desa = get_geojson()

# --- SIDEBAR ---
with st.sidebar:
    st.title("Panel Kontrol")
    if st.button("Reset Tampilan"):
        st.session_state.selected_id = None
        st.rerun()

# --- VISUALISASI PETA ---
center_lat = df['lat'].mean() if not df.empty else -7.35
center_lon = df['lon'].mean() if not df.empty else 109.9

m = folium.Map(location=[center_lat, center_lon], zoom_start=13, tiles="CartoDB dark_matter", zoom_control=False)

if geo_desa:
    folium.GeoJson(geo_desa, style_function=lambda x: {'fillColor': '#238636', 'color': '#deff9a', 'weight': 1, 'fillOpacity': 0.1}).add_to(m)

if not df.empty:
    for row in df.itertuples():
        # Indikator Dinas: Merah jika tanah kritis (N rendah atau pH ekstrem)
        status_warna = "#deff9a" if (5.5 <= row.ph <= 7.0 and row.n >= 80) else "#ff4b4b"
        folium.CircleMarker(
            location=[row.lat, row.lon], radius=12, color=status_warna, fill=True, fill_opacity=0.8,
            popup=f"ID:{int(row.id)}"
        ).add_to(m)

out = st_folium(m, width="100%", height=850, returned_objects=["last_object_clicked_popup"])

if out and out.get("last_object_clicked_popup"):
    try:
        new_id = int(out["last_object_clicked_popup"].split(":")[1])
        if st.session_state.selected_id != new_id:
            st.session_state.selected_id = new_id
            st.rerun()
    except:
        pass

# --- TAMPILAN KARTU INFORMASI ---
if st.session_state.selected_id and not df.empty:
    target_rows = df[df['id'] == st.session_state.selected_id]
    if not target_rows.empty:
        s = target_rows.iloc[0]
        ds, kc = get_village_info(s['lat'], s['lon'], geo_desa)
        mdpl = get_elevation(s['lat'], s['lon'])
        
        # Cek jika kolom tanaman tersedia di sheets
        nama_tanaman = s['tanaman'].upper() if 'tanaman' in df.columns and pd.notna(s['tanaman']) else "UMUM"
        
        st.markdown(f"""
        <div class="floating-card">
            <div style="margin-bottom: 10px;">
                <span style="color:#deff9a; font-size:10px; font-weight:bold; letter-spacing:1px;">WILDANTECH MONITORING ({nama_tanaman})</span>
                <h2 style="margin:2px 0 0 0; font-size:22px;">Desa {ds}</h2>
                <p style="margin:0; opacity:0.6; font-size:12px;">Kecamatan {kc} | ID: {int(s['id'])} | <b>{mdpl}</b></p>
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

        # BAGIAN ANALISIS UNTUK DINAS (EXPANDER)
        with st.expander("DATA ANALISIS DINAS & REKOMENDASI"):
            prioritas = "TINGGI (Kritis)" if (s['n'] < 50 or s['ph'] < 5.0) else "Normal"
            st.write(f"**Status Lahan:** {prioritas}")
            
            if s['n'] < 80:
                st.error("Rekomendasi: Subsidi pupuk Nitrogen (Urea/ZA) diperlukan di titik ini.")
            if s['ph'] < 5.5:
                st.warning("Kondisi: Tanah Asam. Butuh intervensi Kapur Dolomit.")
            elif s['ph'] > 7.5:
                st.warning("Kondisi: Tanah Basa. Butuh aplikasi Belerang.")
            else:
                st.success("Kondisi: Tanah sehat dan optimal.")
                
            st.divider()
            st.info("Data EC menunjukkan kemampuan tanah dalam menghantar nutrisi. Nilai rendah menandakan tanah butuh pembenah organik.")

        st.markdown("</div>", unsafe_allow_html=True)
