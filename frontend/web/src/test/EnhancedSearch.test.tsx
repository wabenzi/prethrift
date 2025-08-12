import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import EnhancedSearch from '../components/EnhancedSearch'
import type { GarmentResponseV2 } from '../api/types-v2'

// Mock the API client
vi.mock('../api/client-v2', () => ({
  ApiClientV2: vi.fn().mockImplementation(() => ({
    searchText: vi.fn(),
    searchImage: vi.fn(),
    searchHybrid: vi.fn(),
    getSuggestions: vi.fn(),
    getFilterOptions: vi.fn()
  }))
}))

describe('EnhancedSearch Component', () => {
  const mockOnSearchResults = vi.fn()
  const mockOnSearchError = vi.fn()

  const mockResults: GarmentResponseV2[] = [
    {
      id: 1,
      title: 'Wide-Leg Star Appliqué Jeans',
      description: 'Vintage wide-leg jeans with star appliqués',
      category: 'pants',
      price: 85.00,
      currency: 'USD',
      confidence: 0.95,
      image_url: '/images/jeans.jpg',
      similarity_score: 0.92
    },
    {
      id: 2,
      title: 'Blue Denim Classic Jeans',
      description: 'Classic blue denim jeans',
      category: 'pants',
      price: 65.00,
      currency: 'USD',
      confidence: 0.78,
      image_url: '/images/blue-jeans.jpg',
      similarity_score: 0.85
    }
  ]

  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renders search input with placeholder text', () => {
    render(
      <EnhancedSearch
        onSearchResults={mockOnSearchResults}
        onSearchError={mockOnSearchError}
      />
    )

    expect(screen.getByPlaceholderText(/search for vintage clothes/i)).toBeInTheDocument()
  })

  it('handles text input changes', async () => {
    const user = userEvent.setup()

    render(
      <EnhancedSearch
        onSearchResults={mockOnSearchResults}
        onSearchError={mockOnSearchError}
      />
    )

    const searchInput = screen.getByPlaceholderText(/search for vintage clothes/i)
    await user.type(searchInput, 'blue jeans')

    expect(searchInput).toHaveValue('blue jeans')
  })

  it('submits search when enter is pressed', async () => {
    const user = userEvent.setup()

    render(
      <EnhancedSearch
        onSearchResults={mockOnSearchResults}
        onSearchError={mockOnSearchError}
      />
    )

    const searchInput = screen.getByPlaceholderText(/search for vintage clothes/i)
    await user.type(searchInput, 'blue jeans{enter}')

    // Should trigger search
    expect(mockOnSearchResults).toHaveBeenCalled()
  })

  it('shows loading state during search', async () => {
    const user = userEvent.setup()

    render(
      <EnhancedSearch
        onSearchResults={mockOnSearchResults}
        onSearchError={mockOnSearchError}
      />
    )

    const searchInput = screen.getByPlaceholderText(/search for vintage clothes/i)
    const searchButton = screen.getByRole('button', { name: /search/i })

    await user.type(searchInput, 'blue jeans')
    await user.click(searchButton)

    // Should show loading indicator
    expect(screen.getByRole('button', { name: /searching/i })).toBeInTheDocument()
  })

  it('switches between search types', async () => {
    const user = userEvent.setup()

    render(
      <EnhancedSearch
        onSearchResults={mockOnSearchResults}
        onSearchError={mockOnSearchError}
      />
    )

    // Should start with text search
    expect(screen.getByDisplayValue('text')).toBeChecked()

    // Switch to image search
    const imageRadio = screen.getByDisplayValue('image')
    await user.click(imageRadio)

    expect(imageRadio).toBeChecked()
    expect(screen.getByText(/upload an image/i)).toBeInTheDocument()
  })

  it('toggles filter panel', async () => {
    const user = userEvent.setup()

    render(
      <EnhancedSearch
        onSearchResults={mockOnSearchResults}
        onSearchError={mockOnSearchError}
      />
    )

    const filtersButton = screen.getByRole('button', { name: /filters/i })
    await user.click(filtersButton)

    expect(screen.getByText(/categories/i)).toBeInTheDocument()
    expect(screen.getByText(/brands/i)).toBeInTheDocument()
  })

  it('applies filters correctly', async () => {
    const user = userEvent.setup()

    render(
      <EnhancedSearch
        onSearchResults={mockOnSearchResults}
        onSearchError={mockOnSearchError}
      />
    )

    // Open filters
    const filtersButton = screen.getByRole('button', { name: /filters/i })
    await user.click(filtersButton)

    // Apply a category filter
    const categorySelect = screen.getByLabelText(/category/i)
    await user.selectOptions(categorySelect, 'pants')

    // Search with filters
    const searchInput = screen.getByPlaceholderText(/search for vintage clothes/i)
    await user.type(searchInput, 'jeans{enter}')

    // Should call search with filters
    expect(mockOnSearchResults).toHaveBeenCalled()
  })

  it('handles search errors gracefully', async () => {
    const user = userEvent.setup()

    // Mock API error
    const mockApiClient = await import('../api/client-v2')
    vi.mocked(mockApiClient.ApiClientV2).mockImplementation(() => ({
      searchText: vi.fn().mockRejectedValue(new Error('Search failed')),
      searchImage: vi.fn(),
      searchHybrid: vi.fn(),
      getSuggestions: vi.fn(),
      getFilterOptions: vi.fn()
    }))

    render(
      <EnhancedSearch
        onSearchResults={mockOnSearchResults}
        onSearchError={mockOnSearchError}
      />
    )

    const searchInput = screen.getByPlaceholderText(/search for vintage clothes/i)
    await user.type(searchInput, 'test query{enter}')

    await waitFor(() => {
      expect(mockOnSearchError).toHaveBeenCalledWith(expect.stringContaining('Search failed'))
    })
  })

  it('displays search suggestions', async () => {
    const user = userEvent.setup()

    // Mock suggestions
    const mockApiClient = await import('../api/client-v2')
    vi.mocked(mockApiClient.ApiClientV2).mockImplementation(() => ({
      searchText: vi.fn(),
      searchImage: vi.fn(),
      searchHybrid: vi.fn(),
      getSuggestions: vi.fn().mockResolvedValue(['blue jeans', 'blue dress', 'blue shirt']),
      getFilterOptions: vi.fn()
    }))

    render(
      <EnhancedSearch
        onSearchResults={mockOnSearchResults}
        onSearchError={mockOnSearchError}
      />
    )

    const searchInput = screen.getByPlaceholderText(/search for vintage clothes/i)
    await user.type(searchInput, 'blue')

    await waitFor(() => {
      expect(screen.getByText('blue jeans')).toBeInTheDocument()
      expect(screen.getByText('blue dress')).toBeInTheDocument()
    })
  })

  it('accepts initial query prop', () => {
    render(
      <EnhancedSearch
        onSearchResults={mockOnSearchResults}
        onSearchError={mockOnSearchError}
        initialQuery="vintage denim"
      />
    )

    expect(screen.getByDisplayValue('vintage denim')).toBeInTheDocument()
  })

  it('clears search results when query is empty', async () => {
    const user = userEvent.setup()

    render(
      <EnhancedSearch
        onSearchResults={mockOnSearchResults}
        onSearchError={mockOnSearchError}
        initialQuery="test"
      />
    )

    const searchInput = screen.getByDisplayValue('test')
    await user.clear(searchInput)

    expect(mockOnSearchResults).toHaveBeenCalledWith([], 0)
  })
})
