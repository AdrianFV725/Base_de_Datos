import spacy
import re
import json
import sys
import yake
import psycopg
from psycopg import sql
from spacy.pipeline import EntityRuler
import os

# ——— Database settings ———
DB_PARAMS = {
    "dbname":   "house_of_emigrants",
    "user":     "postgres",
    "password": "666",
    "host":     "localhost",
    "port":     "5432"
}

def get_db_connection():
    return psycopg.connect(**DB_PARAMS)

# ——— NLP setup ———
def crear_pipeline(nlp):
    ruler = nlp.add_pipe("entity_ruler", before="ner")
    patterns = [
        {"label":"DATE", "pattern":[{"TEXT":{"REGEX":r"\d{4}-\d{2}-\d{2}"}}]},
        {"label":"BIRTHDATE", "pattern":[
            {"TEXT":{"REGEX":r"\d{4}-\d{2}-\d{2}"}},
        ]},
        {"label":"ADDRESS", "pattern":[
            {"TEXT":{"REGEX":r"\d+"}},{"OP":"+"},
            {"TEXT":{"REGEX":r"[A-Za-z]+"}},
            {"TEXT":{"REGEX":r"(Avenue|Street|Road|Blvd|vägen|gatan)"}}                                                                      
        ]},
        {"label":"REGION", "pattern":[{"TEXT":{"REGEX":r"(Region|Province|County|State|District|Región|Provincia|Estado|Condado)"}}]}
    ]
    ruler.add_patterns(patterns)
    return nlp

def extract_keywords(text):
    kw = yake.KeywordExtractor(lan="en", n=1, dedupLim=0.9, top=10)
    kws = [phrase.lower() for phrase, score in kw.extract_keywords(text)]
    return list(dict.fromkeys(kws))

def extract_regions(text):
    # Lista de regiones comunes suecas
    common_regions = [
        "Skåne", "Småland", "Västra Götaland", "Stockholm", "Uppsala",
        "Södermanland", "Östergötland", "Jönköping", "Kronoberg", "Kalmar",
        "Gotland", "Blekinge", "Halland", "Värmland", "Örebro", "Västmanland",
        "Dalarna", "Gävleborg", "Västernorrland", "Jämtland", "Västerbotten", "Norrbotten"
    ]
    
    # Lista de ciudades comunes suecas y otras relevantes
    common_cities = [
        "Stockholm", "Gothenburg", "Göteborg", "Malmö", "Uppsala", "Linköping", 
        "Västerås", "Örebro", "Norrköping", "Helsingborg", "Lund", "Borås", 
        "Umeå", "Gävle", "Södertälje", "Karlstad", "Växjö", "Halmstad", "Sundsvall",
        "Eskilstuna", "Falun", "Kalmar", "Karlskrona", "Kiruna", "Visby", 
        "Ystad", "Mora", "Varberg", "Trelleborg", "Skellefteå", "Jönköping",
        "Jamestown", "Chicago", "New York", "Minnesota", "Duluth", "Boston",
        "Michigan", "Wisconsin", "Iowa", "Illinois", "Nebraska", "Dakota",
        "Seattle", "Portland", "Tacoma", "Washington", "Oregon", "California",
        "San Francisco", "Philadelphia", "Baltimore", "Kansas City", "Denver",
        "St. Paul", "Minneapolis", "St. Louis", "Cincinnati", "Cleveland",
        "Detroit", "Buffalo", "Pittsburgh", "Quebec", "Montreal", "Toronto",
        "Canada", "Halifax", "Winnipeg", "Manitoba", "Nova Scotia", "Ontario"
    ]
    
    found_regions = []
    
    # Primero intentamos extraer ciudades y regiones comunes del texto
    text_lower = text.lower()
    
    # Buscar ciudades por nombre
    for city in common_cities:
        if city.lower() in text_lower:
            found_regions.append(city)
    
    # Buscar regiones por nombre
    for region in common_regions:
        if region.lower() in text_lower:
            found_regions.append(region)
    
    # Si no encontramos regiones específicas, buscamos patrones como "Region de X" o "X County"
    if not found_regions:
        region_patterns = [
            r"(Region|Province|County|State|District|Región|Provincia|Estado|Condado)\s+(?:of|de|del|de la)?\s+([A-Za-zåäöÅÄÖ]+)",
            r"(?:in|from|at|en|från|i)\s+([A-Z][a-zåäöÅÄÖ]+(?:\s+[A-Z][a-zåäöÅÄÖ]+)?)",  # Busca frases como "in Stockholm" o "from Västra Götaland"
            r"(?:to|moved to|went to|till|flyttade till)\s+([A-Z][a-zåäöÅÄÖ]+(?:\s+[A-Z][a-zåäöÅÄÖ]+)?)",  # Destinos
            r"born\s+in\s+([A-Z][a-zåäöÅÄÖ]+(?:\s+[A-Z][a-zåäöÅÄÖ]+)?)",  # Lugar de nacimiento
            r"lived\s+in\s+([A-Z][a-zåäöÅÄÖ]+(?:\s+[A-Z][a-zåäöÅÄÖ]+)?)"   # Lugar donde vivió
        ]
        
        for pattern in region_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                if len(match.groups()) >= 1:
                    # El último grupo capturado debería contener el nombre de la región/ciudad
                    region_name = match.group(len(match.groups()))
                    if region_name and len(region_name) > 2:  # Evitar lugares demasiado cortos
                        found_regions.append(region_name)
    
    # Eliminar duplicados y devolver
    return list(dict.fromkeys(found_regions))

def extraer_datos(texto, nlp):
    doc = nlp(texto)
    datos = {
        "fechas": [],
        "nombres": [],
        "direcciones": [],
        "fechas_nac": [],
        "palabras_clave": [],
        "regiones": []
    }
    for ent in doc.ents:
        if ent.label_ == "DATE" and re.match(r"\d{4}-\d{2}-\d{2}", ent.text):
            datos["fechas"].append(ent.text)
        if ent.label_ == "PERSON":
            datos["nombres"].append(ent.text)
        if ent.label_ == "ADDRESS":
            datos["direcciones"].append(ent.text)
        if ent.label_ == "BIRTHDATE":
            datos["fechas_nac"].append(ent.text)
        if ent.label_ == "GPE" or ent.label_ == "LOC":
            datos["regiones"].append(ent.text)
    
    # Extraer regiones adicionales usando patrones específicos
    datos["regiones"].extend(extract_regions(texto))
    datos["regiones"] = list(dict.fromkeys(datos["regiones"]))
    
    datos["palabras_clave"] = extract_keywords(texto)
    # dedupe names
    datos["nombres"] = list(dict.fromkeys(datos["nombres"]))
    return datos

# ——— Persistence ———
def store_to_db(texto, filepath):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Extract data from text
        nlp = spacy.load("en_core_web_md")
        nlp = crear_pipeline(nlp)
        datos = extraer_datos(texto, nlp)
        
        # 1) Insert person info
        if datos["nombres"]:
            parts = datos["nombres"][0].split(None, 1)
            first_name = parts[0]
            first_surname = parts[1] if len(parts) > 1 else ""
        else:
            first_name, first_surname = ("Unknown", "")
            
        cur.execute(
            sql.SQL("""
              INSERT INTO person_info (first_name, first_surname)
              VALUES (%s, %s)
              RETURNING id_person
            """),
            [first_name, first_surname]
        )
        person_id = cur.fetchone()[0]
        
        # 2) Get default values for reference tables or create them if needed
        # Default sex
        cur.execute("SELECT id_sex FROM sexes LIMIT 1")
        sex_id = cur.fetchone()
        if not sex_id:
            cur.execute("INSERT INTO sexes (sex) VALUES ('Unknown') RETURNING id_sex")
            sex_id = cur.fetchone()[0]
        else:
            sex_id = sex_id[0]
            
        # Default marital status
        cur.execute("SELECT id_marital FROM marital_statuses LIMIT 1")
        marital_id = cur.fetchone()
        if not marital_id:
            cur.execute("INSERT INTO marital_statuses (status) VALUES ('Unknown') RETURNING id_marital")
            marital_id = cur.fetchone()[0]
        else:
            marital_id = marital_id[0]
            
        # Default education level
        cur.execute("SELECT id_education FROM education_levels LIMIT 1")
        education_id = cur.fetchone()
        if not education_id:
            cur.execute("INSERT INTO education_levels (level) VALUES ('Unknown') RETURNING id_education")
            education_id = cur.fetchone()[0]
        else:
            education_id = education_id[0]
            
        # Default legal status
        cur.execute("SELECT id_legal FROM legal_statuses LIMIT 1")
        legal_id = cur.fetchone()
        if not legal_id:
            cur.execute("INSERT INTO legal_statuses (status) VALUES ('Unknown') RETURNING id_legal")
            legal_id = cur.fetchone()[0]
        else:
            legal_id = legal_id[0]
        
        # 3) Insert demographic info
        cur.execute(
            sql.SQL("""
              INSERT INTO demographic_info 
              (id_main_person, id_sex, id_marital, id_education, id_legal)
              VALUES (%s, %s, %s, %s, %s)
              RETURNING id_demography
            """),
            [person_id, sex_id, marital_id, education_id, legal_id]
        )
        demography_id = cur.fetchone()[0]
        
        # 4) Create family link
        cur.execute(
            sql.SQL("""
              INSERT INTO family_link (id_demography, id_person)
              VALUES (%s, %s)
            """),
            [demography_id, person_id]
        )
        
        # 5) Create country entry if needed
        cur.execute("SELECT id_country FROM countries LIMIT 1")
        country_id = cur.fetchone()
        if not country_id:
            cur.execute("INSERT INTO countries (country) VALUES ('Unknown') RETURNING id_country")
            country_id = cur.fetchone()[0]
        else:
            country_id = country_id[0]
        
        # 6) Create or get region
        region_id = None
        if datos["regiones"]:
            # Guardar la primera región para la información de viaje
            region_name = datos["regiones"][0]
            # Check if region exists
            cur.execute("SELECT id_region FROM regions WHERE region_name = %s", [region_name])
            region_row = cur.fetchone()
            if region_row:
                region_id = region_row[0]
            else:
                # Create new region
                cur.execute(
                    "INSERT INTO regions (region_name, id_country) VALUES (%s, %s) RETURNING id_region",
                    [region_name, country_id]
                )
                region_id = cur.fetchone()[0]
            
            # También guardar todas las demás regiones encontradas
            for additional_region in datos["regiones"][1:]:
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
                        print(f"Región adicional guardada: {additional_region}")
            
        # 7) Default travel method
        cur.execute("SELECT id_travel_method FROM travel_methods LIMIT 1")
        travel_method_id = cur.fetchone()
        if not travel_method_id:
            cur.execute("INSERT INTO travel_methods (method) VALUES ('Unknown') RETURNING id_travel_method")
            travel_method_id = cur.fetchone()[0]
        else:
            travel_method_id = travel_method_id[0]
        
        # 8) Insert travel info
        departure_date = datos["fechas"][0] if datos["fechas"] else None
        cur.execute(
            sql.SQL("""
              INSERT INTO travel_info 
              (departure_date, departure_country, departure_region, id_travel_method, motive_migration)
              VALUES (%s, %s, %s, %s, %s)
              RETURNING id_travel
            """),
            [departure_date, country_id, region_id, travel_method_id, "Unknown motivation"]
        )
        travel_id = cur.fetchone()[0]
        
        # 9) Insert text file
        # Get just the filename from the path
        filename = os.path.basename(filepath)
        story_summary = texto[:100] + "..."  # First 100 chars as summary
        
        cur.execute(
            sql.SQL("""
              INSERT INTO text_files 
              (path, story_summary, id_demography, id_travel)
              VALUES (%s, %s, %s, %s)
              RETURNING id_text
            """),
            [filename, story_summary, demography_id, travel_id]
        )
        text_id = cur.fetchone()[0]
        
        # 10) For each keyword: insert into keywords table
        for kw in datos["palabras_clave"]:
            cur.execute(
                sql.SQL("""
                  INSERT INTO keywords (keyword, id_text)
                  VALUES (%s, %s)
                """),
                [kw, text_id]
            )

        conn.commit()
        print(f"Inserted person {person_id}, demographic info {demography_id}, travel info {travel_id}, text file {text_id}, {len(datos['palabras_clave'])} keywords.")
    except Exception as e:
        conn.rollback()
        print(f"Error storing data: {e}")
        raise
    finally:
        cur.close()
        conn.close()

def main(input_file):
    # Load text
    texto = open(input_file, "r", encoding="utf-8").read()
    
    # Store into DB
    store_to_db(texto, input_file)

if __name__ == "__main__":
    if len(sys.argv)!=2:
        print("Usage: python dataExtraction.py <input.txt>")
        sys.exit(1)
    main(sys.argv[1])
