# AI Video Generation Prompting Guide
**JSON & YAML Structured Prompting for Production Video Generation**

*Last Updated: January 2025*

---

## Table of Contents

1. [Why Structured Prompting](#why-structured-prompting)
2. [JSON Schema Structure](#json-schema-structure)
3. [High-Value Parameters](#high-value-parameters)
4. [Platform-Specific Examples](#platform-specific-examples)
5. [Multi-Scene Video Structure](#multi-scene-video-structure)
6. [Parameter Reference](#parameter-reference)
7. [Best Practices](#best-practices)

---

## Why Structured Prompting

**Performance Impact:**
- **300%+ quality improvement** over unstructured text prompts
- **87-90% character consistency** with structured descriptions
- **85% reduction** in unwanted visual elements
- **60%+ cost savings** through efficient iteration

**Key Benefits:**
- Precision parameter control
- Reproducible results via seed management
- Modular, reusable component library
- Reduced ambiguity and AI misinterpretation

---

## JSON Schema Structure

### Complete Google Veo 3 Schema

```json
{
  "version": "veo-3.1",
  "output": {
    "duration_sec": 8,
    "fps": 24,
    "resolution": "1080p",
    "aspect_ratio": "16:9"
  },
  "global_style": {
    "look": "cinematic",
    "color": "warm tones",
    "mood": "dramatic",
    "safety": "block_medium_and_above"
  },
  "continuity": {
    "characters": [
      {
        "id": "char_001",
        "description": "Woman in late 20s with curly brown hair, wearing white t-shirt with bold black text 'CHAD'",
        "visual_traits": "scar over left eye, silver watch on right wrist",
        "consistency_level": "strict"
      }
    ],
    "props": ["red vintage car", "leather jacket"],
    "lighting": {
      "type": "natural",
      "description": "Soft morning light through window"
    }
  },
  "scenes": [
    {
      "id": "scene_001",
      "start": 0.0,
      "end": 4.0,
      "shot": {
        "type": "close-up",
        "framing": "rule of thirds",
        "camera": {
          "movement": "slow zoom in",
          "angle": "eye level",
          "lens": "85mm"
        }
      },
      "action": "Character examining mysterious map with intense focus",
      "environment": {
        "setting": "dimly lit vintage study with floor-to-ceiling bookshelves",
        "atmosphere": "mysterious, tense",
        "time_of_day": "late night"
      },
      "lighting": {
        "type": "dramatic",
        "description": "Single desk lamp creating sharp shadows, golden warm tones",
        "intensity": "medium-low"
      },
      "audio": {
        "dialogue": {
          "text": "This changes everything",
          "tone": "whispered, urgent"
        },
        "ambient": "soft ticking clock, distant thunder",
        "music": "subtle tension-building strings"
      },
      "visual_rules": {
        "exclude": ["text overlays", "subtitles", "compression artifacts"],
        "enhance": ["depth of field", "film grain", "cinematic color grading"]
      }
    }
  ]
}
```

### YAML Configuration Template

```yaml
# Video generation configuration
video_config:
  # Technical parameters
  output:
    duration_sec: 8
    fps: 24
    resolution: "1080p"
    aspect_ratio: "16:9"

  # Global styling
  style:
    visual_look: "cinematic"
    color_grading: "teal and orange"
    mood: "dramatic"
    film_grain: true

  # Character continuity
  characters:
    - id: "main_char"
      description: "Athletic woman in 30s, black athletic wear with neon green accents, long dark ponytail"
      consistency: "strict"

  # Scene definitions
  scenes:
    - id: 1
      duration: 3
      shot:
        type: "extreme close-up"
        lens: "85mm macro"
        movement: "slow push in"
        angle: "eye level"
      content:
        subject: "Product bottle reflecting morning light"
        action: "Water droplets sliding down condensed surface"
      lighting:
        type: "studio"
        setup: "three-point with blue rim light"
      negative_prompt: "no text, no labels, no hands"
```

---

## High-Value Parameters

### Technical Parameters

| Parameter | Type | Values | Purpose |
|-----------|------|--------|---------|
| `duration_sec` | integer | 5, 8, 10 | Video length (5=quick, 8=standard, 10=narrative) |
| `fps` | integer | 24, 30, 60 | Frame rate (24=cinematic, 30=web, 60=action) |
| `resolution` | string | "720p", "1080p", "4K" | Quality (720p=draft, 1080p=production, 4K=premium) |
| `aspect_ratio` | string | "16:9", "9:16", "1:1" | Platform format (16:9=YouTube, 9:16=TikTok, 1:1=Instagram) |
| `seed` | integer | 0-2147483646 | Reproducibility control |

### Camera Parameters

**Shot Types:**
```yaml
shot_types:
  extreme_close_up: "Very tight on detail (eyes, hands, object)"
  close_up: "Face or primary focus"
  medium_close_up: "Head and shoulders"
  medium_shot: "Waist up"
  wide_shot: "Full subject + environment"
  extreme_wide_shot: "Vast landscape"
  over_the_shoulder: "View from behind subject"
  point_of_view: "Character's perspective"
```

**Camera Movements:**
```yaml
movements:
  static: "No movement"
  pan: "Horizontal rotation (left/right)"
  tilt: "Vertical rotation (up/down)"
  zoom: "Lens focal length change (in/out)"
  dolly: "Physical movement toward/away"
  tracking: "Follow subject smoothly"
  orbit: "Circle around subject"
  crane: "High sweeping movement"
  handheld: "Shaky documentary style"
```

**Lens Types:**
```yaml
lenses:
  wide_angle: "24mm-35mm (landscapes, interiors)"
  standard: "50mm (natural perspective)"
  portrait: "85mm (character shots, flattering)"
  telephoto: "135mm+ (compression effects)"
  fisheye: "8mm-16mm (creative distortion)"
  macro: "Extreme close-ups"
```

### Lighting Parameters

```yaml
lighting_types:
  natural:
    golden_hour: "Warm soft light at sunrise/sunset"
    blue_hour: "Cool ethereal light before sunrise/after sunset"
    overcast: "Soft diffused cloudy light"
    midday: "Harsh overhead sunlight"

  dramatic:
    description: "High contrast, directional"
    mood: "Tension, mystery, intensity"

  soft:
    description: "Diffused, even illumination"
    mood: "Peaceful, romantic, dreamy"

  studio:
    three_point: "Key, fill, rim lights"
    rembrandt: "Diagonal key creating cheek triangle"
    butterfly: "High frontal key with nose shadow"

  cinematic:
    description: "Film-style with depth and mood"

  neon:
    description: "Colored artificial lights"
    mood: "Urban, cyberpunk, energetic"

lighting_direction:
  front: "Direct facial lighting"
  side: "90° angle, creates depth"
  back: "Silhouette or rim light"
  top: "Overhead, dramatic shadows"
```

### Style & Mood Parameters

```yaml
visual_styles:
  cinematic:
    characteristics: "Film grain, color grading, depth of field"
    color_palette: "Teal and orange, desaturated"

  documentary:
    characteristics: "Natural lighting, handheld camera"
    color_palette: "Realistic, ungraded"

  commercial:
    characteristics: "High production, perfect lighting"
    color_palette: "Vibrant, saturated"

  vintage_film:
    characteristics: "Film grain, vignetting, scratches"
    color_palette: "Faded, warm/cool tint"

moods:
  dramatic: "High contrast, tension, emotional intensity"
  peaceful: "Soft lighting, calm colors, gentle movement"
  energetic: "Fast pacing, vibrant colors, dynamic camera"
  mysterious: "Shadows, fog, limited visibility"
  romantic: "Soft focus, warm tones, intimate framing"
  epic: "Wide shots, dramatic sky, grand scale"

color_grading:
  teal_and_orange: "Cinematic standard (complementary colors)"
  warm_tones: "Yellow/orange/red for comfort"
  cool_tones: "Blue/teal/purple for calm or tension"
  desaturated: "Muted colors for serious tone"
  vibrant: "High saturation for energy"
  monochrome: "Black and white"
```

### Motion Control Parameters

```yaml
motion_control:
  # Motion intensity (platform-dependent)
  motion_intensity: 0.5  # 0.0-1.0 (0.3=subtle, 0.5=balanced, 0.7=dynamic)

  # Guidance scale (prompt adherence)
  guidance_scale: 10  # 1-24 (8-12 recommended)
  # Low (1-5): High creative freedom
  # Medium (6-12): Balanced
  # High (13-24): Strict prompt following

  # CFG scale (classifier-free guidance)
  cfg_scale: 8  # 1-15 (6-10 recommended)
```

### Audio Parameters

```yaml
audio_structure:
  dialogue:
    text: "Spoken words"
    tone: "whispered | shouted | calm | urgent | sarcastic"
    format: "saying calmly: 'Your text here'"

  ambient:
    description: "Background environmental sounds"
    examples:
      - "gentle ocean waves"
      - "city traffic ambience"
      - "rustling leaves"
      - "rain on window"

  music:
    style: "orchestral | electronic | acoustic | jazz"
    mood: "tense | uplifting | melancholic | energetic"
    intensity: "subtle | moderate | prominent"

  sound_effects:
    type: "footsteps | door creak | glass breaking"
    timing: "synchronized to visual"
```

### Quality Control Parameters

```yaml
# ALWAYS include negative prompts
negative_prompts:
  quality_issues:
    - "blurry"
    - "low quality"
    - "low resolution"
    - "distorted"
    - "deformed"
    - "grainy"
    - "pixelated"
    - "compression artifacts"

  visual_artifacts:
    - "watermarks"
    - "text overlays"
    - "subtitles (unless intentional)"
    - "logos"
    - "duplicate subjects"

  content_exclusions:
    - "nude"
    - "violence"
    - "copyrighted material"

# Safety filters
safety:
  block_low_and_above: "Most restrictive"
  block_medium_and_above: "Standard (recommended)"
  block_high_and_above: "Minimal filtering"
  block_none: "No filtering (use with caution)"
```

---

## Platform-Specific Examples

### Google Veo 3.1 (Recommended - Industry Leading)

**Simple Text-to-Video:**
```json
{
  "model": "veo-3.1",
  "prompt": "A golden retriever puppy running through sunflowers at golden hour. Camera tracks alongside with smooth steadicam movement. Warm cinematic lighting, shallow depth of field.",
  "duration": 8,
  "resolution": "1080p",
  "aspect_ratio": "16:9",
  "generate_audio": true,
  "negative_prompt": "blurry, distorted, low quality, text overlays"
}
```

**Image-to-Video with Parameters:**
```json
{
  "model": "veo-3.1",
  "first_frame": "gs://bucket/start.jpg",
  "last_frame": "gs://bucket/end.jpg",
  "prompt": "Smooth transition showing character walking from city street to park. Natural lighting changes from urban shadows to dappled sunlight through trees.",
  "duration": 8,
  "resolution": "1080p",
  "seed": 42
}
```

**Multi-Scene with [cut] Feature:**
```json
{
  "model": "veo-3.1",
  "prompt": "Close-up of coffee being poured into white cup, steam rising, morning window light. [cut] Medium shot of same person sipping coffee at window, city skyline visible, contemplative expression. [cut] Wide shot of entire café interior, warm cozy atmosphere, golden hour lighting streaming through large windows.",
  "duration": 8,
  "resolution": "1080p"
}
```

### Runway Gen-3/Gen-4

**Gen-4 (Simplified - Recommended):**
```json
{
  "model": "runway-gen4",
  "prompt": "A jellyfish floating in deep ocean water, bioluminescent blue glow, camera orbits slowly",
  "aspect_ratio": "16:9",
  "duration": 10
}
```

**Gen-3 Turbo (Full Control):**
```json
{
  "model": "runway-gen3/turbo/text-to-video",
  "prompt": "Close-up shot of hands playing piano. Dramatic side lighting creates shadows across keys. Camera slowly dollies in. 85mm lens, shallow depth of field, cinematic color grading.",
  "negative_prompt": "blurry, low quality, distorted, text overlays",
  "ratio": "16:9",
  "duration": 10,
  "seed": 42,
  "structure_transformation": 9,
  "turbo": true
}
```

### Luma Dream Machine

**Text-to-Video:**
```json
{
  "model": "ray-2",
  "prompt": "A tiger walking through deep snow in winter forest. Camera follows alongside with smooth tracking. Morning light filters through snow-covered pines. 4K cinematic quality.",
  "resolution": "1080p",
  "duration": "5s",
  "aspect_ratio": "16:9",
  "seed": 12345
}
```

**First-Last Frame Control:**
```json
{
  "model": "ray-2",
  "keyframes": {
    "frame0": {
      "type": "image",
      "url": "https://storage.cdn/start.jpg",
      "mimeType": "image/jpeg"
    },
    "frame1": {
      "type": "image",
      "url": "https://storage.cdn/end.jpg",
      "mimeType": "image/jpeg"
    }
  },
  "prompt": "Smooth camera movement from point A to point B, maintaining consistent lighting and atmosphere",
  "duration": "5s"
}
```

### Kling AI v2.5

**API Format:**
```json
{
  "prompt": "Enchanted forest with glowing mushrooms, fireflies dancing, sparkling river. Camera pans slowly left to right.",
  "negative_prompt": "blurry, low quality, distorted",
  "duration": 10,
  "model": "KLING2_5",
  "height": 1080,
  "width": 1920,
  "fps": 30,
  "creativity_slider": 0.7,
  "relevance_slider": 0.8
}
```

**Structured Text Format:**
```
[Subject], [description], [movement], [scene], [scene description], [camera], [lighting], [atmosphere]

Example:
Young woman with flowing red hair, wearing vintage leather jacket, walking confidently down neon-lit Tokyo street, camera tracking alongside, dramatic side lighting from shop signs, cyberpunk atmosphere
```

### Pika Labs v2.0

**API Format:**
```json
{
  "promptText": "Sleek sports car driving through mountain pass at sunset, camera follows from helicopter perspective",
  "aspectRatio": "16:9",
  "frameRate": 24,
  "camera": {
    "pan": 0.5,
    "tilt": 0.0,
    "zoom": 0.3
  },
  "motion": 3,
  "guidanceScale": 12,
  "negativePrompt": "blurry, distorted, low quality",
  "seed": 9876
}
```

**Camera Control Values:**
- `pan`: -1.0 to 1.0 (horizontal movement)
- `tilt`: -1.0 to 1.0 (vertical movement)
- `zoom`: -1.0 to 1.0 (in/out)
- `rotate`: -1.0 to 1.0 (camera rotation)

---

## Multi-Scene Video Structure

### Complete Storyboard JSON

```json
{
  "project": {
    "title": "Product Launch Video",
    "total_duration": 30,
    "style": "cinematic commercial",
    "target_platform": "Instagram Reels"
  },
  "global_settings": {
    "resolution": "1080p",
    "fps": 30,
    "aspect_ratio": "9:16",
    "color_grading": "vibrant, warm tones"
  },
  "character_continuity": [
    {
      "id": "protagonist",
      "description": "Athletic woman in 30s, black athletic wear with neon green accents, long dark ponytail",
      "consistency_rules": "Must appear identical in every scene"
    }
  ],
  "scenes": [
    {
      "id": "scene_01",
      "duration": 3,
      "transition_out": "hard cut",
      "shot": {
        "type": "extreme close-up",
        "lens": "85mm macro",
        "camera_movement": "slow push in"
      },
      "content": {
        "subject": "Product bottle with water droplets",
        "action": "Condensation sliding down surface",
        "environment": "Clean white studio background"
      },
      "lighting": {
        "type": "studio",
        "setup": "three-point with blue rim light"
      },
      "negative_prompt": "no text, no hands"
    },
    {
      "id": "scene_02",
      "duration": 4,
      "transition_in": "hard cut",
      "transition_out": "match cut",
      "shot": {
        "type": "medium shot",
        "lens": "35mm",
        "camera_movement": "tracking shot"
      },
      "content": {
        "subject": "Athletic woman running on beach",
        "action": "Powerful stride, holding product",
        "environment": "Golden sand, waves, sunrise"
      },
      "lighting": {
        "type": "golden_hour",
        "description": "Warm backlight creating rim light"
      },
      "character_reference": "protagonist"
    }
  ]
}
```

### Scene Transition Types

```yaml
transitions:
  hard_cut:
    timing: "0 frames"
    use_case: "Fast pacing, dramatic shift"

  fade:
    timing: "0.5-2.0 seconds"
    variations:
      - fade_to_black
      - fade_to_white
      - cross_fade
    use_case: "Time passage, softer mood"

  dissolve:
    timing: "0.5-1.5 seconds"
    use_case: "Smooth storytelling, related scenes"

  match_cut:
    types:
      - shape_match
      - motion_match
      - color_match
    use_case: "Creative transitions, thematic connections"

  veo_cut:
    syntax: "[cut]"
    example: "Scene 1 content [cut] Scene 2 content"
    use_case: "Multi-scene single prompt (Veo 3 only)"
```

### Character Consistency Strategy

**Critical Success Factors:**

1. **Forensic Precision**: Copy-paste IDENTICAL descriptions across all scenes
2. **Simple Visual Markers**: Use easily reproducible traits
3. **Text on Clothing**: Simple bold text (e.g., "CHAD" on white t-shirt)
4. **Solid Colors**: Avoid complex patterns or logos
5. **Distinctive Features**: Scars, watches, specific accessories

**Example - High Consistency (87-90% accuracy):**
```json
{
  "character_description": "Woman in late 20s with shoulder-length curly brown hair, wearing crisp white t-shirt with bold black text 'CHAD', blue denim jeans, silver watch on right wrist, small scar over left eyebrow"
}
```

**Example - Poor Consistency:**
```json
{
  "character_description": "A woman wearing casual clothes"
}
```

---

## Parameter Reference

### Quick Reference Cheat Sheet

| Category | Parameter | Optimal Values | Notes |
|----------|-----------|----------------|-------|
| **Technical** | `duration` | 5-8 sec | 5=quick, 8=standard |
| | `fps` | 24-30 | 24=cinematic, 30=web |
| | `resolution` | "1080p" | 720p=draft, 4K=premium |
| | `aspect_ratio` | "16:9", "9:16" | Platform-specific |
| **Camera** | `shot_type` | "close-up", "medium", "wide" | Vary for dynamics |
| | `movement` | "dolly", "pan", "tracking" | Keep smooth |
| | `lens` | "35mm", "50mm", "85mm" | Standard ranges |
| | `angle` | "eye level", "low", "high" | Match emotion |
| **Lighting** | `type` | "natural", "dramatic", "soft" | Sets mood |
| | `direction` | "front", "side", "back" | Creates depth |
| | `time_of_day` | "golden hour", "blue hour" | Visual appeal |
| **Style** | `visual_style` | "cinematic", "documentary" | Genre-specific |
| | `mood` | "dramatic", "peaceful" | Emotional tone |
| | `color_grading` | "teal/orange", "warm" | Color psychology |
| **Motion** | `motion_intensity` | 0.3-0.7 | 0.3=subtle, 0.7=dynamic |
| | `guidance_scale` | 8-12 | Prompt adherence |
| **Quality** | `negative_prompt` | Required | Always include |
| | `seed` | 0-2147483646 | For reproducibility |

### Platform Comparison

| Platform | Best For | Speed | Cost | Quality |
|----------|----------|-------|------|---------|
| **Veo 3.1** | Multi-scene, character consistency | Medium | $$$$ | Excellent |
| **Runway Gen-4** | Simple prompts, fast iteration | Fast | $$ | Excellent |
| **Luma Dream** | Keyframe control, speed | Fast | $ | Very Good |
| **Kling AI** | Long videos (up to 2 min) | Medium | $$ | Good |
| **Pika Labs** | Camera control, motion | Fast | $$ | Good |

---

## Best Practices

### 1. Character Consistency (87-90% accuracy)

**DO:**
```json
{
  "character": "Woman in late 20s, shoulder-length straight black hair, wearing white t-shirt with bold text 'HELLO' in red letters, blue denim jeans, round silver glasses, small mole on right cheek"
}
```

**DON'T:**
```json
{
  "character": "A young woman in casual clothes"
}
```

### 2. Always Use Negative Prompts

**Minimum Negative Prompt:**
```
blurry, low quality, distorted, text overlays, watermarks
```

**Comprehensive Negative Prompt:**
```
blurry, low quality, low resolution, distorted, deformed, grainy, pixelated, compression artifacts, watermarks, text overlays, subtitles, logos, duplicate subjects, extra limbs, motion blur
```

### 3. Optimize for Cost (60%+ Savings)

**Draft Workflow (80% of iterations):**
- Use Veo 3.1 Fast ($0.15/sec vs $0.40/sec)
- 720p resolution
- 16 FPS for testing
- Disable audio for silent videos

**Production Workflow (20% final):**
- Use Veo 3.1 Standard
- 1080p or 4K resolution
- 24-30 FPS
- Enable audio

### 4. Seed Management for A/B Testing

```json
{
  "prompt": "Your prompt here",
  "seed": 42,
  "duration": 8
}
```

**Same seed = identical output** (when other parameters unchanged)
- Use to test prompt variations
- Compare different settings
- Reproduce successful results

### 5. Structured Prompt Engineering Workflow

```yaml
step_1_concept:
  action: "Define idea in natural language"
  output: "Basic story/concept"

step_2_structure:
  action: "Convert to JSON/YAML format"
  output: "Structured prompt with parameters"

step_3_enhancement:
  action: "Add camera, lighting, style details"
  output: "Complete cinematic prompt"

step_4_draft:
  action: "Generate with fast/cheap settings"
  settings: {fps: 16, resolution: "720p", duration: 5}

step_5_production:
  action: "Generate final with premium settings"
  settings: {fps: 24, resolution: "1080p", duration: 8}

step_6_iteration:
  action: "Adjust based on results"
  method: "Use same seed for comparison"
```

### 6. Platform Selection Guide

**Choose Veo 3.1 when:**
- Need multi-scene videos
- Require character consistency across shots
- Want highest quality output
- Need audio generation

**Choose Runway Gen-4 when:**
- Simple single-scene prompts
- Want fastest results
- Prefer simplicity over control

**Choose Luma Dream Machine when:**
- Need first-last frame control
- Want fast iteration speed
- Working with keyframe animation

**Choose Kling AI when:**
- Need videos longer than 10 seconds (up to 2 min)
- Want creative/relevance slider control
- Need specific camera movements

**Choose Pika Labs when:**
- Need precise camera parameter control
- Want motion intensity adjustment
- Prefer credit-based pricing

### 7. Common Mistakes to Avoid

**❌ Vague Descriptions:**
```
"A person walking in a city"
```

**✅ Specific Details:**
```
"Athletic woman in her 30s with long dark ponytail, wearing black running outfit with neon green Nike swoosh, running through downtown Manhattan at dawn. Camera tracks alongside with smooth steadicam movement. Golden hour lighting creates warm glow on glass buildings. 85mm lens, shallow depth of field."
```

**❌ Inconsistent Character Descriptions:**
```
Scene 1: "A woman in casual clothes"
Scene 2: "Young female in relaxed attire"
```

**✅ Identical Character Descriptions:**
```
Scene 1 & 2: "Woman in late 20s, shoulder-length curly brown hair, white t-shirt with bold 'CHAD' text, blue jeans, silver watch right wrist"
```

**❌ No Negative Prompts:**
```json
{
  "prompt": "Beautiful sunset over ocean"
}
```

**✅ Always Include Negatives:**
```json
{
  "prompt": "Beautiful sunset over ocean with dramatic orange and purple clouds",
  "negative_prompt": "blurry, low quality, distorted, text overlays"
}
```

### 8. Temporal Coherence Best Practices

**For Multi-Scene Projects:**

1. **Copy-Paste Character Descriptions**: Never rephrase, always use identical text
2. **Maintain Lighting Consistency**: If same location, use same lighting description
3. **Track Props**: List all props in continuity section
4. **Plan Transitions**: Define transition types between scenes
5. **Control Motion**: Use motion_intensity < 0.7 for better frame coherence

### 9. Audio Generation Tips

**When to Enable Audio:**
- Dialogue scenes
- Narrative storytelling
- Atmospheric videos
- Videos requiring sound design

**When to Disable Audio (33% cost savings):**
- Silent B-roll
- Background footage
- Videos where custom audio will be added
- Draft/iteration phases

**Audio JSON Structure:**
```json
{
  "audio": {
    "dialogue": {
      "text": "This is the moment",
      "tone": "whispered, urgent"
    },
    "ambient": "rain on window, distant thunder",
    "music": "subtle piano melody, melancholic"
  }
}
```

### 10. Batch Processing for Efficiency

**Process Multiple Scenes in Parallel:**

```python
# Async API calls for 3x faster completion
import asyncio

scenes = [
    {"id": 1, "prompt": "Scene 1...", "duration": 5},
    {"id": 2, "prompt": "Scene 2...", "duration": 5},
    {"id": 3, "prompt": "Scene 3...", "duration": 5}
]

async def generate_all_scenes():
    tasks = [generate_video(scene) for scene in scenes]
    results = await asyncio.gather(*tasks)
    return results
```

---

## Complete Example: Product Video

### Scenario
Create a 15-second product video for Instagram Reels showcasing a water bottle.

### Storyboard

```json
{
  "project": {
    "title": "Water Bottle Product Video",
    "total_duration": 15,
    "target_platform": "Instagram Reels"
  },
  "global_settings": {
    "resolution": "1080p",
    "fps": 30,
    "aspect_ratio": "9:16",
    "color_grading": "vibrant, cool tones with warm highlights"
  },
  "scenes": [
    {
      "id": "scene_01",
      "duration": 3,
      "shot": {
        "type": "extreme close-up",
        "lens": "100mm macro",
        "camera_movement": "slow dolly in",
        "angle": "eye level"
      },
      "content": {
        "subject": "Stainless steel water bottle with condensation droplets",
        "action": "Water droplets slowly sliding down metallic surface, reflecting light",
        "environment": "Clean white studio background with soft shadows"
      },
      "lighting": {
        "type": "studio",
        "setup": "three-point lighting with cool blue rim light from left",
        "mood": "fresh, premium, crisp"
      },
      "audio": {
        "sound_effects": ["water droplet sounds", "gentle splash"],
        "music": "upbeat electronic intro, building energy"
      },
      "negative_prompt": "no text, no logos visible, no hands, not blurry, no distortion"
    },
    {
      "id": "scene_02",
      "duration": 5,
      "transition_in": "hard cut",
      "shot": {
        "type": "medium shot",
        "lens": "35mm",
        "camera_movement": "tracking shot following subject",
        "angle": "slightly low angle"
      },
      "content": {
        "subject": "Athletic woman in 30s with long black ponytail, wearing black athletic tank top with white Nike swoosh, black leggings, holding the water bottle",
        "action": "Running powerfully along beach shoreline at sunrise, confident expression, bottle clearly visible in right hand",
        "environment": "Golden sand beach, gentle waves washing up, dramatic sunrise sky with orange and pink clouds"
      },
      "lighting": {
        "type": "golden_hour",
        "description": "Warm sunrise backlight creating dramatic rim light on subject, golden glow on water",
        "mood": "energetic, inspiring, aspirational"
      },
      "audio": {
        "ambient": ["ocean waves", "footsteps on wet sand", "gentle breeze"],
        "music": "beat drops, energetic electronic music intensifies"
      },
      "negative_prompt": "no other people, no buildings, not blurry, no motion blur, no duplicates"
    },
    {
      "id": "scene_03",
      "duration": 3,
      "transition_in": "match cut on motion",
      "shot": {
        "type": "close-up",
        "lens": "50mm",
        "camera_movement": "slow dolly in",
        "angle": "slightly high angle"
      },
      "content": {
        "subject": "Same athletic woman with black ponytail, black Nike tank top, stopping to drink from bottle",
        "action": "Takes refreshing drink from bottle, eyes closed in satisfaction, slight smile forming",
        "environment": "Same beach location, slightly later morning with brighter light"
      },
      "lighting": {
        "type": "natural",
        "description": "Bright morning sunlight, clean shadows, warm glow on face",
        "mood": "refreshing, satisfying, accomplished"
      },
      "audio": {
        "sound_effects": ["drinking sound", "satisfied exhale"],
        "music": "melody reaches peak, uplifting"
      },
      "character_reference": "Must match scene_02 exactly: black ponytail, black Nike tank, same face",
      "negative_prompt": "not distorted, no motion blur, no extra limbs"
    },
    {
      "id": "scene_04",
      "duration": 4,
      "transition_in": "dissolve",
      "shot": {
        "type": "wide shot",
        "lens": "24mm",
        "camera_movement": "crane shot rising up and back",
        "angle": "starting low angle, rising to high angle"
      },
      "content": {
        "subject": "Water bottle positioned on large beach rock in foreground",
        "action": "Waves gently washing around rock base, golden sunlight streaming across water",
        "environment": "Beach at perfect sunrise moment, dramatic sky with clouds catching golden light, peaceful ocean"
      },
      "lighting": {
        "type": "golden_hour",
        "description": "Dramatic sunrise backlight, rim lighting on bottle creating glow, sparkles on water surface",
        "mood": "epic, aspirational, peaceful"
      },
      "audio": {
        "ambient": ["gentle waves", "soft wind", "distant seagulls"],
        "music": "outro with strings swelling, triumphant resolution"
      },
      "negative_prompt": "no people, no text overlay, clean composition, no distortion, not blurry"
    }
  ],
  "metadata": {
    "negative_prompt_global": "blurry, low quality, distorted, watermarks, logos, text overlays, compression artifacts",
    "color_palette": "Cool metallic blues for product, warm golden tones for beach scenes, high contrast",
    "music_style": "Upbeat electronic with organic elements, 120 BPM, building from subtle to energetic",
    "brand_message": "Hydration meets adventure - premium quality for active lifestyle"
  }
}
```

### Implementation Notes

1. **Character Consistency**: Scene 2 and 3 must use IDENTICAL character description
2. **Color Grading**: Maintain cool product tones vs warm environmental tones throughout
3. **Audio**: Music builds from scene 1 to peak at scene 3, resolves in scene 4
4. **Transitions**: Hard cut for energy (1→2), match cut for flow (2→3), dissolve for ending (3→4)
5. **Cost Optimization**: Generate scenes 1 and 4 (no character) first at high quality, then iterate on scenes 2-3 for character consistency

---

## Additional Resources

**Official Documentation:**
- [Google Veo 3 Prompt Guide](https://cloud.google.com/vertex-ai/generative-ai/docs/video/video-gen-prompt-guide)
- [Runway API Docs](https://docs.dev.runwayml.com/)
- [Luma AI Documentation](https://docs.lumalabs.ai/)

**Community Resources:**
- [Veo 3 JSON Prompting Guide](https://www.imagine.art/blogs/veo-3-json-prompting-guide)
- [Veo 3 Prompt Cheat Sheet](https://prompt-helper.com/veo-3-prompt-cheat-sheet/)

**GitHub Examples:**
- [Veo-3-Json-Prompt Repository](https://github.com/aliswl20/Veo-3-Json-Prompt-)
- [VideoTetris (NeurIPS 2024)](https://github.com/YangLing0818/VideoTetris)

---

**Document Version:** 1.0
**Last Updated:** January 2025
**Platforms Covered:** Veo 3.1, Runway Gen-3/4, Luma Dream Machine, Kling AI 2.5, Pika Labs 2.0

---

*This guide represents current state-of-the-art (2024-2025) structured prompting for AI video generation based on production implementations and industry research.*
