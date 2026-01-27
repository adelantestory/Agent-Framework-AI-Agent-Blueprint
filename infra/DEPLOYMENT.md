# Azure Container App Deployment Guide

This guide explains how to deploy the `adelante-ai-chatbot` Azure Container App with proper startup probe configuration to prevent false alerts during cold starts.

## Problem Statement

The Container App was experiencing false Sev1 alerts during cold starts due to:
- Startup probes failing before the application was fully ready
- Insufficient delay and failure thresholds for cold start scenarios
- Lack of a dedicated lightweight startup endpoint

## Solution

This deployment includes:

1. **Dedicated `/startup` endpoint** - A lightweight endpoint that returns immediately when the app can accept connections
2. **Optimized startup probe configuration**:
   - `initialDelaySeconds: 10` - Gives the app time to start before first probe
   - `failureThreshold: 12` - Allows up to 60 seconds for startup (12 failures × 5 second period)
   - `periodSeconds: 5` - Checks every 5 seconds
   - `timeoutSeconds: 3` - 3 second timeout per probe
3. **Separate liveness and readiness probes** using the `/health` endpoint

## Prerequisites

- Azure CLI installed and authenticated
- Azure subscription with Container Apps enabled
- Existing Container App Environment named `adelante-chatbot-env`
- Container image pushed to Azure Container Registry

## Deployment Steps

### Option 1: Deploy using Azure CLI with Bicep

```bash
# Set variables
RESOURCE_GROUP="asf-chatbot-rg"
LOCATION="eastus"  # or your preferred location
CONTAINER_IMAGE="adelantechatbot.azurecr.io/adelante-ai-chatbot:latest"

# Deploy the Bicep template
az deployment group create \
  --resource-group $RESOURCE_GROUP \
  --template-file infra/main.bicep \
  --parameters \
    location=$LOCATION \
    containerImage=$CONTAINER_IMAGE
```

### Option 2: Update Existing Container App

If you already have a Container App deployed, you can update it to add the startup probe:

```bash
az containerapp update \
  --name adelante-ai-chatbot \
  --resource-group asf-chatbot-rg \
  --startup-probe-type http \
  --startup-probe-path /startup \
  --startup-probe-interval 5 \
  --startup-probe-initial-delay 10 \
  --startup-probe-failure-threshold 12 \
  --startup-probe-timeout 3
```

### Option 3: Use Azure Portal

1. Navigate to your Container App in the Azure Portal
2. Go to "Containers" section
3. Edit the container configuration
4. Under "Health probes", add/edit the Startup probe:
   - **Type**: HTTP
   - **Path**: `/startup`
   - **Port**: 5000
   - **Initial Delay**: 10 seconds
   - **Period**: 5 seconds
   - **Failure Threshold**: 12
   - **Success Threshold**: 1
   - **Timeout**: 3 seconds

## Verification

After deployment, verify the startup probe configuration:

```bash
# Get the Container App details
az containerapp show \
  --name adelante-ai-chatbot \
  --resource-group asf-chatbot-rg \
  --query "properties.template.containers[0].probes"
```

Test the endpoints:

```bash
# Get the FQDN
FQDN=$(az containerapp show \
  --name adelante-ai-chatbot \
  --resource-group asf-chatbot-rg \
  --query "properties.configuration.ingress.fqdn" -o tsv)

# Test startup endpoint
curl https://$FQDN/startup

# Test health endpoint
curl https://$FQDN/health
```

Expected responses:
- `/startup`: `{"status":"ready"}`
- `/health`: `{"status":"healthy","mcp_connected":true/false}`

## Monitoring

After deployment, monitor the Container App logs to ensure:
- Startup probes succeed after the initial delay
- No false failures during cold starts
- App scales up/down properly

```bash
# Stream logs
az containerapp logs show \
  --name adelante-ai-chatbot \
  --resource-group asf-chatbot-rg \
  --follow
```

## Configuration Details

### Startup Probe
- **Purpose**: Determines when the container has started successfully
- **Endpoint**: `/startup` - Lightweight endpoint that returns immediately
- **Timing**: 10s initial delay + up to 60s for startup (12 × 5s)
- **Behavior**: Once successful, liveness and readiness probes take over

### Liveness Probe
- **Purpose**: Determines if the container is healthy and should be restarted
- **Endpoint**: `/health` - Checks app health and MCP connection status
- **Timing**: Checks every 30 seconds after startup probe succeeds
- **Behavior**: 3 consecutive failures trigger a restart

### Readiness Probe
- **Purpose**: Determines if the container can receive traffic
- **Endpoint**: `/health` - Checks app health and MCP connection status
- **Timing**: Checks every 10 seconds
- **Behavior**: Controls traffic routing to the container

## Troubleshooting

### Startup Probe Still Failing

If you still see startup probe failures:

1. Increase `initialDelaySeconds` to give more time before first probe
2. Increase `failureThreshold` to allow more retry attempts
3. Check application logs for slow startup issues
4. Consider setting `minReplicas: 1` to avoid cold starts (with cost tradeoff)

### Alert Still Firing

If Sev1 alerts still fire after deployment:

1. Review the Azure Monitor alert rule conditions
2. Ensure alerts are based on actual customer impact metrics
3. Consider different alert severity for probe-related issues
4. Add alert suppression during known maintenance windows

## Cost Optimization

Current configuration uses `minReplicas: 0` for cost optimization (scale-to-zero).

**Tradeoff considerations**:
- `minReplicas: 0` - Lowest cost, but cold starts may take 10-60 seconds
- `minReplicas: 1` - Always-on, no cold starts, higher cost (~$14-30/month for 0.5 CPU + 1GB)

To change to always-on mode:

```bash
az containerapp update \
  --name adelante-ai-chatbot \
  --resource-group asf-chatbot-rg \
  --min-replicas 1
```

## References

- [Azure Container Apps health probes documentation](https://learn.microsoft.com/en-us/azure/container-apps/health-probes)
- [Bicep Container Apps reference](https://learn.microsoft.com/en-us/azure/templates/microsoft.app/containerapps)
- Original Issue: adelantestory/Agent-Framework-AI-Agent-Blueprint#1
