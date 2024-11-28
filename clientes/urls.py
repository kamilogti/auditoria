# clientes/urls.py
from django.urls import path
from . import views
from django.contrib import admin

urlpatterns = [
    path('', views.lista_clientes, name='lista_clientes'),  # Página principal de lista de clientes
    path('auditar_cliente/<int:cliente_id>/', views.auditar_cliente, name='auditar_cliente'),  # Auditoría de cliente específico
    path('resultado_auditoria/<int:cliente_id>/', views.resultado_auditoria, name='resultado_auditoria'),  # Resultado de auditoría
    path('clientes/descargar/<str:nombre_archivo>/', views.descargar_archivo, name='descargar_archivo'),  # Descarga específica de cliente
    path('clientes/descargar_auditoria/', views.generar_archivo_auditoria, name='generar_archivo_auditoria'),  # Generar y descargar archivo de auditoría
    path('login/', views.login_view, name='login'),  # Vista de login
    path('logout/', views.logout_view, name='logout'),  # Vista de logout
    path('usuarios/', views.listar_usuarios, name='listar_usuarios'),  # Lista de usuarios
    path('usuarios/crear/', views.crear_usuario, name='crear_usuario'),  # Crear usuario
    path('usuarios/editar/<int:user_id>/', views.editar_usuario, name='editar_usuario'),  # Editar usuario
    path('usuarios/eliminar/<int:user_id>/', views.eliminar_usuario, name='eliminar_usuario'),  # Eliminar usuario
    path('admin_view/', views.admin_view, name='admin_view'),  # Vista de administrador
    path('cargar_archivo/', views.cargar_archivo, name='cargar_archivo'),
    path('iniciar_auditoria/', views.iniciar_auditoria, name='iniciar_auditoria'),
    path('descargar_resultado/', views.descargar_resultado, name='descargar_resultado'),
    path('cargar_archivo_getnet/', views.cargar_archivo_getnet, name='cargar_archivo_getnet'),
    path('iniciar_auditoria_getnet/', views.iniciar_auditoria_getnet, name='iniciar_auditoria_getnet'),
    path('descargar_resultado_getnet/', views.descargar_resultado_getnet, name='descargar_resultado_getnet'),
]