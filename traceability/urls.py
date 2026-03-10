from django.urls import path

from . import views

app_name = 'traceability'

urlpatterns = [
    path('', views.index, name='index'),
    path('items/new/', views.create_item, name='create_item'),
    path('lots/new/', views.create_lot, name='create_lot'),
    path('lots/<int:pk>/', views.lot_detail, name='lot_detail'),
    path('movements/new/', views.create_movement, name='create_movement'),
]
