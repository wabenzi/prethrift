import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import SearchResults from '../components/SearchResults'
import type { GarmentResponseV2 } from '../api/types-v2'

// Mock the API client
vi.mock('../api/client-v2', () => ({
  ApiClientV2: vi.fn().mockImplementation(() => ({
    findSimilar: vi.fn()
  }))
}))

describe('SearchResults Component', () => {
  const mockOnSimilarSearch = vi.fn()
  const mockOnFilterApply = vi.fn()

  const mockResults: GarmentResponseV2[] = [
    {
      id: 1,
      title: 'Wide-Leg Star Appliqué Jeans',
      description: 'Vintage wide-leg jeans with star appliqués',
      category: 'pants',
      price: 85.00,
      currency: 'USD',
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
      image_url: '/images/blue-jeans.jpg',
      similarity_score: 0.85
    },
    {
      id: 3,
      title: 'Summer Floral Dress',
      description: 'Light summer dress with floral pattern',
      category: 'dress',
      price: 45.00,
      currency: 'USD',
      image_url: '/images/dress.jpg',
      similarity_score: 0.73
    }
  ]

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders search results with correct count', () => {
    render(
      <SearchResults
        results={mockResults}
        searchTime={25.5}
        onSimilarSearch={mockOnSimilarSearch}
        onFilterApply={mockOnFilterApply}
      />
    )

    expect(screen.getByText(/3 results found/i)).toBeInTheDocument()
    expect(screen.getByText(/25\.5ms/i)).toBeInTheDocument()
  })

  it('displays individual search result items', () => {
    render(
      <SearchResults
        results={mockResults}
        searchTime={25.5}
        onSimilarSearch={mockOnSimilarSearch}
        onFilterApply={mockOnFilterApply}
      />
    )

    expect(screen.getByText('Wide-Leg Star Appliqué Jeans')).toBeInTheDocument()
    expect(screen.getByText('Blue Denim Classic Jeans')).toBeInTheDocument()
    expect(screen.getByText('Summer Floral Dress')).toBeInTheDocument()
  })

  it('formats prices correctly', () => {
    render(
      <SearchResults
        results={mockResults}
        searchTime={25.5}
        onSimilarSearch={mockOnSimilarSearch}
        onFilterApply={mockOnFilterApply}
      />
    )

    expect(screen.getByText('$85')).toBeInTheDocument()
    expect(screen.getByText('$65')).toBeInTheDocument()
    expect(screen.getByText('$45')).toBeInTheDocument()
  })

  it('displays similarity scores when available', () => {
    render(
      <SearchResults
        results={mockResults}
        searchTime={25.5}
        onSimilarSearch={mockOnSimilarSearch}
        onFilterApply={mockOnFilterApply}
      />
    )

    expect(screen.getByText(/92%/)).toBeInTheDocument()
    expect(screen.getByText(/85%/)).toBeInTheDocument()
    expect(screen.getByText(/73%/)).toBeInTheDocument()
  })

  it('handles similar search button clicks', async () => {
    const user = userEvent.setup()

    render(
      <SearchResults
        results={mockResults}
        searchTime={25.5}
        onSimilarSearch={mockOnSimilarSearch}
        onFilterApply={mockOnFilterApply}
      />
    )

    const similarButtons = screen.getAllByText(/find similar/i)
    await user.click(similarButtons[0])

    expect(mockOnSimilarSearch).toHaveBeenCalledWith(1)
  })

  it('handles filter clicks from result categories', async () => {
    const user = userEvent.setup()

    render(
      <SearchResults
        results={mockResults}
        searchTime={25.5}
        onSimilarSearch={mockOnSimilarSearch}
        onFilterApply={mockOnFilterApply}
      />
    )

    // Click on a category to filter
    const categoryLinks = screen.getAllByText('pants')
    await user.click(categoryLinks[0])

    expect(mockOnFilterApply).toHaveBeenCalledWith({
      categories: 'pants'
    })
  })

  it('shows empty state when no results', () => {
    render(
      <SearchResults
        results={[]}
        searchTime={15.2}
        onSimilarSearch={mockOnSimilarSearch}
        onFilterApply={mockOnFilterApply}
      />
    )

    expect(screen.getByText(/no results found/i)).toBeInTheDocument()
    expect(screen.getByText(/try different search terms/i)).toBeInTheDocument()
  })

  it('handles missing optional props gracefully', () => {
    render(
      <SearchResults
        results={mockResults}
        searchTime={25.5}
      />
    )

    // Should still render results
    expect(screen.getByText('Wide-Leg Star Appliqué Jeans')).toBeInTheDocument()

    // Similar buttons should not be clickable
    const similarButtons = screen.queryAllByText(/find similar/i)
    expect(similarButtons).toHaveLength(0)
  })

  it('shows loading state for similarity search', async () => {
    const user = userEvent.setup()

    render(
      <SearchResults
        results={mockResults}
        searchTime={25.5}
        onSimilarSearch={mockOnSimilarSearch}
        onFilterApply={mockOnFilterApply}
      />
    )

    const similarButtons = screen.getAllByText(/find similar/i)
    await user.click(similarButtons[0])

    // Should show loading state
    expect(screen.getByText(/finding similar/i)).toBeInTheDocument()
  })

  it('displays result images with proper alt text', () => {
    render(
      <SearchResults
        results={mockResults}
        searchTime={25.5}
        onSimilarSearch={mockOnSimilarSearch}
        onFilterApply={mockOnFilterApply}
      />
    )

    const images = screen.getAllByRole('img')
    expect(images).toHaveLength(3)
    expect(images[0]).toHaveAttribute('alt', 'Wide-Leg Star Appliqué Jeans')
    expect(images[1]).toHaveAttribute('alt', 'Blue Denim Classic Jeans')
    expect(images[2]).toHaveAttribute('alt', 'Summer Floral Dress')
  })

  it('handles result selection and detail view', async () => {
    const user = userEvent.setup()

    render(
      <SearchResults
        results={mockResults}
        searchTime={25.5}
        onSimilarSearch={mockOnSimilarSearch}
        onFilterApply={mockOnFilterApply}
      />
    )

    // Click on first result
    const firstResult = screen.getByText('Wide-Leg Star Appliqué Jeans')
    await user.click(firstResult)

    // Should show detail view
    expect(screen.getByText(/vintage wide-leg jeans with star appliqués/i)).toBeInTheDocument()
  })

  it('sorts results by different criteria', async () => {
    const user = userEvent.setup()

    render(
      <SearchResults
        results={mockResults}
        searchTime={25.5}
        onSimilarSearch={mockOnSimilarSearch}
        onFilterApply={mockOnFilterApply}
      />
    )

    // Should have sort dropdown
    const sortSelect = screen.getByLabelText(/sort by/i)
    await user.selectOptions(sortSelect, 'price')

    // Results should be reordered (lowest price first)
    const resultTitles = screen.getAllByTestId('result-title')
    expect(resultTitles[0]).toHaveTextContent('Summer Floral Dress') // $45
  })
})
