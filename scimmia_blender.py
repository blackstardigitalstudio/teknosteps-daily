# -*- coding: utf-8 -*-
"""
Tekno Monkey 3D - scimmietta VERA in 3D che cammina/balla (Made in Italy).
Eseguire con Blender headless:
  blender --background --python scimmia_blender.py -- --frames 48 --fps 24 --w 1920 --h 1080 --out _blender_frames --bpm 150

Costruisce un personaggio riggato da primitive (torso, testa, cuffie verdi, 2 braccia
con gomito, 2 gambe con ginocchio, piedi, coda) in una gerarchia di GIUNTI, anima un
CICLO DI CAMMINATA (gambe che si muovono, ginocchia che piegano, braccia che
dondolano, corpo che rimbalza a tempo) su un palco neon, e rende una sequenza PNG
loopabile (frame N == frame 0).
"""
import bpy, math, os, sys
from mathutils import Euler


def arg(flag, d):
    a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    return a[a.index(flag) + 1] if flag in a else d


FRAMES = int(arg("--frames", "48"))
FPS = int(arg("--fps", "24"))
RESX = int(arg("--w", "1920"))
RESY = int(arg("--h", "1080"))
OUT = arg("--out", "_blender_frames")
BPM = float(arg("--bpm", "150"))

BROWN = (0.28, 0.15, 0.07)
TAN = (0.85, 0.72, 0.55)
GREEN = (0.45, 1.0, 0.0)
DARKM = (0.02, 0.02, 0.03)

# --- pulisci scena ---
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for coll in (bpy.data.meshes, bpy.data.materials):
    for b in list(coll):
        coll.remove(b)


def mat(name, color, emission=0.0, rough=0.55):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    if emission > 0:
        for k in ("Emission Color", "Emission"):
            if k in b.inputs:
                b.inputs[k].default_value = (*color, 1); break
        if "Emission Strength" in b.inputs:
            b.inputs["Emission Strength"].default_value = emission
    return m


M_FUR = mat("fur", BROWN)
M_TAN = mat("tan", TAN)
M_NEON = mat("neon", GREEN, emission=2.2)
M_GLOW = mat("glow", GREEN, emission=1.1)
M_WHITE = mat("white", (0.95, 0.95, 0.95))
M_DARK = mat("dark", (0.02, 0.02, 0.03))


def _finish(o, name, material, parent):
    o.name = name
    o.data.materials.append(material)
    if parent:
        o.parent = parent
        o.matrix_parent_inverse = parent.matrix_world.inverted()
    return o


def limb(name, joint, depth, radius, material, parent, up=False):
    """Cilindro che pende dal GIUNTO (origine sul giunto -> ruota attorno al giunto)."""
    bpy.ops.mesh.primitive_cylinder_add(vertices=18, radius=radius, depth=depth, location=(0, 0, 0))
    o = bpy.context.active_object
    off = depth / 2 if up else -depth / 2
    for v in o.data.vertices:
        v.co.z += off
    o.location = joint
    return _finish(o, name, material, parent)


def ball(name, loc, radius, material, parent, scale=(1, 1, 1)):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=20, ring_count=12, radius=radius, location=loc)
    o = bpy.context.active_object
    o.scale = scale
    return _finish(o, name, material, parent)


def box(name, loc, size, material, parent):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.active_object
    o.scale = size
    return _finish(o, name, material, parent)


HIP = 1.0
# root (bacino)
bpy.ops.object.empty_add(location=(0, 0, HIP)); root = bpy.context.active_object; root.name = "root"

torso = limb("torso", (0, 0, HIP), 0.62, 0.30, M_FUR, root, up=True)
ball("belly", (0, -0.16, 0.33), 0.20, M_TAN, torso, scale=(1, 0.6, 1.2))
head = ball("head", (0, 0, 1.72), 0.34, M_FUR, torso)
ball("muzzle", (0, -0.26, 1.64), 0.17, M_TAN, head, scale=(1, 0.8, 0.8))
ball("earL", (0.30, 0, 1.80), 0.12, M_FUR, head)
ball("earR", (-0.30, 0, 1.80), 0.12, M_FUR, head)
ball("eyeL", (0.12, -0.28, 1.76), 0.07, M_WHITE, head)
ball("eyeR", (-0.12, -0.28, 1.76), 0.07, M_WHITE, head)
ball("pupL", (0.12, -0.33, 1.76), 0.035, M_DARK, head)
ball("pupR", (-0.12, -0.33, 1.76), 0.035, M_DARK, head)
# cuffie verdi (brand)
ball("cupL", (0.34, 0, 1.66), 0.12, M_NEON, head, scale=(0.6, 1, 1))
ball("cupR", (-0.34, 0, 1.66), 0.12, M_NEON, head, scale=(0.6, 1, 1))
band = limb("band", (0, 0, 1.72), 0.36, 0.03, M_NEON, head, up=True)
band.rotation_euler = Euler((0, math.pi / 2, 0), 'XYZ')

# braccia (spalla -> gomito -> mano)
armLu = limb("armLu", (0.32, 0, 1.52), 0.42, 0.09, M_FUR, torso)
armLl = limb("armLl", (0.32, 0, 1.10), 0.40, 0.08, M_FUR, armLu)
ball("handL", (0.32, 0, 0.70), 0.11, M_NEON, armLl)
armRu = limb("armRu", (-0.32, 0, 1.52), 0.42, 0.09, M_FUR, torso)
armRl = limb("armRl", (-0.32, 0, 1.10), 0.40, 0.08, M_FUR, armRu)
ball("handR", (-0.32, 0, 0.70), 0.11, M_NEON, armRl)

# gambe (anca -> ginocchio -> piede)
thighL = limb("thighL", (0.16, 0, HIP), 0.50, 0.13, M_FUR, root)
shinL = limb("shinL", (0.16, 0, 0.50), 0.48, 0.10, M_FUR, thighL)
box("footL", (0.16, -0.10, 0.03), (0.18, 0.34, 0.10), M_NEON, shinL)
thighR = limb("thighR", (-0.16, 0, HIP), 0.50, 0.13, M_FUR, root)
shinR = limb("shinR", (-0.16, 0, 0.50), 0.48, 0.10, M_FUR, thighR)
box("footR", (-0.16, -0.10, 0.03), (0.18, 0.34, 0.10), M_NEON, shinR)

# coda (2 segmenti)
tail1 = limb("tail1", (0, 0.28, 0.95), 0.45, 0.06, M_FUR, root)
tail1.rotation_euler = Euler((0.9, 0, 0), 'XYZ')
tail2 = limb("tail2", (0, 0, -0.45), 0.40, 0.045, M_NEON, tail1)


def key(o, frame, rot=None, loc=None):
    if rot is not None:
        o.rotation_euler = Euler(rot, 'XYZ'); o.keyframe_insert("rotation_euler", frame=frame)
    if loc is not None:
        o.location = loc; o.keyframe_insert("location", frame=frame)


try:
    bpy.context.preferences.edit.keyframe_new_interpolation_type = 'LINEAR'
except Exception:
    pass

for i in range(FRAMES + 1):          # +1 per chiudere il loop identico
    f = i
    p = 2 * math.pi * i / FRAMES
    bob = 0.06 * math.cos(2 * p)
    key(root, f, rot=(0, 0, 0.06 * math.sin(p)), loc=(0, 0, HIP + bob - 0.02))
    key(thighL, f, rot=(0.65 * math.sin(p), 0, 0))
    key(thighR, f, rot=(0.65 * math.sin(p + math.pi), 0, 0))
    key(shinL, f, rot=(max(0.0, 1.0 * math.sin(p + 2.5)) + 0.12, 0, 0))
    key(shinR, f, rot=(max(0.0, 1.0 * math.sin(p + math.pi + 2.5)) + 0.12, 0, 0))
    key(armLu, f, rot=(-0.55 * math.sin(p), 0, -0.14))
    key(armRu, f, rot=(-0.55 * math.sin(p + math.pi), 0, 0.14))
    key(armLl, f, rot=(0.35 + 0.25 * (0.5 + 0.5 * math.sin(p)), 0, 0))
    key(armRl, f, rot=(0.35 + 0.25 * (0.5 + 0.5 * math.sin(p + math.pi)), 0, 0))
    key(torso, f, rot=(0.05 * math.cos(2 * p), 0, -0.06 * math.sin(p)))
    key(head, f, rot=(0.06 * math.cos(2 * p + 0.5), 0, 0.07 * math.sin(p)))
    key(tail1, f, rot=(0.9 + 0.2 * math.sin(p), 0, 0.35 * math.sin(p)))

# --- PALCO NEON + luci + camera ---
bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 0, 0))
_finish(bpy.context.active_object, "floor", M_DARK, None)
disc = limb("glow", (0, 0, 0.02), 0.03, 1.1, M_GLOW, None)   # disco emissivo sotto i piedi

bpy.ops.object.light_add(type='AREA', location=(3, -4, 5)); kl = bpy.context.active_object
kl.data.energy = 380; kl.data.size = 6
bpy.ops.object.light_add(type='AREA', location=(-3.5, 3.5, 3)); rl = bpy.context.active_object
rl.data.energy = 320; rl.data.size = 5; rl.data.color = (0.5, 1.0, 0.2)
bpy.ops.object.light_add(type='AREA', location=(0, -2.5, 0.6)); fl = bpy.context.active_object
fl.data.energy = 120; fl.data.size = 3; fl.data.color = (0.5, 1.0, 0.2)

bpy.ops.object.empty_add(location=(0, 0, 0.95)); tgt = bpy.context.active_object
bpy.ops.object.camera_add(location=(2.6, -7.2, 2.1)); cam = bpy.context.active_object
con = cam.constraints.new('TRACK_TO'); con.target = tgt
con.track_axis = 'TRACK_NEGATIVE_Z'; con.up_axis = 'UP_Y'
cam.data.lens = 58

sc = bpy.context.scene
sc.camera = cam
w = sc.world
if not w:
    w = bpy.data.worlds.new("W"); sc.world = w
w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.012, 0.014, 0.02, 1)

try:
    sc.render.engine = 'BLENDER_EEVEE_NEXT'
except TypeError:
    sc.render.engine = 'BLENDER_EEVEE'
for attr, val in (("use_bloom", True),):
    try:
        setattr(sc.eevee, attr, val)
    except Exception:
        pass
try:
    sc.eevee.taa_render_samples = 24
except Exception:
    pass

sc.render.resolution_x = RESX
sc.render.resolution_y = RESY
sc.render.fps = FPS
sc.frame_start = 0
sc.frame_end = FRAMES - 1
sc.render.image_settings.file_format = 'PNG'
outdir = OUT if os.path.isabs(OUT) else os.path.join(os.path.dirname(os.path.abspath(__file__)), OUT)
os.makedirs(outdir, exist_ok=True)
sc.render.filepath = os.path.join(outdir, "f")
print("[3D] Render %d frame -> %s" % (FRAMES, outdir))
bpy.ops.render.render(animation=True)
print("[3D] FATTO. Made in Italy.")
