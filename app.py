import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import json
from shapely.geometry import shape, Point
from streamlit_gsheets import GSheetsConnection

# 1. KONFIGURASI HALAMAN
st.set_page_config(
    page_title="Wildantech | Precision Agriculture",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- CSS: DESAIN MODERN FORMAL ---
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

    .stExpander {
        background: rgba(255,255,255,0.05) !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        margin-top: 10px !important;
    }
    </style>
    """, unsafe_allow_html=True)

# 2. LOAD DATA
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
        with open('peta_desa.json', 'r') as f: return json.load(f)
    except: return None

# 3. LOGIKA STATE
if 'selected_id' not in st.session_state:
    st.session_state.selected_id = None

df = get_data()
geo_desa = get_geojson()

def get_village_info(lat, lon, g_data):
    if not g_data: return "Wonosobo", "Jawa Tengah"
    p = Point(lon, lat)
    for feat in g_data['features']:
        if shape(feat['geometry']).contains(p):
            return feat['properties'].get('ds', 'Unknown'), feat['properties'].get('kec', '-')
    return "Luar Area", "-"

# --- SIDEBAR CONTROL ---
with st.sidebar:
    st.write("Kontrol Navigasi")
    if st.button("Reset Tampilan"):
        st.session_state.selected_id = None
        st.rerun()

# --- VISUALISASI PETA ---
center_lat = df['lat'].mean() if not df.empty else -7.35
center_lon = df['lon'].mean() if not df.empty else 109.9

m = folium.Map(location=[center_lat, center_lon], zoom_start=13, tiles="CartoDB dark_matter", zoom_control=False)

if geo_desa:
    folium.GeoJson(geo_desa, style_function=lambda x: {'fillColor': '#238636', 'color': '#deff9a', 'weight': 1, 'fillOpacity': 0.1}).add_to(m)

for row in df.itertuples():
    color = "#deff9a" if (5.5 <= row.ph <= 7.0 and row.n >= 80) else "#ff4b4b"
    folium.CircleMarker(
        location=[row.lat, row.lon], radius=12, color=color, fill=True, fill_opacity=0.8,
        popup=f"ID:{int(row.id)}"
    ).add_to(m)

out = st_folium(m, width="100%", height=850, returned_objects=["last_object_clicked_popup"])

if out and out.get("last_object_clicked_popup"):
    new_id = int(out["last_object_clicked_popup"].split(":")[1])
    if st.session_state.selected_id != new_id:
        st.session_state.selected_id = new_id
        st.rerun()

# --- SISTEM PENDUKUNG KEPUTUSAN ---
if st.session_state.selected_id:
    s = df[df['id'] == st.session_state.selected_id].iloc[0]
    ds, kc = get_village_info(s['lat'], s['lon'], geo_desa)
    
    st.markdown(f"""
        <div class="floating-card">
            <small style="color:#deff9a; letter-spacing:1px; font-weight:bold;">WILDANTECH ANALYTICS</small>
            <h2 style="margin:0; font-size:24px;">Desa {ds}</h2>
            <p style="margin:0; opacity:0.6; font-size:12px;">Kecamatan {kc} | ID: {int(s['id'])}</p>
            <hr style="border:0; border-top:1px solid rgba(255,255,255,0.1); margin:12px 0;">
            
            <div class="grid-metrics">
                <div class="metric-small"><small>Nitrogen (N)</small><br><b>{s['n']} mg/kg</b></div>
                <div class="metric-small"><small>Phosphor (P)</small><br><b>{s['p']} mg/kg</b></div>
                <div class="metric-small"><small>Kalium (K)</small><br><b>{s['k']} mg/kg</b></div>
                <div class="metric-small"><small>Tingkat pH</small><br><b>{s['ph']}</b></div>
                <div class="metric-small"><small>Suhu Tanah</small><br><b>{s['temp']}°C</b></div>
                <div class="metric-small"><small>Kelembapan</small><br><b>{s['moist']}%</b></div>
                <div class="metric-small" style="grid-column: span 2;"><small>EC (Electrical Conductivity)</small><br><b>{s['ec']} us/cm</b></div>
            </div>
    """, unsafe_allow_html=True)

    with st.expander("ANALISIS DAN REKOMENDASI"):
        # Rekomendasi Teknis
        if s['n'] < 80: 
            st.error("Rekomendasi Pupuk: Segera lakukan penambahan pupuk Nitrogen (Urea/ZA).")
        if s['p'] < 50: 
            st.error("Rekomendasi Phospat: Lakukan pemupukan Phosphor menggunakan SP-36.")
        
        if s['ph'] < 5.5: 
            st.warning("Kondisi Tanah: Asam. Disarankan pemberian Kapur Dolomit.")
        elif s['ph'] > 7.5: 
            st.warning("Kondisi Tanah: Basa. Disarankan pemberian Belerang atau Asam Fosfat.")
        else: 
            st.success("Kondisi pH Tanah: Optimal untuk pertumbuhan tanaman.")
            
        st.divider()
        st.write("**Laporan Strategis Dinas:**")
        prioritas = "Tinggi" if (s['n'] < 50 or s['ph'] < 5.0) else "Normal"
        st.write(f"Status Prioritas Distribusi Nutrisi: **{prioritas}**")

    st.markdown('</div>', unsafe_allow_html=True)
