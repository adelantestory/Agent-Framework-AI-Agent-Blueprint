# Qdrant Azure Marketplace Integration Guide

## Overview
This guide walks you through purchasing Qdrant from Azure Marketplace and integrating it with your local development environment.

## Benefits of Azure Marketplace Purchase
✅ **Unified Billing**: Charges appear on your Azure subscription
✅ **Budget Control**: Uses your existing Azure credits/budget
✅ **Simplified Management**: Manage from Azure Portal
✅ **Enterprise Ready**: Azure compliance and security
✅ **Pay-as-you-go**: Scale based on usage

---

## Part 1: Purchase Qdrant from Azure Marketplace

### Step 1: Access Azure Marketplace

1. Go to [Azure Portal](https://portal.azure.com)
2. Click on "Marketplace" or search "Marketplace" in the top search bar
3. In Marketplace, search for **"Qdrant"**

### Step 2: Select Qdrant Offering

You'll see options like:
- **Qdrant Cloud** (Managed SaaS - Recommended)
- **Qdrant Vector Database**

**Choose**: Qdrant Cloud (fully managed)

### Step 3: Subscribe & Configure

1. Click **"Subscribe"** or **"Get It Now"**
2. Fill in details:
   - **Name**: `adelante-qdrant-prod` (or your preferred name)
   - **Subscription**: Your Azure subscription
   - **Resource Group**: Create new or use existing
   - **Region**: Choose closest to your users (e.g., East US, West Europe)
   - **Plan**:
     - Free tier (good for development/testing)
     - Paid tiers (production workloads)

3. Click **"Review + Subscribe"**
4. Accept terms and click **"Subscribe"**

### Step 4: Wait for Deployment

- Deployment typically takes 5-10 minutes
- You'll receive email confirmation when ready
- Status will show "Succeeded" in Azure Portal

### Step 5: Get Connection Details

1. In Azure Portal, go to **Resource Groups** → Your resource group
2. Find your Qdrant resource
3. Click on it to open
4. Look for **"Overview"** or **"Keys and Endpoints"** section
5. Copy these values:
   - **Cluster URL**: Something like `https://abc123.qdrant.io:6333`
   - **API Key**: Long string of characters

**Save these securely!** You'll need them for local setup.

---

## Part 2: Local Development Setup

### Step 1: Install Required Packages

```bash
pip install qdrant-client langchain-qdrant
```

### Step 2: Update .env File

Add your Qdrant credentials from Azure Marketplace to your `.env` file:

```bash
# .env additions
QDRANT_URL=https://your-cluster.qdrant.io:6333
QDRANT_API_KEY=your-api-key-from-azure-portal
QDRANT_COLLECTION_NAME=adelante_knowledge
```

**Replace** `your-cluster.qdrant.io:6333` and `your-api-key-from-azure-portal` with actual values from Azure Portal.

### Step 3: Verify Configuration

Run this test to verify your Qdrant connection:

```bash
python -c "from qdrant_client import QdrantClient; from config import QDRANT_URL, QDRANT_API_KEY; client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY); print('✅ Connected to Qdrant:', client.get_collections())"
```

If you see "✅ Connected to Qdrant", you're good to go!

---

## Part 3: Migrate from FAISS to Qdrant

### Option A: Automatic Migration (Recommended)

Run the migration script:

```bash
python migrate_to_qdrant.py
```

This will:
1. Load your existing FAISS knowledge base
2. Extract all documents
3. Upload them to Qdrant
4. Test the connection

### Option B: Manual Migration

If you prefer to do it manually:

```python
from migrate_to_qdrant import migrate_faiss_to_qdrant
migrate_faiss_to_qdrant()
```

### Verify Migration

Test that Qdrant has your data:

```bash
python migrate_to_qdrant.py test "What programs does Adelante offer?"
```

You should see search results from Qdrant!

---

## Part 4: Update Your Application

### Option 1: Use New RAG Module (Recommended)

Your code now automatically detects Qdrant:

```python
# tools.py - Update the RAG import
from lc_rag_qdrant import search_knowledge_base, get_retriever

# The rest stays the same!
# It will automatically use Qdrant if credentials are set
```

### Option 2: Gradual Migration

Keep both FAISS and Qdrant, switch via environment variable:

```python
# Set in .env
USE_QDRANT=true  # Use Qdrant
# or
USE_QDRANT=false  # Use FAISS (local)
```

---

## Part 5: Testing Locally

### Test 1: Basic Search

```python
from lc_rag_qdrant import search_knowledge_base

results = search_knowledge_base("What is Adelante Story Foundation?")
for i, doc in enumerate(results, 1):
    print(f"\nResult {i}:")
    print(doc.page_content[:200])
```

### Test 2: Agent Integration

Run your FastAPI app:

```bash
python app.py
```

Visit `http://localhost:5000/adelante` and ask the chatbot questions. It will now query Qdrant!

### Test 3: Add New Documents

```python
from lc_rag_qdrant import build_knowledge_base

# Add a new webpage
build_knowledge_base("https://example.com/new-page")
```

---

## Part 6: Monitor Usage in Azure

### View Qdrant Usage

1. Go to Azure Portal
2. Navigate to your Qdrant resource
3. Check **"Metrics"** or **"Monitoring"** tab
4. View:
   - API calls per day
   - Storage used
   - Query latency
   - Costs

### Set Budget Alerts

1. In Azure Portal, go to **"Cost Management + Billing"**
2. Click **"Budgets"**
3. Create alert for Qdrant spending
4. Get email when approaching budget limit

---

## Cost Optimization Tips

### Development Environment
- Use **Free tier** during development (1GB storage, limited requests)
- Only upgrade to paid when deploying to production

### Production Environment
- Start with smallest paid tier
- Monitor usage in Azure Portal
- Scale up only when needed
- Set budget alerts

### Estimated Costs (via Azure Marketplace)
- **Free Tier**: $0/month (1GB, 1M requests)
- **Starter**: ~$25-50/month (10GB)
- **Professional**: ~$100-200/month (50GB, high throughput)
- **Enterprise**: Custom pricing

*Exact pricing may vary - check Azure Marketplace for current rates*

---

## Troubleshooting

### Connection Errors

**Problem**: `ConnectionError: Cannot connect to Qdrant`

**Solution**:
1. Verify QDRANT_URL includes `https://` and port (`:6333`)
2. Check API key is correct (no extra spaces)
3. Ensure Qdrant resource is running in Azure Portal

### Import Errors

**Problem**: `ModuleNotFoundError: No module named 'qdrant_client'`

**Solution**:
```bash
pip install qdrant-client langchain-qdrant
```

### Collection Not Found

**Problem**: `Collection 'adelante_knowledge' not found`

**Solution**:
Run migration script or create collection:
```bash
python migrate_to_qdrant.py
```

### Slow Performance

**Problem**: Queries are slow

**Solution**:
1. Check Azure region - should be close to your location
2. Upgrade Qdrant tier if on free plan
3. Check network connectivity

---

## Next Steps

Once Qdrant is working locally:

1. ✅ **Test thoroughly** with your chatbot
2. ✅ **Monitor costs** in Azure Portal
3. ✅ **Deploy to production** (Azure App Service)
4. ✅ **Set up monitoring** (Application Insights)
5. ✅ **Configure backup** strategy

---

## Support Resources

- **Qdrant Docs**: https://qdrant.tech/documentation/
- **Azure Marketplace Support**: Open ticket in Azure Portal
- **LangChain Qdrant**: https://python.langchain.com/docs/integrations/vectorstores/qdrant

---

## Summary

You now have:
✅ Qdrant purchased via Azure Marketplace (billed to Azure subscription)
✅ Local development environment connected to Qdrant
✅ FAISS knowledge base migrated to Qdrant
✅ Application updated to use Qdrant automatically
✅ Monitoring set up in Azure Portal

Your chatbot now uses a production-grade vector database while keeping costs on your Azure budget!
