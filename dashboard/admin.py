from django.contrib import admin
from .models import *

@admin.register(Agente)
class AgenteAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nombre', 'apellido', 'tipo_contrato', 'activo']
    list_filter = ['tipo_contrato', 'activo']
    search_fields = ['codigo', 'nombre', 'apellido']
    list_per_page = 20

@admin.register(ProgramaDiario)
class ProgramaDiarioAdmin(admin.ModelAdmin):
    list_display = ['agente', 'fecha', 'turno', 'horas_planificadas']
    list_filter = ['fecha', 'turno']
    search_fields = ['agente__codigo', 'agente__nombre']
    date_hierarchy = 'fecha'

@admin.register(RegistroActividad)
class RegistroActividadAdmin(admin.ModelAdmin):
    list_display = ['agente', 'fecha', 'tipo_actividad', 'duracion_minutos']
    list_filter = ['tipo_actividad', 'fecha']
    search_fields = ['agente__codigo']
    date_hierarchy = 'fecha'

@admin.register(KPIMeta)
class KPIMetaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'tipo', 'valor_meta', 'activo']
    list_filter = ['tipo', 'activo']

@admin.register(FactorImpacto)
class FactorImpactoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'categoria', 'impacto_porcentaje']
    list_filter = ['categoria']