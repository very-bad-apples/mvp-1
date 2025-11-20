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

