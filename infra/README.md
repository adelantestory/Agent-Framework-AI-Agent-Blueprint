# Infrastructure Configuration

This directory contains the Azure infrastructure-as-code (IaC) for deploying the `adelante-ai-chatbot` Container App.

## Files

- **`main.bicep`** - Main Bicep template defining the Container App with optimized startup probe configuration
- **`DEPLOYMENT.md`** - Comprehensive deployment guide with multiple deployment options

## Quick Start

To deploy or update the Container App:

```bash
az deployment group create \
  --resource-group asf-chatbot-rg \
  --template-file infra/main.bicep
```

For detailed instructions, see [DEPLOYMENT.md](./DEPLOYMENT.md).

## Key Configuration

The template includes:

### Startup Probe (Critical for Cold Start Reliability)
- **Path**: `/startup` - Dedicated lightweight endpoint
- **Initial Delay**: 10 seconds - Allows app to initialize
- **Failure Threshold**: 12 - Up to 60 seconds for startup
- **Period**: 5 seconds - Check every 5 seconds

This configuration prevents false alerts during cold starts when the app scales from zero.

### Health Probes
- **Liveness Probe**: `/health` - Checks every 30s, restarts on 3 failures
- **Readiness Probe**: `/health` - Checks every 10s, controls traffic routing

### Scaling
- **Min Replicas**: 0 - Scale to zero for cost optimization
- **Max Replicas**: 10 - Scale up to handle traffic
- **HTTP Scaling Rule**: Scales based on concurrent requests

## Application Endpoints

The application provides these health check endpoints:

| Endpoint | Purpose | Response |
|----------|---------|----------|
| `/startup` | Startup probe - lightweight, fast response | `{"status": "ready"}` |
| `/health` | Liveness/readiness - comprehensive health check | `{"status": "healthy", "mcp_connected": bool}` |

## Notes

- The startup probe configuration is specifically designed to handle cold starts in a scale-to-zero scenario
- If you need always-on behavior, set `minReplicas: 1` in the template (cost tradeoff)
- The startup probe allows up to 60 seconds for the app to start (10s initial + 12 × 5s)
- Once the startup probe succeeds, liveness and readiness probes take over

## Related Documentation

- [Azure Container Apps Health Probes](https://learn.microsoft.com/en-us/azure/container-apps/health-probes)
- [Bicep Container Apps Reference](https://learn.microsoft.com/en-us/azure/templates/microsoft.app/containerapps)
