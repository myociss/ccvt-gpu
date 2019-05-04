import bpy
import csv
import json
import random

#with open('C:\\Users\\Fern\\Cyan_Preprocessing\\mesh\\vertices_3d.csv', 'r') as f:
#  reader = csv.reader(f)
#  verts = list(reader)

with open('C:\\Users\\Fern\\tissue_modelling\\vertices.json', 'r') as f:
  vertices = json.load(f)
  
with open('C:\\Users\\Fern\\tissue_modelling\\faces.json', 'r') as f:
  faces = json.load(f)
  
with open('C:\\Users\\Fern\\tissue_modelling\\vertex_colors.txt') as f:
    content = f.readlines()
# you may also want to remove whitespace characters like `\n` at the end of each line
content = [x.strip() for x in content] 
  
verts = [[3 * float(elem) for elem in v] for v in vertices]
faces = [[int(elem) for elem in face] for face in faces]

#create mesh and object
mymesh = bpy.data.meshes.new("finiteElementHead")
myobject = bpy.data.objects.new("finiteElementHead",mymesh)

 
#set mesh location
myobject.location = (0,0,0)
bpy.context.scene.objects.link(myobject)
 
#create mesh from python data
mymesh.from_pydata(verts,[],faces)

mymesh.vertex_colors.new()
color_layer = mymesh.vertex_colors.active  

for i in range(len(vertices)):
    color = content[i]
    color_layer.data[i].color = [1.0, float(color), float(color)]
i = 0
'''
for poly in mymesh.polygons:
    for idx in poly.loop_indices:
        rgb = [1.0 ]
        color_layer.data[i].color = rgb
        i += 1
'''


mymesh.update(calc_edges=True)

#set the object to edit mode
bpy.context.scene.objects.active = myobject
bpy.ops.object.mode_set(mode='EDIT')
 
# remove duplicate vertices
bpy.ops.mesh.remove_doubles() 

# recalculate normals
bpy.ops.mesh.normals_make_consistent(inside=False)
bpy.ops.object.mode_set(mode='VERTEX_PAINT')