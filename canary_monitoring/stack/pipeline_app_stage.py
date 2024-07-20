import aws_cdk as cdk
from constructs import Construct
from canary_monitoring.stack.canary_monitoring_stack import CanaryMonitoringStack

class PipelineAppStage(cdk.Stage):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        CanaryMonitoringStack(self, "CanaryMonitoringStack", construct_id)