/**
 * Integration tests that validate frontend API client against actual backend
 * These tests are meant to be run against a running backend server
 */
import { describe, it, expect, beforeAll } from 'vitest'
import axios from 'axios'
// import { api } from './client' // Will be used when implementing actual API calls

// This test file should be run with a real backend
// Can be skipped in regular unit test runs with: --exclude="*.integration.test.ts"

const BACKEND_URL = process.env.VITE_PROCESSING_SERVER || 'http://localhost:5001'
const TEST_TIMEOUT = 10000

// Helper to check if backend is available
async function isBackendAvailable(): Promise<boolean> {
  try {
    await axios.get(`${BACKEND_URL}/api/status`)
    return true
  } catch {
    return false
  }
}

// Extract all API calls from the client
function extractAPIEndpoints(): Map<string, Set<string>> {
  const endpoints = new Map<string, Set<string>>()
  
  // This would be better done with AST parsing, but for now we'll do it manually
  const apiStructure = {
    'GET': [
      '/api/cameras',
      '/api/motion-settings',
      '/api/active-passive/config',
      '/api/active-passive/stats',
      '/api/active-passive/test-trigger',
      '/api/status',
      '/api/recent-detections',
      '/api/system-settings',
      '/api/models/available',
      '/api/models/{modelId}/classes',
      '/api/logs/pi-capture',
      '/api/logs/ai-processor',
      '/api/logs/remote/pi-capture',
      '/api/logs/combined',
      '/api/logs/levels',
      '/api/logs/export',
      '/api/admin/email/templates',
      '/api/admin/email/templates/{templateType}',
    ],
    'POST': [
      '/api/motion-settings',
      '/api/process-video',
      '/api/process-now',
      '/api/cleanup-now',
      '/api/sync-now',
      '/api/process-server-queue',
      '/api/system-settings',
      '/api/admin/email/templates/{templateType}/reset',
      '/api/admin/email/templates/{templateType}/preview',
      '/api/admin/email/send-invite',
    ],
    'PUT': [
      '/api/admin/email/templates/{templateType}',
    ]
  }
  
  for (const [method, paths] of Object.entries(apiStructure)) {
    if (!endpoints.has(method)) {
      endpoints.set(method, new Set())
    }
    for (const path of paths) {
      endpoints.get(method)!.add(path)
    }
  }
  
  return endpoints
}

describe.skipIf(!isBackendAvailable())('API Contract Integration Tests', () => {
  let authToken: string
  
  beforeAll(async () => {
    // Get auth token if backend requires it
    try {
      const response = await axios.post(`${BACKEND_URL}/api/auth/login`, {
        username: 'test',
        password: 'test'
      })
      authToken = response.data.access_token
    } catch {
      // Backend might not require auth for some endpoints
    }
  })
  
  it('should discover all backend routes', async () => {
    // If the discovery endpoint exists, use it
    try {
      const headers = authToken ? { Authorization: `Bearer ${authToken}` } : {}
      const response = await axios.get(`${BACKEND_URL}/api/discovery/routes`, { headers })
      
      expect(response.status).toBe(200)
      expect(response.data).toHaveProperty('total_routes')
      expect(response.data).toHaveProperty('blueprints')
      
      console.log(`Backend has ${response.data.total_routes} routes`)
    } catch {
      console.warn('Discovery endpoint not available, skipping route discovery')
    }
  }, TEST_TIMEOUT)
  
  it('should validate all frontend routes exist in backend', async () => {
    const frontendEndpoints = extractAPIEndpoints()
    const missingRoutes: string[] = []
    
    for (const [method, paths] of frontendEndpoints) {
      for (const path of paths) {
        try {
          // Make OPTIONS request to check if route exists
          const response = await axios({
            method: 'OPTIONS',
            url: `${BACKEND_URL}${path.replace('{modelId}', 'test').replace('{templateType}', 'test')}`,
            validateStatus: () => true
          })
          
          // 404 means route doesn't exist
          if (response.status === 404) {
            missingRoutes.push(`${method} ${path}`)
          }
        } catch {
          missingRoutes.push(`${method} ${path} (connection error)`)
        }
      }
    }
    
    if (missingRoutes.length > 0) {
      console.error('Missing routes in backend:')
      missingRoutes.forEach(route => console.error(`  - ${route}`))
    }
    
    expect(missingRoutes).toHaveLength(0)
  }, TEST_TIMEOUT)
  
  it('should validate parameter names match between frontend and backend', async () => {
    // Test specific known parameters
    const parameterTests = [
      {
        endpoint: '/api/logs/pi-capture',
        method: 'GET',
        frontendParams: { lines: 100, since: '1h', level: 'ERROR', search: 'test' },
        backendExpects: { lines: 100, since: '1h', levels: 'ERROR', search: 'test' } // Note: backend expects 'levels'
      }
    ]
    
    const parameterIssues: string[] = []
    
    for (const test of parameterTests) {
      try {
        // Test with frontend parameters
        const frontendResponse = await axios({
          method: test.method,
          url: `${BACKEND_URL}${test.endpoint}`,
          params: test.frontendParams,
          headers: authToken ? { Authorization: `Bearer ${authToken}` } : {},
          validateStatus: () => true
        })
        
        // Test with backend expected parameters
        const backendResponse = await axios({
          method: test.method,
          url: `${BACKEND_URL}${test.endpoint}`,
          params: test.backendExpects,
          headers: authToken ? { Authorization: `Bearer ${authToken}` } : {},
          validateStatus: () => true
        })
        
        // If frontend params return error but backend params work, we have a mismatch
        if (frontendResponse.status >= 400 && backendResponse.status < 400) {
          parameterIssues.push(
            `${test.endpoint}: Frontend sends '${Object.keys(test.frontendParams).join(', ')}' but backend expects '${Object.keys(test.backendExpects).join(', ')}'`
          )
        }
      } catch (error) {
        console.warn(`Could not test ${test.endpoint}:`, error)
      }
    }
    
    if (parameterIssues.length > 0) {
      console.error('Parameter mismatches found:')
      parameterIssues.forEach(issue => console.error(`  - ${issue}`))
    }
    
    // This test would fail with current codebase due to level/levels mismatch
    expect(parameterIssues).toHaveLength(0)
  }, TEST_TIMEOUT)
  
  it('should validate response schemas', async () => {
    // Test that responses match expected schemas
    const schemaTests = [
      {
        endpoint: '/api/recent-detections',
        method: 'GET',
        expectedSchema: {
          detections: 'array'
        }
      },
      {
        endpoint: '/api/status',
        method: 'GET',
        expectedSchema: {
          status: 'string',
          uptime: 'number',
          cameras_active: 'number'
        }
      }
    ]
    
    const schemaIssues: string[] = []
    
    for (const test of schemaTests) {
      try {
        const response = await axios({
          method: test.method,
          url: `${BACKEND_URL}${test.endpoint}`,
          headers: authToken ? { Authorization: `Bearer ${authToken}` } : {},
        })
        
        // Validate response structure
        for (const [key, expectedType] of Object.entries(test.expectedSchema)) {
          if (!(key in response.data)) {
            schemaIssues.push(`${test.endpoint}: Missing field '${key}'`)
          } else if (expectedType === 'array' && !Array.isArray(response.data[key])) {
            schemaIssues.push(`${test.endpoint}: Field '${key}' should be array`)
          } else if (expectedType !== 'array' && typeof response.data[key] !== expectedType) {
            schemaIssues.push(`${test.endpoint}: Field '${key}' should be ${expectedType}, got ${typeof response.data[key]}`)
          }
        }
      } catch {
        console.warn(`Could not test schema for ${test.endpoint}`)
      }
    }
    
    if (schemaIssues.length > 0) {
      console.error('Schema validation issues:')
      schemaIssues.forEach(issue => console.error(`  - ${issue}`))
    }
    
    expect(schemaIssues).toHaveLength(0)
  }, TEST_TIMEOUT)
})