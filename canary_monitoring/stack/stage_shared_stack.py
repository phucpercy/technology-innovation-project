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
    aws_ses as ses,
    Duration, Stack, CfnOutput
)
from aws_cdk.aws_cloudwatch import TextWidget, GraphWidget
from constructs import Construct

import config

class CanarySharedStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create SES shared email identity
        self.create_ses_stack()

    def create_ses_stack(self):
        sender_email = config.SENDER_EMAIL
        ses.CfnEmailIdentity(
            self,
            'NotificationSenderEmailIdentity',
            email_identity=sender_email
        )
        for email in config.SUBSCRIPTION_EMAIL_LIST:
            ses.CfnEmailIdentity(
                self,
                'NotificationReceiverEmailIdentity',
                email_identity=email
            )
