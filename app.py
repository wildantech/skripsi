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

# --- CSS: DESAIN MODERN (MOBILE STABLE & FLOATING CARD FIXED) ---
st.markdown("""
<style>
[data-testid="stAppViewContainer"] > section:nth-child(2) { padding: 0 !important; }
.block-container { padding: 0 !important; max-width: 100% !important; }
header, footer { visibility: hidden; }

/* Wadah Utama Kartu Melayang */
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

/* Style untuk Badge Nama Tanaman agar Estetik */
.plant-badge {
    display: inline-block;
    padding: 4px 10px;
    font-size: 11px;
    font-weight: bold;
    border-radius: 20px;
    background: rgba(222, 255, 154, 0.15);
    color: #deff9a;
    border: 1px solid rgba(222, 255, 154, 0.4);
    margin-top: 8px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

/* Grid Dua Kolom di Dalam Kartu */
.grid-metrics {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
    margin-top: 10px;
}

/* Desain Kotak Kecil Parameter Sensor */
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
        return "Yogyakarta"
    except:
        return "Yogyakarta"

@st.cache_data(ttl=5) # Diturunkan ke 5 detik agar data koordinat panjang dari ESP32 langsung masuk
def get_data():
    url = "https://docs.google.com/spreadsheets/d/1tDeGWOU8EyLa7rgxCcRVXAu05CcezDFlI9K0SmIPN1Y/edit?gid=569291149#gid=569291149"
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        # Gunakan URL tab Sheet2 (gid), kompatibel dengan streamlit-gsheets
        # versi yang tidak menerima parameter worksheet.
        df = conn.read(spreadsheet=url)
        df.columns = df.columns.str.strip().str.lower()
        
        # Konversi aman untuk koordinat desimal panjang bawaan hardware ESP32
        cols = ['lat', 'lon', 'n', 'p', 'k', 'ph', 'ec', 'temp', 'moist']
        for c in cols:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c].astype(str).str.replace(',', '.').str.strip(), errors='coerce')
        # Simpan dataframe lengkap: data tanpa GPS tetap sah dan tetap tersedia
        # untuk statistik/dashboard, hanya marker peta yang membutuhkan koordinat.
        return df
    except:
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
    if not g_data: return "Yogyakarta", "DIY"
    p = Point(lon, lat)
    for feat in g_data['features']:
        if shape(feat['geometry']).contains(p):
            return feat['properties'].get('ds', 'Terdeteksi'), feat['properties'].get('kec', '-')
    # Jika koordinat di luar jangkauan geojson Wonosobo (seperti data Jogja mu)
    return "Sleman / Kota", "Yogyakarta"

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
# Otomatis centering peta beralih ke lokasi Jogja jika data terbaru berada di sana
df_peta = df.dropna(subset=['lat', 'lon']) if not df.empty else df
center_lat = df_peta['lat'].iloc[-1] if not df_peta.empty else -7.35
center_lon = df_peta['lon'].iloc[-1] if not df_peta.empty else 109.9

m = folium.Map(location=[center_lat, center_lon], zoom_start=11, tiles="CartoDB dark_matter", zoom_control=False)

if geo_desa:
    folium.GeoJson(geo_desa, style_function=lambda x: {'fillColor': '#238636', 'color': '#deff9a', 'weight': 1, 'fillOpacity': 0.1}).add_to(m)

if not df_peta.empty:
    for row in df_peta.itertuples():
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

# --- TAMPILAN KARTU INFORMASI (DATA UTK DINAS & PETANI) ---
if st.session_state.selected_id and not df.empty:
    # Mengambil baris data PALING BARU (paling bawah di sheets) jika ID-nya duplikat
    target_rows = df[df['id'] == st.session_state.selected_id]
    if not target_rows.empty:
        s = target_rows.iloc[-1]
        ds, kc = get_village_info(s['lat'], s['lon'], geo_desa)
        mdpl = get_elevation(s['lat'], s['lon'])
        
        raw_tanaman = str(s['tanaman']).upper() if 'tanaman' in df.columns and pd.notna(s['tanaman']) else "SINGKONG"
        emoji = "🌱 "
        
        if "close" in st.query_params:
            st.session_state.selected_id = None
            st.query_params.clear()
            st.rerun()

        # String HTML wajib rata kiri penuh agar Streamlit tidak mengubahnya menjadi blok teks kode mentah
        card_html = """
<div class="floating-card">
    <div style="margin-bottom: 10px;">
        <span style="color:rgba(255,255,255,0.4); font-size:10px; font-weight:bold; letter-spacing:1px;">WILDANTECH MONITORING SYSTEM</span>
        <h2 style="margin:2px 0 0 0; font-size:22px;">Desa {ds}</h2>
        <p style="margin:0; opacity:0.6; font-size:12px;">{kc} | ID: {val_id} | <b>{mdpl}</b></p>
        <p style="margin:4px 0 0; opacity:0.55; font-size:11px;">Waktu ukur: {val_waktu}</p>
        <div class="plant-badge">{emoji}{raw_tanaman}</div>
    </div>
    <div style="border-top:1px solid rgba(255,255,255,0.1); padding-top:12px;">
        <a href="/?close=true" target="_self" style="text-decoration: none;">
            <div style="background: rgba(255, 75, 75, 0.15); border: 1px solid rgba(255, 75, 75, 0.4); color: #ff4b4b; text-align: center; border-radius: 8px; padding: 6px; font-size: 12px; font-weight: bold; cursor: pointer; margin-bottom: 12px;">
                ✖ Tutup Detail Lahan
            </div>
        </a>
        <div class="grid-metrics">
            <div class="metric-small"><small>Nitrogen (N)</small><br><b>{val_n} mg/kg</b></div>
            <div class="metric-small"><small>Phosphor (P)</small><br><b>{val_p} mg/kg</b></div>
            <div class="metric-small"><small>Kalium (K)</small><br><b>{val_k} mg/kg</b></div>
            <div class="metric-small"><small>Tingkat pH</small><br><b>{val_ph}</b></div>
            <div class="metric-small"><small>Suhu Tanah</small><br><b>{val_temp}°C</b></div>
            <div class="metric-small"><small>Kelembapan</small><br><b>{val_moist}%</b></div>
            <div class="metric-small" style="grid-column: span 2;"><small>Konduktivitas Listrik (EC)</small><br><b>{val_ec} us/cm</b></div>
        </div>
    </div>
</div>
"""
        st.markdown(
            card_html.format(
                ds=ds, kc=kc, mdpl=mdpl, emoji=emoji, raw_tanaman=raw_tanaman,
                val_id=str(int(s['id'])), val_n=str(s['n']), val_p=str(s['p']), 
                val_k=str(s['k']), val_ph=str(s['ph']), val_temp=str(s['temp']), 
                val_moist=str(s['moist']), val_ec=str(s['ec']),
                val_waktu=str(s['waktu']) if 'waktu' in df.columns and pd.notna(s['waktu']) else "Tidak tersedia"
            ), 
            unsafe_allow_html=True
        )

        # EXPANDER UTK REKOMENDASI DINAS (Dimasukkan ke Sidebar agar Layout Utama Tetap Ramping)
        with st.sidebar:
            st.divider()
            with st.expander("🔍 ANALISIS DINAS & REKOMENDASI", expanded=True):
                prioritas = "TINGGI (Kritis)" if (s['n'] < 50 or s['ph'] < 5.0) else "Normal"
                st.write(f"**Status Lahan:** {prioritas}")
                if s['n'] < 80:
                    st.error("Rekomendasi: Subsidi pupuk Nitrogen (Urea/ZA) diperlukan.")
                if s['ph'] < 5.5:
                    st.warning("Kondisi: Tanah Asam. Butuh intervensi Kapur Dolomit.")
                elif s['ph'] > 7.5:
                    st.warning("Kondisi: Tanah Basa. Butuh aplikasi Belerang.")
                else:
                    st.success("Kondisi: Tanah sehat dan optimal.")
