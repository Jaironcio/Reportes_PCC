# incidencias/models.py
from django.db import models
from django.utils.text import slugify

class Centro(models.Model):
    id = models.CharField(max_length=50, primary_key=True)  # ID es string
    nombre = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)

    # (Esto crea automáticamente el slug, ej: "Santa Juana" -> "santa-juana")
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nombre)
        if not self.id:
            self.id = self.slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre

# --- NUEVO MODELO: OPERARIO ---
# Vamos a guardar los operarios en la base de datos
class Operario(models.Model):
    # Usamos un ID numérico simple
    id = models.PositiveIntegerField(primary_key=True)
    nombre = models.CharField(max_length=200)
    cargo = models.CharField(max_length=200)
    telefono = models.CharField(max_length=50, blank=True)
    
    # IMPORTANTE: Un operario pertenece a un Centro
    # related_name='operarios' nos permite buscar operarios desde un centro
    centro = models.ForeignKey(Centro, on_delete=models.CASCADE, related_name='operarios')

    def __str__(self):
        return f"{self.nombre} ({self.centro.nombre})"

# --- NUEVO MODELO: INCIDENCIA ---
# La tabla principal que guarda todo el formulario
class Incidencia(models.Model):
    # --- Sección 1: Info Básica ---
    fecha_hora = models.DateTimeField()
    turno = models.CharField(max_length=50)
    centro = models.ForeignKey(Centro, on_delete=models.SET_NULL, null=True, blank=True)
    
    # --- Sección 2: Tipo ---
    tipo_incidencia = models.CharField(max_length=50, blank=True) # 'modulos' o 'sensores'

    # --- Sección 3: Módulos ---
    modulo = models.CharField(max_length=100, blank=True)
    estanque = models.CharField(max_length=100, blank=True)
    
    # Checkboxes de parámetros (guardamos una lista simple)
    parametros_afectados = models.CharField(max_length=500, blank=True) # ej: "oxigeno,temperatura"

    # Valores (los guardamos como texto para aceptar la coma ',')
    oxigeno_nivel = models.CharField(max_length=50, blank=True) # 'alta' o 'baja'
    oxigeno_valor = models.CharField(max_length=50, blank=True) # '12,2'
    
    temperatura_nivel = models.CharField(max_length=50, blank=True)
    temperatura_valor = models.CharField(max_length=50, blank=True)

    conductividad_nivel = models.CharField(max_length=50, blank=True)
    # (Conductividad no tiene valor)

    turbidez_nivel = models.CharField(max_length=50, blank=True)
    turbidez_valor = models.CharField(max_length=50, blank=True)

    # --- Sección 4: Sensores (simplificado) ---
    sistema_sensor = models.CharField(max_length=100, blank=True)
    sensor_detectado = models.CharField(max_length=100, blank=True)
    sensor_nivel = models.CharField(max_length=100, blank=True)
    sensor_valor = models.CharField(max_length=50, blank=True)

    # --- Sección 4b: Falla de Plataforma ---
    plataforma = models.CharField(max_length=50, blank=True)  # 'INNOVEX' o 'SINPLANT'
    sistema_fallando = models.CharField(max_length=200, blank=True)
    tiempo_fuera_servicio = models.IntegerField(null=True, blank=True)  # minutos
    contacto_proveedor = models.BooleanField(default=False)
    razon_caida = models.TextField(blank=True)

    # --- Sección 5: Riesgos ---
    tiempo_resolucion = models.IntegerField(null=True, blank=True)
    riesgo_peces = models.BooleanField(default=False)
    perdida_economica = models.BooleanField(default=False)
    riesgo_personas = models.BooleanField(default=False)
    observacion = models.TextField(blank=True)

    # --- Sección 6: Contacto ---
    operario_contacto = models.ForeignKey(Operario, on_delete=models.SET_NULL, null=True, blank=True)
    tipo_incidencia_normalizada = models.CharField(max_length=100, blank=True)

    # Esto es para que se vea bien en el Admin
    def __str__(self):
        centro_nombre = self.centro.nombre if self.centro else "Centro no especificado"
        fecha_str = self.fecha_hora.strftime('%Y-%m-%d %H:%M') if self.fecha_hora else "Fecha no especificada"
        return f"Incidencia en {centro_nombre} - {fecha_str}"

# --- NUEVO MODELO: CONTROL DIARIO ---
# Tabla para registrar parámetros diarios (Temp, pH, Oxígeno) por hora
class ControlDiario(models.Model):
    centro = models.ForeignKey(Centro, on_delete=models.CASCADE, related_name='controles_diarios')
    fecha = models.DateField()
    anio = models.IntegerField()
    semana = models.IntegerField()
    dia = models.CharField(max_length=20)  # Lunes, Martes, etc.
    responsable = models.CharField(max_length=200)
    modulo = models.CharField(max_length=100, default='Hatchery')  # Hatchery, Fry, Smolt, etc.
    
    # Registros por hora (00:00, 04:00, 08:00, 12:00, 16:00, 20:00)
    hora_00_temp = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    hora_00_ph = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    hora_00_oxigeno = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    hora_04_temp = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    hora_04_ph = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    hora_04_oxigeno = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    hora_08_temp = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    hora_08_ph = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    hora_08_oxigeno = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    hora_12_temp = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    hora_12_ph = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    hora_12_oxigeno = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    hora_16_temp = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    hora_16_ph = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    hora_16_oxigeno = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    hora_20_temp = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    hora_20_ph = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    hora_20_oxigeno = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    # Promedios (se calculan automáticamente)
    promedio_temp = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    promedio_ph = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    promedio_oxigeno = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    # Metadata
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-fecha', '-creado_en']
        unique_together = ['centro', 'fecha', 'modulo']
    
    def calcular_promedios(self):
        """Calcula los promedios de temperatura, pH y oxígeno"""
        horas = ['00', '04', '08', '12', '16', '20']
        
        # Calcular promedio temperatura
        temps = [getattr(self, f'hora_{h}_temp') for h in horas if getattr(self, f'hora_{h}_temp') is not None]
        self.promedio_temp = sum(temps) / len(temps) if temps else None
        
        # Calcular promedio pH
        phs = [getattr(self, f'hora_{h}_ph') for h in horas if getattr(self, f'hora_{h}_ph') is not None]
        self.promedio_ph = sum(phs) / len(phs) if phs else None
        
        # Calcular promedio oxígeno
        oxigenos = [getattr(self, f'hora_{h}_oxigeno') for h in horas if getattr(self, f'hora_{h}_oxigeno') is not None]
        self.promedio_oxigeno = sum(oxigenos) / len(oxigenos) if oxigenos else None
    
    def save(self, *args, **kwargs):
        # Calcular promedios antes de guardar
        self.calcular_promedios()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Control Diario - {self.centro.nombre} - {self.fecha} - {self.modulo}"

# --- NUEVO MODELO: REPORTE DE CÁMARAS ---
# Tabla para registrar el estado diario de las cámaras de los 4 centros
class ReporteCamaras(models.Model):
    fecha = models.DateField()
    turno = models.CharField(max_length=20)  # Mañana, Tarde, Noche
    responsable = models.CharField(max_length=200)
    
    # Río Pescado
    rio_pescado_tiene_incidencias = models.BooleanField(default=False)
    rio_pescado_descripcion = models.TextField(default='No se detectaron novedades durante el monitoreo')
    
    # Collín
    collin_tiene_incidencias = models.BooleanField(default=False)
    collin_descripcion = models.TextField(default='No se detectaron novedades durante el monitoreo')
    
    # Lican
    lican_tiene_incidencias = models.BooleanField(default=False)
    lican_descripcion = models.TextField(default='No se detectaron novedades durante el monitoreo')
    
    # Trafún
    trafun_tiene_incidencias = models.BooleanField(default=False)
    trafun_descripcion = models.TextField(default='No se detectaron novedades durante el monitoreo')
    
    # Metadata
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-fecha', '-creado_en']
        unique_together = ['fecha', 'turno']
        verbose_name = 'Reporte de Cámaras'
        verbose_name_plural = 'Reportes de Cámaras'
    
    def __str__(self):
        return f"Reporte Cámaras - {self.fecha} - {self.turno}"


# --- MODELOS PARA SISTEMA DE SENSORES (IDEAL CONTROL) ---

class SensorConfig(models.Model):
    """Configuración de sensores por centro - basado en Alertas_IdealControl.xlsm"""
    centro = models.ForeignKey(Centro, on_delete=models.CASCADE, related_name='sensores')
    sistema = models.CharField(max_length=100)  # MEE, Efluente, Turbidez y CO2, etc.
    equipo = models.CharField(max_length=200)  # Flujómetro pozo 1, NTU Módulo 200, etc.
    tipo_medicion = models.CharField(max_length=100)  # CAUDAL, NIVEL, NTU, CO2, etc.
    limite_min = models.CharField(max_length=50, blank=True)
    limite_max = models.CharField(max_length=50, blank=True)
    activo = models.BooleanField(default=True)
    orden = models.IntegerField(default=0)  # Para ordenar sensores en el formulario
    
    class Meta:
        ordering = ['centro', 'sistema', 'orden', 'equipo']
        unique_together = ['centro', 'sistema', 'equipo']
        verbose_name = 'Configuración de Sensor'
        verbose_name_plural = 'Configuraciones de Sensores'
    
    def __str__(self):
        return f"{self.centro.nombre} - {self.sistema} - {self.equipo}"


class MonitoreoSensores(models.Model):
    """Registro diario de monitoreo de sensores por turno"""
    ESTADO_CHOICES = [
        ('NORMAL', 'Normal'),
        ('ALTO', 'Alto - Sobre límite'),
        ('BAJO', 'Bajo - Bajo límite'),
        ('N/A', 'No aplica')
    ]
    
    TURNO_CHOICES = [
        ('MAÑANA', 'Mañana'),
        ('TARDE', 'Tarde'),
        ('NOCHE', 'Noche')
    ]
    
    fecha = models.DateField()
    hora_inicio = models.TimeField(null=True, blank=True, help_text="Hora de inicio de la incidencia")
    turno = models.CharField(max_length=20, choices=TURNO_CHOICES)
    centro = models.ForeignKey(Centro, on_delete=models.CASCADE)
    sensor = models.ForeignKey(SensorConfig, on_delete=models.CASCADE)
    
    # Estado del sensor en este turno
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='NORMAL')
    
    # Observación específica para este sensor/turno
    observacion = models.TextField(blank=True)
    
    # Metadata
    responsable = models.CharField(max_length=100)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-fecha', 'turno', 'centro', 'sensor']
        unique_together = ['fecha', 'turno', 'centro', 'sensor']
        verbose_name = 'Monitoreo de Sensor'
        verbose_name_plural = 'Monitoreos de Sensores'
    
    def __str__(self):
        return f"{self.fecha} - {self.turno} - {self.centro.nombre} - {self.sensor.equipo}: {self.estado}"


class ReportePlataforma(models.Model):
    """Registro de fallas de plataformas INNOVEX, SINPLANT e IDEAL CONTROL"""
    PLATAFORMA_CHOICES = [
        ('INNOVEX', 'INNOVEX'),
        ('SINPLANT', 'SINPLANT'),
        ('IDEAL CONTROL', 'IDEAL CONTROL')
    ]
    
    TURNO_CHOICES = [
        ('Mañana', 'Mañana'),
        ('Tarde', 'Tarde'),
        ('Noche', 'Noche')
    ]
    
    CONTACTO_PROVEEDOR_CHOICES = [
        ('no', 'No se contactó'),
        ('si', 'Sí, con respuesta'),
        ('sin_respuesta', 'Sí, sin respuesta')
    ]
    
    UNIDAD_TIEMPO_CHOICES = [
        ('minutos', 'Minutos'),
        ('dias', 'Días')
    ]
    
    # Información básica
    fecha_hora = models.DateTimeField()
    turno = models.CharField(max_length=20, choices=TURNO_CHOICES)
    centro = models.ForeignKey(Centro, on_delete=models.CASCADE, related_name='reportes_plataforma')
    
    # Detalles de la falla
    plataforma = models.CharField(max_length=20, choices=PLATAFORMA_CHOICES)
    sistema_fallando = models.CharField(max_length=200)
    tiempo_fuera_servicio = models.IntegerField(help_text='Duración del tiempo fuera de servicio')
    unidad_tiempo = models.CharField(max_length=10, choices=UNIDAD_TIEMPO_CHOICES, default='minutos')
    contacto_proveedor = models.CharField(max_length=20, choices=CONTACTO_PROVEEDOR_CHOICES, default='no')
    razon_caida = models.TextField()
    
    # Evaluación de impacto
    riesgo_peces = models.BooleanField(default=False)
    perdida_economica = models.BooleanField(default=False)
    
    # Información adicional
    responsable = models.CharField(max_length=200)
    observacion = models.TextField(blank=True)
    
    # Metadata
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-fecha_hora', '-creado_en']
        verbose_name = 'Reporte de Plataforma'
        verbose_name_plural = 'Reportes de Plataformas'
    
    def __str__(self):
        return f"{self.plataforma} - {self.centro.nombre} - {self.fecha_hora.strftime('%Y-%m-%d %H:%M')}"


# --- MODELOS PARA CÁLCULO DE COSTOS Y PÉRDIDAS ECONÓMICAS ---

class CostoSistema(models.Model):
    """
    Almacena los costos mensuales de cada sistema/módulo de sensores por piscicultura.
    Basado en el archivo KPI_REDUCCION_COSTOS_SENSORES.xlsx
    """
    centro = models.ForeignKey(Centro, on_delete=models.CASCADE, related_name='costos_sistemas')
    sistema = models.CharField(max_length=200, help_text='Nombre del sistema (ej: IDEAL CLOUD, EFLUENTE SMA, CO2 Y TURBIDEZ)')
    
    # Costos mensuales
    monto_mensual_uf = models.DecimalField(max_digits=10, decimal_places=2, help_text='Costo mensual en UF')
    monto_mensual_clp = models.DecimalField(max_digits=15, decimal_places=2, help_text='Costo mensual en CLP')
    
    # Costos diarios (calculados automáticamente)
    costo_diario_uf = models.DecimalField(max_digits=10, decimal_places=6, help_text='Costo por día (24h) en UF')
    costo_diario_clp = models.DecimalField(max_digits=15, decimal_places=2, help_text='Costo por día (24h) en CLP')
    
    # Costos por hora (calculados automáticamente)
    costo_hora_uf = models.DecimalField(max_digits=10, decimal_places=6, help_text='Costo por hora en UF', null=True, blank=True)
    costo_hora_clp = models.DecimalField(max_digits=15, decimal_places=2, help_text='Costo por hora en CLP', null=True, blank=True)
    
    # Información del contrato
    plazo_contrato = models.CharField(max_length=50, default='36 MESES')
    fecha_inicio = models.DateField()
    fecha_termino = models.DateField()
    cantidad_sensores = models.IntegerField(null=True, blank=True, help_text='Cantidad de sensores en este sistema')
    
    # Totales del contrato
    costo_total_uf = models.DecimalField(max_digits=10, decimal_places=2, help_text='Costo total del contrato en UF')
    costo_total_clp = models.DecimalField(max_digits=15, decimal_places=2, help_text='Costo total del contrato en CLP')
    
    # Metadata
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['centro', 'sistema']
        unique_together = ['centro', 'sistema']
        verbose_name = 'Costo de Sistema'
        verbose_name_plural = 'Costos de Sistemas'
    
    def calcular_costos_derivados(self):
        """Calcula automáticamente costos diarios y por hora desde el monto mensual UF"""
        from decimal import Decimal
        if self.monto_mensual_uf:
            self.costo_diario_uf = self.monto_mensual_uf / Decimal('30')
            self.costo_hora_uf = self.costo_diario_uf / Decimal('24')
    
    def save(self, *args, **kwargs):
        # Calcular costos derivados antes de guardar
        self.calcular_costos_derivados()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.centro.nombre} - {self.sistema} ({self.monto_mensual_uf} UF/mes)"


class RegistroInactividad(models.Model):
    """
    Registra períodos de inactividad de sensores para calcular pérdidas económicas.
    Permite documentar cuando un sensor está fuera de servicio para solicitar rebajas.
    """
    MOTIVO_CHOICES = [
        ('SENSOR_APAGADO', 'Sensor apagado'),
        ('SENSOR_MAL_ESTADO', 'Sensor en mal estado'),
        ('NO_SUBE_DATOS', 'No sube datos a la plataforma'),
        ('FALLA_COMUNICACION', 'Falla de comunicación'),
        ('MANTENIMIENTO', 'En mantenimiento'),
        ('OTRO', 'Otro motivo')
    ]
    
    # Relación con el sistema de costos
    costo_sistema = models.ForeignKey(CostoSistema, on_delete=models.CASCADE, related_name='registros_inactividad')
    sensor = models.ForeignKey(SensorConfig, on_delete=models.CASCADE, related_name='registros_inactividad', 
                               null=True, blank=True, help_text='Sensor específico afectado (opcional)')
    
    # Período de inactividad
    fecha_inicio = models.DateTimeField(help_text='Fecha y hora de inicio de la falla')
    fecha_fin = models.DateTimeField(null=True, blank=True, help_text='Fecha y hora de fin de la falla (dejar vacío si aún está activa)')
    
    # Duración calculada
    duracion_horas = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, 
                                         help_text='Duración total en horas')
    duracion_dias = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                        help_text='Duración total en días')
    
    # Pérdida económica calculada
    perdida_uf = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True,
                                     help_text='Pérdida económica en UF')
    perdida_clp = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True,
                                      help_text='Pérdida económica en CLP')
    valor_uf_usado = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                          help_text='Valor de la UF en CLP al momento del cálculo')
    
    # Detalles de la falla
    motivo = models.CharField(max_length=50, choices=MOTIVO_CHOICES)
    descripcion = models.TextField(help_text='Descripción detallada de la falla')
    
    # Seguimiento
    contacto_proveedor = models.BooleanField(default=False, help_text='¿Se contactó al proveedor?')
    fecha_contacto = models.DateTimeField(null=True, blank=True)
    respuesta_proveedor = models.TextField(blank=True)
    resuelto = models.BooleanField(default=False)
    
    # Documentación para reporte
    incluir_en_reporte = models.BooleanField(default=True, help_text='Incluir en reporte de descuentos')
    observaciones_reporte = models.TextField(blank=True, help_text='Observaciones adicionales para el reporte')
    
    # Metadata
    responsable = models.CharField(max_length=200, help_text='Persona que registra la incidencia')
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-fecha_inicio', '-creado_en']
        verbose_name = 'Registro de Inactividad'
        verbose_name_plural = 'Registros de Inactividad'
    
    def calcular_duracion_y_perdida(self):
        """Calcula la duración y pérdida económica del período de inactividad.
        Fórmula: costo_hora_uf = monto_mensual_uf / 30 / 24
                 perdida_uf = costo_hora_uf * horas_inactividad
                 perdida_clp = perdida_uf * valor_uf_actual
        """
        from decimal import Decimal
        if self.fecha_inicio and self.fecha_fin:
            # Calcular duración
            delta = self.fecha_fin - self.fecha_inicio
            self.duracion_horas = Decimal(str(delta.total_seconds())) / Decimal('3600')
            self.duracion_dias = self.duracion_horas / Decimal('24')
            
            # Calcular pérdida en UF
            if self.costo_sistema.costo_hora_uf and self.duracion_horas:
                self.perdida_uf = self.costo_sistema.costo_hora_uf * self.duracion_horas
            
            # Calcular pérdida en CLP usando valor UF real
            if self.perdida_uf and self.valor_uf_usado:
                self.perdida_clp = self.perdida_uf * self.valor_uf_usado
    
    def save(self, *args, **kwargs):
        # Calcular duración y pérdida antes de guardar
        self.calcular_duracion_y_perdida()
        super().save(*args, **kwargs)
    
    def __str__(self):
        estado = "Activa" if not self.fecha_fin else "Resuelta"
        return f"{self.costo_sistema.centro.nombre} - {self.costo_sistema.sistema} - {self.fecha_inicio.strftime('%Y-%m-%d %H:%M')} ({estado})"
    
    @property
    def esta_activa(self):
        """Retorna True si la falla aún está activa (no tiene fecha de fin)"""
        return self.fecha_fin is None