"""
Vistas para el sistema de cálculo de pérdidas económicas por inactividad de sensores
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie
from django.db.models import Sum, Count, Q, Avg
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
import json

from .models import (
    Centro, CostoSistema, RegistroInactividad, 
    SensorConfig, MonitoreoSensores
)


# ============================================================================
# VISTAS PRINCIPALES
# ============================================================================

def vista_perdidas_economicas(request):
    """
    Vista principal del sistema de pérdidas económicas.
    Muestra dashboard con resumen de inactividades y pérdidas.
    """
    centros = Centro.objects.all().order_by('nombre')
    
    # Estadísticas generales
    total_registros = RegistroInactividad.objects.count()
    registros_activos = RegistroInactividad.objects.filter(fecha_fin__isnull=True).count()
    registros_resueltos = RegistroInactividad.objects.filter(resuelto=True).count()
    
    # Pérdidas totales
    perdidas_totales = RegistroInactividad.objects.filter(
        perdida_uf__isnull=False
    ).aggregate(
        total_uf=Sum('perdida_uf'),
        total_clp=Sum('perdida_clp')
    )
    
    # Registros recientes
    registros_recientes = RegistroInactividad.objects.select_related(
        'costo_sistema__centro', 'sensor'
    ).order_by('-fecha_inicio')[:10]
    
    context = {
        'centros': centros,
        'total_registros': total_registros,
        'registros_activos': registros_activos,
        'registros_resueltos': registros_resueltos,
        'perdidas_totales': perdidas_totales,
        'registros_recientes': registros_recientes,
    }
    
    return render(request, 'incidencias/perdidas_economicas/dashboard.html', context)


@ensure_csrf_cookie
def vista_registrar_inactividad(request):
    """
    Formulario para registrar una nueva inactividad de sensor.
    """
    centros = Centro.objects.all().order_by('nombre')
    
    context = {
        'centros': centros,
        'motivos': RegistroInactividad.MOTIVO_CHOICES,
    }
    
    return render(request, 'incidencias/perdidas_economicas/registrar.html', context)


def vista_editar_inactividad(request, pk):
    """
    Formulario para editar un registro de inactividad existente.
    """
    registro = get_object_or_404(RegistroInactividad, pk=pk)
    centros = Centro.objects.all().order_by('nombre')
    
    context = {
        'registro': registro,
        'centros': centros,
        'motivos': RegistroInactividad.MOTIVO_CHOICES,
        'modo_edicion': True,
    }
    
    return render(request, 'incidencias/perdidas_economicas/registrar.html', context)


def vista_reporte_perdidas(request):
    """
    Vista de reporte consolidado de pérdidas económicas con filtros.
    """
    centros = Centro.objects.all().order_by('nombre')
    
    # Obtener filtros de la URL
    centro_id = request.GET.get('centro')
    fecha_desde = request.GET.get('fecha_desde')
    fecha_hasta = request.GET.get('fecha_hasta')
    estado = request.GET.get('estado')  # 'activa', 'resuelta', 'todas'
    
    context = {
        'centros': centros,
        'filtros': {
            'centro_id': centro_id,
            'fecha_desde': fecha_desde,
            'fecha_hasta': fecha_hasta,
            'estado': estado or 'todas',
        }
    }
    
    return render(request, 'incidencias/perdidas_economicas/reporte.html', context)


# ============================================================================
# APIs
# ============================================================================

@require_http_methods(["GET"])
def api_obtener_sistemas_costos(request):
    """
    API para obtener los sistemas de costos de un centro específico,
    junto con los sensores disponibles agrupados por sistema.
    """
    centro_id = request.GET.get('centro_id')
    
    if not centro_id:
        return JsonResponse({'error': 'Se requiere centro_id'}, status=400)
    
    try:
        # Obtener centro
        centro = Centro.objects.get(id=centro_id)
        
        # Obtener sistemas de costos
        sistemas = CostoSistema.objects.filter(
            centro_id=centro_id,
            activo=True
        ).values(
            'id',
            'sistema',
            'monto_mensual_uf',
            'monto_mensual_clp',
            'costo_diario_uf',
            'costo_diario_clp',
            'costo_hora_uf',
            'costo_hora_clp'
        )
        
        # Obtener sensores del centro agrupados por sistema
        sensores_por_sistema = {}
        sensores_centro = SensorConfig.objects.filter(
            centro=centro.slug,
            activo=True
        ).values('id', 'sistema', 'equipo', 'tipo_medicion')
        
        for sensor in sensores_centro:
            sistema_nombre = sensor['sistema']
            if sistema_nombre not in sensores_por_sistema:
                sensores_por_sistema[sistema_nombre] = []
            sensores_por_sistema[sistema_nombre].append({
                'id': sensor['id'],
                'equipo': sensor['equipo'],
                'tipo_medicion': sensor['tipo_medicion'],
            })
        
        # Obtener todos los sistemas únicos de SensorConfig para este centro
        sistemas_sensores = list(
            SensorConfig.objects.filter(
                centro=centro.slug,
                activo=True
            ).values_list('sistema', flat=True).distinct().order_by('sistema')
        )
        
        return JsonResponse({
            'success': True,
            'sistemas': list(sistemas),
            'sensores_por_sistema': sensores_por_sistema,
            'sistemas_sensores': sistemas_sensores,
        })
        
    except Centro.DoesNotExist:
        return JsonResponse({'error': 'Centro no encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["POST"])
def api_guardar_inactividad(request):
    """
    API para guardar un nuevo registro de inactividad o actualizar uno existente.
    """
    try:
        data = json.loads(request.body)
        
        # Validar datos requeridos
        required_fields = ['costo_sistema_id', 'fecha_inicio', 'motivo', 'descripcion', 'responsable']
        for field in required_fields:
            if field not in data:
                return JsonResponse({'error': f'Campo requerido: {field}'}, status=400)
        
        # Obtener o crear registro
        registro_id = data.get('id')
        
        if registro_id:
            # Actualizar registro existente
            registro = get_object_or_404(RegistroInactividad, pk=registro_id)
        else:
            # Crear nuevo registro
            registro = RegistroInactividad()
        
        # Asignar datos
        registro.costo_sistema_id = data['costo_sistema_id']
        
        # Sensor específico (opcional)
        if data.get('sensor_id'):
            registro.sensor_id = data['sensor_id']
        
        # Fechas - parsear datetime-local (formato: YYYY-MM-DDTHH:MM)
        try:
            fecha_inicio_str = data['fecha_inicio'].replace('Z', '').replace('+00:00', '')
            registro.fecha_inicio = datetime.fromisoformat(fecha_inicio_str)
        except (ValueError, AttributeError) as e:
            return JsonResponse({'error': f'Formato de fecha inicio invalido: {e}'}, status=400)
        
        if data.get('fecha_fin'):
            try:
                fecha_fin_str = data['fecha_fin'].replace('Z', '').replace('+00:00', '')
                registro.fecha_fin = datetime.fromisoformat(fecha_fin_str)
            except (ValueError, AttributeError) as e:
                return JsonResponse({'error': f'Formato de fecha fin invalido: {e}'}, status=400)
        else:
            registro.fecha_fin = None
        
        # Detalles
        registro.motivo = data['motivo']
        registro.descripcion = data['descripcion']
        registro.responsable = data['responsable']
        
        # Seguimiento
        registro.contacto_proveedor = data.get('contacto_proveedor', False)
        if data.get('fecha_contacto'):
            try:
                fc_str = data['fecha_contacto'].replace('Z', '').replace('+00:00', '')
                registro.fecha_contacto = datetime.fromisoformat(fc_str)
            except (ValueError, AttributeError):
                registro.fecha_contacto = None
        
        registro.respuesta_proveedor = data.get('respuesta_proveedor', '')
        registro.resuelto = data.get('resuelto', False)
        
        # Reporte
        registro.incluir_en_reporte = data.get('incluir_en_reporte', True)
        registro.observaciones_reporte = data.get('observaciones_reporte', '')
        
        # Valor UF del día para cálculo CLP
        if data.get('valor_uf_usado'):
            registro.valor_uf_usado = Decimal(str(data['valor_uf_usado']))
        
        # Guardar (esto calculará automáticamente duración y pérdidas)
        registro.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Registro guardado exitosamente',
            'registro_id': registro.id,
            'duracion_horas': float(registro.duracion_horas) if registro.duracion_horas else None,
            'duracion_dias': float(registro.duracion_dias) if registro.duracion_dias else None,
            'perdida_uf': float(registro.perdida_uf) if registro.perdida_uf else None,
            'perdida_clp': float(registro.perdida_clp) if registro.perdida_clp else None,
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def api_listar_inactividades(request):
    """
    API para listar registros de inactividad con filtros.
    """
    try:
        # Obtener filtros
        centro_id = request.GET.get('centro_id') or request.GET.get('centro')
        fecha_desde = request.GET.get('fecha_desde')
        fecha_hasta = request.GET.get('fecha_hasta')
        estado = request.GET.get('estado')  # 'activa', 'resuelta', 'todas'
        
        # Construir query
        queryset = RegistroInactividad.objects.select_related(
            'costo_sistema__centro',
            'sensor'
        ).all()
        
        # Aplicar filtros
        if centro_id:
            queryset = queryset.filter(costo_sistema__centro_id=centro_id)
        
        if fecha_desde:
            queryset = queryset.filter(fecha_inicio__gte=fecha_desde)
        
        if fecha_hasta:
            queryset = queryset.filter(fecha_inicio__lte=fecha_hasta)
        
        if estado == 'activa':
            queryset = queryset.filter(fecha_fin__isnull=True)
        elif estado == 'resuelta':
            queryset = queryset.filter(resuelto=True)
        
        # Ordenar
        queryset = queryset.order_by('-fecha_inicio')
        
        # Serializar
        registros = []
        for reg in queryset:
            registros.append({
                'id': reg.id,
                'centro': reg.costo_sistema.centro.nombre,
                'sistema': reg.costo_sistema.sistema,
                'sensor': reg.sensor.equipo if reg.sensor else 'N/A',
                'fecha_inicio': reg.fecha_inicio.isoformat(),
                'fecha_fin': reg.fecha_fin.isoformat() if reg.fecha_fin else None,
                'duracion_horas': float(reg.duracion_horas) if reg.duracion_horas else None,
                'duracion_dias': float(reg.duracion_dias) if reg.duracion_dias else None,
                'perdida_uf': float(reg.perdida_uf) if reg.perdida_uf else None,
                'perdida_clp': float(reg.perdida_clp) if reg.perdida_clp else None,
                'motivo': reg.get_motivo_display(),
                'descripcion': reg.descripcion,
                'resuelto': reg.resuelto,
                'esta_activa': reg.esta_activa,
                'incluir_en_reporte': reg.incluir_en_reporte,
            })
        
        return JsonResponse({
            'success': True,
            'registros': registros,
            'total': len(registros)
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["POST"])
def api_eliminar_inactividad(request, pk):
    """
    API para eliminar un registro de inactividad.
    """
    try:
        registro = get_object_or_404(RegistroInactividad, pk=pk)
        registro.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Registro eliminado exitosamente'
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["POST"])
def api_resolver_inactividad(request, pk):
    """
    API para marcar una inactividad como resuelta y establecer fecha de fin.
    """
    try:
        data = json.loads(request.body)
        registro = get_object_or_404(RegistroInactividad, pk=pk)
        
        # Establecer fecha de fin si no existe
        if not registro.fecha_fin:
            if data.get('fecha_fin'):
                registro.fecha_fin = datetime.fromisoformat(data['fecha_fin'].replace('Z', '+00:00'))
            else:
                registro.fecha_fin = timezone.now()
        
        # Marcar como resuelto
        registro.resuelto = True
        
        # Guardar (recalculará pérdidas)
        registro.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Inactividad marcada como resuelta',
            'duracion_horas': float(registro.duracion_horas) if registro.duracion_horas else None,
            'perdida_uf': float(registro.perdida_uf) if registro.perdida_uf else None,
            'perdida_clp': float(registro.perdida_clp) if registro.perdida_clp else None,
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def api_estadisticas_perdidas(request):
    """
    API para obtener estadísticas consolidadas de pérdidas económicas.
    """
    try:
        # Filtros
        centro_id = request.GET.get('centro_id')
        fecha_desde = request.GET.get('fecha_desde')
        fecha_hasta = request.GET.get('fecha_hasta')
        
        # Query base
        queryset = RegistroInactividad.objects.all()
        
        if centro_id:
            queryset = queryset.filter(costo_sistema__centro_id=centro_id)
        
        if fecha_desde:
            queryset = queryset.filter(fecha_inicio__gte=fecha_desde)
        
        if fecha_hasta:
            queryset = queryset.filter(fecha_inicio__lte=fecha_hasta)
        
        # Estadísticas generales
        stats = queryset.aggregate(
            total_registros=Count('id'),
            total_perdida_uf=Sum('perdida_uf'),
            total_perdida_clp=Sum('perdida_clp'),
            total_horas=Sum('duracion_horas'),
            promedio_duracion=Avg('duracion_horas')
        )
        
        # Pérdidas por centro
        perdidas_por_centro = queryset.values(
            'costo_sistema__centro__nombre'
        ).annotate(
            total_uf=Sum('perdida_uf'),
            total_clp=Sum('perdida_clp'),
            cantidad=Count('id')
        ).order_by('-total_uf')
        
        # Pérdidas por sistema
        perdidas_por_sistema = queryset.values(
            'costo_sistema__sistema'
        ).annotate(
            total_uf=Sum('perdida_uf'),
            total_clp=Sum('perdida_clp'),
            cantidad=Count('id')
        ).order_by('-total_uf')[:10]
        
        # Pérdidas por motivo
        perdidas_por_motivo = queryset.values(
            'motivo'
        ).annotate(
            total_uf=Sum('perdida_uf'),
            cantidad=Count('id')
        ).order_by('-total_uf')
        
        return JsonResponse({
            'success': True,
            'estadisticas': {
                'total_registros': stats['total_registros'],
                'total_perdida_uf': float(stats['total_perdida_uf'] or 0),
                'total_perdida_clp': float(stats['total_perdida_clp'] or 0),
                'total_horas': float(stats['total_horas'] or 0),
                'promedio_duracion': float(stats['promedio_duracion'] or 0),
            },
            'por_centro': [
                {
                    'centro': item['costo_sistema__centro__nombre'],
                    'total_uf': float(item['total_uf'] or 0),
                    'total_clp': float(item['total_clp'] or 0),
                    'cantidad': item['cantidad']
                }
                for item in perdidas_por_centro
            ],
            'por_sistema': [
                {
                    'sistema': item['costo_sistema__sistema'],
                    'total_uf': float(item['total_uf'] or 0),
                    'total_clp': float(item['total_clp'] or 0),
                    'cantidad': item['cantidad']
                }
                for item in perdidas_por_sistema
            ],
            'por_motivo': [
                {
                    'motivo': item['motivo'],
                    'total_uf': float(item['total_uf'] or 0),
                    'cantidad': item['cantidad']
                }
                for item in perdidas_por_motivo
            ]
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def generar_pdf_perdidas(request):
    """
    Genera un PDF con el reporte de pérdidas económicas.
    """
    # TODO: Implementar generación de PDF
    # Similar a otros reportes existentes en el sistema
    return HttpResponse("Generación de PDF en desarrollo", content_type="text/plain")
