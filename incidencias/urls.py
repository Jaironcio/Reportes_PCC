# incidencias/urls.py (Versión con Selector)

from django.urls import path
from . import views 

urlpatterns = [
    # 0. LANDING PAGE: Página de bienvenida pública con carrusel
    path('', views.vista_landing, name='landing'),
    
    # 1. RUTA DE INICIO (Panel Principal después del login)
    path('panel/', views.vista_selector_centro, name='home'), 
    
    # 2. RUTAS DEL FORMULARIO PCC
    # Ruta para "crear" (apunta a la vista renombrada)
    path('formulario/pcc/', views.vista_formulario_pcc, name='formulario_pcc'),
    # Ruta para "editar" PCC (apunta a la misma vista renombrada)
    path('formulario/pcc/editar/<int:pk>/', views.vista_formulario_pcc, name='editar_incidencia_pcc'), 

    # 3. RUTAS DEL FORMULARIO SANTA JUANA
    path('formulario/santa-juana/', views.vista_formulario_santa_juana, name='formulario_santa_juana'),
    path('formulario/santa-juana/editar/<int:pk>/', views.vista_formulario_santa_juana, name='editar_incidencia_santa_juana'),
    
    # 4. RUTA INTELIGENTE DE EDICIÓN (detecta el centro y redirige)
    path('editar/<int:pk>/', views.vista_editar_incidencia_inteligente, name='editar_incidencia'),
    
    # 5. OTRAS VISTAS (Reporte y Dashboard)
    path('reporte/', views.vista_reporte, name='reporte'),
    path('reporte-santa-juana/', views.vista_reporte_santa_juana, name='reporte_santa_juana'),
    path('dashboard/', views.vista_dashboard, name='dashboard'),
    path('dashboard/profesional/', views.dashboard_profesional, name='dashboard_profesional'),
    
    # 6. CONTROL DIARIO SANTA JUANA
    path('control-diario/santa-juana/', views.vista_control_diario_santa_juana, name='control_diario_santa_juana'),
    
    # 7. REPORTE DE CÁMARAS
    path('reporte-camaras/', views.vista_reporte_camaras, name='reporte_camaras'),
    
    # 8. APIs ()
    path('api/registrar-incidencia/', views.registrar_incidencia_api, name='api-registrar-incidencia'),
    path('api/incidencia/<int:pk>/delete/', views.delete_incidencia_api, name='api-delete-incidencia'),
    path('api/incidencia/<int:pk>/update/', views.update_incidencia_api, name='api-update-incidencia'),
    
    # 9. APIs CONTROL DIARIO
    path('api/control-diario/guardar/', views.guardar_control_diario_api, name='api-guardar-control-diario'),
    path('api/control-diario/obtener/', views.obtener_control_diario_api, name='api-obtener-control-diario'),
    
    # 10. APIs REPORTE DE CÁMARAS
    path('api/reporte-camaras/guardar/', views.guardar_reporte_camaras_api, name='api-guardar-reporte-camaras'),
    path('api/reporte-camaras/obtener/', views.obtener_reporte_camaras_api, name='api-obtener-reporte-camaras'),
    path('api/reporte-camaras/listar/', views.listar_reportes_camaras_api, name='api-listar-reportes-camaras'),
    path('api/reporte-camaras/detalle/<int:pk>/', views.detalle_reporte_camaras_api, name='api-detalle-reporte-camaras'),
    path('api/reporte-camaras/eliminar/<int:pk>/', views.eliminar_reporte_camaras_api, name='api-eliminar-reporte-camaras'),
    
    # 11. CONSULTA DE REPORTES DE CÁMARAS
    path('consulta-reportes-camaras/', views.vista_consulta_reportes_camaras, name='consulta_reportes_camaras'),
    
    # 12. SISTEMA DE MONITOREO DE SENSORES (IDEAL CONTROL)
    path('monitoreo-sensores/', views.vista_monitoreo_sensores, name='monitoreo_sensores'),
    path('consulta-sensores/', views.vista_consulta_sensores, name='consulta_sensores'),
    path('dashboard-sensores/', views.dashboard_sensores, name='dashboard_sensores'),
    path('api/sensores/sistemas/', views.api_obtener_sistemas, name='api_obtener_sistemas'),
    path('api/sensores/sensores/', views.api_obtener_sensores, name='api_obtener_sensores'),
    path('api/sensores/guardar/', views.api_guardar_monitoreo, name='api_guardar_monitoreo'),
    path('api/sensores/reporte/', views.api_obtener_reporte_sensores, name='api_obtener_reporte_sensores'),
    path('api/sensores/listar/', views.api_listar_reportes_sensores, name='api_listar_reportes_sensores'),
    path('api/sensores/detalle/', views.api_detalle_reporte_sensores, name='api_detalle_reporte_sensores'),
    path('api/sensores/eliminar/<int:pk>/', views.api_eliminar_registro_sensor, name='api_eliminar_registro_sensor'),
    path('api/sensores/actualizar/<int:pk>/', views.api_actualizar_registro_sensor, name='api_actualizar_registro_sensor'),
    path('api/sensores/eliminar-reporte/', views.api_eliminar_reporte_completo, name='api_eliminar_reporte_completo'),
    
    # 13. SISTEMA DE REPORTES DE PLATAFORMA (INNOVEX/SINPLANT/IDEAL CONTROL)
    path('reporte-plataformas/', views.vista_reporte_plataformas, name='reporte_plataformas'),
    path('reporte-plataformas/editar/<int:pk>/', views.vista_editar_reporte_plataforma, name='editar_reporte_plataforma'),
    path('consulta-plataformas/', views.vista_consulta_plataformas, name='consulta_plataformas'),
    path('estadisticas-plataformas/', views.vista_estadisticas_plataformas, name='estadisticas_plataformas'),
    path('api/plataformas/guardar/', views.api_guardar_reporte_plataforma, name='api_guardar_reporte_plataforma'),
    path('api/plataformas/eliminar/<int:pk>/', views.api_eliminar_reporte_plataforma, name='api_eliminar_reporte_plataforma'),
    path('api/plataformas/estadisticas/', views.api_estadisticas_plataformas, name='api_estadisticas_plataformas'),
    path('plataformas/pdf/<int:pk>/', views.generar_pdf_plataforma, name='generar_pdf_plataforma'),
    
    # 14. REPORTE GENERAL CONSOLIDADO (PCC + SENSORES)
    path('reporte-general/pdf/', views.generar_reporte_general_pdf, name='generar_reporte_general_pdf'),
    
    # 15. SISTEMA DE CÁLCULO DE PÉRDIDAS ECONÓMICAS (COSTOS SENSORES)
    path('perdidas-economicas/', views.vista_perdidas_economicas, name='perdidas_economicas'),
    path('perdidas-economicas/registrar/', views.vista_registrar_inactividad, name='registrar_inactividad'),
    path('perdidas-economicas/editar/<int:pk>/', views.vista_editar_inactividad, name='editar_inactividad'),
    path('perdidas-economicas/reporte/', views.vista_reporte_perdidas, name='reporte_perdidas'),
    path('api/perdidas/sistemas/', views.api_obtener_sistemas_costos, name='api_obtener_sistemas_costos'),
    path('api/perdidas/guardar/', views.api_guardar_inactividad, name='api_guardar_inactividad'),
    path('api/perdidas/listar/', views.api_listar_inactividades, name='api_listar_inactividades'),
    path('api/perdidas/eliminar/<int:pk>/', views.api_eliminar_inactividad, name='api_eliminar_inactividad'),
    path('api/perdidas/resolver/<int:pk>/', views.api_resolver_inactividad, name='api_resolver_inactividad'),
    path('api/perdidas/estadisticas/', views.api_estadisticas_perdidas, name='api_estadisticas_perdidas'),
    path('perdidas-economicas/pdf/', views.generar_pdf_perdidas, name='generar_pdf_perdidas'),
]