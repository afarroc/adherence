# setup_dasboard.py - VERSIÓN CORREGIDA
import os
import django
from datetime import date, timedelta
import sys

# Añadir el directorio del proyecto al path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'adherence_dasboard.settings')

try:
    django.setup()
except Exception as e:
    print(f"❌ Error configurando Django: {e}")
    sys.exit(1)

from django.contrib.auth.models import User
from django.utils import timezone
from dashboard.models import KPIMeta, FactorImpacto, Agente, ProgramaDiario, RegistroActividad
from dashboard.utils import SimuladorDatos

def inicializar_sistema():
    """Inicializa el sistema con datos básicos"""
    
    print("=" * 50)
    print("🚀 Inicializando Dashboard KPI de Adherencia")
    print("=" * 50)
    
    try:
        # 1. Crear superusuario si no existe
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser(
                username='admin',
                email='admin@contactcenter.com',
                password='admin123'
            )
            print("✅ Superusuario creado: admin / admin123")
        else:
            print("ℹ️  Superusuario ya existe")
    
        # 2. Crear KPIs meta
        kpi_defaults = [
            {
                'nombre': 'Adherencia General',
                'descripcion': 'Meta de adherencia general del contact center',
                'tipo': 'ADHERENCIA',
                'valor_meta': 95.0,
                'valor_minimo': 85.0,
                'fecha_inicio': date.today(),
                'activo': True
            },
            {
                'nombre': 'Adherencia Full-Time',
                'descripcion': 'Meta específica para agentes full-time',
                'tipo': 'ADHERENCIA',
                'valor_meta': 96.0,
                'valor_minimo': 88.0,
                'fecha_inicio': date.today(),
                'activo': True
            },
            {
                'nombre': 'Adherencia Part-Time',
                'descripcion': 'Meta específica para agentes part-time',
                'tipo': 'ADHERENCIA',
                'valor_meta': 93.0,
                'valor_minimo': 83.0,
                'fecha_inicio': date.today(),
                'activo': True
            }
        ]
        
        for kpi_data in kpi_defaults:
            KPIMeta.objects.get_or_create(
                nombre=kpi_data['nombre'],
                defaults=kpi_data
            )
        
        print("✅ KPIs configurados")
        
        # 3. Crear factores de impacto
        factores_default = [
            {
                'nombre': 'Fallas Técnicas',
                'descripcion': 'Problemas con sistemas, teléfonos o internet',
                'impacto_porcentaje': 8.5,
                'categoria': 'TECNICO'
            },
            {
                'nombre': 'Capacitación Insuficiente',
                'descripcion': 'Falta de entrenamiento en procesos nuevos',
                'impacto_porcentaje': 6.2,
                'categoria': 'HUMANO'
            },
            {
                'nombre': 'Sobre reuniones',
                'descripcion': 'Exceso de reuniones que reducen tiempo operativo',
                'impacto_porcentaje': 5.8,
                'categoria': 'OPERATIVO'
            },
            {
                'nombre': 'Complejidad Llamadas',
                'descripcion': 'Llamadas más complejas de lo esperado',
                'impacto_porcentaje': 4.3,
                'categoria': 'CLIENTE'
            },
            {
                'nombre': 'Rotación de Personal',
                'descripcion': 'Alta rotación afecta experiencia acumulada',
                'impacto_porcentaje': 7.1,
                'categoria': 'HUMANO'
            }
        ]
        
        for factor_data in factores_default:
            FactorImpacto.objects.get_or_create(
                nombre=factor_data['nombre'],
                defaults=factor_data
            )
        
        print("✅ Factores de impacto configurados")
        
        # 4. Preguntar si generar datos de prueba
        print("\n" + "-" * 50)
        respuesta = input("¿Generar datos de prueba? (s/n): ")
        
        if respuesta.lower() == 's':
            print("\n🎲 Generando datos de prueba...")
            
            try:
                # Crear agentes de prueba
                print("👥 Creando agentes de prueba...")
                SimuladorDatos.crear_agentes_test()
                
                # Generar programación del mes actual
                print("📅 Generando programación...")
                hoy = date.today()
                SimuladorDatos.generar_programacion_mes(hoy.month, hoy.year)
                
                # Generar actividades de los últimos 7 días
                print("📊 Generando actividades...")
                for i in range(7):
                    fecha_simulada = hoy - timedelta(days=i)
                    SimuladorDatos.generar_actividades_dia(fecha_simulada)
                
                # Mostrar estadísticas usando los modelos directamente
                print(f"\n📊 Datos generados:")
                print(f"   • Agentes: {Agente.objects.count()}")
                print(f"   • Programas: {ProgramaDiario.objects.count()}")
                print(f"   • Actividades: {RegistroActividad.objects.count()}")
                
            except Exception as e:
                print(f"⚠️  Error generando datos de prueba: {e}")
                print("   Continúe con la configuración básica...")
        
        print("\n" + "=" * 50)
        print("🎉 Sistema inicializado correctamente!")
        print("\n📋 Para iniciar el servidor:")
        print("   python manage.py runserver 0.0.0.0:8000")
        print("\n🔗 Acceso:")
        print("   Dashboard: http://localhost:8000")
        print("   Admin: http://localhost:8000/admin")
        print("        Usuario: admin")
        print("        Contraseña: admin123")
        print("=" * 50)
        
    except Exception as e:
        print(f"❌ Error durante la inicialización: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    inicializar_sistema()