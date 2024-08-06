import os
import json

import boto3
import urllib3


TEST_URL = "https://www.python.org/"

TEST_URLS_JSON = '''{
  "urls": [
    {
      "url": "___URL___",
      "name": "Welcome to Python.org",
      "metrics": [
        {"type": "Availability", "threshold": "<1"},
        {"type": "Page Time", "threshold": ">=1"},
        {"type": "Page Size", "threshold": ">1"}
      ]
    }
  ]
}
'''.replace("___URL___", TEST_URL)


def get_resource_url():
    apigateway = boto3.client("apigatewayv2")
    response = apigateway.get_apis()
    filtered_endpoint = [item['ApiEndpoint'] for item in response['Items'] if item['Name'] == 'ResourcesManagementApi']
    base_url = filtered_endpoint[0]

    return os.path.join(base_url, "resources")


def put_urls(url, json_str):
    response = urllib3.request("PUT", url, json=json.loads(json_str))
    assert response.status == 200


def invoke_monitor_lambda(func_name):
    client = boto3.client("lambda")
    response = client.list_functions(MaxItems=10)
    filtered_func_names = [item['FunctionName'] for item in response['Functions'] if func_name in item['FunctionName']]
    response = client.invoke(
        FunctionName=filtered_func_names[0],
        InvocationType="RequestResponse"
    )
    assert response["StatusCode"] == 200


def get_alarms():
    cloudwatch = boto3.client('cloudwatch')
    stage_name = os.environ['STAGE_NAME']
    metrics_namespace = os.environ['METRICS_NAMESPACE']
    alarm_prefix = f"{stage_name}{metrics_namespace}-Alarm-"
    response = cloudwatch.describe_alarms(
        AlarmNamePrefix=alarm_prefix
    )
    alarms = response['MetricAlarms']

    return alarms


def test_alarms():
    url = get_resource_url()
    put_urls(url, TEST_URLS_JSON)
    invoke_monitor_lambda('MonitoringFunction')
    alarms = get_alarms()
    assert len(alarms) == 3
    for alarm in alarms:
        assert TEST_URL in alarm['AlarmName']
        assert alarm['ActionsEnabled']
