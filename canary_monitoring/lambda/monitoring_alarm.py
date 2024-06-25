import json
import boto3
import uuid

dynamodb_client = boto3.resource("dynamodb")

def lambda_handler(event, context):
    event_string = json.dumps(event)
    event_json = json.loads(event_string)
    event_message_str = event_json['Records']['Sns']['Message']
    event_message_json = json.loads(event_message_str)

    item = {
        'id': str(uuid.uuid4()),
        'timestamp': event_message_json['AlarmConfigurationUpdatedTimestamp'],
        'alarmMessage': event_message_json
    }
    table = dynamodb_client.Table('MonitoringAlarm')
    table.put_item(Item=item)