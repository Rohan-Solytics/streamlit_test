import os
import yaml
import boto3
from ruamel.yaml import YAML

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

def update_values_yml(branch_name, host_name, certificate_arn):
    print("updating values.yaml")
    # Get the directory where views.py is located
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # Navigate to the parent directory and then to the streamlit-helm directory
    parent_dir = os.path.dirname(current_dir)

    streamlit_helm_dir = os.path.join(parent_dir, 'streamlit-helm')
    # values_file_path = os.path.join(parent_dir, 'values.yaml')
    values_file_path = os.path.join(streamlit_helm_dir, 'values.yaml')
    
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
        