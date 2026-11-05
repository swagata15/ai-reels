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


def hologram(name: str, color_hex: str, strength: float = 6.0, edge_power: float = 0.25):
    """See-through shell that glows at grazing angles - the classic 'sci-fi scan' look."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    weight = nt.nodes.new("ShaderNodeLayerWeight")
    weight.inputs["Blend"].default_value = edge_power
    transparent = nt.nodes.new("ShaderNodeBsdfTransparent")
    emit = nt.nodes.new("ShaderNodeEmission")
    emit.inputs["Color"].default_value = hex_to_rgba(color_hex)
    emit.inputs["Strength"].default_value = strength
    mix = nt.nodes.new("ShaderNodeMixShader")
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(weight.outputs["Facing"], mix.inputs["Fac"])
    nt.links.new(transparent.outputs[0], mix.inputs[1])
    nt.links.new(emit.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs[0])
    if hasattr(mat, "surface_render_method"):
        mat.surface_render_method = "BLENDED"
    elif hasattr(mat, "blend_method"):
        mat.blend_method = "BLEND"
    return mat


def _mix_rgb(nt, fac_socket, a, b):
    """Colour mix that works across Blender versions; returns the output socket."""
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    nt.links.new(fac_socket, mix.inputs["Factor"])
    sockets = [s for s in mix.inputs if s.type == "RGBA"]
    for sock, val in zip(sockets[:2], (a, b)):
        if isinstance(val, tuple):
            sock.default_value = val
        else:
            nt.links.new(val, sock)
    return [s for s in mix.outputs if s.type == "RGBA"][0]


def tissue(name: str, base_hex: str = "#D99A9A", crease_hex: str = "#5A1F2A",
           vein_hex: str = "#7A0F1E", vein_scale: float = 4.0, crease: str = "pointiness"):
    """Wet, fleshy organic tissue: subsurface scattering, darker creases, fine vessels, coat."""
    mat, bsdf = _principled(name)
    nt = mat.node_tree

    # Creases darker: Pointiness (Cycles only, free) or Ambient Occlusion (works in EEVEE too).
    crease_ramp = nt.nodes.new("ShaderNodeValToRGB")
    if crease == "ao":
        ao = nt.nodes.new("ShaderNodeAmbientOcclusion")
        ao.inputs["Distance"].default_value = 0.35
        crease_ramp.color_ramp.elements[0].position = 0.35
        crease_ramp.color_ramp.elements[1].position = 0.9
        nt.links.new(ao.outputs["AO"], crease_ramp.inputs["Fac"])
    else:
        geo = nt.nodes.new("ShaderNodeNewGeometry")
        crease_ramp.color_ramp.elements[0].position = 0.44
        crease_ramp.color_ramp.elements[1].position = 0.53
        nt.links.new(geo.outputs["Pointiness"], crease_ramp.inputs["Fac"])
    col = _mix_rgb(nt, crease_ramp.outputs["Color"], hex_to_rgba(crease_hex), hex_to_rgba(base_hex))

    # Blood vessels: thin iso-lines of a noise field.
    coord = nt.nodes.new("ShaderNodeTexCoord")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = vein_scale
    noise.inputs["Detail"].default_value = 6.0
    noise.inputs["Roughness"].default_value = 0.55
    nt.links.new(coord.outputs["Object"], noise.inputs["Vector"])
    sub = nt.nodes.new("ShaderNodeMath")
    sub.operation = "SUBTRACT"
    sub.inputs[1].default_value = 0.5
    nt.links.new(noise.outputs["Fac"], sub.inputs[0])
    absn = nt.nodes.new("ShaderNodeMath")
    absn.operation = "ABSOLUTE"
    nt.links.new(sub.outputs[0], absn.inputs[0])
    vein_ramp = nt.nodes.new("ShaderNodeValToRGB")
    vein_ramp.color_ramp.elements[0].position = 0.0
    vein_ramp.color_ramp.elements[0].color = (1, 1, 1, 1)
    vein_ramp.color_ramp.elements[1].position = 0.018
    vein_ramp.color_ramp.elements[1].color = (0, 0, 0, 1)
    nt.links.new(absn.outputs[0], vein_ramp.inputs["Fac"])
    col = _mix_rgb(nt, vein_ramp.outputs["Color"], col, hex_to_rgba(vein_hex))
    nt.links.new(col, bsdf.inputs["Base Color"])

    # Micro-surface bumps for wet specular breakup.
    bump_noise = nt.nodes.new("ShaderNodeTexNoise")
    bump_noise.inputs["Scale"].default_value = 40.0
    nt.links.new(coord.outputs["Object"], bump_noise.inputs["Vector"])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.15
    nt.links.new(bump_noise.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

    _set(bsdf, ["Subsurface Weight", "Subsurface"], 0.35)
    _set(bsdf, "Subsurface Radius", (1.0, 0.35, 0.25))
    _set(bsdf, "Subsurface Scale", 0.15)
    _set(bsdf, "Roughness", 0.38)
    _set(bsdf, ["Coat Weight", "Clearcoat"], 0.45)
    _set(bsdf, ["Coat Roughness", "Clearcoat Roughness"], 0.12)
    return mat
