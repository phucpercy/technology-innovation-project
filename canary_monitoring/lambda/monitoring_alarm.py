import json
import boto3
import uuid

def save_alarm_message(event_message_json):
    dynamodb_client = boto3.resource("dynamodb")
    event_message_trigger = event_message_json['Trigger']
    event_state_reason = event_message_json['NewStateReason']
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
    table = dynamodb_client.Table('MonitoringAlarm')
    table.put_item(Item=item)

def lambda_handler(event, context):
    event_message_str = event['Records'][0]['Sns']['Message']
    event_message_json = json.loads(str(event_message_str))
    save_alarm_message(event_message_json)
