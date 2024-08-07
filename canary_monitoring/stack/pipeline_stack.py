from functools import partial

import aws_cdk as cdk
from constructs import Construct
from aws_cdk.pipelines import CodePipeline, CodePipelineSource, ShellStep, ManualApprovalStep, CodeBuildStep
import aws_cdk.aws_iam as iam

from canary_monitoring.stack.pipeline_app_stage import PipelineAppStage
import config


class CanaryPipelineStack(cdk.Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        code_source = CodePipelineSource.git_hub(
            config.REPO_PATH,
            config.REPO_BRANCH,
            authentication=cdk.SecretValue.secrets_manager(config.REPO_SECRET_KEY_ID)
        )
        ShellStepWithEnvs = partial(ShellStep, env=config.export_env())
        synth_step = ShellStepWithEnvs("Synth",
            input=code_source,
            install_commands=["npm install -g aws-cdk",
                "python -m pip install -r requirements.txt"],
            commands=["cdk synth"]
        )
        pipeline = CodePipeline(self, "Pipeline",
            pipeline_name="CanaryPipeline",
            synth=synth_step
        )
        gamma_stage = pipeline.add_stage(PipelineAppStage(self, "Gamma"))
        gamma_stage.add_pre(ShellStepWithEnvs(
            "Unit Test",
            input=code_source,
            install_commands=["python -m pip install -r requirements.txt"],
            commands=["python -m pytest tests/unit"]
        ))
        gamma_stage.add_post(CodeBuildStep(
            "Integration Test",
            input=code_source,
            install_commands=["python -m pip install -r requirements.txt"],
            commands=["STAGE_NAME=Gamma python -m pytest tests/integration"],
            env=config.export_env(),
            role_policy_statements=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        'apigateway:GET',
                        'lambda:InvokeFunction',
                        'lambda:ListFunctions',
                        'cloudwatch:DescribeAlarms',
                    ],
                    resources=['*',],
                )
            ],
        ))
        gamma_stage.add_post(ManualApprovalStep("Manual approval before production"))
        prod_stage = pipeline.add_stage(PipelineAppStage(self, "Prod"))
