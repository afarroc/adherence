from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator

class Agente(models.Model):
    TIPO_CONTRATO = [
        ('PT', 'Part-Time'),
        ('FT', 'Full-Time'),
        ('TEMP', 'Temporal'),
    ]
    
    codigo = models.CharField(max_length=10, unique=True)
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    tipo_contrato = models.CharField(max_length=4, choices=TIPO_CONTRATO)
    email = models.EmailField()
    fecha_ingreso = models.DateField()
    horas_semana = models.IntegerField(default=40)
    supervisor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    activo = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['codigo']
    
    def __str__(self):
        return f"{self.codigo} - {self.nombre} {self.apellido}"
    
    @property
    def es_part_time(self):
        return self.tipo_contrato == 'PT'
    
    @property
    def es_full_time(self):
        return self.tipo_contrato == 'FT'

class ProgramaDiario(models.Model):
    agente = models.ForeignKey(Agente, on_delete=models.CASCADE, related_name='programas')
    fecha = models.DateField()
    turno = models.CharField(max_length=50)
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    horas_planificadas = models.DecimalField(max_digits=4, decimal_places=2)
    pausas_planificadas = models.DecimalField(max_digits=4, decimal_places=2, default=1.0)
    
    class Meta:
        unique_together = ['agente', 'fecha']
        ordering = ['fecha', 'hora_inicio']
    
    def __str__(self):
        return f"{self.agente.codigo} - {self.fecha}"

class RegistroActividad(models.Model):
    TIPO_ACTIVIDAD = [
        ('LLAMADA', 'En llamada'),
        ('PAUSA', 'Pausa activa'),
        ('DISPO', 'Disponible'),
        ('CAPAC', 'Capacitación'),
        ('REUNION', 'Reunión'),
        ('ADMIN', 'Tareas administrativas'),
        ('ALMUERZO', 'Almuerzo'),
        ('AUSENTE', 'Ausente'),
    ]
    
    agente = models.ForeignKey(Agente, on_delete=models.CASCADE, related_name='actividades')
    fecha = models.DateField()
    hora_inicio = models.DateTimeField()
    hora_fin = models.DateTimeField()
    tipo_actividad = models.CharField(max_length=10, choices=TIPO_ACTIVIDAD)
    duracion_minutos = models.IntegerField()
    llamadas_atendidas = models.IntegerField(default=0)
    tiempo_conversacion = models.IntegerField(default=0)  # en minutos
    
    class Meta:
        ordering = ['-fecha', '-hora_inicio']
        indexes = [
            models.Index(fields=['agente', 'fecha']),
            models.Index(fields=['tipo_actividad', 'fecha']),
        ]
    
    def __str__(self):
        return f"{self.agente.codigo} - {self.tipo_actividad} - {self.fecha}"

class KPIMeta(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField()
    tipo = models.CharField(max_length=20, choices=[
        ('ADHERENCIA', 'Adherencia'),
        ('SERVICIO', 'Nivel de Servicio'),
        ('SATISFACCION', 'Satisfacción'),
    ])
    valor_meta = models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(0), MaxValueValidator(100)])
    valor_minimo = models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(0), MaxValueValidator(100)])
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField(null=True, blank=True)
    activo = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.nombre} - Meta: {self.valor_meta}%"

class FactorImpacto(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField()
    impacto_porcentaje = models.DecimalField(max_digits=4, decimal_places=2)
    categoria = models.CharField(max_length=50, choices=[
        ('TECNICO', 'Técnico'),
        ('OPERATIVO', 'Operativo'),
        ('HUMANO', 'Recursos Humanos'),
        ('CLIENTE', 'Cliente'),
    ])
    
    def __str__(self):
        return f"{self.nombre} ({self.impacto_porcentaje}%)"