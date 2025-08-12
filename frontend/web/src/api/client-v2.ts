// Enhanced API client for Prethrift v2.0 search capabilities
import type {
  SearchRequestV2,
  SearchResponseV2,
  SimilarGarmentsRequest,
  PropertyExtractionRequest,
  PropertyExtractionResponse,
  GarmentResponseV2
} from './types-v2';

export interface ApiClientV2Options {
  baseUrl?: string;
  fetchImpl?: typeof fetch;
}

export class ApiClientV2 {
  private baseUrl: string;
  private fetchImpl: typeof fetch;

  constructor(opts: ApiClientV2Options = {}) {
    this.baseUrl = opts.baseUrl ?? '/api/v2';
    this.fetchImpl = opts.fetchImpl ?? fetch;
  }

  /**
   * Enhanced search with multi-modal capabilities and rich filtering
   */
  async search(request: SearchRequestV2, init?: RequestInit): Promise<SearchResponseV2> {
    const res = await this.fetchImpl(`${this.baseUrl}/search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
      ...(init ?? {})
    });

    if (!res.ok) {
      const errorText = await res.text();
      throw new Error(`Search failed: ${res.status.toString()} - ${errorText}`);
    }

    return res.json() as Promise<SearchResponseV2>;
  }

  /**
   * Find similar garments based on a reference garment
   */
  async findSimilar(request: SimilarGarmentsRequest, init?: RequestInit): Promise<SearchResponseV2> {
    const res = await this.fetchImpl(`${this.baseUrl}/similar`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
      ...(init ?? {})
    });

    if (!res.ok) {
      const errorText = await res.text();
      throw new Error(`Similar search failed: ${res.status.toString()} - ${errorText}`);
    }

    return res.json() as Promise<SearchResponseV2>;
  }

  /**
   * Get detailed garment information including all ontology properties
   */
  async getGarment(garmentId: number, init?: RequestInit): Promise<GarmentResponseV2> {
    const res = await this.fetchImpl(`${this.baseUrl}/garments/${garmentId.toString()}`, {
      method: 'GET',
      ...(init ?? {})
    });

    if (!res.ok) {
      const errorText = await res.text();
      throw new Error(`Get garment failed: ${res.status.toString()} - ${errorText}`);
    }

    return res.json() as Promise<GarmentResponseV2>;
  }

  /**
   * Extract ontology properties for a garment
   */
  async extractProperties(
    request: PropertyExtractionRequest,
    init?: RequestInit
  ): Promise<PropertyExtractionResponse> {
    const res = await this.fetchImpl(`${this.baseUrl}/extract-properties`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
      ...(init ?? {})
    });

    if (!res.ok) {
      const errorText = await res.text();
      throw new Error(`Property extraction failed: ${res.status.toString()} - ${errorText}`);
    }

    return res.json() as Promise<PropertyExtractionResponse>;
  }

  /**
   * Upload and analyze an image for search
   */
  async uploadImage(
    imageFile: File,
    init?: RequestInit
  ): Promise<{ image_id: string; image_url: string }> {
    const formData = new FormData();
    formData.append('image', imageFile);

    const res = await this.fetchImpl(`${this.baseUrl}/upload-image`, {
      method: 'POST',
      body: formData,
      ...(init ?? {})
    });

    if (!res.ok) {
      const errorText = await res.text();
      throw new Error(`Image upload failed: ${res.status.toString()} - ${errorText}`);
    }

    return res.json() as Promise<{ image_id: string; image_url: string }>;
  }

  /**
   * Get search suggestions based on partial query
   */
  async getSuggestions(
    query: string,
    limit = 5,
    init?: RequestInit
  ): Promise<string[]> {
    const params = new URLSearchParams({
      q: query,
      limit: limit.toString()
    });

    const res = await this.fetchImpl(`${this.baseUrl}/suggestions?${params}`, {
      method: 'GET',
      ...(init ?? {})
    });

    if (!res.ok) {
      const errorText = await res.text();
      throw new Error(`Get suggestions failed: ${res.status.toString()} - ${errorText}`);
    }

    const response = await res.json() as { suggestions?: string[] };
    return response.suggestions ?? [];
  }

  /**
   * Get available filter options for faceted search
   */
  async getFilterOptions(init?: RequestInit): Promise<{
    categories: string[];
    brands: string[];
    colors: string[];
    materials: string[];
    styles: string[];
    seasons: string[];
    occasions: string[];
    designer_tiers: string[];
  }> {
    const res = await this.fetchImpl(`${this.baseUrl}/filter-options`, {
      method: 'GET',
      ...(init ?? {})
    });

    if (!res.ok) {
      const errorText = await res.text();
      throw new Error(`Get filter options failed: ${res.status.toString()} - ${errorText}`);
    }

    return res.json() as Promise<{
      categories: string[];
      brands: string[];
      colors: string[];
      materials: string[];
      styles: string[];
      seasons: string[];
      occasions: string[];
      designer_tiers: string[];
    }>;
  }
}
