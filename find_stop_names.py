"""
Find actual stop names in the database
"""
import r_planlayici_app

print("Durak isimleri aranıyor...")
duraklar = r_planlayici_app.veri_oku("stops.csv")
duraklar = r_planlayici_app.baglantilari_kur(duraklar)

# Populer durak isimlerini ara
search_terms = ["Kadık", "Taksim", "Beşikt", "Eminön", "Üskü", "Şişli"]

print("\n" + "=" * 60)
print("DURAK ISIMLERI")
print("=" * 60)

for term in search_terms:
    print(f"\n'{term}' iceren duraklar:")
    matches = []
    for durak in duraklar.values():
        if term.lower() in durak.ad.lower():
            matches.append(durak.ad)
    
    # Unique yap ve sirala
    matches = sorted(set(matches))
    
    for i, name in enumerate(matches[:10]):
        print(f"  {i+1}. {name}")
    
    if len(matches) > 10:
        print(f"  ... ve {len(matches) - 10} tane daha")
