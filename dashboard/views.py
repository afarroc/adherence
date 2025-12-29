from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from datetime import date, timedelta
import json

from .models import Agente, ProgramaDiario, RegistroActividad, KPIMeta
from .utils import CalculadorAdherencia, SimuladorDatos


# dashboard/views.py - CORREGIDO

def dashboard_principal(request):
    """Vista principal del dashboard - VERSIÓN CORREGIDA DEFINITIVA"""
    # Fechas por defecto (últimos 7 días)
    fecha_fin = date.today()
    fecha_inicio = fecha_fin - timedelta(days=7)
    
    # Obtener datos de adherencia
    reporte = CalculadorAdherencia.generar_reporte_adherencia(fecha_inicio, fecha_fin)
    
    # Verificar y corregir adherencias inválidas
    if reporte:
        # Corregir adherencia PT si es mayor a 100%
        if reporte.get('part_time') and reporte['part_time'].get('adherencia_promedio', 0) > 100:
            reporte['part_time']['adherencia_promedio'] = 100
            reporte['part_time']['rango'] = "100.00% - 100.00%"
        
        # Corregir adherencia FT si es mayor a 100%
        if reporte.get('full_time') and reporte['full_time'].get('adherencia_promedio', 0) > 100:
            reporte['full_time']['adherencia_promedio'] = min(reporte['full_time']['adherencia_promedio'], 100)
    
    # Usar la versión CORRECTA
    try:
        adherencia_hora = CalculadorAdherencia.calcular_adherencia_por_hora_minuto_a_minuto(fecha_fin)

        # Análisis de problemas
        problemas = CalculadorAdherencia.analizar_problemas_adherencia_por_minuto(fecha_fin)
    except Exception as e:
        print(f"Error calculando adherencia por hora: {e}")
        adherencia_hora = []
        problemas = {'horas_criticas': [], 'resumen_por_hora': {}}
    
    # Factores de impacto
    factores = CalculadorAdherencia.calcular_impacto_factores(fecha_inicio, fecha_fin)
    
    # KPIs meta
    kpi_meta = KPIMeta.objects.filter(activo=True).first()
    
    context = {
        'reporte': reporte or {},
        'adherencia_hora': adherencia_hora,
        'factores': factores[:5] if factores else [],
        'kpi_meta': kpi_meta,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'hoy': date.today(),
        'total_agentes': Agente.objects.filter(activo=True).count(),
        'agentes_ft': Agente.objects.filter(tipo_contrato='FT', activo=True).count(),
        'agentes_pt': Agente.objects.filter(tipo_contrato='PT', activo=True).count(),
    }
    
    return render(request, 'dashboard/index.html', context)

@login_required
def kpi_detalle(request, tipo):
    """Vista detallada por tipo de KPI"""
    fecha_fin = date.today()
    fecha_inicio = fecha_fin - timedelta(days=30)
    
    if tipo == 'full-time':
        data = CalculadorAdherencia.calcular_adherencia_tipo_contrato('FT', fecha_inicio, fecha_fin)
        titulo = "Adherencia Full-Time"
    elif tipo == 'part-time':
        data = CalculadorAdherencia.calcular_adherencia_tipo_contrato('PT', fecha_inicio, fecha_fin)
        titulo = "Adherencia Part-Time"
    elif tipo == 'hora':
        data = CalculadorAdherencia.calcular_adherencia_por_hora_minuto_a_minuto(date.today())
        titulo = "Adherencia por Hora"
    else:
        data = None
        titulo = "Detalle no disponible"
    
    context = {
        'titulo': titulo,
        'data': data,
        'tipo': tipo,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin
    }
    
    return render(request, 'dashboard/kpi_detail.html', context)

@login_required
def api_adherencia_diaria(request):
    """API para gráfico de adherencia diaria - SOLO DÍAS LABORABLES"""
    dias = int(request.GET.get('dias', 7))
    fecha_fin = date.today()

    datos = []
    fecha_actual = fecha_fin
    dias_contados = 0

    while dias_contados < dias:
        if fecha_actual.weekday() < 5:  # Día laborable (0=lunes, 4=viernes)
            # Calcular para FT
            ft_data = CalculadorAdherencia.calcular_adherencia_tipo_contrato('FT', fecha_actual, fecha_actual)
            ft_adherencia = ft_data['adherencia_promedio'] if ft_data else 0

            # Calcular para PT
            pt_data = CalculadorAdherencia.calcular_adherencia_tipo_contrato('PT', fecha_actual, fecha_actual)
            pt_adherencia = pt_data['adherencia_promedio'] if pt_data else 0

            datos.append({
                'fecha': fecha_actual.strftime('%Y-%m-%d'),
                'ft': ft_adherencia,
                'pt': pt_adherencia,
                'total': round((ft_adherencia + pt_adherencia) / 2, 2)
            })
            dias_contados += 1

        fecha_actual -= timedelta(days=1)

    datos.reverse()  # Orden cronológico
    return JsonResponse({'datos': datos})

@login_required
def api_simular_datos(request):
    """API para simular datos de prueba"""
    try:
        # Crear agentes de prueba
        SimuladorDatos.crear_agentes_test()
        
        # Generar programación del mes actual
        hoy = date.today()
        SimuladorDatos.generar_programacion_mes(hoy.month, hoy.year)
        
        # Generar actividades de los últimos 7 días
        for i in range(7):
            fecha = hoy - timedelta(days=i)
            SimuladorDatos.generar_actividades_dia(fecha)
        
        return JsonResponse({
            'success': True,
            'message': 'Datos simulados correctamente',
            'agentes_creados': Agente.objects.count(),
            'programas_creados': ProgramaDiario.objects.count(),
            'actividades_creadas': RegistroActividad.objects.count()
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        })

@login_required
def api_agentes_top(request):
    """API para top agentes"""
    top_count = int(request.GET.get('top', 5))
    tipo = request.GET.get('tipo', 'all')
    
    fecha_fin = date.today()
    fecha_inicio = fecha_fin - timedelta(days=7)
    
    if tipo == 'ft':
        agentes = Agente.objects.filter(tipo_contrato='FT', activo=True)
    elif tipo == 'pt':
        agentes = Agente.objects.filter(tipo_contrato='PT', activo=True)
    else:
        agentes = Agente.objects.filter(activo=True)
    
    resultados = []
    for agente in agentes[:20]:  # Limitamos para performance
        resultado = CalculadorAdherencia.calcular_adherencia_agente(
            agente, fecha_inicio, fecha_fin
        )
        if resultado:
            resultados.append({
                'codigo': agente.codigo,
                'nombre': f"{agente.nombre} {agente.apellido}",
                'tipo': 'Full-Time' if agente.es_full_time else 'Part-Time',
                'adherencia': resultado['adherencia'],
                'horas_productivas': round(resultado['tiempo_productivo'] / 60, 1)
            })
    
    # Ordenar y limitar
    resultados.sort(key=lambda x: x['adherencia'], reverse=True)
    top_resultados = resultados[:top_count]

    return JsonResponse({'agentes': top_resultados})

@login_required
def regenerate_data(request):
    """Vista para regenerar datos del dashboard"""
    if request.method == 'POST':
        success = SimuladorDatos.regenerar_datos_completos(dias=7)
        if success:
            messages.success(request, 'Datos regenerados correctamente')
        else:
            messages.error(request, 'Error al regenerar los datos')
        return redirect('dashboard:dashboard_principal')

    return render(request, 'dashboard/regenerate.html')

@login_required
def matrix_view(request, agente_id=None):
    """Vista de matriz de adherencia por hora y fecha"""
    agentes = Agente.objects.filter(activo=True).order_by('codigo')

    if agente_id:
        agente = get_object_or_404(Agente, id=agente_id)

        # Obtener últimos 7 días laborables
        fechas = []
        fecha_actual = date.today()
        dias_contados = 0

        while dias_contados < 7:
            if fecha_actual.weekday() < 5:  # Día laborable
                fechas.append(fecha_actual)
                dias_contados += 1
            fecha_actual -= timedelta(days=1)

        fechas.reverse()  # Orden cronológico

        # Calcular matriz
        matriz = CalculadorAdherencia.calcular_matriz_adherencia_agente(agente, fechas)

        # Preparar datos para template
        horas = [f"{h:02d}:00" for h in range(8, 20)]
        datos_matriz = []

        for hora in range(8, 20):
            fila = {'hora': f"{hora:02d}:00", 'valores': []}
            for fecha in fechas:
                valor = matriz.get(fecha, {}).get(hora, 0)
                fila['valores'].append({
                    'fecha': fecha,
                    'adherencia': valor,
                    'clase': 'table-success' if valor >= 90 else 'table-warning' if valor >= 70 else 'table-danger'
                })
            datos_matriz.append(fila)

        context = {
            'agente': agente,
            'fechas': fechas,
            'datos_matriz': datos_matriz,
            'agentes': agentes,
            'segmento': 'Agente'
        }
    else:
        context = {
            'agentes': agentes,
            'segmento': None
        }

    return render(request, 'dashboard/matrix.html', context)