"""
Tests for character reference image upload endpoint.

Run with: pytest test_upload_character_reference.py
Requires the backend server to be running on port 8000
"""

import requests
import json
import io
from PIL import Image


BASE_URL = "http://localhost:8000"
API_URL = f"{BASE_URL}/api/mv"


def create_test_image() -> io.BytesIO:
    """Create a simple test image in memory."""
    img = Image.new('RGB', (100, 100), color='red')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    return img_bytes


def test_upload_character_reference_success():
    """Test successful character reference image upload."""
    print("\n" + "=" * 60)
    print(" Testing Upload Character Reference - Success")
    print("=" * 60)
    
    # Create test image
    test_image = create_test_image()
    
    # Upload image
    files = {'file': ('test_image.png', test_image, 'image/png')}
    response = requests.post(
        f"{API_URL}/upload_character_reference",
        files=files
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    assert response.status_code == 200
    data = response.json()
    assert 'image_id' in data
    assert len(data['image_id']) == 36  # UUID format
    print(f"✓ Image uploaded successfully: {data['image_id']}")
    
    return data['image_id']


def test_upload_character_reference_invalid_file_type():
    """Test upload with invalid file type."""
    print("\n" + "=" * 60)
    print(" Testing Upload Character Reference - Invalid File Type")
    print("=" * 60)
    
    # Create a text file instead of image
    text_file = io.BytesIO(b"This is not an image")
    
    files = {'file': ('test.txt', text_file, 'text/plain')}
    response = requests.post(
        f"{API_URL}/upload_character_reference",
        files=files
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    assert response.status_code == 400
    print("✓ Invalid file type correctly rejected")


def test_upload_character_reference_file_too_large():
    """Test upload with file that's too large."""
    print("\n" + "=" * 60)
    print(" Testing Upload Character Reference - File Too Large")
    print("=" * 60)
    
    # Create a file larger than 10MB
    large_file = io.BytesIO(b'0' * (11 * 1024 * 1024))  # 11MB
    
    files = {'file': ('large_image.png', large_file, 'image/png')}
    response = requests.post(
        f"{API_URL}/upload_character_reference",
        files=files
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    assert response.status_code == 400
    print("✓ File too large correctly rejected")


if __name__ == "__main__":
    print("Character Reference Upload Endpoint Tests")
    print("=" * 60)
    
    try:
        # Test successful upload
        image_id = test_upload_character_reference_success()
        
        # Test invalid file type
        test_upload_character_reference_invalid_file_type()
        
        # Test file too large
        test_upload_character_reference_file_too_large()
        
        print("\n" + "=" * 60)
        print(" All tests passed! ✓")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()


