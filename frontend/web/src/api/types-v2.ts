// Enhanced API types for Prethrift v2.0 search capabilities
// Supports multi-modal search, rich filtering, and ontology properties

export interface SearchRequestV2 {
  search_type: 'text' | 'image' | 'hybrid' | 'metadata';
  text_query?: string;
  image_query?: string; // base64 encoded image or URL
  filters?: SearchFilters;
  limit?: number;
  min_similarity?: number;
  sort_by?: 'similarity' | 'price' | 'date' | 'relevance';
  sort_order?: 'asc' | 'desc';
}

export interface SearchFilters {
  // Core filters
  brand?: string | string[];
  price_range?: [number, number];

  // Ontology-based filters
  category?: string | string[];
  subcategory?: string | string[];
  primary_color?: string | string[];
  secondary_color?: string | string[];
  pattern?: string | string[];
  material?: string | string[];
  style?: string | string[];
  fit?: string | string[];
  season?: string | string[];
  occasion?: string | string[];
  era?: string | string[];
  gender?: string | string[];
  size?: string | string[];
  condition?: string | string[];
  designer_tier?: 'luxury' | 'premium' | 'mid-range' | 'affordable';

  // Advanced filters
  sustainability_score_min?: number;
  ontology_confidence_min?: number;
}

export interface GarmentResponseV2 {
  id: number;
  external_id: string;
  title?: string;
  brand?: string;
  price?: number;
  currency?: string;
  image_path?: string;
  description?: string;

  // Ontology properties
  category?: string;
  subcategory?: string;
  primary_color?: string;
  secondary_color?: string;
  pattern?: string;
  material?: string;
  style?: string;
  fit?: string;
  season?: string;
  occasion?: string;
  era?: string;
  gender?: string;
  size?: string;
  condition?: string;
  designer_tier?: string;
  sustainability_score?: number;
  ontology_confidence?: number;

  // Search metadata
  similarity_score?: number;
  match_reason?: string;
}

export interface SearchResponseV2 {
  query: string;
  search_type: string;
  results: GarmentResponseV2[];
  total_count: number;
  filters_applied: SearchFilters;
  search_time_ms: number;
  facets?: SearchFacets;
}

export interface SearchFacets {
  brands: FacetItem[];
  categories: FacetItem[];
  colors: FacetItem[];
  materials: FacetItem[];
  price_ranges: PriceRangeFacet[];
  designer_tiers: FacetItem[];
}

export interface FacetItem {
  value: string;
  count: number;
  selected?: boolean;
}

export interface PriceRangeFacet {
  min: number;
  max: number;
  count: number;
  label: string;
}

export interface SimilarGarmentsRequest {
  garment_id: number;
  limit?: number;
  min_similarity?: number;
  filters?: SearchFilters;
}

export interface PropertyExtractionRequest {
  garment_id: number;
  force_reextract?: boolean;
}

export interface PropertyExtractionResponse {
  garment_id: number;
  success: boolean;
  properties_extracted: number;
  confidence_score: number;
  extraction_time_ms: number;
}

// Legacy types for backward compatibility
export interface SearchRequest {
  query: string;
  limit?: number;
  model?: string;
  user_id?: string;
  force?: boolean;
}

export interface SearchResponse {
  query?: string;
  results?: SearchResultItem[];
  attributes?: Record<string, unknown>;
  ambiguous?: boolean;
  clarification?: string;
  off_topic?: boolean;
  off_topic_reason?: string;
  message?: string;
}

export interface SearchResultItem {
  garment_id?: number;
  score?: number;
  title?: string;
  brand?: string;
  price?: number;
  currency?: string;
  image_path?: string;
  description?: string;
  attributes?: { family: string; value: string; confidence?: number }[];
  explanation?: Record<string, unknown>;
  thumbnail_url?: string;
  explanation_summary?: { top_components?: string[]; final_score?: number };
}

export interface HTTPValidationError {
  detail?: ValidationError[];
}

export interface ValidationError {
  loc: (string | number)[];
  msg: string;
  type: string;
}
