"""
Sistema de sync automático en segundo plano cada hora
"""

import time
import threading
from sync_data_to_github import sync_manager

def background_sync_worker():
    """Worker que ejecuta sync automático en segundo plano"""
    print("🔄 Iniciando worker de sync automático...")
    
    while True:
        try:
            # Verificar si hay cambios
            changed_files = sync_manager.check_for_changes()
            
            if changed_files:
                print(f"📁 {len(changed_files)} archivos modificados, sincronizando...")
                success_count, total_files, results = sync_manager.sync_all_changed_files()
                
                if success_count > 0:
                    print(f"✅ Auto-sync completado: {success_count}/{total_files} archivos")
                else:
                    print(f"⚠️ Auto-sync falló para {total_files} archivos")
            
            # Esperar 1 hora
            time.sleep(3600)
            
        except Exception as e:
            print(f"❌ Error en worker de sync: {e}")
            time.sleep(300)  # Esperar 5 minutos si hay error

def start_background_sync():
    """Inicia el sync en segundo plano"""
    try:
        thread = threading.Thread(target=background_sync_worker, daemon=True)
        thread.start()
        print("✅ Worker de sync automático iniciado")
        return True
    except:
        print("❌ No se pudo iniciar worker de sync")
        return False

# Iniciar automáticamente al importar
start_background_sync()