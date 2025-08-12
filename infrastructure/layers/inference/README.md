# Inference Lambda Layer

This layer packages heavy ML dependencies so that individual Lambda functions (API & processor) can stay small and faster to deploy. The CDK stack references this directory when creating the `InferenceLayer`.

## Structure

```
inference/
  README.md
  python/
    requirements.txt  # (optional) pin extra libs; otherwise reuse root backend build assets
```

AWS Lambda looks for a `python/` folder inside the layer zip; any packages placed there become importable.

## Adding Dependencies

1. Edit `python/requirements.txt` with pinned versions (keep in sync with backend if needed):
   ```
   torch
   torchvision
   pillow
   scikit-learn
   ```
2. (Optional) Build locally to validate:
   ```bash
   cd infrastructure/layers/inference
   pip install -r python/requirements.txt -t python
   ```
3. Deploy CDK; the layer will be bundled and attached to functions.

## Notes
- Big libs increase cold start. Consider trimming models or using AWS DLC / ECR if size > 250MB unzipped.
- If inference moves to a separate service (e.g., ECS/Fargate), you can detach this layer and remove heavy deps from Lambdas entirely.
