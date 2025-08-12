import React, { useEffect, useState } from 'react';
import { ApiClient } from '../api/client';
import { ApiClientV2 } from '../api/client-v2';
import type { SearchResponse, SearchResultItem } from '../api/types';
import type { GarmentResponseV2, SearchFilters } from '../api/types-v2';
import EnhancedSearch from '../components/EnhancedSearch';
import SearchResults from '../components/SearchResults';

const LOGO_SRC = '/logo.svg';
const GEO_API = 'https://ipapi.co/json/';

const countries = [
  { code: 'US', name: 'United States' },
  { code: 'GB', name: 'United Kingdom' },
  { code: 'IN', name: 'India' },
  { code: 'DE', name: 'Germany' },
  { code: 'FR', name: 'France' },
  // ...add more as needed
];

const legacyApiClient = new ApiClient();
const apiClientV2 = new ApiClientV2();

export default function Landing() {
  const [country, setCountry] = useState('US');

  // Search state
  const [searchResults, setSearchResults] = useState<GarmentResponseV2[]>([]);
  const [searchTime, setSearchTime] = useState(0);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [isShowingLegacyResults, setIsShowingLegacyResults] = useState(false);

  // Mode toggle
  const [useV2Search, setUseV2Search] = useState(true);

  // Legacy search state
  const [legacyQuery, setLegacyQuery] = useState('');
  const [legacyResults, setLegacyResults] = useState<SearchResultItem[]>([]);
  const [isLegacySearching, setIsLegacySearching] = useState(false);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const res = await fetch(GEO_API, { method: 'GET' });
        if (!res.ok) return; // ignore silently
        interface GeoResponse {
          country_code?: string;
        }
        const data = (await res.json()) as GeoResponse | null;
        const code = data?.country_code;
        // eslint-disable-next-line @typescript-eslint/no-unnecessary-condition -- cancellation flag can change before async resolves
        if (!cancelled && typeof code === 'string') {
          setCountry(code);
        }
      } catch {
        // ignore network errors for now
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const handleV2SearchResults = (results: GarmentResponseV2[], searchTimeMs: number) => {
    setSearchResults(results);
    setSearchTime(searchTimeMs);
    setSearchError(null);
    setIsShowingLegacyResults(false);
  };

  const handleV2SearchError = (error: string) => {
    setSearchError(error);
    setSearchResults([]);
    setSearchTime(0);
  };

  const handleSimilarSearch = async (garmentId: number) => {
    try {
      const response = await apiClientV2.findSimilar({
        garment_id: garmentId,
        limit: 20,
        min_similarity: 0.6
      });

      setSearchResults(response.results);
      setSearchTime(response.search_time_ms);
      setSearchError(null);
    } catch (error) {
      console.error('Similar search failed:', error);
      setSearchError('Similar search failed. Please try again.');
    }
  };

  const handleFilterApply = async (filters: SearchFilters) => {
    try {
      const response = await apiClientV2.search({
        search_type: 'metadata',
        filters,
        limit: 50
      });

      setSearchResults(response.results);
      setSearchTime(response.search_time_ms);
      setSearchError(null);
    } catch (error) {
      console.error('Filter search failed:', error);
      setSearchError('Filter search failed. Please try again.');
    }
  };

  const handleLegacySearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!legacyQuery.trim()) return;

    setIsLegacySearching(true);
    setSearchError(null);

    try {
      const response: SearchResponse = await legacyApiClient.search({
        query: legacyQuery.trim(),
        limit: 20,
      });

      setLegacyResults(response.results ?? []);
      setIsShowingLegacyResults(true);
      setSearchResults([]);
    } catch (error) {
      console.error('Legacy search failed:', error);
      setSearchError('Search failed. Please try again.');
    } finally {
      setIsLegacySearching(false);
    }
  };

  const clearResults = () => {
    setSearchResults([]);
    setLegacyResults([]);
    setSearchError(null);
    setIsShowingLegacyResults(false);
  };

  return (
    <div style={{ minHeight: '100vh', background: '#f5f1eb' }}>
      <header
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '24px 48px 12px 48px',
          background: '#fff',
          boxShadow: '0 2px 8px rgba(0,0,0,0.04)',
          position: 'sticky',
          top: 0,
          zIndex: 10,
        }}
      >
        <img src={LOGO_SRC} alt="Prethrift Logo" style={{ height: 48 }} />

        <div style={{ display: 'flex', alignItems: 'center', gap: 24 }}>
          {/* Search mode toggle */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <span style={{ fontSize: 14, color: '#666' }}>Search:</span>
            <div style={{ display: 'flex', borderRadius: 20, overflow: 'hidden', border: '1px solid #d4af37' }}>
              <button
                onClick={() => {
                  setUseV2Search(false);
                  clearResults();
                }}
                style={{
                  padding: '6px 12px',
                  border: 'none',
                  background: !useV2Search ? '#d4af37' : '#fff',
                  color: !useV2Search ? '#fff' : '#d4af37',
                  cursor: 'pointer',
                  fontSize: 13,
                  fontWeight: 500
                }}
              >
                Legacy
              </button>
              <button
                onClick={() => {
                  setUseV2Search(true);
                  clearResults();
                }}
                style={{
                  padding: '6px 12px',
                  border: 'none',
                  background: useV2Search ? '#d4af37' : '#fff',
                  color: useV2Search ? '#fff' : '#d4af37',
                  cursor: 'pointer',
                  fontSize: 13,
                  fontWeight: 500
                }}
              >
                Enhanced v2.0
              </button>
            </div>
          </div>

          <select
            value={country}
            onChange={(e) => {
              setCountry(e.target.value);
            }}
            style={{
              fontSize: 16,
              padding: '6px 12px',
              borderRadius: 8,
              border: '1px solid #d4af37',
            }}
          >
            {countries.map((c) => {
              return (
                <option key={c.code} value={c.code}>
                  {c.name}
                </option>
              );
            })}
          </select>

          <button
            style={{
              background: '#d4af37',
              color: '#fff',
              fontWeight: 600,
              border: 'none',
              borderRadius: 8,
              padding: '10px 24px',
              fontSize: 16,
              cursor: 'pointer',
              boxShadow: '0 2px 8px rgba(212,175,55,0.08)',
            }}
          >
            Sign Up
          </button>
        </div>
      </header>

      <main
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: searchResults.length > 0 || legacyResults.length > 0 ? 'auto' : '70vh',
          padding: '0 20px'
        }}
      >
        <h1
          style={{
            fontFamily: 'Georgia,serif',
            fontWeight: 700,
            fontSize: '2.5rem',
            color: '#2c1810',
            margin: '60px 0 24px 0',
            textAlign: 'center',
          }}
        >
          Prethrift
          <div style={{ fontSize: '1.25rem', fontWeight: 400, marginTop: 12 }}>
            Shop the source.
          </div>
        </h1>

        {/* Search interface based on mode */}
        {useV2Search ? (
          <EnhancedSearch
            onSearchResults={handleV2SearchResults}
            onSearchError={handleV2SearchError}
          />
        ) : (
          <form
            style={{ width: '100%', maxWidth: 520, margin: '0 auto' }}
            onSubmit={(e) => {
              void handleLegacySearch(e);
            }}
          >
            <input
              type="text"
              value={legacyQuery}
              onChange={(e) => {
                setLegacyQuery(e.target.value);
              }}
              placeholder="Search for vintage bags, watches, stories..."
              disabled={isLegacySearching}
              style={{
                width: '100%',
                fontSize: 22,
                padding: '22px 28px',
                borderRadius: 32,
                border: '2px solid #d4af37',
                boxShadow: '0 4px 24px rgba(44,24,16,0.06)',
                outline: 'none',
                marginBottom: 16,
                opacity: isLegacySearching ? 0.7 : 1,
              }}
            />
            <button
              type="submit"
              disabled={isLegacySearching || !legacyQuery.trim()}
              style={{
                background: isLegacySearching || !legacyQuery.trim() ? '#ccc' : '#d4af37',
                color: '#fff',
                fontWeight: 600,
                border: 'none',
                borderRadius: 32,
                padding: '16px 32px',
                fontSize: 18,
                cursor: isLegacySearching || !legacyQuery.trim() ? 'not-allowed' : 'pointer',
                boxShadow: '0 2px 12px rgba(212,175,55,0.2)',
                width: '100%',
                marginBottom: 16,
              }}
            >
              {isLegacySearching ? 'Searching...' : 'Search (Legacy)'}
            </button>
          </form>
        )}

        {/* Error display */}
        {searchError && (
          <div style={{
            color: '#d32f2f',
            fontSize: 16,
            marginBottom: 20,
            padding: '12px 24px',
            background: '#ffebee',
            borderRadius: 8,
            border: '1px solid #ffcdd2',
            maxWidth: 520,
            margin: '0 auto 20px auto'
          }}>
            {searchError}
          </div>
        )}

        {/* Search suggestions */}
        {!searchResults.length && !legacyResults.length && !searchError && (
          <div style={{ color: '#6d4423', fontStyle: 'italic', fontSize: 16, marginBottom: 40, textAlign: 'center' }}>
            {useV2Search ? (
              <>
                Try: "blue vintage denim jacket", upload an image, or use filters
                <div style={{ marginTop: 8, fontSize: 14 }}>
                  ✨ New: Multi-modal search, smart filters, and visual similarity
                </div>
              </>
            ) : (
              'Try: "Chanel 90s bag", "Rolex story", "Paris flea market"'
            )}
          </div>
        )}

        {/* Enhanced search results */}
        {useV2Search && searchResults.length > 0 && (
          <SearchResults
            results={searchResults}
            searchTime={searchTime}
            onSimilarSearch={handleSimilarSearch}
            onFilterApply={handleFilterApply}
          />
        )}

        {/* Legacy search results */}
        {!useV2Search && isShowingLegacyResults && legacyResults.length > 0 && (
          <section style={{ width: '100%', maxWidth: 1200, margin: '0 auto', marginTop: 40 }}>
            <h2 style={{
              fontFamily: 'Georgia,serif',
              fontSize: '1.5rem',
              color: '#2c1810',
              marginBottom: 24,
              textAlign: 'center'
            }}>
              Legacy Results ({legacyResults.length} items)
            </h2>
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
              gap: 24,
              padding: 8
            }}>
              {legacyResults.map((item) => (
                <div
                  key={item.garment_id}
                  style={{
                    background: '#fff',
                    borderRadius: 18,
                    boxShadow: '0 2px 12px rgba(44,24,16,0.07)',
                    padding: 18,
                    transition: 'transform 0.2s, box-shadow 0.2s',
                    cursor: 'pointer',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.transform = 'translateY(-4px)';
                    e.currentTarget.style.boxShadow = '0 8px 24px rgba(44,24,16,0.12)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.transform = 'translateY(0)';
                    e.currentTarget.style.boxShadow = '0 2px 12px rgba(44,24,16,0.07)';
                  }}
                >
                  {item.image_path ?? item.thumbnail_url ? (
                    <img
                      src={item.thumbnail_url ?? item.image_path}
                      alt={item.title ?? 'Vintage item'}
                      style={{
                        width: '100%',
                        height: 200,
                        objectFit: 'cover',
                        borderRadius: 12,
                        marginBottom: 12,
                      }}
                      onError={(e) => {
                        const target = e.target as HTMLImageElement;
                        target.style.display = 'none';
                        const placeholder = target.nextElementSibling as HTMLDivElement;
                        if (placeholder) {
                          placeholder.style.display = 'flex';
                        }
                      }}
                    />
                  ) : null}
                  <div
                    style={{
                      height: 200,
                      background: '#e8ddd4',
                      borderRadius: 12,
                      marginBottom: 12,
                      display: item.image_path ?? item.thumbnail_url ? 'none' : 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: '#6d4423',
                      fontSize: 14,
                    }}
                  >
                    No Image Available
                  </div>

                  <div style={{ fontWeight: 600, color: '#2c1810', fontSize: 18, marginBottom: 8 }}>
                    {item.title ?? 'Vintage Item'}
                  </div>

                  {item.brand && (
                    <div style={{ color: '#d4af37', fontSize: 14, fontWeight: 500, marginBottom: 4 }}>
                      {item.brand}
                    </div>
                  )}

                  {item.price && (
                    <div style={{ color: '#2c1810', fontSize: 16, fontWeight: 600, marginBottom: 8 }}>
                      {item.currency ?? '$'}{item.price}
                    </div>
                  )}

                  {item.description && (
                    <div style={{
                      color: '#6d4423',
                      fontSize: 14,
                      lineHeight: 1.4,
                      display: '-webkit-box',
                      WebkitLineClamp: 3,
                      WebkitBoxOrient: 'vertical',
                      overflow: 'hidden',
                      marginBottom: 8
                    }}>
                      {item.description}
                    </div>
                  )}

                  {item.score && (
                    <div style={{
                      color: '#6d4423',
                      fontSize: 12,
                      fontStyle: 'italic',
                      marginTop: 8,
                      paddingTop: 8,
                      borderTop: '1px solid #e8ddd4'
                    }}>
                      Match: {(item.score * 100).toFixed(0)}%
                    </div>
                  )}
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Placeholder for visual language when no search results */}
        {!searchResults.length && !legacyResults.length && !searchError && (
          <section style={{ width: '100%', maxWidth: 900, margin: '0 auto', marginTop: 40 }}>
            <div style={{ display: 'flex', gap: 32, overflowX: 'auto', padding: 8 }}>
              {[1, 2, 3].map((i) => {
                return (
                  <div
                    key={i}
                    style={{
                      minWidth: 240,
                      background: '#fff',
                      borderRadius: 18,
                      boxShadow: '0 2px 12px rgba(44,24,16,0.07)',
                      padding: 18,
                      textAlign: 'center',
                    }}
                  >
                    <div
                      style={{
                        height: 160,
                        background: '#e8ddd4',
                        borderRadius: 12,
                        marginBottom: 12,
                      }}
                    />
                    <div style={{ fontWeight: 600, color: '#2c1810', fontSize: 18 }}>
                      {useV2Search ? `Enhanced Feature #${i}` : `Curated Find #${i}`}
                    </div>
                    <div style={{ color: '#6d4423', fontSize: 14, marginTop: 4 }}>
                      {useV2Search
                        ? ['Multi-modal search', 'Smart filtering', 'Visual similarity'][i-1]
                        : 'Brand, year, story...'
                      }
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        )}
      </main>
    </div>
  );
}
