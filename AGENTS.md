# AGENTS

**Tipo de documento:** guia de trabajo

## Alcance

Este archivo define como deben colaborar los agentes de IA con el equipo humano para desarrollar Onne sin romper arquitectura, trazabilidad, seguridad o cumplimiento.

## Regla principal

Los agentes pueden proponer, generar y refactorizar codigo, pero no deben inventar requisitos regulatorios ni alterar reglas criticas de negocio sin instruccion explicita.

## Limites obligatorios

### 1. Arquitectura

El agente debe respetar la separacion por capas definida para el proyecto objetivo:

- `models`: estructura y constraints.
- `services`: logica de negocio.
- `selectors`: consultas complejas.
- `api`: exposicion de endpoints cuando exista esa capa.

No debe mover logica de negocio a serializers, views o modelos salvo instruccion explicita.

### 2. Seguridad

El agente no debe:

- exponer datos sensibles en logs
- quitar validaciones de permisos
- almacenar historia clinica en texto plano
- introducir accesos directos inseguros a datos clinicos

### 3. Trazabilidad

El agente no debe:

- permitir consumo de stock sin lote
- omitir fecha de expiracion si aplica
- omitir registro sanitario si aplica
- romper FEFO
- permitir stock negativo

### 4. Auditoria

Toda mutacion relevante debe dejar trazabilidad auditable.

### 5. Normativa

El agente no debe afirmar cumplimiento legal sin sustento documental del proyecto.

## Forma correcta de pedir tareas a un agente

Toda tarea debe incluir:

- contexto funcional
- modulo afectado
- restriccion tecnica
- criterio de aceptacion
- archivos permitidos
- archivos prohibidos
- pruebas esperadas

## Plantilla de instruccion para agente

### Contexto

Estamos desarrollando Onne con Django y PostgreSQL.

### Objetivo

Implementar `[describir tarea]`.

### Restricciones

- Respetar arquitectura en capas.
- No poner logica en views ni serializers.
- Usar `transaction.atomic()` si se afecta inventario o finanzas.
- Mantener compatibilidad con auditoria y soft delete.

### Archivos a tocar

- listar archivos

### No tocar

- listar archivos sensibles

### Entregable

- codigo
- pruebas
- breve explicacion tecnica

## Tipos de tareas aptas para agentes

- scaffold de apps
- serializers simples
- views REST basicas
- tests unitarios
- constraints y modelos
- selectores de lectura
- refactors controlados
- documentacion tecnica

## Tipos de tareas que requieren revision humana fuerte

- diseno regulatorio
- historia clinica
- seguridad y cifrado
- SRI
- costeo de atencion
- trazabilidad de recall
- permisos por rol clinico
- acceso a datos sensibles

## Estandar de respuesta esperado del agente

1. Que entendio.
2. Que archivos tocara.
3. Riesgos.
4. Implementacion.
5. Pruebas.
6. Supuestos.

## Criterios de rechazo de PR generado por IA

Rechazar si:

- mezcla capas
- rompe FEFO
- elimina auditoria
- introduce stock negativo
- omite permisos
- inventa normativa
- usa signals para procesos criticos
- expone datos sensibles

## Filosofia del proyecto

La IA acelera. No decide cumplimiento.
La IA ayuda a construir. No define politica regulatoria.
La IA propone. El equipo valida.
