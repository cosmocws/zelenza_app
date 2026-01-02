#!/usr/bin/env python3
"""
Script de sincronización automática con GitHub para la app de Zelenza.
Este script se puede programar para ejecutarse cada 4 horas (cron job).
"""

import os
import json
import datetime
import subprocess
import sys
from pathlib import Path

# Configuración
REPO_DIR = Path(__file__).parent  # Directorio raíz del proyecto
GIT_COMMAND = "git"  # Asegúrate de que git esté en el PATH
BRANCH = "main"  # o "master" según tu configuración

def ejecutar_comando_git(comando, cwd=None):
    """Ejecuta un comando git y retorna el resultado"""
    if cwd is None:
        cwd = REPO_DIR
    
    try:
        # Dividir el comando en lista para subprocess
        if isinstance(comando, str):
            comando = comando.split()
        
        # Ejecutar comando
        resultado = subprocess.run(
            comando,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False  # No lanzar excepción en error
        )
        
        return {
            'exitoso': resultado.returncode == 0,
            'codigo_salida': resultado.returncode,
            'salida': resultado.stdout.strip(),
            'error': resultado.stderr.strip()
        }
    
    except Exception as e:
        return {
            'exitoso': False,
            'codigo_salida': -1,
            'salida': '',
            'error': str(e)
        }

def verificar_estado_git():
    """Verifica si estamos en un repositorio git válido"""
    resultado = ejecutar_comando_git("git status")
    
    if not resultado['exitoso']:
        print("❌ No es un repositorio git válido o git no está instalado")
        print(f"Error: {resultado['error']}")
        return False
    
    return True

def sincronizar_con_github():
    """Realiza la sincronización completa: pull, commit, push"""
    
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n🔄 Iniciando sincronización: {timestamp}")
    print(f"📁 Directorio: {REPO_DIR}")
    
    # 1. Verificar estado git
    if not verificar_estado_git():
        return False
    
    # 2. Obtener estado actual
    print("\n📊 Estado actual del repositorio:")
    resultado_status = ejecutar_comando_git("git status --short")
    if resultado_status['exitoso']:
        cambios = resultado_status['salida']
        if cambios:
            print("📝 Cambios detectados:")
            for linea in cambios.split('\n'):
                if linea.strip():
                    print(f"   {linea}")
        else:
            print("✅ No hay cambios pendientes")
    
    # 3. Hacer pull para traer cambios remotos
    print("\n⬇️  Haciendo pull desde GitHub...")
    resultado_pull = ejecutar_comando_git(f"git pull origin {BRANCH}")
    
    if resultado_pull['exitoso']:
        if resultado_pull['salida'] and "Already up to date" not in resultado_pull['salida']:
            print(f"✅ Pull exitoso: {resultado_pull['salida']}")
        else:
            print("✅ Ya estás al día con el repositorio remoto")
    else:
        print(f"⚠️  Problema con pull: {resultado_pull['error']}")
        # Continuamos de todos modos, podría ser conflicto que resolveremos
    
    # 4. Verificar si hay cambios locales después del pull
    resultado_status_final = ejecutar_comando_git("git status --short")
    cambios_finales = resultado_status_final['salida'] if resultado_status_final['exitoso'] else ""
    
    if not cambios_finales.strip():
        print("\n✅ No hay cambios locales para commit. Sincronización completa.")
        return True
    
    # 5. Añadir todos los cambios
    print("\n➕ Añadiendo cambios al staging...")
    resultado_add = ejecutar_comando_git("git add .")
    
    if resultado_add['exitoso']:
        print("✅ Cambios añadidos correctamente")
    else:
        print(f"❌ Error añadiendo cambios: {resultado_add['error']}")
        return False
    
    # 6. Crear commit
    mensaje_commit = f"🔄 Sincronización automática: {timestamp}"
    print(f"\n💾 Creando commit: {mensaje_commit}")
    
    resultado_commit = ejecutar_comando_git(f'git commit -m "{mensaje_commit}"')
    
    if resultado_commit['exitoso']:
        print(f"✅ Commit creado: {resultado_commit['salida']}")
    else:
        # Si falla, podría ser porque no hay cambios reales
        print(f"⚠️  Commit no creado: {resultado_commit['error']}")
        if "nothing to commit" in resultado_commit['error']:
            print("✅ No hay cambios sustanciales para commit")
            return True
    
    # 7. Hacer push a GitHub
    print(f"\n⬆️  Haciendo push a GitHub (rama: {BRANCH})...")
    resultado_push = ejecutar_comando_git(f"git push origin {BRANCH}")
    
    if resultado_push['exitoso']:
        print(f"✅ Push exitoso: {resultado_push['salida']}")
        print("\n🎉 Sincronización completada con éxito!")
        return True
    else:
        print(f"❌ Error en push: {resultado_push['error']}")
        return False

def crear_registro_sincronizacion(exito=True):
    """Crea un registro de la sincronización en un archivo log"""
    log_dir = REPO_DIR / "logs"
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / "github_sync.log"
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    estado = "✅ ÉXITO" if exito else "❌ FALLO"
    
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"{timestamp} - {estado}\n")

def main():
    """Función principal"""
    print("=" * 60)
    print("GitHub Auto-Sync - Zelenza Analytics")
    print("=" * 60)
    
    try:
        exito = sincronizar_con_github()
        crear_registro_sincronizacion(exito)
        
        if exito:
            print(f"\n✅ Sincronización completada: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            return 0
        else:
            print(f"\n❌ Sincronización falló: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            return 1
            
    except Exception as e:
        print(f"\n💥 Error inesperado: {str(e)}")
        crear_registro_sincronizacion(False)
        return 1

if __name__ == "__main__":
    sys.exit(main())