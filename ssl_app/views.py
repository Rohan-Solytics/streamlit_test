import os
import logging
import boto3
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import SSLCertificate
from .sslhelper import create_route53_validation_record, update_values_yml

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CheckCertificateStatus(APIView):
    def get(self, request):
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

class CreateSSLCertificate(APIView):
    def post(self, request):
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
        
        # Get the DNS validation records
        retry_count = 0
        max_retries = 10
        dns_records = None
        initial_status = None
        while retry_count < max_retries:
            try:
                cert_details = acm_client.describe_certificate(CertificateArn=certificate_arn)
                initial_status = cert_details['Certificate']['Status']
                if 'DomainValidationOptions' in cert_details['Certificate']:
                    domain_validation_options = cert_details['Certificate']['DomainValidationOptions']
                    if domain_validation_options and 'ResourceRecord' in domain_validation_options[0]:
                        dns_records = domain_validation_options[0]['ResourceRecord']
                        break
                print(f"Attempt {retry_count + 1}: Certificate details retrieved, but DNS records not yet available.")
            except Exception as e:
                return Response({"error": f"Failed to get validation records: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Create Route 53 records for certificate validation
        zone_id = "Z073211023REDLUYMTKDC"
        try:
            create_route53_validation_record(zone_id, dns_records['Name'], dns_records['Value'])
            print("created Route 53 validation record")
        except Exception as e:
            return Response({"error": f"Failed to create Route 53 validation record: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Create CNAME record to route the hostname
        target_dns_name = "nimbus-dev-streamlit-991053992.ap-south-1.elb.amazonaws.com"
        try:
            create_route53_validation_record(zone_id, hostname, target_dns_name)
            print("created CNAME record")
        except Exception as e:
            return Response({"error": f"Failed to create CNAME record: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        update_values_yml(sanitized_branch_name, hostname, certificate_arn)
        return Response({
            "message": "SSL certificate created and stored successfully",
            "branch_name": branch_name,
            "hostname": hostname,
            "certificate_arn": certificate_arn
        }, status=status.HTTP_201_CREATED)
