import aws_cdk as cdk
from constructs import Construct
from aws_cdk.pipelines import CodePipeline, CodePipelineSource, ShellStep, ManualApprovalStep

from canary_monitoring.stack.pipeline_app_stage import PipelineAppStage


class CanaryPipelineStack(cdk.Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        pipeline = CodePipeline(self, "Pipeline",
                        pipeline_name="CanaryPipeline",
                        synth=ShellStep("Synth",
                            input=CodePipelineSource.git_hub(
                                "phucpercy/technology-innovation-project",
                                "main",
                                authentication=cdk.SecretValue.secrets_manager('my-github-token')
                            ),
                            commands=["npm install -g aws-cdk",
                                "python -m pip install -r requirements.txt",
                                "cdk synth"]
                        )
                    )
        gamma_stage = pipeline.add_stage(PipelineAppStage(self, "Gamma"))
        gamma_stage.add_post(ManualApprovalStep("Manual approval before production"))
        prod_stage = pipeline.add_stage(PipelineAppStage(self, "Prod"))