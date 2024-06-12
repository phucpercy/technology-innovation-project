import boto3
from aws_cdk import (
    Stack,
    aws_cloudwatch as cw,
    aws_lambda as _lambda,
    aws_apigateway as apigateway,
    aws_s3 as s3, RemovalPolicy,
)
from aws_cdk.aws_cloudwatch import TextWidget, SingleValueWidget
from constructs import Construct


class CanaryMonitoringStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # The code that defines your stack goes here

        # CloudWatch custom dashboard and metrics
        # dashboard = cw.Dashboard(self, "Web Monitor Dashboard")
        # dashboard.add_widgets(
        #     TextWidget(
        #         markdown = 'Web Monitor Dashboard',
        #         width = 24,
        #         height = 2
        #     )
        # )
        # dashboard.add_widgets(
        #     SingleValueWidget(
        #         metrics = [cw.Metric(
        #             metric_name = 'Test Metric',
        #             namespace = 'Monitor',
        #         )],
        #         width = 6,
        #         height = 3,
        #     )
        # )
        #
        # metric_data = 6
        # metric = {
        #     'MetricName': 'Test Metric',
        #     'Unit': 'None',
        #     'Value': metric_data
        # }
        #
        # cloudwatch = boto3.client('cloudwatch', 'ap-southeast-2')
        # cloudwatch.put_metric_data(
        #     Namespace='Monitor',
        #     MetricData=[metric]
        # )

        # Define the Lambda function resource
        monitoring_handler = _lambda.Function(
            self,
            "MonitoringFunction",
            runtime = _lambda.Runtime.PYTHON_3_11, # Choose any supported Python runtime
            code = _lambda.Code.from_asset("canary_monitoring/lambda"), # Points to the lambda directory
            handler = "resources_monitor.measuring_handler", # Points to the 'helloworld' file in the lambda directory
        )

        # Define the API Gateway resource
        api = apigateway.LambdaRestApi(
            self,
            "Test Measuring Api",
            handler = monitoring_handler,
            proxy = False,
        )

        # Define the '/test' resource with a GET method
        test_handler = api.root.add_resource("test")
        test_handler.add_method("GET")

        # S3 bucket
        s3.Bucket(
            self,
            id="canary_urls",
            bucket_name="tip-monitoring-url-resources",
            removal_policy=RemovalPolicy.DESTROY
        )
