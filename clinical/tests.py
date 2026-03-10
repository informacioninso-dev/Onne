from contextlib import nullcontext
from decimal import Decimal
from pathlib import Path
from tempfile import NamedTemporaryFile
from unittest.mock import MagicMock, patch
from zipfile import ZipFile

from django.core.management.base import CommandError
from django.test import RequestFactory, SimpleTestCase

from appointments.models import Appointment, AppointmentStatus
from clinical.forms import ClinicalEncounterForm, ClinicalNoteTemplateForm, ClinicalOrderForm
from clinical import views
from clinical.management.commands.import_cie10 import Command as ImportCie10Command, load_csv_rows, load_xlsx_rows
from clinical.models import ClinicalEncounter, ClinicalNoteTemplate, ClinicalOrder, ClinicalOrderType, EncounterStatus, OrderPriority, OrderStatus
from patients.models import Patient


class ClinicalNoteTemplateFormTests(SimpleTestCase):
    def test_form_normalizes_name_category_and_diagnosis(self):
        form = ClinicalNoteTemplateForm(
            data={
                'name': ' Control general ',
                'category': ' Consulta externa ',
                'version': '2',
                'diagnosis': ' Hipertension esencial ',
                'subjective': '',
                'objective': '',
                'assessment': '',
                'plan': '',
                'is_active': 'on',
            }
        )

        with (
            patch.object(ClinicalNoteTemplateForm, 'validate_unique', lambda self: None),
            patch.object(ClinicalNoteTemplate, 'full_clean', lambda *args, **kwargs: None),
        ):
            self.assertTrue(form.is_valid(), form.errors)

        self.assertEqual(form.cleaned_data['name'], 'Control general')
        self.assertEqual(form.cleaned_data['category'], 'Consulta externa')
        self.assertEqual(form.cleaned_data['diagnosis'], 'Hipertension esencial')


class ClinicalEncounterFormTests(SimpleTestCase):
    @patch('clinical.forms.ClinicalNoteTemplate.objects.filter')
    @patch('clinical.forms.Appointment.objects.select_related')
    @patch('clinical.forms.Patient.objects.filter')
    def test_form_normalizes_text_fields(self, patient_filter, appointment_select, template_filter):
        patient_qs = MagicMock()
        patient_qs.order_by.return_value = patient_qs
        patient_qs.all.return_value = patient_qs
        patient_filter.return_value = patient_qs

        appointment_qs = MagicMock()
        appointment_qs.order_by.return_value = appointment_qs
        appointment_qs.all.return_value = appointment_qs
        appointment_select.return_value = appointment_qs

        template_qs = MagicMock()
        template_qs.order_by.return_value = template_qs
        template_qs.all.return_value = template_qs
        template_filter.return_value = template_qs

        patient = Patient(
            pk=1,
            mrn='HC-001',
            document_type='NATIONAL_ID',
            document_number='123',
            first_name='Ana',
            last_name='Perez',
        )

        form = ClinicalEncounterForm(
            data={
                'patient': '1',
                'appointment': '',
                'template': '',
                'started_at': '2026-03-10T10:00',
                'chief_complaint': ' Control general ',
                'subjective': ' Refiere dolor leve ',
                'objective': ' Signos vitales estables ',
                'diagnosis': ' Gastritis aguda ',
                'assessment': ' Evaluacion inicial ',
                'plan': ' Plan simple ',
                'status': EncounterStatus.OPEN,
            }
        )
        form.fields['patient'].clean = MagicMock(return_value=patient)
        form.fields['appointment'].clean = MagicMock(return_value=None)
        form.fields['template'].clean = MagicMock(return_value=None)

        with (
            patch.object(ClinicalEncounterForm, 'validate_unique', lambda self: None),
            patch.object(ClinicalEncounter, 'full_clean', lambda *args, **kwargs: None),
        ):
            self.assertTrue(form.is_valid(), form.errors)

        self.assertEqual(form.cleaned_data['chief_complaint'], 'Control general')
        self.assertEqual(form.cleaned_data['subjective'], 'Refiere dolor leve')
        self.assertEqual(form.cleaned_data['objective'], 'Signos vitales estables')
        self.assertEqual(form.cleaned_data['diagnosis'], 'Gastritis aguda')
        self.assertEqual(form.cleaned_data['assessment'], 'Evaluacion inicial')
        self.assertEqual(form.cleaned_data['plan'], 'Plan simple')

    @patch('clinical.forms.ClinicalNoteTemplate.objects.filter')
    @patch('clinical.forms.Appointment.objects.select_related')
    @patch('clinical.forms.Patient.objects.filter')
    def test_form_uses_template_defaults_when_fields_are_blank(self, patient_filter, appointment_select, template_filter):
        patient_qs = MagicMock()
        patient_qs.order_by.return_value = patient_qs
        patient_filter.return_value = patient_qs

        appointment_qs = MagicMock()
        appointment_qs.order_by.return_value = appointment_qs
        appointment_select.return_value = appointment_qs

        template_qs = MagicMock()
        template_qs.order_by.return_value = template_qs
        template_filter.return_value = template_qs

        patient = Patient(pk=1, mrn='HC-001', document_type='NATIONAL_ID', document_number='123', first_name='Ana', last_name='Perez')
        template = ClinicalNoteTemplate(name='Plantilla base', diagnosis='Dx base', subjective='S', objective='O', assessment='A', plan='P')

        form = ClinicalEncounterForm(
            data={
                'patient': '1',
                'appointment': '',
                'template': '5',
                'started_at': '2026-03-10T10:00',
                'chief_complaint': 'Control',
                'subjective': '',
                'objective': '',
                'diagnosis': '',
                'assessment': '',
                'plan': '',
                'status': EncounterStatus.OPEN,
            }
        )
        form.fields['patient'].clean = MagicMock(return_value=patient)
        form.fields['appointment'].clean = MagicMock(return_value=None)
        form.fields['template'].clean = MagicMock(return_value=template)

        with (
            patch.object(ClinicalEncounterForm, 'validate_unique', lambda self: None),
            patch.object(ClinicalEncounter, 'full_clean', lambda *args, **kwargs: None),
        ):
            self.assertTrue(form.is_valid(), form.errors)

        self.assertEqual(form.cleaned_data['diagnosis'], 'Dx base')
        self.assertEqual(form.cleaned_data['subjective'], 'S')
        self.assertEqual(form.cleaned_data['objective'], 'O')
        self.assertEqual(form.cleaned_data['assessment'], 'A')
        self.assertEqual(form.cleaned_data['plan'], 'P')

    @patch('clinical.forms.ClinicalNoteTemplate.objects.filter')
    @patch('clinical.forms.Appointment.objects.select_related')
    @patch('clinical.forms.Patient.objects.filter')
    def test_form_rejects_appointment_from_other_patient(self, patient_filter, appointment_select, template_filter):
        patient_qs = MagicMock()
        patient_qs.order_by.return_value = patient_qs
        patient_qs.all.return_value = patient_qs
        patient_filter.return_value = patient_qs

        appointment_qs = MagicMock()
        appointment_qs.order_by.return_value = appointment_qs
        appointment_qs.all.return_value = appointment_qs
        appointment_select.return_value = appointment_qs

        template_qs = MagicMock()
        template_qs.order_by.return_value = template_qs
        template_qs.all.return_value = template_qs
        template_filter.return_value = template_qs

        patient = Patient(pk=1, mrn='HC-001', document_type='NATIONAL_ID', document_number='123', first_name='Ana', last_name='Perez')
        other_patient = Patient(pk=2, mrn='HC-002', document_type='NATIONAL_ID', document_number='456', first_name='Luis', last_name='Diaz')
        appointment = Appointment(pk=10, patient=other_patient, scheduled_at='2026-03-10T09:00', duration_minutes=30)

        form = ClinicalEncounterForm(
            data={
                'patient': '1',
                'appointment': '10',
                'template': '',
                'started_at': '2026-03-10T10:00',
                'chief_complaint': 'Control',
                'subjective': '',
                'objective': '',
                'diagnosis': '',
                'assessment': '',
                'plan': '',
                'status': EncounterStatus.OPEN,
            }
        )
        form.fields['patient'].clean = MagicMock(return_value=patient)
        form.fields['appointment'].clean = MagicMock(return_value=appointment)
        form.fields['template'].clean = MagicMock(return_value=None)

        with patch.object(ClinicalEncounter, 'full_clean', lambda *args, **kwargs: None):
            self.assertFalse(form.is_valid())
        self.assertIn('appointment', form.errors)


class ClinicalEncounterViewsTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = type('User', (), {'is_authenticated': True})()

    @patch('clinical.views.render')
    @patch('clinical.views.ClinicalEncounter')
    def test_index_filters_by_query_and_status(self, encounter_model, render_mock):
        queryset = MagicMock()
        ordered = MagicMock()
        ordered.__getitem__.return_value = ['e1']
        queryset.filter.return_value = queryset
        queryset.order_by.return_value = ordered
        encounter_model.objects.select_related.return_value = queryset
        render_mock.side_effect = lambda request, template, context: context

        request = self.factory.get('/clinical/', {'q': 'ana', 'status': 'COMPLETED'})
        request.user = self.user

        context = views.index(request)

        self.assertEqual(context['q'], 'ana')
        self.assertEqual(context['status'], 'COMPLETED')
        self.assertEqual(context['encounters'], ['e1'])
        queryset.filter.assert_any_call(status='COMPLETED')

    @patch('clinical.views.JsonResponse')
    @patch('clinical.views.ClinicalEncounter.objects.filter')
    @patch('clinical.views.ClinicalNoteTemplate.objects.filter')
    @patch('clinical.views.DiagnosisCatalogEntry.objects.filter')
    def test_diagnosis_suggestions_merges_catalog_and_local_values(self, catalog_filter, template_filter, encounter_filter, json_response):
        catalog_filter.return_value.values_list.return_value.__getitem__.return_value = [('A00', 'Colera'), ('A01', 'Fiebre tifoidea')]
        template_filter.return_value.exclude.return_value.values_list.return_value.__getitem__.return_value = ['Diag A', 'Diag B']
        encounter_filter.return_value.exclude.return_value.values_list.return_value.__getitem__.return_value = ['Diag B', 'Diag C']

        request = self.factory.get('/clinical/diagnosis-suggestions/', {'q': 'diag'})
        request.user = self.user

        views.diagnosis_suggestions(request)

        json_response.assert_called_once_with(
            {'results': ['A00 - Colera', 'A01 - Fiebre tifoidea', 'Diag A', 'Diag B', 'Diag C']}
        )

    @patch('clinical.views.render')
    @patch('clinical.views.ClinicalNoteTemplate')
    def test_template_index_filters_by_status(self, template_model, render_mock):
        queryset = MagicMock()
        ordered = MagicMock()
        ordered.__getitem__.return_value = ['t1']
        queryset.filter.return_value = queryset
        queryset.order_by.return_value = ordered
        template_model.objects.all.return_value = queryset
        category_qs = MagicMock()
        category_qs.values_list.return_value.distinct.return_value.order_by.return_value = ['Consulta']
        template_model.objects.exclude.return_value = category_qs
        render_mock.side_effect = lambda request, template, context: context

        request = self.factory.get('/clinical/templates/', {'status': 'inactive'})
        request.user = self.user

        context = views.template_index(request)

        self.assertEqual(context['status'], 'inactive')
        self.assertEqual(context['templates'], ['t1'])
        self.assertEqual(context['categories'], ['Consulta'])
        queryset.filter.assert_any_call(is_active=False)

    @patch('clinical.views.render')
    @patch('clinical.views.get_object_or_404')
    def test_create_prefills_from_appointment(self, get_object_mock, render_mock):
        appointment = MagicMock()
        appointment.pk = 12
        appointment.patient_id = 7
        appointment.scheduled_at = '2026-03-10T09:00'
        appointment.reason = 'Control de seguimiento'
        get_object_mock.return_value = appointment
        render_mock.side_effect = lambda request, template, context: context

        request = self.factory.get('/clinical/new/', {'appointment': '12'})
        request.user = self.user

        context = views.create(request)

        self.assertEqual(context['form'].initial['appointment'], 12)
        self.assertEqual(context['form'].initial['patient'], 7)
        self.assertEqual(context['form'].initial['chief_complaint'], 'Control de seguimiento')

    @patch('clinical.views.render')
    @patch('clinical.views.get_object_or_404')
    def test_detail_includes_traceability_cost_summary(self, get_object_mock, render_mock):
        encounter = MagicMock()
        encounter.pk = 8
        encounter.total_supply_cost = Decimal('12.50')

        related_manager = MagicMock()
        select_related_qs = MagicMock()
        ordered_qs = MagicMock()
        ordered_qs.__getitem__.return_value = ['m1', 'm2']
        select_related_qs.order_by.return_value = ordered_qs
        related_manager.select_related.return_value = select_related_qs

        filtered_qs = MagicMock()
        filtered_qs.count.return_value = 2
        related_manager.filter.return_value = filtered_qs

        encounter.stock_movements = related_manager
        get_object_mock.return_value = encounter
        render_mock.side_effect = lambda request, template, context: context

        request = self.factory.get('/clinical/8/')
        request.user = self.user

        context = views.detail(request, pk=8)

        self.assertEqual(context['stock_movements'], ['m1', 'm2'])
        self.assertEqual(context['consumption_count'], 2)
        self.assertEqual(context['total_supply_cost'], Decimal('12.50'))

    @patch('clinical.views.transaction.atomic', return_value=nullcontext())
    @patch('clinical.views.messages.success')
    @patch('clinical.views.get_object_or_404')
    def test_update_status_changes_status(self, get_object_mock, success_mock, _atomic_mock):
        encounter = MagicMock()
        encounter.pk = 1
        encounter.status = EncounterStatus.OPEN
        encounter.appointment = None
        get_object_mock.return_value = encounter

        request = self.factory.post('/clinical/1/status/', {'status': EncounterStatus.COMPLETED})
        request.user = self.user

        response = views.update_status(request, pk=1)

        self.assertEqual(encounter.status, EncounterStatus.COMPLETED)
        encounter.save.assert_called_once_with(update_fields=['status', 'updated_at', 'updated_by'])
        success_mock.assert_called_once()
        self.assertEqual(response.status_code, 302)

    def test_sync_appointment_status_updates_linked_appointment(self):
        appointment = MagicMock()
        appointment.status = AppointmentStatus.SCHEDULED
        encounter = MagicMock()
        encounter.status = EncounterStatus.COMPLETED
        encounter.appointment = appointment

        views._sync_appointment_status(encounter)

        self.assertEqual(appointment.status, AppointmentStatus.COMPLETED)
        appointment.save.assert_called_once_with(update_fields=['status', 'updated_at'])


class ImportCie10HelpersTests(SimpleTestCase):
    def test_load_csv_rows_supports_semicolon_delimiter(self):
        with NamedTemporaryFile('w', suffix='.csv', delete=False, encoding='utf-8-sig', newline='') as handle:
            handle.write('codigo;descripcion\nA00;Colera\n')
            temp_path = Path(handle.name)

        self.addCleanup(lambda: temp_path.unlink(missing_ok=True))
        self.assertEqual(load_csv_rows(temp_path), [['codigo', 'descripcion'], ['A00', 'Colera']])

    def test_load_xlsx_rows_reads_inline_strings(self):
        with NamedTemporaryFile('wb', suffix='.xlsx', delete=False) as handle:
            temp_path = Path(handle.name)

        self.addCleanup(lambda: temp_path.unlink(missing_ok=True))
        with ZipFile(temp_path, 'w') as archive:
            archive.writestr(
                'xl/workbook.xml',
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                '<sheets><sheet name="Catalogo" sheetId="1" r:id="rId1"/></sheets></workbook>',
            )
            archive.writestr(
                'xl/_rels/workbook.xml.rels',
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1" '
                'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
                'Target="worksheets/sheet1.xml"/></Relationships>',
            )
            archive.writestr(
                'xl/worksheets/sheet1.xml',
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                '<sheetData>'
                '<row r="1"><c r="A1" t="inlineStr"><is><t>codigo</t></is></c>'
                '<c r="B1" t="inlineStr"><is><t>descripcion</t></is></c></row>'
                '<row r="2"><c r="A2" t="inlineStr"><is><t>A00</t></is></c>'
                '<c r="B2" t="inlineStr"><is><t>Colera</t></is></c></row>'
                '</sheetData></worksheet>',
            )

        self.assertEqual(load_xlsx_rows(temp_path), [['codigo', 'descripcion'], ['A00', 'Colera']])

    def test_command_requires_schema_when_running_in_public(self):
        command = ImportCie10Command()
        with patch('clinical.management.commands.import_cie10.connection.schema_name', 'public'):
            with self.assertRaises(CommandError):
                command._resolve_target_schemas({'schemas': [], 'all_tenants': False})





class ClinicalOrderFormTests(SimpleTestCase):
    def test_form_normalizes_title_and_notes(self):
        form = ClinicalOrderForm(
            data={
                'order_type': ClinicalOrderType.LAB,
                'title': ' Biometria hematica ',
                'priority': OrderPriority.URGENT,
                'status': OrderStatus.REQUESTED,
                'requested_at': '2026-03-10T12:00',
                'instructions': ' Tomar muestra en ayunas ',
                'result_notes': ' Pendiente ',
            }
        )

        with (
            patch.object(ClinicalOrderForm, 'validate_unique', lambda self: None),
            patch.object(ClinicalOrder, 'full_clean', lambda *args, **kwargs: None),
        ):
            self.assertTrue(form.is_valid(), form.errors)

        self.assertEqual(form.cleaned_data['title'], 'Biometria hematica')
        self.assertEqual(form.cleaned_data['instructions'], 'Tomar muestra en ayunas')
        self.assertEqual(form.cleaned_data['result_notes'], 'Pendiente')


class ClinicalOrderViewsTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = type('User', (), {'is_authenticated': True})()

    @patch('clinical.views.render')
    @patch('clinical.views.get_object_or_404')
    def test_detail_includes_orders(self, get_object_mock, render_mock):
        encounter = MagicMock()
        encounter.pk = 8
        encounter.total_supply_cost = Decimal('12.50')

        stock_manager = MagicMock()
        stock_select = MagicMock()
        stock_ordered = MagicMock()
        stock_ordered.__getitem__.return_value = ['m1']
        stock_select.order_by.return_value = stock_ordered
        stock_manager.select_related.return_value = stock_select
        stock_filtered = MagicMock()
        stock_filtered.count.return_value = 1
        stock_manager.filter.return_value = stock_filtered
        encounter.stock_movements = stock_manager

        orders_manager = MagicMock()
        ordered_orders = MagicMock()
        ordered_orders.__getitem__.return_value = ['o1', 'o2']
        orders_manager.order_by.return_value = ordered_orders
        encounter.orders = orders_manager

        get_object_mock.return_value = encounter
        render_mock.side_effect = lambda request, template, context: context

        request = self.factory.get('/clinical/8/')
        request.user = self.user

        context = views.detail(request, pk=8)

        self.assertEqual(context['orders'], ['o1', 'o2'])
        self.assertEqual(context['order_status_choices'], OrderStatus.choices)

    @patch('clinical.views.messages.success')
    @patch('clinical.views.get_object_or_404')
    def test_update_order_status_changes_status(self, get_object_mock, success_mock):
        order = MagicMock()
        order.pk = 3
        order.encounter_id = 8
        order.status = OrderStatus.REQUESTED
        get_object_mock.return_value = order

        request = self.factory.post('/clinical/orders/3/status/', {'status': OrderStatus.COMPLETED})
        request.user = self.user

        response = views.update_order_status(request, pk=3)

        self.assertEqual(order.status, OrderStatus.COMPLETED)
        order.save.assert_called_once_with(update_fields=['status', 'completed_at', 'updated_at', 'updated_by'])
        success_mock.assert_called_once()
        self.assertEqual(response.status_code, 302)

