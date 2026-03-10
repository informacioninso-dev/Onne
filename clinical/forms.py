from django import forms

from appointments.models import Appointment
from patients.models import Patient

from .models import ClinicalEncounter, ClinicalNoteTemplate, ClinicalOrder


class ClinicalNoteTemplateForm(forms.ModelForm):
    class Meta:
        model = ClinicalNoteTemplate
        fields = ['name', 'category', 'version', 'diagnosis', 'subjective', 'objective', 'assessment', 'plan', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full rounded-lg border px-3 py-2'}),
            'category': forms.TextInput(attrs={'class': 'w-full rounded-lg border px-3 py-2'}),
            'version': forms.NumberInput(attrs={'class': 'w-full rounded-lg border px-3 py-2', 'min': '1', 'step': '1'}),
            'diagnosis': forms.TextInput(attrs={'class': 'w-full rounded-lg border px-3 py-2'}),
            'subjective': forms.Textarea(attrs={'class': 'w-full rounded-lg border px-3 py-2', 'rows': 3}),
            'objective': forms.Textarea(attrs={'class': 'w-full rounded-lg border px-3 py-2', 'rows': 3}),
            'assessment': forms.Textarea(attrs={'class': 'w-full rounded-lg border px-3 py-2', 'rows': 3}),
            'plan': forms.Textarea(attrs={'class': 'w-full rounded-lg border px-3 py-2', 'rows': 3}),
        }

    def clean_name(self):
        return (self.cleaned_data.get('name') or '').strip()

    def clean_category(self):
        return (self.cleaned_data.get('category') or '').strip()

    def clean_diagnosis(self):
        return (self.cleaned_data.get('diagnosis') or '').strip()


class ClinicalEncounterForm(forms.ModelForm):
    class Meta:
        model = ClinicalEncounter
        fields = [
            'patient',
            'appointment',
            'template',
            'started_at',
            'chief_complaint',
            'subjective',
            'objective',
            'diagnosis',
            'assessment',
            'plan',
            'status',
        ]
        widgets = {
            'patient': forms.Select(attrs={'class': 'w-full rounded-lg border px-3 py-2'}),
            'appointment': forms.Select(attrs={'class': 'w-full rounded-lg border px-3 py-2'}),
            'template': forms.Select(attrs={'class': 'w-full rounded-lg border px-3 py-2'}),
            'started_at': forms.DateTimeInput(attrs={'class': 'w-full rounded-lg border px-3 py-2', 'type': 'datetime-local'}),
            'chief_complaint': forms.TextInput(attrs={'class': 'w-full rounded-lg border px-3 py-2'}),
            'subjective': forms.Textarea(attrs={'class': 'w-full rounded-lg border px-3 py-2', 'rows': 4}),
            'objective': forms.Textarea(attrs={'class': 'w-full rounded-lg border px-3 py-2', 'rows': 4}),
            'diagnosis': forms.TextInput(attrs={'class': 'w-full rounded-lg border px-3 py-2', 'list': 'diagnosis-suggestions', 'autocomplete': 'off'}),
            'assessment': forms.Textarea(attrs={'class': 'w-full rounded-lg border px-3 py-2', 'rows': 4}),
            'plan': forms.Textarea(attrs={'class': 'w-full rounded-lg border px-3 py-2', 'rows': 4}),
            'status': forms.Select(attrs={'class': 'w-full rounded-lg border px-3 py-2'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['patient'].queryset = Patient.objects.filter(is_active=True).order_by('last_name', 'first_name')
        self.fields['template'].queryset = ClinicalNoteTemplate.objects.filter(is_active=True).order_by('name', '-version')
        self.fields['template'].required = False

        appointment_qs = Appointment.objects.select_related('patient')
        selected_patient_id = self.data.get('patient') or self.initial.get('patient') or getattr(self.instance, 'patient_id', None)
        if selected_patient_id:
            appointment_qs = appointment_qs.filter(patient_id=selected_patient_id)
        self.fields['appointment'].queryset = appointment_qs.order_by('-scheduled_at')
        self.fields['appointment'].required = False

    def clean_chief_complaint(self):
        return (self.cleaned_data.get('chief_complaint') or '').strip()

    def clean_subjective(self):
        return (self.cleaned_data.get('subjective') or '').strip()

    def clean_objective(self):
        return (self.cleaned_data.get('objective') or '').strip()

    def clean_diagnosis(self):
        return (self.cleaned_data.get('diagnosis') or '').strip()

    def clean_assessment(self):
        return (self.cleaned_data.get('assessment') or '').strip()

    def clean_plan(self):
        return (self.cleaned_data.get('plan') or '').strip()

    def clean(self):
        cleaned_data = super().clean()
        patient = cleaned_data.get('patient')
        appointment = cleaned_data.get('appointment')
        template = cleaned_data.get('template')

        if patient and appointment and appointment.patient_id != patient.pk:
            self.add_error('appointment', 'La cita seleccionada no pertenece al paciente indicado.')

        if template:
            for field in ['diagnosis', 'subjective', 'objective', 'assessment', 'plan']:
                if not cleaned_data.get(field):
                    cleaned_data[field] = getattr(template, field)
        return cleaned_data


class ClinicalOrderForm(forms.ModelForm):
    class Meta:
        model = ClinicalOrder
        fields = ['order_type', 'title', 'priority', 'status', 'requested_at', 'instructions', 'result_notes']
        widgets = {
            'order_type': forms.Select(attrs={'class': 'w-full rounded-lg border px-3 py-2'}),
            'title': forms.TextInput(attrs={'class': 'w-full rounded-lg border px-3 py-2'}),
            'priority': forms.Select(attrs={'class': 'w-full rounded-lg border px-3 py-2'}),
            'status': forms.Select(attrs={'class': 'w-full rounded-lg border px-3 py-2'}),
            'requested_at': forms.DateTimeInput(attrs={'class': 'w-full rounded-lg border px-3 py-2', 'type': 'datetime-local'}),
            'instructions': forms.Textarea(attrs={'class': 'w-full rounded-lg border px-3 py-2', 'rows': 4}),
            'result_notes': forms.Textarea(attrs={'class': 'w-full rounded-lg border px-3 py-2', 'rows': 4}),
        }

    def clean_title(self):
        return (self.cleaned_data.get('title') or '').strip()

    def clean_instructions(self):
        return (self.cleaned_data.get('instructions') or '').strip()

    def clean_result_notes(self):
        return (self.cleaned_data.get('result_notes') or '').strip()
