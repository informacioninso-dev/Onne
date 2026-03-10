from django import forms

from .models import Appointment
from patients.models import Patient


class AppointmentForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = [
            'patient',
            'scheduled_at',
            'duration_minutes',
            'status',
            'reason',
            'notes',
        ]
        widgets = {
            'patient': forms.Select(attrs={'class': 'w-full rounded-lg border px-3 py-2'}),
            'scheduled_at': forms.DateTimeInput(
                attrs={'class': 'w-full rounded-lg border px-3 py-2', 'type': 'datetime-local'}
            ),
            'duration_minutes': forms.NumberInput(attrs={'class': 'w-full rounded-lg border px-3 py-2', 'min': '5'}),
            'status': forms.Select(attrs={'class': 'w-full rounded-lg border px-3 py-2'}),
            'reason': forms.TextInput(attrs={'class': 'w-full rounded-lg border px-3 py-2'}),
            'notes': forms.Textarea(attrs={'class': 'w-full rounded-lg border px-3 py-2', 'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['patient'].queryset = Patient.objects.filter(is_active=True).order_by('last_name', 'first_name')

    def clean_duration_minutes(self):
        duration = self.cleaned_data.get('duration_minutes') or 0
        if duration < 5:
            raise forms.ValidationError('La duracion minima es de 5 minutos.')
        return duration

    def clean_reason(self):
        return (self.cleaned_data.get('reason') or '').strip()

    def clean_notes(self):
        return (self.cleaned_data.get('notes') or '').strip()
