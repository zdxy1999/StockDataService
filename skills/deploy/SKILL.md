---
name: remote-deploy
description: Automates deployment of Stock Data Service to remote server. Use when user requests deployment, needs to deploy to production, or wants to update the remote service.
---

# Remote Deploy Skill

Automates the complete deployment workflow for Stock Data Service, including building, uploading, and restarting the service on the remote server.

## When to use
- User requests to deploy to production server
- User mentions "deploy", "update service", or "release to server"
- User asks to build and push docker image
- User wants to update the remote stock-data-service

## Prerequisites
- VERSION file must contain correct version number
- All code changes must be committed and tested
- Server connection info in env.md must be correct
- SSH key access to remote server required

## Instructions

### 1. Build Docker Image
Build the amd64 architecture docker image for the remote server:

```bash
VERSION=$(cat VERSION)
docker build --platform linux/amd64 -t stock-data-service:${VERSION}-amd64 .
```

### 2. Save Image as TAR
Save the docker image to a tar file for upload:

```bash
mkdir -p dist
docker save stock-data-service:${VERSION}-amd64 -o dist/stock-data-service_amd64_${VERSION}.tar
```

### 3. Upload to Remote Server
Upload the image tar file to the remote server:

```bash
scp -i ~/.ssh/zdxy-ali.pem dist/stock-data-service_amd64_${VERSION}.tar root@47.99.207.160:/root/
```

### 4. Deploy on Remote Server
Connect to the server and deploy the new image:

```bash
ssh -i ~/.ssh/zdxy-ali.pem root@47.99.207.160
```

Then execute:
```bash
# Load new image
docker load -i /root/stock-data-service_amd64_${VERSION}.tar

# Stop and remove old container
docker stop stock-data-service
docker rm stock-data-service

# Start new container with correct configuration
docker run -d \
  --name stock-data-service \
  -p 9090:9090 \
  -p 7070:7070 \
  -v /data/stock-data-service:/app/data \
  -e DATA_ROOT=/app/data \
  -e DAILY_CRON="30 19 * * 1-5" \
  --restart=always \
  stock-data-service:${VERSION}-amd64
```

### 5. Verify Deployment
Check that the service is running correctly:

```bash
# Check container status
docker ps | grep stock-data-service

# Check service logs
docker logs --tail 10 stock-data-service

# Test HTTP endpoint
curl http://localhost:9090/
curl http://localhost:9090/tradeDayBasic

# Test MCP endpoint
curl http://localhost:7070/
```

## Quick One-Liner (Alternative)
For faster deployment, use the automated script:

```bash
./scripts/deploy.sh
```

See `references/automated-script.md` for details on the automated script.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Build fails | Check Docker daemon is running and VERSION file exists |
| Upload timeout | Image is ~400MB, may take several minutes on slow connections |
| Container won't start | Check docker logs for errors, verify port availability |
| Service unreachable | Verify firewall rules allow ports 9090 and 7070 |
| Data loss | Ensure volume mount `-v /data/stock-data-service:/app/data` is correct |

## Reference
- Server connection: `env.md`
- Full deployment guide: `references/full-guide.md`
- Automated script: `scripts/deploy.sh`
