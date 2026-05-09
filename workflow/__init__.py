"""
Workflow studio for ESCRIBE video production.

Node-based visual pipeline editor with templates and execution.
"""

from .node_schema import WorkflowEngine, Workflow, WorkflowNode, NodeDefinition
from .templates import (
    instantiate_template,
    list_templates,
    create_text_to_video_template,
    create_image_to_video_template,
    create_multi_scene_composition_template,
    create_flux_image_generation_template,
)

__all__ = [
    "WorkflowEngine",
    "Workflow",
    "WorkflowNode",
    "NodeDefinition",
    "instantiate_template",
    "list_templates",
    "create_text_to_video_template",
    "create_image_to_video_template",
    "create_multi_scene_composition_template",
    "create_flux_image_generation_template",
]
