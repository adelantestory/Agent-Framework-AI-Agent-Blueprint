#!/bin/bash
# Quick deployment script for adelante-ai-chatbot Container App
# This script updates the startup probe configuration on an existing Container App

set -e

# Configuration
RESOURCE_GROUP="${RESOURCE_GROUP:-asf-chatbot-rg}"
CONTAINER_APP_NAME="${CONTAINER_APP_NAME:-adelante-ai-chatbot}"

echo "========================================="
echo "Updating Container App Startup Probe"
echo "========================================="
echo "Resource Group: $RESOURCE_GROUP"
echo "Container App: $CONTAINER_APP_NAME"
echo ""

# Check if container app exists
echo "Checking if Container App exists..."
if ! az containerapp show --name "$CONTAINER_APP_NAME" --resource-group "$RESOURCE_GROUP" &> /dev/null; then
    echo "❌ Container App '$CONTAINER_APP_NAME' not found in resource group '$RESOURCE_GROUP'"
    echo "   Please deploy the app first using the main.bicep template"
    exit 1
fi

echo "✓ Container App found"
echo ""

# Update startup probe
echo "Updating startup probe configuration..."
az containerapp update \
  --name "$CONTAINER_APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --startup-probe-type http \
  --startup-probe-path /startup \
  --startup-probe-interval 5 \
  --startup-probe-initial-delay 10 \
  --startup-probe-failure-threshold 12 \
  --startup-probe-timeout 3

echo ""
echo "✓ Startup probe updated successfully"
echo ""

# Get FQDN
FQDN=$(az containerapp show \
  --name "$CONTAINER_APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --query "properties.configuration.ingress.fqdn" -o tsv)

echo "========================================="
echo "Deployment Complete"
echo "========================================="
echo "App URL: https://$FQDN"
echo ""
echo "Test endpoints:"
echo "  curl https://$FQDN/startup"
echo "  curl https://$FQDN/health"
echo ""
echo "Monitor logs:"
echo "  az containerapp logs show --name $CONTAINER_APP_NAME --resource-group $RESOURCE_GROUP --follow"
echo ""
