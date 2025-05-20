# Base_de_Datos - House of Emigrants

Plataforma para la exploración y análisis de historias de emigrantes, parte del proyecto para el Museo House of Emigrants.

## Características

- Exploración de datos basada en regiones y fechas
- Visualización de historias con soporte multilingüe (español e inglés)
- Panel de administración para la gestión de archivos
- Generación automática de resúmenes de distintas longitudes
- Análisis de palabras clave y frecuencia

## Requisitos

- Python 3.8 o superior
- PostgreSQL 12 o superior
- Navegador web moderno

## Configuración del entorno virtual

Se recomienda utilizar un entorno virtual para aislar las dependencias del proyecto:

```bash
# Crear el entorno virtual
python3 -m venv venv

# Activar el entorno virtual
## En Windows:
# venv\Scripts\activate
## En macOS/Linux:
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

## Configuración de la base de datos

1. Crear una base de datos PostgreSQL llamada `house_of_emigrants`
2. Ejecutar los scripts SQL para crear las tablas:
   ```bash
   psql -U postgres -d house_of_emigrants -f tablesDatabase.sql
   psql -U postgres -d house_of_emigrants -f nuevoEsquema.sql
   ```

## Ejecución del proyecto

```bash
# Activar el entorno virtual (si no está activado)
source venv/bin/activate

# Ejecutar la aplicación
python main.py
```

La aplicación estará disponible en http://localhost:5002

## Procesamiento de textos

Para procesar nuevos archivos de texto y extraer su información:

```bash
# Procesamiento individual
python dataExtraction.py ruta/al/archivo.txt

# Procesamiento por lotes
python process_multiple_texts.py
```
