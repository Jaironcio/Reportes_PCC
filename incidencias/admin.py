# incidencias/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import Centro, Operario, Incidencia, ControlDiario, ReporteCamaras, CostoSistema, RegistroInactividad

# Personalizar el admin de Centro
@admin.register(Centro)
class CentroAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'slug')
    search_fields = ('nombre', 'slug')

# Personalizar el admin de Operario
@admin.register(Operario)
class OperarioAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'cargo', 'centro', 'telefono')
    list_filter = ('centro', 'cargo')
    search_fields = ('nombre', 'cargo')

# Personalizar el admin de Incidencia
@admin.register(Incidencia)
class IncidenciaAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_centro_nombre', 'fecha_hora', 'turno', 'modulo', 'tipo_incidencia', 'riesgo_peces')
    list_filter = ('centro', 'turno', 'tipo_incidencia', 'riesgo_peces', 'riesgo_personas')
    search_fields = ('centro__nombre', 'modulo', 'estanque', 'observacion', 'tipo_incidencia_normalizada')
    date_hierarchy = 'fecha_hora'
    
    def get_centro_nombre(self, obj):
        return obj.centro.nombre if obj.centro else "Sin centro"
    get_centro_nombre.short_description = 'Centro'
    get_centro_nombre.admin_order_field = 'centro'

# Personalizar el admin de ControlDiario
@admin.register(ControlDiario)
class ControlDiarioAdmin(admin.ModelAdmin):
    list_display = ('fecha', 'centro', 'modulo', 'dia', 'responsable', 'promedio_temp', 'promedio_ph', 'promedio_oxigeno')
    list_filter = ('centro', 'modulo', 'fecha')
    search_fields = ('responsable', 'dia')
    date_hierarchy = 'fecha'

# Personalizar el admin de ReporteCamaras
@admin.register(ReporteCamaras)
class ReporteCamarasAdmin(admin.ModelAdmin):
    list_display = ('fecha', 'turno', 'responsable', 'get_resumen_incidencias', 'creado_en')
    list_filter = ('turno', 'fecha', 'rio_pescado_tiene_incidencias', 'collin_tiene_incidencias', 'lican_tiene_incidencias', 'trafun_tiene_incidencias')
    search_fields = ('responsable', 'rio_pescado_descripcion', 'collin_descripcion', 'lican_descripcion', 'trafun_descripcion')
    date_hierarchy = 'fecha'
    
    def get_resumen_incidencias(self, obj):
        incidencias = []
        if obj.rio_pescado_tiene_incidencias:
            incidencias.append('Río Pescado')
        if obj.collin_tiene_incidencias:
            incidencias.append('Collín')
        if obj.lican_tiene_incidencias:
            incidencias.append('Lican')
        if obj.trafun_tiene_incidencias:
            incidencias.append('Trafún')
        return ', '.join(incidencias) if incidencias else 'Sin incidencias'
    get_resumen_incidencias.short_description = 'Centros con Incidencias'


# ============================================================================
# ADMIN PARA SISTEMA DE PÉRDIDAS ECONÓMICAS
# ============================================================================

@admin.register(CostoSistema)
class CostoSistemaAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'centro',
        'sistema',
        'get_monto_mensual',
        'get_costo_diario',
        'get_costo_hora',
        'fecha_inicio',
        'fecha_termino',
        'get_estado_badge',
    )
    list_filter = ('centro', 'activo', 'fecha_inicio', 'fecha_termino')
    search_fields = ('sistema', 'centro__nombre')
    date_hierarchy = 'fecha_inicio'
    readonly_fields = (
        'costo_hora_uf',
        'costo_hora_clp',
        'creado_en',
        'actualizado_en',
        'get_info_contrato',
    )
    
    fieldsets = (
        ('Identificación', {
            'fields': ('centro', 'sistema', 'activo')
        }),
        ('Costos Mensuales', {
            'fields': ('monto_mensual_uf', 'monto_mensual_clp'),
            'description': 'Costo mensual del sistema/módulo'
        }),
        ('Costos Diarios', {
            'fields': ('costo_diario_uf', 'costo_diario_clp'),
            'description': 'Costo por día (24 horas)'
        }),
        ('Costos por Hora (Calculado Automáticamente)', {
            'fields': ('costo_hora_uf', 'costo_hora_clp'),
            'classes': ('collapse',),
            'description': 'Se calcula automáticamente al guardar'
        }),
        ('Información del Contrato', {
            'fields': (
                'plazo_contrato',
                'fecha_inicio',
                'fecha_termino',
                'cantidad_sensores',
                'get_info_contrato',
            )
        }),
        ('Totales del Contrato', {
            'fields': ('costo_total_uf', 'costo_total_clp'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('creado_en', 'actualizado_en'),
            'classes': ('collapse',)
        }),
    )
    
    def get_monto_mensual(self, obj):
        return format_html(
            '<strong>{} UF</strong><br><small>${:,.0f} CLP</small>',
            obj.monto_mensual_uf,
            obj.monto_mensual_clp
        )
    get_monto_mensual.short_description = 'Costo Mensual'
    
    def get_costo_diario(self, obj):
        return format_html(
            '<span style="color: #3498db;">{} UF/día</span><br><small>${:,.0f} CLP/día</small>',
            obj.costo_diario_uf,
            obj.costo_diario_clp
        )
    get_costo_diario.short_description = 'Costo Diario'
    
    def get_costo_hora(self, obj):
        if obj.costo_hora_uf and obj.costo_hora_clp:
            return format_html(
                '<span style="color: #e67e22;">{:.6f} UF/h</span><br><small>${:,.0f} CLP/h</small>',
                obj.costo_hora_uf,
                obj.costo_hora_clp
            )
        return '-'
    get_costo_hora.short_description = 'Costo por Hora'
    
    def get_estado_badge(self, obj):
        if obj.activo:
            return format_html(
                '<span style="background-color: #27ae60; color: white; padding: 3px 10px; border-radius: 3px;">✓ Activo</span>'
            )
        return format_html(
            '<span style="background-color: #95a5a6; color: white; padding: 3px 10px; border-radius: 3px;">Inactivo</span>'
        )
    get_estado_badge.short_description = 'Estado'
    
    def get_info_contrato(self, obj):
        from datetime import date
        dias_restantes = (obj.fecha_termino - date.today()).days if obj.fecha_termino else 0
        
        html = f'''
        <div style="background: #ecf0f1; padding: 15px; border-radius: 5px;">
            <h3 style="margin-top: 0;">Información del Contrato</h3>
            <table style="width: 100%;">
                <tr>
                    <td><strong>Plazo:</strong></td>
                    <td>{obj.plazo_contrato}</td>
                </tr>
                <tr>
                    <td><strong>Inicio:</strong></td>
                    <td>{obj.fecha_inicio.strftime("%d/%m/%Y")}</td>
                </tr>
                <tr>
                    <td><strong>Término:</strong></td>
                    <td>{obj.fecha_termino.strftime("%d/%m/%Y")}</td>
                </tr>
                <tr>
                    <td><strong>Días restantes:</strong></td>
                    <td><span style="color: {'#e74c3c' if dias_restantes < 90 else '#27ae60'};">{dias_restantes} días</span></td>
                </tr>
                <tr>
                    <td><strong>Costo Total Contrato:</strong></td>
                    <td><strong>{obj.costo_total_uf} UF</strong> (${obj.costo_total_clp:,.0f} CLP)</td>
                </tr>
            </table>
        </div>
        '''
        return format_html(html)
    get_info_contrato.short_description = 'Resumen del Contrato'


@admin.register(RegistroInactividad)
class RegistroInactividadAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'get_centro',
        'get_sistema',
        'get_sensor',
        'fecha_inicio',
        'get_duracion',
        'get_perdida',
        'get_estado_badge',
        'get_proveedor_badge',
    )
    list_filter = (
        'costo_sistema__centro',
        'motivo',
        'resuelto',
        'contacto_proveedor',
        'incluir_en_reporte',
        'fecha_inicio',
    )
    search_fields = (
        'costo_sistema__centro__nombre',
        'costo_sistema__sistema',
        'sensor__equipo',
        'descripcion',
        'responsable',
    )
    date_hierarchy = 'fecha_inicio'
    readonly_fields = (
        'duracion_horas',
        'duracion_dias',
        'perdida_uf',
        'perdida_clp',
        'creado_en',
        'actualizado_en',
        'get_calculo_detallado',
    )
    
    fieldsets = (
        ('Sistema Afectado', {
            'fields': ('costo_sistema', 'sensor')
        }),
        ('Período de Inactividad', {
            'fields': ('fecha_inicio', 'fecha_fin'),
            'description': 'Deje fecha_fin vacía si la falla aún está activa'
        }),
        ('Duración y Pérdida (Calculado Automáticamente)', {
            'fields': (
                'duracion_horas',
                'duracion_dias',
                'perdida_uf',
                'perdida_clp',
                'get_calculo_detallado',
            ),
            'classes': ('collapse',)
        }),
        ('Detalles de la Falla', {
            'fields': ('motivo', 'descripcion', 'responsable')
        }),
        ('Seguimiento con Proveedor', {
            'fields': (
                'contacto_proveedor',
                'fecha_contacto',
                'respuesta_proveedor',
                'resuelto',
            )
        }),
        ('Para Reporte de Descuentos', {
            'fields': ('incluir_en_reporte', 'observaciones_reporte')
        }),
        ('Metadata', {
            'fields': ('creado_en', 'actualizado_en'),
            'classes': ('collapse',)
        }),
    )
    
    def get_centro(self, obj):
        return obj.costo_sistema.centro.nombre
    get_centro.short_description = 'Centro'
    get_centro.admin_order_field = 'costo_sistema__centro__nombre'
    
    def get_sistema(self, obj):
        return format_html(
            '<strong>{}</strong><br><small>{} UF/mes</small>',
            obj.costo_sistema.sistema,
            obj.costo_sistema.monto_mensual_uf
        )
    get_sistema.short_description = 'Sistema'
    
    def get_sensor(self, obj):
        if obj.sensor:
            return format_html(
                '<span style="color: #3498db;">{}</span>',
                obj.sensor.equipo
            )
        return format_html('<span style="color: #95a5a6;">Todo el sistema</span>')
    get_sensor.short_description = 'Sensor'
    
    def get_duracion(self, obj):
        if obj.duracion_dias:
            return format_html(
                '<strong>{:.1f} días</strong><br><small>({:.1f} horas)</small>',
                obj.duracion_dias,
                obj.duracion_horas
            )
        return format_html('<span style="color: #e74c3c;">⏱ En curso</span>')
    get_duracion.short_description = 'Duración'
    
    def get_perdida(self, obj):
        if obj.perdida_uf and obj.perdida_clp:
            return format_html(
                '<strong style="color: #e74c3c;">{:.4f} UF</strong><br><small>${:,.0f} CLP</small>',
                obj.perdida_uf,
                obj.perdida_clp
            )
        return '-'
    get_perdida.short_description = 'Pérdida Económica'
    
    def get_estado_badge(self, obj):
        if obj.esta_activa:
            return format_html(
                '<span style="background-color: #e74c3c; color: white; padding: 3px 10px; border-radius: 3px;">⚠ Activa</span>'
            )
        elif obj.resuelto:
            return format_html(
                '<span style="background-color: #27ae60; color: white; padding: 3px 10px; border-radius: 3px;">✓ Resuelta</span>'
            )
        return format_html(
            '<span style="background-color: #f39c12; color: white; padding: 3px 10px; border-radius: 3px;">Finalizada</span>'
        )
    get_estado_badge.short_description = 'Estado'
    
    def get_proveedor_badge(self, obj):
        if obj.contacto_proveedor:
            return format_html(
                '<span style="background-color: #3498db; color: white; padding: 3px 10px; border-radius: 3px;">📞 Contactado</span>'
            )
        return format_html(
            '<span style="background-color: #95a5a6; color: white; padding: 3px 10px; border-radius: 3px;">Sin contacto</span>'
        )
    get_proveedor_badge.short_description = 'Proveedor'
    
    def get_calculo_detallado(self, obj):
        if not obj.duracion_horas:
            return format_html('<p style="color: #e74c3c;">⚠ Falla aún activa - No se puede calcular pérdida</p>')
        
        html = f'''
        <div style="background: #fff3cd; border: 2px solid #ffc107; padding: 15px; border-radius: 5px;">
            <h3 style="margin-top: 0; color: #856404;">💰 Cálculo de Pérdida Económica</h3>
            
            <table style="width: 100%; margin-bottom: 15px;">
                <tr style="background: #f8f9fa;">
                    <td colspan="2"><strong>Datos del Sistema:</strong></td>
                </tr>
                <tr>
                    <td style="padding: 5px;"><strong>Costo por hora:</strong></td>
                    <td style="padding: 5px;">{obj.costo_sistema.costo_hora_uf:.6f} UF/h (${obj.costo_sistema.costo_hora_clp:,.0f} CLP/h)</td>
                </tr>
                <tr>
                    <td style="padding: 5px;"><strong>Duración:</strong></td>
                    <td style="padding: 5px;">{obj.duracion_horas:.2f} horas ({obj.duracion_dias:.2f} días)</td>
                </tr>
            </table>
            
            <table style="width: 100%; background: white; border: 1px solid #dee2e6;">
                <tr style="background: #e74c3c; color: white;">
                    <td style="padding: 10px;"><strong>Pérdida Total en UF:</strong></td>
                    <td style="padding: 10px; text-align: right;"><strong>{obj.perdida_uf:.4f} UF</strong></td>
                </tr>
                <tr style="background: #c0392b; color: white;">
                    <td style="padding: 10px;"><strong>Pérdida Total en CLP:</strong></td>
                    <td style="padding: 10px; text-align: right;"><strong>${obj.perdida_clp:,.0f}</strong></td>
                </tr>
            </table>
            
            <p style="margin-top: 15px; color: #856404;">
                <strong>Fórmula:</strong> Pérdida = Costo por Hora × Duración en Horas
            </p>
            
            {'<p style="background: #d4edda; padding: 10px; border-radius: 3px; color: #155724;"><strong>✓ Incluido en reporte de descuentos</strong></p>' if obj.incluir_en_reporte else '<p style="background: #f8d7da; padding: 10px; border-radius: 3px; color: #721c24;"><strong>✗ No incluido en reporte</strong></p>'}
        </div>
        '''
        return format_html(html)
    get_calculo_detallado.short_description = 'Detalle del Cálculo'
    
    actions = ['marcar_como_resueltas', 'incluir_en_reporte', 'excluir_de_reporte']
    
    def marcar_como_resueltas(self, request, queryset):
        from django.utils import timezone
        count = 0
        for obj in queryset:
            if not obj.fecha_fin:
                obj.fecha_fin = timezone.now()
            obj.resuelto = True
            obj.save()
            count += 1
        self.message_user(request, f'{count} inactividad(es) marcada(s) como resuelta(s).')
    marcar_como_resueltas.short_description = 'Marcar como resueltas'
    
    def incluir_en_reporte(self, request, queryset):
        count = queryset.update(incluir_en_reporte=True)
        self.message_user(request, f'{count} registro(s) incluido(s) en reporte de descuentos.')
    incluir_en_reporte.short_description = 'Incluir en reporte de descuentos'
    
    def excluir_de_reporte(self, request, queryset):
        count = queryset.update(incluir_en_reporte=False)
        self.message_user(request, f'{count} registro(s) excluido(s) del reporte de descuentos.')
    excluir_de_reporte.short_description = 'Excluir del reporte de descuentos'