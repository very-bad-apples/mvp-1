"""
Comprehensive tests for DynamoDB models and database layer.

Tests Phase 2: PynamoDB Model Definition
- Table initialization
- Model creation and saving
- Data retrieval (GetItem, Query)
- GSI queries
- Status updates
- Helper functions
- Error handling
"""

import pytest
import uuid
from datetime import datetime, timezone
from pynamodb.exceptions import DoesNotExist, TableError

from mv_models import (
    MVProjectItem,
    create_project_metadata,
    create_scene_item,
    StatusIndex
)
from dynamodb_config import init_dynamodb_tables
from config import settings


@pytest.fixture(scope="module", autouse=True)
def setup_dynamodb():
    """Initialize DynamoDB tables before running tests."""
    try:
        init_dynamodb_tables()
        yield
    except Exception as e:
        pytest.fail(f"Failed to initialize DynamoDB tables: {e}")


@pytest.fixture
def project_id():
    """Generate a unique project ID for each test."""
    return str(uuid.uuid4())


@pytest.fixture
def test_project(project_id):
    """Create a test project."""
    project = create_project_metadata(
        project_id=project_id,
        concept_prompt="Test project concept",
        character_description="Test character",
        product_description="Test product",
        character_image_s3_key=f"mv/projects/{project_id}/character.png",
        product_image_s3_key=f"mv/projects/{project_id}/product.jpg",
        audio_backing_track_s3_key=f"mv/projects/{project_id}/audio.mp3"
    )
    project.save()
    yield project
    # Cleanup: delete project and all scenes
    scenes_deleted = False
    project_deleted = False
    try:
        # Delete all scenes first
        for item in MVProjectItem.query(f"PROJECT#{project_id}", MVProjectItem.SK.startswith("SCENE#")):
            item.delete()
        scenes_deleted = True
        # Delete project metadata
        project.delete()
        project_deleted = True
    except DoesNotExist:
        pass  # OK if already deleted
    except Exception as e:
        # Log cleanup failures for debugging but don't fail test
        import structlog
        logger = structlog.get_logger()
        logger.warning("test_cleanup_failed", 
                      project_id=project_id, 
                      scenes_deleted=scenes_deleted,
                      project_deleted=project_deleted,
                      error=str(e))


class TestTableInitialization:
    """Test table creation and initialization."""

    def test_table_exists(self):
        """Verify table exists after initialization."""
        assert MVProjectItem.exists(), "Table should exist after initialization"

    def test_table_meta_configuration(self):
        """Verify table Meta configuration is correct."""
        assert MVProjectItem.Meta.table_name == settings.DYNAMODB_TABLE_NAME
        assert MVProjectItem.Meta.region == settings.DYNAMODB_REGION


class TestProjectCreation:
    """Test project metadata creation."""

    def test_create_project_metadata(self, project_id):
        """Test creating project metadata with helper function."""
        project = create_project_metadata(
            project_id=project_id,
            concept_prompt="Test concept",
            character_description="Test character"
        )
        
        assert project.PK == f"PROJECT#{project_id}"
        assert project.SK == "METADATA"
        assert project.entityType == "project"
        assert project.projectId == project_id
        assert project.status == "pending"
        assert project.GSI1PK == "pending"  # GSI should be set for projects
        
        # Cleanup
        try:
            project.delete()
        except Exception:
            pass

    def test_create_project_with_all_fields(self, project_id):
        """Test creating project with all optional fields."""
        project = create_project_metadata(
            project_id=project_id,
            concept_prompt="Full test concept",
            character_description="Full character",
            product_description="Full product",
            character_image_s3_key="mv/projects/test-project/character.png",
            product_image_s3_key="mv/projects/test-project/product.jpg",
            audio_backing_track_s3_key="mv/projects/test-project/audio.mp3"
        )
        
        assert project.conceptPrompt == "Full test concept"
        assert project.characterDescription == "Full character"
        assert project.productDescription == "Full product"
        assert project.characterImageS3Key == "mv/projects/test-project/character.png"
        
        # Cleanup
        try:
            project.delete()
        except Exception:
            pass

    def test_save_and_retrieve_project(self, project_id):
        """Test saving and retrieving a project."""
        project = create_project_metadata(
            project_id=project_id,
            concept_prompt="Save test",
            character_description="Save character"
        )
        project.save()
        
        # Retrieve using GetItem
        retrieved = MVProjectItem.get(f"PROJECT#{project_id}", "METADATA")
        
        assert retrieved.projectId == project_id
        assert retrieved.conceptPrompt == "Save test"
        assert retrieved.entityType == "project"
        
        # Cleanup
        try:
            project.delete()
        except Exception:
            pass


class TestSceneCreation:
    """Test scene item creation."""

    def test_create_scene_item(self, test_project, project_id):
        """Test creating a scene with helper function."""
        scene = create_scene_item(
            project_id=project_id,
            sequence=1,
            prompt="Test scene prompt",
            negative_prompt="No blur",
            duration=8.0,
            needs_lipsync=True
        )
        
        assert scene.PK == f"PROJECT#{project_id}"
        assert scene.SK == "SCENE#001"
        assert scene.entityType == "scene"
        assert scene.sequence == 1
        assert scene.prompt == "Test scene prompt"
        assert scene.duration == 8.0
        assert scene.needsLipSync is True
        assert scene.GSI1PK is None  # Scenes don't use GSI
        assert scene.GSI1SK is None

    def test_create_scene_with_reference_images(self, test_project, project_id):
        """Test creating scene with reference images."""
        scene = create_scene_item(
            project_id=project_id,
            sequence=2,
            prompt="Scene with refs",
            reference_image_s3_keys=["ref1.png", "ref2.png"]
        )
        
        assert len(scene.referenceImageS3Keys) == 2
        assert "ref1.png" in scene.referenceImageS3Keys
        assert "ref2.png" in scene.referenceImageS3Keys

    def test_save_and_retrieve_scene(self, test_project, project_id):
        """Test saving and retrieving a scene."""
        scene = create_scene_item(
            project_id=project_id,
            sequence=3,
            prompt="Retrieve test scene"
        )
        scene.save()
        
        # Retrieve using GetItem
        retrieved = MVProjectItem.get(f"PROJECT#{project_id}", "SCENE#003")
        
        assert retrieved.sequence == 3
        assert retrieved.prompt == "Retrieve test scene"
        assert retrieved.entityType == "scene"


class TestQueryOperations:
    """Test query operations."""

    def test_query_project_scenes(self, test_project, project_id):
        """Test querying all scenes for a project."""
        # Create multiple scenes
        for seq in range(1, 4):
            scene = create_scene_item(
                project_id=project_id,
                sequence=seq,
                prompt=f"Scene {seq}"
            )
            scene.save()
        
        # Query all scenes - use SK.startswith() for range key condition
        scenes = list(MVProjectItem.query(
            f"PROJECT#{project_id}",
            MVProjectItem.SK.startswith("SCENE#")
        ))
        
        assert len(scenes) >= 3
        sequences = [s.sequence for s in scenes if s.sequence]
        assert 1 in sequences
        assert 2 in sequences
        assert 3 in sequences

    def test_get_project_metadata(self, test_project, project_id):
        """Test getting project metadata."""
        metadata = MVProjectItem.get(f"PROJECT#{project_id}", "METADATA")
        
        assert metadata.entityType == "project"
        assert metadata.projectId == project_id
        assert metadata.SK == "METADATA"


class TestGSIQueries:
    """Test Global Secondary Index queries."""

    def test_query_by_status_pending(self, project_id):
        """Test querying projects by status using GSI."""
        # Create a project with pending status
        project = create_project_metadata(
            project_id=project_id,
            concept_prompt="GSI test",
            character_description="GSI character"
        )
        project.save()
        
        # Query by status using GSI
        # Use the status_index attribute on the model
        pending_projects = list(MVProjectItem.status_index.query("pending"))
        
        # Should find at least our test project
        project_ids = [p.projectId for p in pending_projects if p.entityType == "project"]
        assert project_id in project_ids
        
        # Cleanup
        try:
            project.delete()
        except Exception:
            pass

    def test_query_by_status_processing(self, project_id):
        """Test querying projects with processing status."""
        project = create_project_metadata(
            project_id=project_id,
            concept_prompt="Processing test",
            character_description="Processing character"
        )
        project.save()
        
        # Update status to processing
        project.update_status("processing")
        
        # Query by processing status
        processing_projects = list(MVProjectItem.status_index.query("processing"))
        
        project_ids = [p.projectId for p in processing_projects if p.entityType == "project"]
        assert project_id in project_ids
        
        # Cleanup
        try:
            project.delete()
        except Exception:
            pass


class TestStatusUpdates:
    """Test status update functionality."""

    def test_update_status_method(self, test_project):
        """Test the update_status helper method."""
        original_status = test_project.status
        assert original_status == "pending"
        
        # Update to processing
        test_project.update_status("processing")
        
        # Verify status changed
        retrieved = MVProjectItem.get(test_project.PK, test_project.SK)
        assert retrieved.status == "processing"
        assert retrieved.GSI1PK == "processing"  # GSI should be updated
        
        # Verify updatedAt changed
        assert retrieved.updatedAt > test_project.createdAt

    def test_update_status_to_completed(self, test_project):
        """Test updating status to completed."""
        test_project.update_status("completed")
        
        retrieved = MVProjectItem.get(test_project.PK, test_project.SK)
        assert retrieved.status == "completed"
        assert retrieved.GSI1PK == "completed"

    def test_update_status_to_failed(self, test_project):
        """Test updating status to failed."""
        test_project.update_status("failed")
        
        retrieved = MVProjectItem.get(test_project.PK, test_project.SK)
        assert retrieved.status == "failed"
        assert retrieved.GSI1PK == "failed"


class TestToDict:
    """Test to_dict() method."""

    def test_project_to_dict(self, test_project):
        """Test converting project to dictionary."""
        result = test_project.to_dict()
        
        assert result["projectId"] == test_project.projectId
        assert result["status"] == test_project.status
        assert result["entityType"] == "project"
        assert "conceptPrompt" in result
        assert "createdAt" in result
        assert "updatedAt" in result

    def test_scene_to_dict(self, test_project, project_id):
        """Test converting scene to dictionary."""
        scene = create_scene_item(
            project_id=project_id,
            sequence=5,
            prompt="Dict test scene"
        )
        scene.save()
        
        result = scene.to_dict()
        
        assert result["projectId"] == project_id
        assert result["sequence"] == 5
        assert result["entityType"] == "scene"
        assert result["prompt"] == "Dict test scene"
        assert "referenceImageS3Keys" in result


class TestErrorHandling:
    """Test error handling scenarios."""

    def test_get_nonexistent_project(self):
        """Test getting a project that doesn't exist."""
        fake_id = str(uuid.uuid4())
        with pytest.raises(DoesNotExist):
            MVProjectItem.get(f"PROJECT#{fake_id}", "METADATA")

    def test_get_nonexistent_scene(self, test_project, project_id):
        """Test getting a scene that doesn't exist."""
        with pytest.raises(DoesNotExist):
            MVProjectItem.get(f"PROJECT#{project_id}", "SCENE#999")

    def test_duplicate_project_creation(self, project_id):
        """Test that creating duplicate projects overwrites (PynamoDB behavior)."""
        project1 = create_project_metadata(
            project_id=project_id,
            concept_prompt="Duplicate test",
            character_description="Duplicate"
        )
        project1.save()
        
        # Try to create another project with same ID
        project2 = create_project_metadata(
            project_id=project_id,
            concept_prompt="Duplicate test 2",
            character_description="Duplicate 2"
        )
        
        # PynamoDB doesn't raise on duplicate - it overwrites
        project2.save()
        
        # Verify the second project overwrote the first
        retrieved = MVProjectItem.get(f"PROJECT#{project_id}", "METADATA")
        assert retrieved.conceptPrompt == "Duplicate test 2"
        
        # Cleanup
        try:
            retrieved.delete()
        except Exception:
            pass


class TestDataIntegrity:
    """Test data integrity and relationships."""

    def test_project_scene_relationship(self, test_project, project_id):
        """Test that scenes are properly linked to projects."""
        scene = create_scene_item(
            project_id=project_id,
            sequence=10,
            prompt="Relationship test"
        )
        scene.save()
        
        # Verify scene references project
        assert scene.projectId == project_id
        assert scene.PK == f"PROJECT#{project_id}"
        
        # Query scenes for project
        scenes = list(MVProjectItem.query(
            f"PROJECT#{project_id}",
            MVProjectItem.SK.startswith("SCENE#")
        ))
        
        assert len(scenes) >= 1
        assert any(s.sequence == 10 for s in scenes)

    def test_scene_count_update(self, test_project, project_id):
        """Test updating scene count on project."""
        # Create scenes
        for seq in range(1, 4):
            scene = create_scene_item(
                project_id=project_id,
                sequence=seq,
                prompt=f"Count test {seq}"
            )
            scene.save()
        
        # Update project scene count
        test_project.sceneCount = 3
        test_project.save()
        
        retrieved = MVProjectItem.get(test_project.PK, test_project.SK)
        assert retrieved.sceneCount == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

