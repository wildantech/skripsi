import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import json
from shapely.geometry import shape, Point
from streamlit_gsheets import GSheetsConnection

# 1. SETUP HALAMAN
st.set_page_config(
    page_title="Wildantech Dashboard",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- CSS FIX: FULL SCREEN & CARDS ---
st.markdown("""
    <style>
    /* Menghilangkan margin default streamlit */
    [data-testid="stAppViewContainer"] > section:nth-child(2) { padding: 0 !important; }
    .block-container { padding: 0 !important; max-width: 100% !important; }
    header, footer { visibility: hidden; }
    
    /* Kartu Melayang */
    .floating-card {
        position: fixed;
        top: 20px;
        right: 20px;
        width: 320px;
        background: rgba(13, 17, 23, 0.9);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(222, 255, 154, 0.3);
        border-radius: 20px;
        padding: 20px;
        z-index: 9999; /* Pastikan di atas peta */
        color: white;
        box-shadow: 0 10px 30px rgba(0,0,0,0.5);
    }
    
    .metric-item {
        background: rgba(255,255,255,0.05);
        margin: 8px 0;
        padding: 10px;
        border-radius: 10px;
        border-left: 4px solid #deff9a;
    }

    /* Tombol Tutup Modern */
    .stButton>button {
        width: 100%;
        background-color: #ff4b4b !important;
        color: white !important;
        border-radius: 10px !important;
    }
    </style>
    """, unsafe_allow_html=True)

# 2. LOAD DATA (GSheets & GeoJSON)
@st.cache_data(ttl=60)
def get_data():
    url = "https://docs.google.com/spreadsheets/d/1tDeGWOU8EyLa7rgxCcRVXAu05CcezDFlI9K0SmIPN1Y/edit?usp=sharing"
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(spreadsheet=url)
    df.columns = df.columns.str.strip().str.lower()
    for c in ['lat', 'lon', 'n', 'ph', 'moist']:
        df[c] = pd.to_numeric(df[c].astype(str).str.replace(',', '.'), errors='coerce')
    return df.dropna(subset=['lat', 'lon'])

@st.cache_data
def get_geojson():
    try:
        with open('peta_desa.json', 'r') as f:
            return json.load(f)
    except:
        return None

# 3. LOGIKA STATE
if 'selected_point' not in st.session_state:
    st.session_state.selected_point = None

df = get_data()
geo_desa = get_geojson()

# --- HEADER HIDDEN CONTROL ---
with st.sidebar:
    st.title("Wildantech Control")
    if st.button("Reset / Tutup Kartu"):
        st.session_state.selected_point = None
        st.rerun()

# --- PEMBUATAN PETA ---
# Tentukan pusat peta
center_lat = df['lat'].mean() if not df.empty else -7.35
center_lon = df['lon'].mean() if not df.empty else 109.9

m = folium.Map(location=[center_lat, center_lon], zoom_start=13, tiles="CartoDB dark_matter", zoom_control=False)

# Tambahkan GeoJSON (Garis Desa)
if geo_desa:
    folium.GeoJson(
        geo_desa,
        name="Batas Desa",
        style_function=lambda x: {
            'fillColor': '#238636',
            'color': '#deff9a',
            'weight': 2,
            'fillOpacity': 0.1
        }
    ).add_to(m)

# Tambahkan Titik Sensor
for i, row in df.iterrows():
    folium.CircleMarker(
        location=[row['lat'], row['lon']],
        radius=12,
        color="#deff9a" if row['n'] >= 80 else "#ff4b4b",
        fill=True,
        fill_opacity=0.8,
        # PENTING: popup harus unik agar bisa dideteksi st_folium
        popup=f"SENSOR_ID:{int(row['id'])}"
    ).add_to(m)

# Render Peta
# PENTING: Gunakan returned_objects=["last_object_clicked_popup"] untuk efisiensi
output = st_folium(m, width="100%", height=850, returned_objects=["last_object_clicked_popup"])

# Cek Klik
if output and output.get("last_object_clicked_popup"):
    clicked_raw = output["last_object_clicked_popup"]
    if "SENSOR_ID:" in clicked_raw:
        new_id = int(clicked_raw.split(":")[1])
        if st.session_state.selected_point != new_id:
            st.session_state.selected_point = new_id
            st.rerun()

# --- TAMPILAN KARTU MELAYANG ---
if st.session_state.selected_point:
    data_lahan = df[df['id'] == st.session_state.selected_point].iloc[0]
    
    # Fungsi mencari nama desa dari koordinat (Shapely)
    def get_village_name(lat, lon, g_data):
        if not g_data: return "Wonosobo"
        p = Point(lon, lat)
        for feat in g_data['features']:
            if shape(feat['geometry']).contains(p):
                return feat['properties'].get('ds', 'Desa Tidak Diketahui')
        return "Luar Area"

    nama_desa = get_village_name(data_lahan['lat'], data_lahan['lon'], geo_desa)

    st.markdown(f"""
        <div class="floating-card">
            <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                <div>
                    <small style="color:#deff9a; letter-spacing:1px;">WILDANTECH MONITORING</small>
                    <h2 style="margin:0;">{nama_desa}</h2>
                    <p style="margin:0; opacity:0.6; font-size:12px;">Sensor ID: #{int(data_lahan['id'])}</p>
                </div>
            </div>
            <hr style="border:0; border-top:1px solid rgba(255,255,255,0.1); margin:15px 0;">
            <div class="metric-item">
                <small>NITROGEN (N)</small><br>
                <b style="font-size:20px;">{data_lahan['n']} mg/kg</b>
            </div>
            <div class="metric-item">
                <small>PH TANAH</small><br>
                <b style="font-size:20px;">{data_lahan['ph']}</b>
            </div>
            <div class="metric-item">
                <small>KELEMBAPAN</small><br>
                <b style="font-size:20px;">{data_lahan['moist']}%</b>
            </div>
            <p style="font-size:10px; opacity:0.4; margin-top:10px; text-align:center;">
                Lokasi: {data_lahan['lat']}, {data_lahan['lon']}
            </p>
        </div>
    """, unsafe_allow_html=True)
