// Azure Container App infrastructure for adelante-ai-chatbot
// This Bicep template defines the Container App with proper startup probe configuration
// to prevent false alerts during cold starts

@description('Location for all resources')
param location string = resourceGroup().location

@description('Container App Environment name')
param environmentName string = 'adelante-chatbot-env'

@description('Container App name')
param containerAppName string = 'adelante-ai-chatbot'

@description('Container image name')
param containerImage string = 'adelantechatbot.azurecr.io/adelante-ai-chatbot:latest'

@description('Target port for the container')
param targetPort int = 5000

@description('Minimum replicas (set to 0 for scale-to-zero)')
param minReplicas int = 0

@description('Maximum replicas')
param maxReplicas int = 10

// Container App Environment (must already exist)
// Create the environment first if it doesn't exist:
// az containerapp env create --name adelante-chatbot-env --resource-group asf-chatbot-rg --location eastus
resource environment 'Microsoft.App/managedEnvironments@2023-05-01' existing = {
  name: environmentName
}

// Container App with startup probe configuration
resource containerApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: containerAppName
  location: location
  properties: {
    managedEnvironmentId: environment.id
    configuration: {
      ingress: {
        external: true
        targetPort: targetPort
        allowInsecure: false
        traffic: [
          {
            latestRevision: true
            weight: 100
          }
        ]
      }
      // Secrets configuration
      // Note: If using a private container registry, add registry credentials here
      // Example:
      // secrets: [
      //   {
      //     name: 'registry-password'
      //     value: '<registry-password>'
      //   }
      // ]
      // For managed identity authentication, no secrets are needed for ACR
      secrets: []
    }
    template: {
      containers: [
        {
          name: 'chatbot'
          image: containerImage
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          // Startup probe configuration to prevent false failures during cold starts
          probes: [
            {
              type: 'Startup'
              httpGet: {
                path: '/startup'
                port: targetPort
                scheme: 'HTTP'
              }
              // Give the app time to start up before first probe
              initialDelaySeconds: 10
              // Check every 5 seconds
              periodSeconds: 5
              // Allow more failures during startup (up to 60 seconds total)
              failureThreshold: 12
              // Single success is enough to mark as started
              successThreshold: 1
              // 3 second timeout per probe
              timeoutSeconds: 3
            }
            {
              type: 'Liveness'
              httpGet: {
                path: '/health'
                port: targetPort
                scheme: 'HTTP'
              }
              // Wait until startup probe succeeds before starting liveness probes
              initialDelaySeconds: 0
              periodSeconds: 30
              failureThreshold: 3
              successThreshold: 1
              timeoutSeconds: 5
            }
            {
              type: 'Readiness'
              httpGet: {
                path: '/health'
                port: targetPort
                scheme: 'HTTP'
              }
              initialDelaySeconds: 5
              periodSeconds: 10
              failureThreshold: 3
              successThreshold: 1
              timeoutSeconds: 3
            }
          ]
        }
      ]
      scale: {
        minReplicas: minReplicas
        maxReplicas: maxReplicas
        rules: [
          {
            name: 'http-scaling'
            http: {
              metadata: {
                concurrentRequests: '10'
              }
            }
          }
        ]
      }
    }
  }
}

output containerAppFQDN string = containerApp.properties.configuration.ingress.fqdn
output containerAppName string = containerApp.name
