# regenerate_data.py
"""
Script para regenerar datos del dashboard de manera correcta
"""

import os
import sys
import django
from datetime import date, timedelta
import numpy as np

# Configurar Django
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'adherence_dasboard.settings')
django.setup()

from django.db import transaction
from dashboard.models import Agente, ProgramaDiario, RegistroActividad
from dashboard.utils import SimuladorDatos

@transaction.atomic
def regenerar_datos_correctamente():
    """Regenera todos los datos del dashboard de manera controlada"""
    print("🔄 REGENERANDO DATOS DEL DASHBOARD")
    print("="*50)
    
    # 1. Eliminar datos existentes (en orden inverso a dependencias)
    print("1. Eliminando datos existentes...")
    RegistroActividad.objects.all().delete()
    ProgramaDiario.objects.all().delete()
    Agente.objects.all().delete()
    
    print("   ✅ Datos eliminados")
    
    # 2. Crear agentes con datos más realistas
    print("2. Creando agentes...")
    
    agentes_data = [
        # Full-Time (8 horas/día)
        {'codigo': 'AGT001', 'nombre': 'Ana', 'apellido': 'García', 'tipo_contrato': 'FT'},
        {'codigo': 'AGT002', 'nombre': 'Carlos', 'apellido': 'López', 'tipo_contrato': 'FT'},
        {'codigo': 'AGT003', 'nombre': 'David', 'apellido': 'Rodríguez', 'tipo_contrato': 'FT'},
        {'codigo': 'AGT004', 'nombre': 'Fernando', 'apellido': 'Pérez', 'tipo_contrato': 'FT'},
        {'codigo': 'AGT005', 'nombre': 'Héctor', 'apellido': 'Díaz', 'tipo_contrato': 'FT'},
        {'codigo': 'AGT006', 'nombre': 'Javier', 'apellido': 'Ruiz', 'tipo_contrato': 'FT'},
        
        # Part-Time (4 horas/día)
        {'codigo': 'AGT007', 'nombre': 'Beatriz', 'apellido': 'Martínez', 'tipo_contrato': 'PT'},
        {'codigo': 'AGT008', 'nombre': 'Elena', 'apellido': 'Sánchez', 'tipo_contrato': 'PT'},
        {'codigo': 'AGT009', 'nombre': 'Gabriela', 'apellido': 'Gómez', 'tipo_contrato': 'PT'},
        {'codigo': 'AGT010', 'nombre': 'Irene', 'apellido': 'Fernández', 'tipo_contrato': 'PT'},
    ]
    
    for agente_data in agentes_data:
        Agente.objects.create(
            codigo=agente_data['codigo'],
            nombre=agente_data['nombre'],
            apellido=agente_data['apellido'],
            tipo_contrato=agente_data['tipo_contrato'],
            email=f"{agente_data['nombre'].lower()}.{agente_data['apellido'].lower()}@contactcenter.com",
            fecha_ingreso=date.today() - timedelta(days=np.random.randint(30, 365)),
            horas_semana=40 if agente_data['tipo_contrato'] == 'FT' else 20,
            activo=True
        )
    
    print(f"   ✅ {len(agentes_data)} agentes creados")
    
    # 3. Generar programación realista (últimos 7 días)
    print("3. Generando programación...")
    
    hoy = date.today()
    agentes = Agente.objects.all()
    
    for i in range(7):
        fecha = hoy - timedelta(days=i)
        
        if fecha.weekday() < 5:  # Solo días laborables (lun-vie)
            for agente in agentes:
                if agente.tipo_contrato == 'FT':
                    # Full-Time: 8 horas
                    turno = np.random.choice(['Matutino (8:00-16:00)', 'Vespertino (12:00-20:00)'])
                    horas = 8.0
                    hora_inicio = 8 if '8:00' in turno else 12
                    hora_fin = 16 if '16:00' in turno else 20
                else:
                    # Part-Time: 4 horas
                    turno = np.random.choice(['Medio (8:00-12:00)', 'Medio (14:00-18:00)'])
                    horas = 4.0
                    hora_inicio = 8 if '8:00' in turno else 14
                    hora_fin = 12 if '12:00' in turno else 18
                
                ProgramaDiario.objects.create(
                    agente=agente,
                    fecha=fecha,
                    turno=turno,
                    hora_inicio=f"{hora_inicio:02d}:00",
                    hora_fin=f"{hora_fin:02d}:00",
                    horas_planificadas=horas,
                    pausas_planificadas=1.0 if horas == 8.0 else 0.5
                )
    
    print(f"   ✅ Programación generada para 7 días")
    
    # 4. Generar actividades realistas (ajustadas a horas planificadas)
    print("4. Generando actividades...")
    
    for i in range(7):
        fecha = hoy - timedelta(days=i)
        programas = ProgramaDiario.objects.filter(fecha=fecha)
        
        for programa in programas:
            agente = programa.agente
            hora_actual = programa.hora_inicio
            
            # Convertir hora string a objeto time
            from datetime import datetime
            hora_actual_dt = datetime.strptime(hora_actual, "%H:%M")
            hora_fin_dt = datetime.strptime(programa.hora_fin, "%H:%M")
            
            # Calcular minutos totales disponibles
            minutos_totales = (hora_fin_dt - hora_actual_dt).seconds // 60
            
            # Generar actividades hasta llenar el turno
            minutos_usados = 0
            
            while minutos_usados < minutos_totales and minutos_totales - minutos_usados > 5:
                # Determinar tipo de actividad según tipo de contrato
                if agente.tipo_contrato == 'FT':
                    # Full-Time: más llamadas, menos pausas
                    if minutos_usados < minutos_totales * 0.7:  # 70% del tiempo en llamadas
                        tipo = 'LLAMADA'
                        duracion = np.random.randint(3, 15)
                    elif minutos_usados < minutos_totales * 0.85:  # 15% disponible
                        tipo = 'DISPO'
                        duracion = np.random.randint(5, 15)
                    elif minutos_usados < minutos_totales * 0.95:  # 10% pausa
                        tipo = 'PAUSA'
                        duracion = np.random.randint(5, 10)
                    else:  # 5% administrativo
                        tipo = 'ADMIN'
                        duracion = np.random.randint(10, 20)
                else:
                    # Part-Time: distribución diferente
                    if minutos_usados < minutos_totales * 0.6:  # 60% llamadas
                        tipo = 'LLAMADA'
                        duracion = np.random.randint(3, 12)
                    elif minutos_usados < minutos_totales * 0.8:  # 20% disponible
                        tipo = 'DISPO'
                        duracion = np.random.randint(5, 10)
                    elif minutos_usados < minutos_totales * 0.9:  # 10% pausa
                        tipo = 'PAUSA'
                        duracion = np.random.randint(5, 8)
                    else:  # 10% capacitación
                        tipo = 'CAPAC'
                        duracion = np.random.randint(15, 30)
                
                # Ajustar duración si excede el tiempo restante
                tiempo_restante = minutos_totales - minutos_usados
                if duracion > tiempo_restante:
                    duracion = tiempo_restante
                
                # Crear registro de actividad
                hora_inicio_reg = (hora_actual_dt + timedelta(minutes=minutos_usados)).strftime("%H:%M")
                hora_fin_reg = (hora_actual_dt + timedelta(minutes=minutos_usados + duracion)).strftime("%H:%M")
                
                RegistroActividad.objects.create(
                    agente=agente,
                    fecha=fecha,
                    hora_inicio=hora_inicio_reg,
                    hora_fin=hora_fin_reg,
                    tipo_actividad=tipo,
                    duracion_minutos=duracion,
                    llamadas_atendidas=1 if tipo == 'LLAMADA' else 0,
                    tiempo_conversacion=duracion if tipo == 'LLAMADA' else 0
                )
                
                minutos_usados += duracion
    
    print(f"   ✅ Actividades generadas")
    
    # 5. Resumen final
    print("\n" + "="*50)
    print("📊 DATOS REGENERADOS CORRECTAMENTE")
    print("="*50)
    print(f"\nAgentes: {Agente.objects.count()}")
    print(f"Programas: {ProgramaDiario.objects.count()}")
    print(f"Actividades: {RegistroActividad.objects.count()}")
    print(f"\nFT: {Agente.objects.filter(tipo_contrato='FT').count()} agentes")
    print(f"PT: {Agente.objects.filter(tipo_contrato='PT').count()} agentes")
    print(f"\n🎯 Para probar el dashboard:")
    print("   1. python manage.py runserver 0.0.0.0:8000")
    print("   2. Visitar: http://localhost:8000")

if __name__ == '__main__':
    try:
        regenerar_datos_correctamente()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()