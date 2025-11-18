"""
Test script for Music Video API endpoints.

Tests all CRUD operations for MV projects.

Run with: python test_mv_endpoints.py
Requires the backend server to be running on port 8000
"""

import requests
import json
import time
from pathlib import Path

BASE_URL = "http://localhost:8000"
API_URL = f"{BASE_URL}/api/mv"


def print_section(title):
    """Print section header."""
    print("\n" + "=" * 60)
    print(f" {title}")
    print("=" * 60)


def test_health_check():
    """Test health endpoint."""
    print_section("Testing Health Check")

    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

    assert response.status_code == 200
    print("✓ Health check passed")


def test_create_project():
    """Test project creation."""
    print_section("Testing Create Project")

    # Prepare test data
    data = {
        "mode": "music-video",
        "prompt": "A robot exploring Austin, Texas",
        "characterDescription": "Silver metallic humanoid robot with red shield"
    }

    # Note: In real test, would upload actual files
    # For this test, we'll use FormData without files (will fail validation)
    # This tests the validation logic
    response = requests.post(
        f"{API_URL}/projects",
        data=data
    )

    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

    # Should fail validation (missing audio file for music-video mode)
    if response.status_code == 400:
        print("✓ Validation correctly rejected missing audio file")
        return None

    assert response.status_code == 201
    project_id = response.json()["projectId"]
    print(f"✓ Project created: {project_id}")

    return project_id


def test_get_project(project_id):
    """Test project retrieval."""
    if not project_id:
        print("Skipping - no project ID available")
        return None

    print_section(f"Testing Get Project: {project_id}")

    response = requests.get(f"{API_URL}/projects/{project_id}")

    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        data = response.json()
        assert data["projectId"] == project_id
        print(f"✓ Project retrieved successfully")
        return data
    else:
        print(f"Response: {response.text}")
        print(f"✗ Failed to retrieve project")
        return None


def test_get_project_not_found():
    """Test project retrieval with invalid ID."""
    print_section("Testing Get Project (Not Found)")

    fake_id = "00000000-0000-0000-0000-000000000000"
    response = requests.get(f"{API_URL}/projects/{fake_id}")

    print(f"Status: {response.status_code}")
    assert response.status_code == 404
    print("✓ 404 error correctly returned for non-existent project")


def test_update_project(project_id):
    """Test project update."""
    if not project_id:
        print("Skipping - no project ID available")
        return

    print_section(f"Testing Update Project: {project_id}")

    update_data = {
        "status": "processing"
    }

    response = requests.patch(
        f"{API_URL}/projects/{project_id}",
        json=update_data
    )

    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        data = response.json()
        assert data["status"] == "processing"
        print(f"✓ Project updated successfully")
    else:
        print(f"Response: {response.text}")
        print(f"✗ Failed to update project")


def test_compose_video(project_id):
    """Test video composition (should fail if scenes not complete)."""
    if not project_id:
        print("Skipping - no project ID available")
        return

    print_section(f"Testing Compose Video: {project_id}")

    response = requests.post(f"{API_URL}/projects/{project_id}/compose")

    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

    # Should fail with 400 if scenes not completed
    if response.status_code == 400:
        print("✓ Compose correctly rejected (scenes not ready)")
    elif response.status_code == 200:
        print("✓ Compose job queued")
    else:
        print(f"✗ Unexpected status code: {response.status_code}")


def test_get_final_video(project_id):
    """Test final video retrieval."""
    if not project_id:
        print("Skipping - no project ID available")
        return

    print_section(f"Testing Get Final Video: {project_id}")

    response = requests.get(f"{API_URL}/projects/{project_id}/final-video")

    print(f"Status: {response.status_code}")

    # Should return 404 if not yet composed
    if response.status_code == 404:
        print("✓ Final video not yet available (expected)")
    elif response.status_code == 200:
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        print("✓ Final video URL retrieved")
    else:
        print(f"Response: {response.text}")
        print(f"✗ Unexpected status code: {response.status_code}")


def test_create_project_validation():
    """Test project creation with invalid data."""
    print_section("Testing Create Project Validation")

    # Test invalid mode
    data = {
        "mode": "invalid-mode",
        "prompt": "Test prompt",
        "characterDescription": "Test character"
    }

    response = requests.post(
        f"{API_URL}/projects",
        data=data
    )

    print(f"Status: {response.status_code}")
    assert response.status_code == 400
    print("✓ Invalid mode correctly rejected")

    # Test missing required fields
    data = {
        "mode": "music-video"
        # Missing prompt and characterDescription
    }

    response = requests.post(
        f"{API_URL}/projects",
        data=data
    )

    print(f"Status: {response.status_code}")
    assert response.status_code == 422  # FastAPI validation error
    print("✓ Missing required fields correctly rejected")


def test_create_scenes_without_project_id():
    """Test scene creation without project_id (backward compatible)."""
    print_section("Testing Create Scenes (without project_id)")

    data = {
        "idea": "Test video concept",
        "character_description": "Test character",
        "number_of_scenes": 2
    }

    response = requests.post(
        f"{API_URL}/create_scenes",
        json=data
    )

    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"Scenes generated: {len(result.get('scenes', []))}")
        assert "scenes" in result
        assert "output_files" in result
        assert "metadata" in result
        assert "project_id" not in result["metadata"]  # Should not have project_id
        print("✓ Scene creation without project_id works (backward compatible)")
        return result
    else:
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        # May fail if Gemini API key not configured - that's OK for this test
        print("⚠ Scene creation failed (may need GEMINI_API_KEY)")
        return None


def test_create_scenes_with_project_id(project_id: str):
    """Test scene creation with project_id (database integration)."""
    print_section(f"Testing Create Scenes (with project_id: {project_id})")

    data = {
        "idea": "A robot exploring Austin, Texas",
        "character_description": "Silver metallic humanoid robot with red shield",
        "number_of_scenes": 2,
        "project_id": project_id
    }

    response = requests.post(
        f"{API_URL}/create_scenes",
        json=data
    )

    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"Scenes generated: {len(result.get('scenes', []))}")
        assert "scenes" in result
        assert "metadata" in result
        assert result["metadata"].get("project_id") == project_id
        assert "scenes_created_in_db" in result["metadata"]
        assert "db_integration" in result["metadata"]
        print(f"✓ Scenes created in DB: {result['metadata'].get('scenes_created_in_db')}")
        print(f"✓ DB Integration status: {result['metadata'].get('db_integration')}")
        return result
    elif response.status_code == 404:
        print("⚠ Project not found (may need to create project first)")
        return None
    else:
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        # May fail if Gemini API key not configured - that's OK for this test
        print("⚠ Scene creation failed (may need GEMINI_API_KEY)")
        return None


def test_create_scenes_invalid_project_id():
    """Test scene creation with invalid project_id format."""
    print_section("Testing Create Scenes (invalid project_id)")

    data = {
        "idea": "Test video concept",
        "character_description": "Test character",
        "project_id": "invalid-uuid-format"
    }

    response = requests.post(
        f"{API_URL}/create_scenes",
        json=data
    )

    print(f"Status: {response.status_code}")
    assert response.status_code == 400  # Should return validation error
    result = response.json()
    assert "error" in result.get("detail", {})
    print("✓ Invalid project_id format correctly rejected")


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print(" MV API ENDPOINT TESTS")
    print("=" * 60)

    try:
        # Test health
        test_health_check()

        # Test validation
        test_create_project_validation()

        # Test scene creation without project_id (backward compatibility)
        test_create_scenes_without_project_id()

        # Test invalid project_id format
        test_create_scenes_invalid_project_id()

        # Test project creation (will fail without files, but tests validation)
        project_id = test_create_project()

        # Test not found
        test_get_project_not_found()

        if project_id:
            # Wait briefly for database write
            time.sleep(0.5)

            # Test project retrieval
            test_get_project(project_id)

            # Test project update
            test_update_project(project_id)

            # Test compose (should fail - no scenes)
            test_compose_video(project_id)

            # Test final video (should return 404)
            test_get_final_video(project_id)

            # Test scene creation with project_id (database integration)
            # Note: This may fail if GEMINI_API_KEY is not configured
            test_create_scenes_with_project_id(project_id)

        print("\n" + "=" * 60)
        print(" ALL TESTS COMPLETED")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        raise
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        raise


if __name__ == "__main__":
    main()

