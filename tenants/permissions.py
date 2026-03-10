from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect

from .models import TenantMembership


ROLE_LEVELS = {
    TenantMembership.ROLE_STAFF: 10,
    TenantMembership.ROLE_CLINICAL: 20,
    TenantMembership.ROLE_ADMIN: 30,
    TenantMembership.ROLE_OWNER: 40,
}


def get_tenant_membership(request):
    tenant = getattr(request, 'tenant', None)
    user = getattr(request, 'user', None)

    if not tenant or tenant.schema_name == settings.PUBLIC_SCHEMA_NAME:
        return None
    if user is None or not getattr(user, 'is_authenticated', False) or getattr(user, 'is_superuser', False):
        return None

    cached = getattr(request, 'tenant_membership', None)
    if cached is not None:
        return cached

    membership = (
        TenantMembership.objects.select_related('tenant', 'user')
        .filter(tenant=tenant, user=user, is_active=True)
        .first()
    )
    request.tenant_membership = membership
    return membership


def has_minimum_role(request, minimum_role):
    user = getattr(request, 'user', None)
    if user and getattr(user, 'is_authenticated', False) and getattr(user, 'is_superuser', False):
        return True

    tenant = getattr(request, 'tenant', None)
    if not tenant or tenant.schema_name == settings.PUBLIC_SCHEMA_NAME:
        return True

    membership = get_tenant_membership(request)
    if not membership:
        return False

    return ROLE_LEVELS.get(membership.role, 0) >= ROLE_LEVELS[minimum_role]


def tenant_role_required(minimum_role, message='No tienes permisos suficientes en esta clinica.'):
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            if has_minimum_role(request, minimum_role):
                return view_func(request, *args, **kwargs)
            messages.error(request, message)
            return redirect('dashboard')

        return wrapped

    return decorator


