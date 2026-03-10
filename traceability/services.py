from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import MovementType, StockMovement, SupplyLot


OUTBOUND_TYPES = {MovementType.CONSUMPTION, MovementType.ADJUSTMENT_OUT}
INBOUND_TYPES = {MovementType.RECEIPT, MovementType.ADJUSTMENT_IN}


@transaction.atomic
def register_stock_movement(*, lot, movement_type, quantity, reason, clinical_encounter=None, occurred_at=None, notes=''):
    if quantity is None:
        raise ValidationError('La cantidad es obligatoria.')

    quantity = Decimal(str(quantity))
    if quantity <= 0:
        raise ValidationError('La cantidad debe ser mayor que cero.')

    locked_lot = SupplyLot.objects.select_for_update().get(pk=lot.pk)

    if movement_type in OUTBOUND_TYPES:
        if locked_lot.is_blocked:
            raise ValidationError('No se puede consumir un lote bloqueado.')
        if locked_lot.is_expired:
            raise ValidationError('No se puede consumir un lote expirado.')
        if quantity > locked_lot.current_quantity:
            raise ValidationError('No hay stock suficiente en el lote seleccionado.')
        locked_lot.current_quantity -= quantity
    elif movement_type in INBOUND_TYPES:
        locked_lot.current_quantity += quantity
    else:
        raise ValidationError('Tipo de movimiento invalido.')

    locked_lot.save(update_fields=['current_quantity', 'updated_at'])

    movement = StockMovement.objects.create(
        lot=locked_lot,
        clinical_encounter=clinical_encounter,
        movement_type=movement_type,
        quantity=quantity,
        occurred_at=occurred_at or timezone.now(),
        reason=reason,
        notes=notes,
    )
    return movement
