from aws_cdk import (
    # Duration,
    Stack,
    aws_lambda as _lambda,
    aws_apigateway as apigateway,
    aws_cloudwatch as cw,
    # aws_sqs as sqs,
)

from aws_cdk.aws_cloudwatch import TextWidget, SingleValueWidget, GraphWidget
from constructs import Construct

import boto3

class TechnologyInnovationProjectStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # The code that defines your stack goes here
        dashboard = cw.Dashboard(self, "Web Monitor Dashboard")
        dashboard.add_widgets(
            TextWidget(
                markdown = 'Web Monitor Dashboard',
                width = 24,
                height = 2
            )
        )
        dashboard.add_widgets(
            SingleValueWidget(
                metrics = [cw.Metric(
                    metric_name = 'Test Metric',
                    namespace = 'Monitor',
                )],
                width = 6,
                height = 3,
            )
        )

        metric_data = 6
        metric = {
            'MetricName': 'Test Metric',
            'Unit': 'None',
            'Value': metric_data
        }

        cloudwatch = boto3.client('cloudwatch', 'us-east-1')
        cloudwatch.put_metric_data(
            Namespace='Monitor',
            MetricData=[metric]
        )

        # Define the Lambda function resource
        hello_world_function = _lambda.Function(
            self,
            "HelloWorldFunction",
            runtime = _lambda.Runtime.PYTHON_3_11, # Choose any supported Python runtime
            code = _lambda.Code.from_asset("technology_innovation_project/lambda"), # Points to the lambda directory
            handler = "helloworld.lambda_handler", # Points to the 'helloworld' file in the lambda directory
        )

        # Define the API Gateway resource
        api = apigateway.LambdaRestApi(
            self,
            "HelloWorldApi",
            handler = hello_world_function,
            proxy = False,
        )
        
        # Define the '/hello' resource with a GET method
        hello_resource = api.root.add_resource("hello")
        hello_resource.add_method("GET")
