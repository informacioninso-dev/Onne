# Arquitectura de Onne

**Tipo de documento:** vision futura

## Estado del documento

Este archivo describe la arquitectura objetivo del producto. No todo lo aqui descrito esta implementado en el repositorio actual.

## Principio base

Onne se construye sobre una base multitenant. La multitenencia no es un detalle de infraestructura, sino una capacidad fundacional del sistema.

Eso implica desde la arquitectura:

- tenant publico para administracion general
- tenants por empresa o clinica
- subdominios por tenant
- aislamiento por schema
- memberships y permisos por tenant
- reglas distintas para superadmin y usuarios operativos

## Vision general

Onne evoluciona hacia un ERP de salud con foco en:

- operacion clinica
- trazabilidad de inventario tecnico
- facturacion
- analitica
- cumplimiento normativo

La arquitectura objetivo es de capas desacopladas y tenant-aware.

## Fundacion multitenant

### Componentes base

- `django-tenants` como soporte de aislamiento por schema
- esquema publico para gestion global
- schemas por tenant para operacion aislada
- resolucion por dominio o subdominio
- memberships por tenant
- politicas de acceso segun tenant activo

### Reglas estructurales de multitenencia

- Todo dato operativo debe vivir dentro del tenant correcto.
- Ningun modulo funcional debe asumir contexto global salvo el tenant publico.
- Los permisos deben evaluarse con contexto de tenant.
- La auditoria debe registrar tenant ademas de actor y accion.
- Los procesos administrativos globales deben ejecutarse desde el schema publico.

## Capas

### 1. Modelos

Responsables de la persistencia y constraints basicos.
No deben contener logica de negocio compleja.

### 2. Servicios

Responsables de:

- reglas de negocio
- validaciones operativas
- transacciones
- auditoria
- coordinacion entre modulos
- enforcement de contexto tenant cuando aplique

### 3. Selectores

Responsables de:

- queries complejas
- reporting
- paneles BI
- datasets optimizados
- lectura consistente por tenant

### 4. API

Responsable de:

- serializers
- views
- endpoints
- autenticacion de acceso
- validacion de entrada basica
- resolucion correcta del tenant de trabajo

## Estructura sugerida

```text
apps/
  common/
  auditing/
  security/
  users/
  patients/
  clinical/
  trace/
  finance/
  insight/
```

## Reglas estructurales

- Los services pueden usar models y selectors.
- Los selectors no deben escribir.
- La API llama services o selectors.
- Los models no deben coordinar procesos de negocio.
- Ninguna capa debe saltarse el contexto tenant.

## Diseno de persistencia

### Patrones obligatorios

- UUIDs
- timestamps
- soft delete
- constraints
- indices en campos criticos
- trazabilidad por tenant cuando corresponda

### Campos criticos indexados

- historia clinica
- identificacion
- numero de lote
- numero de serie
- registro sanitario
- fecha de expiracion
- doctor
- referencia documental

## Transaccionalidad

Usar `transaction.atomic()` cuando:

- se consume stock
- se actualiza costo de atencion
- se registra movimiento y auditoria
- se ejecutan procesos financiero-inventario
- se crean o modifican entidades dependientes del mismo proceso tenant

## Seguridad y auditoria

- RBAC
- logs de acceso a datos personales
- cifrado de campos sensibles
- minimizacion de respuesta API
- trazabilidad de cambios con actor, accion, fecha, valor anterior y valor nuevo
- referencia del tenant afectado en eventos auditables

## Reglas de no uso

No usar:

- logica critica en signals
- cascadas destructivas en trazabilidad
- deletes fisicos en clinico o inventario
- consultas BI directamente en views
- accesos cross-tenant sin mecanismo explicito y auditado

## Modulos objetivo

### Trace

- insumos
- lotes
- movimientos
- consumos
- ficha de trazabilidad
- rastreo de recalls

### Clinical

- paciente
- atencion medica
- diagnostico
- notas clinicas
- receta
- vinculo con insumos consumidos

### Finance

- costo real de atencion
- documentos financieros
- integracion SRI
- conciliacion futura

### Insight

- rentabilidad por doctor
- consumo por insumo
- vencimientos
- quiebre de stock
- productividad operativa
- indicadores por tenant y agregados globales cuando este permitido
