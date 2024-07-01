import json
import re

from aws_cdk import (
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

import config


def add_lambda_subscription(topic: sns.Topic, function):
    lambda_subscription = sns_subscriptions.LambdaSubscription(function)
    topic.add_subscription(lambda_subscription)

def add_email_subscription(topic: sns.Topic, email_list):
    for email in email_list:
        email_subscription = sns_subscriptions.EmailSubscription(email_address=email)
        topic.add_subscription(email_subscription)


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

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Define the Lambda function resource
        resources_monitor_function = self.create_lambda_resources_monitor()
        monitoring_alarm_function = self.create_lambda_monitoring_alarm()

        # Define Event Bridge Rule
        self.create_event_bridge_rule(
            resources_monitor_function,
            Duration.seconds(config.MONITOR_INTERVAL_SECONDS)
        )

        # Define the API Gateway resource
        self.create_test_api(resources_monitor_function)

        # S3 bucket
        self.create_s3_bucket(config.S3_BUCKET_NAME)

        # Create DynamoDB
        self.create_dynamo_database(config.DYNAMO_TABLE_NAME)

        # Create SNS topic
        sns_alarm_topic = self.create_sns_topic(config.SNS_TOPIC_NAME)
        add_lambda_subscription(sns_alarm_topic, monitoring_alarm_function)
        email_list = config.SUBSCRIPTION_EMAIL_LIST
        add_email_subscription(sns_alarm_topic, email_list)
        # Sample cdn output to test trigger sns topic
        self.create_test_cfn_output(sns_alarm_topic)

        # Custom CloudWatch dashboard
        dashboard = self.create_cloudwatch_dashboard()
        widgets = self.create_metric_widgets(sns_alarm_topic)
        dashboard.add_widgets(*widgets)


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


    def create_lambda_monitoring_alarm(self):
        monitoring_alarm_function = _lambda.Function(
            self,
            "MonitoringAlarmFunction",
            runtime = _lambda.Runtime.PYTHON_3_11,
            code = _lambda.Code.from_asset("canary_monitoring/lambda"),
            handler = "monitoring_alarm.lambda_handler",
            initial_policy=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        'dynamodb:PutItem*'
                    ],
                    resources=['*', ],
                )
            ]
        )

        return monitoring_alarm_function


    def create_event_bridge_rule(self, function, duration):
        monitoring_scheduled_rule = events.Rule(
            self,
            f'EventBridgeRule',
            schedule=events.Schedule.rate(duration),
            targets=[events_targets.LambdaFunction(handler=function,)],
            rule_name=f'MonitoringSchedule',
        )

        return monitoring_scheduled_rule


    def create_test_api(self, function):
        api = apigateway.LambdaRestApi(
            self,
            "Test Measuring Api",
            handler=function,
            proxy=False,
        )

        # Define the resource with a GET method
        test_handler = api.root.add_resource("monitor")
        test_handler.add_method("GET")

        return api

    
    def create_s3_bucket(self, name):
        bucket = s3.Bucket(
            self,
            id="canary_urls",
            bucket_name=name,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True
        )

        return bucket


    def create_dynamo_database(self, table_name):
        table = dynamodb.Table(
            self, "MonitoringAlarmDB",
            partition_key=dynamodb.Attribute(
                name="id",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="timestamp",
                type=dynamodb.AttributeType.STRING
            ),
            table_name=table_name,
            read_capacity=5,
            write_capacity=5,
            removal_policy=RemovalPolicy.DESTROY
        )

        return table
    
    
    def create_sns_topic(self, topic_name):
        sns_alarm_topic = sns.Topic(
            self,
            "SNSMonitoringAlarm",
            topic_name=topic_name
        )

        return sns_alarm_topic
    

    def create_test_cfn_output(self, topic: sns.Topic):
        CfnOutput(
            self,
            'snsTopicARN',
            value=topic.topic_arn,
            description='The SNS notification-topic ARN for test'
        )
    

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
