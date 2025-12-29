from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard_principal, name='dashboard_principal'),
    path('regenerate/', views.regenerate_data, name='regenerate_data'),
    path('matrix/', views.matrix_view, name='matrix'),
    path('matrix/<int:agente_id>/', views.matrix_view, name='matrix_view'),
    path('kpi/<str:tipo>/', views.kpi_detalle, name='kpi_detalle'),

    # APIs
    path('api/adherencia-diaria/', views.api_adherencia_diaria, name='api_adherencia_diaria'),
    path('api/simular-datos/', views.api_simular_datos, name='api_simular_datos'),
    path('api/agentes-top/', views.api_agentes_top, name='api_agentes_top'),
]