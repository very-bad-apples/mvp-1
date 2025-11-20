# Creative Direction Builder

Minimal internal dev tool for creating creative direction templates for Veo 3.1 video generation.

## Setup

Install dependencies:
```bash
cd tools/creative-direction-builder
pnpm install
```

## Usage

1. Start the save server:
```bash
node server.js
```

2. Open `index.html` in your browser (or use a local server):
```bash
# Option 1: Direct file
open index.html

# Option 2: Local server
npx http-server -p 8080
# Then visit http://localhost:8080
```

3. Fill in parameters, preview YAML/JSON, and save

## Output

Templates saved to: `/backend/mv/director/configs/`

Format: `template-name.yaml` or `template-name.json`

## Files

- `index.html` - Main UI
- `app.js` - Application logic
- `parameters.js` - Parameter definitions from AI_VIDEO_PROMPTING_GUIDE.md
- `server.js` - Save endpoint (runs on port 3000)
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

