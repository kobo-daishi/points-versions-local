import bpy
import tempfile
import os
import json
from bpy.app.handlers import persistent

# Current version information
major_version = 1
minor_version = 0
patch_version = 45

bl_info = {
    "name": "Blender.Points",
    "blender": (3, 0, 0),
    "category": "Object",
    "version": (major_version, minor_version, patch_version),
    "author": "@marv.os",
    "location": "View3D > Sidebar > Blender.Points Tab",
    "description": "An addon to convert mesh to points and apply various operations",
    "warning": "",
    "tracker_url": "https://www.instagram.com/marv.os",
    "support": "COMMUNITY",
}

# Global variable to store whether the addon is unlocked
addon_unlocked = False

def update_geometry_node(self, context):
    selected_object = context.active_object
    if selected_object and selected_object.type == 'MESH':
        props = selected_object.blender_points_props
        for mod in selected_object.modifiers:
            if mod.type == 'NODES' and mod.node_group:
                node_group = mod.node_group
                for node in node_group.nodes:
                    if node.bl_idname == "GeometryNodeSetPointRadius":
                        node.inputs['Radius'].default_value = props.radius
                    if node.bl_idname == "GeometryNodeDistributePointsOnFaces":
                        node.inputs['Density'].default_value = props.density
                        node.inputs['Seed'].default_value = props.random
                    if node.bl_idname == "GeometryNodeMeshToPoints":
                        node.inputs['Radius'].default_value = props.radius
                    if node.bl_idname == "GeometryNodeInstanceOnPoints":
                        if props.selected_feature == 'ADD_POINTS':
                            node.mute = not props.enable_points_add
                            node.inputs['Scale'].default_value = (props.scale_add, props.scale_add, props.scale_add)
                        elif props.selected_feature == 'MESH_TO_POINTS':
                            node.mute = not props.enable_points_mesh
                            node.inputs['Scale'].default_value = (props.scale_mesh, props.scale_mesh, props.scale_mesh)
                    if node.bl_idname == "GeometryNodeObjectInfo":
                        instance_obj = bpy.data.objects.get(props.instance_object_mesh if props.selected_feature == 'MESH_TO_POINTS' else props.instance_object_add)
                        if instance_obj:
                            node.inputs['Object'].default_value = instance_obj

def get_instance_object_items(self, context):
    items = [("None", "Nothing Selected", "")]
    items += [(obj.name, obj.name, "") for obj in bpy.data.objects if obj.type == 'MESH' and obj.name != "PointCloud"]
    return items

class BlenderPointsProperties(bpy.types.PropertyGroup):
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
    enable_points_add: bpy.props.BoolProperty(
        name="Enable Points Instancing for Distribute Points",
        description="Enable or disable points instancing for Distribute Points",
        default=False,
        update=update_geometry_node
    )
    enable_points_mesh: bpy.props.BoolProperty(
        name="Enable Points Instancing for Mesh to Points",
        description="Enable or disable points instancing for Mesh to Points",
        default=False,
        update=update_geometry_node
    )
    instance_object_add: bpy.props.EnumProperty(
        name="Instance Object for Distribute Points",
        description="Select your object to replace the points for Distribute Points",
        items=get_instance_object_items,
        update=update_geometry_node
    )
    instance_object_mesh: bpy.props.EnumProperty(
        name="Instance Object for Mesh to Points",
        description="Select your object to replace the points for Mesh to Points",
        items=get_instance_object_items,
        update=update_geometry_node
    )
    scale_add: bpy.props.FloatProperty(
        name="Scale for Distribute Points",
        description="Overall scale of the instanced object for Distribute Points",
        default=1.0,
        min=0.0,
        max=10.0,
        update=update_geometry_node
    )
    scale_mesh: bpy.props.FloatProperty(
        name="Scale for Mesh to Points",
        description="Overall scale of the instanced object for Mesh to Points",
        default=1.0,
        min=0.0,
        max=10.0,
        update=update_geometry_node
    )
    applied_effect: bpy.props.StringProperty(
        name="Applied Effect",
        description="Stores the applied effect type",
        default=""
    )
    unlocked: bpy.props.BoolProperty(
        name="Unlocked",
        description="Track if the addon is unlocked",
        default=False
    )
    email: bpy.props.StringProperty(
        name="Email",
        description="Enter your email"
    )
    password: bpy.props.StringProperty(
        name="Password",
        description="Enter your password",
        subtype='PASSWORD'
    )
    token: bpy.props.StringProperty(
        name="Token",
        description="Stores the authentication token",
        default=""
    )
    selected_feature: bpy.props.StringProperty(
        name="Selected Feature",
        description="Stores the selected feature",
        default=""
    )

def save_user_credentials(email, token):
    credentials_path = os.path.join(bpy.utils.user_resource('CONFIG'), "blender_points_credentials.json")
    with open(credentials_path, 'w') as f:
        json.dump({"email": email, "token": token}, f)

def load_user_credentials():
    credentials_path = os.path.join(bpy.utils.user_resource('CONFIG'), "blender_points_credentials.json")
    if os.path.exists(credentials_path):
        with open(credentials_path, 'r') as f:
            return json.load(f)
    return None

def create_default_material():
    material = bpy.data.materials.get("BlenderPointsDefaultMaterial")
    if material is None:
        material = bpy.data.materials.new(name="BlenderPointsDefaultMaterial")
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
    props = selected_object.blender_points_props  # Use object property

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
    object_info = nodes.new(type="GeometryNodeObjectInfo")
    instance_on_points = nodes.new(type="GeometryNodeInstanceOnPoints")
    set_material = nodes.new(type="GeometryNodeSetMaterial")

    distribute_points.location = (0, 0)
    set_point_radius.location = (300, 0)
    object_info.location = (500, 0)
    instance_on_points.location = (700, 0)
    set_material.location = (900, 0)

    if selected_object.active_material:
        set_material.inputs['Material'].default_value = selected_object.active_material
    else:
        set_material.inputs['Material'].default_value = create_default_material()

    links.new(group_input.outputs['Geometry'], distribute_points.inputs['Mesh'])
    links.new(distribute_points.outputs['Points'], set_point_radius.inputs['Points'])
    links.new(set_point_radius.outputs['Points'], instance_on_points.inputs['Points'])
    links.new(object_info.outputs['Geometry'], instance_on_points.inputs['Instance'])
    links.new(instance_on_points.outputs['Instances'], set_material.inputs['Geometry'])
    links.new(set_material.outputs['Geometry'], group_output.inputs['Geometry'])

    distribute_points.inputs['Density'].default_value = props.density
    set_point_radius.inputs['Radius'].default_value = props.radius
    distribute_points.inputs['Seed'].default_value = props.random

    instance_on_points.mute = True  # Mute the instance on points node by default

    # Force update to ensure changes are reflected immediately
    bpy.context.view_layer.objects.active = selected_object
    selected_object.update_tag(refresh={'DATA'})
    bpy.context.view_layer.update()

def apply_mesh_to_points(context):
    selected_object = context.active_object
    props = selected_object.blender_points_props  # Use object property

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
    object_info = nodes.new(type="GeometryNodeObjectInfo")
    instance_on_points = nodes.new(type="GeometryNodeInstanceOnPoints")
    set_material = nodes.new(type="GeometryNodeSetMaterial")

    mesh_to_points.location = (0, 0)
    object_info.location = (200, 0)
    instance_on_points.location = (400, 0)
    set_material.location = (600, 0)

    if selected_object.active_material:
        set_material.inputs['Material'].default_value = selected_object.active_material
    else:
        set_material.inputs['Material'].default_value = create_default_material()

    links.new(group_input.outputs['Geometry'], mesh_to_points.inputs['Mesh'])
    links.new(mesh_to_points.outputs['Points'], instance_on_points.inputs['Points'])
    links.new(object_info.outputs['Geometry'], instance_on_points.inputs['Instance'])
    links.new(instance_on_points.outputs['Instances'], set_material.inputs['Geometry'])
    links.new(set_material.outputs['Geometry'], group_output.inputs['Geometry'])

    mesh_to_points.inputs['Radius'].default_value = props.radius

    instance_obj = bpy.data.objects.get(props.instance_object_mesh)
    if instance_obj:
        object_info.inputs['Object'].default_value = instance_obj

    instance_on_points.mute = not props.enable_points_mesh
    instance_on_points.inputs['Scale'].default_value = (props.scale_mesh, props.scale_mesh, props.scale_mesh)

class OBJECT_OT_add_points_modifier(bpy.types.Operator):
    bl_idname = "object.add_points_modifier"
    bl_label = "Distribute Points"
    bl_description = "Add points to the object"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        selected_object = context.active_object
        if selected_object and selected_object.type == 'MESH':
            enable_cycles(context)
            apply_distribute_points(context)
            selected_object.blender_points_props.selected_feature = 'ADD_POINTS'
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
        selected_object = context.active_object
        if selected_object and selected_object.type == 'MESH':
            enable_cycles(context)
            apply_mesh_to_points(context)
            selected_object.blender_points_props.selected_feature = 'MESH_TO_POINTS'
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
            selected_object.blender_points_props.density = 25.0
            selected_object.blender_points_props.radius = 0.023
            selected_object.blender_points_props.random = 0
            self.report({'INFO'}, "Geometry modifier reset to default point size and density settings")
        else:
            self.report({'ERROR'}, "No mesh object selected")
            return {'CANCELLED'}
        return {'FINISHED'}

class OBJECT_OT_return_to_main(bpy.types.Operator):
    bl_idname = "object.return_to_main"
    bl_label = "Return to Main"
    bl_description = "Return to the main selection screen and remove applied geometry nodes"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        selected_object = context.active_object
        if selected_object and selected_object.type == 'MESH':
            for mod in selected_object.modifiers:
                if mod.type == 'NODES':
                    selected_object.modifiers.remove(mod)
            selected_object.blender_points_props.applied_effect = ""
            selected_object.blender_points_props.selected_feature = ""
        context.area.tag_redraw()
        return {'FINISHED'}

class OBJECT_OT_help_button(bpy.types.Operator):
    bl_idname = "object.help_button"
    bl_label = ""
    bl_description = "Submit an email for help or report a bug"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        bpy.ops.wm.url_open(url="mailto:inquiry@marv.studio")
        return {'FINISHED'}

class OBJECT_PT_blender_points_panel(bpy.types.Panel):
    bl_idname = "OBJECT_PT_blender_points_panel"
    bl_label = "Blender.Points"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Blender.Points'
    
    def draw(self, context):
        layout = self.layout
        selected_object = context.active_object
        props = context.scene.blender_points_props

        layout.label(text="Blender.Points", icon='MESH_CIRCLE')
        layout.label(text=f"Version: {major_version}.{minor_version}.{patch_version}")

        if selected_object and selected_object.type == 'MESH':
            object_props = selected_object.blender_points_props

        if selected_object is None or selected_object.type != 'MESH' or not selected_object.blender_points_props.selected_feature:
            layout.label(text="Step 1: Select Feature")
            col = layout.column(align=True)
            col.scale_y = 1.5
            col.operator("object.add_points_modifier", text="", icon='OUTLINER_OB_POINTCLOUD')
            col.label(text="Distribute Points")
            col.operator("object.add_mesh_to_points", text="", icon='MESH_UVSPHERE')
            col.label(text="Mesh to Points")
        else:
            if selected_object and selected_object.type == 'MESH':
                box = layout.box()
                box.label(text=f"Object: {selected_object.name}")
                box.label(text=f"Polygons: {len(selected_object.data.polygons)}")

            if selected_object.blender_points_props.selected_feature == 'ADD_POINTS':
                layout.label(text="Step 2: Point Settings")
                layout.prop(selected_object.blender_points_props, "density", text="Density")
                layout.prop(selected_object.blender_points_props, "radius", text="Point Size")
                layout.prop(selected_object.blender_points_props, "random", text="Random Seed")
                layout.prop(selected_object.blender_points_props, "enable_points_add", text="Enable Points Instancing")
                if selected_object.blender_points_props.enable_points_add:
                    box = layout.box()
                    box.label(text="Instance Settings", icon='MODIFIER')
                    box.prop(selected_object.blender_points_props, "instance_object_add", text="Select your object to replace the points")
                    box.prop(selected_object.blender_points_props, "scale_add", text="Scale")
                layout.operator("object.reset_model", text="Reset", icon='FILE_REFRESH')
            elif selected_object.blender_points_props.selected_feature == 'MESH_TO_POINTS':
                layout.label(text="Step 2: Point Settings")
                layout.prop(selected_object.blender_points_props, "radius", text="Point Size")
                layout.prop(selected_object.blender_points_props, "enable_points_mesh", text="Enable Points Instancing", icon='TOOL_SETTINGS')
                if selected_object.blender_points_props.enable_points_mesh:
                    box = layout.box()
                    box.label(text="Instance Settings", icon='MODIFIER')
                    box.prop(selected_object.blender_points_props, "instance_object_mesh", text="Select your object to replace the points")
                    box.prop(selected_object.blender_points_props, "scale_mesh", text="Scale")

            layout.separator()
            row = layout.row()
            row.scale_x = 0.5
            row.operator("object.return_to_main", text="Return", icon='LOOP_BACK')

        layout.separator()
        row = layout.row()
        row.alignment = 'RIGHT'
        row.scale_x = 0.5
        row.operator("object.help_button", text="", icon='INFO')

def increment_version():
    global major_version, minor_version, patch_version
    patch_version += 1
    if patch_version >= 100:
        patch_version = 0
        minor_version += 1
    if minor_version >= 10:
        minor_version = 0
        major_version += 1

@persistent
def load_persistent_data(dummy):
    credentials = load_user_credentials()
    if credentials:
        props = bpy.context.scene.blender_points_props
        props.email = credentials.get("email", "")
        props.token = credentials.get("token", "")
        if props.email:
            props.unlocked = True
            print("Addon unlocked successfully with persistent data.")
        else:
            props.unlocked = False
            print("No email found in persistent data.")
    else:
        print("No persistent data found.")

classes = (
    BlenderPointsProperties,
    OBJECT_OT_add_points_modifier,
    OBJECT_OT_add_mesh_to_points,
    OBJECT_OT_reset_model,
    OBJECT_OT_return_to_main,
    OBJECT_OT_help_button,
    OBJECT_PT_blender_points_panel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Object.blender_points_props = bpy.props.PointerProperty(type=BlenderPointsProperties)
    bpy.types.Scene.blender_points_props = bpy.props.PointerProperty(type=BlenderPointsProperties)
    bpy.app.handlers.load_post.append(load_persistent_data)
    print("Blender.Points plugin registered")

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    del bpy.types.Object.blender_points_props
    del bpy.types.Scene.blender_points_props
    bpy.app.handlers.load_post.remove(load_persistent_data)
    print("Blender.Points plugin unregistered")

if __name__ == "__main__":
    increment_version()
    register()
