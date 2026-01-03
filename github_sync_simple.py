"""
Sincronización simple con GitHub API para Zelenza
"""

import os
import json
import base64
import requests
from datetime import datetime
import streamlit as st

class GitHubSyncSimple:
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
    
    def test_connection(self):
        """Prueba la conexión a GitHub"""
        try:
            response = requests.get(self.api_base, headers=self.headers)
            if response.status_code == 200:
                return True, "✅ Conexión exitosa a GitHub"
            else:
                return False, f"❌ Error {response.status_code}: {response.text}"
        except Exception as e:
            return False, f"❌ Error de conexión: {str(e)}"
    
    def upload_file(self, file_path, content, message="Sync desde app"):
        """Sube un archivo a GitHub"""
        try:
            # Codificar contenido en base64
            content_b64 = base64.b64encode(content.encode('utf-8')).decode('utf-8')
            
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
                return True, f"✅ Archivo {file_path} subido"
            else:
                return False, f"❌ Error subiendo {file_path}: {response.status_code}"
                
        except Exception as e:
            return False, f"❌ Error: {str(e)}"
    
    def sync_data_files(self):
        """Sincroniza archivos importantes de data/"""
        files_to_sync = [
            "data/precios_luz.csv",
            "data/config_excedentes.csv",
            "data/planes_gas.json",
            "database.json"
        ]
        
        results = []
        success_count = 0
        
        for file_path in files_to_sync:
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    success, message = self.upload_file(
                        file_path, 
                        content,
                        f"Sync automática: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                    )
                    
                    results.append(f"{'✅' if success else '❌'} {file_path}")
                    if success:
                        success_count += 1
                        
                except Exception as e:
                    results.append(f"❌ {file_path}: Error {str(e)}")
            else:
                results.append(f"⚠️ {file_path}: No existe")
        
        return success_count, len(files_to_sync), results

def test_github_config():
    """Función para probar configuración de GitHub"""
    try:
        sync = GitHubSyncSimple()
        success, message = sync.test_connection()
        return success, message
    except ValueError as e:
        return False, str(e)
    except Exception as e:
        return False, f"Error: {str(e)}"