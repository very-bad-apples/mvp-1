#!/bin/bash
# Test script for /api/mv/generate_video endpoint
# Usage: ./test_generate_video.sh [base_url]
# Example: ./test_generate_video.sh http://localhost:8000
#
# WARNING: This endpoint may take 20-400+ seconds to complete
# Video generation is computationally expensive and uses API credits

BASE_URL="${1:-http://localhost:8000}"
ENDPOINT="$BASE_URL/api/mv/generate_video"

echo "Testing POST $ENDPOINT"
echo "================================"
echo "WARNING: Video generation may take 20-400+ seconds!"
echo "This will use Replicate API credits."
echo ""

# Test 1: Minimal request (just prompt)
echo "Test 1: Minimal request (prompt only)"
echo "------------------------------------------------"
echo "Request:"
echo '{
  "prompt": "A silver metallic robot walks through a futuristic city street at sunset, looking around curiously"
}'
echo ""
echo "Response (truncated for readability):"

curl -s -X POST "$ENDPOINT" \
  -H "Content-Type: application/json" \
  --max-time 600 \
  -d '{
    "prompt": "A silver metallic robot walks through a futuristic city street at sunset, looking around curiously"
  }' | jq '{
    video_id: .video_id,
    video_url: .video_url,
    metadata: .metadata
  }'

echo ""
echo ""

# Uncomment below for additional tests
# Note: Each test will take 20-400+ seconds and consume API credits

# Test 2: Request with custom parameters
# echo "Test 2: Custom parameters"
# echo "------------------------------------------------"
# curl -s -X POST "$ENDPOINT" \
#   -H "Content-Type: application/json" \
#   --max-time 600 \
#   -d '{
#     "prompt": "A young woman with curly red hair dances in a colorful studio",
#     "duration": 10,
#     "generate_audio": true,
#     "aspect_ratio": "9:16"
#   }' | jq '{
#     video_id: .video_id,
#     video_url: .video_url,
#     metadata: .metadata
#   }'

# Test 3: Test video retrieval (replace VIDEO_ID with actual ID)
# echo "Test 3: Get video info"
# echo "------------------------------------------------"
# VIDEO_ID="your-video-id-here"
# curl -s "$BASE_URL/api/mv/get_video/$VIDEO_ID/info" | jq .

# Test 4: Download video (replace VIDEO_ID with actual ID)
# echo "Test 4: Download video"
# echo "------------------------------------------------"
# VIDEO_ID="your-video-id-here"
# curl -s "$BASE_URL/api/mv/get_video/$VIDEO_ID" -o "downloaded_video.mp4"
# echo "Video saved to downloaded_video.mp4"

# Test 5: Validation error (missing prompt)
# echo "Test 5: Validation error - missing prompt"
# echo "------------------------------------------------"
# curl -s -X POST "$ENDPOINT" \
#   -H "Content-Type: application/json" \
#   -d '{}' | jq .

# Test 6: Invalid backend
# echo "Test 6: Invalid backend"
# echo "------------------------------------------------"
# curl -s -X POST "$ENDPOINT" \
#   -H "Content-Type: application/json" \
#   -d '{
#     "prompt": "Test prompt",
#     "backend": "invalid"
#   }' | jq .

# Test 7: Test with reference image (base64 encoded)
# This requires an actual base64 encoded image
# echo "Test 7: With reference image"
# echo "------------------------------------------------"
# REFERENCE_IMAGE=$(base64 -w 0 path/to/character_reference.png)
# curl -s -X POST "$ENDPOINT" \
#   -H "Content-Type: application/json" \
#   --max-time 600 \
#   -d "{
#     \"prompt\": \"The robot from the reference walks through a park\",
#     \"reference_image_base64\": \"$REFERENCE_IMAGE\"
#   }" | jq '{
#     video_id: .video_id,
#     video_url: .video_url,
#     metadata: .metadata
#   }'

echo "================================"
echo "Test complete!"
echo ""
echo "To download a generated video:"
echo "  curl $BASE_URL/api/mv/get_video/{video_id} -o video.mp4"
echo ""
echo "To check video info:"
echo "  curl $BASE_URL/api/mv/get_video/{video_id}/info | jq ."
