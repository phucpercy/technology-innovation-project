from aws_cdk import (
    # Duration,
    Stack,
    aws_lambda as _lambda,
    aws_apigateway as apigateway,
    aws_cloudwatch as cw,
    aws_iam as iam,
    # aws_sqs as sqs,
)

from aws_cdk.aws_cloudwatch import TextWidget, SingleValueWidget, GraphWidget
from constructs import Construct


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
        monitor_function = _lambda.Function(
            self,
            "MonitorFunction",
            runtime = _lambda.Runtime.PYTHON_3_11,
            code = _lambda.Code.from_asset("technology_innovation_project/lambda"), # Points to the lambda directory
            handler = "monitor.lambda_handler",
        )
        monitor_function.add_to_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                'cloudwatch:PutMetricData',
            ],
            resources=[
                '*',
            ],
        ))

        # Define the API Gateway resource
        api = apigateway.LambdaRestApi(
            self,
            "MonitorApi",
            handler = monitor_function,
            proxy = False,
        )
        
        # Define the '/monitor' resource with a GET method
        monitor_resource = api.root.add_resource("monitor")
        monitor_resource.add_method("GET")
