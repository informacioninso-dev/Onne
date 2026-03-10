from django.urls import path

from . import views

app_name = 'clinical'

urlpatterns = [
    path('', views.index, name='index'),
    path('new/', views.create, name='create'),
    path('templates/', views.template_index, name='template_index'),
    path('templates/new/', views.create_template, name='create_template'),
    path('templates/<int:pk>/edit/', views.edit_template, name='edit_template'),
    path('diagnosis-suggestions/', views.diagnosis_suggestions, name='diagnosis_suggestions'),
    path('<int:pk>/', views.detail, name='detail'),
    path('<int:pk>/edit/', views.edit, name='edit'),
    path('<int:pk>/status/', views.update_status, name='update_status'),
    path('<int:encounter_pk>/orders/new/', views.create_order, name='create_order'),
    path('orders/<int:pk>/edit/', views.edit_order, name='edit_order'),
    path('orders/<int:pk>/status/', views.update_order_status, name='update_order_status'),
]
