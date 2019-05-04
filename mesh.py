from scipy import sparse
#from scipy import *
from scipy.sparse.linalg import spsolve
import scipy
import math
import numpy as np
import meshio
import json

def distance(v0, v1):
    return math.sqrt( ((v0[0]-v1[0])**2)+((v0[1]-v1[1])**2) + ((v0[2]-v1[2])**2) )

def get_orientation(p, q, r): 
    return (r[0] - p[0]) * (q[1] - p[1]) - (q[0] - p[0]) * (r[1] - p[1])# > 0

def get_normal(a, b, c):
    normal = np.cross(b - a, c - a)
    return normal / np.linalg.norm(normal)
                #(B - A) x (C - A)
#Norm = Dir / len(Dir)

def triangle_area(a, b, c):
    side0 = distance(a, b)
    side1 = distance(b, c)
    side2 = distance(a, c)

    # calculate the semi-perimeter
    s = (side0 + side1 + side2) / 2

    # calculate the area
    area = (s*(s-side0)*(s-side1)*(s-side2)) ** 0.5
    return area


class Mesh:
    
    def __init__(self, vertices, faces):
        self.vertices = vertices
        self.faces = faces
        self.sort_faces_counterclockwise()
        self.set_vertex_areas()
        self.set_edges()
        self.set_cotangent_matrix()
        #self.cholesky = np.linalg.cholesky(self.vertex_cotans)

    def sort_faces_counterclockwise(self):
        self.face_normals = []

        for face_idx, face in enumerate(self.faces):
            v0 = self.vertices[face[0]]
            v1 = self.vertices[face[1]]
            v2 = self.vertices[face[2]]

            orientation = get_orientation(v0, v1, v2)

            if orientation > 0:
                tmp = face[1]
                self.faces[face_idx][1] = face[2]
                self.faces[face_idx][2] = tmp

            v0 = self.vertices[face[0]]
            v1 = self.vertices[face[1]]
            v2 = self.vertices[face[2]]

            self.face_normals.append(get_normal(v0, v1, v2))


    def set_edges(self):
        self.edges = []
        self.edge_length_mean = 0
        
        edge_indices = {}
        for face_idx, face in enumerate(self.faces):
            face_edges = [
                [face[0], face[1], face[2], face_idx], 
                [face[1], face[2], face[0], face_idx], 
                [face[2], face[0], face[1], face_idx]]

            for edge in face_edges:
                edge_lookup = sorted([edge[0], edge[1]])
                edge_lookup_key = ','.join([str(edge_lookup[0]), str(edge_lookup[1])])

                if edge_lookup_key in edge_indices:
                    self.edges[edge_indices[edge_lookup_key]].append(edge)
                else:
                    edge_indices[edge_lookup_key] = len(self.edges)
                    self.edges.append([edge])
                self.edge_length_mean += distance(self.vertices[edge[0]], self.vertices[edge[1]]) / 2
        self.edge_length_mean /= len(self.edges)

    def set_vertex_areas(self):
        self.vertex_faces = [[]for v in self.vertices]
        self.vertex_areas = sparse.dok_matrix(
            (len(self.vertices),len(self.vertices)), dtype=scipy.float32
            )
        for face_id, face in enumerate(self.faces):
            v0 = self.vertices[face[0]]
            v1 = self.vertices[face[1]]
            v2 = self.vertices[face[2]]
            
            area = triangle_area(v0, v1, v2)

            for vertex_id in face:
                self.vertex_areas[vertex_id, vertex_id] += area / 3
            self.vertex_faces[face[0]].append(face_id)
            self.vertex_faces[face[1]].append(face_id)
            self.vertex_faces[face[2]].append(face_id)

    def set_cotangent_matrix(self):
        edge_cotans = scipy.sparse.dok_matrix((len(self.edges),len(self.edges)), dtype=scipy.float32)
        edge_id = 0
        #self.vertex_cotans = sparse.dok_matrix((len(self.vertices),len(self.vertices)), dtype=scipy.float32)

        for edge_id, edge in enumerate(self.edges):
            cotan = 0
            for half_edge in edge:
                v0 = self.vertices[half_edge[0]]
                v1 = self.vertices[half_edge[1]]
                opposite = self.vertices[half_edge[2]]

                u = v0 - opposite
                v = v1 - opposite

                cotan += (np.dot(u,v) / np.linalg.norm(np.cross(u,v)))
            cotan /= 2.0
            edge_cotans[edge_id, edge_id] = cotan

        edge_deriv_zero = scipy.sparse.dok_matrix((len(self.edges),len(self.vertices)), dtype=scipy.float32)
        
        for edge_id, edge in enumerate(self.edges):
            #print(edge[0])
            edge_deriv_zero[edge_id, edge[0][0]] = 1.0
            edge_deriv_zero[edge_id, edge[1][0]] = -1.0

        self.vertex_cotans = np.transpose(edge_deriv_zero) * edge_cotans * edge_deriv_zero
        self.vertex_cotans += 0.00000001 * self.vertex_areas

    def compute_vector_field(self, u):
        self.face_vectors = []
        for face_idx, face in enumerate(self.faces):
            v0 = self.vertices[face[0]]
            v1 = self.vertices[face[1]]
            v2 = self.vertices[face[2]]

            ui = u[face[0]]
            uj = u[face[1]]
            uk = u[face[2]]

            normal = self.face_normals[face_idx]
            #print(normal)
            
            ijhalfpi = np.cross(normal, v1 - v0)
            jkhalfpi = np.cross(normal, v2 - v0)
            kihalfpi = np.cross(normal, v0 - v2)

            X = 0.5 * (ui * jkhalfpi + uj*kihalfpi + uk * ijhalfpi) / triangle_area(v0, v1, v2)

            self.face_vectors.append(X / (np.linalg.norm(X)))
    
    def compute_divergence(self):
        self.div = [0.0 for v in self.vertices]
        for edge in self.edges:
            for half_edge in edge:
                v0 = half_edge[0]
                v1 = half_edge[1]

                normal = self.face_normals[half_edge[3]]
                n = np.cross(normal, self.vertices[v0] - self.vertices[v1])
                self.div[v0] += np.dot(n, self.face_vectors[half_edge[3]])

        #for v in self.vertices:
        '''
        for face_idx, face in self.faces:
            v0 = self.vertices[face[0]]
            v1 = self.vertices[face[1]]
            v2 = self.vertices[face[2]]

            u0 = v1 - v0
            v0 = v2 - v0
            cotanv0 = (np.dot(u0,v0) / np.linalg.norm(np.cross(u0,v0)))

            u1 = v0 - v1
            v1 = v2 - v1
            cotanv1 = (np.dot(u1,v1) / np.linalg.norm(np.cross(u1,v1)))

            u2 = v0 - v2
            v2 = v1 - v2
            cotanv2 = (np.dot(u2,v2) / np.linalg.norm(np.cross(u2,v2)))

            div0 = 0.5 * cotanv1 * np.dot()
        '''
        '''
        for edge_idx, edge in enumerate(self.edges):
            edge_cotan = self.edge_cotans[edge_idx]
            v0 = self.vertices[edge[0]]

            #this edge should be pointing TO the opposite vertex
            v1 = self.vertices[edge[1]]

            opposite_idx = edge[2]
            opposite = self.vertices[edge[2]]

            face_vector = self.face_vectors[edge[3]]

            e0 = v0 - opposite
            e1 = v1 - opposite
            self.div += edge_cotan * np.dot()
        '''
        

mesh_in = meshio.read('heart.mesh')
#faces = [[v-1 for v in face] for face in mesh_in.cells['triangle']]

mesh = Mesh(mesh_in.points, mesh_in.cells['triangle'])
#mesh = Mesh(mesh_in.points, faces)
#print(np.all(np.linalg.eigvals(mesh.vertex_cotans.todense()) > 0))

A = mesh.vertex_areas + ((mesh.edge_length_mean ** 2) * mesh.vertex_cotans)
b = np.array([1.0 if i == 398 else 0.0 for i in range(len(mesh.vertices))])
x = spsolve(A, b)


mesh.compute_vector_field(x)
mesh.compute_divergence()

phi = spsolve(mesh.vertex_cotans, mesh.div)
phi_min = np.amin(phi)
phi -= phi_min
#print(phi)
print(phi_min)
print(np.amin(phi))
print(phi[398])
print(phi[99])
print(phi[444])
print(phi[401])

with open('vertex_colors.txt', 'w') as f:
    for vertex_color in phi:
        f.write(str(vertex_color))
        f.write('\n')

vertices = [[comp for comp in v] for v in mesh.vertices]

with open('vertices.json', 'w') as f:
    json.dump(vertices, f)
#print(x)

'''
(793, 154)    0.18359673
  (793, 202)    2.5356889
  (793, 723)    1.1371272
  (793, 791)    -0.22783169
  (793, 206)    -0.23127122
  (793, 199)    1.4343292
  (793, 737)    -3.4277003
  (793, 198)    -0.63055843
  (793, 200)    -0.8635582
  (793, 615)    -0.6969773
  (793, 362)    -0.9704625
'''