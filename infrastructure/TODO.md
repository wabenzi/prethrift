Provide API key & origins (dev example):
```
export API_KEY=dev-secret
export ALLOWED_ORIGINS=http://localhost:5173
```

CDK deploy with restricted origins:
```
cd infrastructure
cdk synth
cdk deploy
```

Request a presign (with API key):
```
curl -H "x-api-key: dev-secret" -X POST localhost:8000/upload/presign -H 'Content-Type: application/json' \
  -d '{"object_key":"test/image.jpg","content_type":"image/jpeg"}'
  ```

Install new dep (already in requirements.txt): pip install -r requirements.txt
Export Cognito env vars:
```
export COGNITO_REGION=us-east-1
export COGNITO_USER_POOL_ID=us-east-1_XXXXXXX
export COGNITO_APP_CLIENT_ID=YOURAPPCLIENTID
export API_KEY=dev-secret
export ALLOWED_ORIGINS=http://localhost:5173
```
Local test (replace TOKEN with real ID token):
```
curl -X POST http://localhost:8000/upload/presign \
  -H "x-api-key: dev-secret" \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"object_key":"image.jpg","content_type":"image/jpeg","upload_type":"put"}'
  ```

  Note: Import resolution warnings for boto3/aws_cdk disappear in the venv after installs (already handled). If you want optional: create a Cognito stack, add group-based prefixes, or switch to STS AssumeRole temporary credentials for direct browser multipart uploads.

Tell me if you’d like the CDK updated to provision the Cognito User Pool automatically or to generate per-user IAM limited presigned URLs.

create a local e2e test to use the images in degin/images to upload via s3

Source-level quotas or isolation.

Let me know if you’d like:

Source map of dependency tree
Automated diff-based redeploy gating
Lambda Power Tuning integration
Additional alarms or cost guards


Test validates complete pipeline:

S3 Upload Simulation - Mock bucket with image object
Lambda Handler Execution - Direct invocation of processor.handler
Image Standardization - Resize, optimize, convert to JPEG
Description Extraction - Multi-garment analysis (with OpenAI fallback)
Database Operations - InventoryImage, InventoryItem, Garment records
Attribute Classification - Ontology-based extraction (optional)
Static Deployment - Copy optimized images for frontend serving
Usage:

The test runs in ~3.5s and validates the entire image upload→process→store→deploy pipeline without requiring actual AWS resources or OpenAI API keys
