import json
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
    stack = CanaryMonitoringStack(app, "CanaryMonitoringStack", "Gamma")
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


def test_dynamodb_table(stack_template: Template):
    stack_template.resource_count_is("AWS::DynamoDB::Table", 2)
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
            "TableName": "Gamma" + config.DYNAMO_ALARM_TABLE_NAME
        })
    )
    stack_template.has_resource_properties(
        "AWS::DynamoDB::Table",
        Match.object_like({
            "AttributeDefinitions": [
                {
                    "AttributeName": "id",
                    "AttributeType": "S"
                },
                {
                    "AttributeName": "reversed_ts",
                    "AttributeType": "S"
                }
            ],
            "TableName": "Gamma" + config.DYNAMO_RESOURCES_TABLE_NAME
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
            "TopicName": 'Gamma' + config.SNS_TOPIC_NAME
        })
    )


def test_email_template(stack_template: Template):
    stack_template.has_resource_properties(
        "AWS::SES::Template",
        Match.object_like({
            "Template": Match.any_value()
        })
    )


def test_sns_topic_lambda_subscription(stack_template: Template):
    stack_template.has_resource_properties(
        "AWS::SNS::Subscription",
        Match.object_like({
            "Protocol": "lambda"
        })
    )
