from django.urls import path

from . import views

app_name = 'patients'

urlpatterns = [
    path('', views.index, name='index'),
    path('new/', views.create, name='create'),
    path('<int:pk>/', views.detail, name='detail'),
    path('<int:pk>/edit/', views.edit, name='edit'),
    path('<int:pk>/toggle-active/', views.toggle_active, name='toggle_active'),
]
