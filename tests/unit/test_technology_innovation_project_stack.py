import pytest
import aws_cdk as core
from aws_cdk import Duration
from aws_cdk.assertions import Template, Match, Capture
from aws_cdk.aws_events import Schedule

from canary_monitoring.stack.canary_monitoring_stack import CanaryMonitoringStack

import config


@pytest.fixture(scope="session")
def stack_template():
    app = core.App()
    stack = CanaryMonitoringStack(app, "CanaryMonitoringStack")
    template = Template.from_stack(stack)
    return template


def test_lambda_monitoring(stack_template: Template):
    stack_template.has_resource_properties(
        "AWS::Lambda::Function",
        Match.object_like({
            "Handler": "resources_monitor.measuring_handler"
        })
    )


def test_lambda_alarm(stack_template: Template):
    stack_template.has_resource_properties(
        "AWS::Lambda::Function",
        Match.object_like({
            "Handler": "monitoring_alarm.lambda_handler"
        })
    )


def test_event_bridge_rule(stack_template: Template):
    stack_template.resource_count_is("AWS::Events::Rule", 1)
    schedule_expression = Schedule.rate(Duration.seconds(config.MONITOR_INTERVAL_SECONDS)).expression_string
    stack_template.has_resource_properties(
        "AWS::Events::Rule",
        Match.object_like({
            "ScheduleExpression": schedule_expression,
            "State": "ENABLED"
        })
    )


def test_s3_bucket(stack_template: Template):
    stack_template.resource_count_is("AWS::S3::Bucket", 1)
    stack_template.has_resource(
        "AWS::S3::Bucket",
        Match.object_like({
            "Properties": {
                "BucketName": config.S3_BUCKET_NAME
            },
            "UpdateReplacePolicy": "Delete",
            "DeletionPolicy": "Delete"
        })
    )


def test_dynamodb_table(stack_template: Template):
    stack_template.resource_count_is("AWS::DynamoDB::Table", 1)
    stack_template.has_resource_properties(
        "AWS::DynamoDB::Table",
        Match.object_like({
            "AttributeDefinitions": [
                {
                    "AttributeName": "id",
                    "AttributeType": "S"
                },
                {
                    "AttributeName": "timestamp",
                    "AttributeType": "S"
                }
            ],
            "TableName": config.DYNAMO_TABLE_NAME
        })
    )
    stack_template.has_resource(
        "AWS::DynamoDB::Table",
        Match.object_like({
            "UpdateReplacePolicy": "Delete",
            "DeletionPolicy": "Delete"
        })
    )


def test_sns_topic(stack_template: Template):
    stack_template.resource_count_is("AWS::SNS::Topic", 1)
    stack_template.has_resource_properties(
        "AWS::SNS::Topic",
        Match.object_like({
            "TopicName": config.SNS_TOPIC_NAME
        })
    )


def test_sns_topic_email_subscription(stack_template: Template):
    for email in config.SUBSCRIPTION_EMAIL_LIST:
        stack_template.has_resource_properties(
            "AWS::SNS::Subscription",
            Match.object_like({
                "Endpoint": email,
                "Protocol": "email"
            })
        )
    email_subscriptions = stack_template.find_resources(
        "AWS::SNS::Subscription",
        Match.object_like({
            "Properties": {
                "Protocol": "email"
            }
        })
    )
    assert len(email_subscriptions) == len(config.SUBSCRIPTION_EMAIL_LIST)


def test_sns_topic_lambda_subscription(stack_template: Template):
    sep_capture = Capture()
    body_capture = Capture()
    stack_template.has_resource_properties(
        "AWS::CloudWatch::Dashboard",
        Match.object_like({
            "DashboardBody": {
                "Fn::Join": [sep_capture, body_capture]
            }
        })
    )
    body_json = sep_capture.as_string().join(peice for peice in body_capture.as_array() if isinstance(peice, str))
    assert "" == body_json

