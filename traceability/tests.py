from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.core.exceptions import ValidationError
from django.test import RequestFactory, SimpleTestCase

from traceability import services, views
from traceability.forms import StockMovementForm
from traceability.models import MovementType, StockMovement, SupplyItem, SupplyLot


class RegisterStockMovementTests(SimpleTestCase):
    @patch('traceability.services.StockMovement.objects.create')
    @patch('traceability.services.SupplyLot.objects.select_for_update')
    def test_receipt_increases_stock(self, select_for_update, create_movement):
        lot = MagicMock()
        lot.pk = 1
        lot.current_quantity = Decimal('5.00')
        lot.is_blocked = False
        lot.is_expired = False
        select_for_update.return_value.get.return_value = lot
        create_movement.return_value = MagicMock(lot=lot)

        movement = services.register_stock_movement.__wrapped__(
            lot=lot,
            movement_type=MovementType.RECEIPT,
            quantity='2.00',
            reason='Ingreso inicial',
        )

        self.assertEqual(lot.current_quantity, Decimal('7.00'))
        lot.save.assert_called_once_with(update_fields=['current_quantity', 'updated_at'])
        create_movement.assert_called_once()
        self.assertIsNotNone(movement)

    @patch('traceability.services.SupplyLot.objects.select_for_update')
    def test_consumption_rejects_insufficient_stock(self, select_for_update):
        lot = MagicMock()
        lot.pk = 1
        lot.current_quantity = Decimal('1.00')
        lot.is_blocked = False
        lot.is_expired = False
        select_for_update.return_value.get.return_value = lot

        with self.assertRaises(ValidationError):
            services.register_stock_movement.__wrapped__(
                lot=lot,
                movement_type=MovementType.CONSUMPTION,
                quantity='2.00',
                reason='Consumo clinico',
            )

    def test_stock_movement_total_cost_uses_lot_unit_cost(self):
        item = SupplyItem(name='Guante', sku='GUANTE-001', unit_of_measure='unidad')
        lot = SupplyLot(item=item, lot_number='L-001', unit_cost=Decimal('1.25'), current_quantity=Decimal('10.00'))
        movement = StockMovement(lot=lot, movement_type=MovementType.CONSUMPTION, quantity=Decimal('2.00'))

        self.assertEqual(movement.total_cost, Decimal('2.50'))


class StockMovementFormTests(SimpleTestCase):
    @patch('traceability.forms.ClinicalEncounter.objects.select_related')
    @patch('traceability.forms.SupplyItem.objects.filter')
    @patch('traceability.forms.SupplyLot.objects')
    def test_consumption_builds_fefo_recommendations(self, lot_manager, item_filter, encounter_select):
        item_qs = MagicMock()
        item_qs.order_by.return_value = item_qs
        item_filter.return_value = item_qs

        lot_qs = MagicMock()
        filtered_qs = MagicMock()
        excluded_qs = MagicMock()
        filtered_by_item_qs = MagicMock()
        ordered_qs = MagicMock()
        ordered_qs.__getitem__.return_value = ['lot-a', 'lot-b']

        lot_manager.select_related.return_value = lot_qs
        lot_qs.filter.return_value = filtered_qs
        filtered_qs.exclude.return_value = excluded_qs
        excluded_qs.filter.return_value = filtered_by_item_qs
        filtered_by_item_qs.annotate.return_value = ordered_qs
        ordered_qs.order_by.return_value = ordered_qs

        encounter_qs = MagicMock()
        encounter_qs.order_by.return_value = encounter_qs
        encounter_select.return_value = encounter_qs

        form = StockMovementForm(initial={'movement_type': MovementType.CONSUMPTION, 'supply_item': '3'})

        self.assertEqual(form.fefo_recommendations, ['lot-a', 'lot-b'])

    @patch('traceability.forms.ClinicalEncounter.objects.select_related')
    @patch('traceability.forms.SupplyItem.objects.filter')
    @patch('traceability.forms.SupplyLot.objects.select_related')
    def test_clean_requires_supply_item_for_consumption(self, lot_select, item_filter, encounter_select):
        item_qs = MagicMock()
        item_qs.order_by.return_value = item_qs
        item_filter.return_value = item_qs

        lot_qs = MagicMock()
        lot_qs.filter.return_value.exclude.return_value.annotate.return_value.order_by.return_value = lot_qs
        lot_qs.__getitem__.return_value = []
        lot_select.return_value = lot_qs

        encounter_qs = MagicMock()
        encounter_qs.order_by.return_value = encounter_qs
        encounter_select.return_value = encounter_qs

        form = StockMovementForm(data={
            'supply_item': '',
            'lot': '',
            'movement_type': MovementType.CONSUMPTION,
            'quantity': '1.00',
            'occurred_at': '2026-03-10T10:00',
            'clinical_encounter': '',
            'reason': 'Consumo',
            'notes': '',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('supply_item', form.errors)


class TraceabilityViewsTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = type('User', (), {'is_authenticated': True})()

    @patch('traceability.views.StockMovementForm')
    @patch('traceability.views.render')
    @patch('traceability.views.get_object_or_404')
    def test_create_movement_prefills_from_encounter(self, get_object_mock, render_mock, form_cls):
        encounter = MagicMock()
        encounter.pk = 4
        encounter.patient.last_name = 'Perez'
        encounter.patient.first_name = 'Ana'
        get_object_mock.return_value = encounter
        render_mock.side_effect = lambda request, template, context: context

        form = MagicMock()
        form.initial = {'clinical_encounter': 4, 'movement_type': 'CONSUMPTION', 'reason': 'Consumo en atencion de Perez, Ana', 'supply_item': '7'}
        form.fefo_recommendations = ['lot-a']
        form_cls.return_value = form

        request = self.factory.get('/traceability/movements/new/', {'encounter': '4', 'movement_type': 'CONSUMPTION', 'supply_item': '7'})
        request.user = self.user

        context = views.create_movement(request)

        _, kwargs = form_cls.call_args
        self.assertEqual(kwargs['initial']['clinical_encounter'], 4)
        self.assertEqual(kwargs['initial']['movement_type'], 'CONSUMPTION')
        self.assertEqual(kwargs['initial']['supply_item'], '7')
        self.assertIn('Perez', kwargs['initial']['reason'])
        self.assertEqual(context['recommended_lots'], ['lot-a'])
