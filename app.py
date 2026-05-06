import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import json
import requests
from shapely.geometry import shape, Point
from streamlit_gsheets import GSheetsConnection

# 1. KONFIGURASI HALAMAN UTAMA (Dioptimalkan untuk Mobile)
st.set_page_config(
    page_title="Wildantech | Intelligence Dashboard",
    layout="wide",
    initial_sidebar_state="auto"
)

# --- CSS: MODERN & RESPONSIVE ---
st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] > section:nth-child(2) { padding: 0 !important; }
    .block-container { padding: 0 !important; max-width: 100% !important; }
    header, footer { visibility: hidden; }
    
    .floating-card {
        position: fixed;
        top: 10px;
        right: 10px;
        left: 10px;
        max-width: 350px;
        margin-left: auto;
        background: rgba(13, 17, 23, 0.95);
        backdrop-filter: blur(15px);
        border: 1px solid rgba(222, 255, 154, 0.3);
        border-radius: 12px;
        padding: 15px;
        z-index: 10000;
        color: white;
        box-shadow: 0 8px 32px rgba(0,0,0,0.5);
    }
    
    .grid-metrics {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 8px;
        margin-top: 8px;
    }
    
    .metric-small {
        background: rgba(255,255,255,0.05);
        padding: 6px;
        border-radius: 6px;
        border-left: 3px solid #deff9a;
        font-size: 13px;
    }
    </style>
    """, unsafe_allow_html=True)

# 2. FUNGSI TEKNIS (DATA & MDPL)
def get_elevation(lat, lon):
    """Fungsi otomatis mengambil data MDPL"""
    try:
        url = f"https://api.open-elevation.com/api/v1/lookup?locations={lat},{lon}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return response.json()['results'][0]['elevation']
        return "-"
    except:
        return "-"

@st.cache_data(ttl=60)
def get_data():
    url = "https://docs.google.com/spreadsheets/d/1tDeGWOU8EyLa7rgxCcRVXAu05CcezDFlI9K0SmIPN1Y/edit?usp=sharing"
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(spreadsheet=url)
        df.columns = df.columns.str.strip().str.lower()
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

# 3. LOGIKA DESA
def get_village_info(lat, lon, g_data):
    if not g_data: return "Wonosobo", "Jawa Tengah"
    p = Point(lon, lat)
    for feat in g_data['features']:
        if shape(feat['geometry']).contains(p):
            return feat['properties'].get('ds', 'Terdeteksi'), feat['properties'].get('kec', '-')
    return "Luar Area", "-"

# 4. MANAJEMEN STATE
if 'selected_id' not in st.session_state:
    st.session_state.selected_id = None

df = get_data()
geo_desa = get_geojson()

# --- SIDEBAR ---
with st.sidebar:
    st.header("Wildantech Panel")
    if st.button("Reset Dashboard"):
        st.session_state.selected_id = None
        st.rerun()

# --- PETA UTAMA ---
center_lat = df['lat'].mean() if not df.empty else -7.35
center_lon = df['lon'].mean() if not df.empty else 109.9

m = folium.Map(location=[center_lat, center_lon], zoom_start=13, tiles="CartoDB dark_matter")

if geo_desa:
    folium.GeoJson(geo_desa, style_function=lambda x: {'fillColor': '#238636', 'color': '#deff9a', 'weight': 1, 'fillOpacity': 0.1}).add_to(m)

for row in df.itertuples():
    status_warna = "#deff9a" if (5.5 <= row.ph <= 7.0 and row.n >= 80) else "#ff4b4b"
    folium.CircleMarker(
        location=[row.lat, row.lon], radius=15, color=status_warna, fill=True, fill_opacity=0.8,
        popup=f"ID:{int(row.id)}"
    ).add_to(m)

out = st_folium(m, use_container_width=True, height=750, returned_objects=["last_object_clicked_popup"])

if out and out.get("last_object_clicked_popup"):
    try:
        new_id = int(out["last_object_clicked_popup"].split(":")[1])
        if st.session_state.selected_id != new_id:
            st.session_state.selected_id = new_id
            st.rerun()
    except:
        pass

# --- KARTU INFO & MDPL ---
if st.session_state.selected_id:
    s = df[df['id'] == st.session_state.selected_id].iloc[0]
    ds, kc = get_village_info(s['lat'], s['lon'], geo_desa)
    mdpl = get_elevation(s['lat'], s['lon'])
    
    st.markdown(f"""
    <div class="floating-card">
        <div>
            <span style="color:#deff9a; font-size:9px; font-weight:bold;">WILDANTECH ANALYTICS</span>
            <h2 style="margin:0; font-size:18px;">Desa {ds}</h2>
            <p style="margin:0; opacity:0.6; font-size:11px;">Kec. {kc} | {mdpl} MDPL</p>
        </div>
        <div style="border-top:1px solid rgba(255,255,255,0.1); margin-top:8px; padding-top:8px;">
            <div class="grid-metrics">
                <div class="metric-small">N: <b>{s['n']}</b></div>
                <div class="metric-small">P: <b>{s['p']}</b></div>
                <div class="metric-small">K: <b>{s['k']}</b></div>
                <div class="metric-small">pH: <b>{s['ph']}</b></div>
                <div class="metric-small">Suhu: <b>{s['temp']}°C</b></div>
                <div class="metric-small">Lembap: <b>{s['moist']}%</b></div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    with st.expander("REKOMENDASI"):
        if s['n'] < 80: st.error("Butuh tambahan Urea/ZA.")
        if s['ph'] < 5.5: st.warning("Butuh Kapur Dolomit.")
        elif s['ph'] > 7.5: st.warning("Butuh Belerang.")
        else: st.success("Kondisi optimal.")
        
    st.markdown("</div>", unsafe_allow_html=True)
