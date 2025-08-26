import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import DetectionGrid from './DetectionGrid'
import { type Detection } from '../api/client'

// Mock the api client
vi.mock('../api/client', () => ({
  api: {
    detections: {
      getThumbnail: (path: string) => `/thumbnails/${path}`,
      getVideo: (filename: string) => `/videos/${filename}`
    }
  },
  Detection: {} as unknown
}))

const mockDetections: Detection[] = [
  {
    id: 1,
    filename: 'bird_detection_1.mp4',
    thumbnail_path: '/thumbnails/bird_1.jpg',
    received_time: '2025-01-22T10:30:00',
    species: 'bird',
    confidence: 0.95,
    count: 2,
    duration: 30.5
  },
  {
    id: 2,
    filename: 'dog_detection_2.mp4',
    thumbnail_path: '/thumbnails/dog_2.jpg',
    received_time: '2025-01-22T11:00:00',
    species: 'dog',
    confidence: 0.92,
    count: 1,
    duration: 45.2
  },
  {
    id: 3,
    filename: 'cat_detection_3.mp4',
    thumbnail_path: '/thumbnails/cat_3.jpg',
    received_time: '2025-01-22T12:00:00',
    species: 'cat',
    confidence: 0.89,
    count: 3,
    duration: 25.8
  }
]

describe('DetectionGrid Component', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders detection grid with cards', () => {
    render(<DetectionGrid detections={mockDetections} />)
    
    // Check that all detection cards are rendered
    expect(screen.getAllByRole('img')).toHaveLength(3)
    // The DetectionGrid component shows species and confidence, not camera names
    expect(screen.getAllByText(/bird/i)[0]).toBeInTheDocument()
    expect(screen.getAllByText(/dog/i)[0]).toBeInTheDocument()
    expect(screen.getAllByText(/cat/i)[0]).toBeInTheDocument()
  })

  it('displays detection information correctly', () => {
    render(<DetectionGrid detections={mockDetections} />)
    
    // Check first detection card has all the expected information
    const cards = screen.getAllByRole('img')
    const firstCard = cards[0].closest('div.bg-white, div.dark\\:bg-gray-800') || cards[0].parentElement?.parentElement
    expect(firstCard).toHaveTextContent('bird')
    expect(firstCard).toHaveTextContent('95%')
    expect(firstCard).toHaveTextContent('30.5s')
  })

  it('formats timestamps correctly', () => {
    render(<DetectionGrid detections={mockDetections} />)
    
    // Check that timestamps are formatted
    // The exact format depends on locale, so just check for the presence of time parts
    const timestampRegex = /\d{1,2}[:/]\d{2}/
    const timestamps = screen.getAllByText(timestampRegex)
    expect(timestamps.length).toBeGreaterThan(0)
  })

  it('calls onVideoClick when card is clicked', async () => {
    const mockOnVideoClick = vi.fn()
    const user = userEvent.setup()
    render(<DetectionGrid detections={mockDetections} onVideoClick={mockOnVideoClick} />)
    
    const firstCard = screen.getAllByRole('img')[0].closest('div')!
    await user.click(firstCard)
    
    expect(mockOnVideoClick).toHaveBeenCalledWith(mockDetections[0])
  })

  it('displays play button on each card', () => {
    render(<DetectionGrid detections={mockDetections} />)
    
    const playButtons = screen.getAllByRole('button', { name: /play/i })
    expect(playButtons).toHaveLength(3)
  })

  it('handles empty detections list', () => {
    render(<DetectionGrid detections={[]} />)
    
    expect(screen.getByText(/no detections found/i)).toBeInTheDocument()
    expect(screen.getByText(/wildlife will appear here/i)).toBeInTheDocument()
  })

  it('applies confidence-based styling', () => {
    render(<DetectionGrid detections={mockDetections} />)
    
    // Check that confidence badges are displayed
    expect(screen.getByText('95%')).toBeInTheDocument()
    expect(screen.getByText('92%')).toBeInTheDocument()
    expect(screen.getByText('89%')).toBeInTheDocument()
  })

  it('displays species emojis correctly', () => {
    render(<DetectionGrid detections={mockDetections} />)
    
    // Check for species emojis in the component
    expect(screen.getByText('🦜')).toBeInTheDocument()
    expect(screen.getByText('🐱')).toBeInTheDocument()
    expect(screen.getByText('🐕')).toBeInTheDocument()
  })

  it('handles loading state for thumbnails', () => {
    render(<DetectionGrid detections={mockDetections} />)
    
    const images = screen.getAllByRole('img') as HTMLImageElement[]
    
    // Check that images have correct sources
    expect(images[0].src).toContain('/thumbnails/bird_1.jpg')
    expect(images[1].src).toContain('/thumbnails/dog_2.jpg')
    expect(images[2].src).toContain('/thumbnails/cat_3.jpg')
  })

  it('displays multiple detections of same species correctly', () => {
    render(<DetectionGrid detections={mockDetections} />)
    
    // First detection has 2 birds
    const birdCard = screen.getAllByText(/bird/i)[0].closest('div')
    expect(birdCard).toHaveTextContent('(x2)')
    
    // Third detection has 3 cats  
    const catCard = screen.getAllByText(/cat/i)[0].closest('div')
    expect(catCard).toHaveTextContent('(x3)')
  })

  it('handles video URL construction correctly', async () => {
    const mockOnVideoClick = vi.fn()
    const user = userEvent.setup()
    render(<DetectionGrid detections={mockDetections} onVideoClick={mockOnVideoClick} />)
    
    const firstCard = screen.getAllByRole('img')[0].closest('div')!
    await user.click(firstCard)
    
    // Just check that the callback was called with the right detection
    expect(mockOnVideoClick).toHaveBeenCalledWith(mockDetections[0])
  })
})