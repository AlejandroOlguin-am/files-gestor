import os
import hashlib
import shutil
from PIL import Image

def filtrar_imagenes_pequenas(directorio_img):
    basura_dir = os.path.join(directorio_img, "_IMG_PEQUENAS")
    os.makedirs(basura_dir, exist_ok=True)
    
    for filename in os.listdir(directorio_img):
        try:
            filepath = os.path.join(directorio_img, filename)
            with Image.open(filepath) as img:
                width, height = img.size
                # Si es muy pequeña, es basura
                if width < 400 or height < 400:
                    shutil.move(filepath, os.path.join(basura_dir, filename))
        except:
            pass # No era imagen o estaba corrupta

def calcular_hash(filepath):
    """Calcula el hash MD5 de un archivo leyendo por bloques (para no llenar la RAM)."""
    hasher = hashlib.md5()
    try:
        with open(filepath, 'rb') as f:
            # Leemos en bloques de 4KB por si hay archivos gigantes
            buf = f.read(65536)
            while len(buf) > 0:
                hasher.update(buf)
                buf = f.read(65536)
        return hasher.hexdigest()
    except Exception as e:
        print(f"Error leyendo {filepath}: {e}")
        return None

def mover_duplicados(directorio_raiz):
    print(f"🔍 Analizando: {directorio_raiz}")
    
    # Diccionario para guardar {HASH: RUTA_ARCHIVO_ORIGINAL}
    unicos = {}
    
    # Carpeta donde moveremos la basura
    carpeta_destino = os.path.join(directorio_raiz, "_DUPLICADOS_DETECTADOS")
    os.makedirs(carpeta_destino, exist_ok=True)
    
    contador_duplicados = 0

    # os.walk recorre todas las subcarpetas
    for root, dirs, files in os.walk(directorio_raiz):
        # Evitar que el script se analice a sí mismo o a la carpeta de duplicados
        if "_DUPLICADOS_DETECTADOS" in root:
            continue
            
        for filename in files:
            # Ignorar el propio script si está ahí
            if filename == "limpiador.py":
                continue

            ruta_completa = os.path.join(root, filename)
            
            # 1. Calcular Hash
            file_hash = calcular_hash(ruta_completa)
            
            if file_hash is None:
                continue

            # 2. Verificar si ya existe
            if file_hash in unicos:
                # ¡Es un duplicado!
                original = unicos[file_hash]
                print(f"♻️ Duplicado encontrado: {filename}")
                print(f"   -> Original era: {os.path.basename(original)}")
                
                # Mover a la carpeta de cuarentena
                # Manejamos colisión de nombres en destino agregando un contador si es necesario
                destino_final = os.path.join(carpeta_destino, filename)
                if os.path.exists(destino_final):
                    nombre, ext = os.path.splitext(filename)
                    destino_final = os.path.join(carpeta_destino, f"{nombre}_dup{contador_duplicados}{ext}")
                
                shutil.move(ruta_completa, destino_final)
                contador_duplicados += 1
            else:
                # Es nuevo, lo registramos
                unicos[file_hash] = ruta_completa

    print("-" * 30)
    print(f"✅ Proceso terminado. Se movieron {contador_duplicados} archivos a '_DUPLICADOS_DETECTADOS'.")

# --- EJECUCIÓN ---
if __name__ == "__main__":
    # Usamos '.' para decir "el directorio actual"
    ruta_a_limpiar = "./prueba_duplicados" 
    # O puedes poner una ruta fija: ruta_a_limpiar = "/home/olguin/prueba_duplicados"
    
    mover_duplicados(ruta_a_limpiar)