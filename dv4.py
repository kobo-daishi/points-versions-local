import bpy
import bmesh

bl_info = {
    "name": "Easy Points",
    "blender": (3, 0, 0),
    "category": "Object",
    "version": (1, 0, 35),
    "author": "@marv.os",
    "location": "View3D > Sidebar > Easy Points Tab",
    "description": "An addon to convert mesh to points and apply various operations",
    "warning": "",
    "wiki_url": "",
    "tracker_url": "https://www.instagram.com/marv.os",
    "support": "COMMUNITY",
    "doc_url": "",
}

selected_feature = None

def update_geometry_node(self, context):
    selected_object = context.active_object
    if selected_object and selected_object.type == 'MESH':
        for mod in selected_object.modifiers:
            if mod.type == 'NODES' and mod.node_group:
                node_group = mod.node_group
                for node in node_group.nodes:
                    if node.bl_idname == "GeometryNodeSetPointRadius":
                        node.inputs['Radius'].default_value = self.radius
                    if node.bl_idname == "GeometryNodeDistributePointsOnFaces":
                        node.inputs['Density'].default_value = self.density
                        node.inputs['Seed'].default_value = self.random
                    if node.bl_idname == "GeometryNodeMeshToPoints":
                        node.inputs['Radius'].default_value = self.radius

class EasyPointsProperties(bpy.types.PropertyGroup):
    radius: bpy.props.FloatProperty(
        name="Point Size",
        description="Size of the Points",
        default=0.023,
        min=0.0,
        max=100.0,
        update=update_geometry_node
    )
    density: bpy.props.FloatProperty(
        name="Density",
        description="Density of the Points",
        default=25.0,
        min=0.0,
        max=1000000.0,
        update=update_geometry_node
    )
    random: bpy.props.IntProperty(
        name="Random Seed",
        description="Random seed for point distribution",
        default=0,
        min=0,
        max=100,
        update=update_geometry_node
    )
    applied_effect: bpy.props.StringProperty(
        name="Applied Effect",
        description="Stores the applied effect type",
        default=""
    )

def create_default_material():
    material = bpy.data.materials.get("EasyPointsDefaultMaterial")
    if material is None:
        material = bpy.data.materials.new(name="EasyPointsDefaultMaterial")
        material.use_nodes = True
        bsdf = material.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs['Base Color'].default_value = (0.8, 0.8, 0.8, 1.0)
    return material

def enable_cycles(context):
    context.scene.render.engine = 'CYCLES'
    context.scene.cycles.device = 'GPU'

def apply_distribute_points(context):
    selected_object = context.active_object
    props = selected_object.easy_points_props

    existing_modifier = None
    for mod in selected_object.modifiers:
        if mod.type == 'NODES':
            existing_modifier = mod
            break

    if existing_modifier is None:
        bpy.ops.object.modifier_add(type='NODES')
        modifier = selected_object.modifiers[-1]
    else:
        modifier = existing_modifier

    if modifier.node_group is None:
        bpy.ops.node.new_geometry_node_group_assign()
        node_group = modifier.node_group
    else:
        node_group = modifier.node_group

    if node_group is None:
        return

    nodes = node_group.nodes
    links = node_group.links

    group_input = nodes.get('Group Input') or nodes.new('NodeGroupInput')
    group_output = nodes.get('Group Output') or nodes.new('NodeGroupOutput')

    distribute_points = nodes.new(type="GeometryNodeDistributePointsOnFaces")
    set_point_radius = nodes.new(type="GeometryNodeSetPointRadius")
    set_material = nodes.new(type="GeometryNodeSetMaterial")

    if selected_object.active_material:
        set_material.inputs['Material'].default_value = selected_object.active_material
    else:
        default_material = bpy.data.materials.get("Material") or bpy.data.materials.new(name="Material")
        set_material.inputs['Material'].default_value = default_material

    links.new(group_input.outputs['Geometry'], distribute_points.inputs['Mesh'])
    links.new(distribute_points.outputs['Points'], set_point_radius.inputs['Points'])
    links.new(set_point_radius.outputs['Points'], set_material.inputs['Geometry'])
    links.new(set_material.outputs['Geometry'], group_output.inputs['Geometry'])

    distribute_points.inputs['Density'].default_value = props.density
    set_point_radius.inputs['Radius'].default_value = props.radius
    distribute_points.inputs['Seed'].default_value = props.random

    props.applied_effect = "ADD_POINTS"
    context.area.tag_redraw()

def apply_mesh_to_points(context):
    selected_object = context.active_object
    props = selected_object.easy_points_props

    existing_modifier = None
    for mod in selected_object.modifiers:
        if mod.type == 'NODES':
            existing_modifier = mod
            break

    if existing_modifier is None:
        bpy.ops.object.modifier_add(type='NODES')
        modifier = selected_object.modifiers[-1]
    else:
        modifier = existing_modifier

    if modifier.node_group is None:
        bpy.ops.node.new_geometry_node_group_assign()
        node_group = modifier.node_group
    else:
        node_group = modifier.node_group

    if node_group is None:
        return

    nodes = node_group.nodes
    links = node_group.links

    group_input = nodes.get('Group Input') or nodes.new('NodeGroupInput')
    group_output = nodes.get('Group Output') or nodes.new('NodeGroupOutput')

    mesh_to_points = nodes.new(type="GeometryNodeMeshToPoints")
    set_material = nodes.new(type="GeometryNodeSetMaterial")

    if selected_object.active_material:
        set_material.inputs['Material'].default_value = selected_object.active_material
    else:
        set_material.inputs['Material'].default_value = create_default_material()

    links.new(group_input.outputs['Geometry'], mesh_to_points.inputs['Mesh'])
    links.new(mesh_to_points.outputs['Points'], set_material.inputs['Geometry'])
    links.new(set_material.outputs['Geometry'], group_output.inputs['Geometry'])

    mesh_to_points.inputs['Radius'].default_value = props.radius

    props.applied_effect = "MESH_TO_POINTS"
    context.area.tag_redraw()

class OBJECT_OT_add_points_modifier(bpy.types.Operator):
    bl_idname = "object.add_points_modifier"
    bl_label = "Distribute Points"
    bl_description = "Add points to the object"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        global selected_feature
        selected_object = context.active_object
        if selected_object and selected_object.type == 'MESH':
            enable_cycles(context)
            apply_distribute_points(context)
            selected_feature = 'ADD_POINTS'
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, "No mesh object selected")
            return {'CANCELLED'}

class OBJECT_OT_add_mesh_to_points(bpy.types.Operator):
    bl_idname = "object.add_mesh_to_points"
    bl_label = "Mesh to Points"
    bl_description = "Convert mesh to points"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        global selected_feature
        selected_object = context.active_object
        if selected_object and selected_object.type == 'MESH':
            enable_cycles(context)
            apply_mesh_to_points(context)
            selected_feature = 'MESH_TO_POINTS'
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, "No mesh object selected")
            return {'CANCELLED'}

class OBJECT_OT_reset_model(bpy.types.Operator):
    bl_idname = "object.reset_model"
    bl_label = "Reset Model"
    bl_description = "Reset geometry nodes to default settings"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        selected_object = context.active_object
        if selected_object and selected_object.type == 'MESH':
            for mod in selected_object.modifiers:
                if mod.type == 'NODES' and mod.node_group:
                    for node in mod.node_group.nodes:
                        if node.bl_idname == "GeometryNodeSetPointRadius":
                            node.inputs['Radius'].default_value = 0.023
                        if node.bl_idname == "GeometryNodeDistributePointsOnFaces":
                            node.inputs['Density'].default_value = 25.0
                        if node.bl_idname == "GeometryNodeMeshToPoints":
                            node.inputs['Radius'].default_value = 0.023
            selected_object.easy_points_props.applied_effect = ""
            self.report({'INFO'}, "Geometry modifier reset to default point size and density settings")
        else:
            self.report({'ERROR'}, "No mesh object selected")
            return {'CANCELLED'}
        return {'FINISHED'}

class OBJECT_OT_return_to_main(bpy.types.Operator):
    bl_idname = "object.return_to_main"
    bl_label = "Return to Main"
    bl_description = "Return to the main selection screen"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        global selected_feature
        selected_feature = None
        context.area.tag_redraw()
        return {'FINISHED'}

class OBJECT_PT_easy_points_panel(bpy.types.Panel):
    bl_idname = "OBJECT_PT_easy_points_panel"
    bl_label = "Easy Points"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Easy Points'
    
    def draw(self, context):
        layout = self.layout
        global selected_feature
        selected_object = context.active_object

        if selected_object is None or selected_object.type != 'MESH' or not hasattr(selected_object, 'easy_points_props') or selected_object.easy_points_props.applied_effect == "":
            selected_feature = None
        else:
            selected_feature = selected_object.easy_points_props.applied_effect

        layout.label(text="Easy Points v1.0.35", icon='MESH_CIRCLE')

        if selected_feature is None:
            layout.label(text="Step 1: Select Feature")
            col = layout.column(align=True)
            col.scale_y = 1.5
            col.operator("object.add_points_modifier", text="", icon='MESH_CUBE')
            col.label(text="Distribute Points")
            col.operator("object.add_mesh_to_points", text="", icon='OUTLINER_OB_POINTCLOUD')
            col.label(text="Mesh to Points")
        else:
            if selected_object and selected_object.type == 'MESH':
                box = layout.box()
                box.label(text=f"Object: {selected_object.name}")
                box.label(text=f"Polygons: {len(selected_object.data.polygons)}")

            if selected_feature == 'ADD_POINTS':
                layout.label(text="Step 2: Point Settings")
                layout.prop(selected_object.easy_points_props, "density", text="Density")
                layout.prop(selected_object.easy_points_props, "radius", text="Point Size")
                layout.prop(selected_object.easy_points_props, "random", text="Random Seed")
                layout.operator("object.reset_model", text="Reset", icon='FILE_REFRESH')
            elif selected_feature == 'MESH_TO_POINTS':
                layout.label(text="Step 2: Point Settings")
                layout.prop(selected_object.easy_points_props, "radius", text="Point Size")

            layout.separator()
            layout.operator("object.return_to_main", text="Return", icon='LOOP_BACK')

        row = layout.row()
        row.alignment = 'RIGHT'
        row.label(text="Made by marv.os")

classes = (
    EasyPointsProperties,
    OBJECT_OT_add_points_modifier,
    OBJECT_OT_add_mesh_to_points,
    OBJECT_OT_reset_model,
    OBJECT_OT_return_to_main,
    OBJECT_PT_easy_points_panel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Object.easy_points_props = bpy.props.PointerProperty(type=EasyPointsProperties)
    print("Easy Points plugin registered")

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    del bpy.types.Object.easy_points_props
    print("Easy Points plugin unregistered")

if __name__ == "__main__":
    register()
