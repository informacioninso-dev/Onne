from django.contrib import admin

from .models import StockMovement, SupplyItem, SupplyLot


@admin.register(SupplyItem)
class SupplyItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku', 'unit_of_measure', 'is_active')
    list_filter = ('is_active', 'track_expiration')
    search_fields = ('name', 'sku')


@admin.register(SupplyLot)
class SupplyLotAdmin(admin.ModelAdmin):
    list_display = ('item', 'lot_number', 'expires_at', 'current_quantity', 'is_blocked')
    list_filter = ('is_blocked', 'item')
    search_fields = ('item__name', 'item__sku', 'lot_number', 'registry_number')


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ('lot', 'movement_type', 'quantity', 'occurred_at', 'clinical_encounter')
    list_filter = ('movement_type',)
    search_fields = ('lot__item__name', 'lot__lot_number', 'reason')
