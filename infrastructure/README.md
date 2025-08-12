Infrastructure (AWS CDK)
=================================

This directory contains AWS CDK stacks to deploy the Prethrift backend to AWS using:

- API Gateway + Lambda (FastAPI via Mangum)
- Aurora PostgreSQL (Serverless v2) via RDS
- S3 bucket for inventory image storage & static asset hosting
- S3 pre-signed upload flow for third-party catalogue ingestion
- CloudFront distribution for SPA frontend
- Asynchronous image processor Lambda triggered by S3 object creation
- Dead-letter queue (SQS) + retry configuration for processor
- EventBridge bus for post-processing events
- Lambda Layer for heavy inference libraries (torch, torchvision, pillow, scikit-learn)

High-Level Architecture
-----------------------

User -> API Gateway -> Lambda (FastAPI) -> Aurora PostgreSQL
                         |
                         +-> S3 (store images/catalog uploads)

Contents
--------
* `cdk_app.py` - entrypoint for CDK
* `stacks.py` - main stack definitions
* `lambda_build/` - (generated) packaged backend code for Lambda (gitignored)

Deployment Quick Start
----------------------
1. Create/activate a Python 3.11+ env in `infrastructure/`
2. Install deps: `pip install -r requirements.txt`
3. Bootstrap: `cdk bootstrap`
4. Synthesize: `cdk synth`
5. Deploy: `cdk deploy PrethriftStack`

Local Development vs Cloud
--------------------------
Local uses SQLite / file storage. Cloud stack sets `DATABASE_URL` for Lambda to Aurora. Image uploads use pre-signed URLs.

Secure External Upload & Async Processing
----------------------------------------
1. Client obtains a signed upload (POST/PUT) from `/upload/presign` (protected by API key + Cognito JWT).
2. Client uploads directly to the images bucket.
3. S3 ObjectCreated event triggers the processor Lambda.
4. Processor standardizes, classifies, writes DB records, emits success EventBridge event (or DLQ on failure after retries).

Inference Layer
---------------
Heavy ML libs are moved to `layers/inference`. Edit `python/requirements.txt` there to manage versions. The CDK constructs a Lambda Layer and attaches it to both API and processor functions, while excluding those modules from per-function bundles.

EventBridge Events
------------------
Processor emits a custom event with `source: "prethrift.image-processor"` and `detail-type: "InventoryImageProcessed"` plus JSON detail containing `image_id`, `file_path`, `garments`, `width`, `height`. You can add rules targeting this bus `PrethriftProcessingBus` and matching that `detail-type` for downstream workflows.

Dead-letter Queue (DLQ)
-----------------------
Failed processor invocations after retries land in the SQS DLQ exposed via stack output `ProcessorDlqUrl`.

Next Ideas
----------
* Add SNS / Slack notifications consuming EventBridge events.
* Add end-to-end integration tests using `assertions` module for synthesized template.
* Move embedding/model operations to a separate service or container for larger models.

Layer Build Script
------------------
Use `scripts/build_inference_layer.sh` to build the layer dependencies locally before `cdk deploy` if you change layer requirements.

```
chmod +x infrastructure/scripts/build_inference_layer.sh
infrastructure/scripts/build_inference_layer.sh
```
