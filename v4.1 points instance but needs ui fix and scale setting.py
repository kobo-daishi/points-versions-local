bl_info = {
    "name": "Easy Points",
    "blender": (3, 0, 0),
    "category": "Object",
    "version": (1, 0, 11),
    "author": "@marv.os",
    "location": "View3D > Sidebar > Easy Points Tab",
    "description": "An addon to convert mesh to points and apply various operations",
    "warning": "",
    "wiki_url": "",
    "tracker_url": "https://www.instagram.com/marv.os",
    "support": "COMMUNITY",
    "doc_url": "",
}

import bpy
import bmesh

def create_default_cube():
    if "DefaultCube" not in bpy.data.objects:
        bpy.ops.mesh.primitive_cube_add(size=2)
        cube = bpy.context.active_object
        cube.name = "DefaultCube"
        return cube
    return bpy.data.objects["DefaultCube"]

def update_geometry_node(self, context):
    selected_object = context.active_object
    if selected_object and selected_object.type == 'MESH':
        for mod in selected_object.modifiers:
            if mod.type == 'NODES':
                node_group = mod.node_group
                if node_group:
                    for node in node_group.nodes:
                        if node.bl_idname == "GeometryNodeMeshToPoints":
                            node.inputs['Radius'].default_value = self.radius
                            break

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

def get_object_items(self, context):
    items = [(obj.name, obj.name, "") for obj in bpy.data.objects if obj.type == 'MESH']
    return items

class EasyPointsProperties(bpy.types.PropertyGroup):
    radius: bpy.props.FloatProperty(
        name="Point Size",
        description="Size of the Points",
        default=0.05,
        min=0.0,
        max=100.0,
        update=update_geometry_node
    )
    instance_object: bpy.props.EnumProperty(
        name="Instance Object",
        description="Object to instance on points",
        items=get_object_items,
        update=update_instance_object
    )
    enable_points: bpy.props.BoolProperty(
        name="Enable Points",
        description="Enable or disable points instancing",
        default=True,
        update=update_mute_instance_on_points
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

class MATERIAL_PT_easy_points(bpy.types.Panel):
    bl_label = "Easy Points Material"
    bl_idname = "MATERIAL_PT_easy_points"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "material"
    
    @classmethod
    def poll(cls, context):
        return context.active_object is not None and context.active_object.type == 'MESH'
    
    def draw(self, context):
        layout = self.layout
        props = context.scene.easy_points_props
        layout.prop(context.object.active_material, "diffuse_color", text="Base Color")

class OBJECT_OT_set_renderer_cycles(bpy.types.Operator):
    bl_idname = "object.set_renderer_cycles"
    bl_label = "Enable Cycles"
    bl_description = "Set the renderer to Cycles"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        context.scene.render.engine = 'CYCLES'
        self.report({'INFO'}, "Renderer set to Cycles")
        return {'FINISHED'}

class OBJECT_OT_add_points_modifier(bpy.types.Operator):
    bl_idname = "object.add_points_modifier"
    bl_label = "Add Points"
    bl_description = "Add points to the object"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        selected_object = context.active_object
        
        if selected_object is None:
            self.report({'ERROR'}, "No object selected")
            return {'CANCELLED'}
        
        if selected_object.type != 'MESH':
            self.report({'ERROR'}, "Selected object is not a mesh")
            return {'CANCELLED'}
        
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
        props = context.scene.easy_points_props
        
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
            self.report({'ERROR'}, "Node group could not be created")
            return {'CANCELLED'}
        
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

        mesh_to_points = None
        for node in nodes:
            if node.bl_idname == "GeometryNodeMeshToPoints":
                mesh_to_points = node
                break

        if mesh_to_points is None:
            mesh_to_points = nodes.new(type="GeometryNodeMeshToPoints")
            mesh_to_points.location = (-200, 0)
            mesh_to_points.name = "Mesh To Points 1"

        object_info = None
        for node in nodes:
            if node.bl_idname == "GeometryNodeObjectInfo":
                object_info = node
                break
        
        if object_info is None:
            object_info = nodes.new(type="GeometryNodeObjectInfo")
            object_info.location = (-50, 0)
            object_info.name = "Object Info 1"
        
        instance_on_points = nodes.new(type="GeometryNodeInstanceOnPoints")
        instance_on_points.location = (100, 0)
        instance_on_points.name = "Instance On Points 1"

        set_material = nodes.new(type="GeometryNodeSetMaterial")
        set_material.location = (250, 0)
        set_material.name = "Set Material 1"
        
        if selected_object.material_slots:
            set_material.inputs['Material'].default_value = selected_object.material_slots[0].material
        else:
            set_material.inputs['Material'].default_value = create_default_material()
        
        if not any(link.from_node == group_input and link.to_node == mesh_to_points for link in links):
            links.new(group_input.outputs['Geometry'], mesh_to_points.inputs['Mesh'])
        if not any(link.from_node == mesh_to_points and link.to_node == instance_on_points for link in links):
            links.new(mesh_to_points.outputs['Points'], instance_on_points.inputs['Points'])
        if not any(link.from_node == object_info and link.to_node == instance_on_points for link in links):
            links.new(object_info.outputs['Geometry'], instance_on_points.inputs['Instance'])
        if not any(link.from_node == instance_on_points and link.to_node == set_material for link in links):
            links.new(instance_on_points.outputs['Instances'], set_material.inputs['Geometry'])
        if not any(link.from_node == set_material and link.to_node == group_output for link in links):
            links.new(set_material.outputs['Geometry'], group_output.inputs['Geometry'])

        mesh_to_points.inputs['Radius'].default_value = props.radius
        
        instance_obj = bpy.data.objects.get(props.instance_object)
        if instance_obj:
            object_info.inputs['Object'].default_value = instance_obj
        
        instance_on_points.mute = not props.enable_points

        return {'FINISHED'}

class OBJECT_PT_easy_points(bpy.types.Panel):
    bl_label = "Easy Points"
    bl_idname = "OBJECT_PT_easy_points"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Easy Points'
    
    def draw(self, context):
        layout = self.layout
        props = context.scene.easy_points_props

        col = layout.column(align=True)
        col.label(text="Convert Mesh to Points")
        col.prop(props, "radius")
        col.prop(props, "instance_object")
        col.prop(props, "enable_points", text="Enable Points Instancing")
        col.operator("object.add_points_modifier", text="Add Points")
        col.operator("object.set_renderer_cycles", text="Enable Cycles")

classes = [
    EasyPointsProperties,
    OBJECT_PT_easy_points,
    OBJECT_OT_add_points_modifier,
    OBJECT_OT_set_renderer_cycles,
    MATERIAL_PT_easy_points,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.easy_points_props = bpy.props.PointerProperty(type=EasyPointsProperties)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.easy_points_props

if __name__ == "__main__":
    register()
