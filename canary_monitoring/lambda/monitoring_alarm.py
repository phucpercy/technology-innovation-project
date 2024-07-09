import json
import boto3
import uuid
import os

from botocore.exceptions import ClientError


def save_alarm_message(event_message_json):
    dynamodb_client = boto3.resource("dynamodb")
    event_message_trigger = event_message_json['Trigger']
    event_state_reason = event_message_json['NewStateReason']
    dynamodb_table_name = os.environ["DYNAMO_TABLE_NAME"]
    item = {
        'id': str(uuid.uuid4()),
        'timestamp': event_message_json['AlarmConfigurationUpdatedTimestamp'],
        'alarmName': event_message_json['AlarmName'],
        'metricName': event_message_trigger['MetricName'],
        'webURL': event_message_trigger['Dimensions'][0]['value'],
        'threshold': str(event_message_trigger['Threshold']),
        'metricValue': str(event_state_reason[event_state_reason.find("[") + 1:event_state_reason.find("[") + 5]),
        'comparisonOperator': event_message_trigger['ComparisonOperator'],
        'reason': event_state_reason,
        'region': event_message_json['Region']
    }
    table = dynamodb_client.Table(dynamodb_table_name)
    table.put_item(Item=item)

def send_notification_email(event_message_json):
    ses = boto3.client('ses')
    alarm_name = event_message_json['AlarmName']
    aws_account_id = event_message_json['AWSAccountId']
    region = event_message_json['Region']
    threshold = event_message_json['Trigger']['Threshold']
    new_state_reason = event_message_json['NewStateReason']
    state_change_time_full = event_message_json['StateChangeTime']
    state_change_time = state_change_time_full.split(".", 1)[0]
    comparison_operator = event_message_json['Trigger']['ComparisonOperator']
    metric_current_value = new_state_reason[new_state_reason.find("[") + 1:new_state_reason.find("[") + 5]
    email_addresses = os.environ["SUBSCRIPTION_EMAIL_LIST"]

    template_data = {
        'alarm': alarm_name,
        'reason': new_state_reason,
        'account': aws_account_id,
        'region': region,
        'datetime': state_change_time,
        'value': str(metric_current_value),
        'comparisonoperator': comparison_operator,
        'threshold': str(threshold)

    }

    try:
        response = ses.send_templated_email(
            Source='xmanphuc@gmail.com',
            Destination={
                'ToAddresses': email_addresses
            },
            Template='AlarmNotificationTemplate',
            TemplateData=json.dumps(template_data)
        )
        message_id = response["MessageId"]
        print("Sent templated mail.")
    except ClientError as e:
        print(f'Couldn\'t send templated mail: {e}')

def lambda_handler(event, context):
    event_message_str = event['Records'][0]['Sns']['Message']
    event_message_json = json.loads(str(event_message_str))
    save_alarm_message(event_message_json)
    send_notification_email(event_message_json)
