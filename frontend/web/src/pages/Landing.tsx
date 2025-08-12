import { useEffect, useState } from 'react';
import { ApiClient } from '../api/client';
import type { SearchResponse, SearchResultItem } from '../api/types';

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

const apiClient = new ApiClient();

export default function Landing() {
  const [country, setCountry] = useState('US');
  const [query, setQuery] = useState('');
  const [searchResults, setSearchResults] = useState<SearchResultItem[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setIsSearching(true);
    setSearchError(null);

    try {
      const response: SearchResponse = await apiClient.search({
        query: query.trim(),
        limit: 20,
      });

      setSearchResults(response.results ?? []);
    } catch (error) {
      console.error('Search failed:', error);
      setSearchError('Search failed. Please try again.');
    } finally {
      setIsSearching(false);
    }
  };

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
          minHeight: '70vh',
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
        <form
          style={{ width: '100%', maxWidth: 520, margin: '0 auto' }}
          onSubmit={(e) => {
            void handleSearch(e);
          }}
        >
          <input
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
            }}
            placeholder="Search for vintage bags, watches, stories..."
            disabled={isSearching}
            style={{
              width: '100%',
              fontSize: 22,
              padding: '22px 28px',
              borderRadius: 32,
              border: '2px solid #d4af37',
              boxShadow: '0 4px 24px rgba(44,24,16,0.06)',
              outline: 'none',
              marginBottom: 16,
              opacity: isSearching ? 0.7 : 1,
            }}
          />
          <button
            type="submit"
            disabled={isSearching || !query.trim()}
            style={{
              background: isSearching || !query.trim() ? '#ccc' : '#d4af37',
              color: '#fff',
              fontWeight: 600,
              border: 'none',
              borderRadius: 32,
              padding: '16px 32px',
              fontSize: 18,
              cursor: isSearching || !query.trim() ? 'not-allowed' : 'pointer',
              boxShadow: '0 2px 12px rgba(212,175,55,0.2)',
              width: '100%',
              marginBottom: 16,
            }}
          >
            {isSearching ? 'Searching...' : 'Search'}
          </button>
        </form>

        {searchError && (
          <div style={{
            color: '#d32f2f',
            fontSize: 16,
            marginBottom: 20,
            padding: '12px 24px',
            background: '#ffebee',
            borderRadius: 8,
            border: '1px solid #ffcdd2'
          }}>
            {searchError}
          </div>
        )}

        <div style={{ color: '#6d4423', fontStyle: 'italic', fontSize: 16, marginBottom: 40 }}>
          Try: "Chanel 90s bag", "Rolex story", "Paris flea market"
        </div>

        {/* Search Results */}
        {searchResults.length > 0 && (
          <section style={{ width: '100%', maxWidth: 1200, margin: '0 auto', marginTop: 40 }}>
            <h2 style={{
              fontFamily: 'Georgia,serif',
              fontSize: '1.5rem',
              color: '#2c1810',
              marginBottom: 24,
              textAlign: 'center'
            }}>
              Search Results ({searchResults.length} items)
            </h2>
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
              gap: 24,
              padding: 8
            }}>
              {searchResults.map((item) => (
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
                        // Fallback to placeholder on image error
                        const target = e.target as HTMLImageElement;
                        target.style.display = 'none';
                        const placeholder = target.nextElementSibling as HTMLDivElement;
                        placeholder.style.display = 'flex';
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
        {searchResults.length === 0 && !isSearching && (
          <section style={{ width: '100%', maxWidth: 900, margin: '0 auto', marginTop: 40 }}>
            {/* Option 1: Slideshow of Curated Finds */}
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
                      Curated Find #{i}
                    </div>
                    <div style={{ color: '#6d4423', fontSize: 14, marginTop: 4 }}>
                      Brand, year, story...
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
