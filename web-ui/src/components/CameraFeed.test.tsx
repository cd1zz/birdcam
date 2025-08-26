import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import CameraFeed from './CameraFeed'

// Mock the API client
vi.mock('../api/client', () => ({
  api: {
    cameras: {
      getStream: (cameraId: number) => `/api/camera/${cameraId}/stream`,
      getSnapshot: (cameraId: number) => `/api/camera/${cameraId}/snapshot`
    }
  }
}))

const mockCameraId = 1
const mockCameraName = 'Test Camera'

describe('CameraFeed Component', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders camera feed with streaming mode by default', () => {
    render(<CameraFeed cameraId={mockCameraId} cameraName={mockCameraName} />)
    
    const img = screen.getByRole('img') as HTMLImageElement
    expect(img).toBeInTheDocument()
    expect(img.src).toContain('/api/camera/1/stream')
    expect(img.alt).toBe('Test Camera feed')
  })

  it('shows camera name', () => {
    render(<CameraFeed cameraId={mockCameraId} cameraName={mockCameraName} />)
    
    expect(screen.getByText('Test Camera')).toBeInTheDocument()
  })

  it('refreshes feed when refresh button is clicked', async () => {
    const user = userEvent.setup({ delay: null })
    render(<CameraFeed cameraId={mockCameraId} cameraName={mockCameraName} />)
    
    // Click refresh button
    const refreshButton = screen.getByTitle('Refresh feed')
    await user.click(refreshButton)
    
    // Check that loading state is shown again
    expect(screen.getByText('Loading feed...')).toBeInTheDocument()
  })

  it('shows loading state initially', () => {
    render(<CameraFeed cameraId={mockCameraId} cameraName={mockCameraName} />)
    
    expect(screen.getByText('Loading feed...')).toBeInTheDocument()
  })

  it('handles fullscreen toggle', async () => {
    const user = userEvent.setup({ delay: null })
    
    render(<CameraFeed cameraId={mockCameraId} cameraName={mockCameraName} />)
    
    const fullscreenButton = screen.getByTitle('Fullscreen')
    await user.click(fullscreenButton)
    
    // Should show fullscreen modal with two images (regular and fullscreen)
    const images = screen.getAllByRole('img', { name: `${mockCameraName} feed` })
    expect(images).toHaveLength(2)
    
    // Click to exit fullscreen (click the fullscreen button again or click outside)
    await user.click(fullscreenButton)
  })

  it('shows error message when image fails to load', async () => {
    render(<CameraFeed cameraId={mockCameraId} cameraName={mockCameraName} />)
    
    const img = screen.getByRole('img') as HTMLImageElement
    
    // Simulate image error
    fireEvent.error(img)
    
    await waitFor(() => {
      expect(screen.getByText(/Failed to load camera feed/)).toBeInTheDocument()
    })
  })

  it('handles image loading errors', async () => {
    render(<CameraFeed cameraId={mockCameraId} cameraName={mockCameraName} />)
    
    const img = screen.getByRole('img') as HTMLImageElement
    
    // Simulate image error
    fireEvent.error(img)
    
    await waitFor(() => {
      expect(screen.getByText(/failed to load camera feed/i)).toBeInTheDocument()
    })
  })

  it('clears error and shows loading when refresh is clicked after error', async () => {
    const user = userEvent.setup({ delay: null })
    render(<CameraFeed cameraId={mockCameraId} cameraName={mockCameraName} />)
    
    const img = screen.getByRole('img') as HTMLImageElement
    
    // Simulate image error
    fireEvent.error(img)
    
    await waitFor(() => {
      expect(screen.getByText(/failed to load camera feed/i)).toBeInTheDocument()
    })
    
    // Click retry button
    const retryButton = screen.getByRole('button', { name: /retry/i })
    await user.click(retryButton)
    
    // Should show image again
    expect(screen.getByRole('img')).toBeInTheDocument()
    expect(screen.queryByText(/failed to load camera feed/i)).not.toBeInTheDocument()
  })

  it('shows live status when no error', () => {
    render(<CameraFeed cameraId={mockCameraId} cameraName={mockCameraName} />)
    
    const img = screen.getByRole('img') as HTMLImageElement
    
    // Simulate successful load
    fireEvent.load(img)
    
    expect(screen.getByText('Live')).toBeInTheDocument()
  })

  it('shows offline status on error', async () => {
    render(<CameraFeed cameraId={mockCameraId} cameraName={mockCameraName} />)
    
    const img = screen.getByRole('img') as HTMLImageElement
    
    // Simulate image error
    fireEvent.error(img)
    
    await waitFor(() => {
      expect(screen.getByText('Offline')).toBeInTheDocument()
    })
  })

  it('applies custom className', () => {
    const { container } = render(<CameraFeed cameraId={mockCameraId} cameraName={mockCameraName} className="custom-class" />)
    
    const feedContainer = container.querySelector('.custom-class')
    expect(feedContainer).toBeInTheDocument()
  })
})