from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import DecimalField, ExpressionWrapper, F, Sum
from django.utils import timezone

from appointments.models import Appointment
from core.models import AuditModel
from patients.models import Patient


class EncounterStatus(models.TextChoices):
    OPEN = 'OPEN', 'Abierta'
    IN_PROGRESS = 'IN_PROGRESS', 'En atencion'
    COMPLETED = 'COMPLETED', 'Cerrada'
    CANCELED = 'CANCELED', 'Cancelada'


class DiagnosisCodingSystem(models.TextChoices):
    CIE10 = 'CIE10', 'CIE-10'


class ClinicalOrderType(models.TextChoices):
    LAB = 'LAB', 'Laboratorio'
    IMAGE = 'IMAGE', 'Imagen'
    PROCEDURE = 'PROCEDURE', 'Procedimiento'
    MEDICATION = 'MEDICATION', 'Medicacion'
    OTHER = 'OTHER', 'Otro'


class OrderPriority(models.TextChoices):
    ROUTINE = 'ROUTINE', 'Rutina'
    URGENT = 'URGENT', 'Urgente'
    STAT = 'STAT', 'Inmediata'


class OrderStatus(models.TextChoices):
    REQUESTED = 'REQUESTED', 'Solicitada'
    IN_PROGRESS = 'IN_PROGRESS', 'En proceso'
    COMPLETED = 'COMPLETED', 'Completada'
    CANCELED = 'CANCELED', 'Cancelada'


class DiagnosisCatalogEntry(AuditModel):
    system = models.CharField(max_length=20, choices=DiagnosisCodingSystem.choices, default=DiagnosisCodingSystem.CIE10)
    code = models.CharField('Codigo', max_length=20)
    title = models.CharField('Descripcion', max_length=255)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['system', 'code']
        constraints = [
            models.UniqueConstraint(fields=['system', 'code'], name='clinical_diag_catalog_system_code_unique'),
        ]

    def __str__(self):
        return f'{self.code} - {self.title}'


class ClinicalNoteTemplate(AuditModel):
    name = models.CharField('Nombre', max_length=120)
    category = models.CharField('Categoria', max_length=60, blank=True)
    version = models.PositiveIntegerField(default=1)
    diagnosis = models.CharField('Diagnostico sugerido', max_length=255, blank=True)
    subjective = models.TextField('Subjetivo sugerido', blank=True)
    objective = models.TextField('Objetivo sugerido', blank=True)
    assessment = models.TextField('Evaluacion sugerida', blank=True)
    plan = models.TextField('Plan sugerido', blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name', '-version']
        constraints = [
            models.UniqueConstraint(fields=['name', 'version'], name='clinical_template_name_version_unique'),
        ]

    def __str__(self):
        return f'{self.name} v{self.version}'


class ClinicalEncounter(AuditModel):
    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name='clinical_encounters')
    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.PROTECT,
        related_name='clinical_encounters',
        null=True,
        blank=True,
    )
    template = models.ForeignKey(
        ClinicalNoteTemplate,
        on_delete=models.PROTECT,
        related_name='encounters',
        null=True,
        blank=True,
    )
    started_at = models.DateTimeField('Fecha y hora de atencion')
    chief_complaint = models.CharField('Motivo clinico', max_length=255)
    subjective = models.TextField('Subjetivo', blank=True)
    objective = models.TextField('Objetivo', blank=True)
    diagnosis = models.CharField('Diagnostico', max_length=255, blank=True)
    assessment = models.TextField('Evaluacion', blank=True)
    plan = models.TextField('Plan', blank=True)
    status = models.CharField(max_length=20, choices=EncounterStatus.choices, default=EncounterStatus.OPEN)

    class Meta:
        ordering = ['-started_at']

    def clean(self):
        super().clean()
        if self.appointment_id and self.patient_id and self.appointment.patient_id != self.patient_id:
            raise ValidationError({'appointment': 'La cita seleccionada no pertenece al paciente indicado.'})

    def __str__(self):
        return f'Atencion {self.patient} - {self.started_at:%Y-%m-%d %H:%M}'

    @property
    def total_supply_cost(self):
        if not self.pk:
            return Decimal('0.00')

        total = self.stock_movements.filter(movement_type='CONSUMPTION').aggregate(
            total=Sum(
                ExpressionWrapper(
                    F('quantity') * F('lot__unit_cost'),
                    output_field=DecimalField(max_digits=14, decimal_places=2),
                )
            )
        )['total']
        return total or Decimal('0.00')


class ClinicalOrder(AuditModel):
    encounter = models.ForeignKey(ClinicalEncounter, on_delete=models.CASCADE, related_name='orders')
    order_type = models.CharField('Tipo', max_length=20, choices=ClinicalOrderType.choices)
    title = models.CharField('Titulo', max_length=160)
    priority = models.CharField(max_length=20, choices=OrderPriority.choices, default=OrderPriority.ROUTINE)
    status = models.CharField(max_length=20, choices=OrderStatus.choices, default=OrderStatus.REQUESTED)
    requested_at = models.DateTimeField('Fecha de solicitud', default=timezone.now)
    instructions = models.TextField('Indicaciones', blank=True)
    result_notes = models.TextField('Resultado', blank=True)
    completed_at = models.DateTimeField('Fecha de cierre', null=True, blank=True)

    class Meta:
        ordering = ['-requested_at', '-created_at']

    def clean(self):
        super().clean()
        if self.completed_at and self.completed_at < self.requested_at:
            raise ValidationError({'completed_at': 'La fecha de cierre no puede ser anterior a la solicitud.'})

    def save(self, *args, **kwargs):
        if self.status == OrderStatus.COMPLETED and not self.completed_at:
            self.completed_at = timezone.now()
        elif self.status != OrderStatus.COMPLETED:
            self.completed_at = None
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.get_order_type_display()} - {self.title}'
