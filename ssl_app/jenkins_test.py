import requests

# Define Jenkins server URL and job name
JOB_NAME = 'UBO'
USERNAME = 'nimbus_developer'
API_TOKEN = 'nyInDiuVUo'

JENKINS_URL = 'https://jenkins.solyticspartners.com/job/UBO/job/UBO-QA/job/UBO-DEV'

# Use wfapi to get the latest build status
wfapi_url = f'{JENKINS_URL}/wfapi/runs'

auth = (USERNAME, API_TOKEN)

#API or wfapi, if a build is still running, the result field is typically null


#for multiple builds
# try:
#     response = requests.get(wfapi_url, auth=auth)
#     response.raise_for_status()
#     build_info = response.json()

#     if build_info:
#         # Get the last 5 builds (or fewer if less than 5 builds exist)
#         num_builds_to_check = min(2, len(build_info))
#         print(f"Last {num_builds_to_check} builds:")
#         for i in range(num_builds_to_check):
#             build = build_info[i]
#             print(f"Build {i+1}: Status: {build['status']}, ID: {build['id']}, Timestamp: {build['startTimeMillis']}")
#     else:
#         print("No builds found.")


#for single one
try:
    response = requests.get(wfapi_url, auth=auth)
    response.raise_for_status()
    build_info = response.json()

    if build_info:
        latest_build = build_info[0]  # Get the latest build
        print(f"Build Status: {latest_build['status']}")
    else:
        print("No builds found.")

except requests.exceptions.RequestException as e:
    print(f"Failed to retrieve build info: {e}")

# def get_jenkins_build_status(job_name, jenkins_url='https://jenkins.solyticspartners.com', username='your-username', api_token='your-api-token'):
#     """
#     Get the status of the latest Jenkins build.

#     :param job_name: Name of the Jenkins job to check.
#     :param jenkins_url: Base URL of the Jenkins server.
#     :param username: Jenkins username.
#     :param api_token: Jenkins API token.
#     :return: The status of the latest build or None if unable to retrieve status.
#     """
#     wfapi_url = f"{jenkins_url}/job/{job_name}/wfapi/runs"
#     auth = (username, api_token)
    
#     try:
#         response = requests.get(wfapi_url, auth=auth)
#         response.raise_for_status()
#         build_info = response.json()

#         if build_info:
#             latest_build = build_info[0]  # Get the latest build
#             if latest_build['status'] is None and latest_build.get('building', False):
#                 return "In Progress"
#             else:
#                 return latest_build['status']
#         else:
#             return "No Builds Found"
#     except requests.exceptions.RequestException as e:
#         print(f"Failed to retrieve build info: {e}")
#         return None

# get_jenkins_build_status(JOB_NAME, 'https://jenkins.solyticspartners.com', USERNAME, API_TOKEN )