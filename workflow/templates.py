"""
Pre-built workflow templates for common video production tasks.

Provides starting points for T2V, I2V, and composition workflows.
"""
import logging
from .node_schema import Workflow, WorkflowEngine

log = logging.getLogger("workflow_templates")


def create_text_to_video_template(engine: WorkflowEngine) -> Workflow:
    """Create template workflow: Text → Video → Color Grade → Effects.

    Returns:
        Workflow instance with nodes connected in pipeline
    """
    workflow = engine.create_workflow(
        name="Text-to-Video Production",
        description="Generate video from text, apply color grading and effects",
    )

    # T2V node
    t2v_id = engine.add_node(
        workflow,
        "text_to_video",
        config={
            "model": "sora",
            "duration": 5.0,
            "resolution": "1080p",
        },
        position=(50, 100),
    )

    # Color grading node
    grade_id = engine.add_node(
        workflow,
        "color_grade",
        config={
            "profile": "cinematic_default",
            "intensity": 1.0,
        },
        position=(250, 100),
    )

    # Effects node
    effects_id = engine.add_node(
        workflow,
        "apply_effects",
        config={
            "effects": [
                {"name": "vignette", "intensity": 0.3},
                {"name": "film_grain", "intensity": 0.1},
            ],
        },
        position=(450, 100),
    )

    # Connect nodes
    engine.connect_nodes(workflow, t2v_id, "video", grade_id, "input")
    engine.connect_nodes(workflow, grade_id, "output", effects_id, "input")

    log.info("text_to_video_template_created", extra={"workflow_id": workflow.id})
    return workflow


def create_image_to_video_template(engine: WorkflowEngine) -> Workflow:
    """Create template workflow: Image → Video → Color Grade → Effects.

    Returns:
        Workflow instance with nodes connected in pipeline
    """
    workflow = engine.create_workflow(
        name="Image-to-Video Production",
        description="Animate image into video with cinematography",
    )

    # I2V node
    i2v_id = engine.add_node(
        workflow,
        "image_to_video",
        config={
            "model": "runway-i2v",
            "duration": 5.0,
        },
        position=(50, 100),
    )

    # Color grading node
    grade_id = engine.add_node(
        workflow,
        "color_grade",
        config={
            "profile": "warm_golden",
            "intensity": 1.0,
        },
        position=(250, 100),
    )

    # Lighting adjustment node
    lighting_id = engine.add_node(
        workflow,
        "adjust_lighting",
        config={
            "brightness": 0.1,
            "contrast": 0.2,
            "exposure": 0.0,
        },
        position=(450, 100),
    )

    # Effects node
    effects_id = engine.add_node(
        workflow,
        "apply_effects",
        config={
            "effects": [
                {"name": "bokeh_bloom", "intensity": 0.2},
                {"name": "lens_flare", "intensity": 0.15},
            ],
        },
        position=(650, 100),
    )

    # Connect nodes
    engine.connect_nodes(workflow, i2v_id, "video", grade_id, "input")
    engine.connect_nodes(workflow, grade_id, "output", lighting_id, "input")
    engine.connect_nodes(workflow, lighting_id, "output", effects_id, "input")

    log.info("image_to_video_template_created", extra={"workflow_id": workflow.id})
    return workflow


def create_multi_scene_composition_template(engine: WorkflowEngine) -> Workflow:
    """Create template workflow: Multi-scene composition with transitions.

    Returns:
        Workflow instance for composing multiple generated videos
    """
    workflow = engine.create_workflow(
        name="Multi-Scene Composition",
        description="Compose multiple videos with transitions and consistent grading",
    )

    # Scene generation nodes
    scene1_id = engine.add_node(
        workflow,
        "text_to_video",
        config={
            "model": "sora",
            "duration": 5.0,
            "prompt": "[Scene 1 prompt]",
        },
        position=(50, 100),
    )

    scene2_id = engine.add_node(
        workflow,
        "text_to_video",
        config={
            "model": "sora",
            "duration": 5.0,
            "prompt": "[Scene 2 prompt]",
        },
        position=(50, 250),
    )

    scene3_id = engine.add_node(
        workflow,
        "text_to_video",
        config={
            "model": "sora",
            "duration": 5.0,
            "prompt": "[Scene 3 prompt]",
        },
        position=(50, 400),
    )

    # Concatenation node with transitions
    concat_id = engine.add_node(
        workflow,
        "concatenate",
        config={
            "transitions": [
                {"type": "crossfade", "duration": 1.0},
                {"type": "crossfade", "duration": 1.0},
            ],
        },
        position=(250, 250),
    )

    # Final color grading (applies to entire composition)
    grade_id = engine.add_node(
        workflow,
        "color_grade",
        config={
            "profile": "cinematic_default",
            "intensity": 1.0,
        },
        position=(450, 250),
    )

    # Final effects
    effects_id = engine.add_node(
        workflow,
        "apply_effects",
        config={
            "effects": [
                {"name": "film_grain", "intensity": 0.15},
            ],
        },
        position=(650, 250),
    )

    # Connect scene outputs to concatenation
    engine.connect_nodes(workflow, scene1_id, "video", concat_id, "clips")
    engine.connect_nodes(workflow, scene2_id, "video", concat_id, "clips")
    engine.connect_nodes(workflow, scene3_id, "video", concat_id, "clips")

    # Connect final pipeline
    engine.connect_nodes(workflow, concat_id, "output", grade_id, "input")
    engine.connect_nodes(workflow, grade_id, "output", effects_id, "input")

    log.info("multi_scene_composition_template_created", extra={"workflow_id": workflow.id})
    return workflow


def create_flux_image_generation_template(engine: WorkflowEngine) -> Workflow:
    """Create template workflow: Flux image generation with customization.

    Returns:
        Workflow instance for generating images
    """
    workflow = engine.create_workflow(
        name="Flux Image Generation",
        description="Generate high-quality images with Flux",
    )

    # Flux T2I node
    flux_id = engine.add_node(
        workflow,
        "flux_t2i",
        config={
            "model": "flux-pro",
            "width": 1024,
            "height": 1024,
        },
        position=(100, 100),
    )

    log.info("flux_image_generation_template_created", extra={"workflow_id": workflow.id})
    return workflow


def list_templates() -> list[dict]:
    """List all available workflow templates.

    Returns:
        List of template metadata
    """
    return [
        {
            "id": "text_to_video",
            "name": "Text-to-Video Production",
            "description": "Generate video from text prompt with cinematography",
            "category": "generation",
        },
        {
            "id": "image_to_video",
            "name": "Image-to-Video Production",
            "description": "Animate image into video with color grading and effects",
            "category": "animation",
        },
        {
            "id": "multi_scene_composition",
            "name": "Multi-Scene Composition",
            "description": "Compose multiple videos with transitions and consistent grading",
            "category": "composition",
        },
        {
            "id": "flux_image_generation",
            "name": "Flux Image Generation",
            "description": "Generate high-quality images with Flux",
            "category": "generation",
        },
    ]


def instantiate_template(engine: WorkflowEngine, template_id: str) -> Workflow:
    """Instantiate a template workflow.

    Args:
        engine: WorkflowEngine instance
        template_id: Template ID

    Returns:
        Workflow instance or None if not found

    Raises:
        ValueError: If template ID not recognized
    """
    templates = {
        "text_to_video": create_text_to_video_template,
        "image_to_video": create_image_to_video_template,
        "multi_scene_composition": create_multi_scene_composition_template,
        "flux_image_generation": create_flux_image_generation_template,
    }

    if template_id not in templates:
        raise ValueError(f"Unknown template: {template_id}")

    return templates[template_id](engine)
