from scipy import sparse
#from scipy import *
import scipy
import math
import numpy as np
import meshio

def distance(v0, v1):
    return math.sqrt( ((v0[0]-v1[0])**2)+((v0[1]-v1[1])**2) + ((v0[2]-v1[2])**2) )

def orientation_clockwise(p, q, r): 
    return (r[0] - p[0]) * (q[1] - p[1]) - (q[0] - p[0]) * (r[1] - p[1]) > 0


class Mesh:
    
    def __init__(self, vertices, faces):
        self.vertices = vertices
        self.faces = faces
        self.sort_faces_clockwise()
        self.set_vertex_areas()
        self.set_edges()
        self.set_cotangent_matrix()

    def sort_faces_clockwise(self):
        for face_idx, face in enumerate(self.faces):
            v0 = self.vertices[face[0]]
            v1 = self.vertices[face[1]]
            v2 = self.vertices[face[2]]

            if not orientation_clockwise(v0, v1, v2):
                tmp = face[1]
                self.faces[face_idx][1] = face[2]
                self.faces[face_idx][2] = tmp


    def set_edges(self):
        self.edges = []
        
        edge_indices = {}
        for face in self.faces:
            face_edges = [
                [face[0], face[1], face[2]], 
                [face[1], face[2], face[0]], 
                [face[2], face[0], face[1]]]

            for edge in face_edges:
                edge_lookup = sorted([edge[0], edge[1]])
                edge_lookup_key = ','.join([str(edge_lookup[0]), str(edge_lookup[1])])

                if edge_lookup_key in edge_indices:
                    self.edges[edge_indices[edge_lookup_key]].append(edge)
                else:
                    edge_indices[edge_lookup_key] = len(self.edges)
                    self.edges.append([edge])

    def set_vertex_areas(self):
        self.vertex_areas = sparse.dok_matrix(
            (len(self.vertices),len(self.vertices)), dtype=scipy.float32
            )
        for face in self.faces:
            v0 = self.vertices[face[0]]
            v1 = self.vertices[face[1]]
            v2 = self.vertices[face[2]]
            
            side0 = distance(v0, v1)
            side1 = distance(v1, v2)
            side2 = distance(v0, v2)

            # calculate the semi-perimeter
            s = (side0 + side1 + side2) / 2

            # calculate the area
            area = (s*(s-side0)*(s-side1)*(s-side2)) ** 0.5

            for vertex_id in face:
                self.vertex_areas[vertex_id, vertex_id] += area / 3

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
            edge_deriv_zero[edge_id, edge[0]] = -1.0
            edge_deriv_zero[edge_id, edge[1]] = 1.0

        self.vertex_cotans = np.transpose(edge_deriv_zero) * edge_cotans * edge_deriv_zero
        self.vertex_cotans += 0.00000001 * self.vertex_areas
        

mesh_in = meshio.read('heart.mesh')
#print(mesh_in.cells['triangle'][0])
mesh = Mesh(mesh_in.points, mesh_in.cells['triangle'])
#print(mesh_in)
#print(type(mesh.faces[0]))
print(mesh.vertex_cotans)
print(np.all(np.linalg.eigvals(mesh.vertex_cotans.todense()) > 0))