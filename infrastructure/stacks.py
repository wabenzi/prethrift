from __future__ import annotations

from pathlib import Path
import os

import aws_cdk as cdk
from aws_cdk import (
    Duration,
    RemovalPolicy,
    Stack,
    aws_lambda as _lambda,
    aws_apigateway as apigw,
    aws_rds as rds,
    aws_ec2 as ec2,
    aws_secretsmanager as secretsmanager,
    aws_s3 as s3,
    aws_iam as iam,
    aws_logs as logs,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_sqs as sqs,
    aws_events as events,
    aws_lambda_destinations as destinations,
    aws_ssm as ssm,
    aws_cloudwatch as cloudwatch,
)
 # Using standard Lambda function constructs; alpha python helper not installed
from aws_cdk import aws_s3_notifications as s3n
from constructs import Construct


class PrethriftStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, *, allowed_origins: list[str] | None = None, **kwargs):  # noqa: D401
        super().__init__(scope, construct_id, **kwargs)
        # Resolve allowed origins via (in order): explicit arg, CDK context, SSM parameter, fallback default
        if allowed_origins is None:
            ctx_val = self.node.try_get_context("allowed_origins")
            resolved: list[str] | None = None
            if ctx_val:
                if isinstance(ctx_val, str):
                    resolved = [o.strip() for o in ctx_val.split(",") if o.strip()]
                elif isinstance(ctx_val, list):
                    resolved = [str(o).strip() for o in ctx_val if str(o).strip()]
            if not resolved:
                ssm_name = self.node.try_get_context("allowed_origins_ssm")
                if ssm_name:
                    param = ssm.StringParameter.from_string_parameter_name(self, "AllowedOriginsParam", ssm_name)
                    resolved = [o.strip() for o in param.string_value.split(",") if o.strip()]
            allowed_origins = resolved or ["http://localhost:5173"]
        origins_env_val = ",".join(allowed_origins)

        # VPC for Aurora Serverless
        vpc = ec2.Vpc(self, "PrethriftVpc", max_azs=2)

        # S3 bucket for images & uploads
        images_bucket = s3.Bucket(
            self,
            "PrethriftImages",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            versioned=False,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            cors=[
                s3.CorsRule(
                    allowed_methods=[s3.HttpMethods.GET, s3.HttpMethods.PUT, s3.HttpMethods.POST],
                    allowed_origins=allowed_origins,
                    allowed_headers=["*"],
                    max_age=300,
                )
            ],
        )

        # S3 bucket for frontend static site
        frontend_bucket = s3.Bucket(
            self,
            "PrethriftFrontend",
            website_index_document="index.html",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        distribution = cloudfront.Distribution(
            self,
            "PrethriftCdn",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3Origin(frontend_bucket),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
            ),
            default_root_object="index.html",
            error_responses=[
                cloudfront.ErrorResponse(http_status=403, response_http_status=200, response_page_path="/index.html", ttl=Duration.minutes(5)),
                cloudfront.ErrorResponse(http_status=404, response_http_status=200, response_page_path="/index.html", ttl=Duration.minutes(5)),
            ],
        )

        # Aurora Serverless v2 PostgreSQL cluster
        db_secret = secretsmanager.Secret(self, "PrethriftDbSecret")
        cluster = rds.ServerlessCluster(
            self,
            "PrethriftAurora",
            engine=rds.DatabaseClusterEngine.aurora_postgres(version=rds.AuroraPostgresEngineVersion.VER_15_4),
            vpc=vpc,
            default_database_name="prethrift",
            credentials=rds.Credentials.from_secret(db_secret),
            scaling=rds.ServerlessScalingOptions(auto_pause=Duration.minutes(10)),
            enable_data_api=True,
        )

        # IAM role for Lambda
        lambda_role = iam.Role(
            self,
            "PrethriftLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole"),
            ],
        )
        images_bucket.grant_read_write(lambda_role)
        db_secret.grant_read(lambda_role)
        cluster.grant_data_api_access(lambda_role)

        backend_root = Path(__file__).resolve().parents[1] / "backend"

        # Lambda for async S3 image processing (triggered by object created)
        # Inference layer (heavy ML libs) to keep function package slim
        layer_dist_path = Path(__file__).resolve().parent / "layers" / "inference" / "dist"
        if not layer_dist_path.exists():
            # create minimal placeholder to allow synth/test
            placeholder = layer_dist_path / "python"
            os.makedirs(placeholder, exist_ok=True)
            (placeholder / "PLACEHOLDER.txt").write_text("Layer placeholder - run build_inference_layer.sh to populate.")
        inference_layer = _lambda.LayerVersion(
            self,
            "InferenceLayer",
            code=_lambda.Code.from_asset(str(layer_dist_path)),
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_11],
            description="Prebuilt inference dependencies layer (placeholder if empty)",
        )

        # Dead-letter queue for failed async invocations
        dlq = sqs.Queue(
            self,
            "ProcessorDLQ",
            retention_period=Duration.days(14),
            enforce_ssl=True,
        )

        # EventBridge bus for successful processing notifications
        event_bus = events.EventBus(self, "ProcessingBus", event_bus_name="PrethriftProcessingBus")

        use_docker = bool(self.node.try_get_context("dockerBundling")) or bool(os.environ.get("ENABLE_DOCKER_BUNDLING"))
        if use_docker:
            processor_code = _lambda.Code.from_asset(
                str(backend_root),
                bundling=cdk.BundlingOptions(
                    image=_lambda.Runtime.PYTHON_3_11.bundling_image,
                    command=[
                        "bash",
                        "-c",
                        "pip install --no-cache-dir -r requirements.txt -t /asset-output "
                        "&& rm -rf /asset-output/torch /asset-output/torchvision /asset-output/pillow /asset-output/Pillow* /asset-output/scikit_learn* "
                        "&& cp -r app /asset-output/app "
                        "&& find /asset-output -type d -name '__pycache__' -prune -exec rm -rf {} + "
                        "&& find /asset-output -name '*.pyc' -delete",
                    ],
                ),
            )
        else:
            # Fallback simple packaging (expects layer to hold heavy deps)
            processor_code = _lambda.Code.from_asset(str(backend_root))
        processor_fn = _lambda.Function(
            self,
            "InventoryImageProcessor",
            code=processor_code,
            handler="app/processor.handler",
            runtime=_lambda.Runtime.PYTHON_3_11,
            architecture=_lambda.Architecture.ARM_64,
            timeout=Duration.seconds(60),
            memory_size=1024,
            role=lambda_role,
            vpc=vpc,
            environment={
                "IMAGES_BUCKET": images_bucket.bucket_name,
                "DATABASE_SECRET_ARN": db_secret.secret_arn,
                "EVENT_BUS_NAME": event_bus.event_bus_name,
                "ALLOWED_ORIGINS": origins_env_val,
            },
            layers=[inference_layer],
            log_retention=logs.RetentionDays.ONE_WEEK,
        )
        images_bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3n.LambdaDestination(processor_fn),
        )

        _lambda.EventInvokeConfig(
            self,
            "ProcessorInvokeConfig",
            function=processor_fn,
            max_event_age=Duration.hours(2),
            retry_attempts=2,
            on_failure=destinations.SqsDestination(dlq),
            on_success=destinations.EventBridgeDestination(event_bus),
        )

        if use_docker:
            api_code = _lambda.Code.from_asset(
                str(backend_root),
                bundling=cdk.BundlingOptions(
                    image=_lambda.Runtime.PYTHON_3_11.bundling_image,
                    command=[
                        "bash",
                        "-c",
                        "pip install --no-cache-dir -r requirements.txt -t /asset-output "
                        "&& rm -rf /asset-output/torch /asset-output/torchvision /asset-output/pillow /asset-output/Pillow* /asset-output/scikit_learn* "
                        "&& cp -r app /asset-output/app "
                        "&& find /asset-output -type d -name '__pycache__' -prune -exec rm -rf {} + "
                        "&& find /asset-output -name '*.pyc' -delete",
                    ],
                ),
            )
        else:
            api_code = _lambda.Code.from_asset(str(backend_root))
        function = _lambda.Function(
            self,
            "PrethriftApiFn",
            code=api_code,
            handler="app/main.handler",
            runtime=_lambda.Runtime.PYTHON_3_11,
            architecture=_lambda.Architecture.ARM_64,
            timeout=Duration.seconds(30),
            memory_size=1024,
            role=lambda_role,
            vpc=vpc,
            environment={
                "IMAGES_BUCKET": images_bucket.bucket_name,
                "DATABASE_SECRET_ARN": db_secret.secret_arn,
                "ALLOWED_ORIGINS": origins_env_val,
            },
            layers=[inference_layer],
            log_retention=logs.RetentionDays.ONE_WEEK,
        )

        api = apigw.LambdaRestApi(
            self,
            "PrethriftApi",
            handler=function,
            proxy=True,
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=allowed_origins,
                allow_methods=["GET", "POST", "OPTIONS"],
                allow_headers=["*"],
            ),
        )
        cdk.CfnOutput(self, "ApiUrl", value=api.url)
        cdk.CfnOutput(self, "BucketName", value=images_bucket.bucket_name)
        cdk.CfnOutput(self, "DbSecretArn", value=db_secret.secret_arn)
        cdk.CfnOutput(self, "FrontendBucket", value=frontend_bucket.bucket_name)
        cdk.CfnOutput(self, "CloudFrontDomain", value=distribution.domain_name)
        cdk.CfnOutput(self, "ProcessingBusArn", value=event_bus.event_bus_arn)
        cdk.CfnOutput(self, "ProcessorDlqUrl", value=dlq.queue_url)
        cdk.CfnOutput(self, "AllowedOrigins", value=origins_env_val)
        # Expose asset hashes for observability/versioning
        if isinstance(function.node.default_child, cdk.CfnResource):
            fn_hash = function.node.try_get_context('@aws-cdk/core:assetHash') or function.node.addr
            cdk.CfnOutput(self, "ApiFnAssetId", value=fn_hash)
        if isinstance(processor_fn.node.default_child, cdk.CfnResource):
            proc_hash = processor_fn.node.try_get_context('@aws-cdk/core:assetHash') or processor_fn.node.addr
            cdk.CfnOutput(self, "ProcessorFnAssetId", value=proc_hash)

        lambda_role.add_to_policy(iam.PolicyStatement(actions=["events:PutEvents"], resources=[event_bus.event_bus_arn]))

        cloudwatch.Alarm(
            self,
            "ProcessorDlqAlarm",
            metric=dlq.metric_approximate_number_of_messages_visible(),
            threshold=0,
            evaluation_periods=1,
            datapoints_to_alarm=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
            alarm_description="Triggered when the processor DLQ receives any messages",
        )
