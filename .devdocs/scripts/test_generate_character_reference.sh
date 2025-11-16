#!/bin/bash
# Test script for /api/mv/generate_character_reference endpoint
# Usage: ./test_generate_character_reference.sh [base_url]
# Example: ./test_generate_character_reference.sh http://localhost:8000
#
# Note: This endpoint generates images via Replicate API, which may take 10-60+ seconds
# The response includes a large base64-encoded image, so output is truncated by default

BASE_URL="${1:-http://localhost:8000}"
ENDPOINT="$BASE_URL/api/mv/generate_character_reference"

echo "Testing POST $ENDPOINT"
echo "================================"
echo "Note: Image generation may take 10-60+ seconds"

# Test 1: Minimal request (required fields only)
echo ""
echo "Test 1: Minimal request (required fields only)"
echo "------------------------------------------------"
curl -s -X POST "$ENDPOINT" \
  -H "Content-Type: application/json" \
  -d '{
    "character_description": "Silver metallic humanoid robot carrying a large red and silver shield on its left arm"
  }' | jq '{
    output_file: .output_file,
    metadata: .metadata,
    image_base64_preview: (.image_base64 | .[0:50] + "... (truncated)")
  }'

# Uncomment below for additional tests

# Test 2: Request with custom aspect ratio
# echo ""
# echo "Test 2: Custom aspect ratio"
# echo "------------------------------------------------"
# curl -s -X POST "$ENDPOINT" \
#   -H "Content-Type: application/json" \
#   -d '{
#     "character_description": "Young woman with curly red hair wearing a vintage leather jacket",
#     "aspect_ratio": "16:9"
#   }' | jq '{
#     output_file: .output_file,
#     metadata: .metadata,
#     image_base64_preview: (.image_base64 | .[0:50] + "... (truncated)")
#   }'

# Test 3: Request with all optional parameters
# echo ""
# echo "Test 3: All parameters specified"
# echo "------------------------------------------------"
# curl -s -X POST "$ENDPOINT" \
#   -H "Content-Type: application/json" \
#   -d '{
#     "character_description": "Middle-aged barista with a thick beard and tattoo sleeves wearing a dark apron",
#     "aspect_ratio": "1:1",
#     "safety_filter_level": "block_medium_and_above",
#     "person_generation": "allow_adult",
#     "output_format": "png",
#     "negative_prompt": "blurry, low quality, distorted features",
#     "seed": 12345
#   }' | jq '{
#     output_file: .output_file,
#     metadata: .metadata,
#     image_base64_preview: (.image_base64 | .[0:50] + "... (truncated)")
#   }'

# Test 4: Validation error (missing required field)
# echo ""
# echo "Test 4: Validation error - missing character_description"
# echo "------------------------------------------------"
# curl -s -X POST "$ENDPOINT" \
#   -H "Content-Type: application/json" \
#   -d '{}' | jq .

# Test 5: Save the generated image to a file
# echo ""
# echo "Test 5: Generate and save image to file"
# echo "------------------------------------------------"
# RESPONSE=$(curl -s -X POST "$ENDPOINT" \
#   -H "Content-Type: application/json" \
#   -d '{
#     "character_description": "Cute cartoon cat with orange fur"
#   }')
# echo "$RESPONSE" | jq -r '.image_base64' | base64 -d > test_character.png
# echo "Image saved to test_character.png"
# echo "Metadata:"
# echo "$RESPONSE" | jq '.metadata'

echo ""
echo "================================"
echo "Test complete!"
