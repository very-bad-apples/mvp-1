#!/usr/bin/env python3
"""
Template validation script for mode-based templates.

Validates YAML syntax, required fields, types, and placeholder presence.

Usage:
    python scripts/validate_templates.py                    # Validate all templates
    python scripts/validate_templates.py --mode music-video # Validate specific mode
    python scripts/validate_templates.py --mode ad-creative # Validate specific mode
    python scripts/validate_templates.py --verbose          # Show detailed output
"""

import sys
from pathlib import Path

# Add parent directory to Python path so we can import backend modules
script_dir = Path(__file__).parent
backend_dir = script_dir.parent
sys.path.insert(0, str(backend_dir))

import argparse
from mv.template_loader import (
    load_mode_template,
    get_available_modes,
    TemplateError,
)


def validate_all_templates(verbose: bool = False) -> bool:
    """
    Validate all available templates.
    
    Args:
        verbose: If True, show detailed output
        
    Returns:
        True if all templates valid, False otherwise
    """
    modes = get_available_modes()
    all_valid = True
    
    print(f"\n🔍 Validating {len(modes)} template(s)...\n")
    
    for mode in modes:
        try:
            if verbose:
                print(f"  Validating mode: {mode}")
            
            template = load_mode_template(mode)
            
            # Show summary
            print(f"  ✅ {mode}")
            if verbose:
                print(f"     - Number of scenes: {template['number_of_scenes']}")
                print(f"     - Duration per scene: {template['duration_per_scene']}s")
                print(f"     - Camera angle: {template['camera_angle']}")
                print(f"     - Video characteristics: {template['video_characteristics'][:50]}...")
                print(f"     - Prompt template length: {len(template['prompt_template'])} chars")
                print()
        except TemplateError as e:
            print(f"  ❌ {mode}: {e}")
            all_valid = False
            if verbose:
                print()
        except Exception as e:
            print(f"  ❌ {mode}: Unexpected error: {e}")
            all_valid = False
            if verbose:
                print()
    
    return all_valid


def validate_single_template(mode: str, verbose: bool = False) -> bool:
    """
    Validate a single template for a specific mode.
    
    Args:
        mode: Mode to validate
        verbose: If True, show detailed output
        
    Returns:
        True if template valid, False otherwise
    """
    try:
        if verbose:
            print(f"\n🔍 Validating template for mode: {mode}\n")
        
        template = load_mode_template(mode)
        
        print(f"✅ Template valid: {mode}")
        
        if verbose:
            print(f"\n📋 Template Details:")
            print(f"   Number of scenes: {template['number_of_scenes']}")
            print(f"   Duration per scene: {template['duration_per_scene']}s")
            print(f"   Camera angle: {template['camera_angle']}")
            print(f"   Video characteristics: {template['video_characteristics']}")
            print(f"\n📝 Prompt Template Preview:")
            prompt_preview = template['prompt_template'][:200]
            print(f"   {prompt_preview}...")
            print(f"\n   Full length: {len(template['prompt_template'])} characters")
            
            # Check placeholders
            required_placeholders = [
                "{concept_prompt}",
                "{personality_profile}",
                "{video_characteristics}",
                "{camera_angle}",
                "{number_of_scenes}",
                "{duration_per_scene}",
                "{director_style_section}",
            ]
            
            print(f"\n🔗 Placeholders:")
            for placeholder in required_placeholders:
                present = placeholder in template['prompt_template']
                status = "✅" if present else "❌"
                print(f"   {status} {placeholder}")
        
        return True
        
    except TemplateError as e:
        print(f"❌ Template validation failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Validate mode-based templates",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/validate_templates.py
  python scripts/validate_templates.py --mode music-video
  python scripts/validate_templates.py --mode ad-creative --verbose
        """
    )
    parser.add_argument(
        "--mode",
        choices=get_available_modes(),
        help="Validate specific mode (default: validate all)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed output"
    )
    
    args = parser.parse_args()
    
    if args.mode:
        success = validate_single_template(args.mode, args.verbose)
    else:
        success = validate_all_templates(args.verbose)
    
    if success:
        print("\n✅ All templates are valid!\n")
        sys.exit(0)
    else:
        print("\n❌ Some templates failed validation.\n")
        sys.exit(1)


if __name__ == "__main__":
    main()

