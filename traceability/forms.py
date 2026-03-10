from django import forms
from django.db.models import Case, IntegerField, Value, When
from django.utils import timezone

from clinical.models import ClinicalEncounter

from .models import MovementType, StockMovement, SupplyItem, SupplyLot
from .services import register_stock_movement


class SupplyItemForm(forms.ModelForm):
    class Meta:
        model = SupplyItem
        fields = ['name', 'sku', 'unit_of_measure', 'track_expiration', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full rounded-lg border px-3 py-2'}),
            'sku': forms.TextInput(attrs={'class': 'w-full rounded-lg border px-3 py-2'}),
            'unit_of_measure': forms.TextInput(attrs={'class': 'w-full rounded-lg border px-3 py-2'}),
        }

    def clean_name(self):
        return (self.cleaned_data.get('name') or '').strip()

    def clean_sku(self):
        return (self.cleaned_data.get('sku') or '').strip().upper()

    def clean_unit_of_measure(self):
        return (self.cleaned_data.get('unit_of_measure') or '').strip().lower()


class SupplyLotForm(forms.ModelForm):
    class Meta:
        model = SupplyLot
        fields = [
            'item',
            'lot_number',
            'expires_at',
            'supplier',
            'registry_number',
            'unit_cost',
            'current_quantity',
            'is_blocked',
        ]
        widgets = {
            'item': forms.Select(attrs={'class': 'w-full rounded-lg border px-3 py-2'}),
            'lot_number': forms.TextInput(attrs={'class': 'w-full rounded-lg border px-3 py-2'}),
            'expires_at': forms.DateInput(attrs={'class': 'w-full rounded-lg border px-3 py-2', 'type': 'date'}),
            'supplier': forms.TextInput(attrs={'class': 'w-full rounded-lg border px-3 py-2'}),
            'registry_number': forms.TextInput(attrs={'class': 'w-full rounded-lg border px-3 py-2'}),
            'unit_cost': forms.NumberInput(attrs={'class': 'w-full rounded-lg border px-3 py-2', 'step': '0.01', 'min': '0'}),
            'current_quantity': forms.NumberInput(attrs={'class': 'w-full rounded-lg border px-3 py-2', 'step': '0.01', 'min': '0'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['item'].queryset = SupplyItem.objects.filter(is_active=True).order_by('name')

    def clean_lot_number(self):
        return (self.cleaned_data.get('lot_number') or '').strip().upper()

    def clean_supplier(self):
        return (self.cleaned_data.get('supplier') or '').strip()

    def clean_registry_number(self):
        return (self.cleaned_data.get('registry_number') or '').strip().upper()


class StockMovementForm(forms.ModelForm):
    supply_item = forms.ModelChoiceField(
        queryset=SupplyItem.objects.filter(is_active=True).order_by('name'),
        required=False,
        widget=forms.Select(attrs={'class': 'w-full rounded-lg border px-3 py-2'}),
        label='Insumo',
    )

    class Meta:
        model = StockMovement
        fields = ['supply_item', 'lot', 'movement_type', 'quantity', 'occurred_at', 'clinical_encounter', 'reason', 'notes']
        widgets = {
            'lot': forms.Select(attrs={'class': 'w-full rounded-lg border px-3 py-2'}),
            'movement_type': forms.Select(attrs={'class': 'w-full rounded-lg border px-3 py-2'}),
            'quantity': forms.NumberInput(attrs={'class': 'w-full rounded-lg border px-3 py-2', 'step': '0.01', 'min': '0.01'}),
            'occurred_at': forms.DateTimeInput(attrs={'class': 'w-full rounded-lg border px-3 py-2', 'type': 'datetime-local'}),
            'clinical_encounter': forms.Select(attrs={'class': 'w-full rounded-lg border px-3 py-2'}),
            'reason': forms.TextInput(attrs={'class': 'w-full rounded-lg border px-3 py-2'}),
            'notes': forms.Textarea(attrs={'class': 'w-full rounded-lg border px-3 py-2', 'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        movement_type = (self.data.get('movement_type') or self.initial.get('movement_type') or '').strip().upper()
        selected_item_id = self.data.get('supply_item') or self.initial.get('supply_item')
        lot_qs = SupplyLot.objects.select_related('item')
        self.fefo_recommendations = []

        if movement_type == MovementType.CONSUMPTION:
            today = timezone.localdate()
            lot_qs = lot_qs.filter(current_quantity__gt=0, is_blocked=False).exclude(expires_at__lt=today)
            if selected_item_id:
                lot_qs = lot_qs.filter(item_id=selected_item_id)
            lot_qs = lot_qs.annotate(
                expiry_bucket=Case(
                    When(expires_at__isnull=True, then=Value(1)),
                    default=Value(0),
                    output_field=IntegerField(),
                )
            ).order_by('expiry_bucket', 'expires_at', 'item__name', 'lot_number')
        else:
            if selected_item_id:
                lot_qs = lot_qs.filter(item_id=selected_item_id)
            lot_qs = lot_qs.order_by('item__name', 'lot_number')

        self.fields['lot'].queryset = lot_qs
        self.fields['clinical_encounter'].queryset = ClinicalEncounter.objects.select_related('patient').order_by('-started_at')
        self.fields['clinical_encounter'].required = False

        if not selected_item_id:
            selected_lot_id = self.data.get('lot') or self.initial.get('lot') or getattr(self.instance, 'lot_id', None)
            if selected_lot_id:
                try:
                    selected_lot = SupplyLot.objects.select_related('item').get(pk=selected_lot_id)
                except (SupplyLot.DoesNotExist, ValueError, TypeError):
                    selected_lot = None
                if selected_lot is not None:
                    self.initial['supply_item'] = selected_lot.item_id
                    self.fields['supply_item'].initial = selected_lot.item_id
                    lot_qs = lot_qs.filter(item=selected_lot.item)

        self.fefo_recommendations = list(lot_qs[:5])

    def clean_supply_item(self):
        return self.cleaned_data.get('supply_item')

    def clean_reason(self):
        return (self.cleaned_data.get('reason') or '').strip()

    def clean_notes(self):
        return (self.cleaned_data.get('notes') or '').strip()

    def clean(self):
        cleaned_data = super().clean()
        movement_type = cleaned_data.get('movement_type')
        lot = cleaned_data.get('lot')
        supply_item = cleaned_data.get('supply_item')
        if movement_type == MovementType.CONSUMPTION and not supply_item:
            self.add_error('supply_item', 'Selecciona el insumo para sugerir lotes por FEFO.')
        if supply_item and lot and lot.item_id != supply_item.pk:
            self.add_error('lot', 'El lote seleccionado no pertenece al insumo indicado.')
        return cleaned_data

    def save(self, commit=True):
        if not commit:
            raise ValueError('StockMovementForm.save requiere commit=True.')
        cleaned = self.cleaned_data
        return register_stock_movement(
            lot=cleaned['lot'],
            movement_type=cleaned['movement_type'],
            quantity=cleaned['quantity'],
            occurred_at=cleaned['occurred_at'],
            clinical_encounter=cleaned.get('clinical_encounter'),
            reason=cleaned['reason'],
            notes=cleaned['notes'],
        )
