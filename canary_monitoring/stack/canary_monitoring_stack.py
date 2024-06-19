import json

from aws_cdk import (
    Stack,
    Duration,
    aws_cloudwatch as cw,
    aws_cloudwatch_actions as actions,
    aws_lambda as _lambda,
    aws_apigateway as apigateway,
    aws_s3 as s3, RemovalPolicy,
    aws_iam as iam,
    aws_events as events,
    aws_dynamodb as dynamodb,
    aws_sns as sns,
    aws_sns_subscriptions as sns_subscriptions,
    aws_events_targets as events_targets,
    Duration, Stack, CfnOutput
)
from aws_cdk.aws_cloudwatch import TextWidget, GraphWidget
from constructs import Construct


class CanaryMonitoringStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # The code that defines your stack goes here

        # Define the Lambda function resource
        monitoring_function = _lambda.Function(
            self,
            "MonitoringFunction",
            runtime = _lambda.Runtime.PYTHON_3_11, # Choose any supported Python runtime
            code = _lambda.Code.from_asset("canary_monitoring/lambda"), # Points to the lambda directory
            handler = "resources_monitor.measuring_handler",
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
                    resources=[
                        '*',
                    ],
                )
            ]
        )

        monitoring_alarm_function = _lambda.Function(
            self,
            "MonitoringAlarmFunction",
            runtime = _lambda.Runtime.PYTHON_3_11, # Choose any supported Python runtime
            code = _lambda.Code.from_asset("canary_monitoring/lambda"), # Points to the lambda directory
            handler = "monitoring_alarm.lambda_handler",
        )

        # Define Event Bridge Rule
        monitoring_scheduled_rule = events.Rule(
            self,
            f'EventBridgeRule',
            schedule=events.Schedule.rate(Duration.minutes(1)),
            targets=[events_targets.LambdaFunction(handler=monitoring_function,)],
            rule_name=f'MonitoringSchedule',
        )

        # Define the API Gateway resource
        api = apigateway.LambdaRestApi(
            self,
            "Test Measuring Api",
            handler = monitoring_function,
            proxy = False,
        )

        # Define the '/test' resource with a GET method
        test_handler = api.root.add_resource("monitor")
        test_handler.add_method("GET")

        # S3 bucket
        s3.Bucket(
            self,
            id="canary_urls",
            bucket_name="tip-monitoring-url-resources",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True
        )

        # Create DynamoDB
        dynamodb.Table(
            self, "MonitoringAlarmDB",
            partition_key=dynamodb.Attribute(
                name="id",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="timestamp",
                type=dynamodb.AttributeType.STRING
            ),
            table_name="MonitoringAlarm",
            read_capacity=5,
            write_capacity=5,
            removal_policy=RemovalPolicy.DESTROY
        )

        # Create SNS topic
        sns_alarm_topic = sns.Topic(
            self,
            "SNSMonitoringAlarm",
            topic_name="MonitoringAbnormal"
        )
        lambda_subscription = sns_subscriptions.LambdaSubscription(
            monitoring_alarm_function
        )
        sns_alarm_topic.add_subscription(
            lambda_subscription
        )
        # Sample cdn output to test trigger sns topic
        CfnOutput(
            self,
            'snsTopicARN',
            value=sns_alarm_topic.topic_arn,
            description='The SNS notification-topic ARN for test'
        )

        # Custom CloudWatch dashboard
        dashboard = cw.Dashboard(self, "Web Monitor Dashboard")
        dashboard.add_widgets(
            TextWidget(
                markdown = '# Web Monitor Dashboard',
                width = 24,
                height = 2
            )
        )
        widgets = self.create_metric_widgets(sns_alarm_topic)
        dashboard.add_widgets(*widgets)

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
            for metric_name in url_conf['metricNames']:
                metric = cw.Metric(
                    metric_name = metric_name,
                    namespace = 'Monitor',
                    dimensions_map= {'URL': url_conf['url']},
                    period=Duration.minutes(1),
                )
                if metric_name == 'Page Time':
                    alarm: cw.Alarm = metric.create_alarm(
                        self,
                        f'Alarm-{metric_name}-{url_conf["url"]}',
                        threshold=0.5,
                        evaluation_periods=2,
                        datapoints_to_alarm=1,
                        comparison_operator=cw.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD
                    )
                    alarm.add_alarm_action(actions.SnsAction(topic))
                widgets.append(GraphWidget(
                    left = [metric],
                    width = 6,
                    height = 4,
                ))

        return widgets