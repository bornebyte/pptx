#!/bin/bash

# API Endpoint Testing Script
# Tests all endpoints with comprehensive parameter coverage

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"
BASE_URL="${BASE_URL:-http://localhost:5000}"
API_KEY="${API_KEY:-}"
TEMP_DIR=$(mktemp -d)
TEST_RESULTS=()
PASSED=0
FAILED=0

# Cleanup function
cleanup() {
    rm -rf "$TEMP_DIR"
}
trap cleanup EXIT

# Helper functions
print_header() {
    echo -e "\n${CYAN}========================================${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${CYAN}========================================${NC}"
}

print_test() {
    echo -e "${BLUE}[TEST]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[✓ PASS]${NC} $1"
    ((PASSED++))
    TEST_RESULTS+=("✓ $1")
}

print_fail() {
    echo -e "${RED}[✗ FAIL]${NC} $1"
    ((FAILED++))
    TEST_RESULTS+=("✗ $1")
}

print_info() {
    echo -e "${YELLOW}[INFO]${NC} $1"
}

# Check if server is running
check_server() {
    print_header "Checking Server Status"
    if curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/health" | grep -q "200"; then
        print_success "Server is running at $BASE_URL"
        return 0
    else
        print_fail "Server is not running at $BASE_URL"
        echo "Please start the server first with: python main.py"
        exit 1
    fi
}

# Build headers
get_headers() {
    local headers="-H 'Content-Type: application/json'"
    if [ -n "$API_KEY" ]; then
        headers="$headers -H 'X-API-Key: $API_KEY'"
    fi
    echo "$headers"
}

# Test 1: Health Check
test_health() {
    print_header "Test 1: Health Check Endpoint"
    print_test "GET /health"
    
    response=$(curl -s -w "\n%{http_code}" "$BASE_URL/health")
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" = "200" ]; then
        print_success "Health check returned 200"
        echo -e "${MAGENTA}Response:${NC} $body"
    else
        print_fail "Health check failed with status $http_code"
    fi
}

# Test 2: Generate PPT - Single Student
test_generate_ppt_single() {
    print_header "Test 2: Generate PPT - Single Student"
    print_test "POST /generate_ppt (single student)"
    
    json_data=$(cat <<'EOF'
{
    "meta": {
        "title": "Test Presentation",
        "subtitle": "API Test",
        "author": "Test Author"
    },
    "slides": [
        {
            "type": "title"
        },
        {
            "type": "content",
            "title": "Test Slide",
            "subtitle": "Testing Content",
            "blocks": [
                {
                    "kind": "paragraph",
                    "text": "This is a test paragraph."
                },
                {
                    "kind": "bullets",
                    "items": ["Point 1", "Point 2", "Point 3"]
                }
            ]
        }
    ]
}
EOF
)
    
    payload=$(cat <<EOF
{
    "file_name": "test_single_student",
    "json_data": $(echo "$json_data" | jq -c -R -s '.'),
    "jain_data": {
        "enabled": true,
        "type": "single",
        "college_name": "Test College",
        "title": "Test Presentation Title",
        "student_name": "John Doe",
        "usn": "TEST001",
        "course": "BCA",
        "semester": "5th",
        "professor": "Prof. Smith"
    }
}
EOF
)
    
    response=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/generate_ppt" \
        -H "Content-Type: application/json" \
        -d "$payload" \
        -o "$TEMP_DIR/test_single.pptx")
    
    http_code=$(echo "$response" | tail -n1)
    
    if [ "$http_code" = "200" ] && [ -f "$TEMP_DIR/test_single.pptx" ]; then
        file_size=$(stat -f%z "$TEMP_DIR/test_single.pptx" 2>/dev/null || stat -c%s "$TEMP_DIR/test_single.pptx")
        print_success "PPT generated successfully (size: $file_size bytes)"
    else
        print_fail "PPT generation failed with status $http_code"
    fi
}

# Test 3: Generate PPT - Group Students
test_generate_ppt_group() {
    print_header "Test 3: Generate PPT - Group Students"
    print_test "POST /generate_ppt (group students)"
    
    json_data=$(cat <<'EOF'
{
    "meta": {
        "title": "Group Project",
        "subtitle": "Team Presentation"
    },
    "slides": [
        {
            "type": "title"
        },
        {
            "type": "content",
            "title": "Team Work",
            "blocks": [
                {
                    "kind": "paragraph",
                    "text": "This is a group presentation."
                }
            ]
        }
    ]
}
EOF
)
    
    payload=$(cat <<EOF
{
    "file_name": "test_group_students",
    "json_data": $(echo "$json_data" | jq -c -R -s '.'),
    "jain_data": {
        "enabled": true,
        "type": "group",
        "college_name": "Test College",
        "title": "Group Project Presentation",
        "students": [
            {"name": "Alice Johnson", "usn": "TEST101"},
            {"name": "Bob Smith", "usn": "TEST102"},
            {"name": "Charlie Brown", "usn": "TEST103"}
        ],
        "professor": "Prof. Johnson"
    }
}
EOF
)
    
    response=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/generate_ppt" \
        -H "Content-Type: application/json" \
        -d "$payload" \
        -o "$TEMP_DIR/test_group.pptx")
    
    http_code=$(echo "$response" | tail -n1)
    
    if [ "$http_code" = "200" ] && [ -f "$TEMP_DIR/test_group.pptx" ]; then
        file_size=$(stat -f%z "$TEMP_DIR/test_group.pptx" 2>/dev/null || stat -c%s "$TEMP_DIR/test_group.pptx")
        print_success "Group PPT generated successfully (size: $file_size bytes)"
    else
        print_fail "Group PPT generation failed with status $http_code"
    fi
}

# Test 4: List Generations - Basic
test_list_generations_basic() {
    print_header "Test 4: List Generations - Basic"
    print_test "GET /api/generations"
    
    headers=""
    if [ -n "$API_KEY" ]; then
        headers="-H 'X-API-Key: $API_KEY'"
    fi
    
    response=$(curl -s -w "\n%{http_code}" $headers "$BASE_URL/api/generations")
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" = "200" ]; then
        total=$(echo "$body" | jq -r '.total')
        print_success "Listed generations (total: $total)"
        echo -e "${MAGENTA}Response preview:${NC} $(echo "$body" | jq -c '{total, limit, offset, items: .items[0:2]}')"
    else
        print_fail "List generations failed with status $http_code"
    fi
}

# Test 5: List Generations - With Filters
test_list_generations_filters() {
    print_header "Test 5: List Generations - With Filters"
    
    # Test with limit and offset
    print_test "GET /api/generations?limit=5&offset=0"
    headers=""
    if [ -n "$API_KEY" ]; then
        headers="-H 'X-API-Key: $API_KEY'"
    fi
    
    response=$(curl -s -w "\n%{http_code}" $headers "$BASE_URL/api/generations?limit=5&offset=0")
    http_code=$(echo "$response" | tail -n1)
    
    if [ "$http_code" = "200" ]; then
        print_success "Pagination test passed"
    else
        print_fail "Pagination test failed"
    fi
    
    # Test with status filter
    print_test "GET /api/generations?status=success"
    response=$(curl -s -w "\n%{http_code}" $headers "$BASE_URL/api/generations?status=success")
    http_code=$(echo "$response" | tail -n1)
    
    if [ "$http_code" = "200" ]; then
        print_success "Status filter test passed"
    else
        print_fail "Status filter test failed"
    fi
    
    # Test with student type filter
    print_test "GET /api/generations?student_type=single"
    response=$(curl -s -w "\n%{http_code}" $headers "$BASE_URL/api/generations?student_type=single")
    http_code=$(echo "$response" | tail -n1)
    
    if [ "$http_code" = "200" ]; then
        print_success "Student type filter test passed"
    else
        print_fail "Student type filter test failed"
    fi
    
    # Test with sorting
    print_test "GET /api/generations?sort_by=timestamp&sort_dir=desc"
    response=$(curl -s -w "\n%{http_code}" $headers "$BASE_URL/api/generations?sort_by=timestamp&sort_dir=desc")
    http_code=$(echo "$response" | tail -n1)
    
    if [ "$http_code" = "200" ]; then
        print_success "Sorting test passed"
    else
        print_fail "Sorting test failed"
    fi
    
    # Test with global search
    print_test "GET /api/generations?q=test"
    response=$(curl -s -w "\n%{http_code}" $headers "$BASE_URL/api/generations?q=test")
    http_code=$(echo "$response" | tail -n1)
    
    if [ "$http_code" = "200" ]; then
        print_success "Global search test passed"
    else
        print_fail "Global search test failed"
    fi
}

# Test 6: Get Generation by ID
test_get_generation_by_id() {
    print_header "Test 6: Get Generation by ID"
    
    headers=""
    if [ -n "$API_KEY" ]; then
        headers="-H 'X-API-Key: $API_KEY'"
    fi
    
    # First get the list to find an ID
    response=$(curl -s $headers "$BASE_URL/api/generations?limit=1")
    gen_id=$(echo "$response" | jq -r '.items[0].id // empty')
    
    if [ -n "$gen_id" ]; then
        print_test "GET /api/generations/$gen_id"
        response=$(curl -s -w "\n%{http_code}" $headers "$BASE_URL/api/generations/$gen_id")
        http_code=$(echo "$response" | tail -n1)
        body=$(echo "$response" | sed '$d')
        
        if [ "$http_code" = "200" ]; then
            print_success "Retrieved generation by ID: $gen_id"
            echo -e "${MAGENTA}Generation details:${NC} $(echo "$body" | jq -c '{id, file_name, status, num_slides}')"
        else
            print_fail "Get generation by ID failed with status $http_code"
        fi
    else
        print_info "No generations found, skipping ID test"
    fi
}

# Test 7: Export Generations
test_export_generations() {
    print_header "Test 7: Export Generations"
    
    headers=""
    if [ -n "$API_KEY" ]; then
        headers="-H 'X-API-Key: $API_KEY'"
    fi
    
    # Test CSV export
    print_test "GET /api/generations/export?format=csv&limit=10"
    response=$(curl -s -w "\n%{http_code}" $headers "$BASE_URL/api/generations/export?format=csv&limit=10" \
        -o "$TEMP_DIR/export.csv")
    http_code=$(echo "$response" | tail -n1)
    
    if [ "$http_code" = "200" ] && [ -f "$TEMP_DIR/export.csv" ]; then
        lines=$(wc -l < "$TEMP_DIR/export.csv")
        print_success "CSV export successful ($lines lines)"
    else
        print_fail "CSV export failed with status $http_code"
    fi
    
    # Test JSON export
    print_test "GET /api/generations/export?format=json&limit=10"
    response=$(curl -s -w "\n%{http_code}" $headers "$BASE_URL/api/generations/export?format=json&limit=10")
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" = "200" ]; then
        count=$(echo "$body" | jq -r '.count // 0')
        print_success "JSON export successful ($count records)"
    else
        print_fail "JSON export failed with status $http_code"
    fi
}

# Test 8: Submit Feedback - All Categories
test_submit_feedback() {
    print_header "Test 8: Submit Feedback"
    
    categories=("praise" "feature" "bug" "improvement" "other")
    
    for category in "${categories[@]}"; do
        print_test "POST /api/feedback (category: $category)"
        
        payload=$(cat <<EOF
{
    "feedback_text": "This is a test feedback for category: $category",
    "rating": $((RANDOM % 5 + 1)),
    "user_email": "test_${category}@example.com",
    "category": "$category"
}
EOF
)
        
        response=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/feedback" \
            -H "Content-Type: application/json" \
            -d "$payload")
        
        http_code=$(echo "$response" | tail -n1)
        body=$(echo "$response" | sed '$d')
        
        if [ "$http_code" = "201" ]; then
            feedback_id=$(echo "$body" | jq -r '.feedback_id')
            print_success "Feedback submitted ($category) - ID: $feedback_id"
        else
            print_fail "Feedback submission failed ($category) with status $http_code"
        fi
    done
}

# Test 9: List Feedbacks - Basic
test_list_feedbacks_basic() {
    print_header "Test 9: List Feedbacks - Basic"
    print_test "GET /api/feedbacks"
    
    response=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/feedbacks")
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" = "200" ]; then
        total=$(echo "$body" | jq -r '.total')
        print_success "Listed feedbacks (total: $total)"
        echo -e "${MAGENTA}Response preview:${NC} $(echo "$body" | jq -c '{total, limit, offset, items: .items[0:2]}')"
    else
        print_fail "List feedbacks failed with status $http_code"
    fi
}

# Test 10: List Feedbacks - With Filters
test_list_feedbacks_filters() {
    print_header "Test 10: List Feedbacks - With Filters"
    
    # Test with limit and offset
    print_test "GET /api/feedbacks?limit=5&offset=0"
    response=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/feedbacks?limit=5&offset=0")
    http_code=$(echo "$response" | tail -n1)
    
    if [ "$http_code" = "200" ]; then
        print_success "Pagination test passed"
    else
        print_fail "Pagination test failed"
    fi
    
    # Test with category filter
    print_test "GET /api/feedbacks?category=praise"
    response=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/feedbacks?category=praise")
    http_code=$(echo "$response" | tail -n1)
    
    if [ "$http_code" = "200" ]; then
        print_success "Category filter test passed"
    else
        print_fail "Category filter test failed"
    fi
    
    # Test with rating filters
    print_test "GET /api/feedbacks?min_rating=4&max_rating=5"
    response=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/feedbacks?min_rating=4&max_rating=5")
    http_code=$(echo "$response" | tail -n1)
    
    if [ "$http_code" = "200" ]; then
        print_success "Rating filter test passed"
    else
        print_fail "Rating filter test failed"
    fi
    
    # Test with status filter
    print_test "GET /api/feedbacks?status=new"
    response=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/feedbacks?status=new")
    http_code=$(echo "$response" | tail -n1)
    
    if [ "$http_code" = "200" ]; then
        print_success "Status filter test passed"
    else
        print_fail "Status filter test failed"
    fi
    
    # Test with sorting
    print_test "GET /api/feedbacks?sort_by=rating&sort_dir=desc"
    response=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/feedbacks?sort_by=rating&sort_dir=desc")
    http_code=$(echo "$response" | tail -n1)
    
    if [ "$http_code" = "200" ]; then
        print_success "Sorting test passed"
    else
        print_fail "Sorting test failed"
    fi
    
    # Test with global search
    print_test "GET /api/feedbacks?q=test"
    response=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/feedbacks?q=test")
    http_code=$(echo "$response" | tail -n1)
    
    if [ "$http_code" = "200" ]; then
        print_success "Global search test passed"
    else
        print_fail "Global search test failed"
    fi
}

# Test 11: Get Feedback by ID
test_get_feedback_by_id() {
    print_header "Test 11: Get Feedback by ID"
    
    # First get the list to find an ID
    response=$(curl -s "$BASE_URL/api/feedbacks?limit=1")
    feedback_id=$(echo "$response" | jq -r '.items[0].id // empty')
    
    if [ -n "$feedback_id" ]; then
        print_test "GET /api/feedbacks/$feedback_id"
        response=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/feedbacks/$feedback_id")
        http_code=$(echo "$response" | tail -n1)
        body=$(echo "$response" | sed '$d')
        
        if [ "$http_code" = "200" ]; then
            print_success "Retrieved feedback by ID: $feedback_id"
            echo -e "${MAGENTA}Feedback details:${NC} $(echo "$body" | jq -c '{id, category, rating, status}')"
        else
            print_fail "Get feedback by ID failed with status $http_code"
        fi
    else
        print_info "No feedbacks found, skipping ID test"
    fi
}

# Test 12: Update Feedback
test_update_feedback() {
    print_header "Test 12: Update Feedback"
    
    # First get a feedback ID
    response=$(curl -s "$BASE_URL/api/feedbacks?limit=1")
    feedback_id=$(echo "$response" | jq -r '.items[0].id // empty')
    
    if [ -n "$feedback_id" ]; then
        print_test "PATCH /api/feedbacks/$feedback_id"
        
        payload=$(cat <<EOF
{
    "status": "reviewed",
    "category": "improvement"
}
EOF
)
        
        response=$(curl -s -w "\n%{http_code}" -X PATCH "$BASE_URL/api/feedbacks/$feedback_id" \
            -H "Content-Type: application/json" \
            -d "$payload")
        
        http_code=$(echo "$response" | tail -n1)
        body=$(echo "$response" | sed '$d')
        
        if [ "$http_code" = "200" ]; then
            print_success "Updated feedback ID: $feedback_id"
            echo -e "${MAGENTA}Updated details:${NC} $(echo "$body" | jq -c '{id, status, category}')"
        else
            print_fail "Update feedback failed with status $http_code"
        fi
        
        # Test updating to different statuses
        statuses=("resolved" "archived")
        for status in "${statuses[@]}"; do
            print_test "PATCH /api/feedbacks/$feedback_id (status: $status)"
            
            payload=$(cat <<EOF
{
    "status": "$status"
}
EOF
)
            
            response=$(curl -s -w "\n%{http_code}" -X PATCH "$BASE_URL/api/feedbacks/$feedback_id" \
                -H "Content-Type: application/json" \
                -d "$payload")
            
            http_code=$(echo "$response" | tail -n1)
            
            if [ "$http_code" = "200" ]; then
                print_success "Updated feedback status to: $status"
            else
                print_fail "Update to status $status failed"
            fi
        done
    else
        print_info "No feedbacks found, skipping update test"
    fi
}

# Test 13: Export Feedbacks
test_export_feedbacks() {
    print_header "Test 13: Export Feedbacks"
    
    # Test CSV export
    print_test "GET /api/feedbacks/export?format=csv&limit=100"
    response=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/feedbacks/export?format=csv&limit=100" \
        -o "$TEMP_DIR/feedbacks_export.csv")
    http_code=$(echo "$response" | tail -n1)
    
    if [ "$http_code" = "200" ] && [ -f "$TEMP_DIR/feedbacks_export.csv" ]; then
        lines=$(wc -l < "$TEMP_DIR/feedbacks_export.csv")
        print_success "Feedback CSV export successful ($lines lines)"
    else
        print_fail "Feedback CSV export failed with status $http_code"
    fi
    
    # Test JSON export
    print_test "GET /api/feedbacks/export?format=json&limit=100"
    response=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/feedbacks/export?format=json&limit=100")
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" = "200" ]; then
        count=$(echo "$body" | jq -r '.count // 0')
        print_success "Feedback JSON export successful ($count records)"
    else
        print_fail "Feedback JSON export failed with status $http_code"
    fi
}

# Test 14: Edge Cases and Error Handling
test_edge_cases() {
    print_header "Test 14: Edge Cases and Error Handling"
    
    # Test invalid feedback ID
    print_test "GET /api/feedbacks/999999 (non-existent ID)"
    response=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/feedbacks/999999")
    http_code=$(echo "$response" | tail -n1)
    
    if [ "$http_code" = "404" ]; then
        print_success "404 error handling works correctly"
    else
        print_fail "Expected 404, got $http_code"
    fi
    
    # Test invalid generation ID
    print_test "GET /api/generations/999999 (non-existent ID)"
    headers=""
    if [ -n "$API_KEY" ]; then
        headers="-H 'X-API-Key: $API_KEY'"
    fi
    response=$(curl -s -w "\n%{http_code}" $headers "$BASE_URL/api/generations/999999")
    http_code=$(echo "$response" | tail -n1)
    
    if [ "$http_code" = "404" ]; then
        print_success "404 error handling works correctly for generations"
    else
        print_fail "Expected 404, got $http_code"
    fi
    
    # Test missing required feedback field
    print_test "POST /api/feedback (missing feedback_text)"
    payload='{"rating": 5}'
    response=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/feedback" \
        -H "Content-Type: application/json" \
        -d "$payload")
    http_code=$(echo "$response" | tail -n1)
    
    if [ "$http_code" = "400" ]; then
        print_success "400 error handling works correctly"
    else
        print_fail "Expected 400, got $http_code"
    fi
    
    # Test invalid export format
    print_test "GET /api/feedbacks/export?format=xml (invalid format)"
    response=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/feedbacks/export?format=xml")
    http_code=$(echo "$response" | tail -n1)
    
    if [ "$http_code" = "400" ]; then
        print_success "Invalid format error handling works correctly"
    else
        print_fail "Expected 400 for invalid format, got $http_code"
    fi
}

# Test 15: Advanced Filtering Combinations
test_advanced_filters() {
    print_header "Test 15: Advanced Filtering Combinations"
    
    # Test complex generation filters
    print_test "GET /api/generations with multiple filters"
    headers=""
    if [ -n "$API_KEY" ]; then
        headers="-H 'X-API-Key: $API_KEY'"
    fi
    
    response=$(curl -s -w "\n%{http_code}" $headers "$BASE_URL/api/generations?min_slides=2&max_slides=20&status=success&sort_by=timestamp&sort_dir=desc")
    http_code=$(echo "$response" | tail -n1)
    
    if [ "$http_code" = "200" ]; then
        print_success "Complex generation filters work correctly"
    else
        print_fail "Complex generation filters failed"
    fi
    
    # Test complex feedback filters
    print_test "GET /api/feedbacks with multiple filters"
    response=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/feedbacks?min_rating=3&category=feature&status=new&sort_by=rating&sort_dir=desc")
    http_code=$(echo "$response" | tail -n1)
    
    if [ "$http_code" = "200" ]; then
        print_success "Complex feedback filters work correctly"
    else
        print_fail "Complex feedback filters failed"
    fi
}

# Print final summary
print_summary() {
    print_header "Test Summary"
    
    echo -e "${CYAN}Total Tests:${NC} $((PASSED + FAILED))"
    echo -e "${GREEN}Passed:${NC} $PASSED"
    echo -e "${RED}Failed:${NC} $FAILED"
    
    if [ $FAILED -eq 0 ]; then
        echo -e "\n${GREEN}🎉 All tests passed successfully!${NC}"
    else
        echo -e "\n${RED}❌ Some tests failed. Please review the output above.${NC}"
        echo -e "\n${YELLOW}Failed Tests:${NC}"
        for result in "${TEST_RESULTS[@]}"; do
            if [[ $result == ✗* ]]; then
                echo -e "${RED}  $result${NC}"
            fi
        done
    fi
    
    # Print test execution time
    echo -e "\n${CYAN}Test artifacts saved in:${NC} $TEMP_DIR"
}

# Main execution
main() {
    echo -e "${CYAN}"
    echo "╔══════════════════════════════════════════════════╗"
    echo "║   PPT Generator API Comprehensive Test Suite    ║"
    echo "╚══════════════════════════════════════════════════╝"
    echo -e "${NC}"
    
    print_info "Base URL: $BASE_URL"
    print_info "API Key: ${API_KEY:-'Not set'}"
    print_info "Temp Dir: $TEMP_DIR"
    echo ""
    
    # Check if required tools are available
    if ! command -v curl &> /dev/null; then
        echo -e "${RED}Error: curl is not installed${NC}"
        exit 1
    fi
    
    if ! command -v jq &> /dev/null; then
        echo -e "${RED}Error: jq is not installed${NC}"
        exit 1
    fi
    
    # Run all tests
    check_server
    test_health
    test_generate_ppt_single
    test_generate_ppt_group
    test_list_generations_basic
    test_list_generations_filters
    test_get_generation_by_id
    test_export_generations
    test_submit_feedback
    test_list_feedbacks_basic
    test_list_feedbacks_filters
    test_get_feedback_by_id
    test_update_feedback
    test_export_feedbacks
    test_edge_cases
    test_advanced_filters
    
    print_summary
    
    # Return appropriate exit code
    if [ $FAILED -eq 0 ]; then
        exit 0
    else
        exit 1
    fi
}

# Run main function
main
