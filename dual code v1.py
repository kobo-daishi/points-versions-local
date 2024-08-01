import bpy
import bmesh

bl_info = {
    "name": "Easy Points",
    "blender": (3, 0, 0),
    "category": "Object",
    "version": (1, 0, 20),
    "author": "@marv.os",
    "location": "View3D > Sidebar > Easy Points Tab",
    "description": "An addon to convert mesh to points and apply various operations",
    "warning": "",
    "wiki_url": "",
    "tracker_url": "https://www.instagram.com/marv.os",
    "support": "COMMUNITY",
    "doc_url": "",
}

# Global variable to store selected feature
selected_feature = None

def update_geometry_node(self, context):
    selected_object = context.active_object
    if selected_object and selected_object.type == 'MESH':
        for mod in selected_object.modifiers:
            if mod.type == 'NODES':
                node_group = mod.node_group
                if node_group:
                    for node in node_group.nodes:
                        if node.bl_idname == "GeometryNodeSetPointRadius":
                            node.inputs['Radius'].default_value = self.radius
                        if node.bl_idname == "GeometryNodeDistributePointsOnFaces":
                            node.inputs['Density'].default_value = self.density
                            node.inputs['Seed'].default_value = self.random
                        if node.bl_idname == "GeometryNodeMeshToPoints":
                            node.inputs['Radius'].default_value = self.radius

def get_object_items(self, context):
    items = [(obj.name, obj.name, "") for obj in bpy.data.objects if obj.type == 'MESH' and obj.name != "PointCloud"]
    return items

def update_instance_object(self, context):
    selected_object = context.active_object
    if selected_object and selected_object.type == 'MESH':
        for mod in selected_object.modifiers:
            if mod.type == 'NODES':
                node_group = mod.node_group
                if node_group:
                    for node in node_group.nodes:
                        if node.bl_idname == "GeometryNodeObjectInfo":
                            instance_obj = bpy.data.objects.get(self.instance_object)
                            if instance_obj:
                                node.inputs['Object'].default_value = instance_obj
                            break

def update_mute_instance_on_points(self, context):
    selected_object = context.active_object
    if selected_object and selected_object.type == 'MESH':
        for mod in selected_object.modifiers:
            if mod.type == 'NODES':
                node_group = mod.node_group
                if node_group:
                    for node in node_group.nodes:
                        if node.bl_idname == "GeometryNodeInstanceOnPoints":
                            node.mute = not self.enable_points
                            break

def update_instance_scale(self, context):
    selected_object = context.active_object
    if selected_object and selected_object.type == 'MESH':
        for mod in selected_object.modifiers:
            if mod.type == 'NODES':
                node_group = mod.node_group
                if node_group:
                    for node in node_group.nodes:
                        if node.bl_idname == "GeometryNodeInstanceOnPoints":
                            node.inputs['Scale'].default_value = (self.scale_x, self.scale_y, self.scale_z)
                            break

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
    enable_points: bpy.props.BoolProperty(
        name="Enable Points Instancing",
        description="Enable or disable points instancing",
        default=False,
        update=update_geometry_node
    )
    instance_object: bpy.props.EnumProperty(
        name="Instance Object",
        description="Object to instance on points",
        items=get_object_items,
        update=update_instance_object
    )
    scale_x: bpy.props.FloatProperty(
        name="Scale X",
        description="Scale of the instanced object on the X axis",
        default=1.0,
        min=0.0,
        max=10.0,
        update=update_instance_scale
    )
    scale_y: bpy.props.FloatProperty(
        name="Scale Y",
        description="Scale of the instanced object on the Y axis",
        default=1.0,
        min=0.0,
        max=10.0,
        update=update_instance_scale
    )
    scale_z: bpy.props.FloatProperty(
        name="Scale Z",
        description="Scale of the instanced object on the Z axis",
        default=1.0,
        min=0.0,
        max=10.0,
        update=update_instance_scale
    )

def create_default_cube():
    if "DefaultCube" not in bpy.data.objects:
        bpy.ops.mesh.primitive_cube_add(size=2)
        cube = bpy.context.active_object
        cube.name = "DefaultCube"
        cube.hide_viewport = True
        cube.hide_render = True
        collection = bpy.data.collections.get("Instance Example")
        if collection is None:
            collection = bpy.data.collections.new("Instance Example")
            bpy.context.scene.collection.children.link(collection)
        collection.objects.link(cube)
        bpy.context.collection.objects.unlink(cube)
    return bpy.data.objects["DefaultCube"]

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
    props = context.scene.easy_points_props

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

    group_input = None
    group_output = None
    for node in nodes:
        if node.type == 'GROUP_INPUT':
            group_input = node
        elif node.type == 'GROUP_OUTPUT':
            group_output = node

    if group_input is None:
        group_input = nodes.new('NodeGroupInput')
        group_input.location = (-300, 0)

    if group_output is None:
        group_output = nodes.new('NodeGroupOutput')
        group_output.location = (900, 0)

    distribute_points = nodes.new(type="GeometryNodeDistributePointsOnFaces")
    distribute_points.location = (0, 0)

    set_point_radius = nodes.new(type="GeometryNodeSetPointRadius")
    set_point_radius.location = (300, 0)

    set_material = nodes.new(type="GeometryNodeSetMaterial")
    set_material.location = (600, 0)

    if selected_object.active_material:
        set_material.inputs['Material'].default_value = selected_object.active_material
    else:
        default_material = bpy.data.materials.get("Material")
        if default_material is None:
            default_material = bpy.data.materials.new(name="Material")
        set_material.inputs['Material'].default_value = default_material

    links.new(group_input.outputs['Geometry'], distribute_points.inputs['Mesh'])
    links.new(distribute_points.outputs['Points'], set_point_radius.inputs['Points'])
    links.new(set_point_radius.outputs['Points'], set_material.inputs['Geometry'])
    links.new(set_material.outputs['Geometry'], group_output.inputs['Geometry'])

    distribute_points.inputs['Density'].default_value = props.density
    set_point_radius.inputs['Radius'].default_value = props.radius
    distribute_points.inputs['Seed'].default_value = props.random

def apply_mesh_to_points(context):
    selected_object = context.active_object
    props = context.scene.easy_points_props

    mesh = selected_object.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.verts.ensure_lookup_table()

    points = [v.co.copy() for v in bm.verts]
    bm.clear()

    point_cloud_mesh = bpy.data.meshes.new(name="PointCloud")
    point_cloud_obj = bpy.data.objects.new(name="PointCloud", object_data=point_cloud_mesh)
    context.collection.objects.link(point_cloud_obj)

    point_cloud_mesh.from_pydata(points, [], [])
    point_cloud_mesh.update()

    bpy.data.objects.remove(selected_object)
    selected_object = point_cloud_obj

    existing_modifier = None
    for mod in selected_object.modifiers:
        if mod.type == 'NODES':
            existing_modifier = mod
            break

    if existing_modifier is None:
        bpy.context.view_layer.objects.active = selected_object
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

    group_input = None
    group_output = None
    for node in nodes:
        if node.type == 'GROUP_INPUT':
            group_input = node
        elif node.type == 'GROUP_OUTPUT':
            group_output = node

    if group_input is None:
        group_input = nodes.new('NodeGroupInput')
        group_input.location = (-300, 0)

    if group_output is None:
        group_output = nodes.new('NodeGroupOutput')
        group_output.location = (600, 0)

    mesh_to_points = nodes.new(type="GeometryNodeMeshToPoints")
    mesh_to_points.location = (-200, 0)

    object_info = nodes.new(type="GeometryNodeObjectInfo")
    object_info.location = (-50, 0)

    instance_on_points = nodes.new(type="GeometryNodeInstanceOnPoints")
    instance_on_points.location = (100, 0)

    set_material = nodes.new(type="GeometryNodeSetMaterial")
    set_material.location = (250, 0)

    if selected_object.material_slots:
        set_material.inputs['Material'].default_value = selected_object.material_slots[0].material
    else:
        set_material.inputs['Material'].default_value = create_default_material()

    links.new(group_input.outputs['Geometry'], mesh_to_points.inputs['Mesh'])
    links.new(mesh_to_points.outputs['Points'], instance_on_points.inputs['Points'])
    links.new(object_info.outputs['Geometry'], instance_on_points.inputs['Instance'])
    links.new(instance_on_points.outputs['Instances'], set_material.inputs['Geometry'])
    links.new(set_material.outputs['Geometry'], group_output.inputs['Geometry'])

    mesh_to_points.inputs['Radius'].default_value = props.radius

    instance_obj = bpy.data.objects.get(props.instance_object)
    if instance_obj:
        object_info.inputs['Object'].default_value = instance_obj

    instance_on_points.mute = not props.enable_points

class OBJECT_OT_add_points_modifier(bpy.types.Operator):
    bl_idname = "object.add_points_modifier"
    bl_label = "Add Points"
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
    bl_label = "Add Mesh To Points"
    bl_description = "Add mesh to points"
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

class OBJECT_OT_toggle_modifiers(bpy.types.Operator):
    bl_idname = "object.toggle_modifiers"
    bl_label = "Toggle Modifiers"
    bl_description = "Turn all modifiers on or off"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        selected_object = context.active_object
        if selected_object and selected_object.type == 'MESH':
            for mod in selected_object.modifiers:
                mod.show_viewport = not mod.show_viewport
            self.report({'INFO'}, "Toggled all modifiers")
        else:
            self.report({'ERROR'}, "No mesh object selected")
            return {'CANCELLED'}
        return {'FINISHED'}

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
        props = context.scene.easy_points_props
        selected_object = context.active_object

        layout.label(text="Easy Points v1.0.20", icon='MESH_CIRCLE')

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
                layout.prop(props, "density", text="Density")
                layout.prop(props, "radius", text="Point Size")
                layout.prop(props, "random", text="Random Seed")
                layout.operator("object.reset_model", text="Reset", icon='FILE_REFRESH')
            elif selected_feature == 'MESH_TO_POINTS':
                layout.label(text="Step 2: Point Settings")
                layout.prop(props, "radius", text="Point Size")
                layout.prop(props, "enable_points", text="Enable Points Instancing", icon='TOOL_SETTINGS')
                if props.enable_points:
                    box = layout.box()
                    box.label(text="Instance Settings", icon='MODIFIER')
                    box.prop(props, "instance_object", text="Instance Object")
                    box.prop(props, "scale_x", text="Scale X")
                    box.prop(props, "scale_y", text="Scale Y")
                    box.prop(props, "scale_z", text="Scale Z")

            layout.separator()
            layout.operator("object.toggle_modifiers", text="Toggle Modifiers", icon='PAUSE')
            layout.operator("object.return_to_main", text="Return", icon='LOOP_BACK')

        row = layout.row()
        row.alignment = 'RIGHT'
        row.label(text="Made by marv.os")

classes = (
    EasyPointsProperties,
    OBJECT_OT_add_points_modifier,
    OBJECT_OT_add_mesh_to_points,
    OBJECT_OT_toggle_modifiers,
    OBJECT_OT_reset_model,
    OBJECT_OT_return_to_main,
    OBJECT_PT_easy_points_panel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.easy_points_props = bpy.props.PointerProperty(type=EasyPointsProperties)
    if "DefaultCube" not in bpy.data.objects:
        create_default_cube()
    bpy.context.scene.easy_points_props.instance_object = 'DefaultCube'
    print("Easy Points plugin registered")

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.easy_points_props
    print("Easy Points plugin unregistered")

if __name__ == "__main__":
    register()
