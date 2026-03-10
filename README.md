# Onne Health ERP

**Tipo de documento:** estado actual + vision futura

## Estado del documento

Este README mezcla dos perspectivas:

- El estado actual del repositorio.
- La vision objetivo del producto a mediano plazo.

Cuando exista diferencia entre ambas, prevalece el estado actual del codigo para decisiones de implementacion.

## Estado actual del repositorio

Actualmente el proyecto implementa una base Django con multitenancy por schema usando `django-tenants`.

### Componentes presentes hoy

- `tenants`: tenants, dominios, memberships y acceso entre schema publico y tenants.
- `core`: base publica y dashboard inicial.
- `patients`: registro base de pacientes.
- `appointments`: agenda base de citas.
- PostgreSQL como base de datos.
- Poetry para dependencias.

### Forma actual de ejecucion local

- `poetry install`
- `poetry run python manage.py migrate_schemas --shared`
- `poetry run python manage.py setup_public_tenant --domains localhost,127.0.0.1`
- `poetry run python manage.py createsuperuser`
- `poetry run python manage.py runserver`

## Vision futura del producto

Onne se proyecta como un ERP de salud de alta trazabilidad para gestionar operacion clinica, inventario tecnico, facturacion y analitica, con enfoque en cumplimiento normativo para Ecuador y buenas practicas alineadas con ISO 13485.

### Objetivos de producto

- Gestionar pacientes y atencion medica.
- Controlar inventario de farmacos y dispositivos medicos con trazabilidad por lote, serie y expiracion.
- Calcular costos reales de atencion.
- Integrar facturacion electronica.
- Proveer analitica operativa y financiera.
- Garantizar auditoria, privacidad y consistencia transaccional.

### Principios de arquitectura objetivo

- Backend basado en Django y PostgreSQL.
- Arquitectura por capas.
- Logica de negocio concentrada en servicios.
- Consultas complejas concentradas en selectores.
- Trazabilidad y auditoria como capacidades nativas.

### Modulos objetivo

- `patients`
- `clinical`
- `trace`
- `finance`
- `insight`
- `auditing`
- `security`
- `users`

## Reglas criticas

- No se hacen deletes fisicos en datos clinicos ni trazables.
- Todo proceso que afecte inventario o finanzas debe ejecutarse con `transaction.atomic()`.
- Toda mutacion relevante debe generar trazabilidad auditable.
- El consumo de insumos debe respetar FEFO.
- La historia clinica y otros datos sensibles deben protegerse con controles de acceso y cifrado cuando aplique.

## Documentos relacionados

- `AGENTS.md`
- `docs/ARCHITECTURE.md`
- `docs/COMPLIANCE.md`
- `docs/ROADMAP.md`
- `CONTRIBUTING.md`
- `PROMPT_CODEX_BACKEND.md`
- `PROMPT_CODEX_REVIEW.md`
- `docs/adr/ADR_TEMPLATE.md`

