"""
Test script for API endpoints

Run with: python test_endpoints.py
Requires the backend server to be running on port 8000
"""

import requests
import json
import time
from pathlib import Path

BASE_URL = "http://localhost:8000"


def test_health_check():
    """Test health check endpoint"""
    print("\n=== Testing Health Check ===")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    assert response.status_code == 200
    print("✓ Health check passed")


def test_root_endpoint():
    """Test root endpoint"""
    print("\n=== Testing Root Endpoint ===")
    response = requests.get(f"{BASE_URL}/")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    assert response.status_code == 200
    print("✓ Root endpoint passed")


def test_generate_video():
    """Test video generation endpoint"""
    print("\n=== Testing Video Generation Endpoint ===")

    # Test with minimal data (no image)
    data = {
        "product_name": "Test Product",
        "style": "modern",
        "cta_text": "Buy Now!"
    }

    response = requests.post(f"{BASE_URL}/api/generate", data=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

    assert response.status_code == 202
    job_data = response.json()
    assert "job_id" in job_data
    assert job_data["status"] == "pending"

    print("✓ Video generation endpoint passed")
    return job_data["job_id"]


def test_generate_video_with_validation_errors():
    """Test video generation with invalid inputs"""
    print("\n=== Testing Input Validation ===")

    # Test missing required field
    data = {
        "product_name": "",
        "style": "modern",
        "cta_text": "Buy Now!"
    }

    response = requests.post(f"{BASE_URL}/api/generate", data=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

    assert response.status_code == 400
    print("✓ Validation error handling passed")


def test_job_status(job_id):
    """Test job status endpoint"""
    print(f"\n=== Testing Job Status Endpoint ===")

    response = requests.get(f"{BASE_URL}/api/jobs/{job_id}")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

    assert response.status_code == 200
    job_data = response.json()
    assert job_data["job_id"] == job_id
    assert "status" in job_data
    assert "progress" in job_data
    assert "stages" in job_data

    print("✓ Job status endpoint passed")


def test_job_status_404():
    """Test job status with invalid job ID"""
    print("\n=== Testing Job Status 404 ===")

    fake_job_id = "00000000-0000-0000-0000-000000000000"
    response = requests.get(f"{BASE_URL}/api/jobs/{fake_job_id}")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

    assert response.status_code == 404
    print("✓ Job status 404 handling passed")


def test_list_jobs():
    """Test list jobs endpoint"""
    print("\n=== Testing List Jobs Endpoint ===")

    response = requests.get(f"{BASE_URL}/api/jobs")
    print(f"Status: {response.status_code}")
    print(f"Response length: {len(response.json())}")

    assert response.status_code == 200
    assert isinstance(response.json(), list)

    print("✓ List jobs endpoint passed")


def test_websocket_health():
    """Test WebSocket health endpoint"""
    print("\n=== Testing WebSocket Health ===")

    response = requests.get(f"{BASE_URL}/ws/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

    assert response.status_code == 200
    assert "status" in response.json()

    print("✓ WebSocket health endpoint passed")


def run_all_tests():
    """Run all endpoint tests"""
    print("=" * 60)
    print("Starting API Endpoint Tests")
    print("=" * 60)

    try:
        # Basic health checks
        test_health_check()
        test_root_endpoint()
        test_websocket_health()

        # Test video generation
        job_id = test_generate_video()
        test_generate_video_with_validation_errors()

        # Small delay to let job be created
        time.sleep(0.5)

        # Test job status
        test_job_status(job_id)
        test_job_status_404()
        test_list_jobs()

        print("\n" + "=" * 60)
        print("✓ ALL TESTS PASSED!")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        return False
    except requests.exceptions.ConnectionError:
        print("\n✗ Could not connect to server. Make sure it's running on port 8000")
        print("Start server with: cd backend && python main.py")
        return False
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
