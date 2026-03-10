from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from clinical.models import ClinicalEncounter
from core.models import AuditModel


class MovementType(models.TextChoices):
    RECEIPT = 'RECEIPT', 'Ingreso'
    CONSUMPTION = 'CONSUMPTION', 'Consumo'
    ADJUSTMENT_IN = 'ADJUSTMENT_IN', 'Ajuste positivo'
    ADJUSTMENT_OUT = 'ADJUSTMENT_OUT', 'Ajuste negativo'


class SupplyItem(AuditModel):
    name = models.CharField('Nombre', max_length=150)
    sku = models.CharField('SKU', max_length=40, unique=True)
    unit_of_measure = models.CharField('Unidad', max_length=30, default='unidad')
    track_expiration = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.sku})'


class SupplyLot(AuditModel):
    item = models.ForeignKey(SupplyItem, on_delete=models.PROTECT, related_name='lots')
    lot_number = models.CharField('Lote', max_length=60)
    expires_at = models.DateField('Expiracion', null=True, blank=True)
    supplier = models.CharField('Proveedor', max_length=120, blank=True)
    registry_number = models.CharField('Registro sanitario', max_length=80, blank=True)
    unit_cost = models.DecimalField('Costo unitario', max_digits=12, decimal_places=2, default=Decimal('0.00'))
    current_quantity = models.DecimalField('Stock actual', max_digits=12, decimal_places=2, default=Decimal('0.00'))
    is_blocked = models.BooleanField(default=False)

    class Meta:
        ordering = ['expires_at', 'item__name', 'lot_number']
        constraints = [
            models.UniqueConstraint(fields=['item', 'lot_number'], name='traceability_unique_item_lot'),
        ]

    def clean(self):
        super().clean()
        if self.current_quantity < 0:
            raise ValidationError({'current_quantity': 'El stock actual no puede ser negativo.'})

    @property
    def is_expired(self):
        return bool(self.expires_at and self.expires_at < timezone.localdate())

    def __str__(self):
        return f'{self.item.name} - {self.lot_number}'


class StockMovement(AuditModel):
    lot = models.ForeignKey(SupplyLot, on_delete=models.PROTECT, related_name='movements')
    clinical_encounter = models.ForeignKey(
        ClinicalEncounter,
        on_delete=models.PROTECT,
        related_name='stock_movements',
        null=True,
        blank=True,
    )
    movement_type = models.CharField(max_length=20, choices=MovementType.choices)
    quantity = models.DecimalField('Cantidad', max_digits=12, decimal_places=2)
    occurred_at = models.DateTimeField('Fecha y hora', default=timezone.now)
    reason = models.CharField('Motivo', max_length=255)
    notes = models.TextField('Notas', blank=True)

    class Meta:
        ordering = ['-occurred_at', '-id']

    def clean(self):
        super().clean()
        if self.quantity <= 0:
            raise ValidationError({'quantity': 'La cantidad debe ser mayor que cero.'})

    def __str__(self):
        return f'{self.get_movement_type_display()} {self.quantity} - {self.lot}'

    @property
    def total_cost(self):
        return (self.quantity * self.lot.unit_cost).quantize(Decimal('0.01'))