import json
import boto3
import uuid
import config

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
        'threshold': event_message_trigger['Threshold'],
        'metricValue': event_state_reason[event_state_reason.find("[") + 1:event_state_reason.find("[") + 5],
        'comparisonOperator': event_message_trigger['ComparisonOperator'],
        'reason': event_state_reason,
        'region': event_message_json['Region']
    }
    table = dynamodb_client.Table('MonitoringAlarm')
    table.put_item(Item=item)

def send_notification_email(message):
    ses = boto3.client('ses')
    alarm_name = message['AlarmName']
    aws_account_id = message['AWSAccountId']
    region = message['Region']
    threshold = message['Trigger']['Threshold']
    new_state_reason = message['NewStateReason']
    state_change_time_full = message['StateChangeTime']
    state_change_time = state_change_time_full.split(".", 1)[0]
    comparison_operator = message['Trigger']['ComparisonOperator']
    metric_current_value = new_state_reason[new_state_reason.find("[") + 1:new_state_reason.find("[") + 5]
    email_template = {
        "Type": "AWS::SES::Template",
        "Properties": {
            "Template": {
                "TemplateName": "TemplateCritical",
                "SubjectPart": "CRITICAL Alarm on {{alarm}}",
                "HtmlPart": "<h2><span style=\"color: #d13212;\">&#9888</span>Your Amazon CloudWatch alarm was triggered</h2><table style=\"height: 245px; width: 70%; border-collapse: collapse;\" border=\"1\" cellspacing=\"70\" cellpadding=\"5\"><tbody><tr style=\"height: 45px;\"><td style=\"width: 22.6262%; background-color: #f2f3f3; height: 45px;\"><span style=\"color: #16191f;\"><strong>Impact</strong></span></td><td style=\"width: 60.5228%; background-color: #ffffff; height: 45px;\"><strong><span style=\"color: #d13212;\">Critical</span></strong></td></tr><tr style=\"height: 45px;\"><td style=\"width: 22.6262%; height: 45px; background-color: #f2f3f3;\"><span style=\"color: #16191f;\"><strong>Alarm Name</strong></span></td><td style=\"width: 60.5228%; height: 45px;\">{{alarm}}</td></tr><tr style=\"height: 45px;\"><td style=\"width: 22.6262%; height: 45px; background-color: #f2f3f3;\"><span style=\"color: #16191f;\"><strong>Account</strong></span></td><td style=\"width: 60.5228%; height: 45px;\"><p>{{account}} {{region}})</p></td></tr><tr style=\"height: 45px;\"><td style=\"width: 22.6262%; background-color: #f2f3f3; height: 45px;\"><span style=\"color: #16191f;\"><strong>Date-Time</strong></span></td><td style=\"width: 60.5228%; height: 45px;\">{{datetime}}</td></tr><tr style=\"height: 45px;\"><td style=\"width: 22.6262%; height: 45px; background-color: #f2f3f3;\"><span style=\"color: #16191f;\"><strong>Reason</strong></span></td><td style=\"width: 60.5228%; height: 45px;\">Current value <strong> {{value}} </strong> is {{comparisonoperator}} <strong> {{threshold}} </strong> </td></tr></tbody></table>"
            }
        }
    }
    response = ses.send_templated_email(
        Destination={
            'ToAddresses': config.SUBSCRIPTION_EMAIL_LIST
        },
        Template=email_template,
        TemplateData='{ \"alarm\":\"' + alarm_name + '\", \"reason\": \"' + new_state_reason + '\", \"account\": \"' + aws_account_id + '\", \"region\": \"' + region + '\", \"datetime\": \"' + state_change_time + '\", \"value\": \"' + str(
            metric_current_value) + '\", \"comparisonoperator\": \"' + comparison_operator + '\", \"threshold\": \"' + str(
            threshold) + '\" }'
    )

def lambda_handler(event, context):
    event_message_str = event['Records'][0]['Sns']['Message']
    event_message_json = json.loads(str(event_message_str))
    save_alarm_message(event_message_json)
