import requests

def trigger_jenkins_build(job_name, params=None, jenkins_url='https://jenkins.solyticspartners.com', username='your-username', api_token='your-api-token'):
    """
    Trigger a Jenkins job build with specified parameters.

    :param job_name: Name of the Jenkins job to build.
    :param params: Dictionary of parameters to pass to the job (optional).
    :param jenkins_url: Base URL of the Jenkins server.
    :param username: Jenkins username.
    :param api_token: Jenkins API token.
    :return: Response object from the POST request.
    """
    build_url = f"{jenkins_url}/job/{job_name}/buildWithParameters"
    auth = (username, api_token)
    
    try:
        response = requests.post(build_url, auth=auth, params=params if params else {})
        response.raise_for_status()  # Raise an exception for HTTP errors
        return response
    except requests.exceptions.RequestException as e:
        print(f"Failed to trigger build: {e}")
        return None