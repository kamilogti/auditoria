# views.py
from django.urls import reverse

def auditar_cliente(request, cliente_id):
    if request.method == "POST":
        # Definimos los scripts y rutas de archivos según el cliente_id
        rutas_scripts = {
            1: r"C:\Users\csotogu\Desktop\Panel de auditorias\AFPMODELO\Codigo Automation AFPModelo.py",
            2: r"C:\Users\csotogu\Desktop\Panel de auditorias\GETNET\Codigo automation getnet.py"
        }

        script_path = rutas_scripts.get(cliente_id)
        if not script_path:
            return JsonResponse({"message": "Cliente no encontrado o sin script asignado"}, status=404)

        try:
            # Ejecuta el script y captura la salida
            resultado = subprocess.run(
                ["python", script_path],
                check=True, capture_output=True, text=True
            )
            salida = resultado.stdout

            # Genera la URL de la vista de resultado
            redirect_url = reverse('resultado_auditoria', args=[cliente_id])

            # Renderiza la salida y redirige
            return JsonResponse({
                "message": "Auditoría completada correctamente",
                "redirect_url": redirect_url,
                "salida": salida
            })

        except subprocess.CalledProcessError as e:
            return JsonResponse({
                "message": f"Error en la auditoría: {e.stderr}"
            }, status=500)

    return JsonResponse({"message": "Método no permitido"}, status=405)
