# Overleaf Community Edition — Multi-Arch Docker Images (`amd64` & `arm64`)

[![Build Overleaf Multi-Arch](https://github.com/makrron/overleaf-multiarch/actions/workflows/build.yml/badge.svg)](https://github.com/makrron/overleaf-multiarch/actions/workflows/build.yml)

Automated native multi-architecture builds (`linux/amd64` and `linux/arm64`) for **[Overleaf Community Edition (ShareLaTeX)](https://github.com/overleaf/overleaf)**.

---

## 🎯 Motivation

The official Overleaf Community Edition Docker image (`sharelatex/sharelatex`) is currently published **only for `linux/amd64`** ([tracked in Overleaf issue #1059](https://github.com/overleaf/overleaf/issues/1059)).

This repository provides **native multi-arch builds** for both **`linux/amd64`** (standard x86 servers, Intel/AMD PCs) and **`linux/arm64`** (Raspberry Pi 4/5, Apple Silicon M-series, ARM64 servers, Umbrel Home, etc.).

When you pull this image, Docker automatically serves the native binary for your architecture without emulation.

---

## 🚀 Images on GitHub Container Registry (GHCR)

| Tag | Architectures | Source Version |
| :--- | :--- | :--- |
| `ghcr.io/makrron/overleaf:6.3.0` | `linux/amd64`, `linux/arm64` | Overleaf CE `v6.3.0` |
| `ghcr.io/makrron/overleaf:latest` | `linux/amd64`, `linux/arm64` | Latest stable build |

### Quick Pull

```bash
docker pull ghcr.io/makrron/overleaf:6.3.0
```

To verify supported architectures:

```bash
docker buildx imagetools inspect ghcr.io/makrron/overleaf:6.3.0
```

---

## 📦 Docker Compose Example

```yaml
version: '3.7'

services:
  sharelatex:
    image: ghcr.io/makrron/overleaf:6.3.0
    restart: always
    depends_on:
      mongo:
        condition: service_healthy
      redis:
        condition: service_started
    ports:
      - "80:80"
    volumes:
      - ./data/overleaf:/var/lib/overleaf
    environment:
      OVERLEAF_APP_NAME: Overleaf Community Edition
      OVERLEAF_MONGO_URL: mongodb://mongo:27017/sharelatex?replicaSet=rs
      OVERLEAF_REDIS_HOST: redis
      OVERLEAF_REDIS_PORT: 6379
      ENABLED_LINKED_FILE_TYPES: 'project_file,project_output_file'
      ENABLE_CONVERSIONS: 'true'
      EMAIL_CONFIRMATION_DISABLED: 'true'

  mongo:
    image: mongo:8.0
    restart: always
    command: ["--replSet", "rs", "--bind_ip_all", "--port", "27017"]
    volumes:
      - ./data/mongo:/data/db
    healthcheck:
      test: >
        echo "try { rs.status() } catch (err) { rs.initiate({ _id: 'rs', members: [{ _id: 0, host: 'mongo:27017' }] }) }"
        | mongosh --port 27017 --quiet
      interval: 10s
      timeout: 30s
      retries: 30

  redis:
    image: redis:7.2-alpine
    restart: always
    volumes:
      - ./data/redis:/data
```

---

## 🛠️ Automated Builds & Upstream Tracking

Builds are powered by GitHub Actions using native runners and scheduled triggers:
- **⏰ Automatic Daily Check**: Runs every day at **06:00 UTC** (`schedule: cron '0 6 * * *'`). It queries the Docker Hub API for new releases of `sharelatex/sharelatex`. When an unbuilt version is discovered, it automatically initiates the multi-arch build without manual intervention.
- **🚀 Native `linux/amd64`**: Reuses the official, verified Overleaf `sharelatex/sharelatex:<version>` image or compiles natively on GitHub `ubuntu-latest` runners.
- **🚀 Native `linux/arm64`**: Compiles natively on GitHub-hosted `ubuntu-24.04-arm` runners (16 GB RAM, 4 vCPUs) in ~5 minutes, avoiding slow QEMU emulation.
- **✨ Multi-Arch Manifest**: Both architectures are merged into an OCI manifest list using `docker buildx imagetools`.

### Manual Build Trigger

You can also trigger a build on-demand at any time:
1. Go to the **Actions** tab in this repository.
2. Select the **Build Overleaf Multi-Arch** workflow.
3. Click **Run workflow**:
   - Leave `version` blank to auto-detect the latest release, or type a specific version (e.g. `6.3.0`).
   - Click **Run workflow**.

---

## 📄 License

- Build configuration and workflow scripts in this repository are licensed under the [MIT License](LICENSE).
- Overleaf Community Edition source code is licensed under the [GNU AGPLv3](https://github.com/overleaf/overleaf/blob/main/LICENSE).

