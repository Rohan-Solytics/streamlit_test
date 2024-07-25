import os
import yaml
from datetime import datetime, timedelta
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import SSLCertificate

def generate_ssl_certificate(hostname):
    # Generate a private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    # Generate a public key
    public_key = private_key.public_key()

    # Create a certificate builder
    builder = x509.CertificateBuilder()

    # Set the subject name
    builder = builder.subject_name(x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, hostname),
    ]))

    # Set the issuer name (self-signed, so it's the same as the subject)
    builder = builder.issuer_name(x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, hostname),
    ]))

    # Set the public key
    builder = builder.public_key(public_key)

    # Set the serial number
    builder = builder.serial_number(x509.random_serial_number())

    # Set the validity period
    builder = builder.not_valid_before(datetime.utcnow())
    builder = builder.not_valid_after(datetime.utcnow() + timedelta(days=365))

    # Add basic constraints extension
    builder = builder.add_extension(
        x509.BasicConstraints(ca=False, path_length=None), critical=True,
    )

    # Sign the certificate with the private key
    certificate = builder.sign(
        private_key=private_key, algorithm=hashes.SHA256(),
    )

    # Serialize the certificate and private key to PEM format
    certificate_pem = certificate.public_bytes(serialization.Encoding.PEM)
    private_key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )

    return certificate_pem.decode(), private_key_pem.decode()

@api_view(['POST'])
def create_ssl_certificate(request):
    branch_name = request.data.get('branch_name')
    if not branch_name:
        return Response({"error": "Branch name is required"}, status=status.HTTP_400_BAD_REQUEST)

    hostname = f"{branch_name}.solytics.us"
    
    # Generate SSL certificate
    certificate, private_key = generate_ssl_certificate(hostname)
    
    # Store in database
    ssl_cert, created = SSLCertificate.objects.update_or_create(
        branch_name=branch_name,
        defaults={
            'hostname': hostname,
            'certificate': certificate,
            'private_key': private_key
        }
    )
    
    # Set environment variables
    set_ssl_env_vars(branch_name, certificate, private_key)
    
    # Update values.yaml
    update_values_yaml(hostname, certificate)
    
    return Response({
        "message": "SSL certificate created and stored successfully",
        "branch_name": branch_name,
        "hostname": hostname,
        "certificate": certificate
    }, status=status.HTTP_201_CREATED)

def set_ssl_env_vars(branch_name, certificate, private_key):
    os.environ[f'SSL_CERT_{branch_name}'] = certificate
    os.environ[f'SSL_KEY_{branch_name}'] = private_key

def update_values_yaml(hostname, certificate):
    values_path = 'values.yaml'  # Assuming it's in the same directory

    print(f"Attempting to update file: {values_path}")

    try:
        if os.path.exists(values_path):
            with open(values_path, 'r') as file:
                values = yaml.safe_load(file) or {}
            print(f"Existing content: {values}")
        else:
            values = {'ssl_certificate': "", 'hostname': ""}
            print("File doesn't exist. Starting with default structure.")

        # Update the SSL certificate and hostname
        values['ssl_certificate'] = certificate
        values['hostname'] = hostname

        print(f"Updated values: {values}")

        with open(values_path, 'w') as file:
            yaml.dump(values, file, default_flow_style=False)
        print(f"Successfully updated {values_path} with SSL details for {hostname}")

        # Verify the file was updated
        with open(values_path, 'r') as file:
            updated_content = file.read()
        print(f"File content after update:\n{updated_content}")

    except Exception as e:
        print(f"Error updating {values_path}: {str(e)}", exc_info=True)