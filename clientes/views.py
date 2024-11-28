# clientes/views.py
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse, FileResponse, Http404
import pandas as pd
import subprocess
import os
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import render, redirect, get_object_or_404
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from spellchecker import SpellChecker


# Inicializar el corrector ortográfico en español
spell = SpellChecker(language='es')

# Asegúrate de que TEMP_DIR esté definida correctamente
TEMP_DIR = os.path.join(settings.MEDIA_ROOT, 'temp')
os.makedirs(TEMP_DIR, exist_ok=True)


#######################################AFP MODELO##########################################
# Vista para cargar el archivo
@login_required
@csrf_exempt
def cargar_archivo(request):
    if request.method == "POST" and 'file' in request.FILES:
        archivo = request.FILES['file']
        ruta_archivo = default_storage.save(os.path.join(TEMP_DIR, archivo.name), ContentFile(archivo.read()))
        request.session['ruta_archivo'] = ruta_archivo
        return JsonResponse({"message": "Archivo cargado exitosamente."})
    return JsonResponse({"message": "Error al cargar archivo."}, status=400)

# Vista para iniciar la auditoría
@login_required
def iniciar_auditoria(request):
    ruta_archivo = request.session.get('ruta_archivo')
    if not ruta_archivo or not os.path.exists(ruta_archivo):
        return JsonResponse({"message": "Archivo no encontrado."}, status=400)
    
    df = pd.read_excel(ruta_archivo)

    # Verificar columnas
    if 'TIPO_TICKET' in df.columns and 'DESCRIPCION' in df.columns:
        df['Es_SR'] = df['TIPO_TICKET'].apply(lambda x: 'Verdadero' if x == 'SR' else 'Falso')

        def revisar_ortografia(descripcion):
            palabras = descripcion.split()
            palabras_incorrectas = [palabra for palabra in palabras if palabra.lower() not in spell]
            return 'Verdadero' if palabras_incorrectas else 'Falso'

        df['Ortografia_incorrecta'] = df['DESCRIPCION'].apply(revisar_ortografia)

        resultado_path = os.path.join(TEMP_DIR, 'resultado_auditoria.xlsx')
        df.to_excel(resultado_path, index=False)
        request.session['resultado_path'] = resultado_path
        os.remove(ruta_archivo)  # Eliminar archivo original cargado

        return JsonResponse({"message": "Auditoría completada."})
    return JsonResponse({"message": "Columnas requeridas no encontradas."}, status=400)

# Vista para descargar el archivo de resultados
@login_required
def descargar_resultado(request):
    resultado_path = request.session.get('resultado_path')
    if resultado_path and os.path.exists(resultado_path):
        response = FileResponse(open(resultado_path, 'rb'), as_attachment=True, filename='resultado_auditoria.xlsx')
        return response
    raise Http404("Archivo no encontrado.")

################################################################################################

##################################################GETNET#######################################################
@login_required
@csrf_exempt
def cargar_archivo_getnet(request):
    """Carga el archivo único necesario para el cliente GETNET."""
    if request.method == "POST" and 'file' in request.FILES:
        archivo = request.FILES['file']
        ruta_archivo = default_storage.save(os.path.join(TEMP_DIR, archivo.name), ContentFile(archivo.read()))
        request.session['ruta_archivo_getnet'] = ruta_archivo
        return JsonResponse({"message": "Archivo cargado exitosamente para GETNET."})
    return JsonResponse({"message": "Error al cargar archivo para GETNET."}, status=400)

@login_required
def iniciar_auditoria_getnet(request):
    """Inicia la auditoría para el cliente GETNET usando los archivos CSV y el archivo cargado por el usuario."""
    ruta_archivo = request.session.get('ruta_archivo_getnet')
    if not ruta_archivo or not os.path.exists(ruta_archivo):
        return JsonResponse({"message": "Archivo no encontrado para auditoría GETNET."}, status=400)

    # Cargar archivos estáticos
    meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio"]
    df_files = [
        pd.read_csv(
            rf'C:\Users\Kamilo\OneDrive - Sonda S.A\GETNET\Casos Aranda\Creados Mes {month}.csv',
            encoding='Latin-1', sep=';', on_bad_lines='warn'
        ) for month in meses
    ]
    df_unido = pd.concat(df_files, ignore_index=True)

    # Cargar archivo de categorías y grupo solución
    df_csv = pd.read_csv(
        r'C:\Users\Kamilo\OneDrive - Sonda S.A\GETNET\Casos Aranda\Categoría vs Grupo Solución GETNET.csv',
        encoding='latin-1', sep=';'
    )

    # Leer archivo cargado por el usuario
    df_indagacion = pd.read_csv(ruta_archivo, encoding='latin-1', on_bad_lines='skip', sep=';')
    df_derivacion = df_indagacion.copy()

    # Función para verificar la descripción
    def verificar_descripcion(texto):
        oraciones = ["Descripción de solicitud:", "Descripción de la gestión:"]
        return "Bueno" if any(oracion in texto for oracion in oraciones) else "Malo"

    df_indagacion['Indagación'] = df_indagacion['Descripción'].apply(verificar_descripcion)

    # Verificar celdas vacías en `df_unido`
    df_resumen = df_unido[['Número Caso']].copy()
    df_resumen['Resumen'] = df_unido.apply(lambda row: "Malo" if row.isnull().any() else "Bueno", axis=1)

    # Crear diccionario de correcciones para `Grupo Solución`
    correcciones = {}
    for _, row in df_csv.iterrows():
        categoria, grupo_solucion = row['1'], row['2']
        correcciones.setdefault(categoria, set()).add(grupo_solucion)

    # Verificar asignaciones en `df_derivacion`
    df_derivacion['¿Es Correcto el grupo resolutor?'] = df_derivacion.apply(
        lambda row: row['Grupo Solución'] in correcciones.get(row['Categoría'], set()), axis=1
    )

    # Procesamiento de texto con spaCy
    def preprocess_text(text):
        doc = nlp(text)
        return ' '.join(token.lemma_ for token in doc if not token.is_stop and token.is_alpha)

    # Preparación de datos para el modelo
    df_subset = df_unido[['Autor', 'Número Caso', 'Descripción', 'Categoría']].dropna()
    le = LabelEncoder()
    df_subset['Categoría_encoded'] = le.fit_transform(df_subset['Categoría'])
    df_subset['Descripción_procesada'] = df_subset['Descripción'].apply(preprocess_text)

    vectorizer = TfidfVectorizer()
    X = vectorizer.fit_transform(df_subset['Descripción_procesada'])
    X_train, X_test, y_train, y_test = train_test_split(X, df_subset['Categoría_encoded'], test_size=0.2, random_state=42)

    clf = LogisticRegression(max_iter=1000, random_state=42)
    clf.fit(X_train, y_train)

    # Predecir en el archivo de usuario
    df_indagacion['Descripción_procesada'] = df_indagacion['Descripción'].apply(preprocess_text)
    X_new = vectorizer.transform(df_indagacion['Descripción_procesada'])
    y_pred_new = clf.predict(X_new)
    df_indagacion['Categoría Correcta'] = le.inverse_transform(y_pred_new)
    df_indagacion['¿Categoría seleccionada de forma correcta?'] = df_indagacion['Categoría Correcta'] == df_indagacion['Categoría']

    # Concatenar y limpiar DataFrames
    df_combinado = pd.concat([
        df_derivacion[['Número Caso', 'Autor', 'Categoría', 'Grupo Solución', '¿Es Correcto el grupo resolutor?']],
        df_indagacion[['Número Caso', 'Autor', 'Descripción', 'Categoría Correcta', '¿Categoría seleccionada de forma correcta?', 'Indagación']],
        df_resumen[['Resumen']]
    ], axis=1)
    df_combinado = df_combinado.loc[:, ~df_combinado.columns.duplicated()]

    # Guardar resultado como Excel
    resultado_path = os.path.join(TEMP_DIR, 'resultados_combinados_getnet.xlsx')
    df_combinado.to_excel(resultado_path, index=False)
    request.session['resultado_path_getnet'] = resultado_path

    os.remove(ruta_archivo)
    return JsonResponse({"message": "Auditoría GETNET completada."})

@login_required
def descargar_resultado_getnet(request):
    resultado_path = request.session.get('resultado_path_getnet')
    if resultado_path and os.path.exists(resultado_path):
        return FileResponse(open(resultado_path, 'rb'), as_attachment=True, filename='resultados_combinados_getnet.xlsx')
    raise Http404("Archivo no encontrado.")


###########################################################################################################


@login_required
def admin_view(request):
    usuarios = User.objects.all()
    return render(request, 'clientes/admin_view.html', {'usuarios': usuarios})

# Crear usuario
@login_required
def crear_usuario(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        try:
            User.objects.create_user(username=username, password=password)
            messages.success(request, f"Usuario '{username}' creado exitosamente.")
            return redirect('listar_usuarios')
        except Exception as e:
            messages.error(request, f"Error al crear usuario: {e}")
    return render(request, 'clientes/crear_usuario.html')

# Editar usuario
@login_required
def editar_usuario(request, user_id):
    usuario = get_object_or_404(User, pk=user_id)
    if request.method == 'POST':
        nuevo_username = request.POST.get('username')
        nueva_password = request.POST.get('password')
        if nuevo_username:
            usuario.username = nuevo_username
        if nueva_password:
            usuario.set_password(nueva_password)
        usuario.save()
        messages.success(request, f"Usuario '{usuario.username}' editado exitosamente.")
        return redirect('listar_usuarios')
    return render(request, 'clientes/editar_usuario.html', {'usuario': usuario})

# Eliminar usuario
@login_required
def eliminar_usuario(request, user_id):
    usuario = get_object_or_404(User, pk=user_id)
    if request.method == 'POST':
        usuario.delete()
        messages.success(request, f"Usuario '{usuario.username}' eliminado exitosamente.")
        return redirect('listar_usuarios')
    return render(request, 'clientes/eliminar_usuario.html', {'usuario': usuario})

# Listar todos los usuarios
@login_required
def listar_usuarios(request):
    usuarios = User.objects.all()
    return render(request, 'clientes/listar_usuarios.html', {'usuarios': usuarios})
# Vista de login (no protegida)
def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('lista_clientes')  # Redirige a la lista de clientes o página principal
        else:
            messages.error(request, 'Usuario o contraseña incorrectos')
    return render(request, 'clientes/login.html')

# Vista de logout (no protegida)
def logout_view(request):
    logout(request)
    return redirect('login') # Redirige a la página de login después de cerrar sesión

# Vista protegida para mostrar el resultado de la auditoría
@login_required
def resultado_auditoria(request, cliente_id):
    return render(request, 'clientes/resultado_auditoria.html', {'cliente_id': cliente_id})

# Vista protegida para mostrar la lista de clientes
@login_required
def lista_clientes(request):
    return render(request, 'clientes/clientes.html')

# Vista protegida para auditar un cliente específico
@login_required
@csrf_exempt
def auditar_cliente(request, cliente_id):
    if request.method == "POST":
        if 'file' not in request.FILES:
            return JsonResponse({"message": "No se cargó ningún archivo."}, status=400)

        archivo_cargado = request.FILES['file']
        ruta_archivo = os.path.join(settings.MEDIA_ROOT, archivo_cargado.name)

        with open(ruta_archivo, 'wb+') as destination:
            for chunk in archivo_cargado.chunks():
                destination.write(chunk)

        rutas_scripts = {
            1: r"C:\Users\csotogu\Desktop\Panel de auditorias\AFPMODELO\Codigo Automation AFPModelo.py",
            2: r"C:\Users\csotogu\Desktop\Panel de auditorias\GETNET\Codigo automation getnet.py"
        }

        script_path = rutas_scripts.get(cliente_id)
        if not script_path:
            return JsonResponse({"message": "Cliente no encontrado o sin script asignado"}, status=404)

        try:
            resultado = subprocess.run(
                ["python", script_path, ruta_archivo],
                check=True, capture_output=True, text=True
            )
            salida = resultado.stdout
            os.remove(ruta_archivo)

            return JsonResponse({
                "message": f"Auditoría completada: {salida}"
            })

        except subprocess.CalledProcessError as e:
            os.remove(ruta_archivo)
            return JsonResponse({"message": f"Error en la auditoría: {e.stderr}"}, status=500)

    return JsonResponse({"message": "Método no permitido"}, status=405)

# Vista protegida para descargar un archivo específico
@login_required
def descargar_archivo(request, nombre_archivo):
    file_path = os.path.join(r'C:\Users\csotogu\Desktop\Panel de auditorias\panel_auditoria', nombre_archivo)
    if os.path.exists(file_path):
        return FileResponse(open(file_path, 'rb'), as_attachment=True, filename=nombre_archivo)
    else:
        raise Http404("Archivo no encontrado.")

# Vista protegida para generar y descargar un archivo de auditoría
@login_required
def generar_archivo_auditoria(request):
    if request.method == 'POST':
        data = {'Columna1': [1, 2, 3], 'Columna2': ['A', 'B', 'C']}
        df = pd.DataFrame(data)
        
        with io.BytesIO() as buffer:
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            buffer.seek(0)

            response = HttpResponse(buffer, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = 'attachment; filename="resultado_auditoria.xlsx"'
            return response

    return HttpResponse("Método no permitido", status=405)
