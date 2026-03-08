# Sistema de Cálculo de Pérdidas Económicas por Inactividad de Sensores

## Descripción General

Este sistema permite calcular y documentar las pérdidas económicas cuando los sensores de IDEAL CONTROL fallan o dejan de enviar datos, con el objetivo de solicitar rebajas proporcionales en el servicio contratado.

## Características Principales

### ✅ Funcionalidades Implementadas

1. **Modelos de Base de Datos**
   - `CostoSistema`: Almacena costos mensuales, diarios y por hora de cada sistema/módulo
   - `RegistroInactividad`: Registra períodos de falla con cálculo automático de pérdidas

2. **Cálculos Automáticos**
   - Costo por hora = Costo mensual ÷ 30 días ÷ 24 horas
   - Duración = Fecha fin - Fecha inicio (en horas y días)
   - Pérdida económica = Costo por hora × Duración en horas
   - Cálculos en UF y CLP

3. **Interfaz Web**
   - Dashboard con resumen de pérdidas
   - Formulario de registro de inactividades
   - Vista de reporte consolidado
   - APIs REST para integración

4. **Seguimiento**
   - Estado de inactividades (activa/resuelta)
   - Registro de contacto con proveedor
   - Observaciones para reportes de descuento

## Instalación y Configuración

### Paso 1: Aplicar Migraciones

```bash
# Asegúrate de que MySQL esté corriendo
python manage.py migrate
```

### Paso 2: Importar Costos de Sistemas

```bash
# Primero, analiza el Excel con costos (si no lo has hecho)
python analizar_costos_sensores.py

# Luego, importa los costos a la base de datos
python importar_costos_sensores.py
```

**Nota:** El script `importar_costos_sensores.py` lee el archivo `costos_sensores_extraidos.json` y carga los datos en la tabla `CostoSistema`.

### Paso 3: Verificar Centros

Asegúrate de que los centros en la base de datos coincidan con los del Excel:

```python
# En Django shell
python manage.py shell

from incidencias.models import Centro
print(Centro.objects.all().values_list('nombre', flat=True))
```

Centros esperados:
- Santa Juana
- Río Pescado
- Trafún
- Rahue
- PCC
- Liquiñe
- Hueyusca
- Esperanza
- Los Cipreses

## Uso del Sistema

### 1. Acceder al Dashboard

URL: `/perdidas-economicas/`

El dashboard muestra:
- Total de registros de inactividad
- Inactividades activas (sin resolver)
- Inactividades resueltas
- Pérdidas económicas totales (UF y CLP)
- Lista de registros recientes

### 2. Registrar una Inactividad

**URL:** `/perdidas-economicas/registrar/`

**Pasos:**

1. **Identificación del Sistema**
   - Seleccionar centro/piscicultura
   - Seleccionar sistema/módulo afectado
   - (Opcional) Seleccionar sensor específico
   - El sistema muestra automáticamente los costos

2. **Período de Inactividad**
   - Fecha y hora de inicio de la falla
   - Fecha y hora de fin (dejar vacío si aún está activa)
   - El sistema calcula automáticamente la duración

3. **Detalles de la Falla**
   - Motivo (sensor apagado, mal estado, no sube datos, etc.)
   - Descripción detallada
   - Responsable del registro

4. **Seguimiento con Proveedor**
   - ¿Se contactó a IDEAL CONTROL?
   - Fecha de contacto
   - Respuesta del proveedor

5. **Para el Reporte**
   - Incluir en reporte de descuentos (checkbox)
   - Observaciones adicionales

**Cálculo Automático:**
- Al ingresar fecha de fin, el sistema calcula:
  - Duración en horas y días
  - Pérdida en UF
  - Pérdida en CLP

### 3. Ver Reporte de Pérdidas

**URL:** `/perdidas-economicas/reporte/`

Filtros disponibles:
- Por centro
- Por rango de fechas
- Por estado (activa/resuelta/todas)

### 4. Marcar Inactividad como Resuelta

Desde el dashboard o el listado, hacer clic en el botón de check (✓) para marcar una inactividad como resuelta. Esto establecerá la fecha de fin automáticamente si no existe.

## Estructura de Datos

### Tabla: CostoSistema

```python
{
    'centro': ForeignKey(Centro),
    'sistema': str,  # Ej: "IDEAL CLOUD", "CO2 Y TURBIDEZ"
    'monto_mensual_uf': Decimal,
    'monto_mensual_clp': Decimal,
    'costo_diario_uf': Decimal,
    'costo_diario_clp': Decimal,
    'costo_hora_uf': Decimal,  # Calculado automáticamente
    'costo_hora_clp': Decimal,  # Calculado automáticamente
    'fecha_inicio': Date,
    'fecha_termino': Date,
    'plazo_contrato': str,  # "36 MESES"
}
```

### Tabla: RegistroInactividad

```python
{
    'costo_sistema': ForeignKey(CostoSistema),
    'sensor': ForeignKey(SensorConfig, optional),
    'fecha_inicio': DateTime,
    'fecha_fin': DateTime,  # Null si aún está activa
    'duracion_horas': Decimal,  # Calculado automáticamente
    'duracion_dias': Decimal,  # Calculado automáticamente
    'perdida_uf': Decimal,  # Calculado automáticamente
    'perdida_clp': Decimal,  # Calculado automáticamente
    'motivo': str,
    'descripcion': Text,
    'contacto_proveedor': Boolean,
    'fecha_contacto': DateTime,
    'respuesta_proveedor': Text,
    'resuelto': Boolean,
    'incluir_en_reporte': Boolean,
    'observaciones_reporte': Text,
    'responsable': str,
}
```

## APIs Disponibles

### GET /api/perdidas/sistemas/
Obtiene los sistemas de costos de un centro.

**Parámetros:**
- `centro_id`: ID del centro

**Respuesta:**
```json
{
    "success": true,
    "sistemas": [
        {
            "id": 1,
            "sistema": "IDEAL CLOUD",
            "monto_mensual_uf": "9.44",
            "costo_hora_uf": "0.013222",
            ...
        }
    ]
}
```

### POST /api/perdidas/guardar/
Guarda o actualiza un registro de inactividad.

**Body:**
```json
{
    "costo_sistema_id": 1,
    "sensor_id": null,
    "fecha_inicio": "2026-02-16T08:00:00",
    "fecha_fin": "2026-02-16T14:00:00",
    "motivo": "SENSOR_MAL_ESTADO",
    "descripcion": "Sensor no responde...",
    "responsable": "Juan Pérez",
    "contacto_proveedor": true,
    "incluir_en_reporte": true
}
```

### GET /api/perdidas/listar/
Lista registros de inactividad con filtros.

**Parámetros:**
- `centro_id`: Filtrar por centro
- `fecha_desde`: Fecha desde
- `fecha_hasta`: Fecha hasta
- `estado`: 'activa', 'resuelta', 'todas'

### POST /api/perdidas/resolver/{id}/
Marca una inactividad como resuelta.

### GET /api/perdidas/estadisticas/
Obtiene estadísticas consolidadas de pérdidas.

## Ejemplo de Uso Completo

### Escenario: Sensor de CO2 en mal estado

1. **Detectar la falla**
   - Fecha: 16/02/2026 08:00 hrs
   - Centro: Santa Juana
   - Sistema: CO2 Y TURBIDEZ (74.96 UF/mes)
   - Problema: Sensor no marca valores correctos

2. **Registrar en el sistema**
   - Ir a `/perdidas-economicas/registrar/`
   - Seleccionar Santa Juana
   - Seleccionar "CO2 Y TURBIDEZ"
   - Fecha inicio: 16/02/2026 08:00
   - Motivo: "Sensor en mal estado"
   - Descripción: "Sensor de CO2 marca valores erráticos..."

3. **Contactar a IDEAL CONTROL**
   - Marcar checkbox "Se contactó al proveedor"
   - Fecha contacto: 16/02/2026 09:30
   - Respuesta: "Técnico asignado, llegará mañana"

4. **Resolver la falla**
   - Fecha: 17/02/2026 14:00 hrs
   - Editar el registro
   - Agregar fecha fin: 17/02/2026 14:00
   - Guardar

5. **Resultado del cálculo**
   - Duración: 30 horas (1.25 días)
   - Costo hora: 0.1045 UF/hora
   - **Pérdida total: 3.135 UF (~$123,800 CLP)**

6. **Generar reporte para descuento**
   - Ir a `/perdidas-economicas/reporte/`
   - Filtrar por Santa Juana
   - Exportar a PDF/Excel
   - Enviar a IDEAL CONTROL solicitando descuento

## Fórmulas de Cálculo

### Costo por Hora
```
Costo Hora (UF) = Monto Mensual (UF) ÷ 30 días ÷ 24 horas
Costo Hora (CLP) = Monto Mensual (CLP) ÷ 30 días ÷ 24 horas
```

### Duración
```
Duración (horas) = (Fecha Fin - Fecha Inicio) en horas
Duración (días) = Duración (horas) ÷ 24
```

### Pérdida Económica
```
Pérdida (UF) = Costo Hora (UF) × Duración (horas)
Pérdida (CLP) = Costo Hora (CLP) × Duración (horas)
```

## Mantenimiento

### Actualizar Costos

Si cambian los costos de los contratos:

1. Actualizar el Excel `KPI_REDUCCION_COSTOS_SENSORES.xlsx`
2. Ejecutar: `python analizar_costos_sensores.py`
3. Ejecutar: `python importar_costos_sensores.py`

Los registros existentes mantendrán los costos históricos, pero los nuevos usarán los costos actualizados.

### Agregar Nuevo Centro

```python
from incidencias.models import Centro

centro = Centro.objects.create(
    nombre="Nuevo Centro",
    id="nuevo-centro"
)
```

Luego importar los costos de ese centro desde el Excel.

## Reportes y Exportación

### Generar Reporte PDF

URL: `/perdidas-economicas/pdf/`

Parámetros de query string:
- `centro_id`: Filtrar por centro
- `fecha_desde`: Fecha desde
- `fecha_hasta`: Fecha hasta

### Exportar a Excel

(En desarrollo - usar API para obtener datos y exportar manualmente)

## Solución de Problemas

### Error: "Centro no encontrado"

**Causa:** El nombre del centro en el Excel no coincide con la BD.

**Solución:** Verificar nombres en `importar_costos_sensores.py` línea 33 (función `normalizar_nombre_centro`).

### Error: "No se pueden aplicar migraciones"

**Causa:** MySQL no está corriendo.

**Solución:** 
```bash
# Iniciar MySQL
net start MySQL
```

### Los costos no aparecen

**Causa:** No se han importado los costos.

**Solución:**
```bash
python importar_costos_sensores.py
```

## Próximas Mejoras

- [ ] Exportación directa a Excel desde el reporte
- [ ] Generación automática de PDF con logo y formato oficial
- [ ] Notificaciones por email cuando se registra una inactividad
- [ ] Dashboard con gráficos de pérdidas por centro/mes
- [ ] Integración con sistema de tickets de IDEAL CONTROL
- [ ] Cálculo de descuento sugerido basado en SLA del contrato

## Soporte

Para dudas o problemas con el sistema, contactar al equipo de desarrollo o revisar este documento.

---

**Versión:** 1.0  
**Fecha:** Febrero 2026  
**Autor:** Sistema de Gestión de Incidencias PCC
