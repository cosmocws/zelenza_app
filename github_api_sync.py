#!/usr/bin/env python3
"""
Sincronización con GitHub usando API REST (sin comandos git)
Funciona en Streamlit Cloud y otros servidores restringidos
"""

import os
import json
import base64
import requests
from datetime import datetime
import time
from pathlib import Path
import hashlib

class GitHubSync:
    def __init__(self, token=None, repo_owner=None, repo_name=None, branch="main"):
        """
        Inicializa el sincronizador con la API de GitHub
        
        Args:
            token: Token de acceso personal de GitHub
            repo_owner: Propietario del repositorio (usuario/organización)
            repo_name: Nombre del repositorio
            branch: Rama a usar (default: main)
        """
        self.token = token or os.environ.get("GITHUB_TOKEN")
        self.repo_owner = repo_owner or os.environ.get("GITHUB_REPO_OWNER")
        self.repo_name = repo_name or os.environ.get("GITHUB_REPO_NAME")
        self.branch = branch
        
        # Validar configuración
        if not all([self.token, self.repo_owner, self.repo_name]):
            raise ValueError("Faltan credenciales de GitHub. Configura GITHUB_TOKEN, GITHUB_REPO_OWNER y GITHUB_REPO_NAME")
        
        # Headers para la API
        self.headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        # Base URL de la API
        self.api_base = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}"
        
        # Archivos que sincronizar
        self.sync_folders = [
            "data/",
            "modelos_facturas/",
            "config/",
            "logs/",
            "database.json"
        ]
        
        # Log de operaciones
        self.log_file = "logs/github_sync.log"
        os.makedirs("logs", exist_ok=True)
    
    def log(self, message, level="INFO"):
        """Registra un mensaje en el log"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"{timestamp} - {level} - {message}\n"
        
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(log_entry)
        
        print(f"[{level}] {message}")
        return log_entry
    
    def get_file_hash(self, file_path):
        """Calcula el hash MD5 de un archivo"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def encode_file_content(self, file_path):
        """Codifica el contenido de un archivo en base64"""
        with open(file_path, "rb") as f:
            content = f.read()
        return base64.b64encode(content).decode('utf-8')
    
    def get_remote_file_sha(self, file_path):
        """Obtiene el SHA de un archivo en GitHub (si existe)"""
        api_url = f"{self.api_base}/contents/{file_path}?ref={self.branch}"
        
        try:
            response = requests.get(api_url, headers=self.headers)
            if response.status_code == 200:
                return response.json()["sha"]
            elif response.status_code == 404:
                return None  # Archivo no existe en remoto
            else:
                self.log(f"Error al obtener SHA de {file_path}: {response.status_code}", "ERROR")
                return None
        except Exception as e:
            self.log(f"Excepción al obtener SHA de {file_path}: {str(e)}", "ERROR")
            return None
    
    def upload_file(self, local_path, github_path, commit_message=None):
        """
        Sube o actualiza un archivo en GitHub
        
        Args:
            local_path: Ruta local del archivo
            github_path: Ruta en GitHub (relativa al repositorio)
            commit_message: Mensaje del commit (opcional)
        """
        if not os.path.exists(local_path):
            self.log(f"Archivo local no existe: {local_path}", "WARNING")
            return False
        
        # Obtener SHA actual (si existe)
        current_sha = self.get_remote_file_sha(github_path)
        
        # Codificar contenido
        content_encoded = self.encode_file_content(local_path)
        
        # Preparar datos para la API
        data = {
            "message": commit_message or f"Sync: {github_path}",
            "content": content_encoded,
            "branch": self.branch
        }
        
        # Añadir SHA si el archivo ya existe (para actualizar)
        if current_sha:
            data["sha"] = current_sha
        
        # URL de la API
        api_url = f"{self.api_base}/contents/{github_path}"
        
        try:
            # Realizar la petición
            if current_sha:
                method = "PUT"  # Actualizar archivo existente
            else:
                method = "PUT"  # Crear nuevo archivo
            
            response = requests.put(api_url, headers=self.headers, json=data)
            
            if response.status_code in [200, 201]:
                self.log(f"✅ Archivo sincronizado: {github_path}", "SUCCESS")
                return True
            else:
                error_msg = f"Error al subir {github_path}: {response.status_code} - {response.text}"
                self.log(error_msg, "ERROR")
                return False
                
        except Exception as e:
            self.log(f"Excepción al subir {github_path}: {str(e)}", "ERROR")
            return False
    
    def download_file(self, github_path, local_path):
        """
        Descarga un archivo desde GitHub
        
        Args:
            github_path: Ruta en GitHub (relativa al repositorio)
            local_path: Ruta local donde guardar
        """
        api_url = f"{self.api_base}/contents/{github_path}?ref={self.branch}"
        
        try:
            response = requests.get(api_url, headers=self.headers)
            
            if response.status_code == 200:
                file_data = response.json()
                
                # Decodificar contenido base64
                content_encoded = file_data["content"]
                content = base64.b64decode(content_encoded).decode('utf-8')
                
                # Crear directorios si no existen
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                
                # Guardar archivo local
                with open(local_path, "w", encoding="utf-8") as f:
                    f.write(content)
                
                self.log(f"✅ Archivo descargado: {github_path}", "SUCCESS")
                return True
            else:
                self.log(f"Error al descargar {github_path}: {response.status_code}", "WARNING")
                return False
                
        except Exception as e:
            self.log(f"Excepción al descargar {github_path}: {str(e)}", "ERROR")
            return False
    
    def list_files_to_sync(self):
        """Lista todos los archivos que deben sincronizarse"""
        all_files = []
        
        for folder in self.sync_folders:
            if folder.endswith('/'):
                # Es una carpeta, listar todos los archivos
                folder_path = Path(folder)
                if folder_path.exists():
                    for file_path in folder_path.rglob("*"):
                        if file_path.is_file():
                            # Ignorar archivos temporales o de sistema
                            if not any(ignore in str(file_path) for ignore in ['.git', '__pycache__', '.pyc', '.tmp']):
                                all_files.append(str(file_path))
            else:
                # Es un archivo individual
                if os.path.exists(folder):
                    all_files.append(folder)
        
        return all_files
    
    def sync_to_github(self, commit_message=None):
        """
        Sincroniza todos los archivos locales a GitHub (PUSH)
        
        Returns:
            dict: Resultado de la sincronización
        """
        self.log("🚀 Iniciando sincronización PUSH a GitHub", "INFO")
        
        files_to_sync = self.list_files_to_sync()
        results = {
            "total": len(files_to_sync),
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "details": []
        }
        
        commit_msg = commit_message or f"Sync automática: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        for local_file in files_to_sync:
            # Calcular ruta relativa para GitHub
            github_path = local_file
            
            # Verificar si el archivo local es más reciente
            if not os.path.exists(local_file):
                results["skipped"] += 1
                results["details"].append(f"❌ No existe: {local_file}")
                continue
            
            # Subir archivo
            success = self.upload_file(local_file, github_path, commit_msg)
            
            if success:
                results["success"] += 1
                results["details"].append(f"✅ Subido: {github_path}")
            else:
                results["failed"] += 1
                results["details"].append(f"❌ Falló: {github_path}")
        
        # Crear un commit general
        self._create_summary_commit(commit_msg, results)
        
        self.log(f"📊 Sincronización completada: {results['success']}/{results['total']} exitosas", "INFO")
        return results
    
    def sync_from_github(self):
        """
        Sincroniza archivos desde GitHub (PULL)
        
        Returns:
            dict: Resultado de la sincronización
        """
        self.log("⬇️  Iniciando sincronización PULL desde GitHub", "INFO")
        
        # Obtener lista de archivos del repositorio
        api_url = f"{self.api_base}/git/trees/{self.branch}?recursive=1"
        
        try:
            response = requests.get(api_url, headers=self.headers)
            
            if response.status_code != 200:
                self.log(f"Error al listar archivos: {response.status_code}", "ERROR")
                return {"success": False, "error": "No se pudo listar archivos del repositorio"}
            
            tree = response.json().get("tree", [])
            
            results = {
                "total": 0,
                "success": 0,
                "failed": 0,
                "details": []
            }
            
            # Filtrar solo archivos en nuestras carpetas de interés
            for item in tree:
                if item["type"] == "blob":  # Es un archivo
                    github_path = item["path"]
                    
                    # Verificar si está en nuestras carpetas de interés
                    should_sync = any(github_path.startswith(folder.rstrip('/')) 
                                     for folder in self.sync_folders)
                    
                    if should_sync:
                        results["total"] += 1
                        
                        # Ruta local equivalente
                        local_path = github_path
                        
                        # Descargar archivo
                        success = self.download_file(github_path, local_path)
                        
                        if success:
                            results["success"] += 1
                            results["details"].append(f"✅ Descargado: {github_path}")
                        else:
                            results["failed"] += 1
                            results["details"].append(f"❌ Falló: {github_path}")
            
            self.log(f"📊 Descarga completada: {results['success']}/{results['total']} exitosas", "INFO")
            return results
            
        except Exception as e:
            error_msg = f"Error en sync_from_github: {str(e)}"
            self.log(error_msg, "ERROR")
            return {"success": False, "error": error_msg}
    
    def _create_summary_commit(self, message, results):
        """Crea un commit de resumen de la sincronización"""
        summary_file = "logs/sync_summary.json"
        summary = {
            "timestamp": datetime.now().isoformat(),
            "message": message,
            "results": results,
            "type": "PUSH"
        }
        
        # Guardar resumen local
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        # Subir resumen a GitHub
        self.upload_file(summary_file, summary_file, f"Resumen sync: {message}")
        
        return summary
    
    def get_sync_status(self):
        """Obtiene el estado de la última sincronización"""
        # Leer archivo de log
        if os.path.exists(self.log_file):
            with open(self.log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            if lines:
                last_line = lines[-1]
                return {
                    "last_sync": last_line.split(" - ")[0] if " - " in last_line else "Desconocido",
                    "total_lines": len(lines),
                    "last_message": last_line.strip()
                }
        
        return {"last_sync": "Nunca", "total_lines": 0, "last_message": ""}

def test_github_connection():
    """Función de prueba para verificar conexión a GitHub"""
    try:
        sync = GitHubSync()
        api_url = sync.api_base
        
        response = requests.get(api_url, headers=sync.headers)
        
        if response.status_code == 200:
            return True, "✅ Conexión a GitHub exitosa"
        else:
            return False, f"❌ Error de conexión: {response.status_code}"
    except Exception as e:
        return False, f"❌ Error: {str(e)}"

if __name__ == "__main__":
    # Prueba básica
    print("🔧 Probando conexión con GitHub...")
    
    # Cargar configuración desde variables de entorno
    token = os.environ.get("GITHUB_TOKEN")
    owner = os.environ.get("GITHUB_REPO_OWNER")
    repo = os.environ.get("GITHUB_REPO_NAME")
    
    if not all([token, owner, repo]):
        print("❌ Faltan variables de entorno:")
        print(f"   GITHUB_TOKEN: {'✅' if token else '❌'}")
        print(f"   GITHUB_REPO_OWNER: {'✅' if owner else '❌'}")
        print(f"   GITHUB_REPO_NAME: {'✅' if repo else '❌'}")
        exit(1)
    
    # Probar conexión
    success, message = test_github_connection()
    print(message)
    
    if success:
        # Ejecutar sincronización
        sync = GitHubSync(token, owner, repo)
        
        print("\n🔄 Sincronizando con GitHub...")
        results = sync.sync_to_github("Sync automática desde script")
        
        print(f"\n📊 Resultados:")
        print(f"   ✅ Exitosos: {results['success']}")
        print(f"   ❌ Fallidos: {results['failed']}")
        print(f"   ⏭️  Saltados: {results['skipped']}")
        
        # Mostrar primeros 5 detalles
        print("\n📝 Detalles (primeros 5):")
        for detail in results['details'][:5]:
            print(f"   {detail}")
        
        if len(results['details']) > 5:
            print(f"   ... y {len(results['details']) - 5} más")