"""
Comprehensive Route Verification Script
Tests connectivity, transfers, and validates that every step is physically connected in the graph.
"""
import r_planlayici_app
import sys

# Unicode output fix for console
try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

def verify_route(start_name, end_name, duraklar):
    print(f"\nTest ediliyor: {start_name} -> {end_name}")
    print("-" * 50)
    
    # Durak isimlerini dogrula
    ad_to_id = {d.ad: d.id for d in duraklar.values()}
    
    # Isim benzerliginden bul (Exact match yoksa)
    real_start = start_name
    real_end = end_name
    
    if start_name not in ad_to_id:
        candidates = [d for d in duraklar.values() if start_name.lower() in d.ad.lower()]
        if candidates:
            real_start = candidates[0].ad
            print(f"  (Bulunan baslangic: {real_start})")
        else:
            print("  HATA: Baslangic duragi veritabaninda yok!")
            return

    if end_name not in ad_to_id:
        candidates = [d for d in duraklar.values() if end_name.lower() in d.ad.lower()]
        if candidates:
            real_end = candidates[0].ad
            print(f"  (Bulunan bitis: {real_end})")
        else:
            print("  HATA: Bitis duragi veritabaninda yok!")
            return

    # Rotayi bul (Akilli Algoritma)
    try:
        rota, sure, aktarma, maliyet = r_planlayici_app.cok_kriterli_rota_bul(real_start, real_end, duraklar)
    except Exception as e:
        print(f"  HATA: Algoritma calisirken hata olustu: {e}")
        return

    if not rota or rota == ["Rota bulunamadı."] or rota == ["Kriterlere uygun rota bulunamadı."]:
        print("  SONUC: Rota bulunamadi.")
        return

    print("  SONUC: Rota bulundu!")
    print(f"  Toplam Durak: {len(rota)}")
    print(f"  Tahmini Sure: {sure:.1f} dk")
    print(f"  Aktarma Sayisi: {aktarma}")
    
    # BAGLANTI KONTROLU (Connectivity Check)
    print("\n  [BAGLANTI KONTROLU]")
    all_connected = True
    
    for i in range(len(rota) - 1):
        u_id = rota[i]
        v_id = rota[i+1]
        
        u_node = duraklar[u_id]
        v_node = duraklar[v_id]
        
        u_name = u_node.ad
        v_name = v_node.ad
        
        if v_id in u_node.komsular:
            edge = u_node.komsular[v_id]
            # Edge verisini cozumle
            val = r_planlayici_app.unpack_edge(edge)
            edge_sure = val[0]
            edge_tur = val[3]
            edge_hat = val[4] if len(val) > 4 else "?"
            
            hat_str = str(edge_hat[0]) if isinstance(edge_hat, list) and edge_hat else str(edge_hat)
            
            print(f"    OK: {u_name} -> {v_name} via {edge_tur.upper()} ({hat_str}) [{edge_sure:.1f} dk]")
        else:
            print(f"    XXX HATA: {u_name} ile {v_name} arasinda baglanti YOK! (Hayali Atlama)")
            all_connected = False
            
    if all_connected:
        print("\n  >> TEST BASARILI: Tum duraklar birbirine fiziksel olarak bagli.")
    else:
        print("\n  >> TEST BASARISIZ: Rota uzerinde kopukluklar var!")

    # Bitis noktasi kontrolu
    final_stop_id = rota[-1]
    final_stop_name = duraklar[final_stop_id].ad
    
    if final_stop_name == real_end:
        print("  >> HEDEF KONTROLU: Tam isabet (Rota istenen durakta bitiyor).")
    else:
        print(f"  >> HEDEF KONTROLU: HATALI (Bitis: {final_stop_name}, Istenen: {real_end})")


# MAIN Execution
print("Veriler yukleniyor... Lutfen bekleyin.")
r_duraklar = r_planlayici_app.veri_oku("stops.csv")
r_duraklar = r_planlayici_app.baglantilari_kur(r_duraklar)
print("Veriler hazir.\n")

# SENARYO 1: Metro hatları arası (M2 -> Bağlantı -> M1 vb veya aynı hat)
verify_route("Taksim", "Levent", r_duraklar)

# SENARYO 2: Aktarmalı Rota (Mecidiyeköy -> Kadıköy) - Metrobus veya Vapur gerektirir
verify_route("Mecidiyeköy", "Kadıköy", r_duraklar)

# SENARYO 3: Metro -> Metro (Hacıosman -> Yenikapı)
verify_route("Hacıosman", "Yenikapı", r_duraklar)

