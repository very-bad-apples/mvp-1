"""
Demo script for FileUploadService

Demonstrates all features of the file upload service.
"""

import asyncio
from pathlib import Path
from PIL import Image
import io
from services.file_upload import FileUploadService


def create_sample_image(format="JPEG", size=(1920, 1080)):
    """Create a sample image for testing"""
    # Create a gradient image
    img = Image.new('RGB', size)
    pixels = img.load()

    for i in range(size[0]):
        for j in range(size[1]):
            # Create a nice gradient
            r = int(255 * i / size[0])
            g = int(255 * j / size[1])
            b = 128
            pixels[i, j] = (r, g, b)

    # Save to bytes
    img_bytes = io.BytesIO()
    img.save(img_bytes, format=format)
    return img_bytes.getvalue()


async def main():
    print("=" * 70)
    print("File Upload Service Demo")
    print("=" * 70)

    # Initialize service
    service = FileUploadService(upload_dir="/tmp/demo_uploads")
    print(f"\nInitialized FileUploadService at: /tmp/demo_uploads")

    # Demo 1: Upload valid JPEG
    print("\n" + "-" * 70)
    print("Demo 1: Upload valid JPEG image")
    print("-" * 70)

    jpeg_bytes = create_sample_image(format="JPEG", size=(1920, 1080))
    result = await service.process_upload(
        file_content=jpeg_bytes,
        filename="product_image.jpg",
        session_id="demo_session_1",
        generate_thumbnail=True
    )

    print(f"Success: {result['success']}")
    print(f"Format: {result['format']}")
    print(f"Size: {result['size_bytes']:,} bytes ({result['size_bytes'] / 1024:.2f} KB)")
    print(f"File path: {result['file_path']}")
    print(f"Thumbnail: {result['thumbnail_path']}")

    # Verify thumbnail size
    if result['thumbnail_path']:
        with Image.open(result['thumbnail_path']) as img:
            print(f"Thumbnail dimensions: {img.width}x{img.height}")

    # Demo 2: Upload PNG with transparency
    print("\n" + "-" * 70)
    print("Demo 2: Upload PNG with transparency")
    print("-" * 70)

    # Create PNG with transparency
    png_img = Image.new('RGBA', (800, 600), (255, 0, 0, 128))
    png_bytes = io.BytesIO()
    png_img.save(png_bytes, format="PNG")
    png_bytes = png_bytes.getvalue()

    result = await service.process_upload(
        file_content=png_bytes,
        filename="transparent.png",
        session_id="demo_session_2",
        generate_thumbnail=True
    )

    print(f"Success: {result['success']}")
    print(f"Format: {result['format']}")
    print(f"File path: {result['file_path']}")
    print(f"Thumbnail: {result['thumbnail_path']}")

    # Demo 3: Try to upload file that's too large
    print("\n" + "-" * 70)
    print("Demo 3: Upload file exceeding size limit (should fail)")
    print("-" * 70)

    large_bytes = b"X" * (11 * 1024 * 1024)  # 11MB
    result = await service.process_upload(
        file_content=large_bytes,
        filename="too_large.jpg"
    )

    print(f"Success: {result['success']}")
    print(f"Error: {result['error']}")

    # Demo 4: Try to upload invalid format
    print("\n" + "-" * 70)
    print("Demo 4: Upload invalid image format (should fail)")
    print("-" * 70)

    invalid_bytes = b"This is not an image"
    result = await service.process_upload(
        file_content=invalid_bytes,
        filename="invalid.jpg"
    )

    print(f"Success: {result['success']}")
    print(f"Error: {result['error']}")

    # Demo 5: List session files
    print("\n" + "-" * 70)
    print("Demo 5: List files in session")
    print("-" * 70)

    files = await service.get_session_files("demo_session_1")
    print(f"Files in demo_session_1:")
    for f in files:
        print(f"  - {Path(f).name}")

    # Demo 6: WebP format
    print("\n" + "-" * 70)
    print("Demo 6: Upload WebP format")
    print("-" * 70)

    webp_img = Image.new('RGB', (640, 480), (0, 255, 0))
    webp_bytes = io.BytesIO()
    webp_img.save(webp_bytes, format="WEBP")
    webp_bytes = webp_bytes.getvalue()

    result = await service.process_upload(
        file_content=webp_bytes,
        filename="image.webp",
        session_id="demo_session_3"
    )

    print(f"Success: {result['success']}")
    print(f"Format: {result['format']}")
    print(f"File path: {result['file_path']}")

    # Demo 7: Cleanup
    print("\n" + "-" * 70)
    print("Demo 7: Cleanup sessions")
    print("-" * 70)

    for session_id in ["demo_session_1", "demo_session_2", "demo_session_3"]:
        await service.cleanup_session(session_id)
        print(f"Cleaned up: {session_id}")

    # Verify cleanup
    files = await service.get_session_files("demo_session_1")
    print(f"\nFiles remaining in demo_session_1: {len(files)}")

    print("\n" + "=" * 70)
    print("Demo completed successfully!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
