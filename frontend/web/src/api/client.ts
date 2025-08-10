// AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY
// Run: python backend/scripts/generate_typescript_client.py
import type { SearchRequest, SearchResponse, SearchResultItem } from './types';

export interface ApiClientOptions { baseUrl?: string; fetchImpl?: typeof fetch; }

export class ApiClient {
  private baseUrl: string;
  private fetchImpl: typeof fetch;
  constructor(opts: ApiClientOptions = {}) {
    this.baseUrl = opts.baseUrl || '/api';
    this.fetchImpl = opts.fetchImpl || fetch;
  }

    async search(body: SearchRequest, init?: RequestInit): Promise<SearchResponse> {
    const res = await this.fetchImpl(`${this.baseUrl}/search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      ...(init || {})
    });
    if (!res.ok) throw new Error(`Search failed: ${res.status}`);
    return res.json();
  }
}
