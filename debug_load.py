import r_planlayici_app
import traceback

print("Debugging data loading...")

try:
    print("Step 1: Reading stops.csv...")
    duraklar = r_planlayici_app.veri_oku("stops.csv")
    print(f"Loaded {len(duraklar)} stops from csv.")
    
    print("Step 2: Building connections (baglantilari_kur)...")
    duraklar = r_planlayici_app.baglantilari_kur(duraklar)
    print("Connections built successfully.")
    
    print("Data loading passed.")
except Exception:
    traceback.print_exc()
