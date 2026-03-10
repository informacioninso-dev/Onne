# Prompt base para Codex - Backend

**Tipo de documento:** guia de trabajo

## Nota

Este prompt sirve como base operativa. Puede incluir reglas de arquitectura objetivo aunque parte de esa arquitectura aun no este materializada por completo en el repositorio.

## Contexto

Estamos desarrollando Onne con Django, PostgreSQL y Poetry.

## Arquitectura obligatoria

- Modelos: estructura persistente.
- Servicios: logica de negocio.
- Selectores: consultas complejas.
- API: serializers, views y urls cuando exista esa capa.

## Reglas obligatorias

- No pongas logica de negocio en serializers ni views.
- Usa `transaction.atomic()` si la tarea afecta inventario o finanzas.
- No rompas soft delete.
- No elimines auditoria.
- No permitas stock negativo.
- No expongas datos clinicos sensibles.
- No uses signals para procesos criticos.

## Tarea

`[describir tarea]`

## Archivos permitidos

`[listar]`

## Archivos restringidos

`[listar]`

## Entregable esperado

1. Codigo.
2. Tests.
3. Explicacion breve.
4. Riesgos o supuestos.
