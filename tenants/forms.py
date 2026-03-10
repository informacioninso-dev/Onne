import re

from django import forms
from django.conf import settings
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError

from .models import Client, TenantMembership


_SCHEMA_RE = re.compile(r"^[a-z][a-z0-9_]{2,62}$")


_INPUT = {"class": "w-full rounded-lg border px-3 py-2"}


class TenantCreateForm(forms.Form):
    name = forms.CharField(label="Nombre", max_length=120, widget=forms.TextInput(attrs=_INPUT))
    schema_name = forms.CharField(label="Schema", max_length=63, widget=forms.TextInput(attrs=_INPUT))
    subdomain = forms.CharField(
        label="Subdominio",
        max_length=63,
        widget=forms.TextInput(attrs={**_INPUT, "placeholder": "acme"}),
        help_text=f"Se convertira en subdominio.{settings.TENANT_BASE_DOMAIN}"
    )
    plan = forms.ChoiceField(label="Plan", choices=Client.PLAN_CHOICES, widget=forms.Select(attrs=_INPUT))

    admin_username = forms.CharField(label="Usuario admin", max_length=150, required=False, widget=forms.TextInput(attrs=_INPUT))
    admin_email = forms.EmailField(label="Email admin", required=False, widget=forms.EmailInput(attrs=_INPUT))
    admin_password = forms.CharField(
        label="Password admin",
        required=False,
        widget=forms.PasswordInput(attrs=_INPUT),
    )

    def clean_schema_name(self):
        value = (self.cleaned_data.get("schema_name") or "").strip().lower()
        if value == "public":
            raise ValidationError("El schema 'public' esta reservado.")
        if not _SCHEMA_RE.match(value):
            raise ValidationError("Schema invalido. Usa letras, numeros y guion bajo; min 3 caracteres.")
        return value

    def clean_subdomain(self):
        value = (self.cleaned_data.get("subdomain") or "").strip().lower()
        value = value.replace("https://", "").replace("http://", "").strip("/")
        base_domain = settings.TENANT_BASE_DOMAIN
        if value.endswith(f".{base_domain}"):
            value = value[: -(len(base_domain) + 1)]

        if not re.match(r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$", value):
            raise ValidationError("Subdominio invalido. Solo letras, numeros y guiones.")

        full_domain = f"{value}.{base_domain}"
        return full_domain

    def clean(self):
        cleaned = super().clean()
        username = (cleaned.get("admin_username") or "").strip()
        password = (cleaned.get("admin_password") or "").strip()
        email = (cleaned.get("admin_email") or "").strip()

        any_admin = any([username, password, email])
        if any_admin and not username:
            self.add_error("admin_username", "Requerido si vas a crear/usar admin.")
        if any_admin and not password:
            self.add_error("admin_password", "Requerido si vas a crear/usar admin.")
        return cleaned


class TenantEditForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ("name", "plan", "is_active")
        widgets = {
            "name": forms.TextInput(attrs=_INPUT),
            "plan": forms.Select(attrs=_INPUT),
            "is_active": forms.CheckboxInput(attrs={"class": "h-4 w-4 rounded border-gray-300"}),
        }


class AddMemberForm(forms.Form):
    username = forms.CharField(
        label="Usuario",
        max_length=150,
        widget=forms.TextInput(attrs={**_INPUT, "placeholder": "username"}),
    )
    role = forms.ChoiceField(
        label="Rol",
        choices=TenantMembership.ROLE_CHOICES,
        initial=TenantMembership.ROLE_STAFF,
        widget=forms.Select(attrs=_INPUT),
    )


class MembershipRoleForm(forms.ModelForm):
    class Meta:
        model = TenantMembership
        fields = ('role',)
        widgets = {
            'role': forms.Select(attrs=_INPUT),
        }


class TenantAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        label="Usuario o correo",
        max_length=254,
        widget=forms.TextInput(
            attrs={
                "autofocus": True,
                "class": "w-full rounded-lg border px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500",
            }
        ),
    )
    password = forms.CharField(
        label="Contrasena",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "w-full rounded-lg border px-3 py-2 pr-10 focus:outline-none focus:ring-2 focus:ring-blue-500",
            }
        ),
    )
