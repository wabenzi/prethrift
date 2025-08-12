#!/bin/bash

# Prethrift v2.0 Demo Launcher Script
# This script helps you run comprehensive demonstrations of the enhanced search capabilities

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
BACKEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/backend" && pwd)"
FRONTEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/frontend/web" && pwd)"
DEMO_DATA_READY_FILE="${BACKEND_DIR}/.demo_data_ready"

echo -e "${CYAN}🚀 PRETHRIFT V2.0 DEMONSTRATION LAUNCHER${NC}"
echo -e "${CYAN}==========================================${NC}"
echo ""

# Function to print colored headers
print_header() {
    echo -e "${PURPLE}$1${NC}"
    echo -e "${PURPLE}$(printf '=%.0s' $(seq 1 ${#1}))${NC}"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check demo prerequisites
check_prerequisites() {
    print_header "🔍 Checking Prerequisites"

    local missing_deps=0

    # Check Python
    if command_exists python3; then
        echo -e "✅ Python 3: $(python3 --version)"
    else
        echo -e "❌ Python 3 not found"
        missing_deps=1
    fi

    # Check Node.js
    if command_exists node; then
        echo -e "✅ Node.js: $(node --version)"
    else
        echo -e "❌ Node.js not found"
        missing_deps=1
    fi

    # Check PostgreSQL
    if command_exists psql; then
        echo -e "✅ PostgreSQL: Available"
    else
        echo -e "⚠️  PostgreSQL client not found (may affect database demos)"
    fi

    # Check required files
    local required_files=(
        "${BACKEND_DIR}/app/main.py"
        "${BACKEND_DIR}/demo/demo_enhanced_search.py"
        "${BACKEND_DIR}/demo/setup_demo_data.py"
        "${FRONTEND_DIR}/demo_frontend_integration.js"
        "${BACKEND_DIR}/../design/images"
        "${BACKEND_DIR}/../design/text"
    )

    for file in "${required_files[@]}"; do
        if [ -e "$file" ]; then
            echo -e "✅ Found: $(basename "$file")"
        else
            echo -e "❌ Missing: $file"
            missing_deps=1
        fi
    done

    if [ $missing_deps -eq 1 ]; then
        echo -e "\n${RED}❌ Missing prerequisites. Please install missing dependencies.${NC}"
        exit 1
    fi

    echo -e "\n${GREEN}✅ All prerequisites satisfied!${NC}"
}

# Function to setup demo data
setup_demo_data() {
    print_header "🗄️  Setting Up Demo Data"

    cd "$BACKEND_DIR"

    if [ -f "$DEMO_DATA_READY_FILE" ] && [ "$1" != "--force" ]; then
        echo -e "✅ Demo data already set up. Use --force to recreate."
        return 0
    fi

    echo -e "${YELLOW}📦 Installing Python dependencies...${NC}"
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
    fi

    echo -e "\n${YELLOW}🗃️  Setting up demo database...${NC}"
    python3 demo/setup_demo_data.py --reset-db --verbose

    if [ $? -eq 0 ]; then
        touch "$DEMO_DATA_READY_FILE"
        echo -e "\n${GREEN}✅ Demo data setup completed!${NC}"
    else
        echo -e "\n${RED}❌ Demo data setup failed!${NC}"
        exit 1
    fi
}

# Function to run backend demos
run_backend_demo() {
    print_header "🔧 Running Backend Demonstrations"

    cd "$BACKEND_DIR"

    local test_case="${1:-all}"

    echo -e "${YELLOW}🚀 Launching backend demo (test case: $test_case)...${NC}"
    python3 demo/demo_enhanced_search.py --test-case="$test_case" --verbose --export-results

    echo -e "\n${GREEN}✅ Backend demo completed!${NC}"
}

# Function to run frontend demos
run_frontend_demo() {
    print_header "💻 Running Frontend Demonstrations"

    cd "$FRONTEND_DIR"

    local test_case="${1:-all}"

    # Check if node_modules exists
    if [ ! -d "node_modules" ]; then
        echo -e "${YELLOW}📦 Installing frontend dependencies...${NC}"
        npm install
    fi

    echo -e "${YELLOW}🌐 Launching frontend demo (test case: $test_case)...${NC}"
    node demo_frontend_integration.js --test-case="$test_case" --export-results

    echo -e "\n${GREEN}✅ Frontend demo completed!${NC}"
}

# Function to start development servers
start_dev_servers() {
    print_header "🖥️  Starting Development Servers"

    echo -e "${YELLOW}🔧 Starting backend API server...${NC}"
    cd "$BACKEND_DIR"

    # Start backend in background
    python3 -m uvicorn app.main:app --reload --port 8000 &
    BACKEND_PID=$!
    echo -e "✅ Backend server started (PID: $BACKEND_PID)"

    # Wait a moment for backend to start
    sleep 3

    echo -e "\n${YELLOW}🌐 Starting frontend development server...${NC}"
    cd "$FRONTEND_DIR"

    # Start frontend in background
    npm run dev &
    FRONTEND_PID=$!
    echo -e "✅ Frontend server started (PID: $FRONTEND_PID)"

    echo -e "\n${GREEN}🎉 Development servers are running!${NC}"
    echo -e "📍 Backend API: ${BLUE}http://localhost:8000${NC}"
    echo -e "📍 Frontend App: ${BLUE}http://localhost:5173${NC}"
    echo -e "📍 API Docs: ${BLUE}http://localhost:8000/docs${NC}"

    echo -e "\n${CYAN}Press Ctrl+C to stop both servers${NC}"

    # Handle cleanup on exit
    trap 'echo -e "\n${YELLOW}🛑 Stopping servers...${NC}"; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit' INT

    # Wait for user to stop
    wait
}

# Function to run interactive demo
run_interactive_demo() {
    print_header "🎮 Interactive Demo Mode"

    echo -e "${CYAN}This will start both backend and frontend servers for interactive testing.${NC}"
    echo -e "${CYAN}You can then test the v2.0 search features in your browser.${NC}"
    echo ""

    read -p "Start interactive demo? (y/N): " -n 1 -r
    echo

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        start_dev_servers
    else
        echo -e "${YELLOW}Interactive demo cancelled.${NC}"
    fi
}

# Function to run comprehensive demos
run_comprehensive_demo() {
    print_header "🎯 Comprehensive Demo Suite"

    echo -e "${CYAN}This will run all demo scenarios:${NC}"
    echo -e "  1. Setup demo data"
    echo -e "  2. Backend API demonstrations"
    echo -e "  3. Frontend integration demonstrations"
    echo -e "  4. Performance benchmarks"
    echo ""

    read -p "Run comprehensive demo? (y/N): " -n 1 -r
    echo

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        setup_demo_data
        echo ""
        run_backend_demo "all"
        echo ""
        run_frontend_demo "all"

        echo -e "\n${GREEN}🎉 Comprehensive demo completed!${NC}"
        echo -e "📊 Check the generated *_results_*.json files for detailed metrics."
    else
        echo -e "${YELLOW}Comprehensive demo cancelled.${NC}"
    fi
}

# Function to show usage
show_usage() {
    echo -e "${CYAN}Usage: $0 [COMMAND] [OPTIONS]${NC}"
    echo ""
    echo -e "${YELLOW}Commands:${NC}"
    echo -e "  ${GREEN}check${NC}           Check prerequisites"
    echo -e "  ${GREEN}setup${NC}           Setup demo data"
    echo -e "  ${GREEN}backend${NC}         Run backend demonstrations"
    echo -e "  ${GREEN}frontend${NC}        Run frontend demonstrations"
    echo -e "  ${GREEN}servers${NC}         Start development servers"
    echo -e "  ${GREEN}interactive${NC}     Run interactive demo mode"
    echo -e "  ${GREEN}comprehensive${NC}   Run all demonstrations"
    echo -e "  ${GREEN}help${NC}            Show this help message"
    echo ""
    echo -e "${YELLOW}Test Cases (for backend/frontend):${NC}"
    echo -e "  ${GREEN}text${NC}            Text search demonstrations"
    echo -e "  ${GREEN}visual${NC}          Visual similarity search"
    echo -e "  ${GREEN}hybrid${NC}          Hybrid search (text + image + filters)"
    echo -e "  ${GREEN}ontology${NC}        Ontology extraction demos"
    echo -e "  ${GREEN}performance${NC}     Performance benchmarks"
    echo -e "  ${GREEN}all${NC}             All test cases (default)"
    echo ""
    echo -e "${YELLOW}Examples:${NC}"
    echo -e "  ${CYAN}$0 setup${NC}                    # Setup demo data"
    echo -e "  ${CYAN}$0 backend text${NC}             # Run text search demos"
    echo -e "  ${CYAN}$0 frontend visual${NC}          # Run visual search demos"
    echo -e "  ${CYAN}$0 comprehensive${NC}            # Run everything"
    echo -e "  ${CYAN}$0 interactive${NC}              # Start interactive mode"
}

# Main script logic
main() {
    case "${1:-help}" in
        "check")
            check_prerequisites
            ;;
        "setup")
            check_prerequisites
            setup_demo_data "${2:-}"
            ;;
        "backend")
            check_prerequisites
            setup_demo_data
            run_backend_demo "${2:-all}"
            ;;
        "frontend")
            check_prerequisites
            setup_demo_data
            run_frontend_demo "${2:-all}"
            ;;
        "servers")
            check_prerequisites
            setup_demo_data
            start_dev_servers
            ;;
        "interactive")
            check_prerequisites
            setup_demo_data
            run_interactive_demo
            ;;
        "comprehensive")
            check_prerequisites
            run_comprehensive_demo
            ;;
        "help"|"--help"|"-h")
            show_usage
            ;;
        *)
            echo -e "${RED}❌ Unknown command: $1${NC}"
            echo ""
            show_usage
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"
