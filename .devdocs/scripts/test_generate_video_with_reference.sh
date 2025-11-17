#!/bin/bash
# Test script for /api/mv/generate_video endpoint with reference image
# Usage: ./test_generate_video_with_reference.sh [base_url]
# Example: ./test_generate_video_with_reference.sh http://localhost:8000
#
# This script tests the reference_image_base64 parameter by:
# 1. Loading character_reference.png from data/ directory
# 2. Loading prompt data from scene.json
# 3. Sending to generate_video endpoint

BASE_URL="${1:-http://localhost:8000}"
ENDPOINT="$BASE_URL/api/mv/generate_video"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="$SCRIPT_DIR/data"

echo "Testing POST $ENDPOINT with reference image"
echo "============================================="
echo "WARNING: Video generation may take 20-400+ seconds!"
echo "This will use Replicate API credits (unless MOCK_VID_GENS=true)."
echo ""

# Check if required files exist
if [ ! -f "$DATA_DIR/character_reference.png" ]; then
    echo "ERROR: character_reference.png not found in $DATA_DIR"
    exit 1
fi

if [ ! -f "$DATA_DIR/scene.json" ]; then
    echo "ERROR: scene.json not found in $DATA_DIR"
    exit 1
fi

# Check for jq
if ! command -v jq &> /dev/null; then
    echo "ERROR: jq is required but not installed"
    exit 1
fi

# Load scene data
PROMPT=$(jq -r '.description' "$DATA_DIR/scene.json")
NEGATIVE_PROMPT=$(jq -r '.negative_description' "$DATA_DIR/scene.json")

echo "Loaded scene data:"
echo "  Prompt: ${PROMPT:0:100}..."
echo "  Negative Prompt: $NEGATIVE_PROMPT"
echo ""

# Encode reference image to base64
echo "Encoding character_reference.png to base64..."
REFERENCE_IMAGE=$(base64 -w 0 "$DATA_DIR/character_reference.png")
IMAGE_SIZE=$(stat -f%z "$DATA_DIR/character_reference.png" 2>/dev/null || stat -c%s "$DATA_DIR/character_reference.png" 2>/dev/null)
BASE64_SIZE=${#REFERENCE_IMAGE}
echo "  Original image size: $IMAGE_SIZE bytes"
echo "  Base64 encoded size: $BASE64_SIZE characters"
echo ""

# Build JSON payload using file to avoid argument list too long error
echo "Building request payload..."
TEMP_PAYLOAD=$(mktemp)
trap "rm -f $TEMP_PAYLOAD" EXIT

# Write JSON directly to file to handle large base64 strings
cat > "$TEMP_PAYLOAD" << EOF
{
  "prompt": $(echo "$PROMPT" | jq -R -s .),
  "negative_prompt": $(echo "$NEGATIVE_PROMPT" | jq -R -s .),
  "reference_image_base64": "$REFERENCE_IMAGE"
}
EOF

echo "Request payload (reference_image truncated):"
jq '{
    prompt: .prompt,
    negative_prompt: .negative_prompt,
    reference_image_base64: (.reference_image_base64 | .[0:50] + "... [truncated]")
}' "$TEMP_PAYLOAD"
echo ""

# Send request
echo "Sending request to $ENDPOINT..."
echo "This may take several minutes..."
echo ""

RESPONSE=$(curl -s -X POST "$ENDPOINT" \
    -H "Content-Type: application/json" \
    --max-time 600 \
    -d @"$TEMP_PAYLOAD")

# Check for errors
if echo "$RESPONSE" | jq -e '.detail' > /dev/null 2>&1; then
    echo "ERROR Response:"
    echo "$RESPONSE" | jq .
    exit 1
fi

# Display response
echo "Response:"
echo "$RESPONSE" | jq '{
    video_id: .video_id,
    video_url: .video_url,
    metadata: {
        prompt: .metadata.prompt,
        backend_used: .metadata.backend_used,
        model_used: .metadata.model_used,
        is_mock: .metadata.is_mock,
        has_reference_image: .metadata.has_reference_image,
        processing_time_seconds: .metadata.processing_time_seconds,
        parameters_used: .metadata.parameters_used
    }
}'

# Extract video_id for follow-up commands
VIDEO_ID=$(echo "$RESPONSE" | jq -r '.video_id')

echo ""
echo "============================================="
echo "Test complete!"
echo ""
echo "Video ID: $VIDEO_ID"
echo ""
echo "Next steps:"
echo "  View video info:"
echo "    curl $BASE_URL/api/mv/get_video/$VIDEO_ID/info | jq ."
echo ""
echo "  Download video:"
echo "    curl $BASE_URL/api/mv/get_video/$VIDEO_ID -o output.mp4"
echo ""
echo "  Open in browser:"
echo "    $BASE_URL/api/mv/get_video/$VIDEO_ID"
