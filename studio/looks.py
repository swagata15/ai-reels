"""Reusable materials tuned for social-media-friendly, high-contrast looks."""
from __future__ import annotations

import bpy

from .spec import hex_to_rgba


def _principled(name: str):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    return mat, bsdf


def _set(node, names, value):
    """Set the first input that exists (socket names change between Blender versions)."""
    for n in names if isinstance(names, (list, tuple)) else [names]:
        if n in node.inputs:
            node.inputs[n].default_value = value
            return


def neon(name: str, color_hex: str, strength: float = 8.0):
    """Pure emission - glows hard; pair with postprocess --glow."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    emit = nt.nodes.new("ShaderNodeEmission")
    emit.inputs["Color"].default_value = hex_to_rgba(color_hex)
    emit.inputs["Strength"].default_value = strength
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(emit.outputs[0], out.inputs[0])
    return mat


def glossy(name: str, color_hex: str, roughness: float = 0.15, metallic: float = 0.0):
    mat, bsdf = _principled(name)
    _set(bsdf, "Base Color", hex_to_rgba(color_hex))
    _set(bsdf, "Roughness", roughness)
    _set(bsdf, "Metallic", metallic)
    _set(bsdf, ["Coat Weight", "Clearcoat"], 0.6)
    return mat


def iridescent(name: str, color_a: str, color_b: str):
    """Fresnel-blended two-tone metal - reads as 'premium' on phone screens."""
    mat, bsdf = _principled(name)
    nt = mat.node_tree
    fresnel = nt.nodes.new("ShaderNodeLayerWeight")
    fresnel.inputs["Blend"].default_value = 0.35
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = hex_to_rgba(color_a)
    ramp.color_ramp.elements[1].color = hex_to_rgba(color_b)
    nt.links.new(fresnel.outputs["Facing"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    _set(bsdf, "Metallic", 0.85)
    _set(bsdf, "Roughness", 0.2)
    return mat


def assign(obj, mat) -> None:
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)
