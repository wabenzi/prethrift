import React, { useState, useEffect, useRef, useCallback } from 'react';
import type { SearchFilters, SearchRequestV2, GarmentResponseV2 } from '../api/types-v2';
import { ApiClientV2 } from '../api/client-v2';

interface EnhancedSearchProps {
  onSearchResults: (results: GarmentResponseV2[], searchTime: number) => void;
  onSearchError: (error: string) => void;
  initialQuery?: string;
}

interface FilterOptions {
  categories: string[];
  brands: string[];
  colors: string[];
  materials: string[];
  styles: string[];
  seasons: string[];
  occasions: string[];
  designer_tiers: string[];
}

const apiClient = new ApiClientV2();

export default function EnhancedSearch({
  onSearchResults,
  onSearchError,
  initialQuery = ''
}: EnhancedSearchProps) {
  // Search state
  const [query, setQuery] = useState(initialQuery);
  const [searchType, setSearchType] = useState<'text' | 'image' | 'hybrid'>('text');
  const [isSearching, setIsSearching] = useState(false);
  const [selectedImage, setSelectedImage] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);

  // Filter state
  const [showFilters, setShowFilters] = useState(false);
  const [activeFilters, setActiveFilters] = useState<SearchFilters>({});
  const [filterOptions, setFilterOptions] = useState<FilterOptions | null>(null);

  // Advanced options
  const [minSimilarity, setMinSimilarity] = useState(0.6);
  const [sortBy, setSortBy] = useState<'similarity' | 'price' | 'relevance'>('relevance');
  const [limit, setLimit] = useState(20);

  // Suggestions
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const searchTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Load filter options on component mount
  useEffect(() => {
    void loadFilterOptions();
  }, []);

  // Debounced suggestions
  const loadSuggestions = useCallback(async () => {
    try {
      const suggestions = await apiClient.getSuggestions(query, 5);
      setSuggestions(suggestions);
      setShowSuggestions(suggestions.length > 0);
    } catch (error) {
      console.error('Failed to load suggestions:', error);
    }
  }, [query]);

  useEffect(() => {
    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current);
    }

    if (query.length > 2) {
      searchTimeoutRef.current = setTimeout(() => {
        void loadSuggestions();
      }, 300);
    } else {
      setSuggestions([]);
      setShowSuggestions(false);
    }

    return () => {
      if (searchTimeoutRef.current) {
        clearTimeout(searchTimeoutRef.current);
      }
    };
  }, [query, loadSuggestions]);

  const loadFilterOptions = async () => {
    try {
      const options = await apiClient.getFilterOptions();
      setFilterOptions(options);
    } catch (error) {
      console.error('Failed to load filter options:', error);
    }
  };

  const handleImageSelect = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      setSelectedImage(file);

      // Create preview
      const reader = new FileReader();
      reader.onload = (e) => {
        setImagePreview(e.target?.result as string);
      };
      reader.readAsDataURL(file);

      // Switch to image or hybrid search
      if (searchType === 'text') {
        setSearchType(query ? 'hybrid' : 'image');
      }
    }
  }, [searchType, query]);

  const handleSearch = async () => {
    if (!query.trim() && !selectedImage) return;

    setIsSearching(true);
    setShowSuggestions(false);

    try {
      let imageQuery: string | undefined;

      // Upload image if selected
      if (selectedImage) {
        const uploadResult = await apiClient.uploadImage(selectedImage);
        imageQuery = uploadResult.image_url;
      }

      const searchRequest: SearchRequestV2 = {
        search_type: searchType,
        text_query: query.trim() || undefined,
        image_query: imageQuery,
        filters: Object.keys(activeFilters).length > 0 ? activeFilters : undefined,
        limit,
        min_similarity: minSimilarity,
        sort_by: sortBy,
        sort_order: 'desc'
      };

      const response = await apiClient.search(searchRequest);
      onSearchResults(response.results, response.search_time_ms);

    } catch (error) {
      console.error('Search failed:', error);
      onSearchError(error instanceof Error ? error.message : 'Search failed');
    } finally {
      setIsSearching(false);
    }
  };

  const handleFilterChange = (filterType: keyof SearchFilters, value: unknown) => {
    setActiveFilters(prev => ({
      ...prev,
      [filterType]: value
    }));
  };

  const clearFilters = () => {
    setActiveFilters({});
  };

  const removeImage = () => {
    setSelectedImage(null);
    setImagePreview(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
    if (searchType === 'image') {
      setSearchType('text');
    } else if (searchType === 'hybrid' && !query) {
      setSearchType('text');
    }
  };

  const activeFilterCount = Object.values(activeFilters).filter(v =>
    v !== undefined && v !== null && v !== '' &&
    (Array.isArray(v) ? v.length > 0 : true)
  ).length;

  return (
    <div style={{ width: '100%', maxWidth: 800, margin: '0 auto' }}>
      {/* Main search input */}
      <div style={{ position: 'relative', marginBottom: 16 }}>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => suggestions.length > 0 && setShowSuggestions(true)}
          onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
          placeholder="Search for vintage fashion items..."
          disabled={isSearching}
          style={{
            width: '100%',
            fontSize: 22,
            padding: '22px 28px',
            borderRadius: 32,
            border: '2px solid #d4af37',
            boxShadow: '0 4px 24px rgba(44,24,16,0.06)',
            outline: 'none',
            opacity: isSearching ? 0.7 : 1,
          }}
        />

        {/* Search suggestions */}
        {showSuggestions && suggestions.length > 0 && (
          <div style={{
            position: 'absolute',
            top: '100%',
            left: 0,
            right: 0,
            background: '#fff',
            border: '1px solid #d4af37',
            borderRadius: 12,
            marginTop: 4,
            boxShadow: '0 4px 24px rgba(44,24,16,0.12)',
            zIndex: 10
          }}>
            {suggestions.map((suggestion, index) => (
              <div
                key={index}
                style={{
                  padding: '12px 20px',
                  cursor: 'pointer',
                  borderBottom: index < suggestions.length - 1 ? '1px solid #f0f0f0' : 'none'
                }}
                onMouseDown={() => {
                  setQuery(suggestion);
                  setShowSuggestions(false);
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = '#f9f6f1';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = '#fff';
                }}
              >
                {suggestion}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Search type and image upload */}
      <div style={{
        display: 'flex',
        gap: 16,
        alignItems: 'center',
        marginBottom: 16,
        flexWrap: 'wrap'
      }}>
        {/* Search type selector */}
        <div style={{ display: 'flex', gap: 8 }}>
          {(['text', 'image', 'hybrid'] as const).map((type) => (
            <button
              key={type}
              onClick={() => setSearchType(type)}
              style={{
                padding: '8px 16px',
                borderRadius: 20,
                border: 'none',
                background: searchType === type ? '#d4af37' : '#f0f0f0',
                color: searchType === type ? '#fff' : '#666',
                cursor: 'pointer',
                fontSize: 14,
                fontWeight: 500,
                textTransform: 'capitalize'
              }}
            >
              {type}
            </button>
          ))}
        </div>

        {/* Image upload */}
        {(searchType === 'image' || searchType === 'hybrid') && (
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              onChange={handleImageSelect}
              style={{ display: 'none' }}
            />
            <button
              onClick={() => fileInputRef.current?.click()}
              style={{
                padding: '8px 16px',
                borderRadius: 20,
                border: '1px solid #d4af37',
                background: '#fff',
                color: '#d4af37',
                cursor: 'pointer',
                fontSize: 14
              }}
            >
              📷 Upload Image
            </button>

            {imagePreview && (
              <div style={{ position: 'relative', display: 'inline-block' }}>
                <img
                  src={imagePreview}
                  alt="Selected"
                  style={{
                    width: 40,
                    height: 40,
                    objectFit: 'cover',
                    borderRadius: 8,
                    border: '2px solid #d4af37'
                  }}
                />
                <button
                  onClick={removeImage}
                  style={{
                    position: 'absolute',
                    top: -8,
                    right: -8,
                    width: 20,
                    height: 20,
                    borderRadius: '50%',
                    border: 'none',
                    background: '#d32f2f',
                    color: '#fff',
                    cursor: 'pointer',
                    fontSize: 12,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center'
                  }}
                >
                  ✕
                </button>
              </div>
            )}
          </div>
        )}

        {/* Filter toggle */}
        <button
          onClick={() => setShowFilters(!showFilters)}
          style={{
            padding: '8px 16px',
            borderRadius: 20,
            border: '1px solid #d4af37',
            background: showFilters ? '#d4af37' : '#fff',
            color: showFilters ? '#fff' : '#d4af37',
            cursor: 'pointer',
            fontSize: 14,
            display: 'flex',
            alignItems: 'center',
            gap: 4
          }}
        >
          🔍 Filters
          {activeFilterCount > 0 && (
            <span style={{
              background: '#fff',
              color: '#d4af37',
              borderRadius: '50%',
              width: 20,
              height: 20,
              fontSize: 12,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              {activeFilterCount}
            </span>
          )}
        </button>
      </div>

      {/* Advanced filters */}
      {showFilters && filterOptions && (
        <div style={{
          background: '#f9f6f1',
          borderRadius: 12,
          padding: 20,
          marginBottom: 16
        }}>
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
            gap: 16,
            marginBottom: 16
          }}>
            {/* Category filter */}
            <div>
              <label style={{ display: 'block', marginBottom: 4, fontWeight: 500, fontSize: 14 }}>
                Category
              </label>
              <select
                value={activeFilters.category as string || ''}
                onChange={(e) => handleFilterChange('category', e.target.value || undefined)}
                style={{
                  width: '100%',
                  padding: '8px 12px',
                  borderRadius: 8,
                  border: '1px solid #d0d0d0'
                }}
              >
                <option value="">All Categories</option>
                {filterOptions.categories.map((category) => (
                  <option key={category} value={category}>
                    {category.charAt(0).toUpperCase() + category.slice(1)}
                  </option>
                ))}
              </select>
            </div>

            {/* Brand filter */}
            <div>
              <label style={{ display: 'block', marginBottom: 4, fontWeight: 500, fontSize: 14 }}>
                Brand
              </label>
              <select
                value={activeFilters.brand as string || ''}
                onChange={(e) => handleFilterChange('brand', e.target.value || undefined)}
                style={{
                  width: '100%',
                  padding: '8px 12px',
                  borderRadius: 8,
                  border: '1px solid #d0d0d0'
                }}
              >
                <option value="">All Brands</option>
                {filterOptions.brands.slice(0, 20).map((brand) => (
                  <option key={brand} value={brand}>
                    {brand}
                  </option>
                ))}
              </select>
            </div>

            {/* Color filter */}
            <div>
              <label style={{ display: 'block', marginBottom: 4, fontWeight: 500, fontSize: 14 }}>
                Color
              </label>
              <select
                value={activeFilters.primary_color as string || ''}
                onChange={(e) => handleFilterChange('primary_color', e.target.value || undefined)}
                style={{
                  width: '100%',
                  padding: '8px 12px',
                  borderRadius: 8,
                  border: '1px solid #d0d0d0'
                }}
              >
                <option value="">All Colors</option>
                {filterOptions.colors.map((color) => (
                  <option key={color} value={color}>
                    {color.charAt(0).toUpperCase() + color.slice(1)}
                  </option>
                ))}
              </select>
            </div>

            {/* Material filter */}
            <div>
              <label style={{ display: 'block', marginBottom: 4, fontWeight: 500, fontSize: 14 }}>
                Material
              </label>
              <select
                value={activeFilters.material as string || ''}
                onChange={(e) => handleFilterChange('material', e.target.value || undefined)}
                style={{
                  width: '100%',
                  padding: '8px 12px',
                  borderRadius: 8,
                  border: '1px solid #d0d0d0'
                }}
              >
                <option value="">All Materials</option>
                {filterOptions.materials.map((material) => (
                  <option key={material} value={material}>
                    {material.charAt(0).toUpperCase() + material.slice(1)}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Price range */}
          <div style={{ marginBottom: 16 }}>
            <label style={{ display: 'block', marginBottom: 4, fontWeight: 500, fontSize: 14 }}>
              Price Range
            </label>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <input
                type="number"
                placeholder="Min"
                value={activeFilters.price_range?.[0] ?? ''}
                onChange={(e) => {
                  const min = e.target.value ? Number(e.target.value) : undefined;
                  const max = activeFilters.price_range?.[1];
                  handleFilterChange('price_range', min !== undefined || max !== undefined ? [min, max] : undefined);
                }}
                style={{
                  width: 80,
                  padding: '8px 12px',
                  borderRadius: 8,
                  border: '1px solid #d0d0d0'
                }}
              />
              <span>to</span>
              <input
                type="number"
                placeholder="Max"
                value={activeFilters.price_range?.[1] ?? ''}
                onChange={(e) => {
                  const max = e.target.value ? Number(e.target.value) : undefined;
                  const min = activeFilters.price_range?.[0];
                  handleFilterChange('price_range', min !== undefined || max !== undefined ? [min, max] : undefined);
                }}
                style={{
                  width: 80,
                  padding: '8px 12px',
                  borderRadius: 8,
                  border: '1px solid #d0d0d0'
                }}
              />
            </div>
          </div>

          {/* Advanced options */}
          <div style={{
            display: 'flex',
            gap: 16,
            alignItems: 'center',
            marginBottom: 16
          }}>
            <div>
              <label style={{ display: 'block', marginBottom: 4, fontWeight: 500, fontSize: 14 }}>
                Min Similarity: {(minSimilarity * 100).toFixed(0)}%
              </label>
              <input
                type="range"
                min="0.3"
                max="0.95"
                step="0.05"
                value={minSimilarity}
                onChange={(e) => setMinSimilarity(Number(e.target.value))}
                style={{ width: 120 }}
              />
            </div>

            <div>
              <label style={{ display: 'block', marginBottom: 4, fontWeight: 500, fontSize: 14 }}>
                Sort By
              </label>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as typeof sortBy)}
                style={{
                  padding: '8px 12px',
                  borderRadius: 8,
                  border: '1px solid #d0d0d0'
                }}
              >
                <option value="relevance">Relevance</option>
                <option value="similarity">Similarity</option>
                <option value="price">Price</option>
              </select>
            </div>

            <div>
              <label style={{ display: 'block', marginBottom: 4, fontWeight: 500, fontSize: 14 }}>
                Results
              </label>
              <select
                value={limit}
                onChange={(e) => setLimit(Number(e.target.value))}
                style={{
                  padding: '8px 12px',
                  borderRadius: 8,
                  border: '1px solid #d0d0d0'
                }}
              >
                <option value={10}>10</option>
                <option value={20}>20</option>
                <option value={50}>50</option>
                <option value={100}>100</option>
              </select>
            </div>
          </div>

          {/* Clear filters */}
          {activeFilterCount > 0 && (
            <button
              onClick={clearFilters}
              style={{
                padding: '8px 16px',
                borderRadius: 8,
                border: '1px solid #d32f2f',
                background: '#fff',
                color: '#d32f2f',
                cursor: 'pointer',
                fontSize: 14
              }}
            >
              Clear All Filters
            </button>
          )}
        </div>
      )}

      {/* Search button */}
      <button
        onClick={() => void handleSearch()}
        disabled={isSearching || (!query.trim() && !selectedImage)}
        style={{
          background: isSearching || (!query.trim() && !selectedImage) ? '#ccc' : '#d4af37',
          color: '#fff',
          fontWeight: 600,
          border: 'none',
          borderRadius: 32,
          padding: '16px 32px',
          fontSize: 18,
          cursor: isSearching || (!query.trim() && !selectedImage) ? 'not-allowed' : 'pointer',
          boxShadow: '0 2px 12px rgba(212,175,55,0.2)',
          width: '100%',
        }}
      >
        {isSearching ? 'Searching...' : 'Search'}
      </button>
    </div>
  );
}
