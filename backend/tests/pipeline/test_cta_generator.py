"""
Unit and Integration Tests for CTA Generator

Tests:
- CTAGenerator initialization
- CTA image generation with mocks
- Text overlay with Pillow
- All style configurations
- Error handling
- Integration test with actual FLUX API (if API key available)
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from PIL import Image

from pipeline.cta_generator import (
    CTAGenerator,
    CTAGenerationError,
    create_cta_generator,
    STYLE_CONFIGS,
)
from services.replicate_client import ReplicateClient
from pipeline.asset_manager import AssetManager


# Test Fixtures

@pytest.fixture
def mock_replicate_client():
    """Create a mock ReplicateClient"""
    client = Mock(spec=ReplicateClient)
    client.model_id = "black-forest-labs/flux-schnell"
    return client


@pytest.fixture
def cta_generator(mock_replicate_client):
    """Create CTAGenerator with mock client"""
    return CTAGenerator(mock_replicate_client)


@pytest.fixture
def mock_asset_manager(tmp_path):
    """Create a mock AssetManager with temporary directory"""
    am = Mock(spec=AssetManager)
    am.job_id = "test-job-123"
    am.job_dir = tmp_path / "test-job"
    am.job_dir.mkdir(exist_ok=True)
    return am


@pytest.fixture
def sample_cta_text():
    """Sample CTA text for testing"""
    return "Shop Now"


@pytest.fixture
def sample_base_image(tmp_path):
    """Create a sample base image for testing"""
    # Create a simple test image
    img = Image.new('RGB', (1080, 1920), color=(100, 100, 100))
    image_path = tmp_path / "cta_base.png"
    img.save(image_path)
    return str(image_path)


# Test CTAGenerator Initialization

def test_cta_generator_initialization(mock_replicate_client):
    """Test CTAGenerator initializes correctly"""
    generator = CTAGenerator(mock_replicate_client)

    assert generator.client == mock_replicate_client
    assert generator.model_id == "black-forest-labs/flux-schnell"
    assert generator.logger is not None


def test_create_cta_generator_factory():
    """Test factory function creates generator"""
    with patch('pipeline.cta_generator.get_replicate_client') as mock_get:
        mock_client = Mock(spec=ReplicateClient)
        mock_get.return_value = mock_client

        generator = create_cta_generator()

        assert isinstance(generator, CTAGenerator)
        assert generator.client == mock_client
        mock_get.assert_called_once()


def test_create_cta_generator_with_client(mock_replicate_client):
    """Test factory function with provided client"""
    generator = create_cta_generator(mock_replicate_client)

    assert isinstance(generator, CTAGenerator)
    assert generator.client == mock_replicate_client


# Test Prompt Preparation

def test_prepare_cta_prompt_luxury(cta_generator):
    """Test luxury style prompt preparation"""
    prompt = cta_generator._prepare_cta_prompt("Shop Now", "luxury")

    assert "elegant" in prompt.lower()
    assert "gold accents" in prompt.lower()
    assert "premium" in prompt.lower()
    assert "9:16 vertical" in prompt.lower()


def test_prepare_cta_prompt_energetic(cta_generator):
    """Test energetic style prompt preparation"""
    prompt = cta_generator._prepare_cta_prompt("Shop Now", "energetic")

    assert "vibrant" in prompt.lower()
    assert "bold colors" in prompt.lower()
    assert "dynamic energy" in prompt.lower()
    assert "9:16 vertical" in prompt.lower()


def test_prepare_cta_prompt_minimal(cta_generator):
    """Test minimal style prompt preparation"""
    prompt = cta_generator._prepare_cta_prompt("Shop Now", "minimal")

    assert "clean" in prompt.lower()
    assert "minimal" in prompt.lower()
    assert "simple" in prompt.lower()
    assert "9:16 vertical" in prompt.lower()


def test_prepare_cta_prompt_bold(cta_generator):
    """Test bold style prompt preparation"""
    prompt = cta_generator._prepare_cta_prompt("Shop Now", "bold")

    assert "strong contrasts" in prompt.lower()
    assert "dramatic" in prompt.lower()
    assert "powerful" in prompt.lower()
    assert "9:16 vertical" in prompt.lower()


def test_prepare_cta_prompt_with_product_name(cta_generator):
    """Test prompt preparation with product name"""
    prompt = cta_generator._prepare_cta_prompt(
        "Shop Now",
        "luxury",
        product_name="Premium Watch"
    )

    # Product name is optional context, not included in prompt
    assert isinstance(prompt, str)
    assert len(prompt) > 0


# Test Background Image Generation

@pytest.mark.asyncio
async def test_generate_background_image_success(cta_generator, mock_asset_manager, tmp_path):
    """Test successful background image generation"""
    # Mock FileOutput
    mock_file_output = Mock()
    mock_file_output.read.return_value = b"fake_image_data"

    # Mock client responses
    cta_generator.client.run_model_async = AsyncMock(return_value=[mock_file_output])
    cta_generator.client.download_output = Mock(return_value=str(tmp_path / "cta_base.png"))

    # Create test image file
    test_image = tmp_path / "cta_base.png"
    Image.new('RGB', (1080, 1920), color=(100, 100, 100)).save(test_image)

    # Call method
    result = await cta_generator._generate_background_image(
        prompt="test prompt",
        asset_manager=mock_asset_manager
    )

    # Assertions
    assert result == str(tmp_path / "cta_base.png")
    cta_generator.client.run_model_async.assert_called_once()

    # Check model parameters
    call_args = cta_generator.client.run_model_async.call_args
    assert call_args[1]["model_id"] == "black-forest-labs/flux-schnell"
    assert call_args[1]["input_params"]["width"] == 1080
    assert call_args[1]["input_params"]["height"] == 1920
    assert call_args[1]["input_params"]["num_outputs"] == 1


@pytest.mark.asyncio
async def test_generate_background_image_no_output(cta_generator, mock_asset_manager):
    """Test background generation with no output"""
    # Mock empty output
    cta_generator.client.run_model_async = AsyncMock(return_value=[])

    # Should raise error
    with pytest.raises(CTAGenerationError, match="no output"):
        await cta_generator._generate_background_image(
            prompt="test prompt",
            asset_manager=mock_asset_manager
        )


@pytest.mark.asyncio
async def test_generate_background_image_api_error(cta_generator, mock_asset_manager):
    """Test background generation with API error"""
    # Mock API error
    cta_generator.client.run_model_async = AsyncMock(
        side_effect=Exception("API Error")
    )

    # Should raise CTAGenerationError
    with pytest.raises(CTAGenerationError, match="Failed to generate background"):
        await cta_generator._generate_background_image(
            prompt="test prompt",
            asset_manager=mock_asset_manager
        )


# Test Text Overlay

def test_add_text_overlay_luxury(cta_generator, sample_base_image):
    """Test adding text overlay in luxury style"""
    result = cta_generator._add_text_overlay(
        image_path=sample_base_image,
        cta_text="Shop Now",
        style="luxury"
    )

    # Check output file exists
    assert Path(result).exists()
    assert "_final.png" in result

    # Verify image was modified
    img = Image.open(result)
    assert img.size == (1080, 1920)  # Same size as input


def test_add_text_overlay_energetic(cta_generator, sample_base_image):
    """Test adding text overlay in energetic style"""
    result = cta_generator._add_text_overlay(
        image_path=sample_base_image,
        cta_text="Buy Today",
        style="energetic"
    )

    assert Path(result).exists()
    assert "_final.png" in result


def test_add_text_overlay_minimal(cta_generator, sample_base_image):
    """Test adding text overlay in minimal style"""
    result = cta_generator._add_text_overlay(
        image_path=sample_base_image,
        cta_text="Learn More",
        style="minimal"
    )

    assert Path(result).exists()
    assert "_final.png" in result

    # Minimal style has no shadow
    config = STYLE_CONFIGS["minimal"]
    assert config["text_shadow"] is False


def test_add_text_overlay_bold(cta_generator, sample_base_image):
    """Test adding text overlay in bold style"""
    result = cta_generator._add_text_overlay(
        image_path=sample_base_image,
        cta_text="Act Now!",
        style="bold"
    )

    assert Path(result).exists()
    assert "_final.png" in result


def test_add_text_overlay_invalid_image(cta_generator):
    """Test text overlay with invalid image path"""
    with pytest.raises(CTAGenerationError, match="Failed to add text overlay"):
        cta_generator._add_text_overlay(
            image_path="/nonexistent/image.png",
            cta_text="Shop Now",
            style="luxury"
        )


def test_add_text_overlay_with_shadow(cta_generator, sample_base_image):
    """Test text overlay with shadow (luxury, energetic, bold styles)"""
    for style in ["luxury", "energetic", "bold"]:
        result = cta_generator._add_text_overlay(
            image_path=sample_base_image,
            cta_text="Test",
            style=style
        )

        assert Path(result).exists()

        # Verify shadow config
        config = STYLE_CONFIGS[style]
        assert config["text_shadow"] is True
        assert config["shadow_color"] is not None
        assert config["shadow_offset"] is not None


# Test Full CTA Generation

@pytest.mark.asyncio
async def test_generate_cta_success(cta_generator, mock_asset_manager, tmp_path):
    """Test successful CTA generation end-to-end"""
    # Mock background generation
    test_base_image = tmp_path / "cta_base.png"
    Image.new('RGB', (1080, 1920), color=(100, 100, 100)).save(test_base_image)

    cta_generator._generate_background_image = AsyncMock(
        return_value=str(test_base_image)
    )

    # Call generate_cta
    result = await cta_generator.generate_cta(
        cta_text="Shop Now",
        style="luxury",
        asset_manager=mock_asset_manager
    )

    # Assertions
    assert result is not None
    assert Path(result).exists()
    assert "_final.png" in result

    # Verify background generation was called
    cta_generator._generate_background_image.assert_called_once()


@pytest.mark.asyncio
async def test_generate_cta_all_styles(cta_generator, mock_asset_manager, tmp_path):
    """Test CTA generation for all styles"""
    # Mock background generation
    test_base_image = tmp_path / "cta_base.png"
    Image.new('RGB', (1080, 1920), color=(100, 100, 100)).save(test_base_image)

    cta_generator._generate_background_image = AsyncMock(
        return_value=str(test_base_image)
    )

    # Test each style
    for style in STYLE_CONFIGS.keys():
        result = await cta_generator.generate_cta(
            cta_text=f"{style.title()} CTA",
            style=style,
            asset_manager=mock_asset_manager
        )

        assert result is not None
        assert Path(result).exists()
        assert "_final.png" in result


@pytest.mark.asyncio
async def test_generate_cta_invalid_style(cta_generator, mock_asset_manager):
    """Test CTA generation with invalid style"""
    with pytest.raises(ValueError, match="Invalid style"):
        await cta_generator.generate_cta(
            cta_text="Shop Now",
            style="invalid_style",
            asset_manager=mock_asset_manager
        )


@pytest.mark.asyncio
async def test_generate_cta_missing_asset_manager(cta_generator):
    """Test CTA generation without asset manager"""
    with pytest.raises(ValueError, match="asset_manager is required"):
        await cta_generator.generate_cta(
            cta_text="Shop Now",
            style="luxury"
        )


@pytest.mark.asyncio
async def test_generate_cta_with_product_image(cta_generator, mock_asset_manager, tmp_path):
    """Test CTA generation with product image (reserved for future use)"""
    # Mock background generation
    test_base_image = tmp_path / "cta_base.png"
    Image.new('RGB', (1080, 1920), color=(100, 100, 100)).save(test_base_image)

    cta_generator._generate_background_image = AsyncMock(
        return_value=str(test_base_image)
    )

    # Create dummy product image
    product_image = tmp_path / "product.png"
    Image.new('RGB', (512, 512), color=(200, 200, 200)).save(product_image)

    # Call with product image (currently not used, but should not fail)
    result = await cta_generator.generate_cta(
        cta_text="Shop Now",
        style="luxury",
        product_image_path=str(product_image),
        asset_manager=mock_asset_manager
    )

    assert result is not None
    assert Path(result).exists()


@pytest.mark.asyncio
async def test_generate_cta_background_failure(cta_generator, mock_asset_manager):
    """Test CTA generation when background generation fails"""
    # Mock background generation failure
    cta_generator._generate_background_image = AsyncMock(
        side_effect=Exception("Background generation failed")
    )

    # Should raise CTAGenerationError
    with pytest.raises(CTAGenerationError, match="Failed to generate CTA image"):
        await cta_generator.generate_cta(
            cta_text="Shop Now",
            style="luxury",
            asset_manager=mock_asset_manager
        )


# Test Style Configurations

def test_all_styles_have_required_fields():
    """Test that all style configs have required fields"""
    required_fields = [
        "background_prompt",
        "font_family",
        "font_size",
        "font_color",
        "text_position",
        "text_shadow",
    ]

    for style, config in STYLE_CONFIGS.items():
        for field in required_fields:
            assert field in config, f"Style '{style}' missing field '{field}'"


def test_style_font_sizes():
    """Test that font sizes are reasonable"""
    for style, config in STYLE_CONFIGS.items():
        font_size = config["font_size"]
        assert 32 <= font_size <= 128, f"Style '{style}' has unreasonable font size: {font_size}"


def test_style_colors():
    """Test that font colors are valid RGB tuples"""
    for style, config in STYLE_CONFIGS.items():
        color = config["font_color"]
        assert isinstance(color, tuple), f"Style '{style}' color is not a tuple"
        assert len(color) == 3, f"Style '{style}' color is not RGB"
        assert all(0 <= c <= 255 for c in color), f"Style '{style}' has invalid color values"


def test_style_prompts_contain_vertical_format():
    """Test that all prompts specify vertical format"""
    for style, config in STYLE_CONFIGS.items():
        prompt = config["background_prompt"]
        assert "9:16" in prompt or "vertical" in prompt, \
            f"Style '{style}' prompt doesn't specify vertical format"


# Integration Test (requires REPLICATE_API_TOKEN)

@pytest.mark.integration
@pytest.mark.asyncio
async def test_generate_cta_integration(tmp_path):
    """
    Integration test with actual Replicate API.

    This test requires REPLICATE_API_TOKEN to be set in environment.
    Run with: pytest -m integration

    Note: FLUX may return different sizes than requested. This test verifies
    that the image is generated and has reasonable dimensions.
    """
    import os
    from services.replicate_client import get_replicate_client

    # Skip if no API key
    if not os.getenv("REPLICATE_API_TOKEN"):
        pytest.skip("REPLICATE_API_TOKEN not set")

    # Create real client and generator
    client = get_replicate_client()
    generator = CTAGenerator(client)

    # Create real asset manager
    am = AssetManager("integration-test")
    await am.create_job_directory()

    try:
        # Generate CTA
        result = await generator.generate_cta(
            cta_text="Shop Now",
            style="luxury",
            asset_manager=am
        )

        # Verify result
        assert result is not None
        assert Path(result).exists()

        # Check image properties (FLUX may return different sizes than requested)
        img = Image.open(result)
        assert img.size[0] >= 512  # Reasonable width
        assert img.size[1] >= 512  # Reasonable height
        assert img.format == "PNG"

        print(f"✓ Integration test successful: {result}")
        print(f"  Generated image size: {img.size}")

    finally:
        # Cleanup
        await am.cleanup()


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s"])
