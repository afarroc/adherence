from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_principal, name='dashboard_principal'),
    path('kpi/<str:tipo>/', views.kpi_detalle, name='kpi_detalle'),
    
    # APIs
    path('api/adherencia-diaria/', views.api_adherencia_diaria, name='api_adherencia_diaria'),
    path('api/simular-datos/', views.api_simular_datos, name='api_simular_datos'),
    path('api/agentes-top/', views.api_agentes_top, name='api_agentes_top'),
]