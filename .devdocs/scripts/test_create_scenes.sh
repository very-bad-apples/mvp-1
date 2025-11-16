#!/bin/bash
# Test script for /api/mv/create_scenes endpoint
# Usage: ./test_create_scenes.sh [base_url]
# Example: ./test_create_scenes.sh http://localhost:8000

BASE_URL="${1:-http://localhost:8000}"
ENDPOINT="$BASE_URL/api/mv/create_scenes"

echo "Testing POST $ENDPOINT"
echo "================================"

# Test 1: Minimal request (required fields only)
echo ""
echo "Test 1: Minimal request (required fields only)"
echo "------------------------------------------------"
curl -s -X POST "$ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{
    "idea": "Tourist exploring Austin, Texas",
    "character_description": "Silver metallic humanoid robot carrying a large red and silver shield on its left arm"
  }' | jq .

# Uncomment below for additional tests

# Test 2: Request with custom number of scenes
# echo ""
# echo "Test 2: Custom number of scenes"
# echo "------------------------------------------------"
# curl -s -X POST "$ENDPOINT" \
#   -H "Content-Type: application/json" \
#   -d '{
#     "idea": "A day in the life of a street musician",
#     "character_description": "Young woman with curly red hair wearing a vintage leather jacket",
#     "number_of_scenes": 3
#   }' | jq .

# Test 3: Request with all optional parameters (note: output_dir is fixed to backend/mv/outputs/create_scenes/)
# echo ""
# echo "Test 3: All parameters specified"
# echo "------------------------------------------------"
# curl -s -X POST "$ENDPOINT" \
#   -H "Content-Type: application/json" \
#   -d '{
#     "idea": "Making the perfect cup of coffee",
#     "character_description": "Middle-aged barista with a thick beard and tattoo sleeves",
#     "character_characteristics": "calm, methodical, passionate about details",
#     "number_of_scenes": 5,
#     "video_type": "tutorial",
#     "video_characteristics": "warm lighting, close-ups, cozy atmosphere",
#     "camera_angle": "overhead and side angles"
#   }' | jq .

# Test 4: Validation error (missing required field)
# echo ""
# echo "Test 4: Validation error - missing character_description"
# echo "------------------------------------------------"
# curl -s -X POST "$ENDPOINT" \
#   -H "Content-Type: application/json" \
#   -d '{
#     "idea": "Test idea only"
#   }' | jq .

echo ""
echo "================================"
echo "Test complete!"
