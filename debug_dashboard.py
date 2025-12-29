# debug_dashboard.py
"""
Script para depurar y corregir problemas en el dashboard
"""

import os
import sys
import django
from datetime import date, timedelta

# Configurar Django
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'adherence_dasboard.settings')
django.setup()

from dashboard.models import Agente, ProgramaDiario, RegistroActividad, KPIMeta
from dashboard.utils import CalculadorAdherencia

def analizar_problemas():
    """Analiza y muestra problemas en los datos"""
    print("🔍 ANALIZANDO PROBLEMAS DEL DASHBOARD")
    print("="*50)
    
    # 1. Verificar datos de agentes
    agentes = Agente.objects.all()
    print(f"📊 Total agentes: {agentes.count()}")
    print(f"   • FT: {agentes.filter(tipo_contrato='FT').count()}")
    print(f"   • PT: {agentes.filter(tipo_contrato='PT').count()}")
    
    # 2. Verificar programación
    hoy = date.today()
    programas_hoy = ProgramaDiario.objects.filter(fecha=hoy)
    print(f"\n📅 Programación hoy ({hoy}): {programas_hoy.count()}")
    
    # 3. Verificar actividades
    actividades_ultima_semana = RegistroActividad.objects.filter(
        fecha__gte=hoy - timedelta(days=7)
    )
    print(f"\n📈 Actividades últimos 7 días: {actividades_ultima_semana.count()}")
    
    # 4. Calcular adherencia manualmente para diagnóstico
    print("\n🧮 CALCULANDO ADHERENCIA MANUAL")
    print("-"*30)
    
    fecha_fin = hoy
    fecha_inicio = hoy - timedelta(days=7)
    
    # Para cada agente FT
    agentes_ft = Agente.objects.filter(tipo_contrato='FT', activo=True)
    adherencias_ft = []
    
    for agente in agentes_ft:
        resultado = CalculadorAdherencia.calcular_adherencia_agente(agente, fecha_inicio, fecha_fin)
        if resultado:
            print(f"  {agente.codigo}: {resultado['adherencia']}%")
            adherencias_ft.append(resultado['adherencia'])
    
    if adherencias_ft:
        promedio_ft = sum(adherencias_ft) / len(adherencias_ft)
        print(f"\n  📌 FT - Promedio: {promedio_ft:.2f}%")
        print(f"     Rango: {min(adherencias_ft):.2f}% - {max(adherencias_ft):.2f}%")
    
    # Para cada agente PT
    agentes_pt = Agente.objects.filter(tipo_contrato='PT', activo=True)
    adherencias_pt = []
    
    for agente in agentes_pt:
        resultado = CalculadorAdherencia.calcular_adherencia_agente(agente, fecha_inicio, fecha_fin)
        if resultado:
            print(f"  {agente.codigo}: {resultado['adherencia']}%")
            adherencias_pt.append(resultado['adherencia'])
    
    if adherencias_pt:
        promedio_pt = sum(adherencias_pt) / len(adherencias_pt)
        print(f"\n  📌 PT - Promedio: {promedio_pt:.2f}%")
        print(f"     Rango: {min(adherencias_pt):.2f}% - {max(adherencias_pt):.2f}%")
    
    # 5. Verificar problemas específicos
    print("\n🔎 BUSCANDO PROBLEMAS ESPECÍFICOS")
    print("-"*30)
    
    # Verificar actividades sin duración
    actividades_sin_duracion = RegistroActividad.objects.filter(duracion_minutos=0)
    if actividades_sin_duracion.exists():
        print(f"⚠️  Actividades sin duración: {actividades_sin_duracion.count()}")
    
    # Verificar programas sin horas
    programas_sin_horas = ProgramaDiario.objects.filter(horas_planificadas=0)
    if programas_sin_horas.exists():
        print(f"⚠️  Programas sin horas planificadas: {programas_sin_horas.count()}")
    
    # 6. Recomendaciones
    print("\n💡 RECOMENDACIONES")
    print("-"*30)
    
    if len(adherencias_pt) > 0 and max(adherencias_pt) > 100:
        print("❌ Problema detectado: Adherencia PT > 100%")
        print("   Solución: Ejecutar el script de corrección")
    
    if programas_hoy.count() == 0:
        print("⚠️  No hay programación para hoy")
        print("   Solución: Generar programación actual")
    
    print("\n🎯 Para corregir problemas:")
    print("   1. Ejecutar: python fix_adherence_data.py")
    print("   2. Regenerar datos: python manage.py shell < regenerate_data.py")

def corregir_datos():
    """Corrige datos problemáticos"""
    print("\n🛠️  CORRIGIENDO DATOS")
    print("="*50)
    
    # 1. Limitar adherencia a 100%
    print("1. Limitando adherencias a 100%...")
    
    # No hay una tabla directa de adherencia, se calcula dinámicamente
    # Esta corrección se hace en el cálculo, no en los datos
    
    # 2. Verificar y corregir duraciones inválidas
    print("2. Verificando duraciones de actividades...")
    
    actividades = RegistroActividad.objects.all()
    for actividad in actividades:
        if actividad.duracion_minutos < 0:
            actividad.duracion_minutos = abs(actividad.duracion_minutos)
            actividad.save()
            print(f"   Corregida duración negativa: {actividad.id}")
    
    # 3. Asegurar horas planificadas positivas
    print("3. Verificando horas planificadas...")
    
    programas = ProgramaDiario.objects.all()
    for programa in programas:
        if programa.horas_planificadas <= 0:
            programa.horas_planificadas = 4.0 if programa.agente.tipo_contrato == 'PT' else 8.0
            programa.save()
            print(f"   Corregidas horas: {programa.id} -> {programa.horas_planificadas}h")
    
    print("\n✅ Correcciones aplicadas")

if __name__ == '__main__':
    analizar_problemas()
    print("\n¿Desea corregir los datos automáticamente? (s/n): ")
    respuesta = input().strip().lower()
    
    if respuesta == 's':
        corregir_datos()
    else:
        print("\n⚠️  No se aplicaron correcciones")
    
    print("\n📋 Para regenerar datos correctamente:")
    print("   python manage.py shell < regenerate_data.py")