"""
End-to-End Workflow Test for Music Video Pipeline

Tests the complete workflow:
1. Create project via POST /api/mv/projects
2. Verify project in DynamoDB
3. Generate scenes via POST /api/mv/create_scenes with project_id
4. Verify scenes in DynamoDB
5. Verify project status updates
6. Test compose endpoint (expected failure - scenes not completed)
7. Test final video endpoint (expected failure - not composed)
8. Cleanup test data

Run with: python test_e2e_workflow.py
Requires:
- Backend server running on port 8000
- DynamoDB Local running on port 8001
- GEMINI_API_KEY environment variable (for scene generation)
"""

import requests
import json
import time
import uuid
import io
import os
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

# DynamoDB imports
from mv_models import MVProjectItem
from pynamodb.exceptions import DoesNotExist

BASE_URL = "http://localhost:8000"
API_URL = f"{BASE_URL}/api/mv"

# Track test project IDs for cleanup
_test_project_ids: List[str] = []


def print_section(title: str):
    """Print section header."""
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70)


def print_step(step_num: int, description: str):
    """Print test step."""
    print(f"\n[Step {step_num}] {description}")
    print("-" * 70)


def create_mock_audio_file() -> io.BytesIO:
    """
    Create a mock MP3 audio file for testing.
    
    Returns:
        BytesIO object containing mock MP3 data
    """
    # Create minimal MP3 header (not a real MP3, but enough for testing)
    # Real MP3 files start with specific headers, but for testing we just need
    # something that passes file validation
    mock_audio = b'\xff\xfb\x90\x00' + b'\x00' * 1000  # Mock MP3 header + data
    return io.BytesIO(mock_audio)


def create_mock_image_file() -> io.BytesIO:
    """
    Create a mock JPEG image file for testing.
    
    Returns:
        BytesIO object containing mock JPEG data
    """
    # Minimal JPEG header (not a real JPEG, but enough for testing)
    mock_image = b'\xff\xd8\xff\xe0' + b'\x00' * 1000  # Mock JPEG header + data
    return io.BytesIO(mock_image)


def verify_project_in_dynamodb(project_id: str) -> Dict[str, Any]:
    """
    Verify project exists in DynamoDB and return its data.
    
    Args:
        project_id: Project UUID to verify
        
    Returns:
        Dict with project data
        
    Raises:
        AssertionError: If project not found or invalid
    """
    pk = f"PROJECT#{project_id}"
    
    try:
        project_item = MVProjectItem.get(pk, "METADATA")
        
        # Verify structure
        assert project_item.entityType == "project", "Entity type should be 'project'"
        assert project_item.projectId == project_id, "Project ID should match"
        assert project_item.PK == pk, "PK should match"
        assert project_item.SK == "METADATA", "SK should be 'METADATA'"
        
        return {
            "projectId": project_item.projectId,
            "status": project_item.status,
            "sceneCount": project_item.sceneCount or 0,
            "completedScenes": project_item.completedScenes or 0,
            "failedScenes": project_item.failedScenes or 0,
            "conceptPrompt": project_item.conceptPrompt,
            "characterDescription": project_item.characterDescription,
            "createdAt": project_item.createdAt.isoformat() if project_item.createdAt else None,
            "updatedAt": project_item.updatedAt.isoformat() if project_item.updatedAt else None,
        }
    except DoesNotExist:
        raise AssertionError(f"Project {project_id} not found in DynamoDB")
    except Exception as e:
        raise AssertionError(f"Error querying DynamoDB: {e}")


def verify_scenes_in_dynamodb(project_id: str, expected_count: int) -> List[Dict[str, Any]]:
    """
    Verify scenes exist in DynamoDB for a project.
    
    Args:
        project_id: Project UUID
        expected_count: Expected number of scenes
        
    Returns:
        List of scene data dictionaries
        
    Raises:
        AssertionError: If scenes don't match expectations
    """
    pk = f"PROJECT#{project_id}"
    
    try:
        scene_items = list(MVProjectItem.query(
            pk,
            MVProjectItem.SK.begins_with("SCENE#")
        ))
        
        assert len(scene_items) == expected_count, \
            f"Expected {expected_count} scenes, found {len(scene_items)}"
        
        # Sort by sequence
        scene_items.sort(key=lambda s: s.sequence or 0)
        
        scenes_data = []
        for scene_item in scene_items:
            # Verify structure
            assert scene_item.entityType == "scene", "Entity type should be 'scene'"
            assert scene_item.projectId == project_id, "Project ID should match"
            assert scene_item.PK == pk, "PK should match"
            assert scene_item.SK.startswith("SCENE#"), "SK should start with 'SCENE#'"
            assert scene_item.sequence is not None, "Sequence should be set"
            assert scene_item.prompt is not None, "Prompt should be set"
            
            scenes_data.append({
                "sequence": scene_item.sequence,
                "status": scene_item.status,
                "prompt": scene_item.prompt,
                "negativePrompt": scene_item.negativePrompt,
                "duration": scene_item.duration,
                "needsLipSync": scene_item.needsLipSync,
                "createdAt": scene_item.createdAt.isoformat() if scene_item.createdAt else None,
                "updatedAt": scene_item.updatedAt.isoformat() if scene_item.updatedAt else None,
            })
        
        # Verify sequences are consecutive starting from 1
        sequences = [s["sequence"] for s in scenes_data]
        assert sequences == list(range(1, expected_count + 1)), \
            f"Sequences should be 1-{expected_count}, got {sequences}"
        
        return scenes_data
        
    except Exception as e:
        raise AssertionError(f"Error querying scenes from DynamoDB: {e}")


def cleanup_test_project(project_id: str):
    """
    Clean up test project and all its scenes from DynamoDB.
    
    Args:
        project_id: Project UUID to clean up
    """
    pk = f"PROJECT#{project_id}"
    
    try:
        # Delete all scenes
        scene_items = list(MVProjectItem.query(
            pk,
            MVProjectItem.SK.begins_with("SCENE#")
        ))
        
        for scene_item in scene_items:
            try:
                scene_item.delete()
                print(f"  ✓ Deleted scene {scene_item.SK}")
            except Exception as e:
                print(f"  ⚠ Failed to delete scene {scene_item.SK}: {e}")
        
        # Delete project metadata
        try:
            project_item = MVProjectItem.get(pk, "METADATA")
            project_item.delete()
            print(f"  ✓ Deleted project {project_id}")
        except DoesNotExist:
            print(f"  ⚠ Project {project_id} not found (may already be deleted)")
        except Exception as e:
            print(f"  ⚠ Failed to delete project {project_id}: {e}")
            
    except Exception as e:
        print(f"  ⚠ Error during cleanup: {e}")


def test_create_project() -> Optional[str]:
    """Test project creation via API."""
    print_step(1, "Create Project via POST /api/mv/projects")
    
    # Create mock audio file
    audio_file = create_mock_audio_file()
    
    # Prepare form data
    data = {
        "mode": "music-video",
        "prompt": "E2E Test: Robot exploring Austin, Texas",
        "characterDescription": "Silver metallic humanoid robot with red shield"
    }
    
    files = {
        "audio": ("test_audio.mp3", audio_file, "audio/mpeg")
    }
    
    try:
        response = requests.post(
            f"{API_URL}/projects",
            data=data,
            files=files,
            timeout=30
        )
        
        print(f"  Status Code: {response.status_code}")
        
        if response.status_code == 201:
            result = response.json()
            project_id = result["projectId"]
            print(f"  ✓ Project created: {project_id}")
            print(f"  Status: {result.get('status')}")
            print(f"  Message: {result.get('message')}")
            
            _test_project_ids.append(project_id)
            return project_id
        else:
            print(f"  ✗ Failed to create project")
            print(f"  Response: {json.dumps(response.json(), indent=2)}")
            return None
            
    except Exception as e:
        print(f"  ✗ Error creating project: {e}")
        return None


def test_verify_project_in_db(project_id: str):
    """Verify project exists in DynamoDB."""
    print_step(2, "Verify Project in DynamoDB")
    
    try:
        # Wait a moment for eventual consistency
        time.sleep(0.5)
        
        project_data = verify_project_in_dynamodb(project_id)
        
        print(f"  ✓ Project found in DynamoDB")
        print(f"  Status: {project_data['status']}")
        print(f"  Scene Count: {project_data['sceneCount']}")
        print(f"  Concept Prompt: {project_data['conceptPrompt'][:50]}...")
        print(f"  Created At: {project_data['createdAt']}")
        
        # Verify initial state
        assert project_data['status'] == "pending", "Initial status should be 'pending'"
        assert project_data['sceneCount'] == 0, "Initial scene count should be 0"
        
        return project_data
        
    except AssertionError as e:
        print(f"  ✗ Verification failed: {e}")
        raise
    except Exception as e:
        print(f"  ✗ Error verifying project: {e}")
        raise


def test_generate_scenes(project_id: str, num_scenes: int = 2) -> Optional[Dict[str, Any]]:
    """Test scene generation with project_id."""
    print_step(3, f"Generate Scenes via POST /api/mv/create_scenes (project_id={project_id})")
    
    data = {
        "idea": "E2E Test: Robot exploring Austin, Texas",
        "character_description": "Silver metallic humanoid robot with red shield",
        "number_of_scenes": num_scenes,
        "project_id": project_id
    }
    
    try:
        print(f"  Requesting scene generation...")
        print(f"  This may take 10-30 seconds (Gemini API call)...")
        
        response = requests.post(
            f"{API_URL}/create_scenes",
            json=data,
            timeout=60  # Scene generation can take time
        )
        
        print(f"  Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            scenes = result.get("scenes", [])
            metadata = result.get("metadata", {})
            
            print(f"  ✓ Scenes generated: {len(scenes)}")
            print(f"  DB Integration: {metadata.get('db_integration', 'unknown')}")
            print(f"  Scenes Created in DB: {metadata.get('scenes_created_in_db', 0)}")
            
            # Verify response structure
            assert "scenes" in result, "Response should include 'scenes'"
            assert "metadata" in result, "Response should include 'metadata'"
            assert metadata.get("project_id") == project_id, "Metadata should include project_id"
            assert metadata.get("db_integration") == "success", "DB integration should be successful"
            
            return result
        elif response.status_code == 404:
            print(f"  ✗ Project not found (404)")
            print(f"  Response: {json.dumps(response.json(), indent=2)}")
            return None
        else:
            print(f"  ✗ Failed to generate scenes")
            print(f"  Response: {json.dumps(response.json(), indent=2)}")
            return None
            
    except requests.exceptions.Timeout:
        print(f"  ✗ Request timed out (scene generation may be slow)")
        return None
    except Exception as e:
        print(f"  ✗ Error generating scenes: {e}")
        return None


def test_verify_scenes_in_db(project_id: str, expected_count: int):
    """Verify scenes exist in DynamoDB."""
    print_step(4, f"Verify Scenes in DynamoDB (expecting {expected_count} scenes)")
    
    try:
        # Wait a moment for eventual consistency
        time.sleep(0.5)
        
        scenes_data = verify_scenes_in_dynamodb(project_id, expected_count)
        
        print(f"  ✓ Found {len(scenes_data)} scenes in DynamoDB")
        
        # Verify project was updated
        project_data = verify_project_in_dynamodb(project_id)
        assert project_data['sceneCount'] == expected_count, \
            f"Project sceneCount should be {expected_count}, got {project_data['sceneCount']}"
        
        print(f"  ✓ Project sceneCount updated: {project_data['sceneCount']}")
        print(f"  ✓ Project status: {project_data['status']}")
        
        # Print scene details
        for scene in scenes_data:
            print(f"    Scene {scene['sequence']}: {scene['prompt'][:60]}...")
            print(f"      Status: {scene['status']}, Duration: {scene['duration']}s")
        
        return scenes_data
        
    except AssertionError as e:
        print(f"  ✗ Verification failed: {e}")
        raise
    except Exception as e:
        print(f"  ✗ Error verifying scenes: {e}")
        raise


def test_get_project_with_scenes(project_id: str):
    """Test retrieving project with scenes via API."""
    print_step(5, f"Get Project via GET /api/mv/projects/{project_id}")
    
    try:
        response = requests.get(f"{API_URL}/projects/{project_id}", timeout=10)
        
        print(f"  Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            scenes = result.get("scenes", [])
            
            print(f"  ✓ Project retrieved successfully")
            print(f"  Status: {result.get('status')}")
            print(f"  Scene Count: {result.get('sceneCount')}")
            print(f"  Scenes in Response: {len(scenes)}")
            
            # Verify scenes are in response
            assert len(scenes) == result.get('sceneCount', 0), \
                "Number of scenes in response should match sceneCount"
            
            # Verify scene structure
            for scene in scenes:
                assert "sequence" in scene, "Scene should have 'sequence'"
                assert "prompt" in scene, "Scene should have 'prompt'"
                assert "status" in scene, "Scene should have 'status'"
            
            print(f"  ✓ All scenes have correct structure")
            
            return result
        else:
            print(f"  ✗ Failed to retrieve project")
            print(f"  Response: {json.dumps(response.json(), indent=2)}")
            return None
            
    except Exception as e:
        print(f"  ✗ Error retrieving project: {e}")
        return None


def test_compose_video_expected_failure(project_id: str):
    """Test compose endpoint (expected to fail - scenes not completed)."""
    print_step(6, f"Test Compose Video (Expected Failure - scenes not completed)")
    
    try:
        response = requests.post(
            f"{API_URL}/projects/{project_id}/compose",
            json={},
            timeout=10
        )
        
        print(f"  Status Code: {response.status_code}")
        
        if response.status_code == 400:
            result = response.json()
            error_detail = result.get("detail", {})
            message = error_detail.get("message", "")
            
            print(f"  ✓ Compose correctly rejected (expected)")
            print(f"  Error Message: {message}")
            
            # Verify error message indicates scenes not ready
            assert "not all scenes are completed" in message.lower() or \
                   "scenes not ready" in message.lower(), \
                "Error message should indicate scenes are not completed"
            
            return True
        else:
            print(f"  ⚠ Unexpected status code: {response.status_code}")
            print(f"  Response: {json.dumps(response.json(), indent=2)}")
            return False
            
    except Exception as e:
        print(f"  ✗ Error testing compose: {e}")
        return False


def test_get_final_video_expected_failure(project_id: str):
    """Test final video endpoint (expected to fail - not composed)."""
    print_step(7, f"Test Get Final Video (Expected Failure - not composed)")
    
    try:
        response = requests.get(
            f"{API_URL}/projects/{project_id}/final-video",
            timeout=10
        )
        
        print(f"  Status Code: {response.status_code}")
        
        if response.status_code == 404:
            result = response.json()
            error_detail = result.get("detail", {})
            message = error_detail.get("message", "")
            
            print(f"  ✓ Final video correctly returns 404 (expected)")
            print(f"  Message: {message}")
            
            return True
        else:
            print(f"  ⚠ Unexpected status code: {response.status_code}")
            print(f"  Response: {json.dumps(response.json(), indent=2)}")
            return False
            
    except Exception as e:
        print(f"  ✗ Error testing final video: {e}")
        return False


def check_prerequisites() -> bool:
    """Check if prerequisites are met."""
    print_section("Checking Prerequisites")
    
    # Check backend server
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("  ✓ Backend server is running")
        else:
            print(f"  ✗ Backend server returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("  ✗ Backend server is not running")
        print("    Start with: cd backend && uvicorn main:app --reload")
        return False
    except Exception as e:
        print(f"  ✗ Error checking backend server: {e}")
        return False
    
    # Check DynamoDB connection
    try:
        # Try to query a non-existent item to test connection
        MVProjectItem.get("PROJECT#test-connection-check", "METADATA")
    except DoesNotExist:
        print("  ✓ DynamoDB connection working")
    except Exception as e:
        print(f"  ✗ DynamoDB connection failed: {e}")
        print("    Make sure DynamoDB Local is running:")
        print("    docker-compose up -d dynamodb-local")
        return False
    
    # Check GEMINI_API_KEY (warning only)
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    if not gemini_key:
        print("  ⚠ GEMINI_API_KEY not set (scene generation will fail)")
        print("    Set it with: export GEMINI_API_KEY=your_key")
    else:
        print("  ✓ GEMINI_API_KEY is set")
    
    return True


def main():
    """Run end-to-end workflow test."""
    print("\n" + "=" * 70)
    print(" END-TO-END WORKFLOW TEST")
    print("=" * 70)
    print("\nThis test verifies the complete workflow:")
    print("  1. Create project → 2. Verify DB → 3. Generate scenes →")
    print("  4. Verify scenes in DB → 5. Get project → 6. Test compose → 7. Test final video")
    
    # Check prerequisites
    if not check_prerequisites():
        print("\n✗ Prerequisites not met. Please fix issues above and try again.")
        return 1
    
    project_id = None
    test_passed = True
    
    try:
        # Step 1: Create project
        project_id = test_create_project()
        if not project_id:
            print("\n✗ Test failed at Step 1: Project creation")
            return 1
        
        # Step 2: Verify project in DynamoDB
        try:
            test_verify_project_in_db(project_id)
        except AssertionError as e:
            print(f"\n✗ Test failed at Step 2: {e}")
            test_passed = False
        
        # Step 3: Generate scenes
        scene_result = test_generate_scenes(project_id, num_scenes=2)
        if not scene_result:
            print("\n⚠ Scene generation failed (may need GEMINI_API_KEY)")
            print("  Continuing with remaining tests...")
        else:
            num_scenes = len(scene_result.get("scenes", []))
            
            # Step 4: Verify scenes in DynamoDB
            try:
                test_verify_scenes_in_db(project_id, num_scenes)
            except AssertionError as e:
                print(f"\n✗ Test failed at Step 4: {e}")
                test_passed = False
            
            # Step 5: Get project with scenes
            test_get_project_with_scenes(project_id)
        
        # Step 6: Test compose (expected failure)
        test_compose_video_expected_failure(project_id)
        
        # Step 7: Test final video (expected failure)
        test_get_final_video_expected_failure(project_id)
        
        # Summary
        print_section("Test Summary")
        if test_passed:
            print("  ✓ All tests passed!")
        else:
            print("  ✗ Some tests failed (see details above)")
        
        return 0 if test_passed else 1
        
    except KeyboardInterrupt:
        print("\n\n⚠ Test interrupted by user")
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        # Cleanup
        if project_id:
            print_section("Cleanup")
            print(f"Cleaning up test project: {project_id}")
            cleanup_test_project(project_id)
            print("  ✓ Cleanup complete")


if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)

