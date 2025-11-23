"""
Integration test for scene insertion and deletion flow.

Tests the complete flow of adding and deleting scenes, validating
sequence numbers and scene counts after each operation.

Run with: python backend/tests/test_scene_insertion_deletion_flow.py
Requires the backend server to be running on port 8000
"""

import requests
import json
import time
import os
from typing import List, Dict, Optional


BASE_URL = "http://localhost:8000"
API_URL = f"{BASE_URL}/api/mv"
PROJECT_ID = "91cffebd-7c1c-43a1-a515-4116b32c2a8c"

# Get API key from environment (optional - if not set, server may allow requests)
API_KEY = os.getenv("API_KEY", "")


def get_headers() -> Dict[str, str]:
    """Get request headers with API key if available."""
    headers = {}
    if API_KEY:
        headers["X-API-Key"] = API_KEY
    return headers


def get_project(project_id: str) -> Dict:
    """Fetch project data."""
    response = requests.get(f"{API_URL}/projects/{project_id}", headers=get_headers())
    if response.status_code != 200:
        raise Exception(f"Failed to get project: {response.status_code} - {response.text}")
    return response.json()


def validate_scene_sequences(project_data: Dict, expected_count: int) -> tuple[bool, str]:
    """
    Validate that scene sequence numbers are sequential starting from 1.
    
    Returns:
        (is_valid, error_message)
    """
    scenes = project_data.get("scenes", [])
    
    if len(scenes) != expected_count:
        return False, f"Expected {expected_count} scenes, got {len(scenes)}"
    
    if len(scenes) == 0:
        return True, ""
    
    # Extract sequence numbers (use displaySequence if available, fallback to sequence)
    sequences = []
    for scene in scenes:
        seq = scene.get("sequence")
        sequences.append(seq)
    
    # Check for sequential numbering starting from 1
    expected_sequences = list(range(1, len(scenes) + 1))
    if sequences != expected_sequences:
        return False, f"Sequences not sequential. Expected {expected_sequences}, got {sequences}"
    
    # Check for duplicates
    if len(sequences) != len(set(sequences)):
        return False, f"Duplicate sequence numbers found: {sequences}"
    
    return True, ""


def validate_scene_count(project_data: Dict, expected_count: int) -> tuple[bool, str]:
    """Validate that sceneCount matches actual scene count."""
    actual_count = len(project_data.get("scenes", []))
    reported_count = project_data.get("sceneCount", 0)
    
    if actual_count != expected_count:
        return False, f"Expected {expected_count} scenes, got {actual_count}"
    
    if reported_count != actual_count:
        return False, f"sceneCount ({reported_count}) doesn't match actual scene count ({actual_count})"
    
    return True, ""


def get_scene_by_display_sequence(project_data: Dict, sequence: int) -> Optional[Dict]:
    """Find scene by displaySequence (or sequence as fallback)."""
    scenes = project_data.get("scenes", [])
    for scene in scenes:
        if scene.get("sequence") == sequence:
            return scene
    return None


def print_project_state(project_data: Dict, step_name: str):
    """Print current project state for debugging."""
    scenes = project_data.get("scenes", [])
    sequences = [s.get("sequence") for s in scenes]
    scene_count = project_data.get("sceneCount", 0)
    
    print(f"\n  State: {len(scenes)} scene(s) - Sequences: {sequences}")
    print(f"  Reported sceneCount: {scene_count}")
    if len(scenes) > 0:
        print(f"  Scene details:")
        for scene in scenes:
            seq = scene.get("sequence")
            status = scene.get("status", "unknown")
            print(f"    - Scene {seq}: status={status}")


def create_scene(project_id: str, scene_concept: str) -> Dict:
    """Create a new scene."""
    response = requests.post(
        f"{API_URL}/projects/{project_id}/scenes",
        json={"sceneConcept": scene_concept},
        headers=get_headers()
    )
    if response.status_code != 201:
        raise Exception(f"Failed to create scene: {response.status_code} - {response.text}")
    return response.json()


def delete_scene(project_id: str, sequence: int) -> Dict:
    """Delete a scene by sequence number."""
    response = requests.delete(
        f"{API_URL}/projects/{project_id}/scenes/{sequence}",
        headers=get_headers()
    )
    if response.status_code != 200:
        raise Exception(f"Failed to delete scene {sequence}: {response.status_code} - {response.text}")
    return response.json()


def validate_step(project_data: Dict, expected_count: int, step_name: str) -> bool:
    """Validate project state after a step."""
    print(f"\n  Validating after {step_name}...")
    
    # Validate scene count
    count_valid, count_error = validate_scene_count(project_data, expected_count)
    if not count_valid:
        print(f"  ❌ Scene count validation failed: {count_error}")
        return False
    print(f"  ✓ Scene count validation passed: {expected_count} scenes")
    
    # Validate sequence numbers
    seq_valid, seq_error = validate_scene_sequences(project_data, expected_count)
    if not seq_valid:
        print(f"  ❌ Sequence validation failed: {seq_error}")
        return False
    print(f"  ✓ Sequence validation passed: sequential from 1")
    
    return True


def test_scene_insertion_deletion_flow():
    """Test the complete flow of scene insertion and deletion."""
    print("=" * 80)
    print("SCENE INSERTION AND DELETION FLOW TEST")
    print("=" * 80)
    print(f"\nProject ID: {PROJECT_ID}")
    print(f"API URL: {API_URL}")
    if API_KEY:
        print(f"API Key: {'*' * (len(API_KEY) - 4)}{API_KEY[-4:] if len(API_KEY) > 4 else '****'}")
    else:
        print("API Key: Not set (server may allow requests without auth)")
    print()
    
    # Verify project exists and get initial state
    try:
        print("Step 0: Verifying project exists...")
        initial_data = get_project(PROJECT_ID)
        initial_count = len(initial_data.get("scenes", []))
        print(f"  Initial state: {initial_count} scene(s)")
        print_project_state(initial_data, "Initial")
        
        if initial_count != 1:
            print(f"\n⚠️  WARNING: Expected 1 initial scene, got {initial_count}")
            print("  Continuing anyway...")
    except Exception as e:
        print(f"❌ Failed to get initial project state: {e}")
        return False
    
    all_steps_passed = True
    
    try:
        # Step 1: Create a new scene
        print("\n" + "=" * 80)
        print("STEP 1: Create a new scene")
        print("=" * 80)
        project_data = get_project(PROJECT_ID)
        print_project_state(project_data, "Before")
        
        print("\n  Creating scene...")
        create_result = create_scene(PROJECT_ID, "A dramatic opening scene")
        print(f"  ✓ Scene created with sequence: {create_result['scene']['sequence']}")
        
        # Wait a moment for scene to be saved
        time.sleep(1)
        
        project_data = get_project(PROJECT_ID)
        print_project_state(project_data, "After")
        
        if not validate_step(project_data, 2, "Step 1"):
            all_steps_passed = False
        
        # Step 2: Delete the final scene
        print("\n" + "=" * 80)
        print("STEP 2: Delete the final scene")
        print("=" * 80)
        project_data = get_project(PROJECT_ID)
        print_project_state(project_data, "Before")
        
        scenes = project_data.get("scenes", [])
        if len(scenes) == 0:
            print("  ❌ No scenes to delete")
            all_steps_passed = False
        else:
            final_scene = scenes[-1]
            final_sequence = final_scene.get("sequence")
            print(f"\n  Deleting final scene (sequence {final_sequence})...")
            delete_result = delete_scene(PROJECT_ID, final_sequence)
            print(f"  ✓ Scene {delete_result['deletedSequence']} deleted")
            print(f"  Remaining scenes: {delete_result['remainingSceneCount']}")
            
            # Wait a moment for deletion to complete
            time.sleep(1)
            
            project_data = get_project(PROJECT_ID)
            print_project_state(project_data, "After")
            
            if not validate_step(project_data, 1, "Step 2"):
                all_steps_passed = False
        
        # Step 3: Create a new scene
        print("\n" + "=" * 80)
        print("STEP 3: Create a new scene")
        print("=" * 80)
        project_data = get_project(PROJECT_ID)
        print_project_state(project_data, "Before")
        
        print("\n  Creating scene...")
        create_result = create_scene(PROJECT_ID, "A new scene after deletion")
        print(f"  ✓ Scene created with sequence: {create_result['scene']['sequence']}")
        
        time.sleep(1)
        
        project_data = get_project(PROJECT_ID)
        print_project_state(project_data, "After")
        
        if not validate_step(project_data, 2, "Step 3"):
            all_steps_passed = False
        
        # Step 4: Delete the first scene
        print("\n" + "=" * 80)
        print("STEP 4: Delete the first scene")
        print("=" * 80)
        project_data = get_project(PROJECT_ID)
        print_project_state(project_data, "Before")
        
        scenes = project_data.get("scenes", [])
        if len(scenes) == 0:
            print("  ❌ No scenes to delete")
            all_steps_passed = False
        else:
            first_scene = scenes[0]
            first_sequence = first_scene.get("sequence")
            print(f"\n  Deleting first scene (sequence {first_sequence})...")
            delete_result = delete_scene(PROJECT_ID, first_sequence)
            print(f"  ✓ Scene {delete_result['deletedSequence']} deleted")
            print(f"  Remaining scenes: {delete_result['remainingSceneCount']}")
            
            time.sleep(1)
            
            project_data = get_project(PROJECT_ID)
            print_project_state(project_data, "After")
            
            if not validate_step(project_data, 1, "Step 4"):
                all_steps_passed = False
        
        # Step 5: Create 2 new scenes
        print("\n" + "=" * 80)
        print("STEP 5: Create 2 new scenes")
        print("=" * 80)
        project_data = get_project(PROJECT_ID)
        print_project_state(project_data, "Before")
        
        print("\n  Creating first scene...")
        create_result1 = create_scene(PROJECT_ID, "First of two new scenes")
        print(f"  ✓ Scene created with sequence: {create_result1['scene']['sequence']}")
        time.sleep(1)
        
        print("\n  Creating second scene...")
        create_result2 = create_scene(PROJECT_ID, "Second of two new scenes")
        print(f"  ✓ Scene created with sequence: {create_result2['scene']['sequence']}")
        time.sleep(1)
        
        project_data = get_project(PROJECT_ID)
        print_project_state(project_data, "After")
        
        if not validate_step(project_data, 3, "Step 5"):
            all_steps_passed = False
        
        # Step 6: Delete the middle scene
        print("\n" + "=" * 80)
        print("STEP 6: Delete the middle scene")
        print("=" * 80)
        project_data = get_project(PROJECT_ID)
        print_project_state(project_data, "Before")
        
        scenes = project_data.get("scenes", [])
        if len(scenes) < 3:
            print(f"  ❌ Expected at least 3 scenes, got {len(scenes)}")
            all_steps_passed = False
        else:
            middle_scene = scenes[1]  # Second scene (index 1)
            middle_sequence = middle_scene.get("sequence")
            print(f"\n  Deleting middle scene (sequence {middle_sequence})...")
            delete_result = delete_scene(PROJECT_ID, middle_sequence)
            print(f"  ✓ Scene {delete_result['deletedSequence']} deleted")
            print(f"  Remaining scenes: {delete_result['remainingSceneCount']}")
            
            time.sleep(1)
            
            project_data = get_project(PROJECT_ID)
            print_project_state(project_data, "After")
            
            if not validate_step(project_data, 2, "Step 6"):
                all_steps_passed = False
        
        # Step 7: Create a new scene
        print("\n" + "=" * 80)
        print("STEP 7: Create a new scene")
        print("=" * 80)
        project_data = get_project(PROJECT_ID)
        print_project_state(project_data, "Before")
        
        print("\n  Creating scene...")
        create_result = create_scene(PROJECT_ID, "Final scene after middle deletion")
        print(f"  ✓ Scene created with sequence: {create_result['scene']['sequence']}")
        
        time.sleep(1)
        
        project_data = get_project(PROJECT_ID)
        print_project_state(project_data, "After")
        
        if not validate_step(project_data, 3, "Step 7"):
            all_steps_passed = False
        
        # Final summary
        print("\n" + "=" * 80)
        print("FINAL SUMMARY")
        print("=" * 80)
        final_data = get_project(PROJECT_ID)
        print_project_state(final_data, "Final")
        
        if all_steps_passed:
            print("\n✅ ALL STEPS PASSED")
            print("  All validations passed successfully!")
            return True
        else:
            print("\n❌ SOME STEPS FAILED")
            print("  Review the output above for details")
            return False
            
    except Exception as e:
        print(f"\n❌ TEST FAILED WITH EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\nStarting Scene Insertion and Deletion Flow Test...")
    print("=" * 80)
    
    success = test_scene_insertion_deletion_flow()
    
    print("\n" + "=" * 80)
    if success:
        print("TEST COMPLETED SUCCESSFULLY ✅")
        exit(0)
    else:
        print("TEST FAILED ❌")
        exit(1)

