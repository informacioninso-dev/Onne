from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from appointments.models import Appointment, AppointmentStatus
from tenants.models import TenantMembership
from tenants.permissions import tenant_role_required
from .forms import ClinicalEncounterForm, ClinicalNoteTemplateForm, ClinicalOrderForm
from .models import (
    ClinicalEncounter,
    ClinicalNoteTemplate,
    ClinicalOrder,
    DiagnosisCatalogEntry,
    DiagnosisCodingSystem,
    EncounterStatus,
    OrderStatus,
)


def _sync_appointment_status(encounter):
    appointment = encounter.appointment
    if not appointment:
        return

    status_map = {
        EncounterStatus.OPEN: AppointmentStatus.IN_PROGRESS,
        EncounterStatus.IN_PROGRESS: AppointmentStatus.IN_PROGRESS,
        EncounterStatus.COMPLETED: AppointmentStatus.COMPLETED,
        EncounterStatus.CANCELED: AppointmentStatus.CANCELED,
    }
    next_status = status_map.get(encounter.status)
    if next_status and appointment.status != next_status:
        appointment.status = next_status
        appointment.save(update_fields=['status', 'updated_at'])


def _save_audit_user(instance, user, is_new):
    if is_new and not getattr(instance, 'created_by_id', None):
        instance.created_by = user
    instance.updated_by = user


@login_required
@tenant_role_required(TenantMembership.ROLE_CLINICAL)
def index(request):
    q = (request.GET.get('q') or '').strip()
    status = (request.GET.get('status') or 'all').strip().upper()

    encounters = ClinicalEncounter.objects.select_related('patient', 'appointment', 'template')
    if q:
        encounters = encounters.filter(
            Q(patient__last_name__icontains=q)
            | Q(patient__first_name__icontains=q)
            | Q(patient__mrn__icontains=q)
            | Q(chief_complaint__icontains=q)
            | Q(diagnosis__icontains=q)
            | Q(template__name__icontains=q)
        )

    valid_statuses = {choice for choice, _ in EncounterStatus.choices}
    if status in valid_statuses:
        encounters = encounters.filter(status=status)
    else:
        status = 'all'

    encounters = encounters.order_by('-started_at')[:100]
    return render(
        request,
        'clinical/index.html',
        {'encounters': encounters, 'q': q, 'status': status, 'status_choices': EncounterStatus.choices},
    )


@login_required
@tenant_role_required(TenantMembership.ROLE_CLINICAL)
def create(request):
    initial = {}
    appointment_id = request.GET.get('appointment')
    patient_id = request.GET.get('patient')

    if request.method == 'GET' and appointment_id:
        appointment = get_object_or_404(Appointment.objects.select_related('patient'), pk=appointment_id)
        initial.update(
            {
                'appointment': appointment.pk,
                'patient': appointment.patient_id,
                'started_at': appointment.scheduled_at,
                'chief_complaint': appointment.reason,
            }
        )
    elif request.method == 'GET' and patient_id:
        initial['patient'] = patient_id

    form = ClinicalEncounterForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            encounter = form.save(commit=False)
            _save_audit_user(encounter, request.user, is_new=True)
            encounter.save()
            form.save_m2m()
            _sync_appointment_status(encounter)
        messages.success(request, 'Atencion clinica creada correctamente.')
        return redirect('clinical:detail', pk=encounter.pk)
    return render(request, 'clinical/form.html', {'form': form, 'page_title': 'Nueva atencion clinica'})


@login_required
@tenant_role_required(TenantMembership.ROLE_CLINICAL)
def detail(request, pk):
    encounter = get_object_or_404(ClinicalEncounter.objects.select_related('patient', 'appointment', 'template'), pk=pk)
    stock_movements = encounter.stock_movements.select_related('lot__item').order_by('-occurred_at')[:10]
    orders = encounter.orders.order_by('-requested_at', '-created_at')[:20]
    consumption_count = encounter.stock_movements.filter(movement_type='CONSUMPTION').count()
    return render(
        request,
        'clinical/detail.html',
        {
            'encounter': encounter,
            'status_choices': EncounterStatus.choices,
            'order_status_choices': OrderStatus.choices,
            'stock_movements': stock_movements,
            'orders': orders,
            'consumption_count': consumption_count,
            'total_supply_cost': encounter.total_supply_cost,
        },
    )


@login_required
@tenant_role_required(TenantMembership.ROLE_CLINICAL)
def edit(request, pk):
    encounter = get_object_or_404(ClinicalEncounter, pk=pk)
    form = ClinicalEncounterForm(request.POST or None, instance=encounter)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            encounter = form.save(commit=False)
            _save_audit_user(encounter, request.user, is_new=False)
            encounter.save()
            form.save_m2m()
            _sync_appointment_status(encounter)
        messages.success(request, 'Atencion clinica actualizada correctamente.')
        return redirect('clinical:detail', pk=encounter.pk)
    return render(
        request,
        'clinical/form.html',
        {'form': form, 'encounter': encounter, 'page_title': 'Editar atencion clinica'},
    )


@login_required
@tenant_role_required(TenantMembership.ROLE_ADMIN)
def template_index(request):
    q = (request.GET.get('q') or '').strip()
    status = (request.GET.get('status') or 'active').strip().lower()
    category = (request.GET.get('category') or '').strip()

    templates = ClinicalNoteTemplate.objects.all()
    if q:
        templates = templates.filter(Q(name__icontains=q) | Q(diagnosis__icontains=q) | Q(category__icontains=q))
    if category:
        templates = templates.filter(category__iexact=category)
    if status == 'active':
        templates = templates.filter(is_active=True)
    elif status == 'inactive':
        templates = templates.filter(is_active=False)

    templates = templates.order_by('name', '-version')[:100]
    categories = list(ClinicalNoteTemplate.objects.exclude(category='').values_list('category', flat=True).distinct().order_by('category'))
    return render(
        request,
        'clinical/template_index.html',
        {'templates': templates, 'q': q, 'status': status, 'category': category, 'categories': categories},
    )


@login_required
@tenant_role_required(TenantMembership.ROLE_ADMIN)
def create_template(request):
    form = ClinicalNoteTemplateForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        template = form.save(commit=False)
        _save_audit_user(template, request.user, is_new=True)
        template.save()
        form.save_m2m()
        messages.success(request, f"Plantilla clinica '{template.name}' creada correctamente.")
        return redirect('clinical:template_index')
    return render(request, 'clinical/template_form.html', {'form': form, 'page_title': 'Nueva plantilla clinica'})


@login_required
@tenant_role_required(TenantMembership.ROLE_ADMIN)
def edit_template(request, pk):
    template = get_object_or_404(ClinicalNoteTemplate, pk=pk)
    form = ClinicalNoteTemplateForm(request.POST or None, instance=template)
    if request.method == 'POST' and form.is_valid():
        template = form.save(commit=False)
        _save_audit_user(template, request.user, is_new=False)
        template.save()
        form.save_m2m()
        messages.success(request, f"Plantilla clinica '{template.name}' actualizada correctamente.")
        return redirect('clinical:template_index')
    return render(
        request,
        'clinical/template_form.html',
        {'form': form, 'template': template, 'page_title': 'Editar plantilla clinica'},
    )


@login_required
@tenant_role_required(TenantMembership.ROLE_CLINICAL)
def create_order(request, encounter_pk):
    encounter = get_object_or_404(ClinicalEncounter.objects.select_related('patient'), pk=encounter_pk)
    form = ClinicalOrderForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        order = form.save(commit=False)
        order.encounter = encounter
        _save_audit_user(order, request.user, is_new=True)
        order.save()
        form.save_m2m()
        messages.success(request, 'Orden clinica creada correctamente.')
        return redirect('clinical:detail', pk=encounter.pk)
    return render(
        request,
        'clinical/order_form.html',
        {'form': form, 'encounter': encounter, 'page_title': 'Nueva orden clinica'},
    )


@login_required
@tenant_role_required(TenantMembership.ROLE_CLINICAL)
def edit_order(request, pk):
    order = get_object_or_404(ClinicalOrder.objects.select_related('encounter__patient'), pk=pk)
    form = ClinicalOrderForm(request.POST or None, instance=order)
    if request.method == 'POST' and form.is_valid():
        order = form.save(commit=False)
        _save_audit_user(order, request.user, is_new=False)
        order.save()
        form.save_m2m()
        messages.success(request, 'Orden clinica actualizada correctamente.')
        return redirect('clinical:detail', pk=order.encounter_id)
    return render(
        request,
        'clinical/order_form.html',
        {'form': form, 'encounter': order.encounter, 'order': order, 'page_title': 'Editar orden clinica'},
    )


@login_required
@require_POST
@tenant_role_required(TenantMembership.ROLE_CLINICAL)
def update_order_status(request, pk):
    order = get_object_or_404(ClinicalOrder, pk=pk)
    next_status = (request.POST.get('status') or '').strip().upper()
    valid_statuses = {choice for choice, _ in OrderStatus.choices}
    if next_status not in valid_statuses:
        messages.error(request, 'Estado de orden invalido.')
        return redirect('clinical:detail', pk=order.encounter_id)

    order.status = next_status
    _save_audit_user(order, request.user, is_new=False)
    order.save(update_fields=['status', 'completed_at', 'updated_at', 'updated_by'])
    messages.success(request, 'Estado de orden actualizado correctamente.')
    return redirect('clinical:detail', pk=order.encounter_id)


@login_required
@require_GET
@tenant_role_required(TenantMembership.ROLE_CLINICAL)
def diagnosis_suggestions(request):
    q = (request.GET.get('q') or '').strip()
    suggestions = []
    if q:
        catalog_matches = list(
            DiagnosisCatalogEntry.objects.filter(
                Q(code__icontains=q) | Q(title__icontains=q),
                system=DiagnosisCodingSystem.CIE10,
                is_active=True,
            ).values_list('code', 'title')[:10]
        )
        template_matches = list(
            ClinicalNoteTemplate.objects.filter(diagnosis__icontains=q)
            .exclude(diagnosis='')
            .values_list('diagnosis', flat=True)[:10]
        )
        encounter_matches = list(
            ClinicalEncounter.objects.filter(diagnosis__icontains=q)
            .exclude(diagnosis='')
            .values_list('diagnosis', flat=True)[:10]
        )
        seen = set()
        for code, title in catalog_matches:
            label = f'{code} - {title}'
            if label not in seen:
                suggestions.append(label)
                seen.add(label)
            if len(suggestions) >= 10:
                break
        for diagnosis in template_matches + encounter_matches:
            if diagnosis not in seen:
                suggestions.append(diagnosis)
                seen.add(diagnosis)
            if len(suggestions) >= 10:
                break
    return JsonResponse({'results': suggestions})


@login_required
@require_POST
@tenant_role_required(TenantMembership.ROLE_CLINICAL)
def update_status(request, pk):
    encounter = get_object_or_404(ClinicalEncounter, pk=pk)
    next_status = (request.POST.get('status') or '').strip().upper()
    valid_statuses = {choice for choice, _ in EncounterStatus.choices}
    if next_status not in valid_statuses:
        messages.error(request, 'Estado de atencion invalido.')
        return redirect('clinical:detail', pk=encounter.pk)

    with transaction.atomic():
        encounter.status = next_status
        _save_audit_user(encounter, request.user, is_new=False)
        encounter.save(update_fields=['status', 'updated_at', 'updated_by'])
        _sync_appointment_status(encounter)
    messages.success(request, 'Estado de atencion actualizado correctamente.')
    return redirect('clinical:detail', pk=encounter.pk)
