import json
import re

from aws_cdk import (
    aws_cloudwatch as cw,
    aws_cloudwatch_actions as actions,
    aws_lambda as _lambda,
    aws_apigatewayv2 as apigateway,
    aws_apigatewayv2_integrations as integrations,
    aws_s3 as s3, RemovalPolicy,
    aws_iam as iam,
    aws_events as events,
    aws_dynamodb as dynamodb,
    aws_sns as sns,
    aws_sns_subscriptions as sns_subscriptions,
    aws_events_targets as events_targets,
    aws_ses as ses,
    Duration, Stack, CfnOutput
)
from aws_cdk.aws_apigatewayv2 import HttpMethod
from aws_cdk.aws_cloudwatch import TextWidget, GraphWidget
from constructs import Construct

import config


def add_lambda_subscription(topic: sns.Topic, function):
    lambda_subscription = sns_subscriptions.LambdaSubscription(function)
    topic.add_subscription(lambda_subscription)

def parse_threshold_expression(express: str):
    if len(express) == 0:
        return []

    op_map = {
        "<": cw.ComparisonOperator.LESS_THAN_THRESHOLD,
        ">": cw.ComparisonOperator.GREATER_THAN_THRESHOLD,
        "<=": cw.ComparisonOperator.LESS_THAN_OR_EQUAL_TO_THRESHOLD,
        ">=": cw.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
    }

    exps = express.split(',')
    thresholds = []
    for exp in exps:
        exp = exp.strip()
        regex = re.compile(r"[><]=?")
        m = regex.match(exp)
        if m is None:
            raise RuntimeError(f"'{express}' is not a valid threshold expression.")
        compare_op = m.group(0)
        threshold = float(exp[len(compare_op):])
        op = op_map[compare_op]
        thresholds.append((op, threshold))

    return thresholds


class CanaryMonitoringStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, stage_name: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Define the Lambda function resource
        resources_monitor_function = self.create_lambda_resources_monitor()
        monitoring_alarm_function = self.create_lambda_monitoring_alarm(stage_name)
        resources_management_function = self.create_lambda_resources_management(stage_name)
        self.create_resources_management_gateway(resources_management_function)

        # Define Event Bridge Rule
        self.create_event_bridge_rule(
            resources_monitor_function,
            Duration.seconds(config.MONITOR_INTERVAL_SECONDS),
            stage_name
        )

        # S3 bucket
        # self.create_s3_bucket(config.S3_BUCKET_NAME)

        # Create DynamoDB
        self.create_dynamo_database(config.DYNAMO_ALARM_TABLE_NAME, config.DYNAMO_RESOURCES_TABLE_NAME, stage_name)

        # Create SNS topic
        sns_alarm_topic = self.create_sns_topic(config.SNS_TOPIC_NAME, stage_name)
        add_lambda_subscription(sns_alarm_topic, monitoring_alarm_function)

        # Create SES stack
        self.create_ses_stack(stage_name)

        # Custom CloudWatch dashboard
        dashboard = self.create_cloudwatch_dashboard()
        widgets = self.create_metric_widgets(sns_alarm_topic)
        dashboard.add_widgets(*widgets)


    def create_lambda_resources_management(self, stage_name):
        resources_management = _lambda.Function(
            self,
            "ResourcesManagementFunction",
            runtime = _lambda.Runtime.PYTHON_3_11,
            code = _lambda.Code.from_asset("canary_monitoring/lambda"),
            handler = "resources_management.lambda_handler",
            environment={
                "DYNAMO_RESOURCES_TABLE_NAME": stage_name + config.DYNAMO_RESOURCES_TABLE_NAME,
            },
            timeout=Duration.seconds(config.MONITOR_LAMBDA_TIMEOUT_SECONDS),
            initial_policy=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        'dynamodb:*',
                    ],
                    resources=['*',],
                )
            ]
        )

        return resources_management

    def create_lambda_resources_monitor(self):
        monitoring_function = _lambda.Function(
            self,
            "MonitoringFunction",
            runtime = _lambda.Runtime.PYTHON_3_11,
            code = _lambda.Code.from_asset("canary_monitoring/lambda"),
            handler = "resources_monitor.measuring_handler",
            environment={
                "S3_BUCKET_NAME": config.S3_BUCKET_NAME,
                "URL_FILE_NAME": config.URL_FILE_NAME,
                "METRICS_NAMESPACE": config.METRICS_NAMESPACE,
            },
            timeout=Duration.seconds(config.MONITOR_LAMBDA_TIMEOUT_SECONDS),
            initial_policy=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        'cloudwatch:PutMetricData',
                        's3:Get*',
                        's3:List*',
                        's3:Describe*',
                        's3-object-lambda:Get*',
                        's3-object-lambda:List*'
                    ],
                    resources=['*',],
                )
            ]
        )

        return monitoring_function


    def create_lambda_monitoring_alarm(self, stage_name):
        monitoring_alarm_function = _lambda.Function(
            self,
            "MonitoringAlarmFunction",
            runtime = _lambda.Runtime.PYTHON_3_11,
            code = _lambda.Code.from_asset("canary_monitoring/lambda"),
            handler = "monitoring_alarm.lambda_handler",
            environment={
                "SUBSCRIPTION_EMAIL_LIST": ",".join(config.SUBSCRIPTION_EMAIL_LIST),
                "DYNAMO_ALARM_TABLE_NAME": stage_name + config.DYNAMO_ALARM_TABLE_NAME
            },
            initial_policy=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        'dynamodb:PutItem*',
                        'ses:SendTemplatedEmail'
                    ],
                    resources=['*', ],
                )
            ]
        )

        return monitoring_alarm_function


    def create_event_bridge_rule(self, function, duration, stage_name):
        monitoring_scheduled_rule = events.Rule(
            self,
            f'{stage_name}EventBridgeRule',
            schedule=events.Schedule.rate(duration),
            targets=[events_targets.LambdaFunction(handler=function,)],
            rule_name=f'MonitoringSchedule',
        )

        return monitoring_scheduled_rule


    def create_dynamo_database(self, alarm_table_name, resources_table_name, stage_name):
        dynamodb.Table(
            self, f'{stage_name}MonitoringAlarmDB',
            partition_key=dynamodb.Attribute(
                name="id",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="timestamp",
                type=dynamodb.AttributeType.STRING
            ),
            table_name=stage_name + alarm_table_name,
            read_capacity=5,
            write_capacity=5,
            removal_policy=RemovalPolicy.DESTROY
        )
        dynamodb.Table(
            self, f'{stage_name}MonitoringResourcesDB',
            partition_key=dynamodb.Attribute(
                name="id",
                type=dynamodb.AttributeType.STRING
            ),
            table_name=stage_name + resources_table_name,
            read_capacity=5,
            write_capacity=5,
            removal_policy=RemovalPolicy.DESTROY
        )

    
    def create_sns_topic(self, topic_name, stage_name):
        sns_alarm_topic = sns.Topic(
            self,
            f'{stage_name}SNSMonitoringAlarm',
            topic_name=stage_name + topic_name
        )

        return sns_alarm_topic
    
    def create_cloudwatch_dashboard(self):
        dashboard = cw.Dashboard(self, "Web Monitor Dashboard")
        dashboard.add_widgets(
            TextWidget(
                markdown = '# Web Monitor Dashboard',
                width = 24,
                height = 2
            )
        )

        return dashboard


    def create_metric_widgets(self, topic: sns.Topic):
        with open('canary_monitoring/urls.json', 'r') as fr:
            data = json.load(fr)

        widgets = []
        for url_conf in data['urls']:
            widgets.append(TextWidget(
                markdown = f'## {url_conf["name"]}',
                width = 24,
                height = 1
            ))
            for metric_conf in url_conf['metrics']:
                metric_type = metric_conf['type']
                metric = cw.Metric(
                    metric_name = metric_type,
                    namespace = config.METRICS_NAMESPACE,
                    dimensions_map= {'URL': url_conf['url']},
                    period=Duration.minutes(1),
                )
                threshold_exp = metric_conf['threshold']
                thresholds = parse_threshold_expression(threshold_exp)
                for i, (op, threshold) in enumerate(thresholds):
                    alarm: cw.Alarm = metric.create_alarm(
                        self,
                        f'Alarm-{metric_type}-{url_conf["url"]}-{i}',
                        threshold=threshold,
                        evaluation_periods=1,
                        datapoints_to_alarm=1,
                        comparison_operator=op
                    )
                    alarm.add_alarm_action(actions.SnsAction(topic))
                widgets.append(GraphWidget(
                    left = [metric],
                    width = 6,
                    height = 4,
                ))

        return widgets

    def create_ses_stack(self, stage_name):
        ses.CfnTemplate(
            self,
            f'{stage_name}AlarmNotificationEmailTemplate',
            template=ses.CfnTemplate.TemplateProperty(
                template_name=f'{stage_name}AlarmNotificationTemplate',
                subject_part='CRITICAL Alarm on {{alarm}}',
                html_part=f'<h2>Your {stage_name} Amazon CloudWatch alarm was triggered</h2><table style=\"height: 245px; width: 70%; border-collapse: collapse;\" border=\"1\" cellspacing=\"70\" cellpadding=\"5\"><tbody><tr style=\"height: 45px;\"><td style=\"width: 22.6262%; background-color: #f2f3f3; height: 45px;\"><span style=\"color: #16191f;\"><strong>Impact</strong></span></td><td style=\"width: 60.5228%; background-color: #ffffff; height: 45px;\"><strong><span style=\"color: #d13212;\">Critical</span></strong></td></tr><tr style=\"height: 45px;\"><td style=\"width: 22.6262%; height: 45px; background-color: #f2f3f3;\"><span style=\"color: #16191f;\"><strong>Alarm Name</strong></span></td><td style=\"width: 60.5228%; height: 45px;\">{{alarm}}</td></tr><tr style=\"height: 45px;\"><td style=\"width: 22.6262%; height: 45px; background-color: #f2f3f3;\"><span style=\"color: #16191f;\"><strong>Account</strong></span></td><td style=\"width: 60.5228%; height: 45px;\"><p>{{account}} {{region}})</p></td></tr><tr style=\"height: 45px;\"><td style=\"width: 22.6262%; background-color: #f2f3f3; height: 45px;\"><span style=\"color: #16191f;\"><strong>Date-Time</strong></span></td><td style=\"width: 60.5228%; height: 45px;\">{{datetime}}</td></tr><tr style=\"height: 45px;\"><td style=\"width: 22.6262%; height: 45px; background-color: #f2f3f3;\"><span style=\"color: #16191f;\"><strong>Reason</strong></span></td><td style=\"width: 60.5228%; height: 45px;\">Current value <strong> {{value}} </strong> is {{comparisonoperator}} <strong> {{threshold}} </strong> </td></tr></tbody></table>'
            )
        )

    def create_resources_management_gateway(self, resources_management_function):
        api = apigateway.HttpApi(
            self,
            "ResourcesManagementApi",
            api_name="ResourcesManagementApi"
        )
        api.add_routes(
            path='/resources',
            methods=[HttpMethod.GET, HttpMethod.PUT],
            integration=integrations.HttpLambdaIntegration(
                "ResourcesManagementLambda",
                handler=resources_management_function
            )
        )
        api.add_routes(
            path='/resources/{id}',
            methods=[HttpMethod.GET, HttpMethod.DELETE],
            integration=integrations.HttpLambdaIntegration(
                "ResourcesManagementLambda",
                handler=resources_management_function
            )
        )
