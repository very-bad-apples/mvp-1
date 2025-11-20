# Creative Direction Builder - Task List (Simplified)

**Project:** Internal dev tool for creating pre-made creative direction templates for Veo 3.1 video generation

**Output:** YAML templates saved to `/backend/mv/director/configs/` for insertion into scene prompt templates

**Approach:** Minimal single HTML file + Node.js save script for fastest implementation

---

## Phase 0: Project Setup

### 0.1 Create Project Structure
Create directory and basic files:

```bash
mkdir -p tools/creative-direction-builder
cd tools/creative-direction-builder
npm init -y
```

### 0.2 Install Dependencies
```bash
npm install js-yaml
```

### 0.3 Create Output Directory
```bash
mkdir -p ../../backend/mv/director/configs
```

---

## Phase 1: Data Definition

### 1.1 Create Parameter Constants
**File:** `tools/creative-direction-builder/parameters.js`

```javascript
// Parameter values extracted from AI_VIDEO_PROMPTING_GUIDE.md
export const PARAMETERS = {
  camera: {
    shotTypes: [
      "extreme_close_up",
      "close_up",
      "medium_close_up",
      "medium_shot",
      "wide_shot",
      "extreme_wide_shot",
      "over_the_shoulder",
      "point_of_view"
    ],
    movements: [
      "static",
      "pan",
      "tilt",
      "zoom",
      "dolly",
      "tracking",
      "orbit",
      "crane",
      "handheld"
    ],
    lenses: [
      "wide_angle",
      "standard",
      "portrait",
      "telephoto",
      "fisheye",
      "macro"
    ],
    angles: [
      "eye_level",
      "low_angle",
      "high_angle",
      "overhead",
      "dutch_angle"
    ]
  },
  lighting: {
    types: [
      "natural",
      "dramatic",
      "soft",
      "studio",
      "cinematic",
      "neon"
    ],
    directions: [
      "front",
      "side",
      "back",
      "top"
    ]
  },
  style: {
    visualStyles: [
      "cinematic",
      "documentary",
      "commercial",
      "vintage_film"
    ],
    moods: [
      "dramatic",
      "peaceful",
      "energetic",
      "mysterious",
      "romantic",
      "epic"
    ],
    colorGrading: [
      "teal_and_orange",
      "warm_tones",
      "cool_tones",
      "desaturated",
      "vibrant",
      "monochrome"
    ]
  },
  motion: {
    intensityRange: [0.0, 1.0],
    guidanceRange: [1, 24],
    cfgRange: [1, 15]
  },
  audio: {
    dialogueTones: [
      "whispered",
      "shouted",
      "calm",
      "urgent",
      "sarcastic"
    ],
    musicStyles: [
      "orchestral",
      "electronic",
      "acoustic",
      "jazz"
    ],
    musicMoods: [
      "tense",
      "uplifting",
      "melancholic",
      "energetic"
    ],
    musicIntensities: [
      "subtle",
      "moderate",
      "prominent"
    ]
  },
  quality: {
    negativePrompts: {
      qualityIssues: [
        "blurry",
        "low quality",
        "low resolution",
        "distorted",
        "deformed",
        "grainy",
        "pixelated",
        "compression artifacts"
      ],
      visualArtifacts: [
        "watermarks",
        "text overlays",
        "subtitles",
        "logos",
        "duplicate subjects"
      ],
      contentExclusions: [
        "nude",
        "violence",
        "copyrighted material"
      ]
    },
    safetyLevels: [
      "block_low_and_above",
      "block_medium_and_above",
      "block_high_and_above",
      "block_none"
    ]
  },
  transitions: {
    types: [
      "hard_cut",
      "fade",
      "dissolve",
      "match_cut",
      "veo_cut"
    ]
  }
};
```

---

## Phase 2: Core Application

### 2.1 Create Main HTML File
**File:** `tools/creative-direction-builder/index.html`

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Creative Direction Builder</title>
  <style>
    body { font-family: sans-serif; max-width: 1400px; margin: 0 auto; padding: 20px; }
    .container { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
    .form-section { border: 1px solid #ccc; padding: 15px; margin-bottom: 15px; }
    .form-section h2 { margin-top: 0; font-size: 18px; }
    label { display: block; margin-top: 10px; font-weight: bold; }
    select, input { width: 100%; padding: 5px; margin-top: 5px; }
    select[multiple] { height: 150px; }
    button { padding: 10px 20px; font-size: 16px; cursor: pointer; margin-top: 10px; }
    pre { background: #f5f5f5; padding: 15px; border: 1px solid #ccc; overflow-x: auto; }
    .preview { position: sticky; top: 20px; }
    .format-toggle { margin: 10px 0; }
    .status { padding: 10px; margin-top: 10px; border-radius: 4px; }
    .success { background: #d4edda; color: #155724; }
    .error { background: #f8d7da; color: #721c24; }
  </style>
</head>
<body>
  <h1>Creative Direction Builder</h1>

  <div class="container">
    <!-- Left: Form -->
    <div class="form-panel">
      <div class="form-section">
        <h2>Template Name</h2>
        <label>
          Name:
          <input type="text" id="templateName" placeholder="e.g., cinematic-action">
        </label>
      </div>

      <div class="form-section">
        <h2>Camera Parameters</h2>
        <label>
          Shot Type:
          <select id="camera_shotType">
            <option value="">-- Select --</option>
          </select>
        </label>
        <label>
          Movement:
          <select id="camera_movement">
            <option value="">-- Select --</option>
          </select>
        </label>
        <label>
          Lens:
          <select id="camera_lens">
            <option value="">-- Select --</option>
          </select>
        </label>
        <label>
          Angle:
          <select id="camera_angle">
            <option value="">-- Select --</option>
          </select>
        </label>
      </div>

      <div class="form-section">
        <h2>Lighting Parameters</h2>
        <label>
          Type:
          <select id="lighting_type">
            <option value="">-- Select --</option>
          </select>
        </label>
        <label>
          Direction:
          <select id="lighting_direction">
            <option value="">-- Select --</option>
          </select>
        </label>
      </div>

      <div class="form-section">
        <h2>Style & Mood</h2>
        <label>
          Visual Style:
          <select id="style_visualStyle">
            <option value="">-- Select --</option>
          </select>
        </label>
        <label>
          Mood:
          <select id="style_mood">
            <option value="">-- Select --</option>
          </select>
        </label>
        <label>
          Color Grading:
          <select id="style_colorGrading">
            <option value="">-- Select --</option>
          </select>
        </label>
      </div>

      <div class="form-section">
        <h2>Motion Control</h2>
        <label>
          Motion Intensity (0.0 - 1.0):
          <input type="number" id="motion_intensity" min="0" max="1" step="0.1" placeholder="0.5">
        </label>
        <label>
          Guidance Scale (1 - 24):
          <input type="number" id="motion_guidanceScale" min="1" max="24" placeholder="10">
        </label>
        <label>
          CFG Scale (1 - 15):
          <input type="number" id="motion_cfgScale" min="1" max="15" placeholder="8">
        </label>
      </div>

      <div class="form-section">
        <h2>Audio Parameters</h2>
        <label>
          Dialogue Tone:
          <select id="audio_dialogue_tone">
            <option value="">-- Select --</option>
          </select>
        </label>
        <label>
          Music Style:
          <select id="audio_music_style">
            <option value="">-- Select --</option>
          </select>
        </label>
        <label>
          Music Mood:
          <select id="audio_music_mood">
            <option value="">-- Select --</option>
          </select>
        </label>
        <label>
          Music Intensity:
          <select id="audio_music_intensity">
            <option value="">-- Select --</option>
          </select>
        </label>
      </div>

      <div class="form-section">
        <h2>Quality Control</h2>
        <label>
          Negative Prompts (Ctrl/Cmd + click for multiple):
          <select id="quality_negativePrompts" multiple>
            <optgroup label="Quality Issues"></optgroup>
            <optgroup label="Visual Artifacts"></optgroup>
            <optgroup label="Content Exclusions"></optgroup>
          </select>
        </label>
        <label>
          Safety Level:
          <select id="quality_safetyLevel">
            <option value="">-- Select --</option>
          </select>
        </label>
      </div>

      <div class="form-section">
        <h2>Scene Transitions</h2>
        <label>
          Transition Type:
          <select id="transitions_type">
            <option value="">-- Select --</option>
          </select>
        </label>
      </div>

      <div class="form-section">
        <h2>Save Template</h2>
        <div class="format-toggle">
          <label>
            <input type="radio" name="format" value="yaml" checked> YAML
          </label>
          <label>
            <input type="radio" name="format" value="json"> JSON
          </label>
        </div>
        <button onclick="saveTemplate()">Generate & Save Template</button>
        <div id="status"></div>
      </div>
    </div>

    <!-- Right: Preview -->
    <div class="preview">
      <h2>Preview</h2>
      <div class="format-toggle">
        <label>
          <input type="radio" name="previewFormat" value="yaml" checked onchange="updatePreview()"> YAML
        </label>
        <label>
          <input type="radio" name="previewFormat" value="json" onchange="updatePreview()"> JSON
        </label>
      </div>
      <pre id="preview"></pre>
    </div>
  </div>

  <script type="module" src="app.js"></script>
</body>
</html>
```

### 2.2 Create Application Logic
**File:** `tools/creative-direction-builder/app.js`

```javascript
import { PARAMETERS } from './parameters.js';

// Populate dropdowns on load
window.addEventListener('DOMContentLoaded', () => {
  populateDropdowns();
  attachEventListeners();
  updatePreview();
});

function populateDropdowns() {
  // Camera
  populateSelect('camera_shotType', PARAMETERS.camera.shotTypes);
  populateSelect('camera_movement', PARAMETERS.camera.movements);
  populateSelect('camera_lens', PARAMETERS.camera.lenses);
  populateSelect('camera_angle', PARAMETERS.camera.angles);

  // Lighting
  populateSelect('lighting_type', PARAMETERS.lighting.types);
  populateSelect('lighting_direction', PARAMETERS.lighting.directions);

  // Style
  populateSelect('style_visualStyle', PARAMETERS.style.visualStyles);
  populateSelect('style_mood', PARAMETERS.style.moods);
  populateSelect('style_colorGrading', PARAMETERS.style.colorGrading);

  // Audio
  populateSelect('audio_dialogue_tone', PARAMETERS.audio.dialogueTones);
  populateSelect('audio_music_style', PARAMETERS.audio.musicStyles);
  populateSelect('audio_music_mood', PARAMETERS.audio.musicMoods);
  populateSelect('audio_music_intensity', PARAMETERS.audio.musicIntensities);

  // Quality
  const negativeSelect = document.getElementById('quality_negativePrompts');
  const groups = negativeSelect.querySelectorAll('optgroup');
  groups[0].innerHTML = PARAMETERS.quality.negativePrompts.qualityIssues
    .map(v => `<option value="${v}">${v}</option>`).join('');
  groups[1].innerHTML = PARAMETERS.quality.negativePrompts.visualArtifacts
    .map(v => `<option value="${v}">${v}</option>`).join('');
  groups[2].innerHTML = PARAMETERS.quality.negativePrompts.contentExclusions
    .map(v => `<option value="${v}">${v}</option>`).join('');

  populateSelect('quality_safetyLevel', PARAMETERS.quality.safetyLevels);

  // Transitions
  populateSelect('transitions_type', PARAMETERS.transitions.types);
}

function populateSelect(id, options) {
  const select = document.getElementById(id);
  const currentOptions = select.innerHTML;
  select.innerHTML = currentOptions + options.map(opt =>
    `<option value="${opt}">${opt}</option>`
  ).join('');
}

function attachEventListeners() {
  const inputs = document.querySelectorAll('select, input[type="number"], input[type="text"]');
  inputs.forEach(input => {
    input.addEventListener('change', updatePreview);
    input.addEventListener('input', updatePreview);
  });
}

function getTemplateData() {
  const template = {};

  // Camera
  const camera = {};
  const shotType = getValue('camera_shotType');
  const movement = getValue('camera_movement');
  const lens = getValue('camera_lens');
  const angle = getValue('camera_angle');
  if (shotType) camera.shotType = shotType;
  if (movement) camera.movement = movement;
  if (lens) camera.lens = lens;
  if (angle) camera.angle = angle;
  if (Object.keys(camera).length > 0) template.camera = camera;

  // Lighting
  const lighting = {};
  const lightType = getValue('lighting_type');
  const lightDir = getValue('lighting_direction');
  if (lightType) lighting.type = lightType;
  if (lightDir) lighting.direction = lightDir;
  if (Object.keys(lighting).length > 0) template.lighting = lighting;

  // Style
  const style = {};
  const visualStyle = getValue('style_visualStyle');
  const mood = getValue('style_mood');
  const colorGrading = getValue('style_colorGrading');
  if (visualStyle) style.visualStyle = visualStyle;
  if (mood) style.mood = mood;
  if (colorGrading) style.colorGrading = colorGrading;
  if (Object.keys(style).length > 0) template.style = style;

  // Motion
  const motion = {};
  const intensity = getNumberValue('motion_intensity');
  const guidance = getNumberValue('motion_guidanceScale');
  const cfg = getNumberValue('motion_cfgScale');
  if (intensity !== null) motion.intensity = intensity;
  if (guidance !== null) motion.guidanceScale = guidance;
  if (cfg !== null) motion.cfgScale = cfg;
  if (Object.keys(motion).length > 0) template.motion = motion;

  // Audio
  const audio = {};
  const dialogueTone = getValue('audio_dialogue_tone');
  const musicStyle = getValue('audio_music_style');
  const musicMood = getValue('audio_music_mood');
  const musicIntensity = getValue('audio_music_intensity');

  if (dialogueTone) {
    audio.dialogue = { tone: dialogueTone };
  }
  if (musicStyle || musicMood || musicIntensity) {
    audio.music = {};
    if (musicStyle) audio.music.style = musicStyle;
    if (musicMood) audio.music.mood = musicMood;
    if (musicIntensity) audio.music.intensity = musicIntensity;
  }
  if (Object.keys(audio).length > 0) template.audio = audio;

  // Quality
  const quality = {};
  const negatives = getMultiSelectValues('quality_negativePrompts');
  const safety = getValue('quality_safetyLevel');
  if (negatives.length > 0) quality.negativePrompts = negatives;
  if (safety) quality.safetyLevel = safety;
  if (Object.keys(quality).length > 0) template.quality = quality;

  // Transitions
  const transitions = {};
  const transType = getValue('transitions_type');
  if (transType) transitions.type = transType;
  if (Object.keys(transitions).length > 0) template.transitions = transitions;

  return template;
}

function getValue(id) {
  const el = document.getElementById(id);
  return el.value || null;
}

function getNumberValue(id) {
  const el = document.getElementById(id);
  const val = parseFloat(el.value);
  return isNaN(val) ? null : val;
}

function getMultiSelectValues(id) {
  const el = document.getElementById(id);
  return Array.from(el.selectedOptions).map(opt => opt.value);
}

window.updatePreview = function() {
  const template = getTemplateData();
  const format = document.querySelector('input[name="previewFormat"]:checked').value;
  const preview = document.getElementById('preview');

  if (format === 'yaml') {
    preview.textContent = generateYAML(template);
  } else {
    preview.textContent = JSON.stringify(template, null, 2);
  }
};

function generateYAML(obj, indent = 0) {
  let yaml = '';
  const spaces = '  '.repeat(indent);

  for (const [key, value] of Object.entries(obj)) {
    if (value === null || value === undefined) continue;

    if (Array.isArray(value)) {
      yaml += `${spaces}${key}:\n`;
      value.forEach(item => {
        yaml += `${spaces}  - ${item}\n`;
      });
    } else if (typeof value === 'object') {
      yaml += `${spaces}${key}:\n`;
      yaml += generateYAML(value, indent + 1);
    } else {
      yaml += `${spaces}${key}: ${value}\n`;
    }
  }

  return yaml;
}

window.saveTemplate = async function() {
  const templateName = document.getElementById('templateName').value.trim();
  const format = document.querySelector('input[name="format"]:checked').value;
  const statusDiv = document.getElementById('status');

  // Validate
  if (!templateName) {
    statusDiv.className = 'status error';
    statusDiv.textContent = 'Error: Template name is required';
    return;
  }

  if (!/^[a-zA-Z0-9-_]+$/.test(templateName)) {
    statusDiv.className = 'status error';
    statusDiv.textContent = 'Error: Template name can only contain letters, numbers, hyphens, and underscores';
    return;
  }

  const template = getTemplateData();

  if (Object.keys(template).length === 0) {
    statusDiv.className = 'status error';
    statusDiv.textContent = 'Warning: Template is empty';
  }

  // Save via Node script
  try {
    const response = await fetch('http://localhost:3000/save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ templateName, format, template })
    });

    const result = await response.json();

    if (response.ok) {
      statusDiv.className = 'status success';
      statusDiv.textContent = `Success: Saved ${result.filename}`;
    } else {
      statusDiv.className = 'status error';
      statusDiv.textContent = `Error: ${result.error}`;
    }
  } catch (error) {
    statusDiv.className = 'status error';
    statusDiv.textContent = `Error: ${error.message}. Is the server running?`;
  }
};
```

### 2.3 Create Save Server
**File:** `tools/creative-direction-builder/server.js`

```javascript
const http = require('http');
const fs = require('fs').promises;
const path = require('path');
const yaml = require('js-yaml');

const PORT = 3000;
const OUTPUT_DIR = path.join(__dirname, '../../backend/mv/director/configs');

const server = http.createServer(async (req, res) => {
  // CORS headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    res.writeHead(200);
    res.end();
    return;
  }

  if (req.method === 'POST' && req.url === '/save') {
    let body = '';

    req.on('data', chunk => {
      body += chunk.toString();
    });

    req.on('end', async () => {
      try {
        const { templateName, format, template } = JSON.parse(body);

        // Validate
        if (!templateName || !/^[a-zA-Z0-9-_]+$/.test(templateName)) {
          res.writeHead(400, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ error: 'Invalid template name' }));
          return;
        }

        // Generate content
        const ext = format === 'json' ? 'json' : 'yaml';
        const content = format === 'json'
          ? JSON.stringify(template, null, 2)
          : yaml.dump(template, { indent: 2 });

        // Ensure output directory exists
        await fs.mkdir(OUTPUT_DIR, { recursive: true });

        // Save file
        const filename = `${templateName}.${ext}`;
        const filepath = path.join(OUTPUT_DIR, filename);
        await fs.writeFile(filepath, content, 'utf-8');

        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({
          success: true,
          filename,
          path: filepath
        }));

      } catch (error) {
        console.error('Save error:', error);
        res.writeHead(500, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: error.message }));
      }
    });
  } else {
    res.writeHead(404);
    res.end('Not found');
  }
});

server.listen(PORT, () => {
  console.log(`Save server running on http://localhost:${PORT}`);
  console.log(`Output directory: ${OUTPUT_DIR}`);
});
```

---

## Phase 3: Prompt Template

### 3.1 Create Prompt Template File
**File:** `/backend/mv/director/prompt-template.txt`

```
Scene Creative Direction:

Camera: {{camera.shotType}} shot with {{camera.lens}} lens, {{camera.movement}} camera movement, {{camera.angle}} angle.

Lighting: {{lighting.type}} lighting from {{lighting.direction}}.

Visual Style: {{style.visualStyle}} style with {{style.colorGrading}} color grading, {{style.mood}} mood.

Motion: Motion intensity {{motion.intensity}}, guidance scale {{motion.guidanceScale}}, CFG scale {{motion.cfgScale}}.

Audio: {{audio.dialogue.tone}} dialogue tone. Music: {{audio.music.style}} style, {{audio.music.mood}} mood, {{audio.music.intensity}} intensity.

Negative Prompts: {{quality.negativePrompts}}

Safety: {{quality.safetyLevel}}

Transitions: {{transitions.type}}
```

---

## Phase 4: Documentation & Testing

### 4.1 Create README
**File:** `tools/creative-direction-builder/README.md`

```markdown
# Creative Direction Builder

Minimal internal dev tool for creating creative direction templates for Veo 3.1 video generation.

## Setup

Install dependencies:
```bash
cd tools/creative-direction-builder
npm install
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
```

### 4.2 Testing Checklist

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

---

## Completion Criteria

- [ ] All parameter categories from [AI_VIDEO_PROMPTING_GUIDE.md](../_docs/AI_VIDEO_PROMPTING_GUIDE.md) are represented
- [ ] Real-time preview updates on parameter change
- [ ] Templates save to /backend/mv/director/configs/
- [ ] Template naming validation works
- [ ] Tool runs locally without deployment
