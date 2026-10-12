# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 YiningZi (SeventhSlice)

"""Run with Blender --background --factory-startup --python-exit-code 1 --python this_file.

Uses actual mesh edits, including two nearby fingers joined at the palm.
No preferences or user files are modified.
"""
import math
from pathlib import Path
import types

import bpy
import bmesh


ROOT = Path(__file__).resolve().parents[1]


def load_addon(name):
    path = ROOT / "zloop_addon" / "__init__.py"
    module = types.ModuleType(name)
    exec(compile(path.read_text(encoding="utf-8"), str(path), "exec"), module.__dict__)
    return module


def settings_snapshot():
    ts = bpy.context.scene.tool_settings
    names = (
        "use_proportional_edit", "use_proportional_connected",
        "use_proportional_projected", "proportional_size",
        "proportional_edit_falloff", "transform_pivot_point",
    )
    return {name: getattr(ts, name) for name in names}


def make_fingers(joined=True):
    if bpy.context.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    sides, layers = 16, 21
    verts, faces = [], []
    for finger in range(2):
        start = len(verts)
        for layer in range(layers):
            for side in range(sides):
                angle = math.tau * side / sides
                verts.append((finger * 0.85 + 0.35 * math.cos(angle),
                              0.35 * math.sin(angle), layer * 0.25))
        for layer in range(layers - 1):
            for side in range(sides):
                a = start + layer * sides + side
                b = start + layer * sides + (side + 1) % sides
                faces.append((a, b, b + sides, a + sides))
    per_finger = sides * layers
    if joined:
        faces.append((0, 1, per_finger + 7, per_finger + 8))
    mesh = bpy.data.meshes.new("ConnectedFingers")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new("ConnectedFingers", mesh)
    bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_mode(type='EDGE')
    bpy.ops.mesh.select_all(action='DESELECT')
    bm = bmesh.from_edit_mesh(mesh)
    bm.verts.ensure_lookup_table()
    selected = set(range(14 * sides, 15 * sides))
    for edge in bm.edges:
        if all(vert.index in selected for vert in edge.verts):
            edge.select_set(True)
    bm.select_flush_mode()
    bmesh.update_edit_mesh(mesh)
    return obj, sides, per_finger


def run_geometry_case(connected, automatic, joined=True, explicit_option=True):
    obj, sides, per_finger = make_fingers(joined)
    bm = bmesh.from_edit_mesh(obj.data)
    before = {v.index: v.co.copy() for v in bm.verts}
    perimeter = sum(e.calc_length() for e in bm.edges if e.select)
    ts = bpy.context.scene.tool_settings
    ts.use_proportional_edit = False
    ts.use_proportional_connected = not connected
    ts.use_proportional_projected = True
    ts.proportional_size = 3.0
    ts.proportional_edit_falloff = 'LINEAR'
    ts.transform_pivot_point = 'CURSOR'
    saved = settings_snapshot()
    kwargs = dict(target_length=perimeter * 1.1, auto_falloff=automatic,
                  falloff_radius=0.9, falloff_shape='SMOOTH')
    if explicit_option:
        kwargs['use_connected'] = connected
    result = bpy.ops.mesh.zloop_scale_precise(**kwargs)
    assert result == {'FINISHED'}, result
    assert settings_snapshot() == saved, "User transform settings leaked"
    bm = bmesh.from_edit_mesh(obj.data)
    after_perimeter = sum(e.calc_length() for e in bm.edges if e.select)
    assert abs(after_perimeter / perimeter - 1.1) < 1e-5
    moved = {v.index: (v.co - before[v.index]).length for v in bm.verts}
    adjacent_motion = max(moved[i] for i in range(per_finger, per_finger * 2))
    local_motion = max(moved[i] for i in range(15 * sides, 16 * sides))
    assert local_motion > 1e-6, "Same finger must retain smooth local influence"
    assert max(moved[i] for i in range(sides)) < 1e-7, "Palm outside radius moved"
    if connected:
        assert adjacent_motion < 1e-7, "Adjacent finger moved with connected falloff"
    else:
        assert adjacent_motion > 1e-5, "Off control did not reproduce cross-finger influence"
    print(f"PASS geometry: connected={connected}, auto={automatic}, joined={joined}, "
          f"adjacent_motion={adjacent_motion:.8f}, local_motion={local_motion:.8f}")


def test_failure_restore(addon):
    make_fingers()
    ts = bpy.context.scene.tool_settings
    ts.use_proportional_edit = False
    ts.use_proportional_connected = False
    ts.use_proportional_projected = True
    saved = settings_snapshot()
    original = addon.ZLOOP_OT_scale_precise.perform_scaling

    def fail(*args):
        raise RuntimeError("Injected transform failure")

    addon.ZLOOP_OT_scale_precise.perform_scaling = fail
    try:
        try:
            result = bpy.ops.mesh.zloop_scale_precise(target_length=3.0)
            assert result == {'CANCELLED'}
        except RuntimeError as error:
            assert "Injected transform failure" in str(error)
        assert settings_snapshot() == saved, "Failure left transform settings changed"
    finally:
        addon.ZLOOP_OT_scale_precise.perform_scaling = original
    print("PASS failure restores settings")


def assert_unregistered(addon):
    for base, identifier in addon._CLASS_REGISTRY:
        assert base.bl_rna_get_subclass_py(identifier) is None, identifier
    for name in addon._SCENE_PROPERTY_NAMES:
        assert not hasattr(bpy.types.Scene, name), name
        assert all(name not in scene for scene in bpy.data.scenes), name


addon = load_addon("zloop_runtime_test")
addon.register()
assert bpy.context.scene.zloop_use_connected is True
assert bpy.ops.mesh.zloop_scale_precise.get_rna_type().properties['use_connected'].default is True
for automatic in (False, True):
    for connected in (False, True):
        run_geometry_case(connected, automatic)
run_geometry_case(True, False, joined=False)
run_geometry_case(True, True, explicit_option=False)
test_failure_restore(addon)

bpy.ops.object.mode_set(mode='OBJECT')
bpy.context.scene.zloop_use_connected = False
bpy.context.scene.zloop_target_length = 12.5
addon.register()
assert bpy.context.scene.zloop_use_connected is False
assert bpy.context.scene.zloop_target_length == 12.5
# Simulate replacing a loaded module while the old RNA classes still exist.
replacement = load_addon("zloop_runtime_reloaded")
replacement.register()
replacement.unregister()
assert_unregistered(replacement)
replacement.unregister()
replacement.register()
assert bpy.context.scene.zloop_use_connected is True
replacement.unregister()
assert_unregistered(replacement)
print("PASS repeat registration, module replacement, disable/re-enable and cleanup")
print("ALL TESTS PASSED", bpy.app.version_string)
