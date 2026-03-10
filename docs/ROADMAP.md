# Roadmap de desarrollo - Onne

**Tipo de documento:** vision futura

## Estado del documento

Este roadmap describe la secuencia objetivo de construccion del producto. No representa necesariamente el estado implementado actual del repositorio.

## Objetivo

Construir el ERP por incrementos pequenos, verificables y seguros, tomando la multitenencia como fundacion tecnica y operativa del sistema.

## Fase 0 - Base multitenant

- Django con Poetry
- PostgreSQL
- `django-tenants`
- tenant publico
- tenants por empresa
- subdominios por tenant
- aislamiento por schema
- memberships por tenant
- acceso de superadmin y usuarios normales
- bootstrap de nuevas empresas
- settings por ambiente
- estructura inicial de apps

## Fase 1 - Fundaciones operativas

- modelo base UUID
- timestamp
- soft delete
- usuarios y roles
- auditoria inmutable
- logs de acceso a datos sensibles
- permisos por rol dentro de cada tenant
- base comun para catalogos y parametros

## Fase 2 - Pacientes y atencion

- paciente
- ficha base de paciente
- atencion medica
- diagnostico principal
- estructura basica de notas clinicas
- permisos por rol clinico

## Fase 3 - Trazabilidad e inventario

- insumo
- lote
- movimientos
- FEFO
- bloqueo de lotes vencidos
- consumo trazado vinculado a la atencion
- ficha de trazabilidad por paciente y atencion

## Fase 4 - Costeo clinico

- costo de insumos
- honorarios
- costos operativos
- costo total de atencion
- base para margen y rentabilidad

## Fase 5 - Facturacion

- documento comercial
- estructura para SRI
- integracion XML
- estados de documento
- relacion entre atencion, costo y documento financiero

## Fase 6 - BI e insight

- selectores de rentabilidad
- stock en riesgo
- prediccion de quiebre
- dashboards operativos
- indicadores por tenant y comparativos agregados si aplica

## Fase 7 - Compliance reforzado

- matriz de trazabilidad
- simulacion de recall
- accesos sensibles
- hardening de seguridad
- politicas documentales y controles auditables

## MVP recomendado

Para un primer MVP solido:

- base multitenant estable
- pacientes
- atencion medica
- inventario trazable
- consumo de insumos
- auditoria
- costo base de atencion

## Prioridad de construccion

1. Base multitenant
2. Seguridad y auditoria
3. Pacientes y atencion
4. Trazabilidad
5. Costeo
6. Facturacion
7. BI
