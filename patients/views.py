from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from tenants.models import TenantMembership
from tenants.permissions import tenant_role_required

from .forms import PatientForm
from .models import Patient


@login_required
@tenant_role_required(TenantMembership.ROLE_STAFF)
def index(request):
    q = (request.GET.get('q') or '').strip()
    status = (request.GET.get('status') or 'active').strip().lower()

    patients = Patient.objects.all()
    if q:
        patients = patients.filter(
            Q(last_name__icontains=q)
            | Q(first_name__icontains=q)
            | Q(mrn__icontains=q)
            | Q(document_number__icontains=q)
        )

    if status == 'active':
        patients = patients.filter(is_active=True)
    elif status == 'inactive':
        patients = patients.filter(is_active=False)

    patients = patients.order_by('last_name', 'first_name')[:100]
    return render(request, 'patients/index.html', {'patients': patients, 'q': q, 'status': status})


@login_required
@tenant_role_required(TenantMembership.ROLE_STAFF)
def create(request):
    form = PatientForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        patient = form.save()
        messages.success(request, 'Paciente creado correctamente.')
        return redirect('patients:detail', pk=patient.pk)
    return render(request, 'patients/form.html', {'form': form, 'page_title': 'Nuevo paciente'})


@login_required
@tenant_role_required(TenantMembership.ROLE_STAFF)
def detail(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    recent_appointments = patient.appointments.order_by('-scheduled_at')[:5]
    recent_encounters = patient.clinical_encounters.select_related('appointment').order_by('-started_at')[:5]
    return render(
        request,
        'patients/detail.html',
        {
            'patient': patient,
            'recent_appointments': recent_appointments,
            'recent_encounters': recent_encounters,
        },
    )


@login_required
@tenant_role_required(TenantMembership.ROLE_STAFF)
def edit(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    form = PatientForm(request.POST or None, instance=patient)
    if request.method == 'POST' and form.is_valid():
        patient = form.save()
        messages.success(request, 'Paciente actualizado correctamente.')
        return redirect('patients:detail', pk=patient.pk)
    return render(
        request,
        'patients/form.html',
        {'form': form, 'patient': patient, 'page_title': 'Editar paciente'},
    )


@login_required
@require_POST
@tenant_role_required(TenantMembership.ROLE_STAFF)
def toggle_active(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    patient.is_active = not patient.is_active
    patient.save(update_fields=['is_active', 'updated_at'])
    state = 'activado' if patient.is_active else 'desactivado'
    messages.success(request, f'Paciente {state} correctamente.')

    next_url = request.POST.get('next')
    if next_url:
        return HttpResponseRedirect(next_url)
    return redirect('patients:detail', pk=patient.pk)
