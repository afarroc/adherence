from datetime import datetime, date, time, timedelta
from django.utils import timezone
from django.db.models import Sum, Avg, Count, Q
from django.db import transaction
from collections import defaultdict
import pandas as pd  # Import for data analysis
import numpy as np
from .models import *

class CalculadorAdherencia:
    """
    Clase para calcular métricas de adherencia
    """
    
    @staticmethod
    def calcular_adherencia_agente(agente, fecha_inicio, fecha_fin):
        """
        Calcula adherencia individual por agente - VERSIÓN CORREGIDA
        """
        programas = ProgramaDiario.objects.filter(
            agente=agente,
            fecha__range=[fecha_inicio, fecha_fin]
        )
        
        actividades = RegistroActividad.objects.filter(
            agente=agente,
            fecha__range=[fecha_inicio, fecha_fin]
        )
        
        if not programas.exists():
            return None
        
        # Calcular tiempo total planificado (convertir horas a minutos)
        tiempo_planificado_total = sum(
            float(p.horas_planificadas) * 60 for p in programas
        )
        
        # Calcular tiempo en actividades productivas
        actividades_productivas = actividades.filter(
            tipo_actividad__in=['LLAMADA', 'DISPO', 'CAPAC', 'ADMIN']
        )
        
        tiempo_productivo = actividades_productivas.aggregate(
            total=Sum('duracion_minutos')
        )['total'] or 0
        
        # Asegurar que la adherencia no sea mayor al 100%
        if tiempo_planificado_total > 0:
            adherencia = min((tiempo_productivo / tiempo_planificado_total) * 100, 100)
        else:
            adherencia = 0
        
        return {
            'agente': agente,
            'adherencia': round(adherencia, 2),
            'tiempo_productivo': tiempo_productivo,
            'tiempo_planificado': tiempo_planificado_total,
            'dias_analizados': programas.count()
        }
    
    @staticmethod
    def calcular_adherencia_tipo_contrato(tipo_contrato, fecha_inicio, fecha_fin):
        """
        Calcula adherencia promedio por tipo de contrato
        """
        agentes = Agente.objects.filter(
            tipo_contrato=tipo_contrato,
            activo=True
        )
        
        resultados = []
        for agente in agentes:
            resultado = CalculadorAdherencia.calcular_adherencia_agente(
                agente, fecha_inicio, fecha_fin
            )
            if resultado:
                resultados.append(resultado['adherencia'])
        
        if resultados:
            return {
                'tipo_contrato': tipo_contrato,
                'adherencia_promedio': round(np.mean(resultados), 2),
                'adherencia_mediana': round(np.median(resultados), 2),
                'cantidad_agentes': len(resultados),
                'rango': f"{round(min(resultados), 2)}% - {round(max(resultados), 2)}%"
            }
        return None
    
    # dashboard/utils.py - MÉTODO CORREGIDO
    
    @staticmethod
    def calcular_adherencia_por_hora_minuto_a_minuto(fecha):
        """
        Calcula adherencia por hora con cálculo MINUTO A MINUTO - VERSIÓN CORRECTA

        Para cada minuto dentro de la hora:
        1. Identifica qué agentes están programados en ESE minuto exacto
        2. Identifica qué agentes programados están activos en ESE minuto exacto
        3. Calcula: (agentes activos / agentes programados) para ESE minuto
        4. Promedia todos los minutos de la hora

        Esto evita la compensación global y detecta huecos reales.
        """
        horas = []

        for hora in range(8, 20):  # De 8 AM a 8 PM
            # Lista para almacenar adherencia de cada minuto
            adherencias_por_minuto = []
            agentes_programados_por_minuto = []

            # Analizar cada minuto de la hora
            for minuto in range(60):
                # Crear el intervalo exacto de este minuto
                inicio_minuto = time(hora, minuto)
                fin_minuto = time(hora, minuto + 1) if minuto < 59 else time(hora + 1, 0)

                # 1. Agentes programados en ESTE minuto exacto
                programas_en_minuto = ProgramaDiario.objects.filter(
                    fecha=fecha,
                    hora_inicio__lt=fin_minuto,
                    hora_fin__gt=inicio_minuto
                )

                agentes_programados = programas_en_minuto.count()

                if agentes_programados == 0:
                    # Si no hay agentes programados, adherencia = 0% (o N/A)
                    adherencias_por_minuto.append(0)
                    agentes_programados_por_minuto.append(0)
                    continue

                # 2. Agentes ACTIVOS en ESTE minuto exacto
                agentes_ids = programas_en_minuto.values_list('agente_id', flat=True)

                agentes_activos = RegistroActividad.objects.filter(
                    fecha=fecha,
                    agente_id__in=agentes_ids,
                    hora_inicio__time__lt=fin_minuto,
                    hora_fin__time__gt=inicio_minuto,
                    tipo_actividad__in=['LLAMADA', 'DISPO', 'CAPAC', 'ADMIN']
                ).values('agente_id').distinct().count()

                # 3. Calcular adherencia para ESTE minuto exacto
                adherencia_minuto = (agentes_activos / agentes_programados) * 100
                adherencias_por_minuto.append(adherencia_minuto)
                agentes_programados_por_minuto.append(agentes_programados)

            # 4. Calcular promedios para la hora completa
            if adherencias_por_minuto:
                # Promedio ponderado por agentes programados en cada minuto
                total_minutos = len(adherencias_por_minuto)
                minutos_con_programacion = sum(1 for apm in agentes_programados_por_minuto if apm > 0)

                if minutos_con_programacion > 0:
                    # Solo considerar minutos donde HAY programación
                    adherencia_promedio = sum(
                        adherencias_por_minuto[i]
                        for i in range(total_minutos)
                        if agentes_programados_por_minuto[i] > 0
                    ) / minutos_con_programacion

                    # Agentes programados promedio en la hora
                    agentes_programados_promedio = sum(agentes_programados_por_minuto) / total_minutos

                    # Minutos con adherencia < 80% (problemas)
                    minutos_baja_adherencia = sum(1 for a in adherencias_por_minuto if a < 80)

                    horas.append({
                        'hora': f"{hora:02d}:00",
                        'adherencia': round(adherencia_promedio, 2),
                        'agentes_programados_promedio': round(agentes_programados_promedio, 1),
                        'minutos_con_programacion': minutos_con_programacion,
                        'minutos_baja_adherencia': minutos_baja_adherencia,
                        'consistencia': round((1 - (minutos_baja_adherencia / minutos_con_programacion)) * 100, 1) if minutos_con_programacion > 0 else 0
                    })
                else:
                    # No hay programación en toda la hora
                    horas.append({
                        'hora': f"{hora:02d}:00",
                        'adherencia': 0,
                        'agentes_programados_promedio': 0,
                        'minutos_con_programacion': 0,
                        'minutos_baja_adherencia': 0,
                        'consistencia': 0
                    })
            else:
                horas.append({
                    'hora': f"{hora:02d}:00",
                    'adherencia': 0,
                    'agentes_programados_promedio': 0,
                    'minutos_con_programacion': 0,
                    'minutos_baja_adherencia': 0,
                    'consistencia': 0
                })

        return horas

    @staticmethod
    def calcular_adherencia_por_hora(fecha):
        """
        Calcula adherencia por hora con cálculo MINUTO A MINUTO - VERSIÓN OPTIMIZADA
        Usa pre-carga de datos y diccionarios para mejor performance
        """
        from collections import defaultdict
        import numpy as np

        horas = []

        # 1. Pre-cargar TODOS los datos del día una sola vez
        programas_dia = list(ProgramaDiario.objects.filter(fecha=fecha))
        actividades_dia = list(RegistroActividad.objects.filter(
            fecha=fecha,
            tipo_actividad__in=['LLAMADA', 'DISPO', 'CAPAC', 'ADMIN']
        ))

        # 2. Crear estructuras de acceso rápido
        # Diccionario: hora -> minuto -> lista de agentes programados
        programacion_por_minuto = defaultdict(lambda: defaultdict(set))

        for programa in programas_dia:
            # Para cada minuto que cubre este programa, agregar al agente
            hora_inicio_prog = programa.hora_inicio.hour
            minuto_inicio_prog = programa.hora_inicio.minute
            hora_fin_prog = programa.hora_fin.hour
            minuto_fin_prog = programa.hora_fin.minute

            # Convertir a minutos absolutos desde las 00:00
            inicio_abs = hora_inicio_prog * 60 + minuto_inicio_prog
            fin_abs = hora_fin_prog * 60 + minuto_fin_prog

            # Solo considerar horario laboral (8:00-20:00)
            inicio_abs = max(inicio_abs, 8 * 60)  # 8:00 AM
            fin_abs = min(fin_abs, 20 * 60)       # 8:00 PM

            for minuto_abs in range(inicio_abs, fin_abs):
                if 8*60 <= minuto_abs < 20*60:  # Solo horario laboral
                    hora = minuto_abs // 60
                    minuto = minuto_abs % 60
                    programacion_por_minuto[hora][minuto].add(programa.agente_id)

        # 3. Diccionario: hora -> minuto -> lista de agentes activos
        actividad_por_minuto = defaultdict(lambda: defaultdict(set))

        for actividad in actividades_dia:
            hora_inicio_act = actividad.hora_inicio.hour
            minuto_inicio_act = actividad.hora_inicio.minute
            hora_fin_act = actividad.hora_fin.hour
            minuto_fin_act = actividad.hora_fin.minute

            # Convertir a minutos absolutos
            inicio_abs = hora_inicio_act * 60 + minuto_inicio_act
            fin_abs = hora_fin_act * 60 + minuto_fin_act

            # Solo considerar horario laboral
            inicio_abs = max(inicio_abs, 8 * 60)
            fin_abs = min(fin_abs, 20 * 60)

            for minuto_abs in range(inicio_abs, fin_abs):
                if 8*60 <= minuto_abs < 20*60:
                    hora = minuto_abs // 60
                    minuto = minuto_abs % 60
                    actividad_por_minuto[hora][minuto].add(actividad.agente_id)

        # 4. Calcular para cada hora
        for hora in range(8, 20):
            adherencias_minutos = []
            agentes_prog_por_minuto = []
            agentes_activos_por_minuto = []

            for minuto in range(60):
                # Agentes programados en este minuto
                agentes_prog = programacion_por_minuto[hora].get(minuto, set())
                num_agentes_prog = len(agentes_prog)

                if num_agentes_prog == 0:
                    adherencias_minutos.append(0)
                    agentes_prog_por_minuto.append(0)
                    agentes_activos_por_minuto.append(0)
                    continue

                # Agentes activos en este minuto
                agentes_activos = actividad_por_minuto[hora].get(minuto, set())
                num_agentes_activos = len(agentes_activos.intersection(agentes_prog))

                # Adherencia para este minuto
                adherencia = (num_agentes_activos / num_agentes_prog) * 100
                adherencias_minutos.append(adherencia)
                agentes_prog_por_minuto.append(num_agentes_prog)
                agentes_activos_por_minuto.append(num_agentes_activos)

            # Calcular estadísticas para la hora
            if adherencias_minutos:
                # Solo considerar minutos con programación
                minutos_con_programacion = [i for i, apm in enumerate(agentes_prog_por_minuto) if apm > 0]

                if minutos_con_programacion:
                    adherencia_promedio = np.mean([adherencias_minutos[i] for i in minutos_con_programacion])
                    agentes_promedio = np.mean([agentes_prog_por_minuto[i] for i in minutos_con_programacion])
                    agentes_activos_promedio = np.mean([agentes_activos_por_minuto[i] for i in minutos_con_programacion])

                    # Detectar problemas
                    minutos_baja = sum(1 for i in minutos_con_programacion if adherencias_minutos[i] < 80)
                    minutos_criticos = sum(1 for i in minutos_con_programacion if adherencias_minutos[i] < 50)

                    # Calcular consistencia
                    consistencia = (len(minutos_con_programacion) - minutos_baja) / len(minutos_con_programacion) * 100

                    horas.append({
                        'hora': f"{hora:02d}:00",
                        'adherencia': round(adherencia_promedio, 2),
                        'agentes_programados': round(agentes_promedio, 1),
                        'agentes_activos': round(agentes_activos_promedio, 1),
                        'minutos_programados': len(minutos_con_programacion),
                        'minutos_baja_adherencia': minutos_baja,
                        'minutos_criticos': minutos_criticos,
                        'consistencia': round(consistencia, 1),
                        'estado': '✅ Excelente' if adherencia_promedio >= 90 else
                                 '⚠️  Aceptable' if adherencia_promedio >= 80 else
                                 '🔴 Crítico' if adherencia_promedio >= 60 else
                                 '💀 Grave'
                    })
                else:
                    # No hay programación en la hora
                    horas.append({
                        'hora': f"{hora:02d}:00",
                        'adherencia': 0,
                        'agentes_programados': 0,
                        'agentes_activos': 0,
                        'minutos_programados': 0,
                        'minutos_baja_adherencia': 0,
                        'minutos_criticos': 0,
                        'consistencia': 0,
                        'estado': '⏸️  Sin programación'
                    })

        return horas

    @staticmethod
    def analizar_problemas_adherencia_por_minuto(fecha):
            """
            Detecta problemas específicos minuto a minuto
            Devuelve huecos de productividad y sobrecargas
            """
            from collections import defaultdict

            # 1. Obtener datos minuto a minuto
            resultado = CalculadorAdherencia.calcular_adherencia_por_hora(fecha)

            # 2. Analizar problemas
            problemas = {
                'huecos_productividad': [],  # Minutos con adherencia < 50%
                'sobrecargas': [],           # Minutos con adherencia > 110% (imposible)
                'horas_criticas': [],        # Horas con >30% de minutos problemáticos
                'resumen_por_hora': defaultdict(dict)
            }

            for hora_data in resultado:
                hora = hora_data['hora']

                # 3. Detectar horas críticas
                if hora_data['minutos_criticos'] > 0:
                    problemas['horas_criticas'].append({
                        'hora': hora,
                        'minutos_criticos': hora_data['minutos_criticos'],
                        'adherencia_promedio': hora_data['adherencia']
                    })

                problemas['resumen_por_hora'][hora] = {
                    'adherencia': hora_data['adherencia'],
                    'estado': hora_data.get('estado', 'Sin estado'),
                    'minutos_baja': hora_data.get('minutos_baja_adherencia', 0),
                    'consistencia': hora_data.get('consistencia', 0)
                }

            # 4. Obtener datos detallados minuto a minuto para análisis
            print(f"\n🔍 ANÁLISIS DETALLADO DE ADHERENCIA - {fecha}")
            print("="*60)

            for hora in range(8, 20):
                print(f"\n🕐 HORA {hora:02d}:00")
                print("-"*40)

                # Obtener distribución de adherencia por minuto para esta hora
                distribucion = CalculadorAdherencia.obtener_distribucion_adherencia_por_minuto(fecha, hora)

                if distribucion:
                    # Mostrar histograma simple
                    print("Distribución de adherencia por minuto:")
                    for rango in ['0-20%', '20-40%', '40-60%', '60-80%', '80-100%']:
                        count = distribucion['histograma'].get(rango, 0)
                        bar = '█' * (count // 2)  # Cada █ = 2 minutos
                        print(f"  {rango}: {bar} ({count} minutos)")

                    # Mostrar peores minutos
                    if distribucion['minutos_bajos']:
                        print(f"\n⚠️  Minutos más críticos:")
                        for minuto in distribucion['minutos_bajos'][:5]:  # Top 5 peores
                            print(f"  {hora:02d}:{minuto['minuto']:02d} - {minuto['adherencia']:.1f}% "
                                f"({minuto['agentes_activos']}/{minuto['agentes_programados']} agentes)")

            return problemas

    @staticmethod
    def obtener_distribucion_adherencia_por_minuto(fecha, hora):
        """
        Obtiene la distribución detallada de adherencia para una hora específica
        """
        # 1. Obtener programación para esta hora
        hora_inicio = time(hora, 0)
        hora_fin = time(hora + 1, 0)

        programas_hora = ProgramaDiario.objects.filter(
            fecha=fecha,
            hora_inicio__lt=hora_fin,
            hora_fin__gt=hora_inicio
        )

        if not programas_hora.exists():
            return None

        # 2. Para cada minuto, calcular adherencia
        distribucion = {
            'hora': f"{hora:02d}:00",
            'minutos_analizados': 60,
            'histograma': defaultdict(int),
            'minutos_bajos': [],
            'adherencia_promedio': 0,
            'consistencia': 0
        }

        adherencias_minuto = []

        for minuto in range(60):
            inicio_minuto = time(hora, minuto)
            fin_minuto = time(hora, minuto + 1) if minuto < 59 else time(hora + 1, 0)

            # Agentes programados
            agentes_prog = programas_hora.filter(
                hora_inicio__lt=fin_minuto,
                hora_fin__gt=inicio_minuto
            ).count()

            if agentes_prog == 0:
                continue

            # Agentes activos
            agentes_ids = programas_hora.filter(
                hora_inicio__lt=fin_minuto,
                hora_fin__gt=inicio_minuto
            ).values_list('agente_id', flat=True)

            agentes_activos = RegistroActividad.objects.filter(
                fecha=fecha,
                agente_id__in=agentes_ids,
                hora_inicio__time__lt=fin_minuto,
                hora_fin__time__gt=inicio_minuto,
                tipo_actividad__in=['LLAMADA', 'DISPO', 'CAPAC', 'ADMIN']
            ).values('agente_id').distinct().count()

            # Calcular adherencia
            adherencia = (agentes_activos / agentes_prog) * 100
            adherencias_minuto.append(adherencia)

            # Agregar al histograma
            if adherencia <= 20:
                distribucion['histograma']['0-20%'] += 1
            elif adherencia <= 40:
                distribucion['histograma']['20-40%'] += 1
            elif adherencia <= 60:
                distribucion['histograma']['40-60%'] += 1
            elif adherencia <= 80:
                distribucion['histograma']['60-80%'] += 1
            else:
                distribucion['histograma']['80-100%'] += 1

            # Si es baja, agregar a minutos bajos
            if adherencia < 60:
                distribucion['minutos_bajos'].append({
                    'minuto': minuto,
                    'adherencia': round(adherencia, 1),
                    'agentes_programados': agentes_prog,
                    'agentes_activos': agentes_activos
                })

        # Calcular promedios
        if adherencias_minuto:
            distribucion['adherencia_promedio'] = round(sum(adherencias_minuto) / len(adherencias_minuto), 2)

            # Consistencia: % de minutos con adherencia >= 80%
            minutos_consistentes = sum(1 for a in adherencias_minuto if a >= 80)
            distribucion['consistencia'] = round((minutos_consistentes / len(adherencias_minuto)) * 100, 1)

        # Ordenar minutos bajos por peor adherencia
        distribucion['minutos_bajos'].sort(key=lambda x: x['adherencia'])

        return distribucion

    @staticmethod
    def calcular_impacto_factores(fecha_inicio, fecha_fin):
        """
        Simula el impacto de diferentes factores en la adherencia
        """
        factores = FactorImpacto.objects.all()
        resultados = []
        
        for factor in factores:
            # Simular impacto basado en datos históricos
            impacto_simulado = np.random.normal(
                float(factor.impacto_porcentaje), 
                2.5
            )
            
            resultados.append({
                'factor': factor.nombre,
                'categoria': factor.categoria,
                'impacto_teorico': float(factor.impacto_porcentaje),
                'impacto_simulado': round(impacto_simulado, 2),
                'descripcion': factor.descripcion
            })
        
        return sorted(resultados, key=lambda x: abs(x['impacto_simulado']), reverse=True)
    
    @staticmethod
    def generar_reporte_adherencia(fecha_inicio, fecha_fin):
        """
        Genera reporte completo de adherencia
        """
        # Adherencia por tipo de contrato
        ft_adherencia = CalculadorAdherencia.calcular_adherencia_tipo_contrato(
            'FT', fecha_inicio, fecha_fin
        )
        pt_adherencia = CalculadorAdherencia.calcular_adherencia_tipo_contrato(
            'PT', fecha_inicio, fecha_fin
        )
        
        # Top 5 agentes
        agentes_ft = Agente.objects.filter(tipo_contrato='FT', activo=True)
        agentes_pt = Agente.objects.filter(tipo_contrato='PT', activo=True)
        
        top_ft = []
        top_pt = []
        
        for agente in agentes_ft[:10]:  # Limitamos para performance
            resultado = CalculadorAdherencia.calcular_adherencia_agente(
                agente, fecha_inicio, fecha_fin
            )
            if resultado:
                top_ft.append(resultado)
        
        for agente in agentes_pt[:10]:
            resultado = CalculadorAdherencia.calcular_adherencia_agente(
                agente, fecha_inicio, fecha_fin
            ) 
            if resultado:
                top_pt.append(resultado)
        
        # Ordenar por adherencia
        top_ft.sort(key=lambda x: x['adherencia'], reverse=True)
        top_pt.sort(key=lambda x: x['adherencia'], reverse=True)
        
        return {
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin,
            'full_time': ft_adherencia,
            'part_time': pt_adherencia,
            'top_5_ft': top_ft[:5],
            'top_5_pt': top_pt[:5],
            'diferencia_contratos': round(
                (ft_adherencia['adherencia_promedio'] - pt_adherencia['adherencia_promedio']), 2
            ) if ft_adherencia and pt_adherencia else 0
        }


class SimuladorDatos:
    """
    Clase para simular datos de prueba
    """
    
    @staticmethod
    def crear_agentes_test():
        """Crea agentes de prueba"""
        agentes_data = [
            {'codigo': 'AGT001', 'nombre': 'Ana', 'apellido': 'García', 'tipo_contrato': 'FT'},
            {'codigo': 'AGT002', 'nombre': 'Carlos', 'apellido': 'López', 'tipo_contrato': 'FT'},
            {'codigo': 'AGT003', 'nombre': 'Beatriz', 'apellido': 'Martínez', 'tipo_contrato': 'PT'},
            {'codigo': 'AGT004', 'nombre': 'David', 'apellido': 'Rodríguez', 'tipo_contrato': 'FT'},
            {'codigo': 'AGT005', 'nombre': 'Elena', 'apellido': 'Sánchez', 'tipo_contrato': 'PT'},
            {'codigo': 'AGT006', 'nombre': 'Fernando', 'apellido': 'Pérez', 'tipo_contrato': 'FT'},
            {'codigo': 'AGT007', 'nombre': 'Gabriela', 'apellido': 'Gómez', 'tipo_contrato': 'PT'},
            {'codigo': 'AGT008', 'nombre': 'Héctor', 'apellido': 'Díaz', 'tipo_contrato': 'FT'},
            {'codigo': 'AGT009', 'nombre': 'Irene', 'apellido': 'Fernández', 'tipo_contrato': 'PT'},
            {'codigo': 'AGT010', 'nombre': 'Javier', 'apellido': 'Ruiz', 'tipo_contrato': 'FT'},
        ]
        
        for agente_data in agentes_data:
            Agente.objects.get_or_create(
                codigo=agente_data['codigo'],
                defaults={
                    'nombre': agente_data['nombre'],
                    'apellido': agente_data['apellido'],
                    'tipo_contrato': agente_data['tipo_contrato'],
                    'email': f"{agente_data['nombre'].lower()}.{agente_data['apellido'].lower()}@contactcenter.com",
                    'fecha_ingreso': date.today() - timedelta(days=np.random.randint(30, 365)),
                    'horas_semana': 40 if agente_data['tipo_contrato'] == 'FT' else 20,
                    'activo': True
                }
            )
    
    @staticmethod
    def generar_programacion_mes(mes, año):
        """Genera programación para un mes completo - VERSIÓN CORREGIDA"""
        agentes = Agente.objects.filter(activo=True)
        
        for dia in range(1, 29):  # Simulamos 28 días
            fecha = date(año, mes, dia)
            if fecha.weekday() < 5:  # Solo días laborables
                for agente in agentes:
                    # DETERMINAR TURNO SEGÚN TIPO DE CONTRATO - CORREGIDO
                    if agente.es_full_time:
                        # FULL-TIME: Turnos de 8 horas
                        turnos = ['Matutino (8:00-16:00)', 'Vespertino (12:00-20:00)']
                        turno = np.random.choice(turnos)
                        horas = 8.0
                        
                        # Asignar horas correctas
                        if '8:00' in turno:
                            hora_inicio_obj = time(8, 0)
                            hora_fin_obj = time(16, 0)
                        else:  # '12:00' en turno
                            hora_inicio_obj = time(12, 0)
                            hora_fin_obj = time(20, 0)
                    else:
                        # PART-TIME: Turnos de 4 horas - ¡CORREGIDO!
                        turnos = ['Matutino PT (8:00-12:00)', 'Vespertino PT (14:00-18:00)']
                        turno = np.random.choice(turnos)
                        horas = 4.0
                        
                        # Asignar horas correctas para PT
                        if '8:00' in turno:
                            hora_inicio_obj = time(8, 0)
                            hora_fin_obj = time(12, 0)
                        else:  # '14:00' en turno
                            hora_inicio_obj = time(14, 0)
                            hora_fin_obj = time(18, 0)
                    
                    ProgramaDiario.objects.get_or_create(
                        agente=agente,
                        fecha=fecha,
                        defaults={
                            'turno': turno,
                            'hora_inicio': hora_inicio_obj,
                            'hora_fin': hora_fin_obj,
                            'horas_planificadas': horas,
                            'pausas_planificadas': 1.0 if horas == 8.0 else 0.5
                        }
                    )
    
    @staticmethod
    def generar_actividades_dia(fecha):
        """Genera actividades simuladas para un día"""
        from django.utils import timezone
        from datetime import datetime, date, time
        
        agentes_programados = ProgramaDiario.objects.filter(fecha=fecha)
        
        for programa in agentes_programados:
            agente = programa.agente
            hora_actual = programa.hora_inicio
            
            # Simular día de trabajo
            while hora_actual < programa.hora_fin:
                # Determinar tipo de actividad
                if agente.es_full_time:
                    tipos = ['LLAMADA'] * 5 + ['DISPO'] * 2 + ['PAUSA'] * 1 + ['ADMIN'] * 1
                else:
                    tipos = ['LLAMADA'] * 4 + ['DISPO'] * 3 + ['PAUSA'] * 1 + ['CAPAC'] * 1
                
                tipo = np.random.choice(tipos)
                
                # Duración según tipo
                duraciones = {
                    'LLAMADA': np.random.randint(3, 15),
                    'DISPO': np.random.randint(5, 30),
                    'PAUSA': np.random.randint(5, 15),
                    'CAPAC': np.random.randint(30, 60),
                    'ADMIN': np.random.randint(10, 45),
                    'ALMUERZO': 60,
                    'REUNION': 30,
                    'AUSENTE': 15
                }
                
                duracion = duraciones.get(tipo, 10)
                
                # Crear registro CON ZONA HORARIA
                hora_inicio_dt = datetime.combine(fecha, hora_actual)
                hora_fin_dt = hora_inicio_dt + timedelta(minutes=duracion)
                
                # Convertir a zona horaria aware
                hora_inicio_aware = timezone.make_aware(hora_inicio_dt)
                hora_fin_aware = timezone.make_aware(hora_fin_dt)
                
                RegistroActividad.objects.create(
                    agente=agente,
                    fecha=fecha,
                    hora_inicio=hora_inicio_aware,
                    hora_fin=hora_fin_aware,
                    tipo_actividad=tipo,
                    duracion_minutos=duracion,
                    llamadas_atendidas=1 if tipo == 'LLAMADA' else 0,
                    tiempo_conversacion=duracion if tipo == 'LLAMADA' else 0
                )
                
                # Avanzar hora
                hora_actual = (datetime.combine(date.today(), hora_actual) + 
                              timedelta(minutes=duracion)).time()
    
    @staticmethod
    @transaction.atomic
    def regenerar_datos_completos(dias=7):
        """
        Método TODO EN UNO: Regenera todos los datos del dashboard
        Args:
            dias: Número de días de datos a generar (default: 7)
        """
        print("=" * 60)
        print("🔄 REGENERACIÓN COMPLETA DE DATOS DEL DASHBOARD")
        print("=" * 60)
        
        try:
            # 1. Eliminar datos existentes
            print("\n1. 🗑️ Eliminando datos existentes...")
            RegistroActividad.objects.all().delete()
            ProgramaDiario.objects.all().delete()
            Agente.objects.all().delete()
            print("   ✅ Datos eliminados")
            
            # 2. Crear agentes
            print("\n2. 👥 Creando agentes...")
            SimuladorDatos.crear_agentes_test()
            ft_count = Agente.objects.filter(tipo_contrato='FT').count()
            pt_count = Agente.objects.filter(tipo_contrato='PT').count()
            print(f"   ✅ {Agente.objects.count()} agentes creados")
            print(f"      • Full-Time: {ft_count} agentes")
            print(f"      • Part-Time: {pt_count} agentes")
            
            # 3. Verificar horas semanales
            print("\n3. ⏰ Verificando horas semanales...")
            for agente in Agente.objects.all():
                if agente.tipo_contrato == 'FT' and agente.horas_semana != 40:
                    agente.horas_semana = 40
                    agente.save()
                elif agente.tipo_contrato == 'PT' and agente.horas_semana != 20:
                    agente.horas_semana = 20
                    agente.save()
            print("   ✅ Horas semanales verificadas")
            
            # 4. Generar programación
            print(f"\n4. 📅 Generando programación para {dias} días...")
            hoy = date.today()
            
            for i in range(dias):
                fecha = hoy - timedelta(days=i)
                if fecha.weekday() < 5:  # Solo días laborables
                    for agente in Agente.objects.filter(activo=True):
                        if agente.tipo_contrato == 'FT':
                            # FT: 8 horas
                            if np.random.random() > 0.5:
                                turno = 'Matutino (8:00-16:00)'
                                hora_inicio = time(8, 0)
                                hora_fin = time(16, 0)
                            else:
                                turno = 'Vespertino (12:00-20:00)'
                                hora_inicio = time(12, 0)
                                hora_fin = time(20, 0)
                            horas = 8.0
                        else:
                            # PT: 4 horas - ¡CORRECTO!
                            if np.random.random() > 0.5:
                                turno = 'Matutino PT (8:00-12:00)'
                                hora_inicio = time(8, 0)
                                hora_fin = time(12, 0)
                            else:
                                turno = 'Vespertino PT (14:00-18:00)'
                                hora_inicio = time(14, 0)
                                hora_fin = time(18, 0)
                            horas = 4.0
                        
                        ProgramaDiario.objects.create(
                            agente=agente,
                            fecha=fecha,
                            turno=turno,
                            hora_inicio=hora_inicio,
                            hora_fin=hora_fin,
                            horas_planificadas=horas,
                            pausas_planificadas=1.0 if horas == 8.0 else 0.5
                        )
            
            print(f"   ✅ {ProgramaDiario.objects.count()} programas creados")
            
            # 5. Verificar programación
            print("\n5. 🔍 Verificando programación generada...")
            for tipo, label in [('FT', 'Full-Time'), ('PT', 'Part-Time')]:
                programas = ProgramaDiario.objects.filter(agente__tipo_contrato=tipo)
                if programas.exists():
                    horas_prom = programas.aggregate(avg=Avg('horas_planificadas'))['avg'] or 0
                    print(f"   • {label}: {horas_prom:.1f}h promedio planificadas")
                    
                    if tipo == 'PT' and horas_prom > 5:
                        print(f"     ⚠️  Corrigiendo horas PT...")
                        for programa in programas:
                            if programa.horas_planificadas > 5:
                                programa.horas_planificadas = 4.0
                                programa.save()
            
            # 6. Generar actividades
            print(f"\n6. 📊 Generando actividades para {dias} días...")
            actividades_totales = 0
            
            for i in range(dias):
                fecha = hoy - timedelta(days=i)
                actividades_antes = RegistroActividad.objects.count()
                SimuladorDatos.generar_actividades_dia(fecha)
                actividades_despues = RegistroActividad.objects.count()
                actividades_totales += (actividades_despues - actividades_antes)
            
            print(f"   ✅ {actividades_totales} actividades creadas")
            
            # 7. Resumen final
            print("\n" + "=" * 60)
            print("🎉 REGENERACIÓN COMPLETADA EXITOSAMENTE")
            print("=" * 60)
            
            # Estadísticas finales
            print(f"\n📊 ESTADÍSTICAS FINALES:")
            print(f"   • Agentes totales: {Agente.objects.count()}")
            print(f"   • Programas totales: {ProgramaDiario.objects.count()}")
            print(f"   • Actividades totales: {RegistroActividad.objects.count()}")
            
            # Distribución de actividades
            distribucion = RegistroActividad.objects.values('tipo_actividad').annotate(
                total=Count('id')
            ).order_by('-total')
            
            print(f"\n📈 DISTRIBUCIÓN DE ACTIVIDADES:")
            for item in distribucion:
                print(f"   • {item['tipo_actividad']}: {item['total']}")
            
            # Verificación de integridad
            print(f"\n✅ VERIFICACIÓN DE INTEGRIDAD:")
            
            # Verificar que PT tenga ~4h promedio
            programas_pt = ProgramaDiario.objects.filter(agente__tipo_contrato='PT')
            horas_pt_prom = programas_pt.aggregate(avg=Avg('horas_planificadas'))['avg'] or 0
            
            if 3.5 <= horas_pt_prom <= 4.5:
                print(f"   • PT: {horas_pt_prom:.1f}h promedio ✓")
            else:
                print(f"   • PT: {horas_pt_prom:.1f}h promedio (debería ser ~4h)")
            
            # Verificar que FT tenga ~8h promedio
            programas_ft = ProgramaDiario.objects.filter(agente__tipo_contrato='FT')
            horas_ft_prom = programas_ft.aggregate(avg=Avg('horas_planificadas'))['avg'] or 0
            
            if 7.5 <= horas_ft_prom <= 8.5:
                print(f"   • FT: {horas_ft_prom:.1f}h promedio ✓")
            else:
                print(f"   • FT: {horas_ft_prom:.1f}h promedio (debería ser ~8h)")
            
            print(f"\n🎯 INSTRUCCIONES:")
            print(f"   1. Iniciar servidor: python manage.py runserver 0.0.0.0:8000")
            print(f"   2. Acceder al dashboard: http://localhost:8000")
            print(f"   3. Verificar métricas en tiempo real")
            
            return True
            
        except Exception as e:
            print(f"\n❌ ERROR durante la regeneración: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    @staticmethod
    def verificar_datos():
        """
        Verifica la integridad de los datos existentes
        """
        print("🔍 VERIFICANDO INTEGRIDAD DE DATOS")
        print("=" * 50)
        
        problemas = []
        
        # 1. Verificar agentes
        agentes = Agente.objects.all()
        if not agentes.exists():
            problemas.append("No hay agentes creados")
        else:
            print(f"✅ Agentes: {agentes.count()} total")
            print(f"   • FT: {agentes.filter(tipo_contrato='FT').count()}")
            print(f"   • PT: {agentes.filter(tipo_contrato='PT').count()}")
            
            # Verificar horas semanales
            for agente in agentes:
                if agente.tipo_contrato == 'FT' and agente.horas_semana != 40:
                    problemas.append(f"Agente {agente.codigo} FT tiene {agente.horas_semana}h (debería ser 40h)")
                elif agente.tipo_contrato == 'PT' and agente.horas_semana != 20:
                    problemas.append(f"Agente {agente.codigo} PT tiene {agente.horas_semana}h (debería ser 20h)")
        
        # 2. Verificar programación
        programas = ProgramaDiario.objects.all()
        if not programas.exists():
            problemas.append("No hay programación creada")
        else:
            print(f"\n✅ Programas: {programas.count()} total")
            
            # Verificar horas planificadas por tipo
            for tipo, label in [('FT', 'Full-Time'), ('PT', 'Part-Time')]:
                programas_tipo = programas.filter(agente__tipo_contrato=tipo)
                if programas_tipo.exists():
                    horas_prom = programas_tipo.aggregate(avg=Avg('horas_planificadas'))['avg'] or 0
                    print(f"   • {label}: {horas_prom:.1f}h promedio")
                    
                    if tipo == 'PT' and horas_prom > 5:
                        problemas.append(f"PT tiene {horas_prom:.1f}h promedio (debería ser ~4h)")
                    if tipo == 'FT' and horas_prom < 7:
                        problemas.append(f"FT tiene {horas_prom:.1f}h promedio (debería ser ~8h)")
        
        # 3. Verificar actividades
        actividades = RegistroActividad.objects.all()
        if not actividades.exists():
            problemas.append("No hay actividades creadas")
        else:
            print(f"\n✅ Actividades: {actividades.count()} total")
            
            # Distribución
            distribucion = actividades.values('tipo_actividad').annotate(
                total=Count('id')
            ).order_by('-total')
            
            for item in distribucion[:5]:  # Top 5
                print(f"   • {item['tipo_actividad']}: {item['total']}")
        
        # 4. Resumen de problemas
        if problemas:
            print(f"\n⚠️  PROBLEMAS DETECTADOS:")
            for problema in problemas:
                print(f"   • {problema}")
            
            print(f"\n💡 RECOMENDACIÓN:")
            print(f"   Ejecutar: SimuladorDatos.regenerar_datos_completos()")
            return False
        else:
            print(f"\n🎉 TODOS LOS DATOS SON VÁLIDOS")
            return True
    
    @staticmethod
    def crear_datos_rapidos():
        """
        Crea datos rápidos para pruebas (sin eliminar datos existentes)
        """
        print("⚡ CREANDO DATOS RÁPIDOS PARA PRUEBAS")
        print("=" * 50)
        
        try:
            hoy = date.today()
            
            # 1. Crear agentes si no existen
            if not Agente.objects.exists():
                SimuladorDatos.crear_agentes_test()
                print(f"✅ {Agente.objects.count()} agentes creados")
            else:
                print(f"✅ Ya existen {Agente.objects.count()} agentes")
            
            # 2. Crear programación para hoy si no existe
            if not ProgramaDiario.objects.filter(fecha=hoy).exists():
                for agente in Agente.objects.filter(activo=True):
                    if agente.tipo_contrato == 'FT':
                        # FT: 8 horas
                        turno = 'Matutino (8:00-16:00)' if np.random.random() > 0.5 else 'Vespertino (12:00-20:00)'
                        hora_inicio = time(8, 0) if '8:00' in turno else time(12, 0)
                        hora_fin = time(16, 0) if '16:00' in turno else time(20, 0)
                        horas = 8.0
                    else:
                        # PT: 4 horas
                        turno = 'Matutino PT (8:00-12:00)' if np.random.random() > 0.5 else 'Vespertino PT (14:00-18:00)'
                        hora_inicio = time(8, 0) if '8:00' in turno else time(14, 0)
                        hora_fin = time(12, 0) if '12:00' in turno else time(18, 0)
                        horas = 4.0
                    
                    ProgramaDiario.objects.create(
                        agente=agente,
                        fecha=hoy,
                        turno=turno,
                        hora_inicio=hora_inicio,
                        hora_fin=hora_fin,
                        horas_planificadas=horas,
                        pausas_planificadas=1.0 if horas == 8.0 else 0.5
                    )
                print(f"✅ Programación creada para hoy")
            else:
                print(f"✅ Ya existe programación para hoy")
            
            # 3. Crear actividades para hoy si no existen
            if not RegistroActividad.objects.filter(fecha=hoy).exists():
                SimuladorDatos.generar_actividades_dia(hoy)
                print(f"✅ Actividades creadas para hoy")
            else:
                print(f"✅ Ya existen actividades para hoy")
            
            print(f"\n🎉 DATOS RÁPIDOS CREADOS EXITOSAMENTE")
            return True
            
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            return False


# Clase de utilidades adicionales
class DashboardUtilidades:
    """
    Utilidades adicionales para el dashboard
    """
    
    @staticmethod
    def obtener_resumen_sistema():
        """
        Obtiene un resumen del estado del sistema
        """
        hoy = date.today()
        
        return {
            'agentes_totales': Agente.objects.count(),
            'agentes_activos': Agente.objects.filter(activo=True).count(),
            'agentes_ft': Agente.objects.filter(tipo_contrato='FT', activo=True).count(),
            'agentes_pt': Agente.objects.filter(tipo_contrato='PT', activo=True).count(),
            'programas_hoy': ProgramaDiario.objects.filter(fecha=hoy).count(),
            'actividades_hoy': RegistroActividad.objects.filter(fecha=hoy).count(),
            'ultima_actividad': RegistroActividad.objects.order_by('-hora_inicio').first(),
            'estado': 'activo' if ProgramaDiario.objects.filter(fecha=hoy).exists() else 'inactivo'
        }
    
    @staticmethod
    def calcular_adherencia_instantanea():
        """
        Calcula adherencia instantánea para el día actual
        """
        hoy = date.today()
        
        # Programación de hoy
        programas_hoy = ProgramaDiario.objects.filter(fecha=hoy)
        
        if not programas_hoy.exists():
            return {'adherencia': 0, 'estado': 'sin_programacion'}
        
        # Actividades productivas de hoy
        actividades_productivas = RegistroActividad.objects.filter(
            fecha=hoy,
            tipo_actividad__in=['LLAMADA', 'DISPO', 'CAPAC', 'ADMIN']
        )
        
        # Calcular tiempos
        tiempo_planificado = sum(float(p.horas_planificadas) * 60 for p in programas_hoy)
        tiempo_productivo = actividades_productivas.aggregate(total=Sum('duracion_minutos'))['total'] or 0
        
        if tiempo_planificado > 0:
            adherencia = min((tiempo_productivo / tiempo_planificado) * 100, 100)
        else:
            adherencia = 0
        
        return {
            'adherencia': round(adherencia, 2),
            'tiempo_planificado_min': tiempo_planificado,
            'tiempo_productivo_min': tiempo_productivo,
            'agentes_programados': programas_hoy.count(),
            'actividades_productivas': actividades_productivas.count(),
            'estado': 'activo' if tiempo_productivo > 0 else 'inactivo'
        }