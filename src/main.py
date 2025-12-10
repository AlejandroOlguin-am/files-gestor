import os
import hashlib
import shutil

def eliminar_duplicados(directorio_origen):
    hashes = {}
    duplicados_dir = os.path.join(directorio_origen, "_DUPLICADOS")
    os.makedirs(duplicados_dir, exist_ok=True)

    for root, _, files in os.walk(directorio_origen):
        for filename in files:
            filepath = os.path.join(root, filename)
            
            # Calcular Hash
            with open(filepath, "rb") as f:
                file_hash = hashlib.md5(f.read()).hexdigest()
            
            if file_hash in hashes:
                print(f"Duplicado encontrado: {filename}")
                shutil.move(filepath, os.path.join(duplicados_dir, filename))
            else:
                hashes[file_hash] = filepath