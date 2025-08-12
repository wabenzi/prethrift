# Demo Scripts and Data

This directory contains all demonstration scripts, data files, and examples for the PreThrift v2.0 backend.

## Demo Scripts

### Core Demo Programs
- **`demo_enhanced_search.py`** - Comprehensive search demonstration showcasing text search, visual similarity, ontology extraction, and hybrid search capabilities
- **`setup_demo_data.py`** - Demo data setup script that creates sample garments with descriptions, ontology properties, and CLIP embeddings

### Analysis and Migration
- **`demo_local_cv.py`** - Local computer vision demonstration comparing local CLIP vs OpenAI GPT-4 vision
- **`demo_migration_path.py`** - Production migration demonstration showing v1.0 to v2.0 upgrade path

## Demo Data Files

### Generated Data
- **`.demo_data_ready`** - Flag file indicating demo data has been set up
- **`demo_results_*.json`** - Generated results from demo runs with timestamps
- **`demo_search_examples.json`** - Example search queries and filter combinations

## Quick Start

### 1. Set Up Demo Data
```bash
# Basic setup
python demo/setup_demo_data.py

# Full setup with fresh database and embeddings
python demo/setup_demo_data.py --reset-db --verbose

# Skip CLIP embeddings for faster setup
python demo/setup_demo_data.py --no-embeddings
```

### 2. Run Search Demonstrations
```bash
# Full demonstration suite
python demo/demo_enhanced_search.py

# Specific test cases
python demo/demo_enhanced_search.py --test-case text
python demo/demo_enhanced_search.py --test-case visual
python demo/demo_enhanced_search.py --test-case ontology
python demo/demo_enhanced_search.py --test-case hybrid

# Export results for analysis
python demo/demo_enhanced_search.py --verbose --export-results
```

### 3. Computer Vision Comparison
```bash
# Compare local CV vs OpenAI
python demo/demo_local_cv.py
```

### 4. Migration Demonstration
```bash
# Show v1.0 to v2.0 migration path
python demo/demo_migration_path.py
```

## Demo Data Structure

The demo creates sample garments with:
- **Rich metadata** - Titles, brands, prices, sizes, conditions
- **Text descriptions** - Loaded from `../design/text/` files
- **Ontology properties** - Category, color, material, style, pattern, etc.
- **CLIP embeddings** - Visual similarity vectors from `../design/images/`
- **Search examples** - Comprehensive test queries for different search types

## Integration with Main Demo

These scripts are orchestrated by the main demo script at the project root:
```bash
# From project root
./demo.sh
```

See the main project documentation for complete demo workflows and integration testing.
