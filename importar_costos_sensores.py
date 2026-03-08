"""
Script para importar los costos de sistemas de sensores desde el JSON extraído
del archivo KPI_REDUCCION_COSTOS_SENSORES.xlsx
"""
import os
import sys
import django
import json
from datetime import datetime
from decimal import Decimal

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from incidencias.models import Centro, CostoSistema

def limpiar_valor_uf(valor_str):
    """Limpia y convierte valores UF del formato '9,44 UF' a Decimal"""
    if not valor_str:
        return Decimal('0')
    
    # Remover 'UF' y espacios
    valor_limpio = str(valor_str).replace('UF', '').strip()
    # Reemplazar coma por punto para decimal
    valor_limpio = valor_limpio.replace(',', '.')
    
    try:
        return Decimal(valor_limpio)
    except:
        print(f"  [!] Error convirtiendo valor: {valor_str}")
        return Decimal('0')

def normalizar_nombre_centro(nombre):
    """Normaliza nombres de centros para que coincidan con la BD"""
    normalizaciones = {
        'Santa Juana': 'Santa Juana',
        'Rio Pescado': 'Cipreses',
        'Trafun': 'Trafún',
        'Rahue': 'Rahue',
        'PCC': 'PCC',
        'Liquiñe': 'Liquiñe',
        'Hueyusca': 'Hueyusca',
        'Esperanza': 'Esperanza',
        'Cipreses': 'Cipreses'
    }
    return normalizaciones.get(nombre, nombre)

def importar_costos():
    """Importa los costos desde el archivo JSON"""
    
    print("="*80)
    print("IMPORTACIÓN DE COSTOS DE SISTEMAS DE SENSORES")
    print("="*80)
    
    # Cargar datos del JSON
    try:
        with open('costos_sensores_extraidos.json', 'r', encoding='utf-8') as f:
            datos = json.load(f)
    except FileNotFoundError:
        print("ERROR: No se encontro el archivo 'costos_sensores_extraidos.json'")
        print("   Ejecuta primero: python analizar_costos_sensores.py")
        return
    
    costos = datos.get('costos', [])
    print(f"\nTotal de registros a importar: {len(costos)}")
    
    # Estadísticas
    importados = 0
    actualizados = 0
    errores = 0
    centros_sin_match = set()
    
    for idx, registro in enumerate(costos, 1):
        try:
            # Extraer datos
            nombre_centro = registro.get('psiculturaa', '').strip()
            sistema = registro.get('Sistema', '').strip()
            
            if not nombre_centro or not sistema:
                print(f"  [!] Registro {idx}: Falta centro o sistema, saltando...")
                errores += 1
                continue
            
            # Normalizar nombre del centro
            nombre_centro_normalizado = normalizar_nombre_centro(nombre_centro)
            
            # Buscar centro en la BD
            try:
                centro = Centro.objects.get(nombre=nombre_centro_normalizado)
            except Centro.DoesNotExist:
                centros_sin_match.add(nombre_centro)
                continue
            
            # Extraer valores
            monto_mensual_uf = limpiar_valor_uf(registro.get('Monto mensual'))
            monto_mensual_clp = Decimal(str(registro.get('MONTO CLP', 0)))
            costo_diario_uf = limpiar_valor_uf(registro.get('COSTO DIARIO (24 HORAS) EN UF'))
            costo_diario_clp = Decimal(str(registro.get('COSTO DIARIO (24 HORAS)', 0)))
            
            # Fechas
            fecha_inicio_str = registro.get('fecha inicio')
            fecha_termino_str = registro.get('Fecha Termino')
            
            fecha_inicio = datetime.strptime(fecha_inicio_str, '%Y-%m-%d %H:%M:%S').date() if fecha_inicio_str else None
            fecha_termino = datetime.strptime(fecha_termino_str, '%Y-%m-%d %H:%M:%S').date() if fecha_termino_str else None
            
            # Totales
            costo_total_uf = limpiar_valor_uf(registro.get('costo total uf'))
            costo_total_clp = Decimal(str(registro.get('costo total clp', 0)))
            
            # Crear o actualizar registro
            costo_obj, created = CostoSistema.objects.update_or_create(
                centro=centro,
                sistema=sistema,
                defaults={
                    'monto_mensual_uf': monto_mensual_uf,
                    'monto_mensual_clp': monto_mensual_clp,
                    'costo_diario_uf': costo_diario_uf,
                    'costo_diario_clp': costo_diario_clp,
                    'plazo_contrato': registro.get('Plazo Contrato', '36 MESES'),
                    'fecha_inicio': fecha_inicio,
                    'fecha_termino': fecha_termino,
                    'cantidad_sensores': registro.get('CANTIDAD SENSORES '),
                    'costo_total_uf': costo_total_uf,
                    'costo_total_clp': costo_total_clp,
                    'activo': True
                }
            )
            
            if created:
                importados += 1
                print(f"  [+] {idx}. Creado: {centro.nombre} - {sistema} ({monto_mensual_uf} UF/mes)")
            else:
                actualizados += 1
                print(f"  [~] {idx}. Actualizado: {centro.nombre} - {sistema} ({monto_mensual_uf} UF/mes)")
                
        except Exception as e:
            errores += 1
            print(f"  [X] Error en registro {idx}: {str(e)}")
            continue
    
    # Resumen
    print("\n" + "="*80)
    print("RESUMEN DE IMPORTACIÓN")
    print("="*80)
    print(f"[+] Registros creados:      {importados}")
    print(f"[~] Registros actualizados: {actualizados}")
    print(f"[X] Errores:                {errores}")
    
    if centros_sin_match:
        print(f"\n[!] Centros sin coincidencia en BD ({len(centros_sin_match)}):")
        for centro in sorted(centros_sin_match):
            print(f"  - {centro}")
        print("\nSolución: Verifica que estos centros existan en la base de datos")
    
    # Mostrar totales por centro
    print("\n" + "="*80)
    print("COSTOS TOTALES POR CENTRO")
    print("="*80)
    
    centros_con_costos = Centro.objects.filter(costos_sistemas__activo=True).distinct()
    
    for centro in centros_con_costos:
        costos_centro = CostoSistema.objects.filter(centro=centro, activo=True)
        total_mensual_uf = sum(c.monto_mensual_uf for c in costos_centro)
        total_mensual_clp = sum(c.monto_mensual_clp for c in costos_centro)
        
        print(f"\n{centro.nombre}:")
        print(f"  Sistemas: {costos_centro.count()}")
        print(f"  Total mensual: {total_mensual_uf:.2f} UF (${total_mensual_clp:,.0f} CLP)")
        
        for costo in costos_centro:
            print(f"    - {costo.sistema}: {costo.monto_mensual_uf} UF/mes")
    
    print("\n" + "="*80)
    print("Importacion completada exitosamente")
    print("="*80)

if __name__ == '__main__':
    try:
        importar_costos()
    except Exception as e:
        print(f"\nERROR FATAL: {str(e)}")
        import traceback
        traceback.print_exc()
