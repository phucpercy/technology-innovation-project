import aws_cdk as core
import aws_cdk.assertions as assertions

from canary_monitoring.stack.canary_monitoring_stack import CanaryMonitoringStack

# example tests. To run these tests, uncomment this file along with the example
# resource in technology_innovation_project/technology_innovation_project_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = CanaryMonitoringStack(app, "technology-innovation-project")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
