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

# 2. FUNGSI LOAD DATA
@st.cache_data(ttl=60)
def get_data():
    url = "https://docs.google.com/spreadsheets/d/1tDeGWOU8EyLa7rgxCcRVXAu05CcezDFlI9K0SmIPN1Y/edit?usp=sharing"
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(spreadsheet=url)
        df.columns = df.columns.str.strip().str.lower()
        # Variabel yang dibutuhkan
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

# 3. LOGIKA STATE DAN DATA
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
# Menentukan titik tengah peta
if not df.empty:
    center_lat, center_lon = df['lat'].mean(), df['lon'].mean()
else:
    center_lat, center_lon = -7.35, 109.9

m = folium.Map(location=[center_lat, center_lon], zoom_start=13, tiles="CartoDB dark_matter", zoom_control=False)

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

for row in df.itertuples():
    # Penentuan warna berdasarkan kondisi Nitrogen dan pH
    dot_color = "#deff9a" if (5.5 <= row.ph <= 7.0 and row.n >= 80) else "#ff4b4b"
    folium.CircleMarker(
        location=[row.lat, row.lon],
        radius=12,
        color=dot_color,
        fill=True,
        fill_opacity=0.8,
        popup=f"ID:{int(row.id)}"
    ).add_to(m)

# Tampilkan Peta
out = st_folium(m, width="100%", height=850, returned_objects=["last_object_clicked_popup"])

# Deteksi Klik pada Titik
if out and out.get("last_object_clicked_popup"):
    try:
        new_id = int(out["last_object_clicked_popup"].split(":")[1])
        if st.session_state.selected_id != new_id:
            st.session_state.selected_id = new_id
            st.rerun()
    except:
        pass

# --- TAMPILAN INFORMASI DAN SISTEM PENDUKUNG KEPUTUSAN ---
if st.session_state.selected_id:
    # Ambil data baris yang dipilih
    s = df[df['id'] == st.session_state.selected_id].iloc[0]
    ds, kc = get_village_info(s['lat'], s['lon'], geo_desa)
    
    # Render Kartu Melayang menggunakan HTML Baku
    # Saya memecah string HTML agar variabel terisi dengan benar (menghindari error koding muncul di layar)
    card_html = f"""
    <div class="floating-card">
        <div style="margin-bottom: 10px;">
            <span style="color:#deff9a; font-size:10px; font-weight:bold; letter-spacing:1px;">WILDANTECH ANALYTICS</span>
            <h2 style="margin:2px 0 0 0; font-size:22px; color:white;">Desa {ds}</h2>
            <p style="margin:0; opacity:0.6; font-size:12px;">Kecamatan {kc} | ID: {int(s['id'])}</p>
        </div>
        
        <div style="border-top:1px solid rgba(255,255,255,0.1); padding-top:10px;">
            <div class="grid-metrics">
                <div class="metric-small"><small>Nitrogen (N)</small><br><b>{s['n']} mg/kg</b></div>
                <div class="metric-small"><small>Phosphor (P)</small><br><b>{s['p']} mg/kg</b></div>
                <div class="metric-small"><small>Kalium (K)</small><br><b>{s['k']} mg/kg</b></div>
                <div class="metric-small"><small>Tingkat pH</small><br><b>{s['ph']}</b></div>
                <div class="metric-small"><small>Suhu Tanah</small><br><b>{s['temp']}°C</b></div>
                <div class="metric-small"><small>Kelembapan</small><br><b>{s['moist']}%</b></div>
                <div class="metric-small" style="grid-column: span 2;"><small>EC (Konduktivitas Listrik)</small><br><b>{s['ec']} us/cm</b></div>
            </div>
        </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)

    # Bagian Rekomendasi (Menggunakan komponen asli Streamlit agar interaktif dan aman)
    with st.expander("ANALISIS DAN REKOMENDASI TINDAKAN"):
        if s['n'] < 80:
            st.error("Rekomendasi Nutrisi: Diperlukan penambahan pupuk berbasis Nitrogen (Urea atau ZA).")
        
        if s['p'] < 50:
            st.error("Rekomendasi Nutrisi: Diperlukan penambahan pupuk Phosphor (SP-36).")
            
        if s['ph'] < 5.5:
            st.warning("Kondisi Tanah: Tingkat keasaman tinggi (Asam). Disarankan pemberian Kapur Dolomit.")
        elif s['ph'] > 7.5:
            st.warning("Kondisi Tanah: Tingkat keasaman rendah (Basa). Disarankan pemberian Belerang.")
        else:
            st.success("Kondisi pH: Tingkat keasaman tanah berada pada rentang optimal.")
            
        st.divider()
        st.write("**Data Laporan Dinas:**")
        prioritas_distribusi = "Tinggi" if (s['n'] < 50 or s['ph'] < 5.0) else "Normal"
        st.write(f"Prioritas Alokasi Bantuan Nutrisi: **{prioritas_distribusi}**")

    # Tutup div kartu melayang
    st.markdown("</div>", unsafe_allow_html=True)
