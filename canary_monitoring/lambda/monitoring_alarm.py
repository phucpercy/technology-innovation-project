import json
import boto3
import uuid

dynamodb_client = boto3.resource("dynamodb")

def lambda_handler(event, context):
    event_message_str = event['Records'][0]['Sns']['Message']
    event_message_json = json.loads(str(event_message_str))
    print(event_message_json)

    item = {
        'id': str(uuid.uuid4()),
        'timestamp': event_message_json['AlarmConfigurationUpdatedTimestamp'],
        'alarmMessage': event_message_str
    }
    table = dynamodb_client.Table('MonitoringAlarm')
    table.put_item(Item=item)