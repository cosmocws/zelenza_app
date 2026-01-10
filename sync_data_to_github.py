"""
Sistema completo de sincronización: TEMPORAL → GITHUB
Sincroniza TODOS los archivos importantes de data/ y modelos_facturas/
SOLUCIÓN CORREGIDA - FUNCIONA
"""

import os
import json
import time
import streamlit as st
from datetime import datetime, timedelta
from pathlib import Path

# Importar UNA sola vez al inicio
try:
    from github_sync_completo import GitHubSyncCompleto
    GITHUB_AVAILABLE = True
except ImportError as e:
    st.error(f"❌ No se puede importar github_sync_completo: {e}")
    GITHUB_AVAILABLE = False
except Exception as e:
    st.error(f"❌ Error importando: {e}")
    GITHUB_AVAILABLE = False

class DataSyncManager:
    """Gestor de sincronización de datos TEMPORAL → GITHUB - CORREGIDO"""
    
    def __init__(self):
        self.data_folder = "data/"
        self.modelos_folder = "modelos_facturas/"
        self.sync_interval = 3600  # 1 hora en segundos
        self.last_sync_time = None
        self.last_modified_times = {}
        
        # Crear instancia UNA sola vez
        self.github_sync = None
        if GITHUB_AVAILABLE:
            try:
                self.github_sync = GitHubSyncCompleto()
            except Exception as e:
                st.warning(f"⚠️ No se pudo crear GitHubSyncCompleto: {e}")
                self.github_sync = None
        
        # Inicializar lista de archivos
        self._update_file_list()
    
    def _get_all_files_to_sync(self):
        """Obtiene TODOS los archivos de data/ y modelos_facturas/"""
        all_files = []
        
        # Obtener TODOS los archivos de data/
        if os.path.exists(self.data_folder):
            for file_path in Path(self.data_folder).rglob("*"):
                if file_path.is_file():
                    all_files.append(str(file_path))
        
        # Obtener TODOS los archivos de modelos_facturas/
        if os.path.exists(self.modelos_folder):
            for file_path in Path(self.modelos_folder).rglob("*"):
                if file_path.is_file():
                    all_files.append(str(file_path))
        
        return all_files
    
    def _update_file_list(self):
        """Actualiza la lista de archivos a sincronizar"""
        self.target_files = self._get_all_files_to_sync()
    
    def check_for_changes(self):
        """Verifica si hay archivos modificados desde la última sincronización"""
        changed_files = []
        
        # Primero actualizamos la lista por si hay nuevos archivos
        self._update_file_list()
        
        for file_path in self.target_files:
            if os.path.exists(file_path):
                current_mtime = os.path.getmtime(file_path)
                last_mtime = self.last_modified_times.get(file_path, 0)
                
                if current_mtime > last_mtime:
                    changed_files.append(file_path)
                    self.last_modified_times[file_path] = current_mtime
        
        return changed_files
    
    def sync_single_file(self, file_path, operation_name="Cambios"):
        """Sincroniza un solo archivo a GitHub - CORREGIDO"""
        try:
            # Verificar que tenemos conexión a GitHub
            if self.github_sync is None:
                return False, "GitHub no configurado o disponible"
            
            # Verificar que el archivo existe en la sesión temporal
            if not os.path.exists(file_path):
                return False, f"Archivo no existe en sesión temporal: {file_path}"
            
            # Subir archivo usando la instancia ya creada
            commit_msg = f"🔄 Sync automático: {operation_name} - {datetime.now().strftime('%H:%M')}"
            success, message = self.github_sync.upload_file(file_path, commit_msg)
            
            if success:
                # Registrar éxito
                self._log_sync(file_path, True, operation_name)
                
                # Determinar tipo de archivo para mensaje
                if "data/" in file_path:
                    file_display = file_path.replace("data/", "")
                elif "modelos_facturas/" in file_path:
                    file_display = file_path.replace("modelos_facturas/", "📄 ")
                else:
                    file_display = os.path.basename(file_path)
                
                return True, f"✅ {file_display}"
            else:
                self._log_sync(file_path, False, f"Error: {message}")
                return False, f"❌ {message}"
                
        except Exception as e:
            error_msg = f"Excepción: {str(e)[:100]}"
            self._log_sync(file_path, False, error_msg)
            return False, f"❌ Error: {str(e)[:50]}"
    
    def sync_all_changed_files(self, force=False):
        """
        Sincroniza todos los archivos modificados - CORREGIDO
        
        Args:
            force: Si True, sincroniza todos aunque no hayan cambiado
        """
        # Verificar conexión primero
        if self.github_sync is None:
            return 0, 0, ["❌ GitHub no está configurado. Verifica secrets.toml"]
        
        if force:
            # Primero actualizamos la lista por si hay nuevos archivos
            self._update_file_list()
            files_to_sync = [f for f in self.target_files if os.path.exists(f)]
        else:
            files_to_sync = self.check_for_changes()
        
        if not files_to_sync:
            return 0, 0, ["ℹ️ No hay archivos modificados para sincronizar"]
        
        results = []
        success_count = 0
        
        # Probar conexión primero
        test_success, test_message = self.github_sync.test_connection()
        if not test_success:
            return 0, len(files_to_sync), [f"❌ Error de conexión: {test_message}"]
        
        for i, file_path in enumerate(files_to_sync, 1):
            success, message = self.sync_single_file(
                file_path, 
                f"Sync {'forzado' if force else 'automático'}"
            )
            
            results.append(message)
            if success:
                success_count += 1
        
        # Actualizar tiempo de última sincronización
        if success_count > 0:
            self.last_sync_time = time.time()
        
        return success_count, len(files_to_sync), results
    
    def sync_all_files(self):
        """Sincroniza TODOS los archivos (forzado)"""
        return self.sync_all_changed_files(force=True)
    
    def should_auto_sync(self):
        """Determina si es hora de hacer sync automático"""
        if self.last_sync_time is None:
            return True
        
        elapsed = time.time() - self.last_sync_time
        return elapsed >= self.sync_interval
    
    def auto_sync_if_needed(self):
        """Ejecuta sync automático si es necesario"""
        if self.should_auto_sync() and self.github_sync is not None:
            success_count, total_files, results = self.sync_all_changed_files()
            
            if success_count > 0:
                # Log del auto-sync
                self._log_auto_sync(success_count, total_files)
                return True, f"Auto-sync: {success_count}/{total_files} archivos"
        
        return False, "No es necesario auto-sync aún"
    
    def get_sync_status(self):
        """Obtiene estado de sincronización"""
        # Actualizar lista de archivos primero
        self._update_file_list()
        
        changed_files = self.check_for_changes()
        total_files = len([f for f in self.target_files if os.path.exists(f)])
        
        status = {
            "last_sync": self.last_sync_time,
            "next_sync_in": None,
            "changed_files": changed_files,
            "total_files": total_files,
            "github_available": self.github_sync is not None
        }
        
        if self.last_sync_time:
            next_sync = self.last_sync_time + self.sync_interval
            remaining = max(0, next_sync - time.time())
            
            hours = int(remaining // 3600)
            minutes = int((remaining % 3600) // 60)
            seconds = int(remaining % 60)
            
            if hours > 0:
                status["next_sync_in"] = f"{hours}h {minutes}m"
            elif minutes > 0:
                status["next_sync_in"] = f"{minutes}m {seconds}s"
            else:
                status["next_sync_in"] = f"{seconds}s"
        
        return status
    
    def get_file_stats(self):
        """Obtiene estadísticas de los archivos"""
        data_count = 0
        modelos_count = 0
        data_size = 0
        modelos_size = 0
        
        for file_path in self.target_files:
            if os.path.exists(file_path):
                size = os.path.getsize(file_path)
                
                if "data/" in file_path:
                    data_count += 1
                    data_size += size
                elif "modelos_facturas/" in file_path:
                    modelos_count += 1
                    modelos_size += size
        
        return {
            "data_files": data_count,
            "modelos_files": modelos_count,
            "data_size_mb": round(data_size / (1024 * 1024), 2),
            "modelos_size_mb": round(modelos_size / (1024 * 1024), 2)
        }
    
    def _log_sync(self, file_path, success, details=""):
        """Registra operación de sync"""
        os.makedirs("logs", exist_ok=True)
        log_file = "logs/data_sync.log"
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        status = "✅" if success else "❌"
        
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"{timestamp} {status} {os.path.basename(file_path)} - {details}\n")
    
    def _log_auto_sync(self, success_count, total_files):
        """Registra auto-sync"""
        os.makedirs("logs", exist_ok=True)
        log_file = "logs/auto_sync_summary.log"
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"{timestamp} - AUTO-SYNC: {success_count}/{total_files} archivos\n")

# Instancia global - IMPORTANTE: Crear una sola vez
try:
    sync_manager = DataSyncManager()
except Exception as e:
    st.error(f"❌ Error inicializando DataSyncManager: {e}")
    # Crear un manager vacío para evitar crash
    class DummyManager:
        def __init__(self): pass
        def sync_all_changed_files(self, force=False): return 0, 0, ["❌ Error inicial"]
        def get_sync_status(self): return {"error": True, "github_available": False}
        def get_file_stats(self): return {}
    sync_manager = DummyManager()

# Funciones de conveniencia
def sync_now(force=False):
    """Sincroniza ahora mismo"""
    try:
        return sync_manager.sync_all_changed_files(force=force)
    except Exception as e:
        return 0, 0, [f"❌ Error en sync_now: {str(e)}"]

def sync_file(file_path):
    """Sincroniza un archivo específico"""
    return sync_manager.sync_single_file(file_path)

def get_status():
    """Obtiene estado"""
    try:
        return sync_manager.get_sync_status()
    except:
        return {"error": True, "github_available": False}

def auto_sync():
    """Auto-sync si es necesario"""
    return sync_manager.auto_sync_if_needed()

def get_file_stats():
    """Obtiene estadísticas de archivos"""
    try:
        return sync_manager.get_file_stats()
    except:
        return {"data_files": 0, "modelos_files": 0, "data_size_mb": 0, "modelos_size_mb": 0}