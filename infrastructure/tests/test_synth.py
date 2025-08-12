import aws_cdk as cdk
from aws_cdk.assertions import Template
from stacks import PrethriftStack

def test_stack_synth():
    app = cdk.App(
        context={
            "allowedOrigins": ["http://localhost:5173"],
        }
    )
    stack = PrethriftStack(app, "PrethriftStackTest")
    template = Template.from_stack(stack)

    # Basic resource presence assertions
    # There are helper/provider lambdas; ensure at least the two primary ones exist
    lambdas = [k for k,v in template.to_json()["Resources"].items() if v["Type"] == "AWS::Lambda::Function"]
    assert any("PrethriftApiFn" in name for name in lambdas)
    assert any("InventoryImageProcessor" in name for name in lambdas)
    template.resource_count_is("AWS::S3::Bucket", 2)
    template.resource_count_is("AWS::RDS::DBCluster", 1)
    template.resource_count_is("AWS::Events::EventBus", 1)
    template.resource_count_is("AWS::CloudFront::Distribution", 1)

    # Check EventBridge custom bus name
    template.has_resource_properties("AWS::Events::EventBus", {
        "Name": "PrethriftProcessingBus"
    })

    # Ensure DLQ alarm exists
    alarms = [r for r, v in template.to_json()["Resources"].items() if v["Type"] == "AWS::CloudWatch::Alarm"]
    assert any("ProcessorDlqAlarm" in a for a in alarms)
