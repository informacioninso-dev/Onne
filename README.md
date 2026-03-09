# Onne 360 (Base Limpia)

Repositorio reducido para iniciar el sistema gestor de clÃ­nica sobre Django + multitenancy por schema.

## Estado actual

- Apps activas:
  - `tenants` (schema/domain/memberships)
  - `core` (base mÃ­nima y dashboard)
  - `patients` (registro base de pacientes)
  - `appointments` (agenda de citas)
- Apps ERP heredadas eliminadas para evitar arrastrar deuda tÃ©cnica.

## Arranque local

```bash
poetry install
poetry run python manage.py migrate_schemas --shared
poetry run python manage.py setup_public_tenant --domains localhost,127.0.0.1
poetry run python manage.py createsuperuser
poetry run python manage.py runserver
```

## Clinica inicial

```bash
poetry run python manage.py bootstrap_clinic <schema> "<nombre>" <subdominio.dominio> --admin-user <usuario> --admin-email <email> --admin-password "<password>"
```

Ejemplo:

```bash
poetry run python manage.py bootstrap_clinic clinica_a "Clinica A" clinica-a.localhost --admin-user admin --admin-email admin@onne.local --admin-password "Onne2026!"
```

## Acceso y subdominios

- El superadmin accede al portal publico con usuario y contraseÃƒÂ±a para gestionar tenants.
- Los usuarios normales solo pueden entrar a tenants donde tengan membresÃƒÂ­a activa y deben autenticarse con contraseÃƒÂ±a.
- Para compartir sesiÃƒÂ³n entre subdominios (`empresa1.dominio.com`, `empresa2.dominio.com`), define `SESSION_COOKIE_DOMAIN` y `CSRF_COOKIE_DOMAIN` como `.dominio.com`.

