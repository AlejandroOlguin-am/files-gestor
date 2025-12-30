import os
import shutil

# ================= CONFIGURACIÓN =================

# 1. RUTA DONDE ESTÁN LAS CARPETAS recup_dir.XXX
# ¡IMPORTANTE! Cambia esto por la ruta real de tu PC.
# En Windows usa barras dobles \\ o una r delante: r"C:\Users\..."
DIRECTORIO_RAIZ = r"C:\Users\Usuario\Descargas\testdisk-7.3-WIP"
#DIRECTORIO_RAIZ = "./prueba_duplicados" # Para pruebas locales

# 2. DEFINICIÓN DE BASURA
# Extensiones que indican que una carpeta probablemente no sirve.
# AÑADE O QUITA según tus necesidades. (En minúsculas)
EXTENSIONES_BASURA = {
    # Archivos de sistema Windows y aplicaciones
    '.dll', '.exe', '.sys', '.inf', '.cab', '.msi', '.ocx', '.ax', '.ico',
    '.mui', '.cat', '.pnf', '.db', '.dat', '.ini', '.log',
    # Archivos temporales o caché web
    '.tmp', '.cache', '.js', '.css', '.html', '.json', '.xml',
    # Archivos de desarrollo/código (QUITA estos si los quieres conservar)
    '.py', '.pyc', '.c', '.cpp', '.h', '.o', '.obj', '.lib', '.a',
    '.class', '.jar', '.sh', '.bat', '.txt', '.md',
    # Archivos de fuentes (suelen aparecer miles)
    '.ttf', '.fon', '.otf'
}

# 3. UMBRAL DE TOLERANCIA
# Si una carpeta tiene más de este porcentaje de archivos basura, se elimina entera.
# 90% significa: si de 100 archivos, 90 son basura, la carpeta se va.
UMBRAL_PORCENTAJE = 90

# 4. MODO SIMULACRO (SEGURIDAD)
# True = Solo muestra qué carpetas borraría SIN borrarlas.
# False = BORRA LAS CARPETAS REALMENTE.
DRY_RUN = True

# =================================================

def es_archivo_basura(nombre_archivo):
    """Determina si un archivo individual es basura basado en su extensión."""
    # Algunos archivos recuperados no tienen extensión y tienen nombres raros como f955634016
    # Podríamos añadir lógica aquí si es necesario, pero las extensiones suelen bastar.
    _, extension = os.path.splitext(nombre_archivo)
    return extension.lower() in EXTENSIONES_BASURA

def analizar_y_limpiar_carpetas():
    print(f"--- INICIANDO ANÁLISIS EN: {DIRECTORIO_RAIZ} ---")
    if DRY_RUN:
        print(" MODO SIMULACRO ACTIVO. NO SE BORRARÁ NADA. ")
        print("Revisa la lista de abajo. Si estás de acuerdo, cambia DRY_RUN a False.")
    else:
        print(" ATENCIÓN: MODO DE BORRADO REAL ACTIVO. ")
        print("Tienes 5 segundos para cancelar (Ctrl+C) si te arrepientes...")
        import time
        time.sleep(5)

    carpetas_eliminadas = 0
    carpetas_conservadas = 0

    # Iterar solo sobre los directorios directos en la raíz
    try:
        lista_directorios = [d for d in os.listdir(DIRECTORIO_RAIZ) if os.path.isdir(os.path.join(DIRECTORIO_RAIZ, d))]
    except FileNotFoundError:
        print(f" Error: No se encuentra el directorio: {DIRECTORIO_RAIZ}")
        return

    for nombre_carpeta in lista_directorios:
        # Filtro opcional: Asegurar que solo tocamos carpetas que empiecen por "recup_dir"
        # Si tus carpetas se llaman distinto, comenta esta línea.
        if not nombre_carpeta.startswith("recup_dir"):
          continue

        ruta_carpeta_completa = os.path.join(DIRECTORIO_RAIZ, nombre_carpeta)
        
        total_archivos = 0
        total_basura = 0
        
        # Analizar archivos dentro de esta carpeta
        try:
            archivos_en_carpeta = os.listdir(ruta_carpeta_completa)
            for archivo in archivos_en_carpeta:
                ruta_archivo = os.path.join(ruta_carpeta_completa, archivo)
                if os.path.isfile(ruta_archivo):
                    total_archivos += 1
                    if es_archivo_basura(archivo):
                        total_basura += 1
        except Exception as e:
             print(f"Error leyendo carpeta {nombre_carpeta}: {e}")
             continue

        # Calcular porcentaje
        if total_archivos > 0:
            porcentaje_basura = (total_basura / total_archivos) * 100
        else:
            porcentaje_basura = 0
            # Opcional: Borrar carpetas vacías
            # if DRY_RUN: print(f"Carpeta vacía: {nombre_carpeta} (Se eliminaría)")
            # else: os.rmdir(ruta_carpeta_completa)
            continue

        # Decisión: ¿Borrar o conservar?
        if porcentaje_basura >= UMBRAL_PORCENTAJE:
            estado = " A ELIMINAR"
            carpetas_eliminadas += 1
            accion_realizada = False
            
            if not DRY_RUN:
                try:
                    # shutil.rmtree elimina un directorio y TODO su contenido
                    shutil.rmtree(ruta_carpeta_completa)
                    accion_realizada = True
                    estado = " ELIMINADA"
                except Exception as e:
                     print(f"Error al eliminar {nombre_carpeta}: {e}")

            print(f"[{estado}] {nombre_carpeta}: {total_basura}/{total_archivos} archivos son basura ({porcentaje_basura:.1f}%)")

        else:
            carpetas_conservadas += 1
            # Opcional: Mostrar carpetas que se salvan para ver qué tienen
            # if porcentaje_basura > 50: # Solo mostrar las dudosas
            #    print(f"[CONSERVADA] {nombre_carpeta}: {total_basura}/{total_archivos} basura ({porcentaje_basura:.1f}%)")

    print("-" * 30)
    estado_final = "simuladas para eliminación" if DRY_RUN else "ELIMINADAS permanentemente"
    print(f"Resumen: {carpetas_eliminadas} carpetas {estado_final}.")
    print(f"Se conservaron {carpetas_conservadas} carpetas que no superaron el umbral del {UMBRAL_PORCENTAJE}%.")

if __name__ == "__main__":
    analizar_y_limpiar_carpetas()