bl_info = {
    "name": "Simple Mesh to Point Cloud Converter",
    "blender": (2, 80, 0),
    "category": "Object",
}

import bpy
import bmesh
from bpy_extras.io_utils import ExportHelper

class ConvertToPointCloudOperator(bpy.types.Operator):
    bl_idname = "object.convert_to_point_cloud"
    bl_label = "Convert to Point Cloud"
    
    def execute(self, context):
        obj = context.active_object
        if obj is None or obj.type != 'MESH':
            self.report({'ERROR'}, "No mesh object selected")
            return {'CANCELLED'}
        
        mesh = obj.data
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
        
        bpy.data.objects.remove(obj)
        
        return {'FINISHED'}

class ExportPointCloudOperator(bpy.types.Operator, ExportHelper):
    bl_idname = "export_mesh.ply"
    bl_label = "Export Point Cloud"
    filename_ext = ".ply"
    
    def execute(self, context):
        obj = context.active_object
        if obj is None or obj.type != 'MESH':
            self.report({'ERROR'}, "No point cloud object selected")
            return {'CANCELLED'}
        
        bpy.ops.export_mesh.ply(filepath=self.filepath, use_selection=True, use_mesh_modifiers=False)
        return {'FINISHED'}

class AdjustPointSizeOperator(bpy.types.Operator):
    bl_idname = "object.adjust_point_size"
    bl_label = "Adjust Point Size"
    
    def execute(self, context):
        obj = context.active_object
        if obj is None or obj.type != 'MESH':
            self.report({'ERROR'}, "No point cloud object selected")
            return {'CANCELLED'}
        
        mesh = obj.data
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bm.verts.ensure_lookup_table()
        
        size = context.scene.point_size
        for v in bm.verts:
            v.co *= size
        
        bm.to_mesh(mesh)
        mesh.update()
        
        return {'FINISHED'}

class SimpleMeshToPointCloudPanel(bpy.types.Panel):
    bl_label = "Mesh to Point Cloud"
    bl_idname = "OBJECT_PT_mesh_to_point_cloud"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Simple Converter'
    
    def draw(self, context):
        layout = self.layout
        layout.operator("object.convert_to_point_cloud", text="Convert to Point Cloud")
        layout.operator("export_mesh.ply", text="Export Point Cloud")
        
        layout.prop(context.scene, "point_size", text="Point Size")
        layout.operator("object.adjust_point_size", text="Adjust Point Size")

def register():
    bpy.utils.register_class(ConvertToPointCloudOperator)
    bpy.utils.register_class(ExportPointCloudOperator)
    bpy.utils.register_class(AdjustPointSizeOperator)
    bpy.utils.register_class(SimpleMeshToPointCloudPanel)
    
    bpy.types.Scene.point_size = bpy.props.FloatProperty(
        name="Point Size",
        description="Size of the points in the point cloud",
        default=1.0,
        min=0.01,
        max=10.0
    )

def unregister():
    bpy.utils.unregister_class(ConvertToPointCloudOperator)
    bpy.utils.unregister_class(ExportPointCloudOperator)
    bpy.utils.unregister_class(AdjustPointSizeOperator)
    bpy.utils.unregister_class(SimpleMeshToPointCloudPanel)
    
    del bpy.types.Scene.point_size

if __name__ == "__main__":
    register()
