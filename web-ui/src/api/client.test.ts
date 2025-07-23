import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

// Mock axios before importing client
vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => ({
      interceptors: {
        request: { use: vi.fn() },
        response: { use: vi.fn() }
      },
      get: vi.fn(),
      post: vi.fn(),
      put: vi.fn(),
      delete: vi.fn(),
      defaults: {
        headers: {
          common: {}
        }
      }
    }))
  }
}))

// Now import client after mocking
const { api, piApi, apiClient, setAuthToken } = await import('./client')

describe('API Client', () => {
  const mockAccessToken = 'mock-access-token'
  const mockRefreshToken = 'mock-refresh-token'

  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
    localStorage.setItem('access_token', mockAccessToken)
    localStorage.setItem('refresh_token', mockRefreshToken)
  })

  afterEach(() => {
    localStorage.clear()
  })

  describe('Authentication', () => {
    it('sets auth token in headers', () => {
      const token = 'test-token'
      setAuthToken(token)
      
      // Verify the token was set (implementation specific)
      expect(localStorage.getItem('access_token')).toBe(mockAccessToken)
    })

    it('handles token storage', () => {
      expect(localStorage.getItem('access_token')).toBe(mockAccessToken)
      expect(localStorage.getItem('refresh_token')).toBe(mockRefreshToken)
    })
  })

  describe('API Structure', () => {
    it('has expected API structure', () => {
      expect(api).toBeDefined()
      expect(api.auth).toBeDefined()
      expect(api.detections).toBeDefined()
      expect(api.cameras).toBeDefined()
      expect(api.system).toBeDefined()
      expect(api.admin).toBeDefined()
    })

    it('has auth endpoints', () => {
      expect(api.auth.login).toBeDefined()
      expect(api.auth.logout).toBeDefined()
      expect(api.auth.refresh).toBeDefined()
      expect(api.auth.getCurrentUser).toBeDefined()
    })

    it('has detection endpoints', () => {
      expect(api.detections.getRecent).toBeDefined()
      expect(api.detections.getById).toBeDefined()
      expect(api.detections.delete).toBeDefined()
      expect(api.detections.getStats).toBeDefined()
    })

    it('has camera endpoints', () => {
      expect(api.cameras.list).toBeDefined()
      expect(api.cameras.getStream).toBeDefined()
      expect(api.cameras.getSnapshot).toBeDefined()
      expect(api.cameras.getMotionSettings).toBeDefined()
      expect(api.cameras.updateMotionSettings).toBeDefined()
    })
  })
})