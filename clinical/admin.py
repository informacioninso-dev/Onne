from django.contrib import admin

from .models import ClinicalEncounter, ClinicalNoteTemplate, ClinicalOrder, DiagnosisCatalogEntry


@admin.register(ClinicalNoteTemplate)
class ClinicalNoteTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'diagnosis', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'diagnosis')


@admin.register(ClinicalEncounter)
class ClinicalEncounterAdmin(admin.ModelAdmin):
    list_display = ('patient', 'started_at', 'diagnosis', 'status')
    list_filter = ('status',)
    search_fields = ('patient__first_name', 'patient__last_name', 'patient__mrn', 'diagnosis', 'chief_complaint')
    autocomplete_fields = ('patient', 'appointment', 'template')


@admin.register(ClinicalOrder)
class ClinicalOrderAdmin(admin.ModelAdmin):
    list_display = ('title', 'encounter', 'order_type', 'priority', 'status', 'requested_at')
    list_filter = ('order_type', 'priority', 'status')
    search_fields = ('title', 'instructions', 'result_notes', 'encounter__patient__first_name', 'encounter__patient__last_name')
    autocomplete_fields = ('encounter',)


@admin.register(DiagnosisCatalogEntry)
class DiagnosisCatalogEntryAdmin(admin.ModelAdmin):
    list_display = ('code', 'title', 'system', 'is_active')
    list_filter = ('system', 'is_active')
    search_fields = ('code', 'title')
