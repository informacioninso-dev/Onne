# Contributing

**Tipo de documento:** guia de trabajo

## Objetivo

Definir una forma estable de contribuir al proyecto sin deteriorar arquitectura, seguridad ni cumplimiento.

## Reglas generales

- Cambios pequenos y auditables.
- Un PR por tema.
- Toda regla de negocio va en services.
- Toda query compleja va en selectors.
- Nada de logica critica en signals.
- Nada de delete fisico en entidades criticas.

## Flujo sugerido

1. Crear issue o tarea.
2. Definir alcance.
3. Crear rama.
4. Implementar.
5. Probar.
6. Documentar decision relevante.
7. Abrir PR.

## Nomenclatura de ramas

- `feature/...`
- `fix/...`
- `refactor/...`
- `docs/...`

## Estandar de PR

Todo PR debe incluir:

- problema
- solucion
- riesgos
- pruebas ejecutadas
- impacto regulatorio, o indicar `sin impacto regulatorio directo`

## Revision minima

Validar:

- arquitectura
- seguridad
- trazabilidad
- auditoria
- pruebas
- naming
- impacto en datos sensibles

## Que requiere ADR

Crear ADR si se modifica:

- arquitectura
- cifrado
- permisos
- trazabilidad
- auditoria
- estrategia SRI
- estrategia de BI

## Que debe acompanar el codigo

- tests unitarios
- migraciones correctas
- breve documentacion si cambia comportamiento
- actualizacion de roadmap si aplica
