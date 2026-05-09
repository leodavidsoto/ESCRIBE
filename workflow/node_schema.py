"""
Workflow node schema system for visual pipeline editor.

Defines node types, inputs, outputs, and execution contracts.
"""
import logging
from dataclasses import dataclass, field
from typing import Any, Literal, Optional

log = logging.getLogger("workflow_nodes")


@dataclass
class NodePort:
    """Input or output port on a workflow node."""
    name: str
    type: Literal["string", "number", "image", "video", "boolean", "object"]
    required: bool = True
    description: str = ""


@dataclass
class NodeDefinition:
    """Definition of a workflow node type."""
    id: str  # Unique node type ID (e.g., "flux_t2i", "color_grade")
    name: str  # Display name
    category: str  # Category (e.g., "generation", "enhancement", "composition")
    description: str
    inputs: list[NodePort] = field(default_factory=list)
    outputs: list[NodePort] = field(default_factory=list)
    config: dict = field(default_factory=dict)  # Default configuration


@dataclass
class WorkflowNode:
    """Instance of a node in a workflow graph."""
    id: str  # Unique ID in this workflow (e.g., "node_1")
    definition_id: str  # Reference to NodeDefinition.id
    position: tuple[int, int] = (0, 0)  # x, y position for UI
    config: dict = field(default_factory=dict)  # Node-specific configuration
    inputs: dict = field(default_factory=dict)  # Input connections: {port_name: upstream_node_id}


@dataclass
class WorkflowConnection:
    """Connection between two nodes."""
    from_node: str  # Node ID
    from_port: str  # Output port name
    to_node: str  # Node ID
    to_port: str  # Input port name


@dataclass
class Workflow:
    """Complete workflow graph."""
    id: str
    name: str
    description: str = ""
    nodes: dict[str, WorkflowNode] = field(default_factory=dict)  # id -> node
    connections: list[WorkflowConnection] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


# Predefined node definitions
CORE_NODES = {
    "flux_t2i": NodeDefinition(
        id="flux_t2i",
        name="Flux Text-to-Image",
        category="generation",
        description="Generate image from text prompt using Flux",
        inputs=[
            NodePort("prompt", "string", required=True, description="Image description"),
            NodePort("model", "string", required=False, description="Model variant (flux-pro, flux-standard)"),
            NodePort("width", "number", required=False, description="Image width in pixels"),
            NodePort("height", "number", required=False, description="Image height in pixels"),
        ],
        outputs=[
            NodePort("image", "image", description="Generated image"),
            NodePort("metadata", "object", description="Generation metadata"),
        ],
    ),

    "color_grade": NodeDefinition(
        id="color_grade",
        name="Color Grading",
        category="enhancement",
        description="Apply color grading profile to video or image",
        inputs=[
            NodePort("input", "video", required=True, description="Input video or image"),
            NodePort("profile", "string", required=True, description="Grading profile name"),
            NodePort("intensity", "number", required=False, description="Effect intensity (0.0-2.0)"),
        ],
        outputs=[
            NodePort("output", "video", description="Color-graded video"),
        ],
    ),

    "apply_effects": NodeDefinition(
        id="apply_effects",
        name="Apply Effects",
        category="enhancement",
        description="Chain visual effects onto video",
        inputs=[
            NodePort("input", "video", required=True, description="Input video"),
            NodePort("effects", "object", required=True, description="Effects array"),
        ],
        outputs=[
            NodePort("output", "video", description="Video with effects applied"),
        ],
    ),

    "text_to_video": NodeDefinition(
        id="text_to_video",
        name="Text-to-Video",
        category="generation",
        description="Generate video from text prompt",
        inputs=[
            NodePort("prompt", "string", required=True, description="Video description"),
            NodePort("model", "string", required=False, description="Model (sora, kling, veo)"),
            NodePort("duration", "number", required=False, description="Duration in seconds"),
            NodePort("resolution", "string", required=False, description="Output resolution (720p, 1080p, 4k)"),
        ],
        outputs=[
            NodePort("video", "video", description="Generated video"),
        ],
    ),

    "image_to_video": NodeDefinition(
        id="image_to_video",
        name="Image-to-Video",
        category="generation",
        description="Animate image into video",
        inputs=[
            NodePort("image", "image", required=True, description="Input image"),
            NodePort("prompt", "string", required=False, description="Animation direction (optional)"),
            NodePort("model", "string", required=False, description="Model (runway-i2v, veo-i2v)"),
            NodePort("duration", "number", required=False, description="Duration in seconds"),
        ],
        outputs=[
            NodePort("video", "video", description="Generated video"),
        ],
    ),

    "concatenate": NodeDefinition(
        id="concatenate",
        name="Concatenate Videos",
        category="composition",
        description="Join multiple videos together",
        inputs=[
            NodePort("clips", "object", required=True, description="Array of video clips"),
            NodePort("transitions", "object", required=False, description="Transition specs"),
        ],
        outputs=[
            NodePort("output", "video", description="Concatenated video"),
        ],
    ),

    "adjust_lighting": NodeDefinition(
        id="adjust_lighting",
        name="Adjust Lighting",
        category="enhancement",
        description="Adjust brightness, contrast, and exposure",
        inputs=[
            NodePort("input", "video", required=True, description="Input video"),
            NodePort("brightness", "number", required=False, description="Brightness adjustment"),
            NodePort("contrast", "number", required=False, description="Contrast adjustment"),
            NodePort("exposure", "number", required=False, description="Exposure adjustment"),
        ],
        outputs=[
            NodePort("output", "video", description="Adjusted video"),
        ],
    ),
}


class WorkflowEngine:
    """Manages workflow definitions and execution."""

    def __init__(self):
        """Initialize workflow engine."""
        self.node_definitions = CORE_NODES
        log.info("workflow_engine_ready", extra={"nodes": len(self.node_definitions)})

    def create_workflow(
        self,
        name: str,
        description: str = "",
    ) -> Workflow:
        """Create a new empty workflow.

        Args:
            name: Workflow name
            description: Workflow description

        Returns:
            New Workflow instance
        """
        import uuid
        workflow = Workflow(
            id=f"workflow_{uuid.uuid4().hex[:8]}",
            name=name,
            description=description,
        )
        log.info("workflow_created", extra={"workflow_id": workflow.id, "name": name})
        return workflow

    def add_node(
        self,
        workflow: Workflow,
        definition_id: str,
        config: dict = None,
        position: tuple[int, int] = (0, 0),
    ) -> Optional[str]:
        """Add node to workflow.

        Args:
            workflow: Workflow to add to
            definition_id: Node definition ID
            config: Node configuration
            position: Position in UI (x, y)

        Returns:
            Node ID or None if definition not found
        """
        if definition_id not in self.node_definitions:
            log.warning(f"Unknown node definition: {definition_id}")
            return None

        import uuid
        node_id = f"node_{uuid.uuid4().hex[:8]}"
        node = WorkflowNode(
            id=node_id,
            definition_id=definition_id,
            position=position,
            config=config or {},
        )
        workflow.nodes[node_id] = node
        log.info("node_added", extra={"workflow_id": workflow.id, "node_id": node_id})
        return node_id

    def connect_nodes(
        self,
        workflow: Workflow,
        from_node: str,
        from_port: str,
        to_node: str,
        to_port: str,
    ) -> bool:
        """Connect two nodes.

        Args:
            workflow: Workflow
            from_node: Source node ID
            from_port: Source output port name
            to_node: Destination node ID
            to_port: Destination input port name

        Returns:
            True if connection created, False if invalid
        """
        if from_node not in workflow.nodes or to_node not in workflow.nodes:
            log.warning(f"Node not found in workflow")
            return False

        connection = WorkflowConnection(
            from_node=from_node,
            from_port=from_port,
            to_node=to_node,
            to_port=to_port,
        )
        workflow.connections.append(connection)
        log.info(
            "nodes_connected",
            extra={
                "workflow_id": workflow.id,
                "from": f"{from_node}.{from_port}",
                "to": f"{to_node}.{to_port}",
            },
        )
        return True

    def list_node_types(self) -> list[dict]:
        """List all available node types."""
        return [
            {
                "id": definition.id,
                "name": definition.name,
                "category": definition.category,
                "description": definition.description,
                "inputs": [
                    {
                        "name": port.name,
                        "type": port.type,
                        "required": port.required,
                        "description": port.description,
                    }
                    for port in definition.inputs
                ],
                "outputs": [
                    {
                        "name": port.name,
                        "type": port.type,
                        "description": port.description,
                    }
                    for port in definition.outputs
                ],
            }
            for definition in self.node_definitions.values()
        ]

    def validate_workflow(self, workflow: Workflow) -> tuple[bool, list[str]]:
        """Validate workflow structure.

        Args:
            workflow: Workflow to validate

        Returns:
            (is_valid, list of errors)
        """
        errors = []

        if not workflow.nodes:
            errors.append("Workflow has no nodes")
            return False, errors

        # Validate all connections reference existing nodes
        for conn in workflow.connections:
            if conn.from_node not in workflow.nodes:
                errors.append(f"Connection references unknown node: {conn.from_node}")
            if conn.to_node not in workflow.nodes:
                errors.append(f"Connection references unknown node: {conn.to_node}")

        return len(errors) == 0, errors
