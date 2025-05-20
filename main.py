from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from psycopg import sql
import psycopg
import os
import json
import subprocess
from datetime import datetime
import requests  # Para las peticiones HTTP a APIs de traducción
import html  # Para escapar/desescapar HTML

app = Flask(__name__)
app.secret_key = 'a12f9c2b4d5e6f7g8h9i0jklmnopqrst'  # Needed for flashing messages

from flask import send_from_directory
@app.route('/multimedia/<path:filename>')
def serve_multimedia(filename):
    return send_from_directory('multimedia', filename)

# FILES handlings
from werkzeug.utils import secure_filename
UPLOAD_TEXT_FOLDER = './multimedia/text'
UPLOAD_IMAGE_FOLDER = './multimedia/images'
ALLOWED_TEXT_EXTENSIONS = {'txt', 'csv'}
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_TEXT_FOLDER'] = UPLOAD_TEXT_FOLDER
app.config['UPLOAD_IMAGE_FOLDER'] = UPLOAD_IMAGE_FOLDER

def allowed_file(filename, allowed_extensions):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

@app.route('/delete-file', methods=['POST'])
def delete_file():
    # require login
    if 'admin_id' not in session:
        flash('Login required.', 'danger')
        return redirect(url_for('login'))

    # path is like "text/filename.txt" or "images/photo.png"
    rel_path = request.form.get('file_path')
    full_path = os.path.join('multimedia', rel_path)

    try:
        os.remove(full_path)
        flash(f"Deleted {rel_path}", 'success')
    except FileNotFoundError:
        flash(f"File not found: {rel_path}", 'warning')
    except Exception as e:
        flash(f"Error deleting {rel_path}: {e}", 'danger')

    return redirect(url_for('upload_tool'))


@app.route('/replace-file', methods=['POST'])
def replace_file():
    if 'admin_id' not in session:
        flash('Login required.', 'danger')
        return redirect(url_for('login'))

    orig_path = request.form.get('orig_path')
    new_file = request.files.get('new_file')

    if not new_file or new_file.filename == '':
        flash('No replacement file selected.', 'warning')
        return redirect(url_for('upload_tool'))

    # overwrite the original
    full_orig = os.path.join('multimedia', orig_path)
    try:
        # optional: check extension matches orig_path's extension
        new_file.save(full_orig)
        flash(f"Replaced {orig_path}", 'success')
    except Exception as e:
        flash(f"Error replacing {orig_path}: {e}", 'danger')

    return redirect(url_for('upload_tool'))

# Database connection settings
DB_NAME = 'house_of_emigrants'
DB_USER = 'postgres'
DB_PASS = '666'
DB_HOST = 'localhost'
DB_PORT = '5432'

def get_db_connection():
    conn = psycopg.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        host=DB_HOST,
        port=DB_PORT
    )
    return conn

@app.route('/')
def homepage():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        password = request.form['password']
        print(email, " ", password)
        conn = get_db_connection()
        cur = conn.cursor()
        
        query = sql.SQL("SELECT * FROM admins WHERE email = %s")
        cur.execute(query, (email.lower(),))
        conn.commit()
        admin = cur.fetchone()
        print(admin)
        
        cur.close()
        conn.close()

        # admin[2] = password (plaintext now)
        if admin and admin[2] == password:
            session['admin_id'] = admin[0]
            session['admin_email'] = admin[1]
            flash('Login successful!', 'success')
            return redirect(url_for('homepage'))
        else:
            flash('Invalid credentials.', 'danger')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('homepage'))

@app.route('/changePassword')
def change_password():
    return render_template('changePassword.html')

@app.route('/dataExploration')
def data_exploration():
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Get filter parameters
    region_filter = request.args.get('region', '')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    
    # Build base queries with potential WHERE clauses for filters
    timeline_query = """
    SELECT
        EXTRACT(YEAR FROM ti.departure_date)::INT AS year,
        COUNT(*) AS total
    FROM text_files tf
    JOIN travel_info ti ON tf.id_travel = ti.id_travel
    WHERE ti.departure_date IS NOT NULL
    """
    
    wordfreq_query = """
      SELECT k.keyword, COUNT(*) AS freq
      FROM keywords k
      JOIN text_files tf ON k.id_text = tf.id_text
      JOIN travel_info ti ON tf.id_travel = ti.id_travel
      WHERE 1=1
    """
    
    geo_query = """
      SELECT c.country, COUNT(*) AS cnt
      FROM travel_info t
      JOIN countries c ON t.departure_country = c.id_country
      JOIN text_files tf ON tf.id_travel = t.id_travel
      WHERE 1=1
    """
    
    stories_query = """
      SELECT tf.story_summary, tf.path, p.first_name, p.first_surname
      FROM text_files tf
      JOIN demographic_info d ON tf.id_demography = d.id_demography
      JOIN person_info p ON d.id_main_person = p.id_person
      JOIN travel_info ti ON tf.id_travel = ti.id_travel
      WHERE 1=1
    """
    
    # Add region filter if specified
    region_params = []
    if region_filter:
        # Modificamos la consulta para usar una subconsulta corregida
        region_condition = " AND ti.departure_region = (SELECT id_region FROM regions WHERE region_name = %s)"
        region_params = [region_filter]
        timeline_query += region_condition
        wordfreq_query += region_condition
        geo_query = geo_query.replace("WHERE 1=1", "WHERE 1=1" + region_condition.replace("ti.", "t."))
        stories_query += region_condition
    
    # Add date range filter if specified
    date_params = []
    if start_date and end_date:
        try:
            # Parse dates to ensure they're valid
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
            
            date_condition = " AND ti.departure_date IS NOT NULL AND ti.departure_date BETWEEN %s::date AND %s::date"
            date_params = [start_date, end_date]
            
            timeline_query += date_condition
            wordfreq_query += date_condition
            geo_query = geo_query.replace("WHERE 1=1", "WHERE 1=1" + date_condition.replace("ti.", "t."))
            stories_query += date_condition
        except ValueError:
            # Invalid date format, ignore filter
            pass
    
    # Complete queries with GROUP BY and ORDER BY clauses
    timeline_query += " GROUP BY year ORDER BY year"
    wordfreq_query += " GROUP BY k.keyword ORDER BY freq DESC"
    geo_query += " GROUP BY c.country ORDER BY cnt DESC"
    stories_query += " ORDER BY tf.id_text DESC LIMIT 10"
    
    # Execute queries with parameters
    params = region_params + date_params
    
    # 1) Timeline: count of text files by year
    cur.execute(timeline_query, params)
    timeline = cur.fetchall()

    # 2) Word frequency: top keywords
    cur.execute(wordfreq_query, params)
    word_freq = cur.fetchall()

    # 3) Geographic distribution: count by country
    cur.execute(geo_query, params)
    geo = cur.fetchall()

    # 4) Get recent stories
    if start_date and end_date:
        # Si ambas fechas están especificadas, usamos el filtro de fecha con conversión
        cur.execute("""
            SELECT 
                tf.id_text,
                tf.path, 
                tf.story_summary,
                ti.departure_date, 
                p.first_name, 
                p.first_surname,
                s.sex,
                ms.status as marital_status,
                el.level as education,
                c.country as departure_country,
                ti.motive_migration,
                tm.method as travel_method,
                ti.travel_duration
            FROM text_files tf
            LEFT JOIN demographic_info d ON tf.id_demography = d.id_demography
            LEFT JOIN person_info p ON d.id_main_person = p.id_person
            LEFT JOIN travel_info ti ON tf.id_travel = ti.id_travel
            LEFT JOIN regions r ON ti.departure_region = r.id_region
            LEFT JOIN sexes s ON d.id_sex = s.id_sex
            LEFT JOIN marital_statuses ms ON d.id_marital = ms.id_marital
            LEFT JOIN education_levels el ON d.id_education = el.id_education
            LEFT JOIN countries c ON ti.departure_country = c.id_country
            LEFT JOIN travel_methods tm ON ti.id_travel_method = tm.id_travel_method
            WHERE (%s = '' OR r.region_name = %s)
            AND ti.departure_date IS NOT NULL 
            AND ti.departure_date BETWEEN %s::date AND %s::date
            ORDER BY tf.id_text DESC
            LIMIT 10
        """, (region_filter, region_filter, start_date, end_date))
    else:
        # Si no hay fechas, simplemente omitimos el filtro de fechas
        cur.execute("""
            SELECT 
                tf.id_text,
                tf.path, 
                tf.story_summary,
                ti.departure_date, 
                p.first_name, 
                p.first_surname,
                s.sex,
                ms.status as marital_status,
                el.level as education,
                c.country as departure_country,
                ti.motive_migration,
                tm.method as travel_method,
                ti.travel_duration
            FROM text_files tf
            LEFT JOIN demographic_info d ON tf.id_demography = d.id_demography
            LEFT JOIN person_info p ON d.id_main_person = p.id_person
            LEFT JOIN travel_info ti ON tf.id_travel = ti.id_travel
            LEFT JOIN regions r ON ti.departure_region = r.id_region
            LEFT JOIN sexes s ON d.id_sex = s.id_sex
            LEFT JOIN marital_statuses ms ON d.id_marital = ms.id_marital
            LEFT JOIN education_levels el ON d.id_education = el.id_education
            LEFT JOIN countries c ON ti.departure_country = c.id_country
            LEFT JOIN travel_methods tm ON ti.id_travel_method = tm.id_travel_method
            WHERE (%s = '' OR r.region_name = %s)
            ORDER BY tf.id_text DESC
            LIMIT 10
        """, (region_filter, region_filter))
    
    stories_raw = cur.fetchall()
    stories = []
    story_details = {}
    
    for story in stories_raw:
        story_id = story[0]
        path = story[1]
        summary = story[2]
        date = story[3]
        first_name = story[4] or ""
        last_name = story[5] or ""
        gender = story[6] or ""
        marital_status = story[7] or ""
        education = story[8] or ""
        country = story[9] or ""
        motive = story[10] or ""
        travel_method = story[11] or ""
        travel_duration = story[12] or ""
        
        # Obtener palabras clave para esta historia
        cur.execute("""
            SELECT keyword
            FROM keywords
            WHERE id_text = %s
            ORDER BY keyword
        """, (story_id,))
        keywords = [row[0] for row in cur.fetchall()]
        
        # Obtener título de la historia desde el nombre del archivo
        title = os.path.basename(path) if path else f"Historia {story_id}"
        
        # Formatear fecha si existe
        formatted_date = None
        if date:
            try:
                formatted_date = date.strftime('%d/%m/%Y')
            except:
                formatted_date = str(date)
        
        # Agregar a la lista de historias para el template
        stories.append((title, date, first_name, last_name, story_id))
        
        # Guardar detalles completos para uso en el frontend
        story_details[story_id] = {
            'id': story_id,
            'title': title,
            'summary': summary or '',
            'author': f"{first_name} {last_name}".strip() or "Desconocido",
            'gender': gender,
            'marital_status': marital_status,
            'education': education,
            'departure_country': country,
            'departure_date': formatted_date,
            'motive': motive,
            'travel_method': travel_method,
            'travel_duration': travel_duration,
            'keywords': keywords,
            'full_details_url': url_for('file_details', file_id=story_id)
        }
    
    # 5) Get available regions for filter dropdowns - Mejorado para mostrar todas las regiones
    # Aseguramos que la consulta devuelva todas las regiones almacenadas en la base de datos
    cur.execute("""
        SELECT DISTINCT region_name 
        FROM regions
        WHERE region_name IS NOT NULL AND region_name != ''
        ORDER BY region_name
    """)
    available_regions = [row[0] for row in cur.fetchall()]
    
    # Verificar si hay pocas regiones y diagnosticar
    if len(available_regions) < 10:
        print(f"AVISO: Solo se encontraron {len(available_regions)} regiones en la base de datos.")
        # Comprobar cuántas regiones hay en total
        cur.execute("SELECT COUNT(*) FROM regions")
        total_regions = cur.fetchone()[0]
        print(f"Total de regiones en la tabla: {total_regions}")
        
        # Mostrar las primeras 20 regiones para diagnóstico
        cur.execute("SELECT id_region, region_name FROM regions LIMIT 20")
        sample_regions = cur.fetchall()
        print("Muestra de regiones:")
        for region in sample_regions:
            print(f"  ID: {region[0]}, Nombre: {region[1]}")
    
    # 6) Get all unique keywords for the keyword panel
    cur.execute("""
        SELECT DISTINCT keyword
        FROM keywords
        ORDER BY keyword
    """)
    all_keywords = [row[0] for row in cur.fetchall()]

    cur.close()
    conn.close()

    # Turn into JSON-friendly structures
    timeline_years, timeline_counts = zip(*timeline) if timeline else ([], [])
    wf_words, wf_counts = zip(*word_freq) if word_freq else ([], [])
    geo_countries, geo_counts = zip(*geo) if geo else ([], [])

    return render_template('dataExploration.html',
        timeline_years = json.dumps(list(timeline_years)),
        timeline_counts = json.dumps(list(timeline_counts)),
        wf_words = json.dumps(list(wf_words)),
        wf_counts = json.dumps(list(wf_counts)),
        geo_countries = json.dumps(list(geo_countries)),
        geo_counts = json.dumps(list(geo_counts)),
        stories = stories,
        story_details = json.dumps(story_details),
        available_regions = available_regions,
        all_keywords = all_keywords,
        current_region = region_filter,
        start_date = start_date,
        end_date = end_date
    )


@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/uploadTool')
def upload_tool():
    if 'admin_id' not in session:
        flash('Please log in to access the upload tool.', 'warning')
        return redirect(url_for('login'))

    files = []
    # Text files
    for fname in os.listdir(app.config['UPLOAD_TEXT_FOLDER']):
        files.append({
            'name': fname,
            'type': 'text',
            'path': f'text/{fname}'
        })
    # Image files
    for fname in os.listdir(app.config['UPLOAD_IMAGE_FOLDER']):
        files.append({
            'name': fname,
            'type': 'image',
            'path': f'images/{fname}'
        })
    
    # Archivos procesados desde la base de datos
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Obtener archivos de texto de la base de datos
    cur.execute("""
        SELECT tf.id_text, tf.path, p.first_name, p.first_surname
        FROM text_files tf
        LEFT JOIN demographic_info d ON tf.id_demography = d.id_demography
        LEFT JOIN person_info p ON d.id_main_person = p.id_person
        ORDER BY tf.id_text DESC
    """)
    db_text_files = cur.fetchall()
    
    # Agregar los archivos de la base de datos a nuestra lista
    for db_file in db_text_files:
        file_id, file_path, first_name, first_surname = db_file
        name = os.path.basename(file_path) if file_path else f"Archivo {file_id}"
        files.append({
            'name': name,
            'type': 'text_db',
            'id': file_id,
            'path': file_path,
            'person': f"{first_name} {first_surname}" if first_name and first_surname else "Desconocido"
        })
    
    cur.close()
    conn.close()
    
    return render_template('uploadTool.html', files=files)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'admin_id' not in session:
        flash('Login required to upload.', 'danger')
        return redirect(url_for('login'))

    uploaded_files = request.files.getlist('files')
    upload_type    = request.form.get('type')  # 'text' or 'image'

    if not uploaded_files:
        flash('No file selected!', 'warning')
        return redirect(url_for('upload_tool'))

    for file in uploaded_files:
        filename = secure_filename(file.filename)

        # === TEXT FILES ===
        if file and upload_type == 'text' and allowed_file(filename, ALLOWED_TEXT_EXTENSIONS):
            save_path = os.path.join(app.config['UPLOAD_TEXT_FOLDER'], filename)
            file.save(save_path)

            # Immediately invoke your dataExtraction script on that file:
            try:
                # Assumes dataExtraction.py is in the same directory as main.py
                subprocess.run(
                    ['python', 'dataExtraction.py', save_path],
                    check=True,
                )
                flash(f"Uploaded and processed text file: {filename}", "success")
            except subprocess.CalledProcessError as e:
                flash(f"Uploaded {filename}, but processing failed: {e}", "warning")

        # === IMAGE FILES ===
        elif file and upload_type == 'image' and allowed_file(filename, ALLOWED_IMAGE_EXTENSIONS):
            save_path = os.path.join(app.config['UPLOAD_IMAGE_FOLDER'], filename)
            file.save(save_path)
            flash(f"Uploaded image file: {filename}", "success")

        else:
            flash(f"File '{filename}' not allowed or wrong type.", "danger")

    return redirect(url_for('upload_tool'))

@app.route('/file-details/<int:file_id>')
def file_details(file_id):
    if 'admin_id' not in session:
        flash('Please log in to access file details.', 'warning')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Obtener información detallada del archivo de texto
    cur.execute("""
        SELECT 
            tf.id_text, 
            tf.path, 
            tf.story_summary,
            p.first_name,
            p.first_surname,
            s.sex,
            ms.status as marital_status,
            el.level as education,
            ls.status as legal_status,
            ti.departure_date,
            c.country as departure_country,
            ti.motive_migration,
            tm.method as travel_method,
            ti.travel_duration,
            ti.return_plans
        FROM text_files tf
        LEFT JOIN demographic_info d ON tf.id_demography = d.id_demography
        LEFT JOIN person_info p ON d.id_main_person = p.id_person
        LEFT JOIN sexes s ON d.id_sex = s.id_sex
        LEFT JOIN marital_statuses ms ON d.id_marital = ms.id_marital
        LEFT JOIN education_levels el ON d.id_education = el.id_education
        LEFT JOIN legal_statuses ls ON d.id_legal = ls.id_legal
        LEFT JOIN travel_info ti ON tf.id_travel = ti.id_travel
        LEFT JOIN countries c ON ti.departure_country = c.id_country
        LEFT JOIN travel_methods tm ON ti.id_travel_method = tm.id_travel_method
        WHERE tf.id_text = %s
    """, (file_id,))
    file_info = cur.fetchone()
    
    # Obtener palabras clave
    cur.execute("""
        SELECT keyword
        FROM keywords
        WHERE id_text = %s
        ORDER BY keyword
    """, (file_id,))
    keywords = [row[0] for row in cur.fetchall()]
    
    cur.close()
    conn.close()
    
    if not file_info:
        flash('File not found.', 'danger')
        return redirect(url_for('upload_tool'))
    
    return render_template('file_details.html', file=file_info, keywords=keywords)

@app.route('/api/story-details/<int:story_id>')
def story_details_api(story_id):
    """API para obtener detalles de una historia específica en formato JSON."""
    try:
        print(f"DEBUG: Solicitando detalles para historia con ID: {story_id}")
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Consulta simplificada - solo consultar la tabla text_files directamente
        cur.execute("SELECT id_text, path, story_summary FROM text_files WHERE id_text = %s", (story_id,))
        basic_info = cur.fetchone()
        
        if not basic_info:
            print(f"DEBUG: No se encontró historia con ID: {story_id}")
            return jsonify({
                'error': f'Historia con ID {story_id} no encontrada',
                'keywords': []
            })
        
        id_text, path, summary = basic_info
        print(f"DEBUG: Información básica encontrada: ID={id_text}, Path={path}, Resumen disponible: {summary is not None}")
        
        # Obtener título del archivo
        title = os.path.basename(path) if path else f"Historia {id_text}"
        
        # Consulta simplificada para palabras clave
        cur.execute("SELECT keyword FROM keywords WHERE id_text = %s", (story_id,))
        keywords = [row[0] for row in cur.fetchall()]
        print(f"DEBUG: Palabras clave encontradas: {len(keywords)}")
        
        cur.close()
        conn.close()
        
        # Construir respuesta simplificada
        response_data = {
            'id': id_text,
            'title': title,
            'summary': summary or '',
            'author': "Desconocido",  # Valor por defecto simplificado
            'age': '',
            'gender': '',
            'marital_status': '',
            'education': '',
            'departure_country': '',
            'departure_date': None,
            'motive': '',
            'travel_method': '',
            'travel_duration': '',
            'keywords': keywords,
            'full_details_url': url_for('file_details', file_id=id_text)
        }
        
        print(f"DEBUG: Enviando respuesta simplificada para historia {id_text}")
        return jsonify(response_data)
    except Exception as e:
        # Registro detallado del error para depuración
        import traceback
        print(f"ERROR en story_details_api: {e}")
        print(traceback.format_exc())
        # Devolver una respuesta de error en formato JSON
        return jsonify({
            'error': f'Error al procesar la solicitud: {str(e)}',
            'details': str(e),
            'stack': traceback.format_exc()
        }), 500

@app.route('/api/generate-summary/<int:file_id>')
def generate_summary_api(file_id):
    """API para generar resúmenes de diferentes longitudes basados en el contenido del archivo."""
    try:
        # Obtener el tipo de resumen solicitado (normal, short, detailed)
        summary_type = request.args.get('type', 'normal')
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Obtener información del archivo
        cur.execute("""
            SELECT tf.path, tf.story_summary 
            FROM text_files tf
            WHERE tf.id_text = %s
        """, (file_id,))
        
        file_info = cur.fetchone()
        
        if not file_info:
            return jsonify({
                'error': f'Archivo con ID {file_id} no encontrado',
                'summary': ''
            }), 404
        
        file_path, current_summary = file_info
        
        # Obtener palabras clave para usar en el resumen
        cur.execute("SELECT keyword FROM keywords WHERE id_text = %s", (file_id,))
        keywords = [row[0] for row in cur.fetchall()]
        
        cur.close()
        conn.close()
        
        # Si no hay resumen, intentar leer el contenido del archivo
        original_text = ""
        if file_path and os.path.exists(os.path.join('multimedia', file_path)):
            try:
                with open(os.path.join('multimedia', file_path), 'r', encoding='utf-8') as f:
                    original_text = f.read()
            except Exception as e:
                print(f"Error leyendo archivo: {e}")
                
        # Usar el resumen existente si no podemos acceder al texto original
        if not original_text and current_summary:
            original_text = current_summary
        
        # Generar diferentes tipos de resumen según lo solicitado
        summary = ""
        
        if original_text:
            if summary_type == 'short':
                # Resumen corto: primeras frases hasta aproximadamente 150 caracteres
                summary = generate_short_summary(original_text, keywords)
            elif summary_type == 'detailed':
                # Resumen detallado: más largo que el original con información adicional
                summary = generate_detailed_summary(original_text, keywords)
            else:
                # Resumen normal: usar el existente o generar uno de longitud media
                summary = current_summary if current_summary else generate_normal_summary(original_text, keywords)
        else:
            summary = "No hay contenido disponible para generar un resumen."
            
        return jsonify({
            'id': file_id,
            'summary_type': summary_type,
            'summary': summary
        })
        
    except Exception as e:
        import traceback
        print(f"ERROR generando resumen: {e}")
        print(traceback.format_exc())
        return jsonify({
            'error': f'Error al generar resumen: {str(e)}',
            'details': str(e)
        }), 500

def generate_short_summary(text, keywords=None):
    """Genera un resumen corto del texto."""
    # Limpiar y dividir el texto en frases
    text = text.strip()
    sentences = [s.strip() for s in text.replace('\n', ' ').split('.') if s.strip()]
    
    # Para un resumen corto, tomamos las primeras 2-3 frases
    if len(sentences) <= 3:
        return '. '.join(sentences[:len(sentences)]) + '.'
    
    # O tomamos aproximadamente los primeros 150-200 caracteres
    short_summary = ""
    for sentence in sentences:
        if len(short_summary) + len(sentence) < 200:
            short_summary += sentence + '. '
        else:
            break
            
    # Mencionar algunas palabras clave si están disponibles
    if keywords and len(keywords) > 0:
        key_terms = ', '.join(keywords[:3])
        short_summary += f" Temas clave: {key_terms}."
        
    return short_summary

def generate_normal_summary(text, keywords=None):
    """Genera un resumen de longitud media del texto."""
    # Dividir el texto en párrafos y frases
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    
    # Para un resumen normal, tomamos el primer párrafo
    # y posiblemente un fragmento del segundo si el primero es muy corto
    summary = ""
    
    if paragraphs:
        summary = paragraphs[0]
        
        # Si el primer párrafo es corto y hay más párrafos, agregar parte del segundo
        if len(paragraphs) > 1 and len(summary) < 300:
            sentences = [s.strip() for s in paragraphs[1].replace('\n', ' ').split('.') if s.strip()]
            for sentence in sentences:
                if len(summary) + len(sentence) < 500:
                    summary += '. ' + sentence
                else:
                    break
    
    # Agregar algunas palabras clave si están disponibles
    if keywords and len(keywords) > 0:
        key_terms = ', '.join(keywords[:5])
        summary += f"\n\nPalabras clave importantes: {key_terms}."
        
    return summary

def generate_detailed_summary(text, keywords=None):
    """Genera un resumen detallado del texto."""
    # Para un resumen detallado, utilizamos más del contenido original
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    
    summary = ""
    
    # Usar los primeros 2-3 párrafos para el resumen detallado
    for i, para in enumerate(paragraphs):
        if i < 3:  # Limitamos a 3 párrafos
            summary += para + "\n\n"
        else:
            break
    
    # Incluir información estructurada sobre las palabras clave
    if keywords and len(keywords) > 0:
        summary += "Análisis de temas principales:\n"
        for i, keyword in enumerate(keywords[:8]):  # Limitamos a 8 palabras clave
            summary += f"- {keyword}\n"
    
    return summary

@app.route('/api/translate', methods=['POST'])
def translate_api():
    """API para traducir texto a diferentes idiomas."""
    try:
        data = request.json
        if not data or 'text' not in data or 'target_language' not in data:
            return jsonify({
                'error': 'Se requieren los campos "text" y "target_language"'
            }), 400
        
        text = data['text']
        target_language = data['target_language']
        
        # Validar idioma objetivo
        if target_language not in ['es', 'en']:
            return jsonify({
                'error': f'Idioma "{target_language}" no soportado. Use "es" o "en".'
            }), 400
        
        # Traducir el texto - implementación simple para pruebas
        translated_text = translate_text(text, target_language)
        
        return jsonify({
            'original_text': text,
            'target_language': target_language,
            'translated_text': translated_text
        })
        
    except Exception as e:
        import traceback
        print(f"ERROR al traducir: {e}")
        print(traceback.format_exc())
        return jsonify({
            'error': f'Error al procesar la solicitud de traducción: {str(e)}',
            'details': str(e)
        }), 500

def translate_text(text, target_language):
    """
    Traduce el texto al idioma objetivo utilizando una API externa.
    
    En un entorno de producción, aquí usarías una API como Google Translate,
    DeepL, Microsoft Translator, etc. Para esta demostración, usaremos
    un servicio gratuito básico o simulación.
    """
    try:
        # Opción 1: Usar LibreTranslate (API gratuita y de código abierto)
        # Requiere configurar un servidor LibreTranslate o usar una instancia pública
        api_url = "https://translate.fedilab.app/translate"  # Instancia pública de ejemplo
        
        source_lang = "auto"  # Auto-detección del idioma origen
        
        payload = {
            "q": text,
            "source": source_lang,
            "target": target_language,
            "format": "text"
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        response = requests.post(api_url, json=payload, headers=headers, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            if "translatedText" in result:
                return html.unescape(result["translatedText"])
        
        # Si falla, usamos una simulación básica
        print(f"Error al usar API de traducción: {response.status_code}, {response.text}")
        print("Usando traducción simulada...")
        return simulate_translation(text, target_language)
        
    except Exception as e:
        print(f"Error en la traducción: {e}")
        # En caso de error, usar una simulación básica
        return simulate_translation(text, target_language)

def simulate_translation(text, target_language):
    """
    Simula una traducción muy básica para fines de demostración.
    En producción, esto se reemplazaría por una API real.
    """
    if target_language == 'es':
        # Simular traducción al español
        text = text.replace("Summary", "Resumen")
        text = text.replace("keywords", "palabras clave")
        text = text.replace("Analysis", "Análisis")
        text = text.replace("Main themes", "Temas principales")
        text = text.replace("The", "El/La")
        text = text.replace("and", "y")
        text = text.replace("of", "de")
        text = text.replace("in", "en")
        text = text.replace("Key themes", "Temas clave")
    elif target_language == 'en':
        # Simular traducción al inglés
        text = text.replace("Resumen", "Summary")
        text = text.replace("palabras clave", "keywords")
        text = text.replace("Análisis", "Analysis")
        text = text.replace("Temas principales", "Main themes")
        text = text.replace("El/La", "The")
        text = text.replace(" y ", " and ")
        text = text.replace(" de ", " of ")
        text = text.replace(" en ", " in ")
        text = text.replace("Temas clave", "Key themes")
    
    # Añadir nota de que es una traducción simulada
    return text + "\n\n[Nota: Esta es una traducción simulada para fines de demostración. En producción, se utilizaría una API profesional de traducción.]"

if __name__ == '__main__':
    app.run(debug=True, port=5002)