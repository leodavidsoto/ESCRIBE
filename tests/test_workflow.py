"""
Tests for workflow studio system.
"""
import pytest

from workflow.node_schema import WorkflowEngine, Workflow
from workflow.templates import (
    instantiate_template,
    list_templates,
    create_text_to_video_template,
    create_image_to_video_template,
    create_multi_scene_composition_template,
)


@pytest.fixture
def workflow_engine():
    """Fixture for WorkflowEngine."""
    return WorkflowEngine()


class TestWorkflowEngine:
    """Test suite for WorkflowEngine."""

    def test_engine_initialization(self, workflow_engine):
        """Test engine initializes with core nodes."""
        assert len(workflow_engine.node_definitions) >= 7
        assert "flux_t2i" in workflow_engine.node_definitions
        assert "text_to_video" in workflow_engine.node_definitions

    def test_list_node_types(self, workflow_engine):
        """Test listing all node types."""
        nodes = workflow_engine.list_node_types()
        assert len(nodes) >= 7
        assert all("id" in n for n in nodes)
        assert all("name" in n for n in nodes)
        assert all("inputs" in n for n in nodes)
        assert all("outputs" in n for n in nodes)

    def test_create_workflow(self, workflow_engine):
        """Test creating a new workflow."""
        workflow = workflow_engine.create_workflow(
            name="Test Workflow",
            description="A test workflow",
        )
        assert workflow.name == "Test Workflow"
        assert workflow.description == "A test workflow"
        assert workflow.id.startswith("workflow_")
        assert len(workflow.nodes) == 0
        assert len(workflow.connections) == 0

    def test_add_node_success(self, workflow_engine):
        """Test adding a node to workflow."""
        workflow = workflow_engine.create_workflow("Test")
        node_id = workflow_engine.add_node(
            workflow,
            "flux_t2i",
            config={"model": "flux-pro"},
            position=(100, 100),
        )
        assert node_id is not None
        assert node_id in workflow.nodes
        assert workflow.nodes[node_id].definition_id == "flux_t2i"

    def test_add_node_failure(self, workflow_engine):
        """Test adding unknown node fails gracefully."""
        workflow = workflow_engine.create_workflow("Test")
        node_id = workflow_engine.add_node(workflow, "nonexistent_node")
        assert node_id is None
        assert len(workflow.nodes) == 0

    def test_add_multiple_nodes(self, workflow_engine):
        """Test adding multiple nodes."""
        workflow = workflow_engine.create_workflow("Test")
        node1 = workflow_engine.add_node(workflow, "flux_t2i", position=(50, 50))
        node2 = workflow_engine.add_node(workflow, "color_grade", position=(250, 50))
        node3 = workflow_engine.add_node(workflow, "apply_effects", position=(450, 50))

        assert len(workflow.nodes) == 3
        assert node1 in workflow.nodes
        assert node2 in workflow.nodes
        assert node3 in workflow.nodes

    def test_connect_nodes_success(self, workflow_engine):
        """Test connecting two nodes."""
        workflow = workflow_engine.create_workflow("Test")
        node1 = workflow_engine.add_node(workflow, "flux_t2i", position=(50, 50))
        node2 = workflow_engine.add_node(workflow, "color_grade", position=(250, 50))

        connected = workflow_engine.connect_nodes(
            workflow, node1, "image", node2, "input"
        )
        assert connected is True
        assert len(workflow.connections) == 1
        assert workflow.connections[0].from_node == node1
        assert workflow.connections[0].from_port == "image"

    def test_connect_nodes_failure(self, workflow_engine):
        """Test connecting nonexistent nodes fails gracefully."""
        workflow = workflow_engine.create_workflow("Test")
        connected = workflow_engine.connect_nodes(
            workflow, "nonexistent1", "out", "nonexistent2", "in"
        )
        assert connected is False
        assert len(workflow.connections) == 0

    def test_validate_workflow_empty(self, workflow_engine):
        """Test validation of empty workflow."""
        workflow = workflow_engine.create_workflow("Test")
        is_valid, errors = workflow_engine.validate_workflow(workflow)
        assert is_valid is False
        assert len(errors) > 0

    def test_validate_workflow_valid(self, workflow_engine):
        """Test validation of valid workflow."""
        workflow = workflow_engine.create_workflow("Test")
        node1 = workflow_engine.add_node(workflow, "flux_t2i")
        node2 = workflow_engine.add_node(workflow, "color_grade")
        workflow_engine.connect_nodes(workflow, node1, "image", node2, "input")

        is_valid, errors = workflow_engine.validate_workflow(workflow)
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_workflow_broken_connection(self, workflow_engine):
        """Test validation detects broken connections."""
        workflow = workflow_engine.create_workflow("Test")
        node1 = workflow_engine.add_node(workflow, "flux_t2i")
        workflow_engine.connect_nodes(workflow, node1, "out", "nonexistent", "in")

        is_valid, errors = workflow_engine.validate_workflow(workflow)
        assert is_valid is False
        assert any("unknown node" in e for e in errors)


class TestWorkflowTemplates:
    """Test suite for workflow templates."""

    def test_list_templates(self):
        """Test listing available templates."""
        templates = list_templates()
        assert len(templates) >= 4
        assert all("id" in t for t in templates)
        assert all("name" in t for t in templates)

    def test_text_to_video_template(self, workflow_engine):
        """Test text-to-video template creation."""
        workflow = create_text_to_video_template(workflow_engine)
        assert workflow.name == "Text-to-Video Production"
        assert len(workflow.nodes) >= 3
        assert len(workflow.connections) >= 2

    def test_image_to_video_template(self, workflow_engine):
        """Test image-to-video template creation."""
        workflow = create_image_to_video_template(workflow_engine)
        assert workflow.name == "Image-to-Video Production"
        assert len(workflow.nodes) >= 4
        assert len(workflow.connections) >= 3

    def test_multi_scene_composition_template(self, workflow_engine):
        """Test multi-scene composition template."""
        workflow = create_multi_scene_composition_template(workflow_engine)
        assert workflow.name == "Multi-Scene Composition"
        assert len(workflow.nodes) >= 6

    def test_instantiate_template_text_to_video(self, workflow_engine):
        """Test instantiating text-to-video template."""
        workflow = instantiate_template(workflow_engine, "text_to_video")
        assert workflow is not None
        assert len(workflow.nodes) >= 3

    def test_instantiate_template_image_to_video(self, workflow_engine):
        """Test instantiating image-to-video template."""
        workflow = instantiate_template(workflow_engine, "image_to_video")
        assert workflow is not None
        assert len(workflow.nodes) >= 4

    def test_instantiate_template_multi_scene(self, workflow_engine):
        """Test instantiating multi-scene template."""
        workflow = instantiate_template(workflow_engine, "multi_scene_composition")
        assert workflow is not None
        assert len(workflow.nodes) >= 6

    def test_instantiate_invalid_template(self, workflow_engine):
        """Test that invalid template raises error."""
        with pytest.raises(ValueError, match="Unknown template"):
            instantiate_template(workflow_engine, "nonexistent_template")

    def test_template_node_configuration(self, workflow_engine):
        """Test that template nodes have proper configuration."""
        workflow = create_text_to_video_template(workflow_engine)
        for node_id, node in workflow.nodes.items():
            assert node.definition_id is not None
            assert node.config is not None
            # Check that config has expected keys for the node type
            if node.definition_id == "text_to_video":
                assert "model" in node.config or "duration" in node.config

    def test_template_workflow_validation(self, workflow_engine):
        """Test that template workflows are valid."""
        templates_to_test = [
            "text_to_video",
            "image_to_video",
            "multi_scene_composition",
        ]

        for template_id in templates_to_test:
            workflow = instantiate_template(workflow_engine, template_id)
            is_valid, errors = workflow_engine.validate_workflow(workflow)
            assert is_valid is True, f"Template {template_id} validation failed: {errors}"
