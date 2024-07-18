bl_info = {
    "name": "Easy Points",
    "blender": (3, 0, 0),
    "category": "Object",
    "version": (1, 0, 10),
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
from bpy_extras.io_utils import ExportHelper

# Update function for the radius property
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

# Property group for storing custom properties
class EasyPointsProperties(bpy.types.PropertyGroup):
    radius: bpy.props.FloatProperty(
        name="Point Size",
        description="Size of the Points",
        default=0.05,
        min=0.0,
        max=100.0,
        update=update_geometry_node
    )

def create_default_material():
    material = bpy.data.materials.get("EasyPointsMaterial")
    if material is None:
        material = bpy.data.materials.new(name="EasyPointsMaterial")
        material.use_nodes = True
        bsdf = material.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs['Base Color'].default_value = (1.0, 0.0, 0.0, 1.0)
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
        
        # Material properties
        layout.prop(context.object.active_material, "diffuse_color", text="Base Color")

# Operator to set the renderer to Cycles
class OBJECT_OT_set_renderer_cycles(bpy.types.Operator):
    bl_idname = "object.set_renderer_cycles"
    bl_label = "Enable Cycles"
    bl_description = "Set the renderer to Cycles"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        context.scene.render.engine = 'CYCLES'
        self.report({'INFO'}, "Renderer set to Cycles")
        return {'FINISHED'}

# Operator to add a geometry nodes modifier, assign a new node group, and add a "Mesh to Points" node
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
        
        # Convert to point cloud
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
        
        # Add Geometry Nodes Modifier
        selected_object = point_cloud_obj
        props = context.scene.easy_points_props
        
        # Check if the selected object already has a geometry nodes modifier
        existing_modifier = None
        for mod in selected_object.modifiers:
            if mod.type == 'NODES':
                existing_modifier = mod
                break

        if existing_modifier is None:
            # Ensure correct context for adding a modifier
            bpy.context.view_layer.objects.active = selected_object
            bpy.ops.object.modifier_add(type='NODES')
            modifier = selected_object.modifiers[-1]
        else:
            modifier = existing_modifier

        # Assign a new geometry node group if not already assigned
        if modifier.node_group is None:
            bpy.ops.node.new_geometry_node_group_assign()
            node_group = modifier.node_group
        else:
            node_group = modifier.node_group

        if node_group is None:
            self.report({'ERROR'}, "Node group could not be created")
            return {'CANCELLED'}
        
        # Add nodes in the node group
        nodes = node_group.nodes
        links = node_group.links
        
        # Check if Group Input and Output nodes already exist
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

        # Add Mesh to Points node if it does not already exist
        mesh_to_points = None
        for node in nodes:
            if node.bl_idname == "GeometryNodeMeshToPoints":
                mesh_to_points = node
                break

        if mesh_to_points is None:
            mesh_to_points = nodes.new(type="GeometryNodeMeshToPoints")
            mesh_to_points.location = (-100, 0)
        
        # Add Set Material node
        set_material = nodes.new(type="GeometryNodeSetMaterial")
        set_material.location = (200, 0)
        
        # Use the existing material or create a new default material
        if selected_object.active_material:
            set_material.inputs['Material'].default_value = selected_object.active_material
        else:
            set_material.inputs['Material'].default_value = create_default_material()
        
        # Link nodes if not already linked
        if not any(link.from_node == group_input and link.to_node == mesh_to_points for link in links):
            links.new(group_input.outputs['Geometry'], mesh_to_points.inputs['Mesh'])
        if not any(link.from_node == mesh_to_points and link.to_node == set_material for link in links):
            links.new(mesh_to_points.outputs['Points'], set_material.inputs['Geometry'])
        if not any(link.from_node == set_material and link.to_node == group_output for link in links):
            links.new(set_material.outputs['Geometry'], group_output.inputs['Geometry'])

        # Set the radius of the Mesh to Points node
        mesh_to_points.inputs['Radius'].default_value = props.radius
        
        self.report({'INFO'}, "Points added to the object")
        return {'FINISHED'}

# Panel to hold the buttons and properties
class OBJECT_PT_easy_points_panel(bpy.types.Panel):
    bl_idname = "OBJECT_PT_easy_points_panel"
    bl_label = "Easy Points"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Easy Points'
    
    def draw(self, context):
        layout = self.layout
        props = context.scene.easy_points_props
        selected_object = context.active_object

        # Title
        layout.label(text="Easy Points v1.0.10", icon='MESH_CIRCLE')
        layout.label(text="Made by marv.os")

        # Object information box
        if selected_object and selected_object.type == 'MESH':
            box = layout.box()
            box.label(text=f"Object: {selected_object.name}")
            box.label(text=f"Polygons: {len(selected_object.data.polygons)}")

        # Step 1: Enable Cycles
        layout.label(text="Step 1: Renderer")
        layout.operator("object.set_renderer_cycles", text="Enable Cycles", icon='SHADING_RENDERED')

        # Step 2: Add Points
        layout.label(text="Step 2: Add Points")
        layout.operator("object.add_points_modifier", text="Add Points", icon='OUTLINER_OB_POINTCLOUD')

        # Step 3: Point Size
        layout.label(text="Step 3: Point Settings")
        layout.prop(props, "radius", text="Point Size")

classes = (
    EasyPointsProperties,
    OBJECT_OT_set_renderer_cycles,
    OBJECT_OT_add_points_modifier,
    MATERIAL_PT_easy_points,
    OBJECT_PT_easy_points_panel,
)

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
