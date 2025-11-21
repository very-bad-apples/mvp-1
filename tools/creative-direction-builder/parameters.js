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

