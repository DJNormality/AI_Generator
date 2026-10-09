"""Blender node functions for packed RGB material textures.

Run or import this file inside Blender.  It intentionally contains no scene data.
"""

def _nodes(material):
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()
    return nodes, links


def build_rma_material(material, image=None, name='Packed RMA'):
    """R=roughness, G=metallic, B=ambient occlusion."""
    import bpy
    nodes, links = _nodes(material)
    output = nodes.new('ShaderNodeOutputMaterial')
    shader = nodes.new('ShaderNodeBsdfPrincipled')
    texture = nodes.new('ShaderNodeTexImage'); texture.label = name; texture.image = image
    separate = nodes.new('ShaderNodeSeparateColor'); separate.mode = 'RGB'
    ao = nodes.new('ShaderNodeMixRGB'); ao.blend_type = 'MULTIPLY'; ao.inputs[0].default_value = 1.0
    links.new(texture.outputs['Color'], separate.inputs['Color'])
    links.new(separate.outputs['Red'], shader.inputs['Roughness'])
    links.new(separate.outputs['Green'], shader.inputs['Metallic'])
    links.new(separate.outputs['Blue'], ao.inputs[2])
    links.new(shader.outputs['BSDF'], output.inputs['Surface'])
    return {'texture': texture, 'separate': separate, 'shader': shader, 'ao': ao, 'output': output}


def build_art_material(material, image=None, name='Packed ART'):
    """R=ambient occlusion, G=roughness, B=translucency."""
    nodes = build_rma_material(material, image, name)
    links = material.node_tree.links
    for channel in ('Red','Green','Blue'):
        for link in list(nodes['separate'].outputs[channel].links):links.remove(link)
    links.new(nodes['separate'].outputs['Green'], nodes['shader'].inputs['Roughness'])
    links.new(nodes['separate'].outputs['Red'], nodes['ao'].inputs[2])
    if 'Subsurface Weight' in nodes['shader'].inputs:
        links.new(nodes['separate'].outputs['Blue'], nodes['shader'].inputs['Subsurface Weight'])
    elif 'Subsurface' in nodes['shader'].inputs:
        links.new(nodes['separate'].outputs['Blue'], nodes['shader'].inputs['Subsurface'])
    return nodes


def build_mk1_mask_nodes(material, id_image=None, tone_image=None):
    """Create the MK-style ID-blue and Tone-green/blue mask extraction nodes."""
    import bpy
    material.use_nodes = True
    nodes, links = material.node_tree.nodes, material.node_tree.links
    id_texture = nodes.new('ShaderNodeTexImage'); id_texture.label = 'ID map'; id_texture.image = id_image
    id_split = nodes.new('ShaderNodeSeparateColor'); id_split.label = 'ID map — use Blue'; id_split.mode = 'RGB'
    tone_texture = nodes.new('ShaderNodeTexImage'); tone_texture.label = 'Tone map'; tone_texture.image = tone_image
    tone_split = nodes.new('ShaderNodeSeparateColor'); tone_split.label = 'Tone: Green=specular, Blue=dirt/damage'; tone_split.mode = 'RGB'
    links.new(id_texture.outputs['Color'], id_split.inputs['Color'])
    links.new(tone_texture.outputs['Color'], tone_split.inputs['Color'])
    return {'id_blue': id_split.outputs['Blue'], 'tone_green': tone_split.outputs['Green'],
            'tone_blue': tone_split.outputs['Blue'], 'id_texture': id_texture, 'tone_texture': tone_texture}
