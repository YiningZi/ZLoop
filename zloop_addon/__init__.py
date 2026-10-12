bl_info = {
    "name": "ZLoop 环线精确测量与缩放",
    "author": "YiningZi - Enhanced Version",
    "version": (2, 2, 0),
    "blender": (4, 4, 0),
    "location": "View3D > Sidebar > ZLoop",
    "description": "用于精确测量环线周长并进行比例缩放的建模工具",
    "warning": "",
    "doc_url": "",
    "category": "Mesh",
}

import bpy
import bmesh
from mathutils import Vector, Matrix
import math
from bpy.props import FloatProperty, EnumProperty, BoolProperty, IntProperty

class ZLOOP_OT_scale_precise(bpy.types.Operator):
    """按目标周长精确缩放选中的环线"""
    bl_idname = "mesh.zloop_scale_precise"
    bl_label = "应用环线缩放"
    bl_description = "将选中的完整环线缩放到目标周长"
    bl_options = {'REGISTER', 'UNDO'}
    
    # 目标周长控制
    target_length: FloatProperty(
        name="目标周长",
        description="环线缩放后的目标总长度",
        default=50,
        min=0.001,
        precision=3,
        unit='LENGTH'
    )
    
    # 衰减控制
    falloff_radius: FloatProperty(
        name="衰减半径",
        description="比例编辑影响范围的半径",
        default=15,
        min=0.0,
        max=10000.0,
        precision=3,
        unit='LENGTH'
    )
    
    falloff_shape: EnumProperty(
        name="衰减类型",
        description="比例编辑的影响衰减方式",
        items=[
            ('SMOOTH', '平滑', '自然平滑的过渡'),
            ('SPHERE', '球形', '球形衰减'),
            ('ROOT', '根式', '平方根衰减'),
            ('INVERSE_SQUARE', '反平方', '反平方衰减'),
            ('SHARP', '锐利', '快速收窄的衰减'),
            ('LINEAR', '线性', '线性衰减'),
            ('CONSTANT', '恒定', '整个影响范围保持恒定')
        ],
        default='SMOOTH'
    )
    
    # 变换约束
    constraint_mode: EnumProperty(
        name="缩放方向",
        description="环线缩放所使用的坐标方向",
        items=[
            ('NORMAL', '法线', '沿表面法线方向缩放'),
            ('GLOBAL', '全局', '使用全局坐标方向'),
            ('LOCAL', '局部', '使用物体局部坐标方向'),
            ('VIEW', '视图', '相对于当前视图方向')
        ],
        default='NORMAL'
    )
    
    # 高级选项
    use_even_offset: BoolProperty(
        name="均匀偏移",
        description="尽量保持环线顶点间距均匀",
        default=False
    )
    
    preserve_shape: BoolProperty(
        name="保持形状",
        description="缩放时尽量保持原有轮廓形状",
        default=True
    )
    
    auto_falloff: BoolProperty(
        name="自动衰减",
        description="根据环线曲率和相邻网格间距自动计算局部衰减半径",
        default=True
    )

    use_connected: BoolProperty(
        name="仅影响相连项",
        description="沿网格连接计算衰减，避免影响空间上靠近的其他部位；半径过大时仍可能经掌部影响相邻手指",
        default=True
    )

    @classmethod
    def poll(cls, context):
        return (context.mode == 'EDIT_MESH' and 
                context.edit_object and 
                context.edit_object.type == 'MESH')

    def execute(self, context):
        obj = context.edit_object
        original_settings = None
        
        try:
            # 获取物体的世界变换矩阵
            world_matrix = obj.matrix_world
            scale_matrix = world_matrix.to_scale()
            
            # 初始化BMesh
            bm = bmesh.from_edit_mesh(obj.data)
            bm.edges.ensure_lookup_table()
            bm.verts.ensure_lookup_table()
            
            # 验证选择
            selected_edges = [e for e in bm.edges if e.select]
            if not selected_edges:
                self.report({'ERROR'}, "请先选择环线边")
                return {'CANCELLED'}
                
            # 验证边环
            edge_loop = self.get_edge_loop(selected_edges)
            if not edge_loop:
                self.report({'ERROR'}, "当前选择不是完整有效的环线")
                return {'CANCELLED'}
            
            # 计算当前周长（考虑物体缩放）
            current_perimeter = self.calculate_world_perimeter(edge_loop, world_matrix)
            
            if current_perimeter <= 0.001:
                self.report({'ERROR'}, "环线周长无效，无法进行缩放")
                return {'CANCELLED'}
            
            # 计算目标周长（转换到物体本地空间）
            avg_scale = (scale_matrix.x + scale_matrix.y + scale_matrix.z) / 3.0
            target_local = self.target_length / avg_scale
            scale_factor = target_local / (current_perimeter / avg_scale)
            
            # 自动计算衰减半径
            if self.auto_falloff:
                self.falloff_radius = self.calculate_auto_falloff(
                    edge_loop, scale_factor, world_matrix
                )
            
            # 备份原始设置
            original_settings = self.backup_transform_settings(context)
            
            # 配置变换设置
            self.configure_transform_settings(context)
            
            # 执行缩放
            self.perform_scaling(context, scale_factor)
            
            # 验证结果
            bm = bmesh.from_edit_mesh(obj.data)
            selected_edges = [e for e in bm.edges if e.select]
            edge_loop = self.get_edge_loop(selected_edges)
            if edge_loop:
                new_perimeter = self.calculate_world_perimeter(edge_loop, world_matrix)
                accuracy = abs(new_perimeter - self.target_length) / self.target_length * 100
                radius_hint = f"，自动半径 {self.falloff_radius:.3f}" if self.auto_falloff else ""
                self.report({'INFO'}, f"环线已缩放：{current_perimeter:.3f} → {new_perimeter:.3f}（目标 {self.target_length:.3f}，精度 {100-accuracy:.1f}%{radius_hint}）")
            
        except Exception as e:
            self.report({'ERROR'}, f"缩放失败：{str(e)}")
            return {'CANCELLED'}
        finally:
            # 成功、失败或提前退出均恢复用户原有的比例编辑设置。
            if original_settings is not None:
                self.restore_transform_settings(context, original_settings)
        
        # 更新网格
        bmesh.update_edit_mesh(obj.data)
        return {'FINISHED'}
    
    def get_edge_loop(self, selected_edges):
        """获取有效的边环"""
        if len(selected_edges) < 3:
            return None
            
        # 构建顶点连接图
        vert_connections = {}
        for edge in selected_edges:
            v1, v2 = edge.verts
            vert_connections.setdefault(v1, []).append(v2)
            vert_connections.setdefault(v2, []).append(v1)
        
        # 检查是否每个顶点都恰好连接两条边
        for vert, connections in vert_connections.items():
            if len(connections) != 2:
                return None
        
        # 构建有序的边环
        if not vert_connections:
            return None
            
        start_vert = next(iter(vert_connections.keys()))
        ordered_loop = [start_vert]
        current_vert = vert_connections[start_vert][0]
        
        while current_vert != start_vert and len(ordered_loop) < len(vert_connections):
            ordered_loop.append(current_vert)
            connections = vert_connections[current_vert]
            prev_vert = ordered_loop[-2] if len(ordered_loop) > 1 else None
            next_vert = connections[0] if connections[1] == prev_vert else connections[1]
            current_vert = next_vert
        
        if len(ordered_loop) != len(vert_connections):
            return None
            
        return ordered_loop
    
    def calculate_world_perimeter(self, edge_loop, world_matrix):
        """计算世界空间中的周长"""
        total_length = 0.0
        for i in range(len(edge_loop)):
            v1 = edge_loop[i]
            v2 = edge_loop[(i + 1) % len(edge_loop)]
            
            # 转换到世界坐标
            world_v1 = world_matrix @ v1.co
            world_v2 = world_matrix @ v2.co
            
            total_length += (world_v2 - world_v1).length
            
        return total_length
    
    def calculate_auto_falloff(self, edge_loop, scale_factor, world_matrix=None):
        """根据曲率和局部拓扑间距计算局部、平滑的衰减半径。

        半径以环线附近的实际网格尺度为上限：曲率越大，半径越小；
        环线与相邻网格层的间距越大，半径可以适当放宽，但不会扩散到整个模型。
        """
        if len(edge_loop) < 3:
            return max(0.001, self.falloff_radius)

        def median(values):
            values = sorted(value for value in values if value > 1e-8)
            if not values:
                return 0.0
            middle = len(values) // 2
            if len(values) % 2:
                return values[middle]
            return (values[middle - 1] + values[middle]) * 0.5

        if world_matrix is None:
            coords = [vert.co.copy() for vert in edge_loop]
        else:
            coords = [world_matrix @ vert.co for vert in edge_loop]
        edge_lengths = [
            (coords[(index + 1) % len(coords)] - coords[index]).length
            for index in range(len(coords))
        ]
        median_edge_length = median(edge_lengths)
        if median_edge_length <= 1e-8:
            return 0.001

        # 用相邻边的转角估计局部曲率。转角越大，说明需要更短的影响范围。
        turn_angles = []
        for index, current in enumerate(coords):
            incoming = current - coords[index - 1]
            outgoing = coords[(index + 1) % len(coords)] - current
            if incoming.length <= 1e-8 or outgoing.length <= 1e-8:
                continue
            cosine = incoming.normalized().dot(outgoing.normalized())
            cosine = max(-1.0, min(1.0, cosine))
            turn_angles.append(math.acos(cosine))

        average_turn = sum(turn_angles) / len(turn_angles) if turn_angles else 0.0
        curvature_ratio = max(0.0, min(1.0, average_turn / math.pi))
        curvature_factor = max(0.55, min(1.15, 1.15 - curvature_ratio * 0.95))

        # 读取每个环线顶点到下一层未选中顶点的最近距离，得到局部网格尺度。
        loop_vertices = set(edge_loop)
        neighbour_gaps = []
        for vert in edge_loop:
            distances = []
            for edge in vert.link_edges:
                other = edge.other_vert(vert)
                if other not in loop_vertices:
                    gap = (other.co - vert.co).length
                    if gap > 1e-8:
                        distances.append(gap)
            nearest_gap = min(distances) if distances else 0.0
            if nearest_gap > 1e-8:
                neighbour_gaps.append(nearest_gap)

        median_neighbour_gap = median(neighbour_gaps)
        # 基础半径覆盖约 2~3 层邻近边，随后按局部间距和曲率限制。
        base_radius = median_edge_length * 2.5
        if median_neighbour_gap > 1e-8:
            base_radius = max(base_radius, median_neighbour_gap * 0.85)
            local_cap = median_neighbour_gap * 2.25
        else:
            local_cap = median_edge_length * 5.0

        scale_modifier = max(0.8, min(1.45, 0.8 + abs(scale_factor - 1.0) * 0.65))
        radius = base_radius * curvature_factor * scale_modifier
        radius = min(radius, local_cap)
        radius = max(radius, median_edge_length * 1.25)

        return max(0.001, radius)
    
    def backup_transform_settings(self, context):
        """备份当前变换设置"""
        ts = context.scene.tool_settings
        return {
            'proportional': ts.use_proportional_edit,
            'connected': ts.use_proportional_connected,
            'projected': ts.use_proportional_projected,
            'proportional_size': ts.proportional_size,
            'falloff_type': ts.proportional_edit_falloff,
            'pivot_point': ts.transform_pivot_point,
        }
    
    def configure_transform_settings(self, context):
        """配置变换设置"""
        ts = context.scene.tool_settings
        ts.use_proportional_edit = True
        ts.use_proportional_connected = self.use_connected
        ts.use_proportional_projected = False
        ts.proportional_size = self.falloff_radius
        ts.proportional_edit_falloff = self.falloff_shape
        ts.transform_pivot_point = 'MEDIAN_POINT'
    
    def restore_transform_settings(self, context, settings):
        """恢复变换设置"""
        ts = context.scene.tool_settings
        ts.use_proportional_edit = settings['proportional']
        ts.use_proportional_connected = settings['connected']
        ts.use_proportional_projected = settings['projected']
        ts.proportional_size = settings['proportional_size']
        ts.proportional_edit_falloff = settings['falloff_type']
        ts.transform_pivot_point = settings['pivot_point']
    
    def perform_scaling(self, context, scale_factor):
        """执行缩放操作"""
        constraint_axis = (False, False, False)
        
        if self.constraint_mode == 'NORMAL':
            orient_type = 'NORMAL'
        else:
            orient_type = self.constraint_mode
        
        bpy.ops.transform.resize(
            value=(scale_factor, scale_factor, scale_factor),
            orient_type=orient_type,
            constraint_axis=constraint_axis,
            use_proportional_edit=True,
            use_proportional_connected=self.use_connected,
            use_proportional_projected=False,
            proportional_edit_falloff=self.falloff_shape,
            proportional_size=self.falloff_radius
        )

class ZLOOP_OT_analyze_loop(bpy.types.Operator):
    """测量当前选择的环线"""
    bl_idname = "mesh.zloop_analyze"
    bl_label = "测量当前环线"
    bl_description = "统计所选环线的边数、总长度和平均边长"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        obj = context.edit_object
        if not obj:
            self.report({'ERROR'}, "请在编辑模式下选择一个网格物体")
            return {'CANCELLED'}
            
        bm = bmesh.from_edit_mesh(obj.data)
        selected_edges = [e for e in bm.edges if e.select]
        
        if not selected_edges:
            self.report({'INFO'}, "当前没有选择任何边")
            return {'FINISHED'}
        
        # 计算基本信息
        world_matrix = obj.matrix_world
        total_length = 0.0
        
        for edge in selected_edges:
            v1_world = world_matrix @ edge.verts[0].co
            v2_world = world_matrix @ edge.verts[1].co
            total_length += (v2_world - v1_world).length
        
        edge_count = len(selected_edges)
        avg_length = total_length / edge_count if edge_count > 0 else 0
        
        self.report({'INFO'}, 
                   f"环线测量：{edge_count} 条边，总长度 {total_length:.3f}，平均边长 {avg_length:.3f}")
        
        return {'FINISHED'}

class ZLOOP_PT_main_panel(bpy.types.Panel):
    """ZLoop 主工具面板"""
    bl_label = "ZLoop 环线工具"
    bl_idname = "ZLOOP_PT_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'ZLoop'
    
    @classmethod
    def poll(cls, context):
        # 面板始终显示，避免用户因模式或选择状态找不到工具按钮。
        return True
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        layout.use_property_split = True
        layout.use_property_decorate = False

        if context.active_object is None or context.active_object.type != 'MESH':
            status = layout.box()
            status.alert = True
            status.label(text="请先选择一个网格物体", icon='ERROR')
        elif context.mode != 'EDIT_MESH':
            status = layout.box()
            status.alert = True
            status.label(text="请进入编辑模式后选择完整环线", icon='ERROR')

        # 标题区
        header = layout.box()
        row = header.row()
        row.scale_y = 1.25
        row.label(text="环线测量与修改", icon='MESH_DATA')
        header.label(text="选择完整环线后设置目标周长", icon='INFO')

        # 目标周长
        box = layout.box()
        box.label(text="目标尺寸", icon='ARROW_LEFTRIGHT')
        box.prop(scene, "zloop_target_length")

        # 缩放方向
        box = layout.box()
        box.label(text="缩放约束", icon='CONSTRAINT')
        box.prop(scene, "zloop_constraint_mode")

        # 比例编辑衰减
        box = layout.box()
        box.label(text="比例衰减", icon='SMOOTHCURVE')
        box.prop(scene, "zloop_use_connected")
        if scene.zloop_use_connected:
            hint = box.column(align=True)
            hint.use_property_split = False
            hint.label(text="沿网格连接限定影响范围", icon='INFO')
            hint.label(text="半径过大仍可能影响邻指")
        box.prop(scene, "zloop_auto_falloff")
        row = box.row()
        row.enabled = not scene.zloop_auto_falloff
        row.prop(scene, "zloop_falloff_radius")
        box.prop(scene, "zloop_falloff_shape")

        # 高级选项
        box = layout.box()
        box.label(text="高级选项", icon='PREFERENCES')
        box.prop(scene, "zloop_preserve_shape")
        box.prop(scene, "zloop_use_even_offset")

        # 操作按钮
        layout.separator(factor=0.5)
        action = layout.row()
        action.scale_y = 1.35
        op = action.operator("mesh.zloop_scale_precise",
                             text="应用环线缩放", icon='FULLSCREEN_ENTER')
        op.target_length = scene.zloop_target_length
        op.falloff_radius = scene.zloop_falloff_radius
        op.falloff_shape = scene.zloop_falloff_shape
        op.constraint_mode = scene.zloop_constraint_mode
        op.preserve_shape = scene.zloop_preserve_shape
        op.use_even_offset = scene.zloop_use_even_offset
        op.auto_falloff = scene.zloop_auto_falloff
        op.use_connected = scene.zloop_use_connected
        
        inspect = layout.row()
        inspect.scale_y = 1.1
        inspect.operator("mesh.zloop_analyze", text="测量当前环线", icon='VIEWZOOM')

class ZLOOP_PT_info_panel(bpy.types.Panel):
    """使用提示面板"""
    bl_label = "使用说明"
    bl_idname = "ZLOOP_PT_info"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'ZLoop'
    bl_parent_id = "ZLOOP_PT_main"
    bl_options = {'DEFAULT_CLOSED'}
    
    @classmethod
    def poll(cls, context):
        return True
    
    def draw(self, context):
        layout = self.layout
        
        layout.use_property_decorate = False
        box = layout.box()
        box.label(text="操作提示", icon='INFO')
        box.label(text="1. 在编辑模式下选择完整环线")
        box.label(text="2. 输入目标周长并选择缩放方向")
        box.label(text="3. 点击“应用环线缩放”执行修改")
        box.label(text="自动衰减适合大多数曲面模型")
        box.label(text="调整指围建议开启“仅影响相连项”")
        box.label(text="掌部相通时请保持局部衰减半径")

        box = layout.box()
        box.label(text="常用快捷键", icon='KEYINGSET')
        box.label(text="Alt + 单击：选择环线")
        box.label(text="Ctrl + Z：撤销操作")

# 生命周期与缓存清理
_CLASSES = (
    ZLOOP_OT_scale_precise,
    ZLOOP_OT_analyze_loop,
    ZLOOP_PT_main_panel,
    ZLOOP_PT_info_panel,
)

# Blender 用 RNA 标识符存储类；它不一定等于 Python 类名。
_CLASS_REGISTRY = (
    (bpy.types.Operator, "MESH_OT_zloop_scale_precise"),
    (bpy.types.Operator, "MESH_OT_zloop_analyze"),
    (bpy.types.Panel, "ZLOOP_PT_main"),
    (bpy.types.Panel, "ZLOOP_PT_info"),
)

_SCENE_PROPERTY_NAMES = (
    "zloop_target_length",
    "zloop_falloff_radius",
    "zloop_falloff_shape",
    "zloop_constraint_mode",
    "zloop_preserve_shape",
    "zloop_use_even_offset",
    "zloop_auto_falloff",
    "zloop_use_connected",
)


def _unregister_stale_classes():
    """清理可能由旧版本或重复运行留下的 Blender 类注册。"""
    for base_type, rna_identifier in reversed(_CLASS_REGISTRY):
        registered_class = base_type.bl_rna_get_subclass_py(rna_identifier)
        if registered_class is None:
            continue
        bpy.utils.unregister_class(registered_class)


def _remove_scene_properties(clear_values=False):
    """删除旧版本在 Scene 上挂载的所有属性。"""
    for property_name in _SCENE_PROPERTY_NAMES:
        if hasattr(bpy.types.Scene, property_name):
            if clear_values:
                # Blender 5.1 的 RNA 存储不一定出现在 scene.keys() 中。
                for scene in bpy.data.scenes:
                    scene.property_unset(property_name)
            delattr(bpy.types.Scene, property_name)
        if clear_values:
            for scene in bpy.data.scenes:
                if property_name in scene:
                    del scene[property_name]


def _tag_all_areas_for_redraw():
    """让已打开的 Blender 区域立即刷新插件 UI。"""
    window_manager = getattr(bpy.context, "window_manager", None)
    if window_manager is None:
        return
    for window in window_manager.windows:
        screen = window.screen
        if screen:
            for area in screen.areas:
                area.tag_redraw()


def _cleanup_previous_registration():
    """注册新版本前，先清理旧注册，避免必须重启 Blender。"""
    _unregister_stale_classes()
    _remove_scene_properties()


# 属性定义
def update_target_length(self, context):
    """更新目标长度时的回调"""
    pass

def _register_scene_properties():
    # 目标周长
    bpy.types.Scene.zloop_target_length = FloatProperty(
        name="目标周长",
        description="环线缩放后的目标总长度",
        default=50,
        min=0.001,
        precision=3,
        unit='LENGTH',
        update=update_target_length
    )
    
    # 衰减半径
    bpy.types.Scene.zloop_falloff_radius = FloatProperty(
        name="衰减半径",
        description="比例编辑影响范围的半径",
        default=15,
        min=0.0,
        max=10000000.0,
        precision=3,
        unit='LENGTH'
    )
    
    # 衰减形状
    bpy.types.Scene.zloop_falloff_shape = EnumProperty(
        name="衰减类型",
        items=[
            ('SMOOTH', '平滑', '自然平滑的过渡'),
            ('SPHERE', '球形', '球形衰减'),
            ('ROOT', '根式', '平方根衰减'),
            ('INVERSE_SQUARE', '反平方', '反平方衰减'),
            ('SHARP', '锐利', '快速收窄的衰减'),
            ('LINEAR', '线性', '线性衰减'),
            ('CONSTANT', '恒定', '整个影响范围保持恒定')
        ],
        default='SMOOTH'
    )
    
    # 约束模式
    bpy.types.Scene.zloop_constraint_mode = EnumProperty(
        name="缩放方向",
        items=[
            ('NORMAL', '法线', '沿表面法线方向缩放'),
            ('GLOBAL', '全局', '使用全局坐标方向'),
            ('LOCAL', '局部', '使用物体局部坐标方向'),
            ('VIEW', '视图', '相对于当前视图方向')
        ],
        default='NORMAL'
    )
    
    # 高级选项
    bpy.types.Scene.zloop_preserve_shape = BoolProperty(
        name="保持形状",
        description="缩放时尽量保持原有轮廓形状",
        default=True
    )
    
    bpy.types.Scene.zloop_use_even_offset = BoolProperty(
        name="均匀偏移",
        description="尽量保持环线顶点间距均匀",
        default=False
    )
    
    bpy.types.Scene.zloop_auto_falloff = BoolProperty(
        name="自动衰减",
        description="根据环线曲率和相邻网格间距自动计算局部衰减半径",
        default=True
    )

    bpy.types.Scene.zloop_use_connected = BoolProperty(
        name="仅影响相连项",
        description="沿网格连接计算衰减，避免影响空间上靠近的其他部位；半径过大时仍可能经掌部影响相邻手指",
        default=True
    )
    

def register():
    print("Registering ZLoop V2.2...")
    _cleanup_previous_registration()
    try:
        _register_scene_properties()
        for cls in _CLASSES:
            bpy.utils.register_class(cls)
    except Exception:
        _cleanup_previous_registration()
        _tag_all_areas_for_redraw()
        raise
    _tag_all_areas_for_redraw()
    print("ZLoop V2.2 registered successfully!")

def unregister():
    print("Unregistering ZLoop V2.2...")
    _unregister_stale_classes()
    _remove_scene_properties(clear_values=True)
    _tag_all_areas_for_redraw()
    print("ZLoop V2.2 unregistered successfully!")

if __name__ == "__main__":
    register()
