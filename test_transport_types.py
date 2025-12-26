"""
Test script to check if different transport types are properly loaded and accessible
"""
import r_planlayici_app
from collections import defaultdict

print("=" * 60)
print("ULAŞIM TÜRLERİ TEST SCRIPTI")
print("=" * 60)

# Verileri yükle
print("\n1. Veriler yükleniyor...")
duraklar = r_planlayici_app.veri_oku("stops.csv")
print(f"   OK: {len(duraklar)} durak yuklendi")

print("\n2. Baglantılar kuruluyor...")
duraklar = r_planlayici_app.baglantilari_kur(duraklar)
print("   OK: Baglantılar kuruldu")

# Ulaşım türlerini analiz et
print("\n3. Ulaşım türleri analiz ediliyor...")
transport_stats = defaultdict(int)
transport_examples = defaultdict(list)

for durak_id, durak in duraklar.items():
    for komsu_id, edge_data in durak.komsular.items():
        # Edge verisini aç
        sure, yogunluk, durum, tur, hat_list, coords = r_planlayici_app.unpack_edge(edge_data)
        
        transport_stats[tur] += 1
        
        # Her türden birkaç örnek sakla
        if len(transport_examples[tur]) < 3:
            komsu = duraklar.get(komsu_id)
            if komsu:
                example = f"{durak.ad} -> {komsu.ad}"
                if example not in transport_examples[tur]:
                    transport_examples[tur].append(example)

print("\n" + "=" * 60)
print("ULASIM TURLERI ISTATISTIKLERI")
print("=" * 60)

for tur in sorted(transport_stats.keys()):
    print(f"\n{tur.upper()}:")
    print(f"  Toplam baglanti: {transport_stats[tur]:,}")
    print(f"  Ornekler:")
    for example in transport_examples[tur]:
        print(f"    - {example}")

# Metro hatlarını kontrol et
print("\n" + "=" * 60)
print("METRO HATLARI KONTROLU")
print("=" * 60)

metro_lines = defaultdict(int)
for durak_id, durak in duraklar.items():
    for komsu_id, edge_data in durak.komsular.items():
        sure, yogunluk, durum, tur, hat_list, coords = r_planlayici_app.unpack_edge(edge_data)
        
        if tur == "metro":
            for hat in hat_list:
                metro_lines[hat] += 1

print("\nMetro Hatlari:")
for hat in sorted(metro_lines.keys()):
    print(f"  {hat}: {metro_lines[hat]:,} baglanti")

# Vapur hatlarını kontrol et
print("\n" + "=" * 60)
print("VAPUR HATLARI KONTROLU")
print("=" * 60)

ferry_lines = defaultdict(int)
ferry_stops = set()
for durak_id, durak in duraklar.items():
    for komsu_id, edge_data in durak.komsular.items():
        sure, yogunluk, durum, tur, hat_list, coords = r_planlayici_app.unpack_edge(edge_data)
        
        if tur == "ferry":
            ferry_stops.add(durak.ad)
            ferry_stops.add(duraklar[komsu_id].ad)
            for hat in hat_list:
                ferry_lines[hat] += 1

print(f"\nVapur Duraklari ({len(ferry_stops)}):")
for stop in sorted(ferry_stops):
    print(f"  - {stop}")

print("\nVapur Hatlari:")
for hat in sorted(ferry_lines.keys()):
    print(f"  {hat}: {ferry_lines[hat]:,} baglanti")

# Otobüs hatlarını kontrol et (sadece sayı)
print("\n" + "=" * 60)
print("OTOBUS HATLARI KONTROLU")
print("=" * 60)

bus_lines = defaultdict(int)
metrobus_lines = defaultdict(int)

for durak_id, durak in duraklar.items():
    for komsu_id, edge_data in durak.komsular.items():
        sure, yogunluk, durum, tur, hat_list, coords = r_planlayici_app.unpack_edge(edge_data)
        
        if tur == "bus":
            for hat in hat_list:
                bus_lines[hat] += 1
        elif tur == "metrobus":
            for hat in hat_list:
                metrobus_lines[hat] += 1

print(f"\nToplam Otobus Hatlari: {len(bus_lines)}")
print(f"Toplam Metrobus Hatlari: {len(metrobus_lines)}")

if metrobus_lines:
    print("\nMetrobus Hatlari:")
    for hat in sorted(metrobus_lines.keys()):
        print(f"  {hat}: {metrobus_lines[hat]:,} baglanti")

print("\n" + "=" * 60)
print("TEST TAMAMLANDI")
print("=" * 60)
