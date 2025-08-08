from flask import Flask, render_template, request, jsonify, abort
import requests
import re
from urllib.parse import unquote
from math import ceil

# --- Configuración de la Aplicación ---
app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False # Mantener el orden de los diccionarios en JSON

# --- Constantes y Helpers ---
API_URLS = {
    "kemono": "https://kemono.su", # Usamos .su como dominio principal actualizado
    "coomer": "https://coomer.su",
}
VALID_SERVICES = {"onlyfans", "fansly", "patreon", "fanbox", "discord", "fantia", "gumroad", "subscribestar"}
ITEMS_PER_PAGE = 30 # Máximo de elementos a mostrar por página
API_PAGE_SIZE = 50 # Tamaño de página de la API de Kemono/Coomer

session = requests.Session()
session.headers.update({'User-Agent': 'Mozilla/5.0'})

# --- Caché simple en memoria para la lista de creadores ---
creators_cache = {}

def get_creators(platform):
    """Obtiene y cachea la lista de creadores para evitar llamadas repetidas."""
    if platform in creators_cache:
        return creators_cache[platform]
    
    api_url = API_URLS.get(platform)
    if not api_url:
        return []
        
    try:
        url = f"{api_url}/api/v1/creators.txt"
        response = session.get(url, timeout=15)
        response.raise_for_status()
        all_creators = response.json()
        
        # Filtrar y ordenar
        filtered = [c for c in all_creators if c.get("service") in VALID_SERVICES]
        filtered.sort(key=lambda c: c.get("favorited", 0), reverse=True)
        
        creators_cache[platform] = filtered
        return filtered
    except requests.RequestException as e:
        print(f"Error fetching creators for {platform}: {e}")
        return []

def sanitize_filename(filename):
    """Limpia un nombre de archivo de caracteres no válidos."""
    filename = unquote(filename)
    return re.sub(r'[<>:"/\\|?*]', '_', filename).strip()

def find_cdn_server_for_path(path, previews_list):
    """Encuentra el servidor CDN para un archivo específico en Coomer."""
    for preview in previews_list:
        if preview.get("path", "") == path:
            server = preview.get("server", "")
            if server and "//" in server:
                return server.split("//")[-1].split("/")[0]
    return None

# --- Rutas de la Aplicación ---

@app.route('/')
def index():
    """Página principal de búsqueda."""
    return render_template('index.html')

@app.route('/ping')
def ping():
    """Ruta para el 'keep-alive' de Render."""
    return jsonify({"status": "ok"}), 200

@app.route('/api/search')
def api_search():
    """API interna para buscar creadores de forma asíncrona."""
    platform = request.args.get('platform')
    query = request.args.get('q', '').lower()
    
    if not platform or platform not in API_URLS:
        return jsonify({"error": "Plataforma no válida"}), 400
        
    creators = get_creators(platform)
    if not query:
        # Devuelve los 25 más populares si la búsqueda está vacía
        results = creators[:25]
    else:
        results = [c for c in creators if query in c['name'].lower()][:25] # Limitar a 25 resultados

    return jsonify(results)

@app.route('/<platform>/user/<service>/<creator_id>')
def creator_page(platform, service, creator_id):
    """Página que muestra el contenido de un creador, paginado y filtrado."""
    if platform not in API_URLS:
        abort(404, "Plataforma no encontrada")

    page = request.args.get('page', 1, type=int)
    filter_type = request.args.get('type', 'all') # 'all', 'images', 'videos'

    api_url = API_URLS[platform]
    
    # Obtener info del creador
    creators = get_creators(platform)
    creator_info = next((c for c in creators if c['id'] == creator_id and c['service'] == service), None)
    if not creator_info:
        abort(404, "Creador no encontrado")

    # --- Lógica de paginación eficiente ---
    files_to_display = []
    total_files_found = 0
    offset = 0
    
    # Iteramos sobre las páginas de la API externa hasta tener suficientes archivos para nuestra página
    while len(files_to_display) < ITEMS_PER_PAGE:
        paged_url = f"{api_url}/api/v1/{service}/user/{creator_id}/posts-legacy?o={offset}"
        try:
            response = session.get(paged_url, timeout=15)
            response.raise_for_status()
            data = response.json()
        except (requests.RequestException, ValueError) as e:
            print(f"Error fetching posts from API: {e}")
            break

        posts = data.get("results", [])
        previews = data.get("result_previews", {})
        
        if not posts:
            break # No hay más posts

        for post in posts:
            post_attachments = post.get('attachments', []) + ([post['file']] if post.get('file') else [])

            for att in post_attachments:
                if not att or 'path' not in att or 'name' not in att:
                    continue
                
                # Clasificar archivo
                ext = att['name'].split('.')[-1].lower()
                current_file_type = 'other'
                if ext in ['jpg', 'jpeg', 'png', 'webp', 'gif']:
                    current_file_type = 'images'
                elif ext in ['mp4', 'mkv', 'avi', 'mov', 'webm']:
                    current_file_type = 'videos'

                # Aplicar filtro
                if filter_type != 'all' and filter_type != current_file_type:
                    continue

                total_files_found += 1

                # Omitir archivos que no corresponden a la página actual
                if total_files_found < (page - 1) * ITEMS_PER_PAGE + 1:
                    continue

                # Construir URL(s) del archivo
                path = att['path']
                urls = []
                if platform == 'kemono':
                    urls.append(f"{api_url}/data{path}")
                elif platform == 'coomer':
                    cdn_servers = ["c1", "c2", "c3", "c4", "c5", "c6"] # Servidores CDN comunes de coomer
                    # Intentamos encontrar el servidor específico si es posible
                    specific_server = find_cdn_server_for_path(path, previews.get(post['id'], []))
                    if specific_server:
                        urls.append(f"https://{specific_server}/data{path}")
                    # Añadimos los demás como fallback
                    for s in cdn_servers:
                        fallback_url = f"https://{s}.coomer.su/data{path}"
                        if fallback_url not in urls:
                            urls.append(fallback_url)
                
                files_to_display.append({
                    "name": sanitize_filename(att['name']),
                    "urls": urls,
                    "type": current_file_type,
                    "post_id": post['id'],
                    "post_title": post.get('title', 'Sin título')
                })

                if len(files_to_display) >= ITEMS_PER_PAGE:
                    break # Ya tenemos suficientes archivos para esta página
            
            if len(files_to_display) >= ITEMS_PER_PAGE:
                break
        
        offset += API_PAGE_SIZE

    # Estimación del total de páginas (puede no ser 100% precisa, pero es suficiente)
    # Una mejor aproximación sería contar todos los archivos, pero eso consume mucha memoria.
    # Esta estimación asume una distribución uniforme de archivos filtrados.
    total_pages = ceil(total_files_found / ITEMS_PER_PAGE) if total_files_found else 1


    return render_template(
        'creator.html',
        creator=creator_info,
        platform=platform,
        files=files_to_display,
        current_page=page,
        total_pages=total_pages,
        filter_type=filter_type
    )

if __name__ == '__main__':
    app.run(debug=True)