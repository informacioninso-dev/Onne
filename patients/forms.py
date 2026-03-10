from django import forms

from .models import Patient


class PatientForm(forms.ModelForm):
    class Meta:
        model = Patient
        fields = [
            'mrn',
            'document_type',
            'document_number',
            'first_name',
            'last_name',
            'birth_date',
            'sex',
            'phone',
            'email',
            'address',
            'is_active',
        ]
        widgets = {
            'mrn': forms.TextInput(attrs={'class': 'w-full rounded-lg border px-3 py-2'}),
            'document_type': forms.Select(attrs={'class': 'w-full rounded-lg border px-3 py-2'}),
            'document_number': forms.TextInput(attrs={'class': 'w-full rounded-lg border px-3 py-2'}),
            'first_name': forms.TextInput(attrs={'class': 'w-full rounded-lg border px-3 py-2'}),
            'last_name': forms.TextInput(attrs={'class': 'w-full rounded-lg border px-3 py-2'}),
            'birth_date': forms.DateInput(attrs={'class': 'w-full rounded-lg border px-3 py-2', 'type': 'date'}),
            'sex': forms.Select(attrs={'class': 'w-full rounded-lg border px-3 py-2'}),
            'phone': forms.TextInput(attrs={'class': 'w-full rounded-lg border px-3 py-2'}),
            'email': forms.EmailInput(attrs={'class': 'w-full rounded-lg border px-3 py-2'}),
            'address': forms.TextInput(attrs={'class': 'w-full rounded-lg border px-3 py-2'}),
        }

    def clean_mrn(self):
        return (self.cleaned_data.get('mrn') or '').strip().upper()

    def clean_document_number(self):
        return (self.cleaned_data.get('document_number') or '').strip().upper()

    def clean_first_name(self):
        return (self.cleaned_data.get('first_name') or '').strip()

    def clean_last_name(self):
        return (self.cleaned_data.get('last_name') or '').strip()

    def clean_phone(self):
        return (self.cleaned_data.get('phone') or '').strip()

    def clean_email(self):
        return (self.cleaned_data.get('email') or '').strip().lower()

    def clean_address(self):
        return (self.cleaned_data.get('address') or '').strip()
