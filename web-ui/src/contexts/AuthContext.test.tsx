import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act, waitFor } from '@testing-library/react'
import { AuthProvider, useAuth } from './AuthContext'
import { apiClient } from '../api/client'
import { type ReactNode } from 'react'

// Mock the API client
vi.mock('../api/client', () => ({
  apiClient: {
    post: vi.fn(),
    get: vi.fn(),
  },
  setAuthToken: vi.fn(),
}))

const wrapper = ({ children }: { children: ReactNode }) => (
  <AuthProvider>{children}</AuthProvider>
)

describe('AuthContext', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
    vi.useRealTimers()
  })

  it('provides authentication context', () => {
    const { result } = renderHook(() => useAuth(), { wrapper })
    expect(result.current).toBeDefined()
    expect(result.current.user).toBeNull()
    expect(result.current.isAuthenticated).toBe(false)
  })

  it('handles successful login', async () => {
    const mockUser = { id: 1, username: 'testuser', role: 'viewer', email: 'test@example.com' }
    const mockTokens = { 
      access_token: 'mock-access-token', 
      refresh_token: 'mock-refresh-token' 
    }
    
    vi.mocked(apiClient.post).mockResolvedValueOnce({ 
      data: { user: mockUser, ...mockTokens } 
    })

    const { result } = renderHook(() => useAuth(), { wrapper })

    await act(async () => {
      await result.current.login('testuser', 'password')
    })

    await waitFor(() => {
      expect(result.current.isAuthenticated).toBe(true)
      expect(result.current.user).toEqual(mockUser)
    })

    expect(localStorage.getItem('accessToken')).toBe(mockTokens.access_token)
    expect(localStorage.getItem('refreshToken')).toBe(mockTokens.refresh_token)
  })

  it('handles login failure', async () => {
    vi.mocked(apiClient.post).mockRejectedValueOnce(new Error('Invalid credentials'))

    const { result } = renderHook(() => useAuth(), { wrapper })

    await expect(act(async () => {
      await result.current.login('testuser', 'wrongpassword')
    })).rejects.toThrow('Invalid credentials')

    expect(result.current.isAuthenticated).toBe(false)
    expect(result.current.user).toBeNull()
    expect(localStorage.getItem('accessToken')).toBeNull()
  })

  it('handles logout', async () => {
    // Setup: Login first
    const mockUser = { id: 1, username: 'testuser', role: 'viewer', email: 'test@example.com' }
    localStorage.setItem('accessToken', 'mock-token')
    localStorage.setItem('refreshToken', 'mock-refresh')
    
    vi.mocked(apiClient.get).mockResolvedValueOnce({ data: mockUser })

    const { result } = renderHook(() => useAuth(), { wrapper })

    // Wait for initial load
    await waitFor(() => {
      expect(result.current.user).toEqual(mockUser)
    })

    // Logout
    await act(async () => {
      await result.current.logout()
    })

    expect(result.current.isAuthenticated).toBe(false)
    expect(result.current.user).toBeNull()
    expect(localStorage.getItem('accessToken')).toBeNull()
    expect(localStorage.getItem('refreshToken')).toBeNull()
  })

  it.skip('automatically refreshes token', async () => {
    const mockUser = { id: 1, username: 'testuser', role: 'viewer', email: 'test@example.com' }
    const newTokens = { 
      access_token: 'new-access-token', 
      refresh_token: 'new-refresh-token' 
    }
    
    localStorage.setItem('accessToken', 'old-token')
    localStorage.setItem('refreshToken', 'old-refresh')
    
    vi.mocked(apiClient.get).mockResolvedValueOnce({ data: mockUser })
    vi.mocked(apiClient.post).mockResolvedValueOnce({ data: newTokens })

    const { result } = renderHook(() => useAuth(), { wrapper })

    // Wait for initial load
    await waitFor(() => {
      expect(result.current.user).toEqual(mockUser)
    })

    // Fast-forward time to trigger refresh (20 minutes)
    vi.useFakeTimers()
    act(() => {
      vi.advanceTimersByTime(20 * 60 * 1000)
    })

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith('/api/auth/refresh', {
        refresh_token: 'old-refresh'
      })
      expect(localStorage.getItem('accessToken')).toBe(newTokens.access_token)
    })

    vi.useRealTimers()
  })

  it.skip('checks user role from user object', async () => {
    const adminUser = { id: 1, username: 'admin', role: 'admin', email: 'admin@example.com' }
    localStorage.setItem('accessToken', 'mock-token')
    
    vi.mocked(apiClient.get).mockResolvedValueOnce({ data: adminUser })

    const { result } = renderHook(() => useAuth(), { wrapper })

    await waitFor(() => {
      expect(result.current.user).toEqual(adminUser)
    })

    expect(result.current.user?.role).toBe('admin')
    expect(result.current.user?.role === 'admin').toBe(true)
  })
})