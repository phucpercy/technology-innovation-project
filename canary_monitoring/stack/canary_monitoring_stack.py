from aws_cdk import (
    aws_cloudwatch as cw,
    aws_lambda as _lambda,
    aws_apigatewayv2 as apigateway,
    aws_apigatewayv2_integrations as integrations,
    aws_s3 as RemovalPolicy,
    aws_iam as iam,
    aws_events as events,
    aws_dynamodb as dynamodb,
    aws_sns as sns,
    aws_sns_subscriptions as sns_subscriptions,
    aws_events_targets as events_targets,
    aws_ses as ses,
    Duration, Stack, RemovalPolicy
)
from aws_cdk.aws_apigatewayv2 import HttpMethod
from constructs import Construct

import config


def add_lambda_subscription(topic: sns.Topic, function):
    lambda_subscription = sns_subscriptions.LambdaSubscription(function)
    topic.add_subscription(lambda_subscription)


class CanaryMonitoringStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, stage_name: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create SNS topic
        sns_alarm_topic = self.create_sns_topic(config.SNS_TOPIC_NAME, stage_name)

        # Define the Lambda function resource
        resources_monitor_function = self.create_lambda_resources_monitor(sns_alarm_topic, stage_name)
        monitoring_alarm_function = self.create_lambda_monitoring_alarm(stage_name)
        add_lambda_subscription(sns_alarm_topic, monitoring_alarm_function)
        resources_management_function = self.create_lambda_resources_management(stage_name)
        self.create_resources_management_gateway(resources_management_function)

        # Define Event Bridge Rule
        self.create_event_bridge_rule(
            resources_monitor_function,
            Duration.seconds(config.MONITOR_INTERVAL_SECONDS),
            stage_name
        )

        # Create DynamoDB
        self.create_dynamo_database(config.DYNAMO_ALARM_TABLE_NAME, config.DYNAMO_RESOURCES_TABLE_NAME, stage_name)

        # Create SES stack
        self.create_ses_stack(stage_name)

        # Custom CloudWatch dashboard
        self.create_cloudwatch_dashboard()


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


    def create_lambda_resources_monitor(self, topic: sns.Topic, stage_name):
        monitoring_function = _lambda.Function(
            self,
            "MonitoringFunction",
            runtime = _lambda.Runtime.PYTHON_3_11,
            code = _lambda.Code.from_asset("canary_monitoring/lambda"),
            handler = "resources_monitor.measuring_handler",
            environment={
                "ALARM_PREFIX": f"{stage_name}{config.METRICS_NAMESPACE}-Alarm-",
                "DYNAMO_RESOURCES_TABLE_NAME": stage_name + config.DYNAMO_RESOURCES_TABLE_NAME,
                "METRICS_NAMESPACE": config.METRICS_NAMESPACE,
                "CLOUDWATCH_DASHBOARD_NAME": config.CLOUDWATCH_DASHBOARD_NAME,
                "MONITOR_INTERVAL_SECONDS": str(config.MONITOR_INTERVAL_SECONDS),
                "TOPIC_ARN": topic.topic_arn
            },
            timeout=Duration.seconds(config.MONITOR_LAMBDA_TIMEOUT_SECONDS),
            initial_policy=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        'cloudwatch:PutMetricData',
                        'cloudwatch:PutDashboard',
                        'cloudwatch:PutMetricAlarm',
                        'cloudwatch:DescribeAlarms',
                        'cloudwatch:DeleteAlarms',
                        'dynamodb:Scan'
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
                "SENDER_EMAIL": config.SENDER_EMAIL,
                "EMAIL_TEMPLATE_NAME": f'{stage_name}AlarmNotificationTemplate',
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
            sort_key=dynamodb.Attribute(
                name="reversed_ts",
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
        dashboard = cw.Dashboard(self, config.CLOUDWATCH_DASHBOARD_NAME, dashboard_name=config.CLOUDWATCH_DASHBOARD_NAME)
        return dashboard


    def create_ses_stack(self, stage_name):
        ses.CfnTemplate(
            self,
            f'{stage_name}AlarmNotificationEmailTemplate',
            template=ses.CfnTemplate.TemplateProperty(
                template_name=f'{stage_name}AlarmNotificationTemplate',
                subject_part='CRITICAL Alarm on {{alarm}}',
                html_part=f'<h2>Your {stage_name} Amazon CloudWatch alarm was triggered</h2>' + \
                    '''<table style="height: 245px; width: 70%; border-collapse: collapse;" border="1" cellspacing="70" 
                    cellpadding="5"><tbody><tr style="height: 45px;"><td style="width: 22.6262%; background-color: #f2f3f3; 
                    height: 45px;"><span style="color: #16191f;"><strong>Impact</strong></span></td><td style="width: 60.5228%; 
                    background-color: #ffffff; height: 45px;"><strong><span style="color: #d13212;">Critical</span></strong>
                    </td></tr><tr style="height: 45px;"><td style="width: 22.6262%; height: 45px; background-color: #f2f3f3;">
                    <span style="color: #16191f;"><strong>Alarm Name</strong></span></td><td style="width: 60.5228%; height: 45px;">
                    {{alarm}}</td></tr><tr style="height: 45px;"><td style="width: 22.6262%; height: 45px; background-color: #f2f3f3;">
                    <span style="color: #16191f;"><strong>Account</strong></span></td><td style="width: 60.5228%; height: 45px;">
                    <p>{{account}} {{region}})</p></td></tr><tr style="height: 45px;"><td style="width: 22.6262%; 
                    background-color: #f2f3f3; height: 45px;"><span style="color: #16191f;"><strong>Date-Time</strong></span></td>
                    <td style="width: 60.5228%; height: 45px;">{{datetime}}</td></tr><tr style="height: 45px;">
                    <td style="width: 22.6262%; height: 45px; background-color: #f2f3f3;"><span style="color: #16191f;">
                    <strong>Reason</strong></span></td><td style="width: 60.5228%; height: 45px;">Current value <strong> 
                    {{value}} </strong> is {{comparisonoperator}} <strong> {{threshold}} </strong> </td></tr></tbody></table>'''
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
