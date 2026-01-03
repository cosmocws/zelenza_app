"""
Sincronización completa con GitHub API para Zelenza
Sincroniza TODA la carpeta data/ y modelos_facturas/
"""

import os
import json
import base64
import requests
from datetime import datetime
import streamlit as st
from pathlib import Path

class GitHubSyncCompleto:
    def __init__(self):
        """Inicializa con credenciales de secrets.toml"""
        self.token = st.secrets.get("GITHUB_TOKEN")
        self.owner = st.secrets.get("GITHUB_REPO_OWNER")
        self.repo = st.secrets.get("GITHUB_REPO_NAME")
        
        if not all([self.token, self.owner, self.repo]):
            raise ValueError("Faltan credenciales de GitHub en secrets.toml")
        
        self.headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }
        self.api_base = f"https://api.github.com/repos/{self.owner}/{self.repo}"
        
        # Carpetas a sincronizar
        self.folders_to_sync = ["data/", "modelos_facturas/"]
    
    def test_connection(self):
        """Prueba la conexión a GitHub"""
        try:
            response = requests.get(self.api_base, headers=self.headers)
            if response.status_code == 200:
                repo_info = response.json()
                return True, f"✅ Conectado a: {repo_info['full_name']}"
            else:
                return False, f"❌ Error {response.status_code}: {response.text}"
        except Exception as e:
            return False, f"❌ Error de conexión: {str(e)}"
    
    def get_all_files_to_sync(self):
        """Obtiene TODOS los archivos de las carpetas a sincronizar"""
        all_files = []
        
        for folder in self.folders_to_sync:
            folder_path = Path(folder)
            if folder_path.exists():
                # Recursivamente buscar todos los archivos
                for file_path in folder_path.rglob("*"):
                    if file_path.is_file():
                        # Convertir a ruta relativa
                        rel_path = str(file_path)
                        all_files.append(rel_path)
        
        return sorted(all_files)
    
    def upload_file(self, file_path, message="Sync desde app"):
        """Sube un archivo a GitHub"""
        try:
            # Leer contenido del archivo
            with open(file_path, 'rb') as f:
                content_bytes = f.read()
            
            # Codificar contenido en base64
            content_b64 = base64.b64encode(content_bytes).decode('utf-8')
            
            # Verificar si el archivo ya existe
            url = f"{self.api_base}/contents/{file_path}"
            response = requests.get(url, headers=self.headers)
            
            data = {
                "message": message,
                "content": content_b64,
                "branch": "main"
            }
            
            # Si existe, necesitamos el SHA para actualizar
            if response.status_code == 200:
                data["sha"] = response.json()["sha"]
            
            # Subir el archivo
            response = requests.put(url, headers=self.headers, json=data)
            
            if response.status_code in [200, 201]:
                return True, f"✅ {file_path}"
            else:
                return False, f"❌ {file_path} (Error: {response.status_code})"
                
        except FileNotFoundError:
            return False, f"❌ {file_path} (No existe localmente)"
        except Exception as e:
            return False, f"❌ {file_path} (Excepción: {str(e)[:50]}...)"
    
    def upload_files_batch(self, files, message="Sync batch"):
        """Sube múltiples archivos en lote"""
        results = []
        success_count = 0
        
        for i, file_path in enumerate(files):
            # Mostrar progreso en Streamlit
            progress = st.progress((i + 1) / len(files))
            st.caption(f"Subiendo {i+1}/{len(files)}: {os.path.basename(file_path)}")
            
            success, result_msg = self.upload_file(file_path, message)
            results.append(result_msg)
            
            if success:
                success_count += 1
            
            # Pequeña pausa para no saturar la API
            # time.sleep(0.1)
        
        return success_count, len(files), results
    
    def sync_all_data(self):
        """Sincroniza TODOS los archivos de data/ y modelos_facturas/"""
        # Obtener todos los archivos
        all_files = self.get_all_files_to_sync()
        
        if not all_files:
            return 0, 0, ["⚠️ No se encontraron archivos para sincronizar"]
        
        # Mensaje del commit
        commit_msg = f"Sync completa: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        # Subir archivos
        success_count, total_files, results = self.upload_files_batch(
            all_files, 
            commit_msg
        )
        
        return success_count, total_files, results
    
    def download_file(self, github_path, local_path):
        """Descarga un archivo desde GitHub"""
        try:
            url = f"{self.api_base}/contents/{github_path}?ref=main"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                file_data = response.json()
                content_b64 = file_data["content"]
                content = base64.b64decode(content_b64)
                
                # Crear directorios si no existen
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                
                # Guardar archivo local
                with open(local_path, 'wb') as f:
                    f.write(content)
                
                return True, f"✅ {github_path}"
            else:
                return False, f"❌ {github_path} (Error: {response.status_code})"
                
        except Exception as e:
            return False, f"❌ {github_path} (Excepción: {str(e)})"
    
    def download_all_from_github(self):
        """Descarga todos los archivos del repositorio"""
        try:
            # Obtener árbol del repositorio
            url = f"{self.api_base}/git/trees/main?recursive=1"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code != 200:
                return 0, 0, [f"❌ Error al obtener árbol: {response.status_code}"]
            
            tree = response.json().get("tree", [])
            
            # Filtrar solo archivos de nuestras carpetas
            files_to_download = []
            for item in tree:
                if item["type"] == "blob":  # Es un archivo
                    path = item["path"]
                    if path.startswith("data/") or path.startswith("modelos_facturas/"):
                        files_to_download.append(path)
            
            results = []
            success_count = 0
            
            for i, github_path in enumerate(files_to_download):
                progress = st.progress((i + 1) / len(files_to_download))
                st.caption(f"Descargando {i+1}/{len(files_to_download)}: {os.path.basename(github_path)}")
                
                success, result_msg = self.download_file(github_path, github_path)
                results.append(result_msg)
                
                if success:
                    success_count += 1
            
            return success_count, len(files_to_download), results
            
        except Exception as e:
            return 0, 0, [f"❌ Error general: {str(e)}"]

def test_github_config():
    """Función para probar configuración de GitHub"""
    try:
        sync = GitHubSyncCompleto()
        success, message = sync.test_connection()
        return success, message
    except ValueError as e:
        return False, str(e)
    except Exception as e:
        return False, f"Error: {str(e)}"

def get_folder_stats():
    """Obtiene estadísticas de las carpetas a sincronizar"""
    stats = {}
    
    folders = ["data/", "modelos_facturas/"]
    
    for folder in folders:
        folder_path = Path(folder)
        if folder_path.exists():
            files = []
            total_size = 0
            
            for file_path in folder_path.rglob("*"):
                if file_path.is_file():
                    files.append(str(file_path))
                    total_size += file_path.stat().st_size
            
            stats[folder] = {
                "files": len(files),
                "size_mb": round(total_size / (1024 * 1024), 2)
            }
        else:
            stats[folder] = {"files": 0, "size_mb": 0}
    
    return stats