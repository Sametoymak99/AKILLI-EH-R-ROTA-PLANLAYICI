import csv
import heapq
from collections import deque, defaultdict
import math
import json
import os
import pickle


# ====================================================================
# I. VERİ YAPILARI (SINIFLAR)
# ====================================================================

class Durak:
    """Grafikteki bir düğümü (Node) temsil eder."""

    def __init__(self, id, ad, enlem, boylam):
        self.id = id
        self.ad = ad
        self.lat = enlem
        self.lon = boylam
        self.komsular = {}

    def __repr__(self):
        return f"Durak(ID: {self.id}, Ad: {self.ad})"


class Graf:
    """Graf yapısı ve dinamik yol kapatma fonksiyonunu içerir."""

    def __init__(self, duraklar_sozlugu):
        self.duraklar = duraklar_sozlugu

    def yol_kapat(self, durak1_ad, durak2_ad):
        """Dinamik Kenar Kaldırma: İki durak arasındaki yolu geçici olarak kapatır."""
        ad_to_id = {d.ad: d.id for d in self.duraklar.values()}

        try:
            id1 = ad_to_id[durak1_ad]
            id2 = ad_to_id[durak2_ad]

            def kapat_kenar(g_durak, target_id):
                if target_id in g_durak.komsular:
                    val = g_durak.komsular[target_id]
                    # (sure, yogunluk, durum, tur, line) veya eski formatlar
                    if len(val) == 5:
                        g_durak.komsular[target_id] = (val[0], val[1], False, val[3], val[4])
                    elif len(val) == 4:
                        g_durak.komsular[target_id] = (val[0], val[1], False, val[3])
                    else:
                        g_durak.komsular[target_id] = (val[0], val[1], False)

            kapat_kenar(self.duraklar[id1], id2)
            kapat_kenar(self.duraklar[id2], id1)
            return True

        except KeyError:
            return False

    def yogunluk_guncelle(self, durak1_ad, durak2_ad, yeni_yogunluk):
        """Canlı Yoğunluk Puanı: Belirtilen yolun yoğunluk katsayısını günceller."""
        ad_to_id = {d.ad: d.id for d in self.duraklar.values()}

        try:
            id1 = ad_to_id[durak1_ad]
            id2 = ad_to_id[durak2_ad]

            def guncelle_kenar(g_durak, target_id):
                if target_id in g_durak.komsular:
                    val = g_durak.komsular[target_id]
                    if len(val) == 5:
                        g_durak.komsular[target_id] = (val[0], yeni_yogunluk, val[2], val[3], val[4])
                    elif len(val) == 4:
                        g_durak.komsular[target_id] = (val[0], yeni_yogunluk, val[2], val[3])
                    else:
                        g_durak.komsular[target_id] = (val[0], yeni_yogunluk, val[2])

            guncelle_kenar(self.duraklar[id1], id2)
            guncelle_kenar(self.duraklar[id2], id1)
            return True
        except KeyError:
            return False


# ====================================================================
# II. VERİ YÖNETİMİ
# ====================================================================

def veri_oku(dosya_adi="stops.csv"):
    """stops.csv dosyasını okur ve Durak objelerini oluşturur."""
    duraklar_sozlugu = {}

    try:
        # 🔑 KRİTİK DÜZELTME: Dosya okuma kodlaması 'cp1254'
        with open(dosya_adi, 'r', encoding='cp1254') as file:
            reader = csv.DictReader(file, delimiter=',')

            for row in reader:
                try:
                    stop_id = int(row['stop_id'])
                except ValueError:
                    continue

                stop_name = row['stop_name'].strip()
                if not stop_name:
                    continue

                try:
                    stop_lat = float(row['stop_lat'])
                    stop_lon = float(row['stop_lon'])
                except ValueError:
                    continue

                yeni_durak = Durak(stop_id, stop_name, stop_lat, stop_lon)
                yeni_durak.stop_url = row.get('stop_url', '') # Link bilgisini sakla
                duraklar_sozlugu[stop_id] = yeni_durak

        return duraklar_sozlugu

    except FileNotFoundError:
        raise FileNotFoundError(f"❌ Hata: {dosya_adi} dosyası bulunamadı.")
    except Exception as e:
        raise Exception(f"Veri okuma hatası: {e}")

    # Bu satırlar normalde return'den sonra erişilmez ama mantık akışı için burada duruyor (asıl çağıran yerde yapılacak)
    return duraklar_sozlugu


def import_geojson_stops(duraklar_sozlugu, geojson_path):
    """GeoJSON dosyasındaki Point feature'larını durak olarak ekler."""
    if not os.path.exists(geojson_path):
        return duraklar_sozlugu
        
    try:
        if os.path.getsize(geojson_path) == 0:
            return duraklar_sozlugu

        with open(geojson_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        print(f"Info: {geojson_path} durakları taranıyor...")
        
        max_id = 0
        if duraklar_sozlugu:
            max_id = max(duraklar_sozlugu.keys())
        
        eklenen = 0
        for feature in data.get('features', []):
            geometry = feature.get('geometry', {})
            props = feature.get('properties', {})
            
            if geometry.get('type') != 'Point':
                continue
                
            coords = geometry.get('coordinates', [])
            if not coords or len(coords) < 2:
                continue
                
            lon, lat = coords[0], coords[1]
            name = props.get('ISKELE_AD') or props.get('stop_name') or props.get('name') or "Bilinmeyen Durak"
            
            # Simple ID generation
            max_id += 1
            yeni_durak = Durak(max_id, name, lat, lon)
            duraklar_sozlugu[max_id] = yeni_durak
            eklenen += 1
            
        print(f"--> {geojson_path}: {eklenen} yeni durak eklendi.")
            
    except Exception as e:
        print(f"Hata ({geojson_path}): {e}")

    return duraklar_sozlugu


def haversine_distance(lat1, lon1, lat2, lon2):
    """İki nokta arasındaki kuş uçuşu mesafeyi (metre) hesaplar."""
    R = 6371000  # Dünya yarıçapı (metre)
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * \
        math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def process_geojson_routes(duraklar_sozlugu, geojson_path, transport_type="bus"):
    """
    GeoJSON dosyasındaki hatları okur ve durakları eşleştirerek kenar ekler.
    Optimization V2: Point-Based Grid Search + Caching
    Updated: Stores Line Name
    """
    if not os.path.exists(geojson_path):
        return duraklar_sozlugu
        
    # Cache V19 Minutes Fix
    cache_path = geojson_path + ".cache_v19_minutes_fix"
    
    if os.path.exists(cache_path) and os.path.getmtime(cache_path) > os.path.getmtime(geojson_path):
        try:
            print(f"Info: {geojson_path} için önbellek (v19_minutes_fix) yükleniyor...")
            with open(cache_path, 'rb') as f:
                cached_edges = pickle.load(f)
                
            count = 0
            for d_id, komsular in cached_edges.items():
                if d_id in duraklar_sozlugu:
                    duraklar_sozlugu[d_id].komsular.update(komsular)
                    count += 1
            print(f"--> Cache'den {count} durak bağlantısı yüklendi.")
            return duraklar_sozlugu
        except Exception as e:
            print(f"Cache yükleme hatası: {e}, yeniden hesaplanacak.")

    try:
        if os.path.getsize(geojson_path) == 0: return duraklar_sozlugu

        print(f"Info: {geojson_path} - JSON okunuyor...")
        with open(geojson_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        print(f"Info: {geojson_path} - İşleniyor (Optimizasyon V2)...")
        
        # Grid Index
        CELL_SIZE = 0.003
        grid = defaultdict(list)
        stop_list = list(duraklar_sozlugu.values())
        
        for d in stop_list:
            x = int(d.lon / CELL_SIZE)
            y = int(d.lat / CELL_SIZE)
            grid[(x, y)].append(d)
        
        neighbor_offsets = [(-1,-1), (-1,0), (-1,1), (0,-1), (0,0), (0,1), (1,-1), (1,0), (1,1)]
        
        added_count = 0
        features = data.get('features', [])
        total_features = len(features)
        
        edges_updates = {} # Changed from defaultdict to flat dict for pair keys
        
        for idx, feature in enumerate(features):
            if idx > 0 and idx % 2000 == 0:
                print(f"Processing {idx}/{total_features}...")
                
            props = feature.get('properties', {})
            # Hat İsmi Çıkarma
            raw_hat = str(props.get('HAT_KODU') or props.get('HAT_NO') or props.get('name') or props.get('ref') or "")
            hat_ismi = raw_hat.strip()
            
            if not hat_ismi:
                hat_ismi = transport_type.upper()

            geometry = feature.get('geometry', {})
            g_type = geometry.get('type')
            
            lines_to_process = []
            if g_type == 'LineString':
                lines_to_process.append(geometry.get('coordinates', []))
            elif g_type == 'MultiLineString':
                lines_to_process.extend(geometry.get('coordinates', []))
            else:
                continue
                
            for coords in lines_to_process:
                if not coords: continue
                
                found_indices = [] # Stores (index_on_line, stop_obj)
                last_recorded_id = None
                THRESHOLD = 100.0 # Daha hassas (yan sokaklara atlamasın)
                
                prev_gx, prev_gy = None, None
                local_candidates = []
                
                for i, (lon, lat) in enumerate(coords):
                    gx = int(lon / CELL_SIZE)
                    gy = int(lat / CELL_SIZE)
                    
                    if (gx, gy) != (prev_gx, prev_gy):
                        local_candidates = []
                        for dx, dy in neighbor_offsets:
                            local_candidates.extend(grid.get((gx+dx, gy+dy), []))
                        prev_gx, prev_gy = gx, gy
                    
                    if not local_candidates: continue
                    
                    best_d = None
                    min_dist_to_stop = float('inf')
                    for d in local_candidates:
                        d_dist = haversine_distance(lat, lon, d.lat, d.lon)
                        if d_dist < THRESHOLD and d_dist < min_dist_to_stop:
                            best_d = d
                            min_dist_to_stop = d_dist
                    
                    if best_d and best_d.id != last_recorded_id:
                        found_indices.append((i, best_d))
                        last_recorded_id = best_d.id
                
                if len(found_indices) < 2: continue
                
                for i in range(len(found_indices) - 1):
                    idx1, d1 = found_indices[i]
                    idx2, d2 = found_indices[i+1]
                    
                    if d1.id == d2.id: continue
                        
                    # Gerçek koordinatları al (idx1'den idx2'ye)
                    raw_coords = coords[idx1 : idx2+1]
                    actual_segment_coords = [(c[1], c[0]) for c in raw_coords]

                    # Yol mesafesini gerçek segment üzerinden hesapla
                    dist_m = 0
                    if len(actual_segment_coords) > 1:
                        for k in range(len(actual_segment_coords)-1):
                            dist_m += haversine_distance(actual_segment_coords[k][0], actual_segment_coords[k][1], 
                                                        actual_segment_coords[k+1][0], actual_segment_coords[k+1][1])
                    else:
                        dist_m = haversine_distance(d1.lat, d1.lon, d2.lat, d2.lon)

                    speed_m_min = 350.0 # Default bus
                    final_type = transport_type
                    if transport_type == "metro":
                        speed_m_min = 900.0
                    elif transport_type == "ferry":
                        speed_m_min = 500.0
                    elif transport_type == "bus" and hat_ismi.startswith("34"):
                        final_type = "metrobus"
                        speed_m_min = 700.0
                        
                    time_min = (dist_m / speed_m_min) + 0.5
                    
                    pair_key = (d1.id, d2.id)
                    
                    if pair_key not in edges_updates:
                         edges_updates[pair_key] = {
                             'time': time_min,
                             'lines': set(),
                             'type': final_type,
                             'dist': dist_m,
                             'coords': actual_segment_coords
                         }
                    
                    edges_updates[pair_key]['lines'].add(hat_ismi)
                    if time_min < edges_updates[pair_key]['time']:
                         edges_updates[pair_key]['time'] = time_min
                         # Daha kısa rotanın koordinatlarını tercih et
                         if actual_segment_coords:
                             edges_updates[pair_key]['coords'] = actual_segment_coords
                         
                added_count += 1
        
        print(f"--> {geojson_path}: {added_count} hat segmenti işlendi.")
        
        # Convert temporary dict back to Graph format
        final_updates = defaultdict(dict)
        for (u, v), data in edges_updates.items():
            # Tuple: (sure, yogunluk, durum, tur, line_LIST, path_coords)
            edge_val = (data['time'], 1.0, True, data['type'], list(data['lines']), data.get('coords', []))
            
            final_updates[u][v] = edge_val
            final_updates[v][u] = edge_val
            
            # Duraklara işle
            if u in duraklar_sozlugu: duraklar_sozlugu[u].komsular[v] = edge_val
            if v in duraklar_sozlugu: duraklar_sozlugu[v].komsular[u] = edge_val

        try:
            with open(cache_path, 'wb') as f:
                pickle.dump(final_updates, f)
            print("Info: Rota verileri önbelleğe (cache_v19_minutes_fix) kaydedildi.")
        except Exception as e:
            print(f"Cache yazma hatası: {e}")
            
    except Exception as e:
        print(f"Hata ({geojson_path}): {e}")

    return duraklar_sozlugu


def baglantilari_birlestir_transfer_ile(duraklar_sozlugu, transfer_mesafesi=400.0, yurume_hizi_m_dk=60.0):
    """
    Farklı ağları birbirine bağlamak için yakın duraklar arasına yürüme kenarları ekler.
    Kullanıcı isteği: 1m = 1s (60 m/dk).
    """
    print(f"Info: Transfer bağlantıları ({transfer_mesafesi}m) oluşturuluyor...")
    
    CELL_SIZE = 0.004  # Grid boyutunu biraz büyütelim
    grid = defaultdict(list)
    
    stop_list = list(duraklar_sozlugu.values())
    for d in stop_list:
        x = int(d.lon / CELL_SIZE)
        y = int(d.lat / CELL_SIZE)
        grid[(x, y)].append(d)
        
    neighbor_offsets = [(-1,-1), (-1,0), (-1,1), (0,-1), (0,0), (0,1), (1,-1), (1,0), (1,1)]
    transfer_count = 0
    
    for d1 in stop_list:
        gx, gy = int(d1.lon / CELL_SIZE), int(d1.lat / CELL_SIZE)
        candidates = []
        for dx, dy in neighbor_offsets:
            candidates.extend(grid.get((gx+dx, gy+dy), []))
            
        for d2 in candidates:
            if d1.id == d2.id: continue
            if d2.id in d1.komsular: continue
            
            dist = haversine_distance(d1.lat, d1.lon, d2.lat, d2.lon)
            
            if dist <= transfer_mesafesi:
                # 100m = 1dk (Dakika bazlı hesaplama - KRİTİK)
                yurume_suresi_dk = dist / 100.0
                
                # Fatigue Factor: 1.1x
                yurume_suresi_dk *= 1.1
                
                # Kenar Verisi Format: (sure_dk, yogunluk, durum, tur, hat_LIST, path_coords)
                edge_val = (yurume_suresi_dk, 1.0, True, "walking", ["YURUYUS"], [(d1.lat, d1.lon), (d2.lat, d2.lon)])
                
                d1.komsular[d2.id] = edge_val
                transfer_count += 1
    
    print(f"---> {transfer_count} transfer bağlantısı eklendi.")
    return duraklar_sozlugu


def baglantilari_kur(duraklar_sozlugu):
    """Bağlantıları kurar - Metro, Metrobüs, Deniz Otobüsü ve Otobüs verilerini yükler."""
    # GeoJSON Import Stops first (nodes)
    duraklar_sozlugu = import_geojson_stops(duraklar_sozlugu, "maristation.geojson")
    duraklar_sozlugu = import_geojson_stops(duraklar_sozlugu, "railwaystation.geojson")
    duraklar_sozlugu = import_geojson_stops(duraklar_sozlugu, "busstation.geojson")
    
    # Metrobüs istasyonlarını ekle (eğer dosya varsa)
    if os.path.exists("metrobusstation.geojson"):
        duraklar_sozlugu = import_geojson_stops(duraklar_sozlugu, "metrobusstation.geojson")

    # Metro/Marmaray/Metrobüs Bağlantılarını Otomatik Kur (stops.csv'den)
    # Eğer GeoJSON yoksa, stops.csv içindeki linklerden hatları gruplayıp bağlayalım.
    print("Info: Metro ve Raylı sistem hatları stops.csv'den analiz ediliyor...")
    line_groups = defaultdict(list)
    for d in duraklar_sozlugu.values():
        url = d.__dict__.get('stop_url') or ""
        # stop_url genelde 'https://www.metro.istanbul/...hat=M7' formatında
        if "hat=" in url:
            line_id = url.split("hat=")[-1].split("&")[0]
            line_groups[line_id].append(d)
        # --- METRO/MARMARAY TESPİTİ (Gelişmiş & Manuel Takviye) ---
    print("Info: Metro ve Raylı sistemler senkronize ediliyor...")
    
    # İstanbul Ana Metro Hatları Listesi (İsim Bazlı Manuel Takviye)
    METRO_HATLARI = {
        "M1A": ["Yenikapı", "Aksaray", "Emniyet-Fatih", "Topkapı-Ulubatlı", "Bayrampaşa", "Sağmalcılar", "Kartaltepe", "Otogar", "Terazidere", "Davutpaşa", "Merter", "Zeytinburnu", "Bakırköy", "Ataköy", "Yenibosna", "DTM", "Atatürk Havalimanı"],
        "M1B": ["Otogar", "Esenler", "Üçyüzlü", "Bağcılar Meydan", "Kirazlı"],
        "M2": ["Yenikapı", "Vezneciler", "Haliç", "Şişhane", "Taksim", "Osmanbey", "Şişli", "Gayrettepe", "Levent", "4.Levent", "Sanayi Mahallesi", "İTÜ Ayazağa", "Atatürk Oto Sanayi", "Darüşşafaka", "Hacıosman"],
        "M3": ["Kirazlı", "Yenimahalle", "Mahmutbey", "Bölge Parkı", "Siteler", "Turgut Özal", "İkitelli Sanayi", "İstiklal", "Başak Konutları", "MetroKent", "Onurkent", "Şehir Hastanesi", "Kayaşehir"],
        "M4": ["Kadıköy", "Ayrılık Çeşmesi", "Acıbadem", "Ünalan", "Göztepe", "Yenisahra", "Kozyatağı", "Bostancı", "Küçükyalı", "İdealtepe", "Süreyya Plajı", "Maltepe", "Huzurevi", "Gülsuyu", "Esenkent", "Hastane-Adliye", "Soğanlık", "Kartal", "Yakacık", "Pendik", "Tavşantepe", "Fevzi Çakmak", "Yayalar", "Kurtköy", "Sabiha Gökçen Havalimanı"],
        "M5": ["Üsküdar", "Fıstıkağacı", "Bağlarbaşı", "Altunizade", "Kısıklı", "Bulgurlu", "Ümraniye", "Çarşı", "Yamanevler", "Çakmak", "Ihlamurkuyu", "Altınşehir", "İmam Hatip", "Dudullu", "Necip Fazıl", "Çekmeköy"],
        "M7": ["Yıldız", "Beşiktaş", "Fulya", "Mecidiyeköy", "Çağlayan", "Kağıthane", "Nurtepe", "Alibeyköy", "Çırçır", "Veysel Karani", "Yeşilpınar", "Kazım Karabekir", "Yenimahalle", "Karadeniz Mahallesi", "Tekstilkent", "Oruç Reis", "Göztepe Mahallesi", "Mahmutbey"],
        "M8": ["Bostancı", "Emin Ali Paşa", "Ayşekadın", "Kozyatağı", "Küçükbakkalköy", "İçerenköy", "Kayışdağı", "Mevlana", "İMES", "Modoko", "Dudullu", "Huzur", "Parseller"],
        "M9": ["Ataköy", "Yenibosna", "Çobançeşme", "212", "Doğu Sanayi", "İhlas Yuva", "Mimar Sinan", "Bahariye", "Masko", "İkitelli Sanayi", "Ziya Gökalp", "Olimpiyat"],
        "MARMARAY": ["Halkalı", "Mustafa Kemal", "Küçükçekmece", "Florya", "Florya Akvaryum", "Yeşilköy", "Yeşilyurt", "Ataköy", "Bakırköy", "Yenimahalle", "Zeytinburnu", "Kazlıçeşme", "Yenikapı", "Sirkeci", "Üsküdar", "Ayrılık Çeşmesi", "Söğütlüçeşme", "Feneryolu", "Göztepe", "Erenköy", "Suadiye", "Bostancı", "Küçükyalı", "İdealtepe", "Süreyya Plajı", "Maltepe", "Cevizli", "Atalar", "Başak", "Kartal", "Yunus", "Pendik", "Kaynarca", "Tersane", "Güzelyalı", "Aydıntepe", "İçmeler", "Tuzla", "Çayırova", "Fatih", "Osmangazi", "Darıca", "Gebze"]
    }

    # Durak isimlerinden ID'leri hızlıca bulmak için geçici bir tablo
    name_to_ids = defaultdict(list)
    for d in duraklar_sozlugu.values():
        clean_name = d.ad.lower().replace(" ", "").replace("-", "").replace(".", "")
        name_to_ids[clean_name].append(d.id)

    # 1. Manuel hatları bağla
    for line_id, stations in METRO_HATLARI.items():
        prev_node_ids = []
        for s_name in stations:
            clean_s = s_name.lower().replace(" ", "").replace("-", "").replace(".", "")
            current_ids = name_to_ids.get(clean_s, [])
            
            # Eğer bu isimle durak bulunamadıysa bile ana metrolar olduğu için uyaralım (opsiyonel)
            if not current_ids:
                # İsim eşleşmesi biraz daha esnek olsun (Örn: "Üsküdar İH." -> "Üsküdar")
                for dn, ids in name_to_ids.items():
                    if clean_s in dn:
                        current_ids = ids
                        break

            if current_ids and prev_node_ids:
                for pid in prev_node_ids:
                    for cid in current_ids:
                        d1, d2 = duraklar_sozlugu[pid], duraklar_sozlugu[cid]
                        dist = haversine_distance(d1.lat, d1.lon, d2.lat, d2.lon)
                        if dist < 8000: # Bazı istasyonlar arası çok uzun olabilir (Marmaray)
                            time_min = (dist / 1000.0) + 0.5
                            edge_val = (time_min, 1.0, True, "metro", [line_id], [])
                            d1.komsular[cid] = edge_val
                            d2.komsular[pid] = edge_val
            
            prev_node_ids = current_ids

    # 2. Dinamik Hat Tespiti (Geriye Kalanlar İçin)
    line_groups = defaultdict(list)
    for d in duraklar_sozlugu.values():
        url = d.__dict__.get('stop_url', "").lower()
        name = d.ad.lower()
        if "hat=m" in url:
            line_id = url.split("hat=")[-1].split("&")[0].upper()
            line_groups[line_id].append(d)
        elif ("marmaray" in url or "marmaray" in name) and not any(k in name for k in ["otobüs", "durak"]):
            line_groups["MARMARAY"].append(d)
            
    for line_id, stops in line_groups.items():
        lons, lats = [s.lon for s in stops], [s.lat for s in stops]
        if not lons: continue
        if (max(lons)-min(lons)) > (max(lats)-min(lats)):
            sorted_stops = sorted(stops, key=lambda x: x.lon)
        else:
            sorted_stops = sorted(stops, key=lambda x: x.lat)
        for i in range(len(sorted_stops)-1):
            d1, d2 = sorted_stops[i], sorted_stops[i+1]
            if d2.id not in d1.komsular: # Zaten bağlanmadıysa
                dist = haversine_distance(d1.lat, d1.lon, d2.lat, d2.lon)
                if dist < 5000:
                    time_min = (dist / 1000.0) + 0.3
                    d1.komsular[d2.id] = (time_min, 1.0, True, "metro", [line_id], [])
                    d2.komsular[d1.id] = (time_min, 1.0, True, "metro", [line_id], [])

    # --- GEOJSON ROTALARI ---
    if os.path.exists("metrobus.geojson"):
        duraklar_sozlugu = process_geojson_routes(duraklar_sozlugu, "metrobus.geojson", transport_type="metrobus")
    if os.path.exists("railway.geojson"):
        duraklar_sozlugu = process_geojson_routes(duraklar_sozlugu, "railway.geojson", transport_type="metro")
    duraklar_sozlugu = process_geojson_routes(duraklar_sozlugu, "mari.geojson", transport_type="ferry")
    duraklar_sozlugu = process_geojson_routes(duraklar_sozlugu, "bus.geojson", transport_type="bus")

    # --- OKUL/İZOLE DURAK KURTARMA (KULLANICI TALEBİ: MEDENİYET ÜNİ VB.) ---
    # Eğer bir durağın hiçbir yere gidişi yoksa, onu en yakın durağa 1km içinde bağla
    # Optimization: Process AFTER loading all routes so we only check truly isolated nodes
    print("Info: İzole duraklar (Medeniyet Üni vb.) ağa bağlanıyor...")
    
    # Grid optimization for nearest neighbor search
    CELL_SIZE = 0.01 
    grid = defaultdict(list)
    all_stops_list = list(duraklar_sozlugu.values())
    
    # Sadece komşusu olan (bağlı) durakları grid'e ekle (hedef olarak)
    for d in all_stops_list:
        if d.komsular:
            x = int(d.lon / CELL_SIZE)
            y = int(d.lat / CELL_SIZE)
            grid[(x, y)].append(d)
            
    neighbor_offsets = [(-1,-1), (-1,0), (-1,1), (0,-1), (0,0), (0,1), (1,-1), (1,0), (1,1)]
    
    isolated_count = 0
    for d in all_stops_list:
        if not d.komsular:
            # Grid search for this isolated node
            gx = int(d.lon / CELL_SIZE)
            gy = int(d.lat / CELL_SIZE)
            
            closest_node = None
            min_d = 1000.0 # Max 1km
            
            candidates = []
            for dx, dy in neighbor_offsets:
                candidates.extend(grid.get((gx+dx, gy+dy), []))
            
            for target in candidates:
                if d.id == target.id: continue
                
                dist = haversine_distance(d.lat, d.lon, target.lat, target.lon)
                if dist < min_d:
                    min_d = dist
                    closest_node = target
            
            if closest_node:
                # 100m = 1dk
                yurume_suresi_dk = min_d / 100.0
                edge_val = (yurume_suresi_dk, 1.0, True, "walking", ["BAGLANTI"], [(d.lat, d.lon), (closest_node.lat, closest_node.lon)])
                d.komsular[closest_node.id] = edge_val
                closest_node.komsular[d.id] = edge_val
                isolated_count += 1
                
    print(f"--> {isolated_count} izole durak ağa bağlandı.")
    
    # Final Transfer Bağlantıları (400m)
    duraklar_sozlugu = baglantilari_birlestir_transfer_ile(duraklar_sozlugu, transfer_mesafesi=400.0, yurume_hizi_m_dk=100.0)
    
    return duraklar_sozlugu


# ====================================================================
# III. ALGORİTMALAR (BFS ve DIJKSTRA)
# ====================================================================

# Helper for unpacking edges safely
def unpack_edge(edge_val):
    """
    Kenar verisini açar.
    Format: (sure, yogunluk, durum, tur, hat_LIST, path_coords)
    """
    if len(edge_val) == 6:
        return edge_val
    elif len(edge_val) == 5:
        # Eski format (koordinat yok)
        return edge_val[0], edge_val[1], edge_val[2], edge_val[3], edge_val[4], []
    elif len(edge_val) == 4:
        return edge_val[0], edge_val[1], edge_val[2], edge_val[3], [], []
    else:
        return edge_val[0], edge_val[1], edge_val[2], "bus", [], []

def en_az_aktarma_bul(baslangic_ad, hedef_ad, duraklar_sozlugu):
    """
    BFS ile en az aktarma rotası bulur.
    Yürüme kenarları aktarma sayılmaz ama kullanılır (mecbur kalınca).
    """
    ad_to_id = {d.ad: d.id for d in duraklar_sozlugu.values()}

    try:
        baslangic_id = ad_to_id[baslangic_ad.strip()]
        hedef_id = ad_to_id[hedef_ad.strip()]
    except KeyError:
        return ["Hata: Durak bulunamadı."], 0

    if baslangic_id == hedef_id:
        return [baslangic_id], 0

    # (current_id, yol_ids, prev_transport_type)
    kuyruk = deque([(baslangic_id, [baslangic_id], None)])
    # State: (node_id, transport_type) -> min_transfers
    ziyaret_edildi = {(baslangic_id, None): 0}

    while kuyruk:
        mevcut_id, yol_ids, prev_type = kuyruk.popleft()
        mevcut_durak = duraklar_sozlugu[mevcut_id]
        current_transfers = ziyaret_edildi.get((mevcut_id, prev_type), 0)

        for komsunun_id, val in mevcut_durak.komsular.items():
            sure, yogunluk, durum, tur, _, _ = unpack_edge(val)

            if not durum:
                continue

            # Aktarma hesabı: Yürüme aktarma sayılmaz
            new_transfers = current_transfers
            if prev_type is not None and prev_type != "walking" and tur != "walking" and tur != prev_type:
                new_transfers += 1  # Gerçek aktarma (araçtan araça)
            
            state_key = (komsunun_id, tur)
            
            # Eğer bu state'i daha az aktarmayla ziyaret etmişsek, atla
            if state_key in ziyaret_edildi and ziyaret_edildi[state_key] <= new_transfers:
                continue
            
            ziyaret_edildi[state_key] = new_transfers
            yeni_yol = yol_ids + [komsunun_id]

            if komsunun_id == hedef_id:
                # Hedefe ulaştık - rotayı döndür
                return yeni_yol, new_transfers

            kuyruk.append((komsunun_id, yeni_yol, tur))

    return [], -1


def en_kisa_sure_bul(baslangic_ad, hedef_ad, duraklar_sozlugu):
    ad_to_id = {d.ad: d.id for d in duraklar_sozlugu.values()}

    try:
        baslangic_id = ad_to_id[baslangic_ad.strip()]
        hedef_id = ad_to_id[hedef_ad.strip()]
    except KeyError:
        return [], 0

    # Transfer Cezası (Dakika)
    TRANSFER_PENALTY = 2.0  
    WALKING_START_PENALTY = 3.0

    # (toplam_sure, mevcut_id, gelen_hat, yol_listesi_ids)
    pq = [(0, baslangic_id, None, [baslangic_id])]
    
    # Sadece node_id bazlı state tracking (daha basit ve etkili)
    min_costs = {}

    while pq:
        current_cost, current_id, prev_line, yol_ids = heapq.heappop(pq)

        if current_id == hedef_id:
            # Hedefe ulaştık - rotayı döndür
            return yol_ids, current_cost

        # Basitleştirilmiş state - sadece node ID
        if current_id in min_costs and min_costs[current_id] <= current_cost:
            continue
        min_costs[current_id] = current_cost

        mevcut_durak = duraklar_sozlugu[current_id]

        for komsunun_id, val in mevcut_durak.komsular.items():
            sure, yogunluk, durum, tur, hat_ismi, _ = unpack_edge(val)

            if not durum: 
                continue
            
            travel_time = sure * yogunluk
            
            # Hat listesini normalize et
            available_lines = []
            if isinstance(hat_ismi, list):
                available_lines = hat_ismi
            elif hat_ismi:
                available_lines = [str(hat_ismi)]
            
            penalty = 0
            selected_next_line = None
            
            # Yürüme kenarı kontrolü
            is_walking_edge = (tur == "walking")
            
            if is_walking_edge:
                selected_next_line = "walking"
                if prev_line and prev_line != "walking":
                    penalty = WALKING_START_PENALTY
            else:
                if not available_lines:
                    selected_next_line = tur
                elif prev_line in available_lines:
                    selected_next_line = prev_line
                    penalty = 0
                else:
                    selected_next_line = available_lines[0]
                    if prev_line is None:
                        penalty = 0
                    elif prev_line == "walking":
                        penalty = WALKING_START_PENALTY
                    else:
                        penalty = TRANSFER_PENALTY

            new_cost = current_cost + travel_time + penalty

            # Komşu düğümü kuyruğa ekle
            if komsunun_id not in min_costs or new_cost < min_costs.get(komsunun_id, float('inf')):
                heapq.heappush(pq, (new_cost, komsunun_id, selected_next_line, yol_ids + [komsunun_id]))

    return [], -1


def cok_kriterli_rota_bul(baslangic_ad, hedef_ad, duraklar_sozlugu, zaman_agirligi=1.0, aktarma_agirligi=6000.0):
    """
    Çok kriterli rota bulma: Zaman ve aktarma sayısını dengeler.
    Gerçek aktarma sayısını hesaplar (her kenar değil, sadece hat değişimi).
    """
    ad_to_id = {d.ad: d.id for d in duraklar_sozlugu.values()}

    try:
        baslangic_id = ad_to_id[baslangic_ad.strip()]
        hedef_id = ad_to_id[hedef_ad.strip()]
    except KeyError:
        return [], 0, 0, 0

    # (maliyet, toplam_sure, aktarma_sayisi, mevcut_id, prev_line, yol_ids)
    pq = [(0, 0, 0, baslangic_id, None, [baslangic_id])]
    # State: (node_id, prev_line) -> (min_cost, min_time, min_transfers)
    en_iyi_maliyetler = {(baslangic_id, None): (0, 0, 0)}

    while pq:
        maliyet, top_sure, aktarma, mevcut_id, prev_line, yol_ids = heapq.heappop(pq)

        if mevcut_id == hedef_id:
            # Hedefe ulaştık - rotayı döndür
            return yol_ids, top_sure, aktarma, maliyet

        state_key = (mevcut_id, prev_line)
        if state_key in en_iyi_maliyetler:
            best_cost, best_time, best_transfers = en_iyi_maliyetler[state_key]
            if maliyet > best_cost:
                continue

        mevcut_durak = duraklar_sozlugu[mevcut_id]

        for komsunun_id, val in mevcut_durak.komsular.items():
            sure, yogunluk, durum, tur, hat_ismi, _ = unpack_edge(val)
            
            if not durum: 
                continue
            
            segment_suresi = sure * yogunluk
            yeni_top_sure = top_sure + segment_suresi
            
            # Hat listesini normalize et
            available_lines = []
            if isinstance(hat_ismi, list):
                available_lines = hat_ismi
            elif hat_ismi:
                available_lines = [str(hat_ismi)]
            
            # Aktarma hesabı (Dijkstra ile aynı mantık)
            yeni_aktarma = aktarma
            selected_next_line = None
            
            is_walking = (tur == "walking")
            
            if is_walking:
                selected_next_line = "walking"
            else:
                if not available_lines:
                    selected_next_line = tur
                elif prev_line in available_lines:
                    selected_next_line = prev_line
                else:
                    selected_next_line = available_lines[0]
                    if prev_line is not None and prev_line != "walking":
                        yeni_aktarma += 1
            
            yeni_maliyet = (yeni_top_sure * zaman_agirligi) + (yeni_aktarma * aktarma_agirligi)
            
            next_state_key = (komsunun_id, selected_next_line)
            
            if next_state_key not in en_iyi_maliyetler or yeni_maliyet < en_iyi_maliyetler[next_state_key][0]:
                en_iyi_maliyetler[next_state_key] = (yeni_maliyet, yeni_top_sure, yeni_aktarma)
                # NOT: yolda ID saklıyoruz
                yeni_yol = yol_ids + [komsunun_id]
                heapq.heappush(pq, (yeni_maliyet, yeni_top_sure, yeni_aktarma, komsunun_id, selected_next_line, yeni_yol))

    return [], -1, -1, -1