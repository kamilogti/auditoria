import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'panel_auditoria.settings')
django.setup()

from django.contrib.auth.models import User

# Crear usuario de prueba
def crear_usuario():
    print("\n--- Crear Usuario ---")
    username = input("Ingrese el nombre de usuario: ")
    password = input("Ingrese la contraseña: ")
    try:
        User.objects.create_user(username=username, password=password)
        print(f"Usuario '{username}' creado exitosamente.")
    except Exception as e:
        print(f"Error al crear usuario: {e}")

# Editar usuario
def editar_usuario():
    print("\n--- Editar Usuario ---")
    username = input("Ingrese el nombre de usuario a editar: ")
    nuevo_username = input("Ingrese el nuevo nombre de usuario (dejar en blanco si no cambia): ")
    nueva_password = input("Ingrese la nueva contraseña (dejar en blanco si no cambia): ")
    try:
        usuario = User.objects.get(username=username)
        if nuevo_username:
            usuario.username = nuevo_username
        if nueva_password:
            usuario.set_password(nueva_password)
        usuario.save()
        print(f"Usuario '{username}' editado exitosamente.")
    except User.DoesNotExist:
        print(f"Usuario '{username}' no encontrado.")
    except Exception as e:
        print(f"Error al editar usuario: {e}")

# Eliminar usuario
def eliminar_usuario():
    print("\n--- Eliminar Usuario ---")
    username = input("Ingrese el nombre de usuario a eliminar: ")
    try:
        usuario = User.objects.get(username=username)
        usuario.delete()
        print(f"Usuario '{username}' eliminado exitosamente.")
    except User.DoesNotExist:
        print(f"Usuario '{username}' no encontrado.")
    except Exception as e:
        print(f"Error al eliminar usuario: {e}")

# Consultar todos los usuarios
def listar_usuarios():
    print("\n--- Listar Usuarios ---")
    usuarios = User.objects.all()
    if usuarios:
        print("Usuarios creados:")
        for usuario in usuarios:
            print(f"- {usuario.username}")
    else:
        print("No hay usuarios creados.")

# Menú principal
def menu():
    while True:
        print("\nSeleccione una opción:")
        print("1. Crear usuario")
        print("2. Editar usuario")
        print("3. Eliminar usuario")
        print("4. Listar todos los usuarios")
        print("5. Salir")

        opcion = input("Ingrese el número de la opción: ")

        if opcion == '1':
            crear_usuario()
        elif opcion == '2':
            editar_usuario()
        elif opcion == '3':
            eliminar_usuario()
        elif opcion == '4':
            listar_usuarios()
        elif opcion == '5':
            print("Saliendo del programa.")
            break
        else:
            print("Opción no válida, intente de nuevo.")

# Iniciar el menú
menu()
