# dashboard/context_processors.py - VERSIÓN CORREGIDA

from django.utils import timezone
from django.conf import settings  # ✅ ¡IMPORTANTE! Agregar esta línea
from datetime import date, timedelta
from django.db.models import Count, Sum, Avg, Q
from .models import Agente, KPIMeta, ProgramaDiario, RegistroActividad
from .utils import CalculadorAdherencia

def kpi_data(request):
    """
    Context processor para datos generales del dashboard
    Se ejecuta automáticamente en todas las vistas
    """
    # Inicializamos con valores por defecto
    context = {
        'hoy': date.today(),
        'kpi_meta': None,
        'total_agentes': 0,
        'agentes_ft': 0,
        'agentes_pt': 0,
        'estado_sistema': 'inactivo'
    }
    
    # Solo procesar si la base de datos está lista
    # (evita errores durante migraciones iniciales)
    try:
        # 1. Estadísticas básicas de agentes
        agentes_activos = Agente.objects.filter(activo=True)
        context['total_agentes'] = agentes_activos.count()
        context['agentes_ft'] = agentes_activos.filter(tipo_contrato='FT').count()
        context['agentes_pt'] = agentes_activos.filter(tipo_contrato='PT').count()
        
        # 2. Obtener KPI meta activo
        context['kpi_meta'] = KPIMeta.objects.filter(activo=True).first()
        
        # 3. Verificar si hay datos en el sistema
        hoy = date.today()
        tiene_programacion_hoy = ProgramaDiario.objects.filter(fecha=hoy).exists()
        tiene_actividades_hoy = RegistroActividad.objects.filter(fecha=hoy).exists()
        
        if tiene_programacion_hoy and tiene_actividades_hoy:
            context['estado_sistema'] = 'activo'
        elif tiene_programacion_hoy:
            context['estado_sistema'] = 'parcial'
        else:
            context['estado_sistema'] = 'inactivo'
        
        # 4. Datos para el header/navbar (si el usuario está autenticado)
        if request.user.is_authenticated:
            # Calcular adherencia del día actual rápidamente
            fecha_hoy = date.today()
            
            # Solo calcular si hay datos suficientes
            if tiene_actividades_hoy:
                # Obtener agentes programados hoy
                agentes_programados_hoy = ProgramaDiario.objects.filter(
                    fecha=fecha_hoy
                ).values('agente').distinct().count()
                
                # Actividades productivas hoy
                actividades_productivas = RegistroActividad.objects.filter(
                    fecha=fecha_hoy,
                    tipo_actividad__in=['LLAMADA', 'DISPO', 'CAPAC']
                ).count()
                
                if agentes_programados_hoy > 0:
                    context['adherencia_hoy_quick'] = round(
                        (actividades_productivas / agentes_programados_hoy) * 100, 1
                    )
                else:
                    context['adherencia_hoy_quick'] = 0
            else:
                context['adherencia_hoy_quick'] = 0
            
            # Agregar indicador de alertas (simulado)
            context['alertas_pendientes'] = {
                'criticas': 0,
                'advertencias': 0,
                'informativas': 0
            }
            
            # Si hay agentes FT, calcular rápidamente su adherencia
            if context['agentes_ft'] > 0:
                # Cálculo simplificado para el context processor
                fecha_inicio = fecha_hoy - timedelta(days=7)
                ft_data = CalculadorAdherencia.calcular_adherencia_tipo_contrato(
                    'FT', fecha_inicio, fecha_hoy
                )
                if ft_data:
                    context['ft_adherencia_rapida'] = ft_data['adherencia_promedio']
            
            # Configuración del usuario
            context['user_config'] = {
                'notifications': True,
                'auto_refresh': True,
                'theme': 'light'  # o 'dark'
            }
        
        # 5. Información del entorno - ¡CORREGIDO!
        context['entorno'] = {
            'modo': 'desarrollo' if settings.DEBUG else 'producción',  # ✅ Ahora funciona
            'version': '1.0.0',
            'ultima_actualizacion': timezone.now()
        }
        
    except Exception as e:
        # En caso de error (ej. tablas no creadas aún), usar valores por defecto
        print(f"⚠️ Error en context processor: {e}")
        context['estado_sistema'] = 'error'
    
    return context


def filtros_comunes(request):
    """
    Context processor para filtros y rangos de fechas comunes
    """
    context = {}
    
    # Rangos de fecha predeterminados
    hoy = date.today()
    context['rangos_fecha'] = {
        'hoy': hoy,
        'ayer': hoy - timedelta(days=1),
        'ultima_semana': {
            'inicio': hoy - timedelta(days=7),
            'fin': hoy
        },
        'ultimo_mes': {
            'inicio': hoy - timedelta(days=30),
            'fin': hoy
        },
        'mes_actual': {
            'inicio': hoy.replace(day=1),
            'fin': hoy
        }
    }
    
    # Obtener parámetros de filtro de la URL o session
    filtro_tipo = request.GET.get('tipo', request.session.get('filtro_tipo', 'todos'))
    filtro_fecha_inicio = request.GET.get('fecha_inicio', 
                                         request.session.get('filtro_fecha_inicio'))
    filtro_fecha_fin = request.GET.get('fecha_fin', 
                                      request.session.get('filtro_fecha_fin'))
    
    # Guardar en session para persistencia
    if 'filtro_tipo' in request.GET:
        request.session['filtro_tipo'] = filtro_tipo
    if 'filtro_fecha_inicio' in request.GET:
        request.session['filtro_fecha_inicio'] = filtro_fecha_inicio
    if 'filtro_fecha_fin' in request.GET:
        request.session['filtro_fecha_fin'] = filtro_fecha_fin
    
    context['filtros_activos'] = {
        'tipo': filtro_tipo,
        'fecha_inicio': filtro_fecha_inicio,
        'fecha_fin': filtro_fecha_fin
    }
    
    return context


def estadisticas_globales(request):
    """
    Estadísticas globales para mostrar en el sidebar o header
    """
    context = {}
    
    try:
        hoy = date.today()
        semana_pasada = hoy - timedelta(days=7)
        
        # 1. Total de llamadas hoy
        llamadas_hoy = RegistroActividad.objects.filter(
            fecha=hoy,
            tipo_actividad='LLAMADA'
        ).count()
        
        # 2. Agentes activos hoy (con al menos una actividad)
        agentes_activos_hoy = RegistroActividad.objects.filter(
            fecha=hoy
        ).values('agente').distinct().count()
        
        # 3. Tiempo promedio de llamada
        tiempo_llamadas = RegistroActividad.objects.filter(
            fecha=hoy,
            tipo_actividad='LLAMADA',
            tiempo_conversacion__gt=0
        ).aggregate(
            promedio=Avg('tiempo_conversacion'),
            total=Sum('tiempo_conversacion')
        )
        
        # 4. Comparación con ayer
        ayer = hoy - timedelta(days=1)
        llamadas_ayer = RegistroActividad.objects.filter(
            fecha=ayer,
            tipo_actividad='LLAMADA'
        ).count()
        
        variacion_llamadas = 0
        if llamadas_ayer > 0:
            variacion_llamadas = round(((llamadas_hoy - llamadas_ayer) / llamadas_ayer) * 100, 1)
        
        context['estadisticas_hoy'] = {
            'llamadas_atendidas': llamadas_hoy,
            'agentes_activos': agentes_activos_hoy,
            'tiempo_promedio_llamada': round(tiempo_llamadas['promedio'] or 0, 1),
            'tiempo_total_conversacion': tiempo_llamadas['total'] or 0,
            'variacion_llamadas_vs_ayer': variacion_llamadas,
            'llamadas_ayer': llamadas_ayer
        }
        
        # 5. Programación para mañana
        manana = hoy + timedelta(days=1)
        agentes_programados_manana = ProgramaDiario.objects.filter(
            fecha=manana
        ).count()
        
        context['programacion_manana'] = {
            'agentes_programados': agentes_programados_manana,
            'fecha': manana
        }
        
    except Exception as e:
        # En caso de error, retornar estructura vacía
        context['estadisticas_hoy'] = {}
        context['programacion_manana'] = {}
    
    return context


def configuracion_ui(request):
    """
    Configuración de UI/UX que puede cambiar por usuario
    """
    context = {}
    
    # Configuración por defecto
    ui_config = {
        'tema': 'claro',
        'densidad': 'normal',  # compacto, normal, espaciado
        'orden_tablas': 'descendente',
        'mostrar_graficos': True,
        'mostrar_detalles': True,
        'auto_refresh': True,
        'intervalo_refresh': 30000,  # milisegundos
    }
    
    # Sobrescribir con preferencias del usuario si está autenticado
    if request.user.is_authenticated:
        # Aquí podrías cargar de la base de datos las preferencias del usuario
        # Por ahora usamos la session
        user_prefs = request.session.get('ui_preferences', {})
        ui_config.update(user_prefs)
    
    # También permitir override por parámetros GET (para testing)
    if 'tema' in request.GET:
        ui_config['tema'] = request.GET['tema']
        request.session['ui_preferences'] = ui_config
    
    context['ui_config'] = ui_config
    
    # Determinar clases CSS según configuración
    context['css_classes'] = {
        'tema': f"theme-{ui_config['tema']}",
        'densidad': f"density-{ui_config['densidad']}",
        'sidebar': 'sidebar-collapsed' if ui_config.get('sidebar_collapsed', False) else ''
    }
    
    return context