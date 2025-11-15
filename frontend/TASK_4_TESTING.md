# Task 4: Job Status Page - Testing Guide

## Implementation Summary

The Job Status Page has been fully implemented with the following features:

### ✅ Completed Features

1. **Real-time WebSocket Integration**
   - Connects to `ws://localhost:8000/ws/jobs/{job_id}`
   - Receives live progress updates
   - Auto-reconnects on disconnection (3-second delay)
   - Shows connection status badge (Live/Disconnected)

2. **Comprehensive Job Status Display**
   - Job ID and creation timestamp
   - Overall status badge (pending/processing/completed/failed)
   - Overall progress percentage with animated progress bar
   - User's original prompt display

3. **Stage-by-Stage Progress Tracking**
   - Four stages: Script Generation, Voiceover Generation, Video Generation, Compositing
   - Individual progress bars for each stage
   - Status indicators with icons (Clock, Loader, CheckCircle, XCircle)
   - Animated spinner for processing stages
   - Color-coded badges (gray/blue/green/red)

4. **Video Player (Completed Jobs)**
   - HTML5 video player with controls
   - Download button (opens video in new tab)
   - "Create Another Video" button
   - Responsive aspect-ratio container

5. **Error Handling**
   - 404 errors for invalid job IDs
   - Network error handling
   - WebSocket connection errors
   - Failed job error messages display
   - Retry functionality for failed jobs

6. **Loading States**
   - Skeleton loaders while fetching initial data
   - Smooth transitions between states
   - Connection status indicators

7. **Responsive Design**
   - Mobile-optimized layout
   - Stacked cards on mobile
   - Full-width progress bars
   - Matches landing page dark gradient theme

## Testing Instructions

### Prerequisites
```bash
# Terminal 1: Start Backend
cd backend
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
uvicorn main:app --reload

# Terminal 2: Start Frontend
cd frontend
pnpm dev
```

### Test Scenarios

#### 1. Test Loading State
1. Navigate to `http://localhost:3000/job/test-job-id`
2. Observe skeleton loaders while fetching
3. Should show error state if backend is not running

#### 2. Test 404 Error (Invalid Job ID)
1. Start backend and frontend
2. Navigate to `http://localhost:3000/job/invalid-job-12345`
3. Should show:
   - Red error alert with "Job not found" message
   - Retry button
   - "Create New Video" button

#### 3. Test Pending Job
Create a test job via API:
```bash
curl -X POST http://localhost:8000/api/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A beautiful sunset over the ocean",
    "voice_id": "alloy",
    "background_music": "calm"
  }'
```

This returns a job_id. Navigate to `http://localhost:3000/job/{job_id}`

Should show:
- "Generating Your Video" title
- "Live" badge (if WebSocket connected)
- Job ID and prompt
- Overall progress bar at 0%
- Four stage cards, all showing "pending" status
- Gray badges and clock icons

#### 4. Test Processing Job with WebSocket Updates

The backend will automatically start processing. Watch for:
- Progress bar animating from 0% to 100%
- Stages changing from pending → processing → completed
- Spinner animation on processing stages
- Color changes (gray → blue → green)
- "Live" badge indicating real-time updates
- Overall progress calculation

#### 5. Test WebSocket Disconnection
1. While job is processing, stop the backend
2. Should show:
   - "Disconnected" badge (red, with WifiOff icon)
   - Yellow alert: "Connection Issue - Live updates are unavailable"
   - Page continues to show last known status
3. Restart backend
4. Should auto-reconnect within 3 seconds
5. "Live" badge should reappear

#### 6. Test Completed Job
When job reaches 100% and status becomes "completed":
- Title changes to "Video Ready!"
- Green "Completed" badge
- All stages show green checkmarks
- Video player appears with controls
- Download button functional
- "Create Another Video" button visible

#### 7. Test Failed Job
To test failure scenario (requires backend support):
1. Create a job that will fail (e.g., invalid API keys)
2. Navigate to job status page
3. Should show:
   - "Generation Failed" title
   - Red "Failed" badge
   - Error message in red alert
   - "Try Again" button (redirects to /create)
   - "Back to Home" button

#### 8. Test Responsive Design
- Resize browser window
- Check mobile view (< 768px)
- Verify cards stack properly
- Check progress bars are full-width
- Verify text doesn't overflow
- Check video player aspect ratio

#### 9. Test Network Errors
1. Stop backend while on job page
2. Click "Retry" button
3. Should show network error message
4. Restart backend and retry
5. Should successfully fetch data

#### 10. Test Video Download
1. Complete a job successfully
2. Click "Download Video" button
3. Should open video URL in new tab
4. Verify video plays

## Manual WebSocket Testing

Use a WebSocket client (e.g., wscat) to simulate updates:

```bash
# Install wscat
npm install -g wscat

# Connect to job WebSocket
wscat -c ws://localhost:8000/ws/jobs/test-job-id

# Send test progress update
{"type": "progress_update", "job_id": "test-job-id", "progress": 50, "stages": [...]}
```

## Expected API Responses

### GET /api/jobs/{job_id} - Success
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "progress": 45,
  "created_at": "2025-01-14T12:00:00Z",
  "prompt": "A beautiful sunset",
  "voice_id": "alloy",
  "background_music": "calm",
  "stages": [
    {
      "stage": "script_gen",
      "progress": 100,
      "status": "completed"
    },
    {
      "stage": "voice_gen",
      "progress": 80,
      "status": "processing"
    },
    {
      "stage": "video_gen",
      "progress": 0,
      "status": "pending"
    },
    {
      "stage": "compositing",
      "progress": 0,
      "status": "pending"
    }
  ]
}
```

### WebSocket Message Format
```json
{
  "type": "progress_update",
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "progress": 55,
  "status": "processing",
  "stages": [
    {
      "stage": "voice_gen",
      "progress": 100,
      "status": "completed"
    },
    {
      "stage": "video_gen",
      "progress": 20,
      "status": "processing"
    }
  ]
}
```

## Known Behaviors

1. **WebSocket Reconnection**: Automatically attempts to reconnect every 3 seconds if disconnected during processing
2. **Progress Calculation**: Overall progress is average of all stage progress percentages
3. **Stage Names**: Mapped from API keys (script_gen → "Script Generation")
4. **Connection Badge**: Only shows during pending/processing status
5. **Error Recovery**: Retry button refetches data from API
6. **Download**: Opens video URL in new tab (browser handles download UI)

## Performance Considerations

- WebSocket connection is cleaned up on component unmount
- Reconnection timeout is cleared on unmount
- State updates are optimized using functional setState
- Only reconnects if job is still pending/processing

## Browser Compatibility

- Tested on modern browsers (Chrome, Firefox, Safari, Edge)
- WebSocket support required (all modern browsers)
- HTML5 video support required (all modern browsers)
- Responsive design uses CSS Grid and Flexbox

## Accessibility

- Semantic HTML structure
- ARIA labels on interactive elements (via shadcn/ui)
- Color is not the only indicator (icons + text)
- Keyboard navigation support
- Screen reader friendly status updates

## Next Steps

After testing, proceed to:
- Task 5: Backend Setup (if not started)
- Task 9: Job Status Endpoint
- Task 10: WebSocket Implementation
- End-to-end integration testing

## Troubleshooting

**Issue**: "Job not found" error
- **Solution**: Verify backend is running and job_id is valid

**Issue**: WebSocket won't connect
- **Solution**: Check NEXT_PUBLIC_WS_URL in .env.local, verify backend WebSocket endpoint

**Issue**: Video won't play
- **Solution**: Check video_url is accessible, CORS settings, video format support

**Issue**: Page doesn't update in real-time
- **Solution**: Check WebSocket connection status badge, verify backend is sending updates

**Issue**: Build errors
- **Solution**: Run `pnpm install` and `pnpm run build`
