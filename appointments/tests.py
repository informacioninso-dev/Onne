from unittest.mock import MagicMock, patch

from django.test import RequestFactory, SimpleTestCase

from appointments.forms import AppointmentForm
from appointments import views
from appointments.models import Appointment, AppointmentStatus
from patients.models import Patient


class AppointmentFormTests(SimpleTestCase):
    @patch('appointments.forms.Patient.objects.filter')
    def test_form_rejects_short_duration(self, patient_filter):
        queryset = MagicMock()
        queryset.order_by.return_value = queryset
        queryset.all.return_value = queryset
        patient_filter.return_value = queryset

        form = AppointmentForm(
            data={
                'patient': '1',
                'scheduled_at': '2026-03-10T09:00',
                'duration_minutes': 4,
                'status': AppointmentStatus.SCHEDULED,
                'reason': ' Consulta ',
                'notes': ' Nota inicial ',
            }
        )
        form.fields['patient'].clean = MagicMock(
            return_value=Patient(
                pk=1,
                mrn='HC-001',
                document_type='NATIONAL_ID',
                document_number='123',
                first_name='Ana',
                last_name='Perez',
            )
        )
        with patch.object(Appointment, 'full_clean', lambda *args, **kwargs: None):
            self.assertFalse(form.is_valid())
        self.assertIn('duration_minutes', form.errors)

    @patch('appointments.forms.Patient.objects.filter')
    def test_form_normalizes_reason_and_notes(self, patient_filter):
        queryset = MagicMock()
        queryset.order_by.return_value = queryset
        queryset.all.return_value = queryset
        patient_filter.return_value = queryset

        form = AppointmentForm(
            data={
                'patient': '1',
                'scheduled_at': '2026-03-10T09:00',
                'duration_minutes': 30,
                'status': AppointmentStatus.SCHEDULED,
                'reason': ' Consulta de control ',
                'notes': ' Seguimiento simple ',
            }
        )
        form.fields['patient'].clean = MagicMock(
            return_value=Patient(
                pk=1,
                mrn='HC-001',
                document_type='NATIONAL_ID',
                document_number='123',
                first_name='Ana',
                last_name='Perez',
            )
        )

        with (
            patch.object(AppointmentForm, 'validate_unique', lambda self: None),
            patch.object(Appointment, 'full_clean', lambda *args, **kwargs: None),
        ):
            self.assertTrue(form.is_valid(), form.errors)

        self.assertEqual(form.cleaned_data['reason'], 'Consulta de control')
        self.assertEqual(form.cleaned_data['notes'], 'Seguimiento simple')


class AppointmentViewsTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = type('User', (), {'is_authenticated': True})()

    @patch('appointments.views.render')
    @patch('appointments.views.Appointment')
    def test_index_filters_by_query_and_status(self, appointment_model, render_mock):
        queryset = MagicMock()
        ordered = MagicMock()
        ordered.__getitem__.return_value = ['a1']
        queryset.filter.return_value = queryset
        queryset.order_by.return_value = ordered
        appointment_model.objects.select_related.return_value = queryset
        render_mock.side_effect = lambda request, template, context: context

        request = self.factory.get('/appointments/', {'q': 'ana', 'status': 'CONFIRMED'})
        request.user = self.user

        context = views.index(request)

        self.assertEqual(context['q'], 'ana')
        self.assertEqual(context['status'], 'CONFIRMED')
        self.assertEqual(context['appointments'], ['a1'])
        queryset.filter.assert_any_call(status='CONFIRMED')
        queryset.order_by.assert_called_once_with('-scheduled_at')

    @patch('appointments.views.render')
    def test_create_prefills_patient_from_querystring(self, render_mock):
        render_mock.side_effect = lambda request, template, context: context
        request = self.factory.get('/appointments/new/', {'patient': '5'})
        request.user = self.user

        context = views.create(request)

        self.assertEqual(context['form'].initial['patient'], '5')

    @patch('appointments.views.messages.success')
    @patch('appointments.views.get_object_or_404')
    def test_update_status_changes_status(self, get_object_mock, success_mock):
        appointment = MagicMock()
        appointment.pk = 1
        appointment.status = AppointmentStatus.SCHEDULED
        get_object_mock.return_value = appointment

        request = self.factory.post('/appointments/1/status/', {'status': AppointmentStatus.COMPLETED})
        request.user = self.user

        response = views.update_status(request, pk=1)

        self.assertEqual(appointment.status, AppointmentStatus.COMPLETED)
        appointment.save.assert_called_once_with(update_fields=['status', 'updated_at'])
        success_mock.assert_called_once()
        self.assertEqual(response.status_code, 302)
