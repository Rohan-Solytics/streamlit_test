from rest_framework import serializers
from .models import SSLCertificate

class SSLCertificateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SSLCertificate
        fields = ['branch_name', 'hostname', 'certificate', 'private_key']