# Prompt base para Codex - Review

**Tipo de documento:** guia de trabajo

## Nota

Este prompt sirve para revisar cambios contra el estado actual del codigo y contra la arquitectura objetivo cuando aplique.

## Instruccion

Revisa el siguiente cambio del proyecto Onne.

## Evalua especificamente

- respeto de arquitectura por capas
- riesgo de seguridad
- riesgo regulatorio
- riesgo de trazabilidad
- calidad de tests
- posible deuda tecnica

## Marca como critico si detectas

- logica en views o serializers
- ausencia de `transaction.atomic()` en procesos criticos
- stock negativo posible
- perdida de auditoria
- exposicion de datos sensibles
- dependencia circular
- mezcla de lectura BI con logica de escritura

## Formato de salida

1. Resumen.
2. Hallazgos criticos.
3. Hallazgos importantes.
4. Mejoras sugeridas.
5. Veredicto.
