"""
Scene template system for video generation.

Uses hardcoded templates for guaranteed quality and coherence.
This is a deliberate architectural choice to ensure 100% predictable structure
rather than relying on dynamic LLM-generated scenes which can be inconsistent.
"""

from typing import Dict, List, Any
import copy


def get_scene_template(style: str) -> Dict[str, Any]:
    """
    Returns a 4-scene template for 30-second ads.

    Each template is carefully crafted for a specific visual style with:
    - Consistent pacing (8s, 8s, 10s, 4s = 30s total)
    - Scene 4 as static image (cost optimization)
    - Product-focused composition
    - Professional voiceover timing

    Args:
        style: One of 'luxury', 'energetic', 'minimal', 'bold'

    Returns:
        Dictionary with scene specifications including:
        - total_duration: Total video length in seconds
        - style_keywords: Visual style descriptors
        - scenes: List of scene specifications

    Example:
        >>> template = get_scene_template("luxury")
        >>> print(template["total_duration"])
        30
        >>> print(len(template["scenes"]))
        4
    """

    templates = {
        "luxury": {
            "total_duration": 30,
            "style_keywords": "soft lighting, elegant, premium, refined",
            "scenes": [
                {
                    "id": 1,
                    "duration": 8,
                    "type": "video",
                    "video_prompt_template": "Close-up of {product_name}, slow camera tilt, luxury lighting, soft white background, premium product photography, cinematic depth of field, 9:16 vertical format",
                    "use_product_image": True,
                    "voiceover_template": "Discover {product_name}.",
                    "text_overlay": "{product_name}",
                    "text_timing": "0.3s before voice",
                    "text_style": "elegant serif, gold accent"
                },
                {
                    "id": 2,
                    "duration": 8,
                    "type": "video",
                    "video_prompt_template": "Elegant hand holding {product_name}, soft focus, luxury aesthetic, natural light, lifestyle photography, sophisticated composition, 9:16 vertical",
                    "use_product_image": False,
                    "voiceover_template": "[benefit statement]",
                    "text_overlay": "Transform Your Experience",
                    "text_timing": "fade in 1s",
                    "text_style": "elegant serif, subtle animation"
                },
                {
                    "id": 3,
                    "duration": 10,
                    "type": "video",
                    "video_prompt_template": "{product_name} in beautiful setting, luxury mood, premium feel, slow motion, elegant composition, refined atmosphere, 9:16 vertical",
                    "use_product_image": True,
                    "voiceover_template": "[social proof]",
                    "text_overlay": "Loved by Thousands",
                    "text_timing": "fade in 1s",
                    "text_style": "elegant serif, soft glow"
                },
                {
                    "id": 4,
                    "duration": 4,
                    "type": "image",
                    "image_prompt_template": "Clean white background, {product_name} in corner, bold text: '{cta_text}', modern luxury typography, minimalist design, 9:16 vertical",
                    "voiceover_template": "Get yours today.",
                    "text_overlay": "{cta_text}",
                    "text_timing": "immediate",
                    "text_style": "luxury sans-serif, bold"
                }
            ]
        },
        "energetic": {
            "total_duration": 30,
            "style_keywords": "vibrant, dynamic, bold, exciting, high-energy",
            "scenes": [
                {
                    "id": 1,
                    "duration": 8,
                    "type": "video",
                    "video_prompt_template": "{product_name} with dynamic camera movement, vibrant colors, energetic lighting, bold composition, fast-paced action, 9:16 vertical format",
                    "use_product_image": True,
                    "voiceover_template": "Introducing {product_name}!",
                    "text_overlay": "{product_name}",
                    "text_timing": "0.2s before voice",
                    "text_style": "bold sans-serif, bright colors"
                },
                {
                    "id": 2,
                    "duration": 8,
                    "type": "video",
                    "video_prompt_template": "{product_name} in action, high energy, dynamic movement, vibrant setting, exciting composition, bold colors, 9:16 vertical",
                    "use_product_image": False,
                    "voiceover_template": "[benefit statement]",
                    "text_overlay": "Unleash Your Potential",
                    "text_timing": "snap in 0.5s",
                    "text_style": "bold sans-serif, energetic animation"
                },
                {
                    "id": 3,
                    "duration": 10,
                    "type": "video",
                    "video_prompt_template": "Fast-paced shots of {product_name}, dynamic angles, vibrant atmosphere, energetic mood, bold visuals, exciting composition, 9:16 vertical",
                    "use_product_image": True,
                    "voiceover_template": "[social proof]",
                    "text_overlay": "Join the Movement",
                    "text_timing": "zoom in 0.8s",
                    "text_style": "bold sans-serif, dynamic pulse"
                },
                {
                    "id": 4,
                    "duration": 4,
                    "type": "image",
                    "image_prompt_template": "Vibrant gradient background, {product_name} centered, bold text: '{cta_text}', energetic typography, dynamic design, 9:16 vertical",
                    "voiceover_template": "Get it now!",
                    "text_overlay": "{cta_text}",
                    "text_timing": "immediate",
                    "text_style": "bold sans-serif, vibrant colors"
                }
            ]
        },
        "minimal": {
            "total_duration": 30,
            "style_keywords": "clean, simple, modern, minimal, understated",
            "scenes": [
                {
                    "id": 1,
                    "duration": 8,
                    "type": "video",
                    "video_prompt_template": "{product_name} on clean white surface, minimalist composition, simple lighting, modern aesthetic, clean lines, 9:16 vertical format",
                    "use_product_image": True,
                    "voiceover_template": "Meet {product_name}.",
                    "text_overlay": "{product_name}",
                    "text_timing": "0.5s before voice",
                    "text_style": "minimal sans-serif, black text"
                },
                {
                    "id": 2,
                    "duration": 8,
                    "type": "video",
                    "video_prompt_template": "Simple scene with {product_name}, clean background, minimal styling, modern composition, understated elegance, 9:16 vertical",
                    "use_product_image": False,
                    "voiceover_template": "[benefit statement]",
                    "text_overlay": "Simply Better",
                    "text_timing": "fade in 1.5s",
                    "text_style": "minimal sans-serif, subtle"
                },
                {
                    "id": 3,
                    "duration": 10,
                    "type": "video",
                    "video_prompt_template": "{product_name} in minimalist setting, clean aesthetic, simple composition, modern feel, understated presentation, 9:16 vertical",
                    "use_product_image": True,
                    "voiceover_template": "[social proof]",
                    "text_overlay": "Trusted Simplicity",
                    "text_timing": "fade in 2s",
                    "text_style": "minimal sans-serif, clean"
                },
                {
                    "id": 4,
                    "duration": 4,
                    "type": "image",
                    "image_prompt_template": "Pure white background, {product_name} minimal placement, clean text: '{cta_text}', modern minimal typography, 9:16 vertical",
                    "voiceover_template": "Learn more.",
                    "text_overlay": "{cta_text}",
                    "text_timing": "immediate",
                    "text_style": "minimal sans-serif, simple"
                }
            ]
        },
        "bold": {
            "total_duration": 30,
            "style_keywords": "strong, impactful, striking, bold, dramatic",
            "scenes": [
                {
                    "id": 1,
                    "duration": 8,
                    "type": "video",
                    "video_prompt_template": "{product_name} with dramatic lighting, strong shadows, bold composition, impactful presentation, striking visuals, 9:16 vertical format",
                    "use_product_image": True,
                    "voiceover_template": "This is {product_name}.",
                    "text_overlay": "{product_name}",
                    "text_timing": "0.1s before voice",
                    "text_style": "bold condensed, high contrast"
                },
                {
                    "id": 2,
                    "duration": 8,
                    "type": "video",
                    "video_prompt_template": "Strong visual of {product_name}, dramatic atmosphere, bold styling, impactful lighting, striking composition, 9:16 vertical",
                    "use_product_image": False,
                    "voiceover_template": "[benefit statement]",
                    "text_overlay": "Make Your Statement",
                    "text_timing": "hard cut 0.3s",
                    "text_style": "bold condensed, strong impact"
                },
                {
                    "id": 3,
                    "duration": 10,
                    "type": "video",
                    "video_prompt_template": "{product_name} with powerful visuals, dramatic mood, bold presentation, striking atmosphere, impactful composition, 9:16 vertical",
                    "use_product_image": True,
                    "voiceover_template": "[social proof]",
                    "text_overlay": "Leaders Choose Us",
                    "text_timing": "slam in 0.5s",
                    "text_style": "bold condensed, dramatic"
                },
                {
                    "id": 4,
                    "duration": 4,
                    "type": "image",
                    "image_prompt_template": "Black background, {product_name} prominent, bold text: '{cta_text}', strong typography, dramatic contrast, 9:16 vertical",
                    "voiceover_template": "Take action now.",
                    "text_overlay": "{cta_text}",
                    "text_timing": "immediate",
                    "text_style": "bold condensed, maximum impact"
                }
            ]
        }
    }

    # Return deep copy to prevent template mutation
    return copy.deepcopy(templates.get(style, templates["luxury"]))


def fill_template(template: Dict[str, Any], product_name: str, cta_text: str) -> Dict[str, Any]:
    """
    Fills template with actual product information.

    Replaces placeholder variables in all template strings:
    - {product_name}: Name of the product being advertised
    - {cta_text}: Call-to-action text (e.g., "Shop Now", "Learn More")

    Args:
        template: Scene template from get_scene_template()
        product_name: Actual product name to insert
        cta_text: Call-to-action text for final scene

    Returns:
        Template with all placeholders replaced

    Example:
        >>> template = get_scene_template("luxury")
        >>> filled = fill_template(template, "Premium Watch", "Shop Now")
        >>> print(filled["scenes"][0]["voiceover_template"])
        'Discover Premium Watch.'
    """
    # Deep copy to avoid mutating the original template
    filled = copy.deepcopy(template)

    # Replace placeholders in all scenes
    for scene in filled["scenes"]:
        # Replace in video/image prompts
        if "video_prompt_template" in scene:
            scene["video_prompt_template"] = scene["video_prompt_template"].replace(
                "{product_name}", product_name
            ).replace("{cta_text}", cta_text)

        if "image_prompt_template" in scene:
            scene["image_prompt_template"] = scene["image_prompt_template"].replace(
                "{product_name}", product_name
            ).replace("{cta_text}", cta_text)

        # Replace in voiceover
        if "voiceover_template" in scene:
            scene["voiceover_template"] = scene["voiceover_template"].replace(
                "{product_name}", product_name
            ).replace("{cta_text}", cta_text)

        # Replace in text overlay
        if "text_overlay" in scene:
            scene["text_overlay"] = scene["text_overlay"].replace(
                "{product_name}", product_name
            ).replace("{cta_text}", cta_text)

    return filled


def get_available_styles() -> List[str]:
    """
    Returns list of available template styles.

    Returns:
        List of style names that can be used with get_scene_template()

    Example:
        >>> styles = get_available_styles()
        >>> print(styles)
        ['luxury', 'energetic', 'minimal', 'bold']
    """
    return ["luxury", "energetic", "minimal", "bold"]


def validate_template(template: Dict[str, Any]) -> bool:
    """
    Validates that a template has the required structure.

    Checks for:
    - total_duration field
    - scenes list with 4 scenes
    - Required fields in each scene

    Args:
        template: Template to validate

    Returns:
        True if template is valid, False otherwise

    Example:
        >>> template = get_scene_template("luxury")
        >>> validate_template(template)
        True
    """
    try:
        # Check top-level fields
        if "total_duration" not in template:
            return False
        if "scenes" not in template:
            return False
        if len(template["scenes"]) != 4:
            return False

        # Check each scene
        required_scene_fields = ["id", "duration", "type"]
        for scene in template["scenes"]:
            for field in required_scene_fields:
                if field not in scene:
                    return False

            # Scene 4 should be image type
            if scene["id"] == 4 and scene["type"] != "image":
                return False

        # Check total duration matches sum of scenes
        total = sum(scene["duration"] for scene in template["scenes"])
        if total != template["total_duration"]:
            return False

        return True
    except Exception:
        return False
