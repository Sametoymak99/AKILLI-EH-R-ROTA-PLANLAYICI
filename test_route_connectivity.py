"""
Test script to check route connectivity and endpoint accuracy
"""
import r_planlayici_app
from collections import defaultdict

print("=" * 60)
print("ROTA BAGLANTI TESTI")
print("=" * 60)

# Verileri yukle
print("\n1. Veriler yukleniyor...")
duraklar = r_planlayici_app.veri_oku("stops.csv")
print(f"   OK: {len(duraklar)} durak yuklendi")

print("\n2. Baglantılar kuruluyor...")
duraklar = r_planlayici_app.baglantilari_kur(duraklar)
print("   OK: Baglantılar kuruldu")

# Test rotaları
test_routes = [
    ("Kadikoy", "Taksim"),
    ("Kadikoy", "Besiktas"),
    ("Eminonu", "Uskudar"),
    ("Sisli", "Kadikoy"),
]

print("\n" + "=" * 60)
print("ROTA TESTLERI")
print("=" * 60)

for start, end in test_routes:
    print(f"\n--- {start} -> {end} ---")
    
    # En kisa sure
    rota, sure = r_planlayici_app.en_kisa_sure_bul(start, end, duraklar)
    
    if sure == -1:
        print(f"  HATA: Rota bulunamadi!")
    else:
        print(f"  Sure: {sure:.1f} dk")
        print(f"  Durak sayisi: {len(rota)}")
        print(f"  Baslangic: {rota[0]}")
        print(f"  Bitis: {rota[-1]}")
        
        # Kontrol: Baslangic ve bitis dogru mu?
        if rota[0] != start:
            print(f"  !!! UYARI: Baslangic yanlis! Beklenen: {start}, Bulunan: {rota[0]}")
        if rota[-1] != end:
            print(f"  !!! UYARI: Bitis yanlis! Beklenen: {end}, Bulunan: {rota[-1]}")
        
        # Rota detaylarini goster
        print(f"  Rota: {' -> '.join(rota[:5])}{'...' if len(rota) > 5 else ''}")
        
        # Baglanti kontrolu
        broken_links = []
        for i in range(len(rota) - 1):
            # Durak adlarini ID'ye cevir
            ad_to_id = {d.ad: d.id for d in duraklar.values()}
            
            if rota[i] not in ad_to_id or rota[i+1] not in ad_to_id:
                broken_links.append(f"{rota[i]} -> {rota[i+1]} (Durak bulunamadi)")
                continue
            
            curr_id = ad_to_id[rota[i]]
            next_id = ad_to_id[rota[i+1]]
            
            curr_durak = duraklar[curr_id]
            
            if next_id not in curr_durak.komsular:
                broken_links.append(f"{rota[i]} -> {rota[i+1]}")
        
        if broken_links:
            print(f"  !!! KOPUK BAGLANTILAR ({len(broken_links)}):")
            for link in broken_links[:3]:
                print(f"      - {link}")

# Izole durak kontrolu
print("\n" + "=" * 60)
print("IZOLE DURAK KONTROLU")
print("=" * 60)

isolated = []
for durak_id, durak in duraklar.items():
    if not durak.komsular:
        isolated.append(durak.ad)

print(f"\nIzole durak sayisi: {len(isolated)}")
if isolated:
    print("Ornekler:")
    for name in isolated[:10]:
        print(f"  - {name}")

# Populer duraklarin baglanti sayisi
print("\n" + "=" * 60)
print("POPULER DURAKLARIN BAGLANTI SAYISI")
print("=" * 60)

popular_stops = ["Kadikoy", "Taksim", "Besiktas", "Eminonu", "Uskudar", "Sisli"]

for stop_name in popular_stops:
    ad_to_id = {d.ad: d.id for d in duraklar.values()}
    
    if stop_name in ad_to_id:
        stop_id = ad_to_id[stop_name]
        stop = duraklar[stop_id]
        print(f"\n{stop_name}:")
        print(f"  Baglanti sayisi: {len(stop.komsular)}")
        
        # Baglanti turlerini say
        transport_types = defaultdict(int)
        for neighbor_id, edge_data in stop.komsular.items():
            sure, yogunluk, durum, tur, hat_list, coords = r_planlayici_app.unpack_edge(edge_data)
            transport_types[tur] += 1
        
        print(f"  Baglanti turleri:")
        for t_type, count in sorted(transport_types.items()):
            print(f"    - {t_type}: {count}")
    else:
        print(f"\n{stop_name}: BULUNAMADI!")

print("\n" + "=" * 60)
print("TEST TAMAMLANDI")
print("=" * 60)
