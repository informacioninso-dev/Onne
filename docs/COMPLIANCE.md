# Compliance Base - Onne

**Tipo de documento:** vision futura + guia de control

## Estado del documento

Este archivo define criterios base de cumplimiento y controles tecnicos esperados. No debe interpretarse como certificacion ni como afirmacion legal cerrada.

## Enfoque

Onne debe diseniarse bajo estos ejes:

- privacidad y proteccion de datos
- trazabilidad sanitaria
- historia clinica
- auditabilidad
- integridad operativa
- segregacion de funciones

## Ecuador

### Proteccion de datos personales

Aplicar principios compatibles con LOPDP:

- minimizacion
- finalidad
- confidencialidad
- acceso controlado
- trazabilidad de acceso
- privacidad desde el diseno

### Historia clinica

La historia clinica debe manejarse como dato sensible y confidencial.

Implicaciones tecnicas:

- acceso restringido por rol
- logs de acceso
- no exposicion masiva por API
- cifrado de contenido sensible
- conservacion controlada

### Receta y atencion

La prescripcion y la atencion deben permitir estructura suficiente para cumplir requisitos locales de identificacion del paciente y del profesional.

### Trazabilidad sanitaria

Aunque una normativa especifica haya cambiado o sido derogada, el sistema debe implementar trazabilidad robusta como politica de calidad y control.

Campos minimos:

- lote
- serie si aplica
- fecha de expiracion
- registro sanitario si aplica
- proveedor
- paciente final
- atencion o documento asociado

## ISO 13485 - enfoque aplicable al software

Aunque el ERP no reemplaza el sistema de calidad, debe facilitar:

- trazabilidad
- registros integros
- control de cambios
- recuperacion de informacion
- auditoria
- gestion documental futura

## Controles tecnicos minimos

### Control de acceso

- RBAC
- principio de menor privilegio
- separacion de rol clinico, financiero y tecnico

### Auditoria

- logs inmutables de cambios
- logs de acceso a datos sensibles
- referencia de actor y timestamp

### Integridad de datos

- constraints
- foreign keys con `PROTECT` cuando aplique
- soft delete

### Seguridad de datos

- cifrado aplicativo para contenido clinico sensible
- secretos fuera del codigo
- ambientes separados
- backups

## Riesgos de incumplimiento

- acceso excesivo a historia clinica
- ausencia de registro de lectura
- consumo de insumos sin lote
- stock negativo
- anulacion destructiva de registros
- edicion sin trazabilidad
- exposicion de informacion sensible en logs

## Recomendacion documental adicional

Crear mas adelante:

- matriz requisito normativo -> control tecnico
- matriz dato personal -> base legal -> control
- politica de retencion
- politica de acceso
- inventario de activos de informacion
