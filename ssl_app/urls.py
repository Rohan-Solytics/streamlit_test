from django.urls import path
from .views import CheckCertificateStatus, CreateSSLCertificate

urlpatterns = [
    path('create-ssl/', CreateSSLCertificate.as_view(), name='create-ssl'),
    path('check-ssl-status/', CheckCertificateStatus.as_view(), name='check-status'),
]