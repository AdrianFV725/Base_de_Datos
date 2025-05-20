#!/usr/bin/env python3
import os
import sys
import time
from dataExtraction import store_to_db

def process_directory(directory_path):
    """
    Procesa todos los archivos .txt de un directorio y los almacena en la base de datos
    """
    # Verificar que el directorio existe
    if not os.path.exists(directory_path):
        print(f"Error: El directorio {directory_path} no existe.")
        return
    
    # Obtener todos los archivos .txt del directorio
    txt_files = [f for f in os.listdir(directory_path) if f.endswith('.txt') or f.endswith('.TXT')]
    total_files = len(txt_files)
    
    print(f"Se encontraron {total_files} archivos de texto para procesar.")
    
    # Procesar cada archivo
    successful = 0
    failed = 0
    
    for i, filename in enumerate(txt_files):
        file_path = os.path.join(directory_path, filename)
        print(f"Procesando archivo {i+1}/{total_files}: {filename}")
        
        try:
            # Leer el archivo
            with open(file_path, "r", encoding="utf-8") as f:
                texto = f.read()
            
            # Almacenar en la base de datos
            store_to_db(texto, file_path)
            successful += 1
            
            # Pequeña pausa para evitar sobrecargar la base de datos
            time.sleep(0.1)
            
        except Exception as e:
            print(f"Error al procesar el archivo {filename}: {str(e)}")
            failed += 1
    
    print(f"\nResumen:")
    print(f"Total procesados: {successful + failed}")
    print(f"Exitosos: {successful}")
    print(f"Fallidos: {failed}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        directory = sys.argv[1]
    else:
        directory = "./text 2"  # Directorio predeterminado
    
    print(f"Iniciando procesamiento de archivos en: {directory}")
    process_directory(directory) 