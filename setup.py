#!/usr/bin/env python3
"""
Interactive setup script for CLIPER
Creates .env file with user input
"""

import os
import sys
import argparse
from pathlib import Path

def get_input(prompt: str, default: str = None) -> str:
    """Get user input with optional default value"""
    if default:
        full_prompt = f"{prompt} [{default}]: "
    else:
        full_prompt = f"{prompt}: "

    user_input = input(full_prompt).strip()
    return user_input if user_input else default

def confirm(prompt: str) -> bool:
    """Get yes/no confirmation from user"""
    response = input(f"{prompt} (y/n): ").strip().lower()
    return response in ['y', 'yes']

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Interactive CLIPER setup script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python setup.py                    # Create/update .env in current directory
  python setup.py --output=.env.demo # Create .env.demo instead
  python setup.py --output=/etc/cliper.env  # Custom path
        """
    )
    parser.add_argument(
        "--output",
        default=".env",
        help="Output file path (default: .env)"
    )

    args = parser.parse_args()
    env_path = Path(args.output)

    print("\n" + "="*60)
    print("🎬 CLIPER SETUP")
    print("="*60)
    print(f"\nThis script will help you configure CLIPER.")
    print(f"Configuration will be saved to: {env_path.resolve()}\n")

    # Check if output file already exists
    existing_env = {}

    if env_path.exists():
        # Load existing .env values
        existing_content = env_path.read_text()
        for line in existing_content.split('\n'):
            if '=' in line and not line.strip().startswith('#'):
                key, value = line.split('=', 1)
                existing_env[key.strip()] = value.strip()

        if not confirm(f"{env_path.name} already exists. Update settings?"):
            print("Setup cancelled.")
            return

    # Load .env.example as template
    example_path = Path(".env.example")
    if not example_path.exists():
        print("Error: .env.example not found")
        sys.exit(1)

    env_example = example_path.read_text()

    print("\n" + "-"*60)
    print("REQUIRED SETTINGS")
    print("-"*60)

    # Google API Key (required)
    print("\n🔑 Google Gemini API Key")
    print("This is required for AI caption generation.")
    print("Get your free API key at: https://aistudio.google.com/app/apikey\n")

    default_api_key = existing_env.get('GOOGLE_API_KEY', '')
    if default_api_key:
        # Mask the existing key for display
        masked_key = '*' * (len(default_api_key) - 4) + default_api_key[-4:]
        api_key = get_input("Enter your Google API key (or keep existing)", masked_key)
        # If user didn't change it (entered the masked version), use the existing key
        if api_key == masked_key:
            api_key = default_api_key
    else:
        api_key = get_input("Enter your Google API key")

    if not api_key or api_key.startswith('*'):
        print("Error: Valid API key is required")
        sys.exit(1)

    print("\n✓ API key configured\n")

    print("-"*60)
    print("TRANSCRIPTION SETTINGS (Optional)")
    print("-"*60)

    # Whisper Model
    print("\nWhisper Model for transcription:")
    print("  tiny    - Fastest (low accuracy)")
    print("  base    - Good balance (recommended)")
    print("  small   - Better accuracy")
    print("  medium  - High accuracy")
    print("  large   - Best accuracy (slowest)")

    default_whisper = existing_env.get('WHISPER_MODEL', 'base')
    whisper_model = get_input("Select Whisper model", default_whisper)
    if whisper_model not in ['tiny', 'base', 'small', 'medium', 'large']:
        print(f"Warning: '{whisper_model}' is not a standard model size, using as-is")

    # Whisper Language
    default_lang = existing_env.get('WHISPER_LANGUAGE', '')
    whisper_lang = get_input("Language for transcription (ISO 639-1 code, or leave empty for auto-detect)", default_lang)

    print("\n✓ Transcription settings configured\n")

    print("-"*60)
    print("CLIP GENERATION SETTINGS (Optional)")
    print("-"*60)

    default_min = existing_env.get('MIN_CLIP_DURATION', '30')
    default_max = existing_env.get('MAX_CLIP_DURATION', '90')
    min_clip = get_input("Minimum clip duration (seconds)", default_min)
    max_clip = get_input("Maximum clip duration (seconds)", default_max)

    try:
        min_val = int(min_clip)
        max_val = int(max_clip)
        if min_val > max_val:
            print("Warning: Min duration is greater than max, swapping values")
            min_clip, max_clip = max_clip, min_clip
    except ValueError:
        print("Warning: Invalid duration values, using defaults")
        min_clip, max_clip = "30", "90"

    print("\n✓ Clip generation settings configured\n")

    print("-"*60)
    print("AI CAPTION SETTINGS (Optional)")
    print("-"*60)

    print("\nGemini Model:")
    print("  gemini-2.0-flash-exp - Faster and cheaper (recommended)")
    print("  gemini-1.5-pro       - More powerful but slower")

    default_gemini = existing_env.get('GEMINI_MODEL', 'gemini-2.0-flash-exp')
    gemini_model = get_input("Select Gemini model", default_gemini)

    print("\nCaption Generation Style:")
    print("  auto         - Let AI decide based on content (recommended)")
    print("  viral        - High-engagement, hook-driven")
    print("  educational  - Value-focused, educational")
    print("  storytelling - Narrative-driven, emotional")

    default_style = existing_env.get('COPY_STYLE', 'auto')
    copy_style = get_input("Select caption style", default_style)

    print("\n✓ AI caption settings configured\n")

    print("-"*60)
    print("VIDEO EXPORT SETTINGS (Optional)")
    print("-"*60)

    print("\nVideo Quality (CRF: 18-28, lower = better quality):")
    print("  18-20 - High quality (large files)")
    print("  21-23 - Recommended (good balance)")
    print("  24-26 - Lower quality (smaller files)")

    default_crf = existing_env.get('VIDEO_CRF', '23')
    video_crf = get_input("Video quality (CRF)", default_crf)

    try:
        crf_val = int(video_crf)
        if not 0 <= crf_val <= 51:
            print("Warning: CRF should be between 0-51, using default")
            video_crf = default_crf
    except ValueError:
        print("Warning: Invalid CRF value, using default")
        video_crf = default_crf

    default_sub_size = existing_env.get('SUBTITLE_FONT_SIZE', '24')
    default_sub_color = existing_env.get('SUBTITLE_FONT_COLOR', 'white')
    subtitle_size = get_input("Subtitle font size", default_sub_size)
    subtitle_color = get_input("Subtitle font color", default_sub_color)

    print("\n✓ Video export settings configured\n")

    # Generate .env file
    print("-"*60)
    print("SUMMARY")
    print("-"*60)

    env_content = f"""# ============================================================================
# CLIPER Environment Configuration
# ============================================================================
# Auto-generated by setup.py
# Last configured: {os.popen('date').read().strip()}

# ============================================================================
# GOOGLE GEMINI API (REQUIRED for AI Copy Generation)
# ============================================================================
# Get your free API key at: https://aistudio.google.com/app/apikey
# Used for: AI-powered caption generation with LangGraph
# Cost: ~$0.02 USD per video (99 clips) with Gemini 2.0 Flash
GOOGLE_API_KEY={api_key}

# ============================================================================
# TRANSCRIPTION SETTINGS (Optional - WhisperX runs locally)
# ============================================================================
# Whisper model size: tiny, base, small, medium, large
# Larger = more accurate but slower
# Recommended: base (good balance) or medium (best quality)
WHISPER_MODEL={whisper_model}

# Language for transcription (ISO 639-1 code)
# Leave empty for auto-detection
# Examples: es (Spanish), en (English), fr (French)
WHISPER_LANGUAGE={whisper_lang}

# ============================================================================
# CLIP GENERATION SETTINGS (Optional)
# ============================================================================
# Minimum clip duration in seconds
MIN_CLIP_DURATION={min_clip}

# Maximum clip duration in seconds
MAX_CLIP_DURATION={max_clip}

# ============================================================================
# AI COPY GENERATION SETTINGS (Optional)
# ============================================================================
# Gemini model to use for copy generation
# Options: gemini-2.0-flash-exp (faster, cheaper), gemini-1.5-pro (more powerful)
# Recommended: gemini-2.0-flash-exp
GEMINI_MODEL={gemini_model}

# Copy generation style
# Options: auto (LangGraph decides), viral, educational, storytelling
# Recommended: auto
COPY_STYLE={copy_style}

# ============================================================================
# VIDEO EXPORT SETTINGS (Optional)
# ============================================================================
# Output video quality (CRF value: 18-28, lower = better quality)
# Recommended: 23 (good quality, reasonable file size)
VIDEO_CRF={video_crf}

# Subtitle font size (default: 24)
SUBTITLE_FONT_SIZE={subtitle_size}

# Subtitle font color (default: white)
SUBTITLE_FONT_COLOR={subtitle_color}

# ============================================================================
# NOTES
# ============================================================================
# - WhisperX runs 100% locally (no API key needed)
# - ClipsAI runs 100% locally (no API key needed)
# - Only Gemini requires an API key
# - All settings have sensible defaults if not specified
# - For production use, consider using .env.production
"""

    # Create parent directory if needed
    env_path.parent.mkdir(parents=True, exist_ok=True)

    # Write .env file
    env_path.write_text(env_content)
    print(f"\n✓ Configuration saved to {env_path.resolve()}")
    print(f"\nSettings applied:")
    print(f"  • Gemini API Key: {'*' * (len(api_key) - 4) + api_key[-4:]}")
    print(f"  • Whisper Model: {whisper_model}")
    print(f"  • Clip Duration: {min_clip}s - {max_clip}s")
    print(f"  • Gemini Model: {gemini_model}")
    print(f"  • Caption Style: {copy_style}")
    print(f"  • Video Quality: {video_crf}")

    print("\n" + "="*60)
    print("✨ Setup complete! You're ready to use CLIPER.")
    print("="*60)
    print("\nNext steps:")
    print("  1. Run: uv sync")
    print("  2. Run: uv run cliper.py")
    print("     or")
    print("     python cliper_gui.py")
    print("\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSetup cancelled.")
        sys.exit(0)
