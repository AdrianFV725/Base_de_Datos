import os
import psycopg
import re
from dataExtraction import extract_regions, get_db_connection

def update_regions_in_database():
    print("Actualizando regiones en la base de datos...")
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Obtener todos los archivos de texto en la base de datos
        cur.execute("""
            SELECT tf.id_text, tf.path, ti.id_travel
            FROM text_files tf
            JOIN travel_info ti ON tf.id_travel = ti.id_travel
        """)
        text_files = cur.fetchall()
        
        print(f"Encontrados {len(text_files)} archivos de texto para procesar.")
        
        # Obtener o crear el país por defecto
        cur.execute("SELECT id_country FROM countries LIMIT 1")
        country_id = cur.fetchone()[0]
        
        # Verificar la estructura de directorios
        text_dir = os.path.join('multimedia', 'text')
        if not os.path.exists(text_dir):
            os.makedirs(text_dir, exist_ok=True)
            print(f"Creado directorio: {text_dir}")
        
        # Buscar archivos de texto en diferentes ubicaciones potenciales
        text_locations = [
            os.path.join('multimedia', 'text'),  # Lugar predeterminado
            'text',                            # Directorio text en la raíz
            'text 2',                          # Directorio text 2 en la raíz
            'texts',                           # Otro posible nombre
            os.path.join('multimedia', 'texts')
        ]
        
        # Crear un mapeo de nombres de archivo a rutas completas
        file_paths = {}
        for location in text_locations:
            if os.path.exists(location):
                for filename in os.listdir(location):
                    if filename.endswith('.txt'):
                        file_paths[filename] = os.path.join(location, filename)
        
        print(f"Encontrados {len(file_paths)} archivos .txt en el sistema de archivos.")
        
        # Lista para almacenar todas las regiones encontradas
        all_regions = []
        
        # Por cada archivo, leer su contenido y extraer regiones
        updated_count = 0
        regions_count = 0
        for id_text, path, id_travel in text_files:
            try:
                # Obtener el nombre del archivo base
                base_filename = os.path.basename(path)
                
                # Buscar la ruta real del archivo
                full_path = None
                if base_filename in file_paths:
                    full_path = file_paths[base_filename]
                else:
                    # Intentar buscar en todas las ubicaciones
                    for location in text_locations:
                        potential_path = os.path.join(location, base_filename)
                        if os.path.exists(potential_path):
                            full_path = potential_path
                            break
                
                # Verificar si el archivo existe
                if not full_path or not os.path.exists(full_path):
                    print(f"Archivo no encontrado: {base_filename}")
                    continue
                
                # Leer el contenido del archivo
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Extraer regiones usando la función mejorada
                regions = extract_regions(content)
                
                if regions:
                    # Guardar todas las regiones encontradas para estadísticas
                    all_regions.extend(regions)
                    regions_count += len(regions)
                    
                    # Usar la primera región encontrada como principal
                    region_name = regions[0]
                    
                    # Verificar si la región ya existe
                    cur.execute("SELECT id_region FROM regions WHERE region_name = %s", [region_name])
                    region_row = cur.fetchone()
                    
                    if region_row:
                        region_id = region_row[0]
                    else:
                        # Crear nueva región
                        cur.execute(
                            "INSERT INTO regions (region_name, id_country) VALUES (%s, %s) RETURNING id_region",
                            [region_name, country_id]
                        )
                        region_id = cur.fetchone()[0]
                    
                    # Actualizar la info de viaje con la región
                    cur.execute(
                        "UPDATE travel_info SET departure_region = %s WHERE id_travel = %s",
                        [region_id, id_travel]
                    )
                    
                    # También guardar todas las demás regiones encontradas
                    for additional_region in regions[1:]:
                        if additional_region != region_name:  # Evitar duplicados
                            # Check if region exists
                            cur.execute("SELECT id_region FROM regions WHERE region_name = %s", [additional_region])
                            existing_region = cur.fetchone()
                            if not existing_region:
                                # Create new region
                                cur.execute(
                                    "INSERT INTO regions (region_name, id_country) VALUES (%s, %s)",
                                    [additional_region, country_id]
                                )
                    
                    updated_count += 1
                    print(f"Actualizado: {path} -> Regiones: {', '.join(regions)}")
            except Exception as e:
                print(f"Error procesando {path}: {e}")
        
        conn.commit()
        
        # Mostrar estadísticas de regiones
        print(f"Proceso completado. Se actualizaron {updated_count} archivos.")
        print(f"Total de regiones encontradas: {regions_count}")
        
        # Las regiones más comunes
        from collections import Counter
        region_counter = Counter(all_regions)
        print("\nRegiones más comunes:")
        for region, count in region_counter.most_common(20):
            print(f"  {region}: {count}")
        
    except Exception as e:
        conn.rollback()
        print(f"Error: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    update_regions_in_database() 