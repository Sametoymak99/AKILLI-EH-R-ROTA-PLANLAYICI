import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import folium
from streamlit_folium import st_folium
from r_planlayici_app import veri_oku, baglantilari_kur, en_az_aktarma_bul, en_kisa_sure_bul, cok_kriterli_rota_bul, Graf, unpack_edge
import os
import random
import math

# -----------------
# YARDIMCI FONKSİYONLAR
# -----------------

def get_weather():
    try:
        url = "https://api.open-meteo.com/v1/forecast?latitude=41.0082&longitude=28.9784&current_weather=true"
        response = requests.get(url, timeout=2)
        if response.status_code == 200:
            data = response.json()
            return f"{data['current_weather']['temperature']} °C"
    except:
        return "?"
    return "-"

def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

def calculate_price_and_details(path_ids, duraklar):
    """
    Rotayı analiz eder ve aynı hat üzerindeki durakları gruplandırır.
    Girdi: path_ids (Durak ID listesi)
    """
    if not path_ids or len(path_ids) < 2: return 0, [], 0, 0
    
    # Artık doğrudan path_ids kullanıyoruz, isim kontrolüne gerek yok
    
    
    total_price = 0.0
    current_fare = 30.0
    first_vehicle_boarded = False
    
    grouped_steps = []
    
    def get_transport_meta(t_type, line_name=""):
        line_name = str(line_name).upper() if line_name else ""
        
        # Vapur (Ferry)
        if t_type == "ferry": 
            if line_name and line_name != "FERRY":
                return "⛴️", "#0369a1", f"Vapur ({line_name})"
            return "⛴️", "#0369a1", "Vapur"
        
        # Metro
        if t_type == "metro":
            if "M1A" in line_name: return "🚇", "#e11d48", "Metro M1A"
            if "M1B" in line_name: return "🚇", "#e11d48", "Metro M1B"
            if "M1" in line_name: return "🚇", "#e11d48", f"Metro {line_name}"
            if "M2" in line_name: return "🚇", "#16a34a", f"Metro {line_name}"
            if "M3" in line_name: return "🚇", "#2563eb", f"Metro {line_name}"
            if "M4" in line_name: return "🚇", "#db2777", f"Metro {line_name}"
            if "M5" in line_name: return "🚇", "#7c3aed", f"Metro {line_name}"
            if "M6" in line_name: return "🚇", "#f59e0b", f"Metro {line_name}"
            if "M7" in line_name: return "🚇", "#ea580c", f"Metro {line_name}"
            if "M8" in line_name: return "🚇", "#8b5cf6", f"Metro {line_name}"
            if "M9" in line_name: return "🚇", "#ec4899", f"Metro {line_name}"
            if "MARMARAY" in line_name: return "🚆", "#0f172a", "MARMARAY"
            if line_name and line_name != "METRO":
                return "🚇", "#be123c", f"Metro {line_name}"
            return "🚇", "#be123c", "Metro"
        
        # Yürüme
        if t_type == "walking": 
            return "🚶", "#f97316", "Yürüme"
        
        # Metrobüs
        if t_type == "metrobus": 
            if line_name and line_name != "METROBUS":
                return "🚍", "#d97706", f"Metrobüs {line_name}"
            return "🚍", "#d97706", "Metrobüs"
        
        # Otobüs (Default)
        if line_name and line_name != "BUS":
            return "🚌", "#0f766e", f"Otobüs {line_name}"
        return "🚌", "#0f766e", "Otobüs"


    logical_prev_line = None
    
    for i in range(len(path_ids) - 1):
        u, v = path_ids[i], path_ids[i+1]
        node_u, node_v = duraklar[u], duraklar[v]
        edge = node_u.komsular.get(v)
        if not edge: continue
        
        sure, yogunluk, _, transport_type, line_name_list, actual_segment_coords = unpack_edge(edge)
        
        # Hat belirleme - Optimize edilmiş mantık
        active_line = None
        
        if transport_type == "walking":
            active_line = "walking"
        else:
            # Eğer hat listesi boşsa, transport type'ı kullan
            if not line_name_list or len(line_name_list) == 0:
                active_line = transport_type.upper()
            else:
                # Hat listesi varsa
                # 1. Önce önceki hatla devam edip edemeyeceğimize bak
                if logical_prev_line and logical_prev_line != "walking" and logical_prev_line in line_name_list:
                    active_line = logical_prev_line
                # 2. Değilse, ilk hattı al
                else:
                    active_line = line_name_list[0]
        
        
        real_time = sure * yogunluk
        dist = haversine(node_u.lat, node_u.lon, node_v.lat, node_v.lon) * 1.1

        # Koordinatları hazırla (Snap to nodes)
        seg_coords = []
        if actual_segment_coords:
            seg_coords = [(node_u.lat, node_u.lon)] + actual_segment_coords + [(node_v.lat, node_v.lon)]
        else:
            seg_coords = [(node_u.lat, node_u.lon), (node_v.lat, node_v.lon)]

        # GRUPLAMA MANTIĞI: Eğer aynı tip ve hat ise son adıma ekle
        if grouped_steps and grouped_steps[-1]['raw_type'] == transport_type and grouped_steps[-1]['line'] == active_line:
            last = grouped_steps[-1]
            last['to'] = node_v.ad
            last['time'] += real_time
            last['dist'] += dist
            last['stops_count'] += 1
            if "Bilinmeyen" not in node_v.ad:
                last['passed_stops'].append(node_v.ad)
            last['path_coords'] += seg_coords[1:] # İlk noktayı atla ki üst üste binmesin
        else:
            # Yeni bir adım (Step)
            # Ücretlendirme burada tetiklenir (Yeni araç veya aktarma)
            price_label = ""
            if transport_type != "walking":
                if not first_vehicle_boarded:
                    total_price += 30.0
                    price_label = "30.00 ₺"
                    first_vehicle_boarded = True
                else:
                    current_fare *= 0.80
                    total_price += current_fare
                    price_label = f"{current_fare:.2f} ₺ (Aktarma)"
            else:
                price_label = "Ücretsiz"

            icon, color, tr_name = get_transport_meta(transport_type, active_line)
            
            # Başlangıç duraklarını temizle
            initial_stops = []
            if "Bilinmeyen" not in node_u.ad: initial_stops.append(node_u.ad)
            if "Bilinmeyen" not in node_v.ad: initial_stops.append(node_v.ad)
            
            grouped_steps.append({
                "from": node_u.ad,
                "to": node_v.ad,
                "type_name": tr_name,
                "raw_type": transport_type,
                "line": active_line,
                "icon": icon,
                "color": color,
                "time": real_time,
                "dist": dist,
                "price_label": price_label,
                "stops_count": 1,
                "passed_stops": initial_stops,
                "path_coords": seg_coords
            })
        
        logical_prev_line = active_line

    return total_price, grouped_steps, sum(s['time'] for s in grouped_steps), sum(s['dist'] for s in grouped_steps)

def draw_advanced_route_map(grouped_details):
    """
    Gruplanmış segmentleri kullanarak çok renkli bir harita çizer.
    """
    if not grouped_details: return None
    
    # Harita merkezini bul
    all_points = []
    for segment in grouped_details:
        all_points.extend(segment['path_coords'])
        
    if not all_points: return None
    
    avg_lat = sum(p[0] for p in all_points) / len(all_points)
    avg_lon = sum(p[1] for p in all_points) / len(all_points)
    
    m = folium.Map(location=[avg_lat, avg_lon], zoom_start=12)
    
    # Her segmenti ayrı renkte çiz
    for seg in grouped_details:
        points = seg['path_coords']
        color = seg['color']
        
        # Rotayı çiz
        is_walking = (seg.get('raw_type') == 'walking')
        folium.PolyLine(
            points, 
            color=color, 
            weight=7 if not is_walking else 5,
            opacity=0.8, 
            line_join='round',
            line_cap='round',
            dash_array='10, 10' if is_walking else None, # Yürüme ise kesikli çiz
            tooltip=f"{seg.get('type_name', 'Rota')}"
        ).add_to(m)
        
        # Başlangıç/Bitiş noktalarına Marker koy (Ara durakları boğmamak için)
        # Sadece segment başlarını işaretleyelim
        start_pt = points[0]
        folium.CircleMarker(
            location=start_pt,
            radius=6,
            color=color,
            fill=True,
            fill_color="white",
            fill_opacity=1,
            popup=seg['from']
        ).add_to(m)
        
    # En son durağı da işaretle
    last_seg = grouped_details[-1]
    last_pt = last_seg['path_coords'][-1]
    folium.Marker(
        location=last_pt,
        popup=f"Bitiş: {last_seg['to']}",
        icon=folium.Icon(color="red", icon="flag")
    ).add_to(m)
    
    # 1. Durağı (Tam Başlangıç) işaretle
    first_seg = grouped_details[0]
    first_pt = first_seg['path_coords'][0]
    folium.Marker(
        location=first_pt,
        popup=f"Başlangıç: {first_seg['from']}",
        icon=folium.Icon(color="green", icon="play")
    ).add_to(m)

    folium.TileLayer(
        tiles='http://mt0.google.com/vt/lyrs=m,traffic&hl=tr&x={x}&y={y}&z={z}&s=Ga',
        attr='Google Traffic', name='Canlı Trafik', overlay=True, control=True
    ).add_to(m)
    
    folium.LayerControl().add_to(m)
    return m

@st.cache_data(ttl=3600, show_spinner="Veriler yükleniyor...") # Cache V17 METRO-X
def get_cached_data():
    try:
        duraklar = veri_oku("stops.csv")
        duraklar = baglantilari_kur(duraklar)
        durak_adlari = sorted([d.ad for d in duraklar.values()])
        return duraklar, durak_adlari
    except Exception as e:
        print(f"DEBUG ERROR in get_cached_data: {e}")
        import traceback
        traceback.print_exc()
        return None, None

# -----------------
# YORUM SİSTEMİ
# -----------------
COMMENTS_FILE = "comments.csv"

def load_comments():
    if not os.path.exists(COMMENTS_FILE): return []
    try:
        df = pd.read_csv(COMMENTS_FILE)
        return df.to_dict('records')[::-1]
    except: return []

def save_comment(name, comment):
    new_data = {"name": name, "comment": comment, "date": datetime.now().strftime("%Y-%m-%d %H:%M")}
    df_new = pd.DataFrame([new_data])
    if not os.path.exists(COMMENTS_FILE): df_new.to_csv(COMMENTS_FILE, index=False)
    else: df_new.to_csv(COMMENTS_FILE, mode='a', header=False, index=False)

# -----------------
# MAIN APP
# -----------------
def main():
    st.set_page_config(page_title="Şehir Asistanı", layout="wide", page_icon="🏙️")
    
    # ------------------------------------
    # CSS STYLING (NEW THEME: SMART CITY TEAL)
    # ------------------------------------
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
    
    html, body, [class*="css"]  {
        font-family: 'Inter', sans-serif;
    }
    
    /* Background: Clean Slate */
    .stApp {
        background-color: #f1f5f9;
        background-image: radial-gradient(#cbd5e1 1px, transparent 1px);
        background-size: 20px 20px;
    }
    
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e2e8f0;
        box-shadow: 2px 0 10px rgba(0,0,0,0.02);
    }
    
    /* Header Container */
    .main-header {
        background: linear-gradient(120deg, #0f766e 0%, #0e7490 100%);
        padding: 40px;
        border-radius: 24px;
        color: white;
        text-align: center;
        margin-bottom: 30px;
        box-shadow: 0 10px 30px rgba(14, 116, 144, 0.25);
        position: relative;
        overflow: hidden;
    }
    
    /* Cards */
    .metric-card {
        background: white;
        border-radius: 16px;
        padding: 24px;
        text-align: center;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        border: 1px solid #f1f5f9;
        transition: transform 0.2s;
    }
    .metric-card:hover { transform: translateY(-3px); }
    
    .metric-value {
        font-size: 28px;
        font-weight: 800;
        color: #0f766e;
        line-height: 1.2;
    }
    .metric-label {
        font-size: 13px;
        color: #64748b;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    /* Timeline Step */
    .timeline-step {
        background: white;
        padding: 20px;
        border-radius: 16px;
        margin-bottom: 15px;
        border: 1px solid #e2e8f0;
        display: flex;
        align-items: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    
    /* Inputs */
    .stSelectbox div[data-baseweb="select"] > div {
        background-color: white;
        border-radius: 10px;
        border-color: #cbd5e1;
    }
    
    /* Buttons */
    .stButton>button {
        background-color: #0f766e;
        color: white;
        border-radius: 10px;
        padding: 12px 24px;
        font-weight: 600;
        border: none;
        transition: all 0.2s;
    }
    .stButton>button:hover {
        background-color: #115e59;
        box-shadow: 0 4px 12px rgba(15, 118, 110, 0.3);
    }
    
    </style>
    """, unsafe_allow_html=True)
    
    # Load Data First
    raw_duraklar, durak_adlari = get_cached_data()
    if not raw_duraklar:
         st.error("Veri seti yüklenemedi!")
         st.stop()
    
    rota_grafi = Graf(raw_duraklar)

    # --- SIDEBAR ---
    st.sidebar.markdown("<h2 style='color:#0f766e;'>🏙️ Şehir Asistanı</h2>", unsafe_allow_html=True)
    
    # 1. RASTGELE ROTA
    if st.sidebar.button("🎲 Rastgele Macera", type="secondary"):
        if durak_adlari and len(durak_adlari) > 1:
            st.session_state.preset_start = random.choice(durak_adlari)
            st.session_state.preset_end = random.choice(durak_adlari)
            while st.session_state.preset_end == st.session_state.preset_start:
                 st.session_state.preset_end = random.choice(durak_adlari)
            st.rerun()

    # GEÇMİŞ ARAMALAR
    if 'search_history' not in st.session_state: st.session_state.search_history = []
    
    st.sidebar.markdown("### 🕒 Son Aramalar")
    if st.session_state.search_history:
        for item in reversed(st.session_state.search_history[-5:]):
            if st.sidebar.button(f"🔁 {item['from']} ➝ {item['to']}", key=item['timestamp']):
                st.session_state.preset_start = item['from']
                st.session_state.preset_end = item['to']
                st.rerun()
    else:
        st.sidebar.info("Henüz bir arama yapmadınız.")

    # --- MAIN PAGE ---
    st.markdown(f"""
    <div class="main-header">
        <h1>🚀 Akıllı Şehir Navigasyonu</h1>
        <p style="opacity: 0.9; font-size: 18px;">Hızlı, Sürdürülebilir ve Doğa Dostu.</p>
        <div style="margin-top: 20px; display: inline-block; background: rgba(255,255,255,0.2); padding: 8px 16px; border-radius: 20px;">
            🌤️ İstanbul {get_weather()}
        </div>
    </div>
    """, unsafe_allow_html=True)

    
    # State Init
    if 'kapali_yollar' not in st.session_state: st.session_state.kapali_yollar = []
    if 'yogunluklar' not in st.session_state: st.session_state.yogunluklar = {}
    if 'rota_sonuc' not in st.session_state: st.session_state.rota_sonuc = None
    
    # Apply Mods
    for k1, k2 in st.session_state.kapali_yollar: rota_grafi.yol_kapat(k1, k2)
    for (d1, d2), val in st.session_state.yogunluklar.items(): rota_grafi.yogunluk_guncelle(d1, d2, val)
    
    # Input Section
    col_in1, col_in2, col_in3 = st.columns([1, 1, 1])
    
    # Handle presets
    default_start_idx = 0
    default_end_idx = 1
    if 'preset_start' in st.session_state and st.session_state.preset_start in durak_adlari:
        default_start_idx = durak_adlari.index(st.session_state.preset_start)
    if 'preset_end' in st.session_state and st.session_state.preset_end in durak_adlari:
        default_end_idx = durak_adlari.index(st.session_state.preset_end)

    with col_in1:
        baslangic = st.selectbox("Nereden?", durak_adlari, index=default_start_idx)
    with col_in2:
        hedef = st.selectbox("Nereye?", durak_adlari, index=default_end_idx)
    with col_in3:
        kriter = st.selectbox("Tercihiniz", ["En Hızlı Rota ⚡", "En Az Aktarma 🔄", "Dengeli (Akıllı) 🧠"])
    
    # Advanced Toggle
    with st.expander("🛠️ Uzman Paneli (Trafik & Ayarlar)"):
        c_adv1, c_adv2 = st.columns(2)
        with c_adv1:
            st.caption("Yol Kapatma")
            k1 = st.selectbox("A Durağı", durak_adlari, key="k1")
            k2 = st.selectbox("B Durağı", durak_adlari, key="k2")
            if st.button("Yolu Kapat"):
                st.session_state.kapali_yollar.append((k1, k2))
                st.success("Yol kapatıldı")
                rota_grafi.yol_kapat(k1, k2)
        with c_adv2:
            st.caption("Yoğunluk Atama")
            d1 = st.selectbox("A Durağı", durak_adlari, key="d1")
            d2 = st.selectbox("B Durağı", durak_adlari, key="d2")
            y_val = st.slider("Yoğunluk Çarpanı", 1.0, 5.0, 1.0)
            if st.button("Yoğunluk Ata"):
                st.session_state.yogunluklar[(d1, d2)] = y_val
                st.success("Yoğunluk güncellendi")
                rota_grafi.yogunluk_guncelle(d1, d2, y_val)

    if st.button("🔍 Rotayı Bul", type="primary", use_container_width=True):
        if baslangic == hedef:
            st.warning("Başlangıç ve hedef aynı olamaz.")
        else:
            # Add to history
            timestamp = datetime.now().strftime("%H:%M:%S")
            st.session_state.search_history.append({"from": baslangic, "to": hedef, "timestamp": timestamp})
            
            with st.spinner("Şehir verileri analiz ediliyor..."):
                rota, val = [], -1
                algo_name = ""
                
                if "Hızlı" in kriter:
                    rota, val = en_kisa_sure_bul(baslangic, hedef, raw_duraklar)
                    algo_name = "En Hızlı (Dijkstra)"
                elif "Aktarma" in kriter:
                    rota, val = en_az_aktarma_bul(baslangic, hedef, raw_duraklar)
                    algo_name = "En Az Aktarma (BFS)"
                else:
                    rota, val, _, _ = cok_kriterli_rota_bul(baslangic, hedef, raw_duraklar)
                    algo_name = "Akıllı Algoritma"
                
                
                if val != -1:
                    # Rota bulundu - detayları hesapla
                    price, grouped_det, time, dist = calculate_price_and_details(rota, raw_duraklar)

                    
                    # CO2 Hesaplama: Araba (120g/km) vs Toplu Taşıma (~40g/km) => 80g tasarruf
                    co2_saved = dist * 0.080 # kg olarak
                    
                    st.session_state.rota_sonuc = {
                        "rota": rota, "sure": time, "fiyat": price, "detaylar": grouped_det, "algo": algo_name, "dist": dist, "co2": co2_saved
                    }
                else:
                    st.session_state.rota_sonuc = "not_found"

    # Results
    if st.session_state.rota_sonuc:
        st.write("")
        if st.session_state.rota_sonuc == "not_found":
            st.error("😔 Rota bulunamadı. Lütfen farklı bir güzergah deneyin.")
        else:
            res = st.session_state.rota_sonuc
            
            # Metrics 4 Columns now
            c1, c2, c3, c4 = st.columns(4)
            
            with c1:
                st.markdown(f"""<div class='metric-card'><div class='metric-label'>SÜRE</div><div class='metric-value'>{res['sure']:.0f} dk</div></div>""", unsafe_allow_html=True)
            with c2:
                st.markdown(f"""<div class='metric-card'><div class='metric-label'>TUTAR</div><div class='metric-value'>{res['fiyat']:.2f} ₺</div></div>""", unsafe_allow_html=True)
            with c3:
                st.markdown(f"""<div class='metric-card'><div class='metric-label'>MESAFE</div><div class='metric-value'>{res['dist']:.1f} km</div></div>""", unsafe_allow_html=True)
            with c4:
                # Green Metric
                st.markdown(f"""
                <div class='metric-card' style='background-color:#f0fdf4; border-color:#86efac;'>
                    <div class='metric-label' style='color:#15803d;'>🌱 CO2 TASARRUFU</div>
                    <div class='metric-value' style='color:#166534;'>{res['co2']:.2f} kg</div>
                </div>
                """, unsafe_allow_html=True)
            
            # Harita
            st.write("")
            st.subheader("📍 Güzergah")
            # YENİLER: draw_advanced_route_map kullanıyoruz
            harita = draw_advanced_route_map(res['detaylar'])
            if harita:
                st_folium(harita, width=1900, height=500, returned_objects=[])
                
            # Timeline - Geliştirilmiş Görünüm
            st.subheader("🗺️ Rota Detayları")
            
            for idx, step in enumerate(res['detaylar'], 1):
               # Durakları virgülle ayırıp küçük yazıyla göster
               stops_list_str = " → ".join(step['passed_stops'])
               
               # Transport type badge
               transport_badge = ""
               if step['raw_type'] == "bus":
                   transport_badge = "🚌 OTOBÜS"
               elif step['raw_type'] == "metro":
                   transport_badge = "🚇 METRO"
               elif step['raw_type'] == "ferry":
                   transport_badge = "⛴️ VAPUR"
               elif step['raw_type'] == "metrobus":
                   transport_badge = "🚍 METROBÜS"
               elif step['raw_type'] == "walking":
                   transport_badge = "🚶 YÜRÜME"
               else:
                   transport_badge = step['icon'] + " " + step['raw_type'].upper()
               
               st.markdown(f"""
               <div class="timeline-step" style="border-left: 4px solid {step['color']}; padding-left: 15px;">
                   <div style="font-size: 24px; margin-right: 15px;">{step['icon']}</div>
                   <div style="flex-grow: 1;">
                       <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px;">
                           <span style="background: {step['color']}; color: white; padding: 4px 12px; border-radius: 12px; font-size: 11px; font-weight: 700;">{transport_badge}</span>
                           <span style="font-weight: 600; color: #334155; font-size:16px;">{step['from']} <span style="color:#94a3b8;">→</span> {step['to']}</span>
                       </div>
                       <div style="font-size: 13px; color: #64748b; margin-bottom: 4px;">
                           <b>{step['type_name']}</b> | <b>{step['stops_count']} Durak</b> | {step['time']:.1f} dk | {step['dist']:.1f} km
                       </div>
                       <div style="font-size: 11px; color: #94a3b8; font-style: italic;">
                           🏠 {stops_list_str}
                       </div>
                   </div>
                   <div style="font-weight: 700; color: #0f766e; min-width: 80px; text-align: right;">
                       {step['price_label']}
                   </div>
               </div>
               """, unsafe_allow_html=True)

    # Comments Section
    st.markdown("---")
    st.subheader("💬 Söz Sizde")
    
    with st.form("new_comment"):
        c1, c2 = st.columns([1,3])
        name = c1.text_input("Adınız")
        msg = c2.text_input("Yorumunuz")
        if st.form_submit_button("Yorum Yap"):
            if name and msg:
                save_comment(name, msg)
                st.success("Değerli görüşünüz için teşekkürler!")
                st.rerun()
    
    comments = load_comments()
    if comments:
        for c in comments[:5]:
            st.markdown(f"**{c['name']}** <span style='color:#94a3b8; font-size:12px;'>{c['date']}</span>: {c['comment']}", unsafe_allow_html=True)

if __name__ == '__main__':
    main()