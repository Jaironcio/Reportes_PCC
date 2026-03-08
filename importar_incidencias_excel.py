"""Borra TODO y reimporta desde CSV (ultra rápido)."""
import os, sys, django, csv
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from datetime import datetime
from django.utils import timezone
from incidencias.models import Incidencia, Centro, Operario

CSV_PATH = os.path.join(os.path.dirname(__file__), 'incidencias_temp.csv')
CM = {'Cipreses':'cipreses','Liquiñe':'liquine','Trafún':'trafun'}
TM = {'Día':'Día','Dia':'Día','DÍA':'Día','Tarde':'Tarde','Noche':'Noche','Mañana':'Día'}

print("1) Borrando incidencias...")
Incidencia.objects.all().delete()
print("   OK")

centros = {cid: Centro.objects.get(id=cid) for cid in CM.values()}
ops = {}
for o in Operario.objects.select_related('centro').all():
    ops[(o.centro.nombre.lower(), o.nombre.lower())] = o

print("2) Leyendo CSV...")
nuevas = []
err = 0

def s(val):
    if not val or val == 'nan' or val == 'NaT': return ''
    return str(val).strip()

def b(val):
    return s(val).lower().startswith('si')

with open(CSV_PATH, 'r', encoding='utf-8') as f:
    reader = csv.reader(f)
    next(reader)  # skip header
    for row in reader:
        try:
            if len(row) < 17 or not row[0] or row[0] == 'nan': continue
            # Fecha
            fecha_str = row[0]
            hora_str = row[1]
            try:
                fv = datetime.strptime(fecha_str.split(' ')[0], '%Y-%m-%d')
            except:
                continue
            # Hora
            try:
                if hora_str and hora_str != 'nan':
                    parts = hora_str.split(':')
                    h, m = int(parts[0]), int(parts[1])
                    fh = fv.replace(hour=h, minute=m)
                else:
                    fh = fv
            except:
                fh = fv
            fh = timezone.make_aware(fh)

            cn = s(row[3])
            cid = CM.get(cn)
            if not cid: continue

            ts = s(row[6]).lower()
            ti = 'sensores' if ('sensor' in ts or 'plataforma' in ts) else 'modulos'
            o2n,o2v,tn,tv = '','','',''
            if 'bajo' in ts and 'ox' in ts: o2n,o2v='baja',s(row[9])
            elif 'alto' in ts and 'ox' in ts: o2n,o2v='alta',s(row[9])
            elif 'temperatura' in ts:
                tn = 'alta' if 'alta' in ts else ('baja' if 'baja' in ts else '')
                tv = s(row[9])
            p = []
            if o2n: p.append('oxigeno')
            if tn: p.append('temperatura')
            try:
                tiempo = int(float(row[10])) if row[10] and row[10] != 'nan' else None
            except: tiempo = None

            op = None
            pn = s(row[16]).lower()
            if pn:
                op = ops.get((cn.lower(), pn))
                if not op:
                    for k,v in ops.items():
                        if k[0]==cn.lower() and pn.split()[0] in k[1]:
                            op=v; break

            nuevas.append(Incidencia(
                fecha_hora=fh, turno=TM.get(s(row[2]),s(row[2])),
                centro=centros[cid], tipo_incidencia=ti,
                modulo=s(row[4]), estanque=s(row[5]),
                parametros_afectados=','.join(p),
                oxigeno_nivel=o2n, oxigeno_valor=o2v,
                temperatura_nivel=tn, temperatura_valor=tv,
                tiempo_resolucion=tiempo,
                riesgo_peces=b(row[11]), perdida_economica=b(row[12]), riesgo_personas=b(row[13]),
                observacion=s(row[15]), operario_contacto=op,
                tipo_incidencia_normalizada=s(row[14]),
            ))
        except Exception as e:
            err += 1

print(f"   {len(nuevas)} filas procesadas, {err} errores")
print("3) Insertando...")
Incidencia.objects.bulk_create(nuevas, batch_size=500)
print(f"\nLISTO: {Incidencia.objects.count()} incidencias en BD")
