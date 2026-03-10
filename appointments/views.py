from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from tenants.models import TenantMembership
from tenants.permissions import tenant_role_required

from .forms import AppointmentForm
from .models import Appointment, AppointmentStatus


@login_required
@tenant_role_required(TenantMembership.ROLE_STAFF)
def index(request):
    q = (request.GET.get('q') or '').strip()
    status = (request.GET.get('status') or 'all').strip().upper()

    appointments = Appointment.objects.select_related('patient')
    if q:
        appointments = appointments.filter(
            Q(patient__last_name__icontains=q)
            | Q(patient__first_name__icontains=q)
            | Q(patient__mrn__icontains=q)
            | Q(reason__icontains=q)
        )

    valid_statuses = {choice for choice, _ in AppointmentStatus.choices}
    if status in valid_statuses:
        appointments = appointments.filter(status=status)
    else:
        status = 'all'

    appointments = appointments.order_by('-scheduled_at')[:100]
    return render(
        request,
        'appointments/index.html',
        {'appointments': appointments, 'q': q, 'status': status, 'status_choices': AppointmentStatus.choices},
    )


@login_required
@tenant_role_required(TenantMembership.ROLE_STAFF)
def create(request):
    initial = {}
    patient_id = request.GET.get('patient')
    if request.method == 'GET' and patient_id:
        initial['patient'] = patient_id

    form = AppointmentForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        appointment = form.save()
        messages.success(request, 'Cita creada correctamente.')
        return redirect('appointments:detail', pk=appointment.pk)
    return render(request, 'appointments/form.html', {'form': form, 'page_title': 'Nueva cita'})


@login_required
@tenant_role_required(TenantMembership.ROLE_STAFF)
def detail(request, pk):
    appointment = get_object_or_404(Appointment.objects.select_related('patient'), pk=pk)
    related_encounters = appointment.clinical_encounters.select_related('patient').order_by('-started_at')[:5]
    return render(
        request,
        'appointments/detail.html',
        {'appointment': appointment, 'related_encounters': related_encounters},
    )


@login_required
@tenant_role_required(TenantMembership.ROLE_STAFF)
def edit(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk)
    form = AppointmentForm(request.POST or None, instance=appointment)
    if request.method == 'POST' and form.is_valid():
        appointment = form.save()
        messages.success(request, 'Cita actualizada correctamente.')
        return redirect('appointments:detail', pk=appointment.pk)
    return render(
        request,
        'appointments/form.html',
        {'form': form, 'appointment': appointment, 'page_title': 'Editar cita'},
    )


@login_required
@require_POST
@tenant_role_required(TenantMembership.ROLE_STAFF)
def update_status(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk)
    next_status = (request.POST.get('status') or '').strip().upper()
    valid_statuses = {choice for choice, _ in AppointmentStatus.choices}
    if next_status not in valid_statuses:
        messages.error(request, 'Estado de cita invalido.')
        return redirect('appointments:detail', pk=appointment.pk)

    appointment.status = next_status
    appointment.save(update_fields=['status', 'updated_at'])
    messages.success(request, 'Estado de cita actualizado correctamente.')
    return redirect('appointments:detail', pk=appointment.pk)
