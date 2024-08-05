from django.urls import path
from . import views

urlpatterns = [
    path('create-ssl/', views.create_ssl_certificate, name='create-ssl'),
    path('check-ssl-status/', views.check_certificate_status, name='check-status'),
]