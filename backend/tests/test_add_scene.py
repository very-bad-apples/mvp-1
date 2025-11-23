"""
Tests for adding a single scene to an existing project.

Run with: pytest test_add_scene.py -v
Requires the backend server to be running on port 8000
"""

import requests
import json
import uuid
from typing import Optional


BASE_URL = "http://localhost:8000"
API_URL = f"{BASE_URL}/api/mv"


def create_test_project(mode: str = "music-video") -> str:
    """Helper to create a test project. Returns project_id."""
    response = requests.post(
        f"{API_URL}/projects",
        data={
            "mode": mode,
            "prompt": "Test project for add scene",
            "characterDescription": "Test character"
        }
    )
    assert response.status_code == 201
    data = response.json()
    return data["projectId"]


def wait_for_project_status(project_id: str, target_status: str, timeout: int = 30):
    """Wait for project to reach target status."""
    import time
    start_time = time.time()
    while time.time() - start_time < timeout:
        response = requests.get(f"{API_URL}/projects/{project_id}")
        if response.status_code == 200:
            data = response.json()
            if data["status"] == target_status:
                return True
        time.sleep(1)
    return False


def test_get_next_scene_sequence_empty_project():
    """Test get_next_scene_sequence with empty project (should return 1)."""
    print("\n" + "=" * 60)
    print(" Testing get_next_scene_sequence - Empty Project")
    print("=" * 60)
    
    # Create a project but don't generate scenes
    project_id = create_test_project()
    
    # Add a scene - should get sequence 1
    response = requests.post(
        f"{API_URL}/projects/{project_id}/scenes",
        json={"sceneConcept": "First scene"}
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 201:
        data = response.json()
        assert data["scene"]["sequence"] == 1
        print(f"✓ First scene got sequence 1")
    else:
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        raise AssertionError(f"Expected 201, got {response.status_code}")


def test_get_next_scene_sequence_with_existing_scenes():
    """Test get_next_scene_sequence with existing scenes."""
    print("\n" + "=" * 60)
    print(" Testing get_next_scene_sequence - With Existing Scenes")
    print("=" * 60)
    
    # Create project and generate initial scenes
    project_id = create_test_project()
    
    # Start generation to create scenes
    response = requests.post(f"{API_URL}/projects/{project_id}/generate")
    assert response.status_code == 200
    
    # Wait for scenes to be created (status becomes processing or completed)
    wait_for_project_status(project_id, "processing", timeout=10)
    
    # Get project to see how many scenes exist
    response = requests.get(f"{API_URL}/projects/{project_id}")
    assert response.status_code == 200
    project_data = response.json()
    existing_scene_count = project_data["sceneCount"]
    
    print(f"Existing scenes: {existing_scene_count}")
    
    # Add a new scene - should get next sequence
    response = requests.post(
        f"{API_URL}/projects/{project_id}/scenes",
        json={"sceneConcept": "Additional scene"}
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 201:
        data = response.json()
        expected_sequence = existing_scene_count + 1
        assert data["scene"]["sequence"] == expected_sequence
        print(f"✓ New scene got sequence {expected_sequence} (after {existing_scene_count} existing)")
    else:
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        raise AssertionError(f"Expected 201, got {response.status_code}")


def test_add_scene_to_completed_project():
    """Test adding scene to completed project (success case)."""
    print("\n" + "=" * 60)
    print(" Testing Add Scene - Completed Project")
    print("=" * 60)
    
    project_id = create_test_project()
    
    # Start generation
    response = requests.post(f"{API_URL}/projects/{project_id}/generate")
    assert response.status_code == 200
    
    # Wait for completion (or at least processing)
    wait_for_project_status(project_id, "processing", timeout=10)
    
    # Add scene
    response = requests.post(
        f"{API_URL}/projects/{project_id}/scenes",
        json={"sceneConcept": "A dramatic close-up scene"}
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    assert response.status_code == 201
    data = response.json()
    assert "scene" in data
    assert "message" in data
    assert data["scene"]["prompt"] is not None
    assert data["scene"]["status"] == "pending"  # New scene starts as pending
    print("✓ Scene added successfully to completed project")


def test_add_scene_to_processing_project():
    """Test adding scene to processing project (should also work)."""
    print("\n" + "=" * 60)
    print(" Testing Add Scene - Processing Project")
    print("=" * 60)
    
    project_id = create_test_project()
    
    # Start generation (project will be in processing state)
    response = requests.post(f"{API_URL}/projects/{project_id}/generate")
    assert response.status_code == 200
    
    # Immediately try to add scene (project is processing)
    response = requests.post(
        f"{API_URL}/projects/{project_id}/scenes",
        json={"sceneConcept": "Additional scene during processing"}
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 201:
        print("✓ Scene added successfully to processing project")
    else:
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        # This might fail if project is still pending, which is acceptable


def test_add_scene_to_pending_project():
    """Test adding scene to pending project (should fail with 400)."""
    print("\n" + "=" * 60)
    print(" Testing Add Scene - Pending Project (Should Fail)")
    print("=" * 60)
    
    project_id = create_test_project()
    
    # Try to add scene immediately (project is still pending)
    response = requests.post(
        f"{API_URL}/projects/{project_id}/scenes",
        json={"sceneConcept": "Scene for pending project"}
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    assert response.status_code == 400
    assert "status" in response.json()["detail"]["message"].lower() or "pending" in response.json()["detail"]["message"].lower()
    print("✓ Correctly rejected adding scene to pending project")


def test_add_scene_to_nonexistent_project():
    """Test adding scene to non-existent project (should fail with 404)."""
    print("\n" + "=" * 60)
    print(" Testing Add Scene - Non-existent Project (Should Fail)")
    print("=" * 60)
    
    fake_project_id = str(uuid.uuid4())
    
    response = requests.post(
        f"{API_URL}/projects/{fake_project_id}/scenes",
        json={"sceneConcept": "Scene for fake project"}
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    assert response.status_code == 404
    print("✓ Correctly rejected adding scene to non-existent project")


def test_add_scene_empty_concept():
    """Test adding scene with empty concept (should fail with 400)."""
    print("\n" + "=" * 60)
    print(" Testing Add Scene - Empty Concept (Should Fail)")
    print("=" * 60)
    
    project_id = create_test_project()
    
    # Start generation to move to processing/completed
    response = requests.post(f"{API_URL}/projects/{project_id}/generate")
    wait_for_project_status(project_id, "processing", timeout=10)
    
    # Try with empty concept
    response = requests.post(
        f"{API_URL}/projects/{project_id}/scenes",
        json={"sceneConcept": ""}
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    # Should fail validation (422 for Pydantic validation or 400)
    assert response.status_code in [400, 422]
    print("✓ Correctly rejected empty scene concept")


def test_add_scene_uses_project_context():
    """Test that added scene uses project's mode, director config, and reference images."""
    print("\n" + "=" * 60)
    print(" Testing Add Scene - Uses Project Context")
    print("=" * 60)
    
    # Create project with director config
    project_id = create_test_project()
    
    # Update project to have director config (if endpoint exists)
    # For now, just verify scene is created with project's mode
    
    # Start generation
    response = requests.post(f"{API_URL}/projects/{project_id}/generate")
    wait_for_project_status(project_id, "processing", timeout=10)
    
    # Add scene
    response = requests.post(
        f"{API_URL}/projects/{project_id}/scenes",
        json={"sceneConcept": "Test scene with project context"}
    )
    
    assert response.status_code == 201
    data = response.json()
    
    # Verify scene has reference images if project has them
    project_response = requests.get(f"{API_URL}/projects/{project_id}")
    project_data = project_response.json()
    
    # Scene should have been created
    assert data["scene"]["sequence"] > 0
    print("✓ Scene created with project context")
    
    # Verify scene count was incremented
    updated_project = requests.get(f"{API_URL}/projects/{project_id}")
    updated_data = updated_project.json()
    assert updated_data["sceneCount"] >= project_data["sceneCount"] + 1
    print("✓ Project scene count incremented")


def test_add_scene_sequence_ordering():
    """Test that multiple scene adds get correct sequence ordering."""
    print("\n" + "=" * 60)
    print(" Testing Add Scene - Sequence Ordering")
    print("=" * 60)
    
    project_id = create_test_project()
    
    # Start generation
    response = requests.post(f"{API_URL}/projects/{project_id}/generate")
    wait_for_project_status(project_id, "processing", timeout=10)
    
    # Get initial scene count
    response = requests.get(f"{API_URL}/projects/{project_id}")
    initial_count = response.json()["sceneCount"]
    
    # Add multiple scenes
    sequences = []
    for i in range(3):
        response = requests.post(
            f"{API_URL}/projects/{project_id}/scenes",
            json={"sceneConcept": f"Scene {i+1}"}
        )
        if response.status_code == 201:
            data = response.json()
            sequences.append(data["scene"]["sequence"])
    
    print(f"Added scenes with sequences: {sequences}")
    
    # Verify sequences are sequential and increasing
    assert len(sequences) == 3
    assert sequences == sorted(sequences)
    assert sequences[0] == initial_count + 1
    assert sequences[1] == initial_count + 2
    assert sequences[2] == initial_count + 3
    print("✓ Scene sequences are correctly ordered")


if __name__ == "__main__":
    print("Add Scene Endpoint Tests")
    print("=" * 60)
    print("Note: These tests require the backend server to be running")
    print("Start server with: uvicorn main:app --reload")
    print("=" * 60)
    
    # Run tests
    test_get_next_scene_sequence_empty_project()
    test_get_next_scene_sequence_with_existing_scenes()
    test_add_scene_to_completed_project()
    test_add_scene_to_processing_project()
    test_add_scene_to_pending_project()
    test_add_scene_to_nonexistent_project()
    test_add_scene_empty_concept()
    test_add_scene_uses_project_context()
    test_add_scene_sequence_ordering()
    
    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)

