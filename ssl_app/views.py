import os
import yaml
import logging
import boto3
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
import aioboto3
import asyncio
import time
from ruamel.yaml import YAML

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# async def check_certificate_status(certificate_arn):
#     async with aioboto3.create_client('acm') as acm_client:
#         try:
#             # Describe the certificate
#             response = await acm_client.describe_certificate(CertificateArn=certificate_arn)
#             # Extract the status from the response
#             certificate_status = response['Certificate']['Status']
#             return certificate_status
#         except Exception as e:
#             print(f"Error checking certificate status: {e}")
#             return None

# async def main(certificate_arn):
#     status = await check_certificate_status(certificate_arn)
#     if status == "ISSUED":
#         print("The certificate status is ISSUED.")
#     else:
#         print(f"The certificate status is {status}.")

@api_view(['GET'])
def check_certificate_status(request):
    certificate_arn = request.query_params.get('arn')
    
    if not certificate_arn:
        return Response({"error": "Certificate ARN is required"}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        acm_client = boto3.client('acm')
        cert_description = acm_client.describe_certificate(CertificateArn=certificate_arn)
        cert_status = cert_description['Certificate']['Status']
        
        return Response({
            "certificate_arn": certificate_arn,
            "status": cert_status
        }, status=status.HTTP_200_OK)
    
    except acm_client.exceptions.ResourceNotFoundException:
        return Response({"error": "Certificate not found"}, status=status.HTTP_404_NOT_FOUND)
    
    except Exception as e:
        return Response({"error": f"An error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def create_ssl_certificate(request):
    branch_name = request.data.get('branch_name')
    if not branch_name:
        return Response({"error": "Branch name is required"}, status=status.HTTP_400_BAD_REQUEST)

    sanitized_branch_name = branch_name.replace('_', '-')
    hostname = f"{sanitized_branch_name}.solytics.us"

    acm_client = boto3.client('acm')
    try:
        response = acm_client.request_certificate(
            DomainName=hostname,
            ValidationMethod='DNS',
            Options={'CertificateTransparencyLoggingPreference': 'ENABLED'}
        )
        certificate_arn = response['CertificateArn']
        print(f'Certificate ARN: {certificate_arn}')
    except Exception as e:
        return Response({"error": f"Failed to create SSL certificate: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    #route and map the host

    # waiter = acm_client.get_waiter('certificate_validated')
    # try:
    #     waiter.wait(CertificateArn=certificate_arn)
    # except Exception as e:
    #     return Response({"error": f"Certificate validation timed out: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Get the DNS validation records
    retry_count = 0
    max_retries = 5
    dns_records = None
    initial_status = None
    while retry_count < max_retries:
        try:
            cert_details = acm_client.describe_certificate(CertificateArn=certificate_arn)
            initial_status = cert_details['Certificate']['Status']
            
            # Check if DomainValidationOptions is available
            if 'DomainValidationOptions' in cert_details['Certificate']:
                domain_validation_options = cert_details['Certificate']['DomainValidationOptions']
                if domain_validation_options and 'ResourceRecord' in domain_validation_options[0]:
                    dns_records = domain_validation_options[0]['ResourceRecord']
                    break  # Exit the loop if we successfully got the DNS records
            
            print(f"Attempt {retry_count + 1}: Certificate details retrieved, but DNS records not yet available.")
        except Exception as e:
            return Response({"error": f"Failed to get validation records: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Step 3: Create Route 53 records for certificate validation
    zone_id = "Z073211023REDLUYMTKDC"  # your hosted zone ID
    try:
        create_route53_validation_record(zone_id, dns_records['Name'], dns_records['Value'])
    except Exception as e:
        return Response({"error": f"Failed to create Route 53 validation record: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Step 4: Create CNAME record to route the hostname
    target_dns_name = "nimbus-dev-streamlit-991053992.ap-south-1.elb.amazonaws.com"
    try:
        create_route53_cname_record(sanitized_branch_name, hostname, target_dns_name, zone_id)
    except Exception as e:
        return Response({"error": f"Failed to create CNAME record: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    update_values_yml(sanitized_branch_name, hostname, certificate_arn)

    # asyncio.run(main(certificate_arn))
    
    return Response({
        "message": "SSL certificate created and stored successfully",
        "branch_name": branch_name,
        "hostname": hostname,
        "certificate_arn": certificate_arn
    }, status=status.HTTP_201_CREATED) 

def create_route53_validation_record(zone_id, record_name, record_value):
    route53 = boto3.client('route53')
    change_batch = {
        'Changes': [
            {
                'Action': 'UPSERT',
                'ResourceRecordSet': {
                    'Name': record_name,
                    'Type': 'CNAME',
                    'TTL': 300,
                    'ResourceRecords': [{'Value': record_value}],
                }
            }
        ]
    }
    route53.change_resource_record_sets(HostedZoneId=zone_id, ChangeBatch=change_batch)

def create_route53_cname_record(branch_name, hostname, target_dns_name, zone_id, weight=None):
    route53 = boto3.client('route53')
    try:
        change_batch = {
            'Changes': [
                {
                    'Action': 'UPSERT',
                    'ResourceRecordSet': {
                        'Name': hostname,
                        'Type': 'CNAME',
                        'TTL': 300,
                        'ResourceRecords': [{'Value': target_dns_name}],
                    }
                }
            ]
        }
        if weight is not None:
            change_batch['Changes'][0]['ResourceRecordSet'].update({
                'SetIdentifier': branch_name,
                'Weight': weight
            })
        response = route53.change_resource_record_sets(
            HostedZoneId=zone_id,
            ChangeBatch=change_batch
        )
        logger.info(f"Successfully created CNAME record for {hostname} pointing to {target_dns_name}")
    except Exception as e:
        logger.error(f"Error creating CNAME record for {hostname}: {str(e)}")
        raise

def update_values_yml(branch_name, host_name, certificate_arn):
    print("updating values.yaml")
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    values_file_path = os.path.join(parent_dir, 'values.yaml')
    # values_file_path = 'values.yml'  # Update this with the actual path to your values.yml file

    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.indent(mapping=2, sequence=4, offset=2)

    try:
        # Read the existing values.yml file
        if os.path.exists(values_file_path):
            with open(values_file_path, 'r') as file:
                values = yaml.load(file)

            continuous_branch_name = branch_name.replace('-', '').replace('_', '').lower()
            # Update the necessary fields
            values['ingress']['annotations']['alb.ingress.kubernetes.io/certificate-arn'] = certificate_arn
            values['ingress']['hosts'][0]['host'] = host_name
            values['nameOverride'] = f"streamlit-{continuous_branch_name}"
            values['fullnameOverride'] = f"streamlit-{continuous_branch_name}"

            # Write the updated values back to the values.yml file
            with open(values_file_path, 'w') as file:
                yaml.dump(values, file)

            print(f"values.yaml file updated successfully at {values_file_path}")
    
    except Exception as e:
        print(f"Error updating : {str(e)}")