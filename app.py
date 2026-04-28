import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import json
from shapely.geometry import shape, Point
from streamlit_gsheets import GSheetsConnection

# 1. KONFIGURASI HALAMAN (Initial sidebar auto agar bisa ditarik di HP)
st.set_page_config(
    page_title="Wildantech Dashboard",
    layout="wide",
    initial_sidebar_state="auto"
)

# --- CSS: MODERN FORMAL & MOBILE FRIENDLY ---
st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] > section:nth-child(2) { padding: 0 !important; }
    .block-container { padding: 0 !important; max-width: 100% !important; }
    header, footer { visibility: hidden; }
    
    /* Kartu responsif untuk HP */
    .floating-card {
        position: fixed;
        top: 10px;
        right: 10px;
        left: 10px;
        max-width: 350px;
        margin-left: auto; /* Agar tetap di kanan pada layar besar */
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

    /* Penyesuaian khusus layar kecil */
    @media (max-width: 640px) {
        .floating-card {
            width: auto;
            right: 5px;
            left: 5px;
            top: 5px;
        }
    }
    </style>
    """, unsafe_allow_html=True)

# 2. FUNGSI LOAD DATA
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
            return feat['properties'].get('ds', 'Wilayah Terdeteksi'), feat['properties'].get('kec', '-')
    return "Luar Area", "-"

# --- SIDEBAR (Bisa ditarik di HP karena state=auto) ---
with st.sidebar:
    st.header("Menu Kontrol")
    if st.button("Tutup Detail / Reset"):
        st.session_state.selected_id = None
        st.rerun()

# --- PETA ---
center_lat = df['lat'].mean() if not df.empty else -7.35
center_lon = df['lon'].mean() if not df.empty else 109.9

m = folium.Map(location=[center_lat, center_lon], zoom_start=13, tiles="CartoDB dark_matter", zoom_control=True)

if geo_desa:
    folium.GeoJson(geo_desa, style_function=lambda x: {'fillColor': '#238636', 'color': '#deff9a', 'weight': 1, 'fillOpacity': 0.1}).add_to(m)

for row in df.itertuples():
    dot_color = "#deff9a" if (5.5 <= row.ph <= 7.0 and row.n >= 80) else "#ff4b4b"
    folium.CircleMarker(
        location=[row.lat, row.lon], radius=15, color=dot_color, fill=True, fill_opacity=0.8,
        popup=f"ID:{int(row.id)}"
    ).add_to(m)

# Gunakan use_container_width agar responsif di HP
out = st_folium(m, use_container_width=True, height=700, returned_objects=["last_object_clicked_popup"])

if out and out.get("last_object_clicked_popup"):
    try:
        new_id = int(out["last_object_clicked_popup"].split(":")[1])
        if st.session_state.selected_id != new_id:
            st.session_state.selected_id = new_id
            st.rerun()
    except:
        pass

# --- TAMPILAN KARTU & REKOMENDASI ---
if st.session_state.selected_id:
    s = df[df['id'] == st.session_state.selected_id].iloc[0]
    ds, kc = get_village_info(s['lat'], s['lon'], geo_desa)
    
    # HTML Pembuka Kartu
    st.markdown(f"""
    <div class="floating-card">
        <div>
            <span style="color:#deff9a; font-size:9px; font-weight:bold;">WILDANTECH ANALYTICS</span>
            <h2 style="margin:0; font-size:18px;">Desa {ds}</h2>
            <p style="margin:0; opacity:0.6; font-size:11px;">Kec. {kc} | ID: {int(s['id'])}</p>
        </div>
        <div style="border-top:1px solid rgba(255,255,255,0.1); margin-top:8px; padding-top:8px;">
            <div class="grid-metrics">
                <div class="metric-small">N: <b>{s['n']}</b></div>
                <div class="metric-small">P: <b>{s['p']}</b></div>
                <div class="metric-small">K: <b>{s['k']}</b></div>
                <div class="metric-small">pH: <b>{s['ph']}</b></div>
                <div class="metric-small">Suhu: <b>{s['temp']}°</b></div>
                <div class="metric-small">Lembap: <b>{s['moist']}%</b></div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Rekomendasi di dalam kartu (Expander)
    with st.expander("REKOMENDASI"):
        if s['n'] < 80: st.error("Tambah pupuk Urea/ZA.")
        if s['ph'] < 5.5: st.warning("Tambah Kapur Dolomit.")
        elif s['ph'] > 7.5: st.warning("Tambah Belerang.")
        else: st.success("Kondisi optimal.")
        
        prioritas = "Tinggi" if (s['n'] < 50 or s['ph'] < 5.0) else "Normal"
        st.write(f"Prioritas Dinas: **{prioritas}**")

    st.markdown("</div>", unsafe_allow_html=True)
