from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from clinical.models import ClinicalEncounter
from tenants.models import TenantMembership
from tenants.permissions import tenant_role_required

from .forms import StockMovementForm, SupplyItemForm, SupplyLotForm
from .models import MovementType, StockMovement, SupplyItem, SupplyLot


@login_required
@tenant_role_required(TenantMembership.ROLE_CLINICAL)
def index(request):
    items = SupplyItem.objects.order_by('name')[:50]
    lots = SupplyLot.objects.select_related('item').order_by('expires_at', 'item__name', 'lot_number')[:50]
    recent_movements = StockMovement.objects.select_related('lot__item', 'clinical_encounter__patient').order_by('-occurred_at')[:20]
    return render(
        request,
        'traceability/index.html',
        {'items': items, 'lots': lots, 'recent_movements': recent_movements},
    )


@login_required
@tenant_role_required(TenantMembership.ROLE_ADMIN)
def create_item(request):
    form = SupplyItemForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        item = form.save()
        messages.success(request, 'Insumo creado correctamente.')
        return redirect('traceability:index')
    return render(request, 'traceability/item_form.html', {'form': form, 'page_title': 'Nuevo insumo'})


@login_required
@tenant_role_required(TenantMembership.ROLE_ADMIN)
def create_lot(request):
    form = SupplyLotForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        lot = form.save()
        messages.success(request, 'Lote creado correctamente.')
        return redirect('traceability:lot_detail', pk=lot.pk)
    return render(request, 'traceability/lot_form.html', {'form': form, 'page_title': 'Nuevo lote'})


@login_required
@tenant_role_required(TenantMembership.ROLE_CLINICAL)
def lot_detail(request, pk):
    lot = get_object_or_404(SupplyLot.objects.select_related('item'), pk=pk)
    movements = lot.movements.select_related('clinical_encounter__patient').order_by('-occurred_at')[:20]
    return render(request, 'traceability/lot_detail.html', {'lot': lot, 'movements': movements})


@login_required
@tenant_role_required(TenantMembership.ROLE_CLINICAL)
def create_movement(request):
    initial = {}
    encounter_id = request.GET.get('encounter')
    movement_type = request.GET.get('movement_type')
    supply_item = request.GET.get('supply_item')
    if encounter_id:
        encounter = get_object_or_404(ClinicalEncounter.objects.select_related('patient'), pk=encounter_id)
        initial['clinical_encounter'] = encounter.pk
        initial['reason'] = f'Consumo en atencion de {encounter.patient.last_name}, {encounter.patient.first_name}'
    if movement_type:
        initial['movement_type'] = movement_type
    if supply_item:
        initial['supply_item'] = supply_item

    form = StockMovementForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        movement = form.save()
        messages.success(request, 'Movimiento registrado correctamente.')
        return redirect('traceability:lot_detail', pk=movement.lot.pk)

    effective_type = request.POST.get('movement_type') or initial.get('movement_type') or ''
    return render(
        request,
        'traceability/movement_form.html',
        {
            'form': form,
            'page_title': 'Nuevo movimiento',
            'recommended_lots': form.fefo_recommendations,
            'is_consumption': effective_type == MovementType.CONSUMPTION,
        },
    )
