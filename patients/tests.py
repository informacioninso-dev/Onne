from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import RequestFactory, SimpleTestCase

from patients.forms import PatientForm
from patients import views


class PatientFormTests(SimpleTestCase):
    def test_form_normalizes_text_fields(self):
        form = PatientForm(
            data={
                'mrn': ' hc-001 ',
                'document_type': 'NATIONAL_ID',
                'document_number': ' 123abc ',
                'first_name': ' Ana ',
                'last_name': ' Perez ',
                'birth_date': '1990-01-02',
                'sex': 'F',
                'phone': ' 0999999999 ',
                'email': ' TEST@MAIL.COM ',
                'address': ' Av. Siempre Viva ',
                'is_active': 'on',
            }
        )

        with (
            patch.object(PatientForm, 'validate_unique', lambda self: None),
            patch('patients.models.Patient.validate_constraints', lambda *args, **kwargs: None),
        ):
            self.assertTrue(form.is_valid(), form.errors)

        self.assertEqual(form.cleaned_data['mrn'], 'HC-001')
        self.assertEqual(form.cleaned_data['document_number'], '123ABC')
        self.assertEqual(form.cleaned_data['first_name'], 'Ana')
        self.assertEqual(form.cleaned_data['last_name'], 'Perez')
        self.assertEqual(form.cleaned_data['phone'], '0999999999')
        self.assertEqual(form.cleaned_data['email'], 'test@mail.com')
        self.assertEqual(form.cleaned_data['address'], 'Av. Siempre Viva')


class PatientViewsTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = SimpleNamespace(is_authenticated=True)

    @patch('patients.views.render')
    @patch('patients.views.Patient')
    def test_index_filters_by_query_and_active_status(self, patient_model, render_mock):
        queryset = MagicMock()
        ordered = MagicMock()
        ordered.__getitem__.return_value = ['p1']
        queryset.filter.return_value = queryset
        queryset.order_by.return_value = ordered
        patient_model.objects.all.return_value = queryset
        render_mock.side_effect = lambda request, template, context: context

        request = self.factory.get('/patients/', {'q': '123', 'status': 'active'})
        request.user = self.user

        context = views.index(request)

        self.assertEqual(context['q'], '123')
        self.assertEqual(context['status'], 'active')
        self.assertEqual(context['patients'], ['p1'])
        queryset.filter.assert_any_call(is_active=True)
        queryset.order_by.assert_called_once_with('last_name', 'first_name')

    @patch('patients.views.messages.success')
    @patch('patients.views.get_object_or_404')
    def test_toggle_active_switches_state_and_redirects_to_next(self, get_object_mock, success_mock):
        patient = MagicMock()
        patient.is_active = True
        get_object_mock.return_value = patient

        request = self.factory.post('/patients/1/toggle-active/', {'next': '/patients/'})
        request.user = self.user

        response = views.toggle_active(request, pk=1)

        self.assertFalse(patient.is_active)
        patient.save.assert_called_once_with(update_fields=['is_active', 'updated_at'])
        success_mock.assert_called_once()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/patients/')
