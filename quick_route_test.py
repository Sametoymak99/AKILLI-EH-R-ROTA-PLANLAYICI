"""
Quick route test with actual stop names
"""
import r_planlayici_app

print("Veriler yukleniyor...")
duraklar = r_planlayici_app.veri_oku("stops.csv")
duraklar = r_planlayici_app.baglantilari_kur(duraklar)

print("\n" + "=" * 60)
print("ROTA TESTLERI (Gercek Durak Isimleri)")
print("=" * 60)

# Test 1: Taksim'den bir yere
start = "Taksim"
end_options = []

# Taksim'in komsularini bul
ad_to_id = {d.ad: d.id for d in duraklar.values()}
if start in ad_to_id:
    taksim_id = ad_to_id[start]
    taksim = duraklar[taksim_id]
    
    print(f"\n{start} duragi bulundu!")
    print(f"Baglanti sayisi: {len(taksim.komsular)}")
    
    # Birkaç komşu al
    for neighbor_id in list(taksim.komsular.keys())[:5]:
        neighbor = duraklar[neighbor_id]
        end_options.append(neighbor.ad)
    
    print(f"Ornekleri komsular: {', '.join(end_options[:3])}")
    
    # Test rotasi
    if end_options:
        end = end_options[0]
        print(f"\n--- Test: {start} -> {end} ---")
        
        rota, sure = r_planlayici_app.en_kisa_sure_bul(start, end, duraklar)
        
        if sure != -1:
            print(f"  Basarili!")
            print(f"  Sure: {sure:.1f} dk")
            print(f"  Durak sayisi: {len(rota)}")
            print(f"  Baslangic: '{rota[0]}'")
            print(f"  Bitis: '{rota[-1]}'")
            print(f"  Rota: {' -> '.join(rota)}")
            
            # Kontrol
            if rota[0] == start and rota[-1] == end:
                print("  ✓ BASARILI: Baslangic ve bitis dogru!")
            else:
                print(f"  X HATA: Baslangic: '{rota[0]}' (beklenen: '{start}')")
                print(f"  X HATA: Bitis: '{rota[-1]}' (beklenen: '{end}')")
        else:
            print("  X Rota bulunamadi!")
else:
    print(f"\n{start} duragi bulunamadi!")

print("\n" + "=" * 60)
