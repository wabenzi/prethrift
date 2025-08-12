import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ImageUpload from '../components/ImageUpload'

describe('ImageUpload Component', () => {
  const mockOnImageSelect = vi.fn()
  const mockOnImageRemove = vi.fn()

  const createMockFile = (name: string, type: string = 'image/jpeg', size: number = 1024): File => {
    const content = 'mock image content'.repeat(size / 18) // Approximate size
    return new File([content], name, { type })
  }

  beforeEach(() => {
    vi.clearAllMocks()

    // Mock FileReader
    const mockFileReader = {
      readAsDataURL: vi.fn(),
      result: 'data:image/jpeg;base64,mockbase64data',
      onload: null as ((event: any) => void) | null
    }

    vi.spyOn(window, 'FileReader').mockImplementation(() => mockFileReader as any)

    // Auto-trigger onload when readAsDataURL is called
    mockFileReader.readAsDataURL.mockImplementation(() => {
      if (mockFileReader.onload) {
        mockFileReader.onload({ target: mockFileReader } as any)
      }
    })
  })

  it('renders upload area with correct text', () => {
    render(
      <ImageUpload
        onImageSelect={mockOnImageSelect}
        onImageRemove={mockOnImageRemove}
      />
    )

    expect(screen.getByText(/drag and drop an image/i)).toBeInTheDocument()
    expect(screen.getByText(/or click to browse/i)).toBeInTheDocument()
  })

  it('handles file selection via input', async () => {
    const user = userEvent.setup()
    const mockFile = createMockFile('test-image.jpg')

    render(
      <ImageUpload
        onImageSelect={mockOnImageSelect}
        onImageRemove={mockOnImageRemove}
      />
    )

    const fileInput = screen.getByLabelText(/choose image file/i)
    await user.upload(fileInput, mockFile)

    expect(mockOnImageSelect).toHaveBeenCalledWith(
      mockFile,
      'data:image/jpeg;base64,mockbase64data'
    )
  })

  it('validates file type correctly', async () => {
    const user = userEvent.setup()
    const invalidFile = new File(['content'], 'test.txt', { type: 'text/plain' })

    render(
      <ImageUpload
        onImageSelect={mockOnImageSelect}
        onImageRemove={mockOnImageRemove}
      />
    )

    const fileInput = screen.getByLabelText(/choose image file/i)
    await user.upload(fileInput, invalidFile)

    expect(screen.getByText(/please select an image file/i)).toBeInTheDocument()
    expect(mockOnImageSelect).not.toHaveBeenCalled()
  })

  it('validates file size correctly', async () => {
    const user = userEvent.setup()
    const largeFile = createMockFile('large-image.jpg', 'image/jpeg', 11 * 1024 * 1024) // 11MB

    render(
      <ImageUpload
        onImageSelect={mockOnImageSelect}
        onImageRemove={mockOnImageRemove}
        maxSizeMB={10}
      />
    )

    const fileInput = screen.getByLabelText(/choose image file/i)
    await user.upload(fileInput, largeFile)

    expect(screen.getByText(/file size must be less than 10mb/i)).toBeInTheDocument()
    expect(mockOnImageSelect).not.toHaveBeenCalled()
  })

  it('handles drag and drop events', () => {
    const mockFile = createMockFile('dropped-image.jpg')

    render(
      <ImageUpload
        onImageSelect={mockOnImageSelect}
        onImageRemove={mockOnImageRemove}
      />
    )

    const dropZone = screen.getByText(/drag and drop an image/i).closest('div')

    // Simulate drag over
    fireEvent.dragOver(dropZone!, {
      dataTransfer: { files: [mockFile] }
    })

    expect(dropZone).toHaveClass('drag-over') // Assuming this class is added

    // Simulate drop
    fireEvent.drop(dropZone!, {
      dataTransfer: { files: [mockFile] }
    })

    expect(mockOnImageSelect).toHaveBeenCalledWith(
      mockFile,
      'data:image/jpeg;base64,mockbase64data'
    )
  })

  it('displays current image when provided', () => {
    const currentImageUrl = 'https://example.com/current-image.jpg'

    render(
      <ImageUpload
        onImageSelect={mockOnImageSelect}
        onImageRemove={mockOnImageRemove}
        currentImage={currentImageUrl}
      />
    )

    const currentImage = screen.getByRole('img')
    expect(currentImage).toHaveAttribute('src', currentImageUrl)
  })

  it('handles image removal', async () => {
    const user = userEvent.setup()
    const currentImageUrl = 'https://example.com/current-image.jpg'

    render(
      <ImageUpload
        onImageSelect={mockOnImageSelect}
        onImageRemove={mockOnImageRemove}
        currentImage={currentImageUrl}
      />
    )

    const removeButton = screen.getByRole('button', { name: /remove image/i })
    await user.click(removeButton)

    expect(mockOnImageRemove).toHaveBeenCalled()
  })

  it('respects disabled state', () => {
    render(
      <ImageUpload
        onImageSelect={mockOnImageSelect}
        onImageRemove={mockOnImageRemove}
        disabled={true}
      />
    )

    const fileInput = screen.getByLabelText(/choose image file/i)
    expect(fileInput).toBeDisabled()
  })

  it('accepts custom file types', () => {
    render(
      <ImageUpload
        onImageSelect={mockOnImageSelect}
        onImageRemove={mockOnImageRemove}
        accept="image/png,image/gif"
      />
    )

    const fileInput = screen.getByLabelText(/choose image file/i)
    expect(fileInput).toHaveAttribute('accept', 'image/png,image/gif')
  })

  it('shows upload progress indicator', async () => {
    const user = userEvent.setup()
    const mockFile = createMockFile('test-image.jpg')

    // Mock FileReader with delayed onload
    const mockFileReader = {
      readAsDataURL: vi.fn(),
      result: 'data:image/jpeg;base64,mockbase64data',
      onload: null as ((event: any) => void) | null
    }

    vi.spyOn(window, 'FileReader').mockImplementation(() => mockFileReader as any)

    render(
      <ImageUpload
        onImageSelect={mockOnImageSelect}
        onImageRemove={mockOnImageRemove}
      />
    )

    const fileInput = screen.getByLabelText(/choose image file/i)
    await user.upload(fileInput, mockFile)

    // Should show processing state before FileReader finishes
    expect(screen.getByText(/processing image/i)).toBeInTheDocument()

    // Trigger FileReader completion
    if (mockFileReader.onload) {
      mockFileReader.onload({ target: mockFileReader } as any)
    }

    expect(mockOnImageSelect).toHaveBeenCalled()
  })

  it('clears error messages on successful upload', async () => {
    const user = userEvent.setup()

    render(
      <ImageUpload
        onImageSelect={mockOnImageSelect}
        onImageRemove={mockOnImageRemove}
      />
    )

    const fileInput = screen.getByLabelText(/choose image file/i)

    // First, upload invalid file to show error
    const invalidFile = new File(['content'], 'test.txt', { type: 'text/plain' })
    await user.upload(fileInput, invalidFile)

    expect(screen.getByText(/please select an image file/i)).toBeInTheDocument()

    // Then upload valid file
    const validFile = createMockFile('test-image.jpg')
    await user.upload(fileInput, validFile)

    expect(screen.queryByText(/please select an image file/i)).not.toBeInTheDocument()
  })
})
