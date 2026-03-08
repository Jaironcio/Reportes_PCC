# incidencias/views.py (Versión Revertida a PCC)

from django.shortcuts import render, get_object_or_404, redirect
from .models import Centro, Operario, Incidencia, ReportePlataforma, SensorConfig, MonitoreoSensores
import json
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status 
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required # IMPORTADO

# --- IMPORTACIONES ADICIONALES (Limpias) ---
from django.utils import timezone
from datetime import timedelta, datetime
from django.db.models import Count, Q, Avg # Quitamos 'F' que no se usa aquí
from django.db.models.functions import TruncDate, TruncMonth 
from .serializers import IncidenciaSerializer
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger 
import pytz

# --- IMPORTACIONES PARA PDF ---
from django.http import HttpResponse, JsonResponse
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from io import BytesIO
from django.views.decorators.http import require_http_methods
# ---

# DATOS FIJOS DE MÓDULOS (Original)
DATOS_MODULOS_ESTANQUES = {
    "trafun": {
        "Módulo 400": ["401", "402", "403", "404", "405", "406", "407", "408", "409", "410"],
        "Módulo 300": ["301", "302", "303", "304", "305", "306", "307", "308", "309", "310", "311", "312"],
        "Módulo 200": ["201", "202", "203", "204", "205", "206", "207", "208", "209", "210", "211", "212"],
        "Alevinaje B": ["116", "117", "118", "119", "120", "121", "122", "123", "124", "125", "126", "127", "128", "129", "130"],
        "Alevinaje A": ["101", "102", "103", "104", "105", "106", "107", "108", "109", "110", "111", "112", "113", "114", "115"]
    },
    "liquine": {
        "Módulo 100": ["101", "102", "103", "104", "105", "106", "107", "108", "109", "110", "111", "112", "113", "114", "115", "116", "117", "118", "119", "120", "121", "122", "123", "124", "125", "126", "127", "128", "129", "130", "131", "132", "133", "134", "135", "136", "137", "138", "139", "140"],
        "Módulo 200": ["201", "202", "203", "204", "205", "206", "207"],
        "Módulo 300": ["301", "302", "303", "304", "305", "306", "307", "308", "309", "310", "311", "312", "313"],
        "Módulo 400": ["401", "402", "403", "404", "405", "406", "407", "408", "409"],
        "Módulo 500": ["501", "502", "503", "504", "505", "506", "507", "508"],
        "Alevinaje": ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13"]
    },
    "cipreses": {
        "Módulo 100": ["101", "102", "103", "104", "105", "106", "107", "108", "109", "110", "111", "112", "113", "114", "115", "116"],
        "Módulo 200": ["201", "202", "203", "204", "205", "206", "207", "208", "209", "210"],
        "Módulo 300": ["301", "302", "303", "304", "305", "306", "307", "308", "309", "310", "311", "312", "313", "314", "315", "316"],
        "Módulo 400": ["401", "402", "403", "404", "405", "406", "407", "408", "409", "410", "411", "412", "413", "414", "415"]
    },
    "santa_juana": {
        "Smolt 1": ["Estanque 1", "Estanque 2", "Estanque 3", "Estanque 4", "Estanque 5"],
        "Smolt 2": ["Estanque 6", "Estanque 7", "Estanque 8", "Estanque 9", "Estanque 10"],
        "Fry 1": ["Estanque A", "Estanque B", "Estanque C"],
        "Hatchery": ["Incubadora 1", "Incubadora 2", "Incubadora 3"],
    },
    "rahue": {}, "esperanza": {}, "hueyusca": {}, "pcc": {}
}

# --- VISTA 0: LANDING PAGE (PÁGINA DE BIENVENIDA PÚBLICA) ---
def vista_landing(request):
    """
    Página de bienvenida pública con carrusel de imágenes.
    Si el usuario ya está autenticado, redirige al panel principal.
    """
    if request.user.is_authenticated:
        return redirect('home')
    return render(request, 'landing.html')


# --- VISTA 1: EL SELECTOR DE CENTROS (NUEVA PÁGINA DE INICIO) ---
@login_required
def vista_selector_centro(request):
    """
    Renderiza el panel principal con menú lateral profesional.
    Si el usuario NO es admin (staff), lo redirige directo al dashboard.
    """
    if not request.user.is_staff:
        return redirect('dashboard')
        
    return render(request, 'panel_principal.html')


# --- VISTA INTELIGENTE: Redirige al formulario correcto según el centro ---
@login_required
def vista_editar_incidencia_inteligente(request, pk):
    """
    Detecta si la incidencia es de Santa Juana o PCC y redirige al formulario correcto.
    """
    # Proteccion para visualizadores
    if not request.user.is_staff:
        return redirect('dashboard')

    incidencia = get_object_or_404(Incidencia, pk=pk)
    
    # Si el centro es Santa Juana, redirige a su formulario
    if incidencia.centro and incidencia.centro.slug == 'santa-juana':
        return redirect('editar_incidencia_santa_juana', pk=pk)
    else:
        # Si es otro centro, va al formulario PCC
        return redirect('editar_incidencia_pcc', pk=pk)


# --- VISTA 2: FORMULARIO SANTA JUANA (FUNCIONAL) ---
@login_required
def vista_formulario_santa_juana(request, pk=None):
    """
    Renderiza el formulario exclusivo de Santa Juana.
    """
    # Proteccion para visualizadores
    if not request.user.is_staff:
        return redirect('dashboard')

    incidencia_a_editar = None
    incidencia_json = 'null'
    
    # 1. Lógica para EDITAR (serializar datos completos de la incidencia)
    if pk:
        incidencia_a_editar = get_object_or_404(Incidencia, pk=pk)
        incidencia_json = json.dumps({
            'pk': incidencia_a_editar.pk,
            'fecha_hora': incidencia_a_editar.fecha_hora.isoformat() if incidencia_a_editar.fecha_hora else None,
            'turno': incidencia_a_editar.turno,
            'centro_id': incidencia_a_editar.centro_id,
            'modulo': incidencia_a_editar.modulo,
            'estanque': incidencia_a_editar.estanque,
            'tipo_incidencia': incidencia_a_editar.tipo_incidencia,
            'tipo_incidencia_normalizada': incidencia_a_editar.tipo_incidencia_normalizada,
            'tiempo_resolucion': incidencia_a_editar.tiempo_resolucion,
            'riesgo_peces': incidencia_a_editar.riesgo_peces,
            'perdida_economica': incidencia_a_editar.perdida_economica,
            'riesgo_personas': incidencia_a_editar.riesgo_personas,
            'observacion': incidencia_a_editar.observacion,
            'operario_contacto_id': incidencia_a_editar.operario_contacto_id,
        })

    # 2. Obtener Centros y Operarios (igual que en PCC)
    todos_los_centros = Centro.objects.all().order_by('nombre')
    
    # Convertimos el QuerySet de Centros a una lista simple de diccionarios (JSON)
    centros_list = list(todos_los_centros.values('id', 'nombre'))
    centros_json = json.dumps(centros_list)
    
    # --- NUEVA CORRECCIÓN (para el error de "Centro no encontrado") ---
    # Necesitamos encontrar el slug del centro actual para pasarlo al JS
    centro_sj = todos_los_centros.filter(slug='santa-juana').first()
    
    operarios_por_centro = {}
    operarios = Operario.objects.select_related('centro').all()
    for op in operarios:
        centro_id = op.centro.id
        if centro_id not in operarios_por_centro:
            operarios_por_centro[centro_id] = []
        operarios_por_centro[centro_id].append({
            'id': op.id,
            'nombre': op.nombre,
            'cargo': op.cargo,
            'telefono': op.telefono
        })

    # --- CORRECCIÓN FINAL DEL CONTEXTO ---
    contexto = {
        'centros_json': centros_json, # Para el JS que usaba 'CENTROS' (ya no se usa pero es bueno tenerlo)
        'datos_modulos_json': json.dumps(DATOS_MODULOS_ESTANQUES),
        'datos_operarios_json': json.dumps(operarios_por_centro),
        'incidencia_a_editar': incidencia_a_editar,
        'incidencia_a_editar_json': incidencia_json,
        
        # --- ESTAS SON LAS 2 LÍNEAS QUE FALTABAN ---
        'centros': todos_los_centros,  # Para el bucle {% for %} en <script id="centros-data">
        'centro_actual_slug': centro_sj.slug if centro_sj else '', # Para el data-centro-slug
        'es_admin': request.user.is_staff
    }
    
    # Renderiza el nuevo template de Santa Juana
    return render(request, 'formulario_santa_juana.html', contexto)

# --- VISTA 1: EL FORMULARIO (Nombre original 'vista_formulario') ---
@login_required
def vista_formulario_pcc(request, pk=None): 
    
    # Proteccion para visualizadores
    if not request.user.is_staff:
        return redirect('dashboard')

    incidencia_a_editar = None
    incidencia_json = 'null'

    if pk:
        incidencia_a_editar = get_object_or_404(Incidencia, pk=pk)
        incidencia_json = json.dumps({
            'pk': incidencia_a_editar.pk,
            'fecha_hora': incidencia_a_editar.fecha_hora.isoformat() if incidencia_a_editar.fecha_hora else None,
            'turno': incidencia_a_editar.turno,
            'centro_id': incidencia_a_editar.centro_id,
            'tipo_incidencia': incidencia_a_editar.tipo_incidencia,
            'modulo': incidencia_a_editar.modulo,
            'estanque': incidencia_a_editar.estanque,
            'parametros_afectados': incidencia_a_editar.parametros_afectados.split(',') if incidencia_a_editar.parametros_afectados else [],
            'oxigeno_nivel': incidencia_a_editar.oxigeno_nivel,
            'oxigeno_valor': incidencia_a_editar.oxigeno_valor,
            'temperatura_nivel': incidencia_a_editar.temperatura_nivel,
            'temperatura_valor': incidencia_a_editar.temperatura_valor,
            'conductividad_nivel': incidencia_a_editar.conductividad_nivel,
            'turbidez_nivel': incidencia_a_editar.turbidez_nivel,
            'turbidez_valor': incidencia_a_editar.turbidez_valor,
            'sistema_sensor': incidencia_a_editar.sistema_sensor,
            'sensor_detectado': incidencia_a_editar.sensor_detectado,
            'sensor_nivel': incidencia_a_editar.sensor_nivel,
            'sensor_valor': incidencia_a_editar.sensor_valor,
            'tiempo_resolucion': incidencia_a_editar.tiempo_resolucion,
            'riesgo_peces': incidencia_a_editar.riesgo_peces,
            'perdida_economica': incidencia_a_editar.perdida_economica,
            'riesgo_personas': incidencia_a_editar.riesgo_personas,
            'observacion': incidencia_a_editar.observacion,
            'operario_contacto_id': incidencia_a_editar.operario_contacto_id,
            'tipo_incidencia_normalizada': incidencia_a_editar.tipo_incidencia_normalizada,
        })
    
    # Solo centros PCC: trafun, cipreses, liquine
    # (filtramos por id/slug para evitar problemas de encoding con tildes)
    todos_los_centros = Centro.objects.filter(id__in=['trafun', 'cipreses', 'liquine']).order_by('nombre')
    operarios_por_centro = {}
    operarios = Operario.objects.select_related('centro').all()
    for op in operarios:
        centro_id = op.centro.id
        if centro_id not in operarios_por_centro:
            operarios_por_centro[centro_id] = []
        operarios_por_centro[centro_id].append({
            'id': op.id,
            'nombre': op.nombre,
            'cargo': op.cargo,
            'telefono': op.telefono
        })

    contexto = {
        'centros': todos_los_centros,
        'datos_modulos_json': json.dumps(DATOS_MODULOS_ESTANQUES),
        'datos_operarios_json': json.dumps(operarios_por_centro),
        'incidencia_a_editar': incidencia_a_editar,
        'incidencia_a_editar_json': incidencia_json,
        'es_admin': request.user.is_staff
    }
    
    # Renderiza el formulario original
    return render(request, 'formulario.html', contexto)


# --- VISTA 2: LA PÁGINA DE REPORTES (Original) ---
@login_required
def vista_reporte(request):
    
    # Determinar el contexto del formulario (de dónde viene el usuario)
    formulario_contexto = request.GET.get('formulario', None)
    
    # Filtrar centros según el contexto
    if formulario_contexto == 'pcc':
        # PCC solo muestra: trafun, liquine, cipreses
        centros_permitidos = Centro.objects.filter(id__in=['trafun', 'liquine', 'cipreses'])
        lista_de_incidencias = Incidencia.objects.select_related(
            'centro', 'operario_contacto'
        ).filter(centro_id__in=['trafun', 'liquine', 'cipreses']).order_by('-fecha_hora')
    elif formulario_contexto == 'santa_juana':
        # Santa Juana solo muestra: Santa Juana
        centros_permitidos = Centro.objects.filter(nombre='Santa Juana')
        lista_de_incidencias = Incidencia.objects.select_related(
            'centro', 'operario_contacto'
        ).filter(centro__nombre='Santa Juana').order_by('-fecha_hora')
    else:
        # Vista general - muestra todos
        centros_permitidos = Centro.objects.all()
        lista_de_incidencias = Incidencia.objects.select_related(
            'centro', 'operario_contacto'
        ).all().order_by('-fecha_hora')
    
    filtro_fecha = request.GET.get('fecha', None)
    filtro_turno = request.GET.get('turno', None)
    filtro_centro = request.GET.get('centro', None)
    filtro_tipo = request.GET.get('tipo', None)

    if filtro_fecha:
        from datetime import datetime as dt
        from django.utils import timezone
        try:
            fecha_obj = dt.strptime(filtro_fecha, '%Y-%m-%d')
            # Crear fechas con timezone para compatibilidad con USE_TZ=True
            fecha_inicio = timezone.make_aware(fecha_obj.replace(hour=0, minute=0, second=0))
            fecha_fin = timezone.make_aware(fecha_obj.replace(hour=23, minute=59, second=59))
            lista_de_incidencias = lista_de_incidencias.filter(
                fecha_hora__gte=fecha_inicio,
                fecha_hora__lte=fecha_fin
            )
        except Exception:
            pass  # Invalid date format or timezone error, skip filter
    if filtro_turno:
        lista_de_incidencias = lista_de_incidencias.filter(turno=filtro_turno)
    if filtro_centro:
        lista_de_incidencias = lista_de_incidencias.filter(centro_id=filtro_centro)
    if filtro_tipo:
        lista_de_incidencias = lista_de_incidencias.filter(tipo_incidencia=filtro_tipo)

    todos_los_centros = centros_permitidos.order_by('nombre')
    
    # Paginación: 15 incidencias por página
    paginator = Paginator(lista_de_incidencias, 15)
    page = request.GET.get('page', 1)
    
    try:
        incidencias_paginadas = paginator.page(page)
    except PageNotAnInteger:
        incidencias_paginadas = paginator.page(1)
    except EmptyPage:
        incidencias_paginadas = paginator.page(paginator.num_pages)
    
    centro_actual_slug = None
    if filtro_centro:
        centro_obj = Centro.objects.filter(id=filtro_centro).first()
        if centro_obj:
            centro_actual_slug = centro_obj.slug
    
    contexto = {
        'incidencias': incidencias_paginadas,
        'centros': todos_los_centros,
        'filtros_aplicados': request.GET,
        'es_admin': request.user.is_staff,
        'total_incidencias': paginator.count,
        'centro_actual': centro_actual_slug,
    }
    
    return render(request, 'reporte.html', contexto)


# --- VISTA: REPORTE SANTA JUANA (Separado del PCC) ---
@login_required
def vista_reporte_santa_juana(request):
    """Vista de reportes exclusiva para el centro Santa Juana"""
    from datetime import datetime as dt
    
    # Solo incidencias de Santa Juana
    lista_de_incidencias = Incidencia.objects.select_related(
        'centro', 'operario_contacto'
    ).filter(centro__nombre='Santa Juana').order_by('-fecha_hora')
    
    filtro_fecha = request.GET.get('fecha', None)
    filtro_turno = request.GET.get('turno', None)
    filtro_tipo = request.GET.get('tipo', None)

    if filtro_fecha:
        try:
            fecha_obj = dt.strptime(filtro_fecha, '%Y-%m-%d')
            fecha_inicio = timezone.make_aware(fecha_obj.replace(hour=0, minute=0, second=0))
            fecha_fin = timezone.make_aware(fecha_obj.replace(hour=23, minute=59, second=59))
            lista_de_incidencias = lista_de_incidencias.filter(
                fecha_hora__gte=fecha_inicio,
                fecha_hora__lte=fecha_fin
            )
        except Exception:
            pass
    if filtro_turno:
        lista_de_incidencias = lista_de_incidencias.filter(turno=filtro_turno)
    if filtro_tipo:
        lista_de_incidencias = lista_de_incidencias.filter(tipo_incidencia=filtro_tipo)
    
    # Paginación: 15 incidencias por página
    paginator = Paginator(lista_de_incidencias, 15)
    page = request.GET.get('page', 1)
    
    try:
        incidencias_paginadas = paginator.page(page)
    except PageNotAnInteger:
        incidencias_paginadas = paginator.page(1)
    except EmptyPage:
        incidencias_paginadas = paginator.page(paginator.num_pages)
    
    contexto = {
        'incidencias': incidencias_paginadas,
        'filtros_aplicados': request.GET,
        'es_admin': request.user.is_staff,
        'total_incidencias': paginator.count,
        'active_menu': 'reporte_santa_juana',
    }
    
    return render(request, 'reporte_santa_juana.html', contexto)


# --- VISTA 3: DASHBOARD (Original) ---
@login_required
def vista_dashboard(request):
    
    periodo_filtro = request.GET.get('periodo', 'all')
    centro_filtro = request.GET.get('centro', None)
    formulario_contexto = request.GET.get('formulario', None)

    # Filtrar por contexto del formulario
    if formulario_contexto == 'pcc':
        # PCC: solo Trafún, Liquiñe, Cipreses
        base_query = Incidencia.objects.filter(centro__nombre__in=['Trafún', 'Liquiñe', 'Cipreses'])
    elif formulario_contexto == 'santa_juana':
        # Santa Juana: solo Santa Juana
        base_query = Incidencia.objects.filter(centro__nombre='Santa Juana')
    else:
        # Vista general
        base_query = Incidencia.objects.all()
    
    fecha_limite = None
    if periodo_filtro == 'week':
        fecha_limite = timezone.now() - timedelta(days=7)
    elif periodo_filtro == 'month':
        fecha_limite = timezone.now() - timedelta(days=30)
    elif periodo_filtro == 'quarter':
        fecha_limite = timezone.now() - timedelta(days=90)
    
    if fecha_limite:
        base_query = base_query.filter(fecha_hora__gte=fecha_limite)
    if centro_filtro:
        base_query = base_query.filter(centro_id=centro_filtro)

    total_incidencias = base_query.count()
    alto_riesgo_count = base_query.filter(Q(riesgo_peces=True) | Q(riesgo_personas=True)).count()
    promedio_dict = base_query.filter(tiempo_resolucion__isnull=False).aggregate(avg_tiempo=Avg('tiempo_resolucion'))
    promedio_resolucion = int(promedio_dict['avg_tiempo']) if promedio_dict['avg_tiempo'] else 0

    chart_centro_query = base_query.filter(centro__isnull=False) \
        .values('centro__nombre') \
        .annotate(count=Count('id')) \
        .order_by('-count')
    chart_centro_labels = [item['centro__nombre'] for item in chart_centro_query]
    chart_centro_counts = [item['count'] for item in chart_centro_query]
    centro_mas_incidencias = chart_centro_labels[0] if chart_centro_labels else "-"

    chart_tendencia_query = base_query \
        .annotate(dia=TruncDate('fecha_hora')) \
        .values('dia') \
        .annotate(count=Count('id')) \
        .order_by('dia')
    chart_tendencia_labels = []
    chart_tendencia_data = []
    for item in chart_tendencia_query:
        try:
            if item['dia']:
                chart_tendencia_labels.append(item['dia'].strftime('%Y-%m-%d'))
                chart_tendencia_data.append(item['count'])
        except:
            pass

    modulos_count = base_query.filter(tipo_incidencia='modulos').count()
    sensores_count = base_query.filter(tipo_incidencia='sensores').count()
    chart_tipos_data = [modulos_count, sensores_count]
    
    chart_operario_query = base_query.filter(operario_contacto__isnull=False) \
        .values('operario_contacto__nombre') \
        .annotate(count=Count('id')) \
        .order_by('-count')[:7]
    chart_operario_labels = [item['operario_contacto__nombre'] for item in chart_operario_query]
    chart_operario_data = [item['count'] for item in chart_operario_query]

    chart_clasificacion_query = base_query.filter(tipo_incidencia_normalizada__isnull=False) \
        .exclude(tipo_incidencia_normalizada='') \
        .values('tipo_incidencia_normalizada') \
        .annotate(count=Count('id')) \
        .order_by('-count')
    chart_clasificacion_labels = [item['tipo_incidencia_normalizada'] for item in chart_clasificacion_query]
    chart_clasificacion_data = [item['count'] for item in chart_clasificacion_query]

    # --- NUEVO: Agrupación por Categoría Mayor ---
    mapping_categorias = {
        'Manejo Operacional': [
            'Estanque en Tratamiento', 
            'Estanque en Manejo', 
            'Estanque con traslado de peces',
            'Estanque en Flashing',
            'Estanque en Vacunación',
            'Desdoble de estanque',
            'Recambio de agua',
            'Estanque vacío',
            'Estanque en selección',
            'Estanque en ayuna'
        ],
        'Problemas de Sensores': [
            'Manipulando sensor',
            'Falla sensor CO2', 
            'Falla sensor T°', 
            'Falla sensor pH',
            'Problemas con la TEMPERATURA'
        ],
        'Problemas Eléctricos / Conectividad': [
            'Corte de energía',
            'Corte de luz',
            'Falla en plataforma de monitoreo',
            'Problemas con la plataforma',
            'Sin señal o conectividad'
        ],
        'Problemas Operacionales Específicos': [
            'Problemas con el cono de oxigenación'
        ],
        'Parámetros Fuera de Rango': [
            'Temperatura baja', 
            'Temperatura alta', 
            'CO2 alto', 
            'CO2 bajo'
        ],
        'Problemas de Comunicación': [
            'Sin respuesta del centro',
            'Llamada no contestada', 
            'Celular centro apagado'
        ]
    }
    
    # Inicializar contadores
    conteo_categorias = {
        'Manejo Operacional': 0,
        'Problemas de Sensores': 0,
        'Problemas Eléctricos / Conectividad': 0,
        'Problemas Operacionales Específicos': 0,
        'Parámetros Fuera de Rango': 0,
        'Problemas de Comunicación': 0
    }

    # Clasificar "al vuelo"
    todos_los_tipos = base_query.values_list('tipo_incidencia_normalizada', flat=True)
    
    for tipo_texto in todos_los_tipos:
        if not tipo_texto: continue
        for categoria, lista_tipos in mapping_categorias.items():
            if tipo_texto in lista_tipos:
                conteo_categorias[categoria] += 1
                break
            
    # Preparar arrays para el gráfico
    chart_categorias_labels = list(conteo_categorias.keys())
    chart_categorias_data = list(conteo_categorias.values())
    # ---------------------------------------------

    # Filtrar centros disponibles - SOLO Trafún, Cipreses, Liquiñe
    centros_disponibles = Centro.objects.filter(nombre__in=['Trafún', 'Liquiñe', 'Cipreses'])
    
    # Calcular KPIs por centro, separados por turno
    # Cada turno tiene su propia meta de cumplimiento (configurable)
    turnos_config = {
        'Día':   {'meta': 80, 'icono': 'sun', 'color': '#f39c12'},
        'Tarde': {'meta': 80, 'icono': 'cloud-sun', 'color': '#e67e22'},
        'Noche': {'meta': 80, 'icono': 'moon', 'color': '#2c3e50'},
    }
    
    # Tiempo KPI por centro+turno (minutos). Default: 20 min
    kpi_tiempo_especial = {
        ('Trafún', 'Día'): 35,
    }
    kpi_tiempo_default = 20
    
    # Pesos del KPI compuesto
    peso_tiempo = 0.8
    peso_volumen = 0.2
    
    kpi_por_turno = {}
    for turno, config in turnos_config.items():
        # Paso 1: Calcular totales por centro en este turno
        datos_brutos = []
        for c in centros_disponibles:
            tiempo_kpi = kpi_tiempo_especial.get((c.nombre, turno), kpi_tiempo_default)
            total_c = base_query.filter(centro=c, turno=turno).count()
            en_kpi = base_query.filter(centro=c, turno=turno, tiempo_resolucion__lte=tiempo_kpi).count()
            if total_c > 0:
                pct_tiempo = int((en_kpi / total_c) * 100)
            else:
                pct_tiempo = 100
            datos_brutos.append({
                'centro': c,
                'total': total_c,
                'en_kpi': en_kpi,
                'pct_tiempo': pct_tiempo,
                'tiempo_kpi': tiempo_kpi,
            })
        
        # Paso 2: Calcular promedio de incidencias del turno para el % volumen
        totales = [d['total'] for d in datos_brutos]
        promedio_turno = sum(totales) / len(totales) if totales else 1
        max_turno = max(totales) if totales else 1
        if max_turno == 0:
            max_turno = 1
        
        # Paso 3: Calcular % volumen y KPI compuesto con pesos dinámicos
        kpi_turno_lista = []
        for d in datos_brutos:
            # % Volumen: 100% si tiene 0 incidencias, baja con curva suave
            # Raíz cuadrada suaviza la caída: el centro con más no cae a 0%
            ratio_vol = d['total'] / max_turno  # 0 a 1
            pct_volumen = max(15, int(100 - (ratio_vol ** 0.5) * 85))
            
            # Pesos dinámicos suavizados según volumen relativo
            # Rango comprimido: ratio va de 0.3 a 1.0 para evitar extremos
            ratio_bruto = d['total'] / max_turno  # 0 a 1
            ratio = 0.3 + 0.7 * ratio_bruto       # 0.3 a 1.0
            peso_t = peso_tiempo * ratio
            peso_v = 1 - peso_t
            
            # KPI Compuesto
            kpi_compuesto = int(d['pct_tiempo'] * peso_t + pct_volumen * peso_v)
            
            kpi_turno_lista.append({
                'centro_nombre': d['centro'].nombre,
                'total_incidencias': d['total'],
                'en_kpi': d['en_kpi'],
                'pct_tiempo': d['pct_tiempo'],
                'pct_volumen': pct_volumen,
                'kpi_compuesto': kpi_compuesto,
                'cumple_meta': kpi_compuesto >= config['meta'],
                'tiempo_kpi': d['tiempo_kpi'],
            })
        
        kpi_por_turno[turno] = {
            'data': kpi_turno_lista,
            'meta': config['meta'],
            'icono': config['icono'],
            'color': config['color'],
        }

    # --- TOP INCIDENCIAS BAJAS DE OXÍGENO (Semáforo) ---
    o2_bajas_query = base_query.filter(oxigeno_nivel='baja').exclude(oxigeno_valor='')
    top_o2_bajas = []
    conteo_semaforo = {'rojo': 0, 'amarillo': 0, 'verde': 0}
    
    for inc in o2_bajas_query.select_related('centro', 'operario_contacto'):
        try:
            valor = float(inc.oxigeno_valor.replace(',', '.'))
        except (ValueError, TypeError):
            continue
        
        if valor >= 2 and valor <= 4:
            color = 'rojo'
            conteo_semaforo['rojo'] += 1
        elif valor >= 5 and valor <= 6:
            color = 'amarillo'
            conteo_semaforo['amarillo'] += 1
        elif valor > 6:
            color = 'verde'
            conteo_semaforo['verde'] += 1
        else:
            color = 'rojo'
            conteo_semaforo['rojo'] += 1
        
        top_o2_bajas.append({
            'centro': inc.centro.nombre if inc.centro else '-',
            'modulo': inc.modulo,
            'estanque': inc.estanque,
            'valor': valor,
            'color': color,
            'fecha': inc.fecha_hora.strftime('%d/%m/%Y %H:%M') if inc.fecha_hora else '-',
            'turno': inc.turno,
            'operario': inc.operario_contacto.nombre if inc.operario_contacto else 'Operario Turno Noche',
            'tipo_incidencia': inc.tipo_incidencia_normalizada if inc.tipo_incidencia_normalizada else '-',
        })
    
    # Ordenar por valor ascendente (los más críticos primero)
    top_o2_bajas.sort(key=lambda x: x['valor'])

    contexto = {
        'total_incidencias': total_incidencias,
        'alto_riesgo_count': alto_riesgo_count,
        'promedio_resolucion': promedio_resolucion,
        'centro_mas_incidencias': centro_mas_incidencias,
        
        'chart_centro_labels_json': json.dumps(chart_centro_labels),
        'chart_centro_counts_json': json.dumps(chart_centro_counts),
        
        'chart_tendencia_labels_json': json.dumps(chart_tendencia_labels),
        'chart_tendencia_data_json': json.dumps(chart_tendencia_data),
        
        'chart_tipos_data_json': json.dumps(chart_tipos_data),
        
        'chart_operario_labels_json': json.dumps(chart_operario_labels),
        'chart_operario_data_json': json.dumps(chart_operario_data),

        'chart_clasificacion_labels_json': json.dumps(chart_clasificacion_labels),
        'chart_clasificacion_data_json': json.dumps(chart_clasificacion_data),
        
        # NUEVO: Gráfico por Categorías
        'chart_categorias_labels_json': json.dumps(chart_categorias_labels),
        'chart_categorias_data_json': json.dumps(chart_categorias_data),
        
        'kpi_por_turno': kpi_por_turno,
        'centros': centros_disponibles.order_by('nombre'),
        'filtros_aplicados': request.GET,
        'es_admin': request.user.is_staff,
        
        # TOP Incidencias Bajas O2 (Semáforo)
        'top_o2_bajas': top_o2_bajas,
        'conteo_semaforo': conteo_semaforo,
    }
    
    return render(request, 'dashboard.html', contexto)


# --- APIs (Originales) ---

@csrf_exempt
@api_view(['POST'])
def registrar_incidencia_api(request):
    if request.method == 'POST':
        serializer = IncidenciaSerializer(data=request.data) 
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        print(serializer.errors)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)


@csrf_exempt
@api_view(['PUT'])
def update_incidencia_api(request, pk):
    try:
        incidencia = Incidencia.objects.get(pk=pk)
    except Incidencia.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == 'PUT':
        serializer = IncidenciaSerializer(incidencia, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        print(serializer.errors) 
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)


@csrf_exempt
@api_view(['DELETE'])
def delete_incidencia_api(request, pk):
    
    incidencia = get_object_or_404(Incidencia, pk=pk)
    
    if request.method == 'DELETE':
        incidencia.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)


# --- VISTAS PARA CONTROL DIARIO ---
@login_required
def vista_control_diario_santa_juana(request):
    """
    Vista principal para el Control Diario de parámetros (Temp, pH, Oxígeno)
    Versión simplificada sin consultas a la BD
    """
    if not request.user.is_staff:
        return redirect('dashboard')
    
    from datetime import date
    
    # Buscar centro Santa Juana (si no existe, crear uno temporal)
    centro_sj = Centro.objects.filter(slug='santa-juana').first()
    
    if not centro_sj:
        # Crear un objeto temporal para evitar errores
        class CentroTemp:
            id = 'santa-juana'
            nombre = 'Santa Juana'
            slug = 'santa-juana'
        centro_sj = CentroTemp()
    
    fecha_actual = date.today()
    
    contexto = {
        'centro': centro_sj,
        'fecha_actual': fecha_actual,
        'anio_actual': fecha_actual.year,
        'es_admin': request.user.is_staff
    }
    
    return render(request, 'control_diario_santa_juana.html', contexto)


@csrf_exempt
@api_view(['POST'])
def guardar_control_diario_api(request):
    """
    API para guardar o actualizar un registro de Control Diario
    Versión que verifica si la tabla existe antes de intentar guardar
    """
    from datetime import datetime
    
    if request.method == 'POST':
        data = request.data
        
        try:
            # Intentar importar el modelo
            try:
                from .models import ControlDiario
            except ImportError:
                return Response({
                    'success': False,
                    'message': 'El modelo ControlDiario no está disponible. Por favor, ejecuta las migraciones.'
                }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            
            # Verificar si la tabla existe
            from django.db import connection
            table_name = 'cermaq_incidencias_incidencias_controldiario'
            
            with connection.cursor() as cursor:
                cursor.execute(f"SHOW TABLES LIKE '{table_name}'")
                if not cursor.fetchone():
                    return Response({
                        'success': False,
                        'message': 'La tabla de Control Diario no existe. Por favor, ejecuta el script SQL: crear_tabla_control_diario.sql'
                    }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            
            centro = Centro.objects.get(id=data.get('centro_id'))
            fecha = datetime.strptime(data.get('fecha'), '%Y-%m-%d').date()
            modulo = data.get('modulo', 'Hatchery')
            
            control, created = ControlDiario.objects.get_or_create(
                centro=centro,
                fecha=fecha,
                modulo=modulo,
                defaults={
                    'anio': data.get('anio'),
                    'semana': data.get('semana'),
                    'dia': data.get('dia'),
                    'responsable': data.get('responsable', ''),
                }
            )
            
            if not created:
                control.anio = data.get('anio')
                control.semana = data.get('semana')
                control.dia = data.get('dia')
                control.responsable = data.get('responsable', '')
            
            for hora in ['00', '04', '08', '12', '16', '20']:
                for param in ['temp', 'ph', 'oxigeno']:
                    field_name = f'hora_{hora}_{param}'
                    value = data.get(field_name)
                    if value:
                        setattr(control, field_name, float(value))
            
            control.save()
            
            return Response({
                'success': True,
                'message': 'Control diario guardado exitosamente',
                'id': control.id,
                'promedio_temp': str(control.promedio_temp) if control.promedio_temp else None,
                'promedio_ph': str(control.promedio_ph) if control.promedio_ph else None,
                'promedio_oxigeno': str(control.promedio_oxigeno) if control.promedio_oxigeno else None,
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({
                'success': False,
                'message': f'Error al guardar: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)


@csrf_exempt
@api_view(['GET'])
def obtener_control_diario_api(request):
    """
    API para obtener un registro de Control Diario por fecha
    Versión que verifica si la tabla existe antes de consultar
    """
    from datetime import datetime
    
    fecha_str = request.GET.get('fecha')
    centro_id = request.GET.get('centro_id')
    modulo = request.GET.get('modulo', 'Hatchery')
    
    if not fecha_str or not centro_id:
        return Response({'error': 'Faltan parámetros'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Intentar importar el modelo
        try:
            from .models import ControlDiario
        except ImportError:
            return Response({
                'error': 'El modelo ControlDiario no está disponible'
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        # Verificar si la tabla existe
        from django.db import connection
        table_name = 'cermaq_incidencias_incidencias_controldiario'
        
        with connection.cursor() as cursor:
            cursor.execute(f"SHOW TABLES LIKE '{table_name}'")
            if not cursor.fetchone():
                return Response({
                    'error': 'La tabla de Control Diario no existe. Por favor, ejecuta el script SQL.'
                }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        control = ControlDiario.objects.filter(
            centro_id=centro_id,
            fecha=fecha,
            modulo=modulo
        ).first()
        
        if control:
            data = {
                'id': control.id,
                'fecha': str(control.fecha),
                'anio': control.anio,
                'semana': control.semana,
                'dia': control.dia,
                'responsable': control.responsable,
                'modulo': control.modulo,
            }
            
            for hora in ['00', '04', '08', '12', '16', '20']:
                for param in ['temp', 'ph', 'oxigeno']:
                    field_name = f'hora_{hora}_{param}'
                    value = getattr(control, field_name)
                    data[field_name] = str(value) if value else None
            
            data['promedio_temp'] = str(control.promedio_temp) if control.promedio_temp else None
            data['promedio_ph'] = str(control.promedio_ph) if control.promedio_ph else None
            data['promedio_oxigeno'] = str(control.promedio_oxigeno) if control.promedio_oxigeno else None
            
            return Response(data, status=status.HTTP_200_OK)
        else:
            return Response({'message': 'No encontrado'}, status=status.HTTP_404_NOT_FOUND)
            
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


# --- VISTAS PARA REPORTE DE CÁMARAS ---
@login_required
def vista_reporte_camaras(request):
    """
    Vista principal para el Reporte de Cámaras
    """
    if not request.user.is_staff:
        return redirect('dashboard')
    
    from datetime import date
    
    fecha_actual = date.today()
    
    contexto = {
        'fecha_actual': fecha_actual,
        'es_admin': request.user.is_staff
    }
    
    return render(request, 'reporte_camaras.html', contexto)


@csrf_exempt
@api_view(['POST'])
def guardar_reporte_camaras_api(request):
    """
    API para guardar o actualizar un reporte de cámaras
    """
    from datetime import datetime
    
    if request.method == 'POST':
        data = request.data
        
        try:
            try:
                from .models import ReporteCamaras
            except ImportError:
                return Response({
                    'success': False,
                    'message': 'El modelo ReporteCamaras no está disponible. Por favor, ejecuta las migraciones.'
                }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            
            fecha = datetime.strptime(data.get('fecha'), '%Y-%m-%d').date()
            turno = data.get('turno')
            responsable = data.get('responsable')
            centros_data = data.get('centros', {})
            
            reporte, created = ReporteCamaras.objects.get_or_create(
                fecha=fecha,
                turno=turno,
                defaults={
                    'responsable': responsable,
                }
            )
            
            if not created:
                reporte.responsable = responsable
            
            for centro_key, centro_info in centros_data.items():
                field_incidencia = f'{centro_key}_tiene_incidencias'
                field_descripcion = f'{centro_key}_descripcion'
                
                setattr(reporte, field_incidencia, centro_info.get('tiene_incidencias', False))
                setattr(reporte, field_descripcion, centro_info.get('descripcion', ''))
            
            reporte.save()
            
            return Response({
                'success': True,
                'message': 'Reporte de cámaras guardado exitosamente',
                'id': reporte.id,
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({
                'success': False,
                'message': f'Error al guardar: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)


@csrf_exempt
@api_view(['GET'])
def obtener_reporte_camaras_api(request):
    """
    API para obtener un reporte de cámaras por fecha
    """
    from datetime import datetime
    
    fecha_str = request.GET.get('fecha')
    
    if not fecha_str:
        return Response({'error': 'Falta el parámetro fecha'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        try:
            from .models import ReporteCamaras
        except ImportError:
            return Response({
                'error': 'El modelo ReporteCamaras no está disponible'
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        reporte = ReporteCamaras.objects.filter(fecha=fecha).first()
        
        if reporte:
            data = {
                'id': reporte.id,
                'fecha': str(reporte.fecha),
                'turno': reporte.turno,
                'responsable': reporte.responsable,
                'centros': {
                    'rio_pescado': {
                        'tiene_incidencias': reporte.rio_pescado_tiene_incidencias,
                        'descripcion': reporte.rio_pescado_descripcion
                    },
                    'collin': {
                        'tiene_incidencias': reporte.collin_tiene_incidencias,
                        'descripcion': reporte.collin_descripcion
                    },
                    'lican': {
                        'tiene_incidencias': reporte.lican_tiene_incidencias,
                        'descripcion': reporte.lican_descripcion
                    },
                    'trafun': {
                        'tiene_incidencias': reporte.trafun_tiene_incidencias,
                        'descripcion': reporte.trafun_descripcion
                    }
                }
            }
            
            return Response(data, status=status.HTTP_200_OK)
        else:
            return Response({'message': 'No encontrado'}, status=status.HTTP_404_NOT_FOUND)
            
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


# --- VISTAS PARA CONSULTA DE REPORTES DE CÁMARAS ---
@login_required
def vista_consulta_reportes_camaras(request):
    """
    Vista para consultar y filtrar reportes de cámaras
    """
    if not request.user.is_staff:
        return redirect('dashboard')
    
    return render(request, 'consulta_reportes_camaras.html')


@csrf_exempt
@api_view(['GET'])
def listar_reportes_camaras_api(request):
    """
    API para listar reportes de cámaras con filtros
    """
    from datetime import datetime
    
    try:
        try:
            from .models import ReporteCamaras
        except ImportError:
            return Response({
                'error': 'El modelo ReporteCamaras no está disponible'
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        # Obtener parámetros de filtro
        fecha_desde = request.GET.get('fecha_desde')
        fecha_hasta = request.GET.get('fecha_hasta')
        turno_filtro = request.GET.get('turno')
        responsable_filtro = request.GET.get('responsable')
        centro_incidencias = request.GET.get('centro_incidencias')
        
        # Iniciar query
        reportes = ReporteCamaras.objects.all()
        
        # Aplicar filtros
        if fecha_desde:
            reportes = reportes.filter(fecha__gte=fecha_desde)
        
        if fecha_hasta:
            reportes = reportes.filter(fecha__lte=fecha_hasta)
        
        if turno_filtro:
            reportes = reportes.filter(turno=turno_filtro)
        
        if responsable_filtro:
            reportes = reportes.filter(responsable__icontains=responsable_filtro)
        
        if centro_incidencias:
            field_name = f'{centro_incidencias}_tiene_incidencias'
            filter_dict = {field_name: True}
            reportes = reportes.filter(**filter_dict)
        
        # Ordenar por fecha descendente
        reportes = reportes.order_by('-fecha', '-creado_en')
        
        # Serializar datos
        reportes_data = []
        for reporte in reportes:
            reportes_data.append({
                'id': reporte.id,
                'fecha': str(reporte.fecha),
                'turno': reporte.turno,
                'responsable': reporte.responsable,
                'rio_pescado_tiene_incidencias': reporte.rio_pescado_tiene_incidencias,
                'collin_tiene_incidencias': reporte.collin_tiene_incidencias,
                'lican_tiene_incidencias': reporte.lican_tiene_incidencias,
                'trafun_tiene_incidencias': reporte.trafun_tiene_incidencias,
                'creado_en': reporte.creado_en.isoformat(),
            })
        
        return Response({
            'success': True,
            'reportes': reportes_data,
            'total': len(reportes_data)
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@csrf_exempt
@api_view(['GET'])
def detalle_reporte_camaras_api(request, pk):
    """
    API para obtener el detalle completo de un reporte de cámaras
    """
    try:
        try:
            from .models import ReporteCamaras
        except ImportError:
            return Response({
                'error': 'El modelo ReporteCamaras no está disponible'
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        reporte = ReporteCamaras.objects.filter(id=pk).first()
        
        if reporte:
            data = {
                'id': reporte.id,
                'fecha': str(reporte.fecha),
                'turno': reporte.turno,
                'responsable': reporte.responsable,
                'rio_pescado_tiene_incidencias': reporte.rio_pescado_tiene_incidencias,
                'rio_pescado_descripcion': reporte.rio_pescado_descripcion,
                'collin_tiene_incidencias': reporte.collin_tiene_incidencias,
                'collin_descripcion': reporte.collin_descripcion,
                'lican_tiene_incidencias': reporte.lican_tiene_incidencias,
                'lican_descripcion': reporte.lican_descripcion,
                'trafun_tiene_incidencias': reporte.trafun_tiene_incidencias,
                'trafun_descripcion': reporte.trafun_descripcion,
                'creado_en': reporte.creado_en.isoformat(),
                'actualizado_en': reporte.actualizado_en.isoformat(),
            }
            
            return Response(data, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Reporte no encontrado'}, status=status.HTTP_404_NOT_FOUND)
            
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@csrf_exempt
@api_view(['DELETE'])
def eliminar_reporte_camaras_api(request, pk):
    """
    API para eliminar un reporte de cámaras
    """
    try:
        try:
            from .models import ReporteCamaras
        except ImportError:
            return Response({
                'error': 'El modelo ReporteCamaras no está disponible'
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        reporte = ReporteCamaras.objects.filter(id=pk).first()
        
        if reporte:
            reporte.delete()
            return Response({
                'success': True,
                'message': 'Reporte eliminado exitosamente'
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'success': False,
                'message': 'Reporte no encontrado'
            }, status=status.HTTP_404_NOT_FOUND)
            
    except Exception as e:
        return Response({
            'success': False,
            'message': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


# --- VISTA: DASHBOARD PROFESIONAL ---
@login_required
def dashboard_profesional(request):
    """
    Dashboard profesional estilo Power BI con gráficos avanzados
    """
    # Obtener todas las incidencias
    incidencias = Incidencia.objects.all().select_related('centro', 'operario_contacto').order_by('-fecha_hora')
    
    # Calcular KPIs
    total_incidencias = incidencias.count()
    
    # Contar por niveles de oxígeno
    oxigeno_alto = incidencias.filter(oxigeno_nivel='alta').count()
    oxigeno_bajo = incidencias.filter(oxigeno_nivel='baja').count()
    
    # Contar temperatura baja
    temperatura_baja = incidencias.filter(temperatura_nivel='baja').count()
    
    # Centro con más incidencias
    centro_stats = incidencias.values('centro__nombre').annotate(
        count=Count('id')
    ).order_by('-count').first()
    centro_top = f"{centro_stats['centro__nombre']} - {centro_stats['count']}" if centro_stats else "N/A"
    
    # Datos para gráfico de barras (por centro y parámetro)
    # Filtrar solo centros PCC que tienen incidencias
    centros_con_datos = Centro.objects.filter(
        nombre__in=['Trafún', 'Cipreses', 'Liquiñe']
    ).filter(
        id__in=incidencias.values_list('centro_id', flat=True).distinct()
    )
    centros = centros_con_datos
    centros_labels = [c.nombre for c in centros]
    
    oxigeno_alto_data = []
    oxigeno_bajo_data = []
    temperatura_baja_data = []
    
    for centro in centros:
        oxigeno_alto_data.append(
            incidencias.filter(centro=centro, oxigeno_nivel='alta').count()
        )
        oxigeno_bajo_data.append(
            incidencias.filter(centro=centro, oxigeno_nivel='baja').count()
        )
        temperatura_baja_data.append(
            incidencias.filter(centro=centro, temperatura_nivel='baja').count()
        )
    
    # Datos para gráfico de dona (distribución de tipos)
    tipos_stats = incidencias.values('tipo_incidencia_normalizada').annotate(
        count=Count('id')
    ).order_by('-count')  # Todos los tipos
    
    tipos_labels = [t['tipo_incidencia_normalizada'] or 'Sin clasificar' for t in tipos_stats]
    tipos_data = [t['count'] for t in tipos_stats]
    
    # Datos para gráfico de tendencia temporal (últimos 12 meses)
    from datetime import datetime, timedelta
    fecha_inicio = timezone.now() - timedelta(days=365)
    
    try:
        tendencia_stats = list(incidencias.filter(fecha_hora__gte=fecha_inicio).annotate(
            mes=TruncDate('fecha_hora')
        ).values('mes').annotate(
            count=Count('id')
        ).order_by('mes'))
        
        tendencia_labels = []
        tendencia_data = []
        for t in tendencia_stats:
            if t['mes']:
                try:
                    tendencia_labels.append(t['mes'].strftime('%b %Y'))
                    tendencia_data.append(t['count'])
                except:
                    pass
    except Exception:
        tendencia_labels = []
        tendencia_data = []
    
    # Datos para gráfico de tiempo de resolución promedio por centro
    resolucion_data = []
    for centro in centros:
        promedio = incidencias.filter(centro=centro).aggregate(
            promedio=Avg('tiempo_resolucion')
        )['promedio']
        resolucion_data.append(round(promedio, 1) if promedio else 0)
    
    # Datos para gráfico de incidencias por turno
    turnos_stats = incidencias.values('turno').annotate(
        count=Count('id')
    ).order_by('-count')
    
    turnos_labels = [t['turno'] or 'Sin turno' for t in turnos_stats]
    turnos_data = [t['count'] for t in turnos_stats]
    
    # Coordenadas reales de los centros PCC
    coordenadas_centros = {
        'Trafún': {'lat': -40.5833, 'lng': -73.0833, 'nombre': 'Trafún', 'ubicacion': 'San Pablo, Osorno'},
        'Cipreses': {'lat': -52.9167, 'lng': -70.8333, 'nombre': 'Cipreses', 'ubicacion': 'Punta Arenas, Magallanes'},
        'Liquiñe': {'lat': -39.7333, 'lng': -71.8667, 'nombre': 'Liquiñe', 'ubicacion': 'Liquiñe, Los Ríos'}
    }
    
    # Obtener meses únicos con datos - extraer directamente de fecha_hora
    meses_unicos = []
    meses_nombres = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 
                     'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
    
    meses_vistos = set()
    for inc in incidencias:
        if inc.fecha_hora:
            mes_num = inc.fecha_hora.month
            if mes_num not in meses_vistos:
                meses_vistos.add(mes_num)
                meses_unicos.append({
                    'numero': mes_num,
                    'nombre': meses_nombres[mes_num - 1]
                })
    
    # Ordenar por número de mes
    meses_unicos.sort(key=lambda x: x['numero'])
    
    # === ANÁLISIS DE JUSTIFICACIÓN Y VALOR AGREGADO ===
    
    # 1. Análisis de Causa Raíz (Top 5 causas más frecuentes)
    causas_raiz = incidencias.values('tipo_incidencia_normalizada').annotate(
        count=Count('id'),
        tiempo_promedio=Avg('tiempo_resolucion')
    ).order_by('-count')[:5]
    
    causas_labels = [c['tipo_incidencia_normalizada'] or 'Sin clasificar' for c in causas_raiz]
    causas_count = [c['count'] for c in causas_raiz]
    causas_tiempo = [round(c['tiempo_promedio'], 1) if c['tiempo_promedio'] else 0 for c in causas_raiz]
    
    # 2. Top 5 Tipos de Incidencia cuando Oxígeno está BAJO (oxigeno_nivel='baja')
    oxigeno_bajo_top = incidencias.filter(
        oxigeno_nivel='baja'
    ).values('tipo_incidencia_normalizada').annotate(
        count=Count('id'),
        tiempo_promedio=Avg('tiempo_resolucion')
    ).order_by('-count')[:5]
    
    oxigeno_bajo_labels = [item['tipo_incidencia_normalizada'] or 'Sin tipo' for item in oxigeno_bajo_top]
    oxigeno_bajo_count = [item['count'] for item in oxigeno_bajo_top]
    oxigeno_bajo_tiempo = [round(item['tiempo_promedio'], 1) if item['tiempo_promedio'] else 0 for item in oxigeno_bajo_top]
    
    # 3. Top 5 Tipos de Incidencia cuando Oxígeno está ALTO (oxigeno_nivel='alta')
    oxigeno_alto_top = incidencias.filter(
        oxigeno_nivel='alta'
    ).values('tipo_incidencia_normalizada').annotate(
        count=Count('id'),
        tiempo_promedio=Avg('tiempo_resolucion')
    ).order_by('-count')[:5]
    
    oxigeno_alto_labels = [item['tipo_incidencia_normalizada'] or 'Sin tipo' for item in oxigeno_alto_top]
    oxigeno_alto_count = [item['count'] for item in oxigeno_alto_top]
    oxigeno_alto_tiempo = [round(item['tiempo_promedio'], 1) if item['tiempo_promedio'] else 0 for item in oxigeno_alto_top]
    
    # 3. Tiempo de Respuesta vs Objetivo (SLA: 30 minutos)
    tiempo_objetivo = 30  # minutos
    tiempos_por_centro = []
    cumplimiento_sla = []
    
    for centro in centros:
        incidencias_centro = incidencias.filter(centro=centro)
        tiempo_promedio = incidencias_centro.aggregate(Avg('tiempo_resolucion'))['tiempo_resolucion__avg']
        tiempo_promedio = round(tiempo_promedio, 1) if tiempo_promedio else 0
        tiempos_por_centro.append(tiempo_promedio)
        
        # Calcular % de cumplimiento de SLA
        total_centro = incidencias_centro.count()
        dentro_sla = incidencias_centro.filter(tiempo_resolucion__lte=tiempo_objetivo).count()
        porcentaje_sla = round((dentro_sla / total_centro * 100), 1) if total_centro > 0 else 0
        cumplimiento_sla.append(porcentaje_sla)
    
    # 3. Tendencia de Mejora Mes a Mes (últimos 6 meses)
    from datetime import datetime, timedelta
    fecha_6_meses = timezone.now() - timedelta(days=180)
    
    try:
        mejora_mensual = list(incidencias.filter(fecha_hora__gte=fecha_6_meses).annotate(
            mes=TruncMonth('fecha_hora')
        ).values('mes').annotate(
            total=Count('id'),
            tiempo_promedio=Avg('tiempo_resolucion')
        ).order_by('mes'))
        
        mejora_labels = []
        mejora_total = []
        mejora_tiempo = []
        for m in mejora_mensual:
            if m['mes']:
                try:
                    mejora_labels.append(m['mes'].strftime('%b %Y'))
                    mejora_total.append(m['total'])
                    mejora_tiempo.append(round(m['tiempo_promedio'], 1) if m['tiempo_promedio'] else 0)
                except:
                    pass
    except Exception:
        mejora_labels = []
        mejora_total = []
        mejora_tiempo = []
    
    # 4. Análisis de Recurrencia (incidencias repetidas en mismo estanque/módulo)
    incidencias_recurrentes = 0
    incidencias_nuevas = 0
    
    # Agrupar por estanque y tipo para detectar recurrencia
    agrupacion = incidencias.values('estanque', 'tipo_incidencia_normalizada').annotate(
        count=Count('id')
    )
    
    for grupo in agrupacion:
        if grupo['count'] > 1:
            incidencias_recurrentes += grupo['count']
        else:
            incidencias_nuevas += grupo['count']
    
    # 5. KPIs de Valor Agregado
    # Calcular reducción de incidencias (comparar primer mes vs último mes)
    if len(mejora_total) >= 2:
        reduccion_porcentual = round(((mejora_total[0] - mejora_total[-1]) / mejora_total[0] * 100), 1) if mejora_total[0] > 0 else 0
        incidencias_evitadas = mejora_total[0] - mejora_total[-1]
    else:
        reduccion_porcentual = 0
        incidencias_evitadas = 0
    
    # Calcular mejora en tiempo de respuesta
    if len(mejora_tiempo) >= 2:
        mejora_tiempo_porcentual = round(((mejora_tiempo[0] - mejora_tiempo[-1]) / mejora_tiempo[0] * 100), 1) if mejora_tiempo[0] > 0 else 0
        minutos_ahorrados = round((mejora_tiempo[0] - mejora_tiempo[-1]) * total_incidencias, 0)
    else:
        mejora_tiempo_porcentual = 0
        minutos_ahorrados = 0
    
    # 5.1 Eficiencia Operativa (incidencias resueltas por hora de trabajo)
    horas_trabajo_estimadas = total_incidencias * (sum(tiempos_por_centro) / len(tiempos_por_centro) if tiempos_por_centro else 30) / 60
    eficiencia_operativa = round(total_incidencias / horas_trabajo_estimadas, 1) if horas_trabajo_estimadas > 0 else 0
    
    # 5.2 Cobertura de Centros (% de centros con seguimiento activo)
    centros_activos = len(centros)
    cobertura_centros = 100.0  # Todos los centros PCC tienen cobertura
    
    # 5.3 Tasa de Éxito (% de incidencias resueltas dentro del SLA)
    total_dentro_sla = sum([incidencias.filter(centro=centro, tiempo_resolucion__lte=tiempo_objetivo).count() for centro in centros])
    tasa_exito = round((total_dentro_sla / total_incidencias * 100), 1) if total_incidencias > 0 else 0
    
    # 5.4 Comparación con Periodo Anterior (si hay suficientes datos)
    if len(mejora_total) >= 4:
        # Comparar primeros 3 meses vs últimos 3 meses
        periodo_anterior = sum(mejora_total[:3])
        periodo_actual = sum(mejora_total[-3:])
        comparacion_periodos = round(((periodo_anterior - periodo_actual) / periodo_anterior * 100), 1) if periodo_anterior > 0 else 0
    else:
        comparacion_periodos = 0
    
    # 5.5 Insights Automáticos (interpretación de datos en lenguaje simple)
    insights = []
    
    # Insight 1: Tendencia general
    if reduccion_porcentual > 10:
        insights.append({
            'icono': '📉',
            'titulo': 'Tendencia Positiva',
            'mensaje': f'Las incidencias han disminuido un {reduccion_porcentual}%. ¡Excelente trabajo del equipo!',
            'tipo': 'success'
        })
    elif reduccion_porcentual < -10:
        insights.append({
            'icono': '📈',
            'titulo': 'Alerta: Aumento de Incidencias',
            'mensaje': f'Las incidencias aumentaron un {abs(reduccion_porcentual)}%. Revisar causas.',
            'tipo': 'warning'
        })
    else:
        insights.append({
            'icono': '➡️',
            'titulo': 'Estabilidad',
            'mensaje': 'Las incidencias se mantienen estables. Continuar monitoreando.',
            'tipo': 'info'
        })
    
    # Insight 2: Eficiencia del equipo
    if tasa_exito >= 90:
        insights.append({
            'icono': '⚡',
            'titulo': 'Equipo Altamente Eficiente',
            'mensaje': f'{tasa_exito}% de incidencias resueltas dentro del objetivo. ¡Excelente desempeño!',
            'tipo': 'success'
        })
    elif tasa_exito >= 70:
        insights.append({
            'icono': '👍',
            'titulo': 'Buen Desempeño',
            'mensaje': f'{tasa_exito}% de cumplimiento. Hay margen de mejora.',
            'tipo': 'info'
        })
    else:
        insights.append({
            'icono': '⚠️',
            'titulo': 'Oportunidad de Mejora',
            'mensaje': f'Solo {tasa_exito}% dentro del objetivo. Revisar procesos.',
            'tipo': 'warning'
        })
    
    # Insight 3: Problemas recurrentes
    porcentaje_recurrentes = round((incidencias_recurrentes / total_incidencias * 100), 1) if total_incidencias > 0 else 0
    if porcentaje_recurrentes > 50:
        insights.append({
            'icono': '🔄',
            'titulo': 'Alta Recurrencia',
            'mensaje': f'{porcentaje_recurrentes}% son problemas repetitivos. Implementar soluciones permanentes.',
            'tipo': 'warning'
        })
    else:
        insights.append({
            'icono': '✨',
            'titulo': 'Buena Prevención',
            'mensaje': f'Solo {porcentaje_recurrentes}% son recurrentes. La prevención está funcionando.',
            'tipo': 'success'
        })
    
    # Insight 4: Cobertura y disponibilidad
    insights.append({
        'icono': '�',
        'titulo': 'Cobertura Total',
        'mensaje': f'Monitoreo activo en {centros_activos} centros PCC con {cobertura_centros}% de cobertura.',
        'tipo': 'success'
    })
    
    # Insight 5: Centro crítico
    if centro_top:
        centro_nombre = centro_top.split(' - ')[0] if ' - ' in centro_top else centro_top
        insights.append({
            'icono': '🎯',
            'titulo': 'Centro Prioritario',
            'mensaje': f'{centro_nombre} concentra la mayor cantidad de incidencias. Enfocar recursos aquí.',
            'tipo': 'info'
        })
    
    # 6. Top 3 Recomendaciones basadas en datos
    recomendaciones = []
    
    # Recomendación 1: Centro con más incidencias
    if centro_top and 'Trafún' in str(centro_top):
        recomendaciones.append({
            'titulo': 'Priorizar Trafún',
            'descripcion': f'{centro_top} requiere atención prioritaria',
            'impacto': 'Alto'
        })
    
    # Recomendación 2: Tipo de incidencia más frecuente
    if causas_labels:
        recomendaciones.append({
            'titulo': f'Prevenir {causas_labels[0]}',
            'descripcion': f'Representa {causas_count[0]} incidencias ({round(causas_count[0]/total_incidencias*100, 1)}%)',
            'impacto': 'Alto'
        })
    
    # Recomendación 3: Centros bajo SLA
    centros_bajo_sla = [centros_labels[i] for i, sla in enumerate(cumplimiento_sla) if sla < 80]
    if centros_bajo_sla:
        recomendaciones.append({
            'titulo': 'Mejorar Tiempo de Respuesta',
            'descripcion': f'{", ".join(centros_bajo_sla)} bajo 80% de cumplimiento SLA',
            'impacto': 'Medio'
        })
    
    # Preparar datos para JavaScript
    datos_json = json.dumps({
        'total': total_incidencias,
        'oxigeno_alto': oxigeno_alto,
        'oxigeno_bajo': oxigeno_bajo,
        'temperatura_baja': temperatura_baja
    })
    
    context = {
        'centros': centros,
        'incidencias': incidencias,  # Todas las incidencias para filtrado correcto
        'total_incidencias': total_incidencias,
        'oxigeno_alto': oxigeno_alto,
        'oxigeno_bajo': oxigeno_bajo,
        'temperatura_baja': temperatura_baja,
        'centro_top': centro_top,
        'meses_unicos': meses_unicos,  # Meses con datos reales
        'centros_labels': json.dumps(centros_labels),
        'oxigeno_alto_data': json.dumps(oxigeno_alto_data),
        'oxigeno_bajo_data': json.dumps(oxigeno_bajo_data),
        'temperatura_baja_data': json.dumps(temperatura_baja_data),
        'tipos_labels': json.dumps(tipos_labels),
        'tipos_data': json.dumps(tipos_data),
        'tendencia_labels': json.dumps(tendencia_labels),
        'tendencia_data': json.dumps(tendencia_data),
        'resolucion_data': json.dumps(resolucion_data),
        'turnos_labels': json.dumps(turnos_labels),
        'turnos_data': json.dumps(turnos_data),
        'coordenadas_centros': json.dumps(coordenadas_centros),
        'datos_json': datos_json,
        # Datos de análisis y justificación
        'causas_labels': json.dumps(causas_labels),
        'causas_count': json.dumps(causas_count),
        'causas_tiempo': json.dumps(causas_tiempo),
        'oxigeno_bajo_labels': json.dumps(oxigeno_bajo_labels),
        'oxigeno_bajo_count': json.dumps(oxigeno_bajo_count),
        'oxigeno_bajo_tiempo': json.dumps(oxigeno_bajo_tiempo),
        'oxigeno_alto_labels': json.dumps(oxigeno_alto_labels),
        'oxigeno_alto_count': json.dumps(oxigeno_alto_count),
        'oxigeno_alto_tiempo': json.dumps(oxigeno_alto_tiempo),
        'tiempo_objetivo': tiempo_objetivo,
        'tiempos_por_centro': json.dumps(tiempos_por_centro),
        'cumplimiento_sla': json.dumps(cumplimiento_sla),
        'mejora_labels': json.dumps(mejora_labels),
        'mejora_total': json.dumps(mejora_total),
        'mejora_tiempo': json.dumps(mejora_tiempo),
        'incidencias_recurrentes': incidencias_recurrentes,
        'incidencias_nuevas': incidencias_nuevas,
        'reduccion_porcentual': reduccion_porcentual,
        'mejora_tiempo_porcentual': mejora_tiempo_porcentual,
        'recomendaciones': recomendaciones,
        # Nuevas métricas de mejora
        'incidencias_evitadas': incidencias_evitadas,
        'minutos_ahorrados': int(minutos_ahorrados),
        'eficiencia_operativa': eficiencia_operativa,
        'horas_trabajo_estimadas': round(horas_trabajo_estimadas, 1),
        'centros_activos': centros_activos,
        'cobertura_centros': cobertura_centros,
        'tasa_exito': tasa_exito,
        'comparacion_periodos': comparacion_periodos,
        'insights': insights,
    }
    
    return render(request, 'dashboard_profesional.html', context)


# ============================================================================
# SISTEMA DE MONITOREO DE SENSORES (IDEAL CONTROL)
# ============================================================================

@login_required
def vista_monitoreo_sensores(request):
    """Vista principal del formulario de monitoreo de sensores"""
    centros = Centro.objects.all().order_by('nombre')
    
    contexto = {
        'centros': centros,
        'fecha_hoy': timezone.now().date(),
    }
    
    return render(request, 'monitoreo_sensores.html', contexto)


@login_required
def vista_consulta_sensores(request):
    """Vista para consultar reportes de sensores registrados (similar a reporte.html)"""
    # Obtener filtros
    fecha_filtro = request.GET.get('fecha', '')
    turno_filtro = request.GET.get('turno', '')
    centro_filtro = request.GET.get('centro', '')
    
    # Query base - SOLO INCIDENCIAS (ALTO/BAJO) para reportes
    # Los datos NORMALES se mantienen en BD para estadísticas del dashboard
    registros = MonitoreoSensores.objects.select_related('centro', 'sensor').filter(
        estado__in=['ALTO', 'BAJO']
    )
    
    # Aplicar filtros
    if fecha_filtro:
        registros = registros.filter(fecha=fecha_filtro)
    
    if turno_filtro:
        registros = registros.filter(turno=turno_filtro)
    
    if centro_filtro:
        registros = registros.filter(centro_id=centro_filtro)
    
    # Ordenar
    registros = registros.order_by('-fecha', 'turno', 'centro__nombre', 'sensor__sistema')
    
    # Agrupar por fecha y turno
    reportes_agrupados = {}
    for registro in registros:
        key = f"{registro.fecha}_{registro.turno}"
        if key not in reportes_agrupados:
            reportes_agrupados[key] = {
                'fecha': registro.fecha,
                'hora_inicio': registro.hora_inicio,
                'turno': registro.turno,
                'responsable': registro.responsable,
                'registros': [],
                'total_sensores': 0,
                'total_altos': 0,
                'total_bajos': 0,
                'total_normales': 0,
                'centros': set()
            }
        
        reportes_agrupados[key]['registros'].append(registro)
        reportes_agrupados[key]['total_sensores'] += 1
        reportes_agrupados[key]['centros'].add(registro.centro.nombre)
        
        if registro.estado == 'ALTO':
            reportes_agrupados[key]['total_altos'] += 1
        elif registro.estado == 'BAJO':
            reportes_agrupados[key]['total_bajos'] += 1
        else:
            reportes_agrupados[key]['total_normales'] += 1
    
    # Convertir a lista y ordenar
    reportes_lista = []
    for key, datos in reportes_agrupados.items():
        datos['centros'] = ', '.join(sorted(datos['centros']))
        datos['total_incidencias'] = datos['total_altos'] + datos['total_bajos']
        reportes_lista.append(datos)
    
    reportes_lista.sort(key=lambda x: (x['fecha'], x['turno']), reverse=True)
    
    # Obtener centros para el filtro
    centros = Centro.objects.all().order_by('nombre')
    
    # Calcular estadísticas globales
    total_registros = registros.count()
    total_altos = registros.filter(estado='ALTO').count()
    total_bajos = registros.filter(estado='BAJO').count()
    total_normales = registros.filter(estado='NORMAL').count()
    
    contexto = {
        'reportes': reportes_lista,
        'centros': centros,
        'total_registros': total_registros,
        'total_altos': total_altos,
        'total_bajos': total_bajos,
        'total_normales': total_normales,
        'filtros_aplicados': {
            'fecha': fecha_filtro,
            'turno': turno_filtro,
            'centro': centro_filtro,
        },
        'es_admin': request.user.is_staff,
    }
    
    return render(request, 'consulta_sensores.html', contexto)


@login_required
def api_obtener_sistemas(request):
    """API para obtener sistemas disponibles por centro"""
    centro_id = request.GET.get('centro_id')
    
    if not centro_id:
        return JsonResponse({'error': 'Centro no especificado'}, status=400)
    
    try:
        # Obtener sistemas únicos para este centro
        sistemas = SensorConfig.objects.filter(
            centro_id=centro_id,
            activo=True
        ).values_list('sistema', flat=True).distinct().order_by('sistema')
        
        return JsonResponse({
            'sistemas': list(sistemas)
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def api_obtener_sensores(request):
    """API para obtener sensores de un sistema específico"""
    centro_id = request.GET.get('centro_id')
    sistema = request.GET.get('sistema')
    
    if not centro_id or not sistema:
        return JsonResponse({'error': 'Parámetros incompletos'}, status=400)
    
    try:
        sensores = SensorConfig.objects.filter(
            centro_id=centro_id,
            sistema=sistema,
            activo=True
        ).values(
            'id',
            'equipo',
            'tipo_medicion',
            'limite_min',
            'limite_max'
        ).order_by('orden', 'equipo')
        
        return JsonResponse({
            'sensores': list(sensores)
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def api_guardar_monitoreo(request):
    """API para guardar el monitoreo completo de sensores"""
    try:
        data = json.loads(request.body)
        
        fecha = data.get('fecha')
        hora_inicio = data.get('hora_inicio')
        turno = data.get('turno')
        responsable = data.get('responsable')
        registros = data.get('registros', [])
        
        if not all([fecha, turno, responsable, registros]):
            return JsonResponse({'error': 'Datos incompletos'}, status=400)
        
        # Guardar cada registro
        registros_guardados = 0
        for reg in registros:
            MonitoreoSensores.objects.update_or_create(
                fecha=fecha,
                turno=turno,
                centro_id=reg['centro_id'],
                sensor_id=reg['sensor_id'],
                defaults={
                    'hora_inicio': hora_inicio if hora_inicio else None,
                    'estado': reg['estado'],
                    'observacion': reg.get('observacion', ''),
                    'responsable': responsable
                }
            )
            registros_guardados += 1
        
        return JsonResponse({
            'success': True,
            'mensaje': f'{registros_guardados} sensores registrados correctamente',
            'registros_guardados': registros_guardados
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def api_obtener_reporte_sensores(request):
    """API para obtener datos del reporte de sensores"""
    fecha = request.GET.get('fecha')
    turno = request.GET.get('turno')
    
    if not fecha or not turno:
        return JsonResponse({'error': 'Fecha y turno requeridos'}, status=400)
    
    try:
        # Obtener todos los registros del día/turno
        registros = MonitoreoSensores.objects.filter(
            fecha=fecha,
            turno=turno
        ).select_related('centro', 'sensor').order_by('centro__nombre', 'sensor__sistema')
        
        datos = []
        for reg in registros:
            if reg.estado != 'NORMAL':  # Solo incluir incidencias
                datos.append({
                    'fecha': str(reg.fecha),
                    'piscicultura': reg.centro.nombre,
                    'sistema': reg.sensor.sistema,
                    'equipo': reg.sensor.equipo,
                    'tipo_medicion': reg.sensor.tipo_medicion,
                    'incidencia': f"LIMITE {reg.sensor.limite_min} - {reg.sensor.limite_max}",
                    'estado': reg.estado,
                    'observacion': reg.observacion,
                    'total_alto': 1 if reg.estado == 'ALTO' else 0,
                    'total_bajo': 1 if reg.estado == 'BAJO' else 0
                })
        
        return JsonResponse({
            'success': True,
            'registros': datos,
            'total': len(datos)
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def api_listar_reportes_sensores(request):
    """API para listar todos los reportes de sensores registrados"""
    try:
        # Obtener reportes únicos por fecha y turno
        reportes = MonitoreoSensores.objects.values(
            'fecha', 'turno', 'responsable'
        ).annotate(
            total_sensores=Count('id'),
            total_altos=Count('id', filter=Q(estado='ALTO')),
            total_bajos=Count('id', filter=Q(estado='BAJO')),
            total_normales=Count('id', filter=Q(estado='NORMAL'))
        ).order_by('-fecha', 'turno')
        
        datos = []
        for reporte in reportes:
            # Obtener centros involucrados
            centros = MonitoreoSensores.objects.filter(
                fecha=reporte['fecha'],
                turno=reporte['turno']
            ).values_list('centro__nombre', flat=True).distinct()
            
            datos.append({
                'fecha': str(reporte['fecha']),
                'turno': reporte['turno'],
                'responsable': reporte['responsable'],
                'total_sensores': reporte['total_sensores'],
                'total_altos': reporte['total_altos'],
                'total_bajos': reporte['total_bajos'],
                'total_normales': reporte['total_normales'],
                'centros': ', '.join(centros)
            })
        
        return JsonResponse({
            'success': True,
            'reportes': datos,
            'total': len(datos)
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def api_detalle_reporte_sensores(request):
    """API para obtener el detalle completo de un reporte específico"""
    fecha = request.GET.get('fecha')
    turno = request.GET.get('turno')
    
    if not fecha or not turno:
        return JsonResponse({'error': 'Fecha y turno requeridos'}, status=400)
    
    try:
        registros = MonitoreoSensores.objects.filter(
            fecha=fecha,
            turno=turno
        ).select_related('centro', 'sensor').order_by('centro__nombre', 'sensor__sistema', 'sensor__equipo')
        
        if not registros.exists():
            return JsonResponse({'error': 'Reporte no encontrado'}, status=404)
        
        datos = []
        for reg in registros:
            datos.append({
                'id': reg.id,
                'centro': reg.centro.nombre,
                'sistema': reg.sensor.sistema,
                'equipo': reg.sensor.equipo,
                'tipo_medicion': reg.sensor.tipo_medicion,
                'limite_min': reg.sensor.limite_min,
                'limite_max': reg.sensor.limite_max,
                'estado': reg.estado,
                'observacion': reg.observacion,
                'responsable': reg.responsable,
                'creado_en': reg.creado_en.strftime('%Y-%m-%d %H:%M:%S')
            })
        
        return JsonResponse({
            'success': True,
            'fecha': fecha,
            'turno': turno,
            'registros': datos,
            'total': len(datos)
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# --- DASHBOARD DE SENSORES ---
@login_required
def dashboard_sensores(request):
    """
    Dashboard profesional para el sistema de monitoreo de sensores
    """
    from django.db.models import Count
    from django.db.models.functions import TruncDate
    import json
    
    # Filtros
    periodo_filtro = request.GET.get('periodo', 'all')
    centro_filtro = request.GET.get('centro', None)
    
    # Query base
    base_query = MonitoreoSensores.objects.all()
    
    # Filtrar por periodo
    fecha_limite = None
    if periodo_filtro == 'week':
        fecha_limite = timezone.now() - timedelta(days=7)
    elif periodo_filtro == 'month':
        fecha_limite = timezone.now() - timedelta(days=30)
    elif periodo_filtro == 'quarter':
        fecha_limite = timezone.now() - timedelta(days=90)
    
    if fecha_limite:
        base_query = base_query.filter(creado_en__gte=fecha_limite)
    if centro_filtro:
        base_query = base_query.filter(centro_id=centro_filtro)
    
    # Estadísticas principales
    total_registros = base_query.count()
    total_incidencias = base_query.filter(estado__in=['ALTO', 'BAJO']).count()
    total_normales = base_query.filter(estado='NORMAL').count()
    total_altos = base_query.filter(estado='ALTO').count()
    total_bajos = base_query.filter(estado='BAJO').count()
    
    # Porcentaje de cumplimiento (sensores normales)
    porcentaje_cumplimiento = int((total_normales / total_registros * 100)) if total_registros > 0 else 0
    
    # Gráfico: Incidencias por Centro
    chart_centro_query = base_query.filter(centro__isnull=False, estado__in=['ALTO', 'BAJO']) \
        .values('centro__nombre') \
        .annotate(count=Count('id')) \
        .order_by('-count')
    chart_centro_labels = [item['centro__nombre'] for item in chart_centro_query]
    chart_centro_counts = [item['count'] for item in chart_centro_query]
    centro_mas_incidencias = chart_centro_labels[0] if chart_centro_labels else "-"
    
    # Gráfico: Tendencia temporal
    chart_tendencia_query = base_query.filter(estado__in=['ALTO', 'BAJO']) \
        .annotate(dia=TruncDate('creado_en')) \
        .values('dia') \
        .annotate(count=Count('id')) \
        .order_by('dia')
    chart_tendencia_labels = [item['dia'].strftime('%Y-%m-%d') if item['dia'] else 'Sin fecha' for item in chart_tendencia_query]
    chart_tendencia_data = [item['count'] for item in chart_tendencia_query]
    
    # Gráfico: Distribución por estado
    chart_estados_data = [total_normales, total_altos, total_bajos]
    
    # Gráfico: Incidencias por Sistema
    chart_sistema_query = base_query.filter(sensor__isnull=False, estado__in=['ALTO', 'BAJO']) \
        .values('sensor__sistema') \
        .annotate(count=Count('id')) \
        .order_by('-count')[:10]
    chart_sistema_labels = [item['sensor__sistema'] for item in chart_sistema_query]
    chart_sistema_data = [item['count'] for item in chart_sistema_query]
    
    # KPIs por Centro
    centros_disponibles = Centro.objects.all()
    kpi_lista_final = []
    
    for c in centros_disponibles:
        total_c = base_query.filter(centro=c).count()
        normales_c = base_query.filter(centro=c, estado='NORMAL').count()
        incidencias_c = base_query.filter(centro=c, estado__in=['ALTO', 'BAJO']).count()
        porcentaje = int((normales_c / total_c * 100)) if total_c > 0 else 0
        
        kpi_lista_final.append({
            'centro_nombre': c.nombre,
            'total_sensores': total_c,
            'normales': normales_c,
            'incidencias': incidencias_c,
            'porcentaje': porcentaje,
            'cumple_meta': porcentaje >= 80
        })
    
    contexto = {
        'total_registros': total_registros,
        'total_incidencias': total_incidencias,
        'total_normales': total_normales,
        'total_altos': total_altos,
        'total_bajos': total_bajos,
        'porcentaje_cumplimiento': porcentaje_cumplimiento,
        'centro_mas_incidencias': centro_mas_incidencias,
        
        'chart_centro_labels_json': json.dumps(chart_centro_labels),
        'chart_centro_counts_json': json.dumps(chart_centro_counts),
        
        'chart_tendencia_labels_json': json.dumps(chart_tendencia_labels),
        'chart_tendencia_data_json': json.dumps(chart_tendencia_data),
        
        'chart_estados_data_json': json.dumps(chart_estados_data),
        
        'chart_sistema_labels_json': json.dumps(chart_sistema_labels),
        'chart_sistema_data_json': json.dumps(chart_sistema_data),
        
        'kpi_data': kpi_lista_final,
        'centros': centros_disponibles.order_by('nombre'),
        'filtros_aplicados': request.GET,
        'es_admin': request.user.is_staff
    }
    
    return render(request, 'dashboard_sensores.html', contexto)


# --- APIs PARA EDITAR Y ELIMINAR SENSORES ---
@csrf_exempt
@api_view(['DELETE'])
def api_eliminar_registro_sensor(request, pk):
    """
    Elimina un registro de sensor específico
    """
    try:
        registro = MonitoreoSensores.objects.get(pk=pk)
        registro.delete()
        return Response({
            'success': True,
            'message': 'Registro eliminado correctamente'
        }, status=status.HTTP_200_OK)
    except MonitoreoSensores.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Registro no encontrado'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'success': False,
            'message': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@csrf_exempt
@api_view(['PUT'])
def api_actualizar_registro_sensor(request, pk):
    """
    Actualiza un registro de sensor específico
    """
    try:
        registro = MonitoreoSensores.objects.get(pk=pk)
        
        # Actualizar campos
        if 'estado' in request.data:
            registro.estado = request.data['estado']
        if 'observacion' in request.data:
            registro.observacion = request.data['observacion']
        
        registro.save()
        
        return Response({
            'success': True,
            'message': 'Registro actualizado correctamente',
            'registro': {
                'id': registro.id,
                'estado': registro.estado,
                'observacion': registro.observacion
            }
        }, status=status.HTTP_200_OK)
    except MonitoreoSensores.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Registro no encontrado'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'success': False,
            'message': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@csrf_exempt
@api_view(['DELETE'])
def api_eliminar_reporte_completo(request):
    """
    Elimina todos los registros de sensores de una fecha y turno específicos
    """
    try:
        fecha = request.GET.get('fecha')
        turno = request.GET.get('turno')
        
        if not fecha or not turno:
            return Response({
                'success': False,
                'message': 'Fecha y turno son requeridos'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Eliminar todos los registros de esa fecha y turno
        registros = MonitoreoSensores.objects.filter(fecha=fecha, turno=turno)
        cantidad = registros.count()
        registros.delete()
        
        return Response({
            'success': True,
            'message': f'Reporte eliminado correctamente. {cantidad} registros eliminados.'
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({
            'success': False,
            'message': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


# ============================================
# VISTAS PARA REPORTES DE PLATAFORMA
# ============================================

@login_required
def vista_reporte_plataformas(request):
    """Vista para registrar reportes de fallas de plataforma"""
    centros = Centro.objects.all().order_by('nombre')
    return render(request, 'reporte_plataformas.html', {
        'centros': centros
    })


@login_required
def vista_editar_reporte_plataforma(request, pk):
    """Vista para editar un reporte de plataforma existente"""
    reporte = get_object_or_404(ReportePlataforma, pk=pk)
    centros = Centro.objects.all().order_by('nombre')
    
    # Serializar el reporte para pasarlo al JavaScript
    reporte_data = {
        'id': reporte.id,
        'fecha_hora': reporte.fecha_hora.strftime('%Y-%m-%dT%H:%M'),
        'turno': reporte.turno,
        'centro_id': reporte.centro.id,
        'plataforma': reporte.plataforma,
        'sistema_fallando': reporte.sistema_fallando,
        'tiempo_fuera_servicio': reporte.tiempo_fuera_servicio,
        'unidad_tiempo': reporte.unidad_tiempo,
        'contacto_proveedor': reporte.contacto_proveedor,
        'razon_caida': reporte.razon_caida,
        'riesgo_peces': reporte.riesgo_peces,
        'perdida_economica': reporte.perdida_economica,
        'responsable': reporte.responsable,
        'observacion': reporte.observacion
    }
    
    return render(request, 'reporte_plataformas.html', {
        'centros': centros,
        'reporte_editar': json.dumps(reporte_data),
        'editando': True
    })


@login_required
def vista_consulta_plataformas(request):
    """Vista para consultar reportes de plataformas registrados"""
    # Obtener filtros
    fecha_filtro = request.GET.get('fecha', '')
    plataforma_filtro = request.GET.get('plataforma', '')
    centro_filtro = request.GET.get('centro', '')
    
    # Query base
    reportes = ReportePlataforma.objects.select_related('centro').all()
    
    # Aplicar filtros
    if fecha_filtro:
        reportes = reportes.filter(fecha_hora__date=fecha_filtro)
    
    if plataforma_filtro:
        reportes = reportes.filter(plataforma=plataforma_filtro)
    
    if centro_filtro:
        reportes = reportes.filter(centro_id=centro_filtro)
    
    # Ordenar
    reportes = reportes.order_by('-fecha_hora', '-creado_en')
    
    # Paginación
    paginator = Paginator(reportes, 20)
    page = request.GET.get('page', 1)
    
    try:
        reportes_paginados = paginator.page(page)
    except PageNotAnInteger:
        reportes_paginados = paginator.page(1)
    except EmptyPage:
        reportes_paginados = paginator.page(paginator.num_pages)
    
    # Obtener centros para el filtro
    centros = Centro.objects.all().order_by('nombre')
    
    context = {
        'reportes': reportes_paginados,
        'centros': centros,
        'fecha_filtro': fecha_filtro,
        'plataforma_filtro': plataforma_filtro,
        'centro_filtro': centro_filtro,
    }
    
    return render(request, 'consulta_plataformas.html', context)


@api_view(['POST'])
@csrf_exempt
def api_guardar_reporte_plataforma(request):
    """API para guardar o actualizar un reporte de plataforma"""
    try:
        data = request.data
        reporte_id = data.get('id')
        
        # Datos del reporte
        reporte_data = {
            'fecha_hora': data.get('fecha_hora'),
            'turno': data.get('turno'),
            'centro_id': data.get('centro'),
            'plataforma': data.get('plataforma'),
            'sistema_fallando': data.get('sistema_fallando'),
            'tiempo_fuera_servicio': data.get('tiempo_fuera_servicio'),
            'unidad_tiempo': data.get('unidad_tiempo', 'minutos'),
            'contacto_proveedor': data.get('contacto_proveedor', 'no'),
            'razon_caida': data.get('razon_caida'),
            'riesgo_peces': data.get('riesgo_peces', False),
            'perdida_economica': data.get('perdida_economica', False),
            'responsable': data.get('responsable'),
            'observacion': data.get('observacion', '')
        }
        
        if reporte_id:
            # Actualizar reporte existente
            reporte = ReportePlataforma.objects.get(pk=reporte_id)
            for key, value in reporte_data.items():
                setattr(reporte, key, value)
            reporte.save()
            mensaje = 'Reporte actualizado correctamente'
        else:
            # Crear nuevo reporte
            reporte = ReportePlataforma.objects.create(**reporte_data)
            mensaje = 'Reporte registrado correctamente'
        
        return Response({
            'success': True,
            'message': mensaje,
            'reporte_id': reporte.id
        }, status=status.HTTP_201_CREATED if not reporte_id else status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': False,
            'message': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@csrf_exempt
def api_eliminar_reporte_plataforma(request, pk):
    """API para eliminar un reporte de plataforma"""
    try:
        reporte = get_object_or_404(ReportePlataforma, pk=pk)
        reporte.delete()
        
        return Response({
            'success': True,
            'message': 'Reporte eliminado correctamente'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': False,
            'message': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@login_required
def generar_reporte_general_pdf(request):
    """Genera un reporte consolidado diario estilo ejecutivo con incidencias PCC y alertas de sensores"""
    import os
    from django.conf import settings
    from .models import MonitoreoSensores
    import pytz
    from datetime import datetime, timedelta
    from reportlab.lib.pagesizes import A4, landscape
    
    # Obtener parámetros de fecha y turno
    fecha = request.GET.get('fecha', timezone.now().date())
    turno = request.GET.get('turno', '')
    
    if isinstance(fecha, str):
        fecha = datetime.strptime(fecha, '%Y-%m-%d').date()
    
    # Timezone Chile
    chile_tz = pytz.timezone('America/Santiago')
    inicio_dia = chile_tz.localize(datetime.combine(fecha, datetime.min.time()))
    fin_dia = inicio_dia + timedelta(days=1)
    
    # Obtener incidencias PCC
    incidencias_query = Incidencia.objects.filter(fecha_hora__gte=inicio_dia, fecha_hora__lt=fin_dia)
    if turno:
        incidencias_query = incidencias_query.filter(turno=turno)
    incidencias = incidencias_query.select_related('centro').order_by('centro__nombre', 'fecha_hora')
    
    # Obtener alertas de sensores
    sensores_query = MonitoreoSensores.objects.filter(fecha=fecha, estado__in=['ALTO', 'BAJO'])
    if turno:
        turno_map = {'Mañana': 'MAÑANA', 'Tarde': 'TARDE', 'Noche': 'NOCHE'}
        turno_sensor = turno_map.get(turno, turno.upper())
        sensores_query = sensores_query.filter(turno=turno_sensor)
    sensores = sensores_query.select_related('centro', 'sensor').order_by('centro__nombre', 'sensor__sistema')
    
    # Estadísticas por turno y centro
    centros_pcc = ['Liquiñe', 'Cipreses', 'Trafún']
    turnos_data = {'Mañana': 0, 'Tarde': 0, 'Noche': 0}
    centros_data = {c: {'count': 0, 'turnos': set(), 'estanques': set(), 'fallas': set(), 'incidencias': []} for c in centros_pcc}
    
    for inc in incidencias:
        centro_nombre = inc.centro.nombre if inc.centro else 'Otro'
        if inc.turno in turnos_data:
            turnos_data[inc.turno] += 1
        if centro_nombre in centros_data:
            centros_data[centro_nombre]['count'] += 1
            if inc.turno:
                centros_data[centro_nombre]['turnos'].add(inc.turno)
            if inc.estanque:
                centros_data[centro_nombre]['estanques'].add(inc.estanque)
            centros_data[centro_nombre]['fallas'].add('Estanque en Flushing')
            hora = inc.fecha_hora.astimezone(chile_tz).strftime('%H:%M') if inc.fecha_hora else '--:--'
            params = []
            if inc.oxigeno_nivel:
                params.append(f"O: {inc.oxigeno_valor or ''} mg/L")
            if inc.temperatura_nivel:
                params.append(f"T: {inc.temperatura_valor or ''}")
            centros_data[centro_nombre]['incidencias'].append({
                'hora': hora,
                'modulo': inc.modulo or '',
                'estanque': inc.estanque or '',
                'tipo': 'Estanque en Flushing',
                'tiempo': inc.tiempo_resolucion or '--',
                'kpi': 'OK' if inc.tiempo_resolucion and inc.tiempo_resolucion <= 20 else 'NO',
                'parametros': ', '.join(params) if params else '-'
            })
    
    # Crear PDF en formato horizontal
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Reporte_General_{fecha.strftime("%d%m%Y")}.pdf"'
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), rightMargin=15, leftMargin=15, topMargin=15, bottomMargin=15)
    elements = []
    styles = getSampleStyleSheet()
    
    page_width = landscape(A4)[0]
    
    # === HEADER ===
    header_data = [[
        Paragraph("<b>REPORTE MÓDULO/ESTANQUES Y SENSORES</b>", 
                  ParagraphStyle('Header', fontSize=14, textColor=colors.white, fontName='Helvetica-Bold')),
        Paragraph(f"<b>Fecha: {fecha.strftime('%d-%m-%Y')}</b><br/><font size=8>{'Turno: ' + turno if turno else 'Día Completo'}</font>",
                  ParagraphStyle('HeaderRight', fontSize=10, textColor=colors.white, alignment=2))
    ]]
    header_table = Table(header_data, colWidths=[page_width*0.6 - 30, page_width*0.4 - 30])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#008B8B')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('LEFTPADDING', (0, 0), (-1, -1), 15),
        ('RIGHTPADDING', (0, 0), (-1, -1), 15),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 10))
    
    # === KPI BOXES ===
    total_inc = incidencias.count()
    kpi_data = [[
        Paragraph(f"<font size=7>TOTAL</font><br/><b><font size=14>{total_inc}</font></b>", ParagraphStyle('KPI', alignment=1)),
        Paragraph(f"<font size=7>MAÑANA</font><br/><b><font size=14>{turnos_data['Mañana']}</font></b>", ParagraphStyle('KPI', alignment=1)),
        Paragraph(f"<font size=7>TARDE</font><br/><b><font size=14>{turnos_data['Tarde']}</font></b>", ParagraphStyle('KPI', alignment=1)),
        Paragraph(f"<font size=7>NOCHE</font><br/><b><font size=14>{turnos_data['Noche']}</font></b>", ParagraphStyle('KPI', alignment=1)),
        Paragraph(f"<font size=7>ALERTAS SENSORES</font><br/><b><font size=14>{sensores.count()}</font></b>", ParagraphStyle('KPI', alignment=1)),
    ]]
    kpi_table = Table(kpi_data, colWidths=[80, 80, 80, 80, 100])
    kpi_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), colors.HexColor('#F0F0F0')),
        ('BACKGROUND', (1, 0), (1, 0), colors.HexColor('#FFF8DC')),
        ('BACKGROUND', (2, 0), (2, 0), colors.HexColor('#FFE4C4')),
        ('BACKGROUND', (3, 0), (3, 0), colors.HexColor('#E6E6FA')),
        ('BACKGROUND', (4, 0), (4, 0), colors.HexColor('#FFE4E1')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.grey),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(kpi_table)
    elements.append(Spacer(1, 8))
    
    # === RESUMEN POR CENTRO ===
    elements.append(Paragraph("<b>RESUMEN POR CENTRO</b>", ParagraphStyle('Section', fontSize=9, spaceAfter=4)))
    
    centro_cards = []
    card_width = (page_width - 60) / 3
    
    for centro in centros_pcc:
        data = centros_data[centro]
        if data['count'] == 0:
            content = "<font size=7>Sin incidencias</font>"
        else:
            content = f"<b><font size=8>{data['count']} incidencia(s)</font></b><br/>"
            if data['turnos']:
                content += f"<font size=7><b>Turno:</b> {', '.join(data['turnos'])}</font><br/>"
            if data['estanques']:
                est_list = sorted(list(data['estanques']))[:5]
                content += f"<font size=7><b>Estanques:</b> {', '.join(est_list)}</font><br/>"
            if data['fallas']:
                content += f"<font size=7 color='#C75050'><b>Fallas:</b> {list(data['fallas'])[0]}</font>"
        
        centro_cards.append([
            Paragraph(f"<b>{centro.upper()}</b>", ParagraphStyle('CentroHeader', fontSize=8, textColor=colors.white, alignment=1)),
            Paragraph(content, ParagraphStyle('CentroContent', fontSize=7))
        ])
    
    # Crear tabla de centros
    centro_table_data = [[centro_cards[0][0], centro_cards[1][0], centro_cards[2][0]],
                         [centro_cards[0][1], centro_cards[1][1], centro_cards[2][1]]]
    centro_table = Table(centro_table_data, colWidths=[card_width, card_width, card_width], rowHeights=[18, 55])
    centro_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#008B8B')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.grey),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
        ('VALIGN', (0, 1), (-1, 1), 'TOP'),
        ('TOPPADDING', (0, 1), (-1, 1), 4),
        ('LEFTPADDING', (0, 1), (-1, 1), 4),
    ]))
    elements.append(centro_table)
    elements.append(Spacer(1, 8))
    
    # === DETALLE DE INCIDENCIAS PCC ===
    elements.append(Paragraph("<b>DETALLE DE INCIDENCIAS PCC</b>", ParagraphStyle('Section', fontSize=9, spaceAfter=4)))
    
    if incidencias.exists():
        detail_data = [['No.', 'Centro', 'Hora', 'Ubicación', 'Tipo de Incidencia', 'Parámetros Afectados', 'Tiempo', 'KPI']]
        row_num = 1
        for centro in centros_pcc:
            for inc in centros_data[centro]['incidencias'][:10]:
                ubicacion = f"Módulo {inc['modulo']} / Estanque {inc['estanque']}" if inc['modulo'] else 'N/A'
                kpi_color = '#2E8B57' if inc['kpi'] == 'OK' else '#C75050'
                detail_data.append([
                    str(row_num), centro, inc['hora'], ubicacion[:25], inc['tipo'][:30], 
                    inc['parametros'][:25], f"{inc['tiempo']} min",
                    Paragraph(f"<font color='{kpi_color}'><b>{inc['kpi']}</b></font>", styles['Normal'])
                ])
                row_num += 1
        
        if len(detail_data) > 1:
            detail_table = Table(detail_data, colWidths=[25, 55, 35, 90, 100, 100, 45, 35])
            detail_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#008B8B')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 7),
                ('FONTSIZE', (0, 1), (-1, -1), 6.5),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#E0E0E0')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8F9FA')]),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ]))
            elements.append(detail_table)
        else:
            elements.append(Paragraph("<i>No hay incidencias PCC registradas</i>", styles['Normal']))
    else:
        elements.append(Paragraph("<i>✓ Sin incidencias PCC registradas</i>", styles['Normal']))
    
    elements.append(Spacer(1, 10))
    
    # === ALERTAS DE SENSORES ===
    elements.append(Paragraph("<b>ALERTAS DE SENSORES (IDEAL CONTROL)</b>", ParagraphStyle('Section', fontSize=9, spaceAfter=4)))
    
    if sensores.exists():
        sensor_data = [['Centro', 'Sistema', 'Equipo', 'Estado', 'Observación']]
        for s in sensores[:15]:
            estado_color = '#C75050' if s.estado == 'ALTO' else '#D4A574'
            sensor_data.append([
                s.centro.nombre, s.sensor.sistema[:25], s.sensor.equipo[:35],
                Paragraph(f"<font color='{estado_color}'><b>{s.estado}</b></font>", styles['Normal']),
                (s.observacion[:45] + '...' if s.observacion and len(s.observacion) > 45 else s.observacion) or '-'
            ])
        
        sensor_table = Table(sensor_data, colWidths=[70, 100, 150, 50, 150])
        sensor_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#008B8B')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 7),
            ('FONTSIZE', (0, 1), (-1, -1), 6.5),
            ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#E0E0E0')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8F9FA')]),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        elements.append(sensor_table)
        elements.append(Paragraph(f"<b>Total: {sensores.count()} alertas</b>", ParagraphStyle('Total', fontSize=8, spaceBefore=4)))
    else:
        elements.append(Paragraph("<i>✓ Sin alertas de sensores</i>", styles['Normal']))
    
    # === FOOTER ===
    elements.append(Spacer(1, 15))
    fecha_gen = timezone.now().astimezone(chile_tz)
    elements.append(Paragraph(
        f"<font size=6 color='grey'>Generado automáticamente: {fecha_gen.strftime('%d/%m/%Y %H:%M')} hrs | Sistema de Monitoreo CERMAQ</font>",
        ParagraphStyle('Footer', alignment=1)
    ))
    
    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)
    
    return response


@login_required
def generar_pdf_plataforma(request, pk):
    """Genera un PDF simple y bonito del reporte de plataforma para enviar por correo"""
    import os
    from django.conf import settings
    
    reporte = get_object_or_404(ReportePlataforma, pk=pk)
    
    # Crear el objeto HttpResponse con el tipo de contenido PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Falla_{reporte.plataforma}_{reporte.fecha_hora.strftime("%d%m%Y")}.pdf"'
    
    # Crear el PDF
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=50, leftMargin=50, topMargin=40, bottomMargin=40)
    
    # Contenedor para los elementos del PDF
    elements = []
    
    # Estilos
    styles = getSampleStyleSheet()
    
    # Intentar agregar el logo de CERMAQ
    try:
        logo_path = os.path.join(settings.BASE_DIR, 'static', 'imagenes', 'logo-reporte-cermaq.png')
        if os.path.exists(logo_path):
            logo = Image(logo_path, width=2.5*inch, height=0.8*inch)
            logo.hAlign = 'CENTER'
            elements.append(logo)
            elements.append(Spacer(1, 15))
    except:
        pass
    
    # Título
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#00457C'),
        spaceAfter=5,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.HexColor('#666666'),
        spaceAfter=20,
        alignment=TA_CENTER,
        fontName='Helvetica'
    )
    
    # Determinar el subtítulo según la plataforma
    if reporte.plataforma == 'INNOVEX':
        subtitulo = "Liquiñe / Trafún"
    elif reporte.plataforma == 'SINPLANT':
        subtitulo = "Cipreses"
    elif reporte.plataforma == 'IDEAL CONTROL':
        subtitulo = f"Centro: {reporte.centro.nombre}"
    else:
        subtitulo = reporte.centro.nombre
    
    elements.append(Paragraph(f"REPORTE DE FALLA - {reporte.plataforma}", title_style))
    elements.append(Paragraph(subtitulo, subtitle_style))
    elements.append(Spacer(1, 10))
    
    # Convertir fecha_hora a zona horaria de Chile
    import pytz
    chile_tz = pytz.timezone('America/Santiago')
    fecha_hora_chile = reporte.fecha_hora.astimezone(chile_tz) if timezone.is_aware(reporte.fecha_hora) else chile_tz.localize(reporte.fecha_hora)
    
    # Determinar el texto del contacto con proveedor
    contacto_texto = {
        'no': '✗ No se contactó',
        'si': '✓ Sí, con respuesta',
        'sin_respuesta': '⚠ Sí, sin respuesta'
    }.get(reporte.contacto_proveedor, '✗ No se contactó')
    
    # Tabla principal con diseño bonito y profesional
    # Determinar la unidad de tiempo
    unidad = 'días' if reporte.unidad_tiempo == 'dias' else 'minutos'
    
    data = [
        ['FECHA Y HORA', fecha_hora_chile.strftime('%d/%m/%Y - %H:%M hrs')],
        ['TURNO', reporte.turno],
        ['', ''],
        ['SISTEMA AFECTADO', reporte.sistema_fallando],
        ['TIEMPO FUERA', f'{reporte.tiempo_fuera_servicio} {unidad}'],
        ['CONTACTO PROVEEDOR', contacto_texto],
        ['', ''],
        ['RAZÓN DE LA CAÍDA', reporte.razon_caida],
        ['', ''],
        ['RIESGO PECES', '⚠ SÍ' if reporte.riesgo_peces else '✓ NO'],
        ['PÉRDIDA ECONÓMICA', '⚠ SÍ' if reporte.perdida_economica else '✓ NO'],
    ]
    
    if reporte.observacion:
        data.append(['', ''])
        data.append(['OBSERVACIONES', reporte.observacion])
    
    # Convertir textos largos a Paragraphs para que se ajusten automáticamente
    normal_style = styles['Normal']
    normal_style.fontSize = 10
    normal_style.leading = 12
    
    # Procesar la data para convertir textos largos en Paragraphs
    processed_data = []
    for row in data:
        if len(row) == 2 and row[0] and row[1]:  # Solo procesar filas con contenido
            # Si el texto es largo, convertirlo a Paragraph
            if isinstance(row[1], str) and len(row[1]) > 50:
                processed_data.append([row[0], Paragraph(row[1], normal_style)])
            else:
                processed_data.append(row)
        else:
            processed_data.append(row)
    
    table = Table(processed_data, colWidths=[2.2*inch, 4.8*inch])
    table.setStyle(TableStyle([
        # Encabezados (columna izquierda)
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#E8F4F8')),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#00457C')),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (0, -1), 10),
        
        # Valores (columna derecha)
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (1, 0), (1, -1), 10),
        ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#333333')),
        
        # Alineación
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        
        # Padding
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        
        # Bordes suaves
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#CCCCCC')),
        ('LINEBELOW', (0, 0), (-1, -2), 0.5, colors.HexColor('#E0E0E0')),
        
        # Filas vacías (separadores)
        ('BACKGROUND', (0, 2), (-1, 2), colors.white),
        ('BACKGROUND', (0, 6), (-1, 6), colors.white),
        ('BACKGROUND', (0, 8), (-1, 8), colors.white),
        ('LINEBELOW', (0, 2), (-1, 2), 0, colors.white),
        ('LINEBELOW', (0, 6), (-1, 6), 0, colors.white),
        ('LINEBELOW', (0, 8), (-1, 8), 0, colors.white),
    ]))
    
    elements.append(table)
    elements.append(Spacer(1, 20))
    
    # Pie de página con fecha y hora completa en zona horaria de Chile
    import pytz
    chile_tz = pytz.timezone('America/Santiago')
    fecha_generacion = timezone.now().astimezone(chile_tz)
    
    # Obtener el día de la semana en español
    dias_semana = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
    dia_semana = dias_semana[fecha_generacion.weekday()]
    
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor('#999999'),
        alignment=TA_CENTER
    )
    
    fecha_texto = f"{dia_semana} {fecha_generacion.strftime('%d/%m/%Y')} - {fecha_generacion.strftime('%H:%M')} hrs"
    elements.append(Paragraph(f"Generado: {fecha_texto} | Puerto Montt, Chile | CERMAQ", footer_style))
    
    # Construir el PDF
    doc.build(elements)
    
    # Obtener el valor del buffer y escribirlo en la respuesta
    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)
    
    return response


# ============================================================================
# VISTAS PARA ESTADÍSTICAS DE PLATAFORMAS
# ============================================================================

def normalizar_razon_caida(razon):
    """
    Normaliza las razones de caída para agrupar descripciones similares.
    Detecta patrones comunes y los estandariza.
    """
    if not razon:
        return "Sin especificar"
    
    razon_lower = razon.lower().strip()
    
    # Diccionario de patrones ordenados por prioridad (más específicos primero)
    patrones = {
        # Sin respuesta del proveedor (DEBE IR PRIMERO para capturar correctamente)
        'Sin respuesta del proveedor': [
            'sin respuesta de sinplant', 'sin respuesta de innovex', 'sin respuesta de ideal control',
            'sin respuesta de idealcontrol', 'sin respuesta del proveedor', 'proveedor sin responder', 
            'proveedor no responde', 'sin respuesta por parte de', 'no hay respuesta de', 
            'falta respuesta de', 'se contactó con innovex y la rediseñ', 'se contacto con innovex',
            'no se tuvo información clara', 'no se tuvo informacion clara',
            'se contactó y no hubo respuesta de idealcontrol', 'se contacto y no hubo respuesta de idealcontrol',
            'no hubo respuesta de idealcontrol', 'no hubo respuesta de ideal control',
            'página caída sin respuesta inmediata', 'pagina caida sin respuesta inmediata',
            'sin respuesta inmediata luego del correo', 'sin respuesta inmediata',
            'datos sin actualizar', 'sin actualización de datos', 'sin actualizacion de datos',
            'datos no se actualizan', 'datos congelados', 'datos estáticos', 'datos estaticos',
            'sin carga de datos', 'datos no cargan', 'no carga datos en tiempo real',
            'sin carga en tiempo real', 'no carga en tiempo real'
        ],
        
        # Plataforma caída - Sin visualización de datos
        'Plataforma caída - Sin visualización de datos': [
            'plataforma caída', 'plataforma caida', 'caída de plataforma',
            'caida de plataforma', 'sin visualización de datos', 'sin visualizacion de datos',
            'plataforma sin funcionar', 'plataforma no funciona',
            'plataforma fuera de servicio', 'plataforma down', 'plataforma inaccesible'
        ],
        
        # Sistema congelado - Interfaz no responde
        'Sistema congelado - Interfaz no responde': [
            'sistema congelado', 'interfaz congelada', 'pantalla congelada',
            'sistema no responde', 'interfaz no responde', 'sistema bloqueado',
            'interfaz bloqueada', 'sistema trabado', 'interfaz trabada',
            'se reinició y no hubo respuesta del servidor', 'se reinicio y no hubo respuesta'
        ],
        
        # Pérdida de conectividad
        'Pérdida de conectividad': [
            'sin conectividad', 'pérdida de conectividad', 'perdida de conectividad',
            'falta de conectividad', 'problemas de conectividad',
            'falla de conectividad', 'conectividad perdida',
            'falla de conexión', 'falla de conexion', 'sin conexión', 'sin conexion',
            'pérdida de conexión', 'perdida de conexion', 'conexión perdida',
            'falla en la conexión', 'problemas de conexión', 'problemas de conexion',
            'sin señal', 'pérdida de señal', 'perdida de señal'
        ],
        
        # Cambio de servidor / Interferencia técnica
        'Cambio de servidor / Interferencia técnica': [
            'innovex en proceso de cambio de servidor', 'cambio de servidor',
            'proceso de cambio', 'interferencia', 'interferencia técnica',
            'interferencia tecnica'
        ],
        
        # Actualización / Modificación del sistema
        'Actualización / Modificación del sistema': [
            'se estuvieron realizando modificaciones en la bds', 
            'realizando modificaciones', 'modificaciones en',
            'actualización del sistema', 'actualizacion del sistema',
            'modificación del sistema', 'modificacion del sistema'
        ],
        
        # Mantenimiento programado
        'Mantenimiento programado': [
            'mantenimiento programado', 'mantenimiento preventivo', 'mantenimiento planificado',
            'en mantenimiento', 'mantenimiento de sistema', 'actualización programada',
            'actualizacion programada'
        ],
        
        # Falla eléctrica
        'Falla eléctrica': [
            'falla eléctrica', 'falla electrica', 'corte de luz', 'corte eléctrico',
            'corte electrico', 'problema eléctrico', 'problema electrico',
            'sin energía', 'sin energia', 'falta de energía', 'falta de energia'
        ],
        
        # Sobrecarga del sistema
        'Sobrecarga del sistema': [
            'sobrecarga', 'sistema sobrecargado', 'alto tráfico', 'mucho tráfico',
            'alto trafico', 'mucho trafico',
            'exceso de carga', 'saturación del sistema', 'saturacion del sistema'
        ],
        
        # Error de software
        'Error de software': [
            'error de software', 'bug', 'error en el sistema', 'fallo de software',
            'error de aplicación', 'error de aplicacion', 'error del programa'
        ]
    }
    
    # Buscar coincidencias en los patrones (orden importa)
    for categoria, keywords in patrones.items():
        for keyword in keywords:
            if keyword in razon_lower:
                return categoria
    
    # Si no coincide con ningún patrón, devolver la razón original capitalizada
    return razon.strip().capitalize()


@login_required
def vista_estadisticas_plataformas(request):
    """Vista principal para mostrar estadísticas de fallas de plataforma"""
    centros = Centro.objects.all().order_by('nombre')
    
    context = {
        'centros': centros,
    }
    
    return render(request, 'estadisticas_plataformas.html', context)


@login_required
def api_estadisticas_plataformas(request):
    """API para obtener datos estadísticos de fallas de plataforma"""
    try:
        # Obtener filtros opcionales
        fecha_inicio = request.GET.get('fecha_inicio', '')
        fecha_fin = request.GET.get('fecha_fin', '')
        plataforma_filtro = request.GET.get('plataforma', '')
        centro_filtro = request.GET.get('centro', '')
        
        # Query base
        reportes = ReportePlataforma.objects.select_related('centro').all()
        
        # Aplicar filtros
        if fecha_inicio:
            reportes = reportes.filter(fecha_hora__date__gte=fecha_inicio)
        if fecha_fin:
            reportes = reportes.filter(fecha_hora__date__lte=fecha_fin)
        if plataforma_filtro:
            reportes = reportes.filter(plataforma=plataforma_filtro)
        if centro_filtro:
            reportes = reportes.filter(centro_id=centro_filtro)
        
        # Estadísticas por tipo de falla
        fallas_por_tipo = {}
        for reporte in reportes:
            tipo = reporte.sistema_fallando
            if tipo not in fallas_por_tipo:
                fallas_por_tipo[tipo] = 0
            fallas_por_tipo[tipo] += 1
        
        # Estadísticas por plataforma
        fallas_por_plataforma = {}
        for reporte in reportes:
            plataforma = reporte.plataforma
            if plataforma not in fallas_por_plataforma:
                fallas_por_plataforma[plataforma] = 0
            fallas_por_plataforma[plataforma] += 1
        
        # Estadísticas por centro
        fallas_por_centro = {}
        for reporte in reportes:
            centro = reporte.centro.nombre
            if centro not in fallas_por_centro:
                fallas_por_centro[centro] = 0
            fallas_por_centro[centro] += 1
        
        # Tipos de falla por plataforma
        fallas_tipo_plataforma = {}
        for reporte in reportes:
            plataforma = reporte.plataforma
            tipo = reporte.sistema_fallando
            
            if plataforma not in fallas_tipo_plataforma:
                fallas_tipo_plataforma[plataforma] = {}
            
            if tipo not in fallas_tipo_plataforma[plataforma]:
                fallas_tipo_plataforma[plataforma][tipo] = 0
            
            fallas_tipo_plataforma[plataforma][tipo] += 1
        
        # Tiempo promedio fuera de servicio por tipo de falla (convertir todo a minutos)
        tiempo_por_tipo = {}
        for reporte in reportes:
            tipo = reporte.sistema_fallando
            # Convertir a minutos si está en días
            tiempo_minutos = reporte.tiempo_fuera_servicio
            if reporte.unidad_tiempo == 'dias':
                tiempo_minutos = reporte.tiempo_fuera_servicio * 1440  # 1 día = 1440 minutos
            
            if tipo not in tiempo_por_tipo:
                tiempo_por_tipo[tipo] = {'total': 0, 'count': 0}
            
            tiempo_por_tipo[tipo]['total'] += tiempo_minutos
            tiempo_por_tipo[tipo]['count'] += 1
        
        # Calcular promedios
        tiempo_promedio_por_tipo = {}
        for tipo, datos in tiempo_por_tipo.items():
            tiempo_promedio_por_tipo[tipo] = round(datos['total'] / datos['count'], 2)
        
        # Observaciones más comunes (normalizadas) con detalles de incidencias
        observaciones_comunes = {}
        detalles_por_razon = {}
        
        for reporte in reportes:
            # Si tiene razón de caída, normalizarla; si no, clasificar como 'Sin razón especificada'
            if reporte.razon_caida:
                razon_normalizada = normalizar_razon_caida(reporte.razon_caida)
            else:
                razon_normalizada = 'Sin razón especificada'
            
            # Contar ocurrencias
            if razon_normalizada not in observaciones_comunes:
                observaciones_comunes[razon_normalizada] = 0
                detalles_por_razon[razon_normalizada] = []
            
            observaciones_comunes[razon_normalizada] += 1
            
            # Guardar detalles de la incidencia
            chile_tz = pytz.timezone('America/Santiago')
            fecha_hora_chile = reporte.fecha_hora.astimezone(chile_tz) if timezone.is_aware(reporte.fecha_hora) else chile_tz.localize(reporte.fecha_hora)
            
            detalles_por_razon[razon_normalizada].append({
                'id': reporte.id,
                'fecha_hora': fecha_hora_chile.strftime('%d/%m/%Y %H:%M'),
                'centro': reporte.centro.nombre,
                'plataforma': reporte.plataforma,
                'sistema_fallando': reporte.sistema_fallando,
                'tiempo_fuera': f"{reporte.tiempo_fuera_servicio} {'días' if reporte.unidad_tiempo == 'dias' else 'min'}",
                'responsable': reporte.responsable,
                'razon_original': reporte.razon_caida if reporte.razon_caida else 'Sin razón',
                'observacion': reporte.observacion
            })
        
        # Ordenar observaciones por frecuencia
        observaciones_ordenadas = sorted(
            observaciones_comunes.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:10]  # Top 10
        
        return JsonResponse({
            'success': True,
            'total_reportes': reportes.count(),
            'fallas_por_tipo': fallas_por_tipo,
            'fallas_por_plataforma': fallas_por_plataforma,
            'fallas_por_centro': fallas_por_centro,
            'fallas_tipo_plataforma': fallas_tipo_plataforma,
            'tiempo_promedio_por_tipo': tiempo_promedio_por_tipo,
            'observaciones_comunes': dict(observaciones_ordenadas),
            'detalles_por_razon': detalles_por_razon
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


# ============================================================================
# IMPORTAR VISTAS DE PÉRDIDAS ECONÓMICAS
# ============================================================================
from .views_perdidas_economicas import (
    vista_perdidas_economicas,
    vista_registrar_inactividad,
    vista_editar_inactividad,
    vista_reporte_perdidas,
    api_obtener_sistemas_costos,
    api_guardar_inactividad,
    api_listar_inactividades,
    api_eliminar_inactividad,
    api_resolver_inactividad,
    api_estadisticas_perdidas,
    generar_pdf_perdidas
)
