# Azure Container App Startup Probe Fix - Summary

## Issue
**Alert ID**: `sre-test-incident-sev1-1804`  
**Problem**: False Sev1 alerts during cold starts of the `adelante-ai-chatbot` Container App  
**Root Cause**: Startup probe failures when the app scales from zero before it's fully ready

## Solution Overview

This fix implements a **dedicated lightweight startup endpoint** and **optimized probe configuration** to prevent false failures during cold starts.

### Changes Made

#### 1. Application Code (`app.py`)
Added a new `/startup` endpoint that returns immediately when FastAPI is ready:

```python
@app.get("/startup")
async def startup_check():
    """
    Lightweight startup probe endpoint for Container App.
    Returns immediately to signal the app has started and can accept connections.
    """
    return {"status": "ready"}
```

**Why this works:**
- Returns instantly (< 2ms) without waiting for external dependencies
- Signals that the FastAPI server is accepting connections
- Perfect for startup probes that need quick feedback

#### 2. Infrastructure Configuration (`infra/main.bicep`)
Created a complete Bicep template with optimized startup probe configuration:

```bicep
probes: [
  {
    type: 'Startup'
    httpGet: {
      path: '/startup'
      port: 5000
    }
    initialDelaySeconds: 10      // Wait 10s before first probe
    periodSeconds: 5              // Check every 5 seconds
    failureThreshold: 12          // Allow up to 12 failures (60s total)
    timeoutSeconds: 3             // 3s timeout per probe
  }
]
```

**How this prevents false alerts:**
- **10s initial delay** - Gives the container time to start Python and initialize FastAPI
- **12 failure threshold** - Allows up to 60 seconds for startup (12 × 5s periods)
- **Lightweight endpoint** - `/startup` responds instantly, unlike `/` which loads templates

#### 3. Documentation
- **`infra/DEPLOYMENT.md`** - Complete deployment guide with 3 deployment options
- **`infra/README.md`** - Quick reference for infrastructure configuration
- **`infra/update-startup-probe.sh`** - One-command script to update existing apps

#### 4. Testing
- **`test_health_endpoints.py`** - Automated tests verifying both endpoints work correctly
- All tests pass, endpoints respond in < 2ms

## Deployment

### Quick Update (Existing Container App)
```bash
cd infra
./update-startup-probe.sh
```

### Full Deployment (New or Existing)
```bash
az deployment group create \
  --resource-group asf-chatbot-rg \
  --template-file infra/main.bicep
```

### Verify
```bash
# Get app URL
FQDN=$(az containerapp show \
  --name adelante-ai-chatbot \
  --resource-group asf-chatbot-rg \
  --query "properties.configuration.ingress.fqdn" -o tsv)

# Test endpoints
curl https://$FQDN/startup  # Should return: {"status":"ready"}
curl https://$FQDN/health   # Should return: {"status":"healthy","mcp_connected":...}
```

## Technical Details

### Probe Behavior

1. **Startup Phase** (First 60 seconds max)
   - Container starts
   - Wait 10 seconds
   - Check `/startup` every 5 seconds
   - Allow up to 12 failures
   - Once successful, liveness/readiness probes take over

2. **Running Phase** (After startup succeeds)
   - **Liveness**: Check `/health` every 30s (restart on 3 failures)
   - **Readiness**: Check `/health` every 10s (control traffic routing)

### Cold Start Timeline

```
0s    Container starts
10s   First startup probe → May fail if app still initializing
15s   Second probe → May fail
20s   Third probe → App likely ready → SUCCESS
      ↓
      Liveness and readiness probes begin
      App receives traffic
```

**Before this fix**: Probes started immediately, failed during 0-20s startup window  
**After this fix**: 10s delay + 12 attempts = up to 60s grace period for startup

### Why `/startup` Instead of `/health`?

- **`/startup`**: Ultra-lightweight, returns instantly when FastAPI is ready
- **`/health`**: More comprehensive, checks MCP connection and other services
- **Separation of concerns**: Startup = "can accept requests", Health = "functioning correctly"

## Validation

✅ **Code changes tested**
- Unit tests pass for both endpoints
- Response times < 2ms
- Correct JSON responses

✅ **Security scan passed**
- CodeQL found 0 alerts
- No security vulnerabilities introduced

✅ **Code review completed**
- Documentation improved based on feedback
- Prerequisites clearly documented

## Expected Impact

### Before
- Cold starts triggered false Sev1 alerts
- Startup probes failed during 0-20s initialization window
- Manual intervention required to dismiss false alerts

### After
- No false alerts during normal cold starts
- 60-second grace period for startup
- Automatic detection of actual startup failures (> 60s)

### When to Still Alert

True failures that should still alert:
- App crashes during startup
- App takes > 60 seconds to start (real issue)
- App becomes unhealthy after startup (liveness probe fails)

## Monitoring Recommendations

After deployment, monitor for:

1. **Startup probe success rate** - Should be ~100% after this fix
2. **Cold start duration** - Should be < 20s typically
3. **False alert rate** - Should drop to zero

If startup still fails:
- Check logs for actual startup errors
- Increase `initialDelaySeconds` if needed
- Consider `minReplicas: 1` to avoid cold starts (cost tradeoff)

## Cost Optimization

Current setting: `minReplicas: 0` (scale-to-zero)
- **Pro**: Minimal cost when idle
- **Con**: Cold starts take 10-20 seconds

Alternative: `minReplicas: 1` (always-on)
- **Pro**: No cold starts, instant response
- **Con**: ~$14-30/month baseline cost

## Files Changed

1. **`app.py`** - Added `/startup` endpoint
2. **`infra/main.bicep`** - Complete Container App template with optimized probes
3. **`infra/DEPLOYMENT.md`** - Deployment guide
4. **`infra/README.md`** - Quick reference
5. **`infra/update-startup-probe.sh`** - Deployment script
6. **`test_health_endpoints.py`** - Automated tests

## References

- Original Issue: adelantestory/Agent-Framework-AI-Agent-Blueprint#1
- [Azure Container Apps Health Probes](https://learn.microsoft.com/en-us/azure/container-apps/health-probes)
- [Kubernetes Startup Probes](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/#define-startup-probes)
