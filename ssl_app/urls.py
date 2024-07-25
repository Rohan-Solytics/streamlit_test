from django.urls import path
from . import views

urlpatterns = [
    path('create-ssl/', views.create_ssl_certificate, name='create-ssl'),
]