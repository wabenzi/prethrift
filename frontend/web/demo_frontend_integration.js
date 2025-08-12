#!/usr/bin/env node
/**
 * Prethrift Frontend Integration Demo
 *
 * This script demonstrates frontend integration for the v2.0 search capabilities.
 * It includes tests for React components, API integration, and user workflows.
 *
 * Usage:
 *   npm run demo:frontend
 *   node demo_frontend_integration.js --test-case visual
 *   node demo_frontend_integration.js --interactive
 */

import fs from 'fs/promises';
import path from 'path';
import axios from 'axios';
import { fileURLToPath } from 'url';
import { dirname } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Demo configuration
const DESIGN_IMAGES_PATH = path.join(__dirname, '..', '..', 'design', 'images');
const DESIGN_TEXT_PATH = path.join(__dirname, '..', '..', 'design', 'text');
const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8000';
const FRONTEND_URL = process.env.FRONTEND_URL || 'http://localhost:5173';

class FrontendDemoRunner {
    constructor() {
        this.demoGarments = {};
        this.apiClient = null;
        this.performanceMetrics = [];
    }

    async initialize() {
        console.log('🚀 Initializing Frontend Demo Runner');
        console.log('=' * 50);

        await this.loadDemoData();
        this.setupAPIClient();

        console.log(`✅ Demo data loaded: ${Object.keys(this.demoGarments).length} items`);
        console.log(`🌐 API Base URL: ${API_BASE_URL}`);
        console.log(`💻 Frontend URL: ${FRONTEND_URL}`);
    }

    async loadDemoData() {
        const demoItems = {
            'baggy_jeans': {
                title: 'Wide-Leg Star Appliqué Jeans',
                imagePath: path.join(DESIGN_IMAGES_PATH, 'baggy-jeans.jpeg'),
                descriptionFile: path.join(DESIGN_TEXT_PATH, 'baggy-jeans.txt'),
                expectedFilters: {
                    category: 'bottoms',
                    primaryColor: 'blue',
                    style: 'casual',
                    season: 'spring'
                },
                searchTerms: ['wide leg jeans', 'blue denim', 'star applique', 'casual bottoms']
            },
            'pattern_dress': {
                title: 'Geometric Pattern A-Line Dress',
                imagePath: path.join(DESIGN_IMAGES_PATH, 'blue-black-pattern-dress.jpeg'),
                descriptionFile: path.join(DESIGN_TEXT_PATH, 'blue-black-pattern-dress.txt'),
                expectedFilters: {
                    category: 'dresses',
                    primaryColor: 'blue',
                    pattern: 'geometric',
                    style: 'bohemian',
                    season: 'summer'
                },
                searchTerms: ['geometric dress', 'blue pattern', 'a-line dress', 'bohemian style']
            },
            'queen_tshirt': {
                title: 'QUEEN Eagle Graphic Tee',
                imagePath: path.join(DESIGN_IMAGES_PATH, 'queen-tshirt.jpeg'),
                descriptionFile: path.join(DESIGN_TEXT_PATH, 'queen-tshirt.txt'),
                expectedFilters: {
                    category: 'tops',
                    primaryColor: 'cream',
                    style: 'graphic',
                    season: 'summer'
                },
                searchTerms: ['queen tshirt', 'graphic tee', 'eagle shirt', 'cream colored']
            },
            'orange_dress': {
                title: 'Orange Pattern Dress',
                imagePath: path.join(DESIGN_IMAGES_PATH, 'orange-pattern-dress.jpeg'),
                descriptionFile: path.join(DESIGN_TEXT_PATH, 'orange-pattern-dress.txt'),
                expectedFilters: {
                    category: 'dresses',
                    primaryColor: 'orange',
                    pattern: 'floral',
                    season: 'summer'
                },
                searchTerms: ['orange dress', 'floral pattern', 'summer dress', 'bright colors']
            },
            'blue_flower_dress': {
                title: 'Blue Flower Dress',
                imagePath: path.join(DESIGN_IMAGES_PATH, 'blue-flower-dress.jpeg'),
                descriptionFile: path.join(DESIGN_TEXT_PATH, 'blue-flower-dress.txt'),
                expectedFilters: {
                    category: 'dresses',
                    primaryColor: 'blue',
                    pattern: 'floral',
                    season: 'spring'
                },
                searchTerms: ['blue floral dress', 'flower pattern', 'spring dress', 'feminine style']
            }
        };

        // Load descriptions
        for (const [itemId, itemData] of Object.entries(demoItems)) {
            try {
                const description = await fs.readFile(itemData.descriptionFile, 'utf8');
                itemData.description = description.trim();
            } catch (error) {
                console.warn(`⚠️  Description file not found: ${itemData.descriptionFile}`);
                itemData.description = `Demo ${itemData.title}`;
            }
        }

        this.demoGarments = demoItems;
    }

    setupAPIClient() {
        this.apiClient = axios.create({
            baseURL: API_BASE_URL,
            timeout: 10000,
            headers: {
                'Content-Type': 'application/json'
            }
        });

        // Add request/response interceptors for performance monitoring
        this.apiClient.interceptors.request.use(
            (config) => {
                config.metadata = { startTime: Date.now() };
                return config;
            }
        );

        this.apiClient.interceptors.response.use(
            (response) => {
                const endTime = Date.now();
                const duration = endTime - response.config.metadata.startTime;

                this.performanceMetrics.push({
                    endpoint: response.config.url,
                    method: response.config.method.toUpperCase(),
                    duration,
                    status: response.status,
                    timestamp: new Date().toISOString()
                });

                return response;
            },
            (error) => {
                const endTime = Date.now();
                const duration = error.config ? endTime - error.config.metadata.startTime : 0;

                this.performanceMetrics.push({
                    endpoint: error.config?.url || 'unknown',
                    method: error.config?.method?.toUpperCase() || 'UNKNOWN',
                    duration,
                    status: error.response?.status || 0,
                    error: error.message,
                    timestamp: new Date().toISOString()
                });

                return Promise.reject(error);
            }
        );
    }

    async demoTextSearch() {
        console.log('\n🔍 DEMO: Enhanced Text Search API');
        console.log('=' * 40);

        const results = {};

        for (const [itemId, itemData] of Object.entries(this.demoGarments)) {
            console.log(`\n📝 Testing search terms for: ${itemData.title}`);

            for (const searchTerm of itemData.searchTerms) {
                console.log(`  🔍 Query: "${searchTerm}"`);

                try {
                    const searchPayload = {
                        text_query: searchTerm,
                        search_type: 'text',
                        filters: {},
                        limit: 10,
                        include_similarity: true
                    };

                    const response = await this.apiClient.post('/api/v2/search', searchPayload);

                    const { results: searchResults, metadata } = response.data;

                    console.log(`    📊 Results: ${searchResults.length} items`);
                    console.log(`    ⏱️  Response time: ${metadata.search_time_ms}ms`);

                    if (searchResults.length > 0) {
                        const topResult = searchResults[0];
                        console.log(`    🥇 Top result: ${topResult.title || 'Unknown'}`);
                        console.log(`    🎯 Relevance: ${topResult.relevance_score?.toFixed(3) || 'N/A'}`);

                        if (topResult.extracted_properties) {
                            const props = Object.entries(topResult.extracted_properties)
                                .map(([key, value]) => `${key}: ${value}`)
                                .join(', ');
                            console.log(`    🏷️  Properties: ${props}`);
                        }
                    }

                    if (!results[itemId]) results[itemId] = {};
                    results[itemId][searchTerm] = {
                        resultsCount: searchResults.length,
                        responseTime: metadata.search_time_ms,
                        topResult: searchResults[0] || null,
                        apiSuccess: true
                    };

                } catch (error) {
                    console.log(`    ❌ Error: ${error.message}`);
                    if (!results[itemId]) results[itemId] = {};
                    results[itemId][searchTerm] = {
                        apiSuccess: false,
                        error: error.message
                    };
                }
            }
        }

        return results;
    }

    async demoImageSearch() {
        console.log('\n🖼️  DEMO: Visual Image Search API');
        console.log('=' * 40);

        const results = {};

        for (const [itemId, itemData] of Object.entries(this.demoGarments)) {
            console.log(`\n📷 Testing image search for: ${itemData.title}`);

            try {
                // Check if image file exists
                await fs.access(itemData.imagePath);

                // Prepare form data for image upload
                const formData = new FormData();
                const imageBuffer = await fs.readFile(itemData.imagePath);
                const blob = new Blob([imageBuffer], { type: 'image/jpeg' });
                formData.append('image', blob, path.basename(itemData.imagePath));
                formData.append('search_type', 'image');
                formData.append('limit', '10');
                formData.append('include_similarity', 'true');

                const response = await this.apiClient.post('/api/v2/search', formData, {
                    headers: {
                        'Content-Type': 'multipart/form-data'
                    }
                });

                const { results: searchResults, metadata } = response.data;

                console.log(`  📊 Visual similarity results: ${searchResults.length} items`);
                console.log(`  ⏱️  Processing time: ${metadata.search_time_ms}ms`);
                console.log(`  🧠 CLIP embedding generated: ${metadata.used_clip ? '✅' : '❌'}`);

                if (searchResults.length > 0) {
                    console.log(`  🔝 Top 3 similar items:`);
                    for (let i = 0; i < Math.min(3, searchResults.length); i++) {
                        const result = searchResults[i];
                        console.log(`    ${i + 1}. ${result.title || 'Unknown'} (similarity: ${result.similarity_score?.toFixed(3) || 'N/A'})`);
                    }
                }

                results[itemId] = {
                    resultsCount: searchResults.length,
                    processingTime: metadata.search_time_ms,
                    usedCLIP: metadata.used_clip || false,
                    topResults: searchResults.slice(0, 3),
                    apiSuccess: true
                };

            } catch (error) {
                console.log(`  ❌ Error: ${error.message}`);
                results[itemId] = {
                    apiSuccess: false,
                    error: error.message
                };
            }
        }

        return results;
    }

    async demoHybridSearch() {
        console.log('\n🔄 DEMO: Hybrid Search (Text + Image + Filters)');
        console.log('=' * 50);

        const results = {};

        const hybridScenarios = [
            {
                name: 'Blue casual summer wear',
                itemId: 'baggy_jeans',
                textQuery: 'blue casual',
                filters: {
                    primaryColor: 'blue',
                    occasion: 'casual',
                    season: 'summer'
                }
            },
            {
                name: 'Patterned dresses',
                itemId: 'pattern_dress',
                textQuery: 'geometric pattern',
                filters: {
                    category: 'dresses',
                    pattern: 'geometric'
                }
            },
            {
                name: 'Graphic t-shirts',
                itemId: 'queen_tshirt',
                textQuery: 'graphic tee',
                filters: {
                    category: 'tops',
                    style: 'graphic'
                }
            }
        ];

        for (const scenario of hybridScenarios) {
            console.log(`\n🎯 Scenario: ${scenario.name}`);
            console.log(`  📝 Text: "${scenario.textQuery}"`);
            console.log(`  🔍 Filters: ${JSON.stringify(scenario.filters)}`);

            try {
                const itemData = this.demoGarments[scenario.itemId];

                // Prepare hybrid search request
                const searchPayload = {
                    text_query: scenario.textQuery,
                    search_type: 'hybrid',
                    filters: scenario.filters,
                    limit: 20,
                    include_similarity: true,
                    combine_scores: true
                };

                // Add image if available
                let formData;
                try {
                    await fs.access(itemData.imagePath);
                    formData = new FormData();
                    const imageBuffer = await fs.readFile(itemData.imagePath);
                    const blob = new Blob([imageBuffer], { type: 'image/jpeg' });
                    formData.append('image', blob, path.basename(itemData.imagePath));

                    // Add other parameters
                    for (const [key, value] of Object.entries(searchPayload)) {
                        if (key === 'filters') {
                            formData.append(key, JSON.stringify(value));
                        } else {
                            formData.append(key, value.toString());
                        }
                    }

                    console.log(`  📷 Including reference image: ${path.basename(itemData.imagePath)}`);
                } catch {
                    console.log(`  📝 Text + filters only (no reference image)`);
                }

                const response = await this.apiClient.post('/api/v2/search',
                    formData || searchPayload,
                    formData ? { headers: { 'Content-Type': 'multipart/form-data' } } : {}
                );

                const { results: searchResults, metadata } = response.data;

                console.log(`  📊 Hybrid results: ${searchResults.length} items`);
                console.log(`  ⏱️  Total time: ${metadata.search_time_ms}ms`);
                console.log(`  🧮 Score combination: ${metadata.used_hybrid ? '✅' : '❌'}`);

                if (searchResults.length > 0) {
                    console.log(`  🏆 Top results with combined scores:`);
                    for (let i = 0; i < Math.min(3, searchResults.length); i++) {
                        const result = searchResults[i];
                        console.log(`    ${i + 1}. ${result.title || 'Unknown'}`);
                        console.log(`       📊 Combined score: ${result.combined_score?.toFixed(3) || 'N/A'}`);
                        console.log(`       📝 Text relevance: ${result.text_relevance?.toFixed(3) || 'N/A'}`);
                        console.log(`       👁️  Visual similarity: ${result.similarity_score?.toFixed(3) || 'N/A'}`);
                        console.log(`       🎯 Filter match: ${result.filter_score?.toFixed(3) || 'N/A'}`);
                    }
                }

                results[scenario.name] = {
                    resultsCount: searchResults.length,
                    processingTime: metadata.search_time_ms,
                    usedHybrid: metadata.used_hybrid || false,
                    topResults: searchResults.slice(0, 3),
                    apiSuccess: true
                };

            } catch (error) {
                console.log(`  ❌ Error: ${error.message}`);
                results[scenario.name] = {
                    apiSuccess: false,
                    error: error.message
                };
            }
        }

        return results;
    }

    async demoFilteringAndFacets() {
        console.log('\n🏷️  DEMO: Advanced Filtering and Faceted Search');
        console.log('=' * 50);

        const results = {};

        const filterScenarios = [
            {
                name: 'Color-based filtering',
                filters: { primaryColor: 'blue' },
                description: 'Find all blue items'
            },
            {
                name: 'Category + Season filtering',
                filters: { category: 'dresses', season: 'summer' },
                description: 'Summer dresses'
            },
            {
                name: 'Style + Occasion filtering',
                filters: { style: 'casual', occasion: 'everyday' },
                description: 'Casual everyday wear'
            },
            {
                name: 'Multi-property filtering',
                filters: {
                    category: 'tops',
                    primaryColor: 'cream',
                    style: 'graphic',
                    season: 'summer'
                },
                description: 'Cream graphic summer tops'
            }
        ];

        for (const scenario of filterScenarios) {
            console.log(`\n🔍 ${scenario.name}: ${scenario.description}`);

            try {
                // Test faceted search endpoint
                const facetsResponse = await this.apiClient.get('/api/v2/facets', {
                    params: { filters: JSON.stringify(scenario.filters) }
                });

                const facets = facetsResponse.data.facets;
                console.log(`  📈 Available facets:`);

                for (const [facetName, facetData] of Object.entries(facets)) {
                    const values = Object.entries(facetData.values || {})
                        .sort(([,a], [,b]) => b - a)
                        .slice(0, 3)
                        .map(([value, count]) => `${value} (${count})`)
                        .join(', ');

                    console.log(`    ${facetName}: ${values}`);
                }

                // Test filtered search
                const searchResponse = await this.apiClient.post('/api/v2/search', {
                    search_type: 'filter',
                    filters: scenario.filters,
                    limit: 50,
                    include_facets: true
                });

                const { results: searchResults, facets: resultFacets, metadata } = searchResponse.data;

                console.log(`  📊 Filtered results: ${searchResults.length} items`);
                console.log(`  ⏱️  Search time: ${metadata.search_time_ms}ms`);

                if (searchResults.length > 0) {
                    console.log(`  🎯 Sample results:`);
                    for (let i = 0; i < Math.min(3, searchResults.length); i++) {
                        const result = searchResults[i];
                        const props = [];

                        for (const filterKey of Object.keys(scenario.filters)) {
                            const value = result.extracted_properties?.[filterKey];
                            if (value) props.push(`${filterKey}: ${value}`);
                        }

                        console.log(`    ${i + 1}. ${result.title || 'Unknown'}`);
                        console.log(`       Properties: ${props.join(', ') || 'None extracted'}`);
                    }
                }

                results[scenario.name] = {
                    filtersApplied: scenario.filters,
                    resultsCount: searchResults.length,
                    searchTime: metadata.search_time_ms,
                    facetsAvailable: Object.keys(facets).length,
                    apiSuccess: true
                };

            } catch (error) {
                console.log(`  ❌ Error: ${error.message}`);
                results[scenario.name] = {
                    filtersApplied: scenario.filters,
                    apiSuccess: false,
                    error: error.message
                };
            }
        }

        return results;
    }

    async demoPerformanceMetrics() {
        console.log('\n⚡ DEMO: Performance Metrics Analysis');
        console.log('=' * 45);

        const metrics = this.performanceMetrics;

        if (metrics.length === 0) {
            console.log('❌ No performance metrics collected');
            return {};
        }

        // Group by endpoint
        const endpointMetrics = {};
        metrics.forEach(metric => {
            const endpoint = metric.endpoint.replace(/^\/api\/v2/, '');
            if (!endpointMetrics[endpoint]) {
                endpointMetrics[endpoint] = [];
            }
            endpointMetrics[endpoint].push(metric);
        });

        console.log(`📊 Analyzed ${metrics.length} API calls across ${Object.keys(endpointMetrics).length} endpoints:`);

        const performanceSummary = {};

        for (const [endpoint, endpointCalls] of Object.entries(endpointMetrics)) {
            const successfulCalls = endpointCalls.filter(call => call.status >= 200 && call.status < 300);
            const avgDuration = successfulCalls.reduce((sum, call) => sum + call.duration, 0) / successfulCalls.length;
            const minDuration = Math.min(...successfulCalls.map(call => call.duration));
            const maxDuration = Math.max(...successfulCalls.map(call => call.duration));
            const successRate = (successfulCalls.length / endpointCalls.length) * 100;

            console.log(`\n🎯 ${endpoint}:`);
            console.log(`  📞 Calls: ${endpointCalls.length} (${successfulCalls.length} successful)`);
            console.log(`  ⏱️  Avg response time: ${avgDuration.toFixed(1)}ms`);
            console.log(`  🚀 Best: ${minDuration}ms, Worst: ${maxDuration}ms`);
            console.log(`  ✅ Success rate: ${successRate.toFixed(1)}%`);

            // Performance categorization
            let performanceRating;
            if (avgDuration < 100) performanceRating = 'Excellent';
            else if (avgDuration < 300) performanceRating = 'Good';
            else if (avgDuration < 1000) performanceRating = 'Fair';
            else performanceRating = 'Needs Improvement';

            console.log(`  🏆 Performance: ${performanceRating}`);

            performanceSummary[endpoint] = {
                totalCalls: endpointCalls.length,
                successfulCalls: successfulCalls.length,
                averageDuration: avgDuration,
                minDuration,
                maxDuration,
                successRate,
                performanceRating
            };
        }

        // Overall summary
        const overallAvgDuration = metrics.reduce((sum, metric) => sum + metric.duration, 0) / metrics.length;
        const overallSuccessRate = (metrics.filter(m => m.status >= 200 && m.status < 300).length / metrics.length) * 100;

        console.log(`\n📈 OVERALL PERFORMANCE:`);
        console.log(`  🔄 Total API calls: ${metrics.length}`);
        console.log(`  ⏱️  Average response time: ${overallAvgDuration.toFixed(1)}ms`);
        console.log(`  ✅ Overall success rate: ${overallSuccessRate.toFixed(1)}%`);

        return {
            endpointMetrics: performanceSummary,
            overallMetrics: {
                totalCalls: metrics.length,
                averageDuration: overallAvgDuration,
                successRate: overallSuccessRate
            }
        };
    }

    async generateComponentUsageExamples() {
        console.log('\n🧩 DEMO: React Component Usage Examples');
        console.log('=' * 50);

        const examples = {
            enhancedSearch: `
// EnhancedSearch Component Usage Example
import { EnhancedSearch } from '../components/EnhancedSearch';

const SearchPage = () => {
  const [searchResults, setSearchResults] = useState([]);

  const handleSearch = async (searchData) => {
    console.log('Search triggered:', searchData);
    // API call handled internally by component
  };

  return (
    <div className="search-page">
      <EnhancedSearch
        onSearch={handleSearch}
        placeholder="Search for vintage clothes, colors, styles..."
        showAdvancedFilters={true}
        enableImageUpload={true}
        enableVoiceSearch={false}
      />
    </div>
  );
};`,

            searchResults: `
// SearchResults Component Usage Example
import { SearchResults } from '../components/SearchResults';

const ResultsPage = () => {
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);

  return (
    <div className="results-page">
      <SearchResults
        results={results}
        loading={loading}
        onSimilaritySearch={(garmentId) => {
          console.log('Finding similar to:', garmentId);
        }}
        onFilterChange={(filters) => {
          console.log('Filters changed:', filters);
        }}
        showSimilarityButton={true}
        enableFiltering={true}
      />
    </div>
  );
};`,

            imageUpload: `
// ImageUpload Component Usage Example
import { ImageUpload } from '../components/ImageUpload';

const VisualSearchPage = () => {
  const [uploadedImage, setUploadedImage] = useState(null);

  const handleImageUpload = async (imageFile) => {
    console.log('Image uploaded:', imageFile.name);
    setUploadedImage(imageFile);

    // Trigger visual search
    const formData = new FormData();
    formData.append('image', imageFile);
    // API call to search by image...
  };

  return (
    <div className="visual-search">
      <ImageUpload
        onImageUpload={handleImageUpload}
        accept="image/*"
        maxSize={10 * 1024 * 1024} // 10MB
        showPreview={true}
        dragDropText="Drop your fashion image here to find similar items"
      />
    </div>
  );
};`,

            fullIntegration: `
// Complete Integration Example (LandingV2 style)
import { useState } from 'react';
import { EnhancedSearch } from '../components/EnhancedSearch';
import { SearchResults } from '../components/SearchResults';
import { apiClientV2 } from '../api/client-v2';

const FashionSearchApp = () => {
  const [searchResults, setSearchResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchType, setSearchType] = useState('text');

  const handleSearch = async (searchData) => {
    setLoading(true);
    try {
      const results = await apiClientV2.search(searchData);
      setSearchResults(results.results);
    } catch (error) {
      console.error('Search failed:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSimilaritySearch = async (garmentId) => {
    setLoading(true);
    try {
      const results = await apiClientV2.findSimilar(garmentId);
      setSearchResults(results.results);
    } catch (error) {
      console.error('Similarity search failed:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fashion-search-app">
      <header>
        <h1>Prethrift v2.0 - Enhanced Fashion Search</h1>
        <div className="search-type-toggle">
          <button
            className={searchType === 'text' ? 'active' : ''}
            onClick={() => setSearchType('text')}
          >
            Text Search
          </button>
          <button
            className={searchType === 'visual' ? 'active' : ''}
            onClick={() => setSearchType('visual')}
          >
            Visual Search
          </button>
          <button
            className={searchType === 'hybrid' ? 'active' : ''}
            onClick={() => setSearchType('hybrid')}
          >
            Hybrid Search
          </button>
        </div>
      </header>

      <main>
        <EnhancedSearch
          onSearch={handleSearch}
          searchType={searchType}
          showAdvancedFilters={true}
          enableImageUpload={searchType !== 'text'}
        />

        <SearchResults
          results={searchResults}
          loading={loading}
          onSimilaritySearch={handleSimilaritySearch}
          showSimilarityButton={true}
          enableFiltering={true}
        />
      </main>
    </div>
  );
};

export default FashionSearchApp;`
        };

        console.log('📝 Generated React component usage examples:');
        console.log('  ✅ EnhancedSearch component integration');
        console.log('  ✅ SearchResults component integration');
        console.log('  ✅ ImageUpload component integration');
        console.log('  ✅ Complete application integration');

        return examples;
    }

    async runFullDemo(exportResults = false) {
        console.log('🚀 PRETHRIFT FRONTEND V2.0 DEMONSTRATION');
        console.log('=' * 60);
        console.log(`🕐 Demo started at: ${new Date().toISOString()}`);

        const demoResults = {
            demoMetadata: {
                timestamp: new Date().toISOString(),
                apiBaseUrl: API_BASE_URL,
                frontendUrl: FRONTEND_URL,
                demoGarmentsCount: Object.keys(this.demoGarments).length
            },
            textSearch: await this.demoTextSearch(),
            imageSearch: await this.demoImageSearch(),
            hybridSearch: await this.demoHybridSearch(),
            filteringAndFacets: await this.demoFilteringAndFacets(),
            performanceMetrics: await this.demoPerformanceMetrics(),
            componentExamples: await this.generateComponentUsageExamples()
        };

        console.log('\n📊 FRONTEND DEMO SUMMARY');
        console.log('=' * 40);

        // API Health Summary
        const totalRequests = this.performanceMetrics.length;
        const successfulRequests = this.performanceMetrics.filter(m => m.status >= 200 && m.status < 300).length;
        const avgResponseTime = this.performanceMetrics.reduce((sum, m) => sum + m.duration, 0) / totalRequests;

        console.log(`🌐 API Integration:`);
        console.log(`  📞 Total requests: ${totalRequests}`);
        console.log(`  ✅ Success rate: ${((successfulRequests / totalRequests) * 100).toFixed(1)}%`);
        console.log(`  ⏱️  Avg response time: ${avgResponseTime.toFixed(1)}ms`);

        // Feature Coverage Summary
        const featureTests = [
            ['Text Search', demoResults.textSearch],
            ['Image Search', demoResults.imageSearch],
            ['Hybrid Search', demoResults.hybridSearch],
            ['Filtering & Facets', demoResults.filteringAndFacets]
        ];

        console.log(`\n🧪 Feature Test Coverage:`);
        featureTests.forEach(([featureName, results]) => {
            const testCount = Object.keys(results).length;
            const successfulTests = Object.values(results).filter(r => r.apiSuccess !== false).length;
            console.log(`  ${featureName}: ${successfulTests}/${testCount} tests passed`);
        });

        if (exportResults) {
            const outputFile = `frontend_demo_results_${new Date().toISOString().replace(/[:.]/g, '-')}.json`;
            await fs.writeFile(outputFile, JSON.stringify(demoResults, null, 2));
            console.log(`💾 Results exported to: ${outputFile}`);
        }

        console.log('\n✅ Frontend demo completed successfully!');
        console.log('\n🚀 Next Steps:');
        console.log('  1. Start the frontend development server: npm run dev');
        console.log('  2. Navigate to the LandingV2 page to test interactively');
        console.log('  3. Upload design images for visual search testing');
        console.log('  4. Try different search combinations and filters');

        return demoResults;
    }
}

// CLI handling
async function main() {
    const args = process.argv.slice(2);
    const testCase = args.find(arg => arg.startsWith('--test-case='))?.split('=')[1] || 'all';
    const interactive = args.includes('--interactive');
    const exportResults = args.includes('--export-results');
    const verbose = args.includes('--verbose');

    try {
        const demoRunner = new FrontendDemoRunner();
        await demoRunner.initialize();

        let results;
        if (testCase === 'all') {
            results = await demoRunner.runFullDemo(exportResults);
        } else if (testCase === 'text') {
            results = await demoRunner.demoTextSearch();
        } else if (testCase === 'visual') {
            results = await demoRunner.demoImageSearch();
        } else if (testCase === 'hybrid') {
            results = await demoRunner.demoHybridSearch();
        } else if (testCase === 'filters') {
            results = await demoRunner.demoFilteringAndFacets();
        } else if (testCase === 'performance') {
            results = await demoRunner.demoPerformanceMetrics();
        } else if (testCase === 'components') {
            results = await demoRunner.generateComponentUsageExamples();
        }

        if (verbose) {
            console.log('\n📄 Detailed Results:');
            console.log(JSON.stringify(results, null, 2));
        }

        if (interactive) {
            console.log('\n🎮 Interactive Mode: Open your browser to', FRONTEND_URL);
            console.log('Try the demo scenarios manually using the web interface!');
        }

    } catch (error) {
        console.error('❌ Frontend demo failed:', error.message);
        if (verbose) {
            console.error(error.stack);
        }
        process.exit(1);
    }
}

// Run if this is the main module
if (import.meta.url === `file://${process.argv[1]}`) {
    main();
}

// Export for programmatic use
export { FrontendDemoRunner };
