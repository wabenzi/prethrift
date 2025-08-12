#!/usr/bin/env python3
import aws_cdk as cdk
from stacks import PrethriftStack

app = cdk.App()
PrethriftStack(app, "PrethriftStack")
app.synth()
