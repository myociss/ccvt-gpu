import meshio
import random

mesh = meshio.read('heart.off')
print(len(mesh.points))
print(len(mesh.cells['triangle']))

vertex_var_string = 'var mesh_vertices=['
for idx, p in enumerate(mesh.points):
    vertex_var_string += '[' + ','.join([str(comp) for comp in p]) + ']'
    if idx != len(mesh.points) - 1:
        vertex_var_string += ','
vertex_var_string += '];'

with open('mesh_vertices.js', 'w') as f:
    f.write(vertex_var_string)

face_var_string = 'var mesh_faces=['
for idx, f in enumerate(mesh.cells['triangle']):
    face_var_string += '[' + ','.join([str(v) for v in f]) + ']'
    if idx != len(mesh.cells['triangle']) - 1:
        face_var_string += ','
face_var_string += '];'

with open('mesh_faces.js', 'w') as f:
    f.write(face_var_string)

with open('vertex_colors.txt') as f:
    vertex_colors = f.read()

vertex_colors = list(filter(None, vertex_colors.split(',')))

vertex_colors = [int(seed_id) for seed_id in vertex_colors]
color_map = []

for i in range(max(vertex_colors) + 1):
    r = lambda: random.randint(0,255)
    color_map.append('#%02X%02X%02X' % (r(),r(),r()))

#print(color_map)

with open('vertex_colors.js', 'w') as f:
    f.write('var vertex_colors = [')
    for idx, seed_id in enumerate(vertex_colors):
        color = color_map[int(seed_id)]
        f.write("'" + color + "'")
        if idx != len(vertex_colors) - 1:
            f.write(',')
    f.write('];')