import json

from aws_cdk import (
    Stack,
    aws_cloudwatch as cw,
    aws_lambda as _lambda,
    aws_apigateway as apigateway,
    aws_s3 as s3, RemovalPolicy,
    aws_iam as iam,
    aws_events as events,
    aws_events_targets as events_targets, Duration
)
from aws_cdk.aws_cloudwatch import TextWidget, GraphWidget
from constructs import Construct


def create_metric_widgets():
    with open('canary_monitoring/urls.json', 'r') as fr:
        data = json.load(fr)
    
    widgets = []
    for url_conf in data['urls']:
        widgets.append(TextWidget(
            markdown = f'## {url_conf["name"]}',
            width = 24,
            height = 1
        ))
        for metric in url_conf['metricNames']:
            widgets.append(GraphWidget(
                left = [cw.Metric(
                    metric_name = metric,
                    namespace = 'Monitor',
                    dimensions_map= {'URL': url_conf['url']},
                )],
                width = 6,
                height = 4,
            ))
    return widgets


class CanaryMonitoringStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # The code that defines your stack goes here

        # Custom CloudWatch dashboard
        dashboard = cw.Dashboard(self, "Web Monitor Dashboard")
        dashboard.add_widgets(
            TextWidget(
                markdown = '# Web Monitor Dashboard',
                width = 24,
                height = 2
            )
        )
        widgets = create_metric_widgets()
        dashboard.add_widgets(*widgets)

        # Define the Lambda function resource
        monitoring_function = _lambda.Function(
            self,
            "MonitoringFunction",
            runtime = _lambda.Runtime.PYTHON_3_11, # Choose any supported Python runtime
            code = _lambda.Code.from_asset("canary_monitoring/lambda"), # Points to the lambda directory
            handler = "resources_monitor.measuring_handler",
        )

        monitoring_function.add_to_role_policy(iam.PolicyStatement(
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
        ))

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
            removal_policy=RemovalPolicy.DESTROY
        )
