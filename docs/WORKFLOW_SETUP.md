# Lägg till GitHub Actions workflow manuellt

Eftersom GitHub kräver extra scope (`workflow`) för att pusha Actions-filer via CLI, behöver du lägga till denna fil manuellt.

## Steg

1. Gå till: https://github.com/pexnet/vmtips/new/main/.github/workflows
2. Filnamn: `docker-build.yml`
3. Klistra in innehållet nedan
4. Commita direkt till `main`

---

## Filinnehåll (kopiera allt)

```yaml
name: Build and Push Docker Image

on:
  push:
    branches: [main]
  workflow_dispatch:

env:
  REGISTRY: docker.io
  IMAGE_NAME: pexnet/vmtips

jobs:
  build-and-push:
    runs-on: ubuntu-latest
    permissions:
      contents: read

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up QEMU
        uses: docker/setup-qemu-action@v3

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Log in to Docker Hub
        uses: docker/login-action@v3
        with:
          username: ${{ secrets.DOCKERHUB_USERNAME }}
          password: ${{ secrets.DOCKERHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=sha,prefix=,suffix=,format=short
            type=raw,value=latest,enable={{is_default_branch}}

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          file: ./Dockerfile
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
          platforms: linux/amd64,linux/arm64
```

## Efter detta

1. Lägg till secrets i repo-inställningar:
   - Gå till https://github.com/pexnet/vmtips/settings/secrets/actions
   - `DOCKERHUB_USERNAME` = ditt Docker Hub-användarnamn
   - `DOCKERHUB_TOKEN` = access token från https://hub.docker.com/settings/security

2. Pusha valfri ändring till `main` → workflow triggar automatiskt
