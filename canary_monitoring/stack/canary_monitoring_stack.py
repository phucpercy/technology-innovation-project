import boto3
from aws_cdk import (
    Stack,
    aws_cloudwatch as cw,
    aws_lambda as _lambda,
    aws_apigateway as apigateway,
    aws_s3 as s3, RemovalPolicy,
    aws_iam as iam
)
from aws_cdk.aws_cloudwatch import TextWidget, GraphWidget
from constructs import Construct


class CanaryMonitoringStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # The code that defines your stack goes here

        # Custom CloudWatch dashboard
        dashboard = cw.Dashboard(self, "Web Monitor Dashboard")
        dashboard.add_widgets(
            TextWidget(
                markdown = 'Web Monitor Dashboard',
                width = 24,
                height = 2
            )
        )
        dashboard.add_widgets(
            GraphWidget(
                left = [cw.Metric(
                    metric_name = 'Page Time',
                    namespace = 'Monitor',
                )],
                width = 6,
                height = 3,
            )
        )

        # Define the Lambda function resource
        monitoring_function = _lambda.Function(
            self,
            "MonitoringFunction",
            runtime = _lambda.Runtime.PYTHON_3_11, # Choose any supported Python runtime
            code = _lambda.Code.from_asset("canary_monitoring/lambda"), # Points to the lambda directory
            handler = "resources_monitor.measuring_handler", # Points to the 'helloworld' file in the lambda directory
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
