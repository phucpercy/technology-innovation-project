import aws_cdk as cdk
from constructs import Construct
from aws_cdk.pipelines import CodePipeline, CodePipelineSource, ShellStep

class CanaryPipelineStack(cdk.Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        CodePipeline(self, "Pipeline",
                        pipeline_name="CanaryPipeline",
                        synth=ShellStep("Synth",
                            input=CodePipelineSource.git_hub("phucpercy/technology-innovation-project", "main"),
                            commands=["npm install -g aws-cdk",
                                "python -m pip install -r requirements.txt",
                                "cdk synth"]
                        )
                    )