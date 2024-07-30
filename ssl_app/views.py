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

@api_view(['POST'])
def create_ssl_certificate(request):
    branch_name = request.data.get('branch_name')
    if not branch_name:
        return Response({"error": "Branch name is required"}, status=status.HTTP_400_BAD_REQUEST)
    hostname = f"{branch_name}.solytics.us"

    #route and map the host
    target_dns_name = "nimbus-dev-streamlit-991053992.ap-south-1.elb.amazonaws.com"  #"your-application-load-balancer-dns-name"
    zone_id = "Z073211023REDLUYMTKDC"  #"your-hosted-zone-id"
    create_route53_cname_record(branch_name, hostname, target_dns_name, zone_id)

    #create certificate and Retrieve certificate ARN 
    acm_client = boto3.client('acm')
    response = acm_client.request_certificate(
    DomainName=hostname,
    ValidationMethod='DNS',
    Options={
        'CertificateTransparencyLoggingPreference': 'ENABLED'
    }
    )
    certificate_arn = response['CertificateArn']
    print(f'Certificate ARN: {certificate_arn}')
    
    # Debugging output
    certificate_arn = None
    paginator = acm_client.get_paginator('list_certificates')
    for page in paginator.paginate():
        for cert in page['CertificateSummaryList']:
            # Debugging output
            print(f"Checking certificate: {cert['DomainName']} with ARN {cert['CertificateArn']}")
            if cert['DomainName'] == hostname:
                certificate_arn = cert['CertificateArn']
                break
        if certificate_arn:
            break

    # asyncio.run(main(certificate_arn))
    
    return Response({
        "message": "SSL certificate created and stored successfully",
        "branch_name": branch_name,
        "hostname": hostname,
        "certificate_arn": certificate_arn
    }, status=status.HTTP_201_CREATED) 

       
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