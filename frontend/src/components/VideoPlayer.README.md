# VideoPlayer Component

A fully-featured, reusable video player component built with React, TypeScript, and shadcn/ui components.

## Overview

The VideoPlayer component provides a modern, accessible video playback experience with advanced controls, mobile optimizations, and share functionality. It's built on top of the native HTML5 `<video>` element with no external player dependencies.

## Features

### Core Playback Controls
- **Play/Pause**: Toggle video playback with visual feedback
- **Timeline Scrubbing**: Click or drag to seek to any position
- **Time Display**: Shows current time and total duration (MM:SS format)
- **Volume Control**: Adjustable volume slider with mute toggle
- **Playback Speed**: Options for 0.5x, 0.75x, 1x, 1.25x, 1.5x, and 2x speeds
- **Fullscreen Mode**: Toggle fullscreen viewing
- **Buffer Indicator**: Visual feedback for video buffering status

### Mobile Optimizations
- **Touch-Friendly Controls**: Larger hit areas for mobile devices
- **Double-Tap Seek**: Double-tap left side to rewind 10s, right side to forward 10s
- **Auto-Hide Controls**: Controls automatically hide after 3 seconds of inactivity
- **Native Playback**: Uses `playsInline` for iOS compatibility
- **Responsive Design**: Adapts to all screen sizes

### Share Functionality
- **Copy Link**: Copy video URL to clipboard
- **Social Sharing**: Share on Twitter/X and Facebook
- **Download Video**: Direct download link
- **Native Share API**: Uses Web Share API when available (mobile devices)

### Keyboard Shortcuts
| Key | Action |
|-----|--------|
| `Space` or `K` | Play/Pause |
| `←` or `J` | Rewind 5 seconds |
| `→` or `L` | Fast forward 5 seconds |
| `↑` | Increase volume |
| `↓` | Decrease volume |
| `F` | Toggle fullscreen |
| `M` | Toggle mute |

### Loading & Error States
- **Loading Spinner**: Shown while video is loading
- **Buffer Indicator**: Shows buffering progress
- **Error Handling**: Displays error message with retry option
- **Graceful Degradation**: Handles video load failures

## Usage

### Basic Example

```tsx
import VideoPlayer from '@/components/VideoPlayer'

export default function MyPage() {
  return (
    <VideoPlayer
      src="https://example.com/video.mp4"
    />
  )
}
```

### Advanced Example

```tsx
import VideoPlayer from '@/components/VideoPlayer'

export default function MyPage() {
  const handleVideoEnd = () => {
    console.log('Video ended, showing recommendations...')
  }

  const handleVideoError = (error: Error) => {
    console.error('Video failed to load:', error)
    // Send error to analytics
  }

  return (
    <VideoPlayer
      src="https://example.com/video.mp4"
      poster="https://example.com/thumbnail.jpg"
      autoPlay={false}
      muted={false}
      loop={false}
      className="max-w-4xl mx-auto"
      onEnded={handleVideoEnd}
      onError={handleVideoError}
    />
  )
}
```

## Props

### VideoPlayerProps

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `src` | `string` | **Required** | URL of the video file |
| `poster` | `string` | `undefined` | URL of the thumbnail/poster image |
| `autoPlay` | `boolean` | `false` | Auto-play video on load |
| `muted` | `boolean` | `false` | Start video muted |
| `loop` | `boolean` | `false` | Loop video playback |
| `className` | `string` | `""` | Additional CSS classes for the container |
| `onEnded` | `() => void` | `undefined` | Callback when video playback ends |
| `onError` | `(error: Error) => void` | `undefined` | Callback when video fails to load |

## Component Architecture

### State Management
The component uses React hooks for state management:
- `useState` for UI state (playing, muted, volume, etc.)
- `useRef` for DOM references (video element, container)
- `useCallback` for memoized event handlers
- `useEffect` for side effects (event listeners, keyboard shortcuts)

### Key Components Used
- `Button` (shadcn/ui) - Control buttons
- `Slider` (shadcn/ui) - Volume and progress controls
- `Dialog` (shadcn/ui) - Share modal
- `DropdownMenu` (shadcn/ui) - Playback speed selector
- `useToast` (shadcn/ui) - Toast notifications

## Accessibility

- **Keyboard Navigation**: Full keyboard control support
- **ARIA Labels**: Proper labeling for screen readers (future enhancement)
- **Focus Management**: Clear focus indicators on interactive elements
- **Touch Targets**: Minimum 44x44px touch targets for mobile

## Browser Compatibility

### Supported Browsers
- ✅ Chrome 90+
- ✅ Firefox 88+
- ✅ Safari 14+
- ✅ Edge 90+
- ✅ Mobile Safari (iOS 14+)
- ✅ Chrome Mobile (Android 8+)

### Feature Support
- **Fullscreen API**: Supported in all modern browsers
- **Web Share API**: Available on mobile devices and some desktop browsers
- **HTML5 Video**: Universal support
- **Custom Controls**: Works in all browsers

## Styling

The component uses Tailwind CSS for styling and follows the dark theme pattern from the application:
- Dark gradient overlays
- Semi-transparent controls
- Smooth transitions and animations
- Responsive design with mobile-first approach

### Customization

You can customize the appearance by:
1. Passing a `className` prop for container styling
2. Modifying the component's internal Tailwind classes
3. Overriding styles in your global CSS

```tsx
<VideoPlayer
  src="/video.mp4"
  className="shadow-2xl border-2 border-blue-500"
/>
```

## Performance Considerations

1. **Auto-Hide Controls**: Reduces UI clutter and CPU usage
2. **Event Debouncing**: Mouse movement events are optimized
3. **Lazy Loading**: Video loads only when needed
4. **Buffer Monitoring**: Efficient progress tracking
5. **Memory Management**: Proper cleanup of event listeners

## Known Limitations

1. **No Picture-in-Picture**: Not currently implemented (future enhancement)
2. **No Quality Selector**: Single quality source only
3. **No Captions**: Closed captions not yet supported
4. **No Thumbnails on Hover**: Timeline preview not implemented

## Future Enhancements

- [ ] Picture-in-Picture support
- [ ] Quality/resolution selector
- [ ] Closed captions/subtitles
- [ ] Thumbnail preview on timeline hover
- [ ] Gesture controls (swipe volume/brightness)
- [ ] Advanced analytics tracking
- [ ] Playlist support
- [ ] Chromecast integration

## Troubleshooting

### Video Won't Play
1. Check that the `src` URL is accessible
2. Verify CORS headers if loading from external domain
3. Ensure video format is supported (MP4, WebM recommended)
4. Check browser console for errors

### Controls Not Showing
1. Move mouse over video area
2. Check that `showControls` state is being updated
3. Verify z-index stacking context

### Fullscreen Not Working
1. Ensure browser supports Fullscreen API
2. Check that user gesture initiated the action
3. Verify no parent element is blocking fullscreen

### Share Button Not Working
1. Check browser's clipboard permissions
2. Verify HTTPS for Web Share API
3. Test with different share methods

## Dependencies

- `react` ^18.3.1
- `lucide-react` ^0.553.0 (icons)
- `@radix-ui/react-slider` (via shadcn/ui)
- `@radix-ui/react-dialog` (via shadcn/ui)
- `@radix-ui/react-dropdown-menu` (via shadcn/ui)

## License

Part of the Bad Apple Video Generator project.
