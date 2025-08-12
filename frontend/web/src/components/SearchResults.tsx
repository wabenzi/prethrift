import React, { useState } from 'react';
import type { GarmentResponseV2, SearchFilters } from '../api/types-v2';
import { ApiClientV2 } from '../api/client-v2';

interface SearchResultsProps {
  results: GarmentResponseV2[];
  searchTime: number;
  onSimilarSearch?: (garmentId: number) => void;
  onFilterApply?: (filters: SearchFilters) => void;
}

const apiClient = new ApiClientV2();

export default function SearchResults({
  results,
  searchTime,
  onSimilarSearch,
  onFilterApply
}: SearchResultsProps) {
  const [selectedGarment, setSelectedGarment] = useState<GarmentResponseV2 | null>(null);
  const [isLoadingSimilar, setIsLoadingSimilar] = useState<number | null>(null);

  const handleSimilarSearch = async (garmentId: number) => {
    if (!onSimilarSearch) return;

    setIsLoadingSimilar(garmentId);
    try {
      onSimilarSearch(garmentId);
    } finally {
      setIsLoadingSimilar(null);
    }
  };

  const handleFilterClick = (filterType: keyof SearchFilters, value: string) => {
    if (!onFilterApply) return;

    onFilterApply({
      [filterType]: value
    });
  };

  const formatPrice = (price?: number, currency?: string) => {
    if (!price) return null;
    const currencySymbol = currency === 'USD' ? '$' : currency === 'EUR' ? '€' : currency ?? '$';
    return `${currencySymbol}${price.toLocaleString()}`;
  };

  const getConfidenceColor = (confidence?: number) => {
    if (!confidence) return '#999';
    if (confidence >= 0.8) return '#4caf50';
    if (confidence >= 0.6) return '#ff9800';
    return '#f44336';
  };

  const renderPropertyTags = (garment: GarmentResponseV2) => {
    const properties = [
      { key: 'category', value: garment.category, label: 'Category' },
      { key: 'subcategory', value: garment.subcategory, label: 'Type' },
      { key: 'primary_color', value: garment.primary_color, label: 'Color' },
      { key: 'material', value: garment.material, label: 'Material' },
      { key: 'style', value: garment.style, label: 'Style' },
      { key: 'season', value: garment.season, label: 'Season' },
      { key: 'occasion', value: garment.occasion, label: 'Occasion' },
      { key: 'designer_tier', value: garment.designer_tier, label: 'Tier' },
      { key: 'era', value: garment.era, label: 'Era' },
      { key: 'condition', value: garment.condition, label: 'Condition' }
    ].filter(prop => prop.value);

    return (
      <div style={{
        display: 'flex',
        flexWrap: 'wrap',
        gap: 6,
        marginTop: 8
      }}>
        {properties.map((prop) => (
          <button
            key={prop.key}
            onClick={() => {
              handleFilterClick(prop.key as keyof SearchFilters, prop.value!);
            }}
            style={{
              background: '#f0f8ff',
              border: '1px solid #d4af37',
              borderRadius: 12,
              padding: '4px 8px',
              fontSize: 11,
              color: '#2c1810',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 2,
              transition: 'all 0.2s'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = '#d4af37';
              e.currentTarget.style.color = '#fff';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = '#f0f8ff';
              e.currentTarget.style.color = '#2c1810';
            }}
            title={`Filter by ${prop.label}: ${prop.value}`}
          >
            <span style={{ fontSize: 10, opacity: 0.7 }}>{prop.label}:</span>
            <span style={{ fontWeight: 500 }}>
              {prop.value!.charAt(0).toUpperCase() + prop.value!.slice(1)}
            </span>
          </button>
        ))}
      </div>
    );
  };

  if (results.length === 0) {
    return (
      <div style={{
        textAlign: 'center',
        padding: 40,
        color: '#6d4423',
        fontSize: 16
      }}>
        <div style={{ fontSize: 48, marginBottom: 16 }}>🔍</div>
        <div style={{ fontWeight: 500, marginBottom: 8 }}>No results found</div>
        <div>Try adjusting your search terms or filters</div>
      </div>
    );
  }

  return (
    <div style={{ width: '100%', maxWidth: 1200, margin: '0 auto' }}>
      {/* Search metadata */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 24,
        padding: '0 8px'
      }}>
        <h2 style={{
          fontFamily: 'Georgia,serif',
          fontSize: '1.5rem',
          color: '#2c1810',
          margin: 0
        }}>
          {results.length} Results
        </h2>
        <div style={{
          color: '#6d4423',
          fontSize: 14,
          fontStyle: 'italic'
        }}>
          Found in {searchTime}ms
        </div>
      </div>

      {/* Results grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
        gap: 24,
        padding: 8
      }}>
        {results.map((garment) => (
          <div
            key={garment.id}
            style={{
              background: '#fff',
              borderRadius: 18,
              boxShadow: '0 2px 12px rgba(44,24,16,0.07)',
              padding: 18,
              transition: 'transform 0.2s, box-shadow 0.2s',
              cursor: 'pointer',
              position: 'relative'
            }}
            onClick={() => { setSelectedGarment(garment); }}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = 'translateY(-4px)';
              e.currentTarget.style.boxShadow = '0 8px 24px rgba(44,24,16,0.12)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = 'translateY(0)';
              e.currentTarget.style.boxShadow = '0 2px 12px rgba(44,24,16,0.07)';
            }}
          >
            {/* Similarity score badge */}
            {garment.similarity_score && (
              <div style={{
                position: 'absolute',
                top: 12,
                right: 12,
                background: getConfidenceColor(garment.similarity_score),
                color: '#fff',
                borderRadius: 12,
                padding: '4px 8px',
                fontSize: 11,
                fontWeight: 600,
                zIndex: 1
              }}>
                {(garment.similarity_score * 100).toFixed(0)}%
              </div>
            )}

            {/* Image */}
            {garment.image_path ? (
              <img
                src={garment.image_path}
                alt={garment.title ?? 'Vintage item'}
                style={{
                  width: '100%',
                  height: 220,
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

            {/* Image placeholder */}
            <div
              style={{
                height: 220,
                background: '#e8ddd4',
                borderRadius: 12,
                marginBottom: 12,
                display: garment.image_path ? 'none' : 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#6d4423',
                fontSize: 14,
              }}
            >
              No Image Available
            </div>

            {/* Title */}
            <div style={{
              fontWeight: 600,
              color: '#2c1810',
              fontSize: 18,
              marginBottom: 8,
              lineHeight: 1.3
            }}>
              {garment.title ?? 'Vintage Item'}
            </div>

            {/* Brand */}
            {garment.brand && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleFilterClick('brand', garment.brand!);
                }}
                style={{
                  background: 'none',
                  border: 'none',
                  color: '#d4af37',
                  fontSize: 14,
                  fontWeight: 500,
                  marginBottom: 4,
                  cursor: 'pointer',
                  padding: 0,
                  textDecoration: 'underline'
                }}
                title={`Filter by brand: ${garment.brand}`}
              >
                {garment.brand}
              </button>
            )}

            {/* Price */}
            {garment.price && (
              <div style={{
                color: '#2c1810',
                fontSize: 16,
                fontWeight: 600,
                marginBottom: 8
              }}>
                {formatPrice(garment.price, garment.currency)}
              </div>
            )}

            {/* Description */}
            {garment.description && (
              <div style={{
                color: '#6d4423',
                fontSize: 14,
                lineHeight: 1.4,
                display: '-webkit-box',
                WebkitLineClamp: 2,
                WebkitBoxOrient: 'vertical',
                overflow: 'hidden',
                marginBottom: 8
              }}>
                {garment.description}
              </div>
            )}

            {/* Property tags */}
            {renderPropertyTags(garment)}

            {/* Ontology confidence */}
            {garment.ontology_confidence && (
              <div style={{
                marginTop: 8,
                fontSize: 11,
                color: '#666',
                display: 'flex',
                alignItems: 'center',
                gap: 4
              }}>
                <span>Properties:</span>
                <div style={{
                  width: 40,
                  height: 4,
                  background: '#e0e0e0',
                  borderRadius: 2,
                  overflow: 'hidden'
                }}>
                  <div style={{
                    width: `${garment.ontology_confidence * 100}%`,
                    height: '100%',
                    background: getConfidenceColor(garment.ontology_confidence),
                    borderRadius: 2
                  }} />
                </div>
                <span>{(garment.ontology_confidence * 100).toFixed(0)}%</span>
              </div>
            )}

            {/* Action buttons */}
            <div style={{
              display: 'flex',
              gap: 8,
              marginTop: 12,
              paddingTop: 12,
              borderTop: '1px solid #e8ddd4'
            }}>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  void handleSimilarSearch(garment.id);
                }}
                disabled={isLoadingSimilar === garment.id}
                style={{
                  flex: 1,
                  padding: '8px 12px',
                  borderRadius: 8,
                  border: '1px solid #d4af37',
                  background: '#fff',
                  color: '#d4af37',
                  cursor: isLoadingSimilar === garment.id ? 'not-allowed' : 'pointer',
                  fontSize: 12,
                  fontWeight: 500,
                  opacity: isLoadingSimilar === garment.id ? 0.6 : 1
                }}
              >
                {isLoadingSimilar === garment.id ? 'Loading...' : 'Find Similar'}
              </button>

              <button
                onClick={(e) => {
                  e.stopPropagation();
                  window.open(`/garments/${garment.id}`, '_blank');
                }}
                style={{
                  flex: 1,
                  padding: '8px 12px',
                  borderRadius: 8,
                  border: 'none',
                  background: '#d4af37',
                  color: '#fff',
                  cursor: 'pointer',
                  fontSize: 12,
                  fontWeight: 500
                }}
              >
                View Details
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Detailed view modal */}
      {selectedGarment && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(0,0,0,0.8)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
            padding: 20
          }}
          onClick={() => { setSelectedGarment(null); }}
        >
          <div
            style={{
              background: '#fff',
              borderRadius: 18,
              maxWidth: 800,
              maxHeight: '90vh',
              overflow: 'auto',
              padding: 24
            }}
            onClick={(e) => { e.stopPropagation(); }}
          >
            {/* Close button */}
            <button
              onClick={() => { setSelectedGarment(null); }}
              style={{
                position: 'absolute',
                top: 16,
                right: 16,
                width: 32,
                height: 32,
                borderRadius: '50%',
                border: 'none',
                background: '#f0f0f0',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}
            >
              ✕
            </button>

            <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap' }}>
              {/* Image */}
              {selectedGarment.image_path && (
                <div style={{ flex: '1 1 300px' }}>
                  <img
                    src={selectedGarment.image_path}
                    alt={selectedGarment.title ?? 'Vintage item'}
                    style={{
                      width: '100%',
                      height: 400,
                      objectFit: 'cover',
                      borderRadius: 12
                    }}
                  />
                </div>
              )}

              {/* Details */}
              <div style={{ flex: '1 1 300px' }}>
                <h3 style={{
                  fontFamily: 'Georgia,serif',
                  fontSize: '1.5rem',
                  color: '#2c1810',
                  marginBottom: 16
                }}>
                  {selectedGarment.title}
                </h3>

                {selectedGarment.brand && (
                  <div style={{
                    color: '#d4af37',
                    fontSize: 16,
                    fontWeight: 500,
                    marginBottom: 8
                  }}>
                    {selectedGarment.brand}
                  </div>
                )}

                {selectedGarment.price && (
                  <div style={{
                    color: '#2c1810',
                    fontSize: 20,
                    fontWeight: 600,
                    marginBottom: 16
                  }}>
                    {formatPrice(selectedGarment.price, selectedGarment.currency)}
                  </div>
                )}

                {selectedGarment.description && (
                  <div style={{
                    color: '#6d4423',
                    fontSize: 14,
                    lineHeight: 1.5,
                    marginBottom: 16
                  }}>
                    {selectedGarment.description}
                  </div>
                )}

                {/* All properties */}
                {renderPropertyTags(selectedGarment)}

                {/* Confidence scores */}
                <div style={{ marginTop: 16 }}>
                  {selectedGarment.similarity_score && (
                    <div style={{ marginBottom: 8, fontSize: 14 }}>
                      <span style={{ color: '#666' }}>Search Match: </span>
                      <span style={{
                        color: getConfidenceColor(selectedGarment.similarity_score),
                        fontWeight: 600
                      }}>
                        {(selectedGarment.similarity_score * 100).toFixed(1)}%
                      </span>
                    </div>
                  )}

                  {selectedGarment.ontology_confidence && (
                    <div style={{ fontSize: 14 }}>
                      <span style={{ color: '#666' }}>Property Accuracy: </span>
                      <span style={{
                        color: getConfidenceColor(selectedGarment.ontology_confidence),
                        fontWeight: 600
                      }}>
                        {(selectedGarment.ontology_confidence * 100).toFixed(1)}%
                      </span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
