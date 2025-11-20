# Creative Direction Builder

Minimal internal dev tool for creating creative direction templates for Veo 3.1 video generation.

## Setup

Install dependencies:
```bash
cd tools/creative-direction-builder
pnpm install
```

## Usage

### Quick Start

Start both servers (in separate terminals):

**Terminal 1 - Save Server:**
```bash
pnpm start:server
# Server runs on http://localhost:3002
```

**Terminal 2 - HTTP Server:**
```bash
pnpm start:http
# Server runs on http://localhost:8080
```

Then open `http://localhost:8080` in your browser.

### Manual Start

Alternatively, start servers manually:

1. Start the save server:
```bash
node server.js
# Or: pnpm start:server
```

2. Start the HTTP server (in another terminal):
```bash
npx http-server -p 8080 --cors
# Or: pnpm start:http
```

3. Open `http://localhost:8080` in your browser

4. Fill in parameters, preview YAML/JSON, and save

## Output

Templates saved to: `/backend/mv/director/configs/`

Format: `template-name.yaml` or `template-name.json`

## Files

- `index.html` - Main UI
- `app.js` - Application logic
- `parameters.js` - Parameter definitions from AI_VIDEO_PROMPTING_GUIDE.md
- `server.js` - Save endpoint (runs on port 3002)
- `package.json` - Dependencies

## Testing Checklist

Manual tests:
1. Start server with `node server.js`
2. Open `index.html` in browser
3. Verify all dropdowns populated
4. Select various parameters
5. Verify preview updates in real-time
6. Switch between YAML/JSON preview
7. Save as YAML format
8. Save as JSON format
9. Verify files created in `/backend/mv/director/configs/`
10. Test validation: empty name, invalid characters

