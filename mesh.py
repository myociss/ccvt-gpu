from scipy import sparse
#from scipy import *
from scipy.sparse.linalg import spsolve
import scipy
import math
import numpy as np
import meshio
import json

def nearestPD(A):
    """Find the nearest positive-definite matrix to input

    A Python/Numpy port of John D'Errico's `nearestSPD` MATLAB code [1], which
    credits [2].

    [1] https://www.mathworks.com/matlabcentral/fileexchange/42885-nearestspd

    [2] N.J. Higham, "Computing a nearest symmetric positive semidefinite
    matrix" (1988): https://doi.org/10.1016/0024-3795(88)90223-6
    """

    B = (A + A.T) / 2
    _, s, V = np.linalg.svd(B)

    H = np.dot(V.T, np.dot(np.diag(s), V))

    A2 = (B + H) / 2

    A3 = (A2 + A2.T) / 2

    if isPD(A3):
        return A3

    spacing = np.spacing(np.linalg.norm(A))
    # The above is different from [1]. It appears that MATLAB's `chol` Cholesky
    # decomposition will accept matrixes with exactly 0-eigenvalue, whereas
    # Numpy's will not. So where [1] uses `eps(mineig)` (where `eps` is Matlab
    # for `np.spacing`), we use the above definition. CAVEAT: our `spacing`
    # will be much larger than [1]'s `eps(mineig)`, since `mineig` is usually on
    # the order of 1e-16, and `eps(1e-16)` is on the order of 1e-34, whereas
    # `spacing` will, for Gaussian random matrixes of small dimension, be on
    # othe order of 1e-16. In practice, both ways converge, as the unit test
    # below suggests.
    I = np.eye(A.shape[0])
    k = 1
    while not isPD(A3):
        mineig = np.min(np.real(np.linalg.eigvals(A3)))
        A3 += I * (-mineig * k**2 + spacing)
        k += 1

    return A3

def isPD(B):
    """Returns true when input is positive-definite, via Cholesky"""
    try:
        _ = np.linalg.cholesky(B)
        return True
    except np.linalg.LinAlgError:
        return False

def distance(v0, v1):
    return math.sqrt( ((v0[0]-v1[0])**2)+((v0[1]-v1[1])**2) + ((v0[2]-v1[2])**2) )

def get_orientation(p, q, r): 
    return (r[0] - p[0]) * (q[1] - p[1]) - (q[0] - p[0]) * (r[1] - p[1])# > 0

def get_normal(a, b, c):
    normal = np.cross(b - a, c - a)
    return normal / np.linalg.norm(normal)
                #(B - A) x (C - A)
#Norm = Dir / len(Dir)

#def triangle_area(a, b, c):
def triangle_area(side0, side1, side2):
    #side0 = distance(a, b)
    #side1 = distance(b, c)
    #side2 = distance(a, c)

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
            
            area = triangle_area(distance(v0, v1), distance(v1, v2), distance(v0, v2))

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
def check_symmetric(a, rtol=1e-05, atol=1e-08):
    return np.allclose(a, a.T, rtol=rtol, atol=atol)

mesh_in = meshio.read('heart.mesh')

vertices = mesh_in.points
faces = mesh_in.cells['triangle']

edges = []
edges_lookup = {}

edge_length_avg = 0.0

for face in faces:
    for i in range(3):
        for j in range(i + 1, 3):
            v0 = face[i]
            v1 = face[j]
            sorted_edge = sorted([v0, v1])
            lookup_key = ','.join([str(v) for v in sorted_edge])
            if lookup_key not in edges_lookup:
                edges_lookup[lookup_key] = len(edges)
                edges.append(sorted_edge)
                edge_length_avg += distance(vertices[v0], vertices[v1])
edge_length_avg /= len(edges)

vertex_areas = sparse.dok_matrix((len(vertices),len(vertices)), dtype=scipy.float32)


#vertex_cotans = np.zeros(shape=(len(vertices),len(vertices)), dtype=np.float32)
edge_cotans = sparse.dok_matrix((len(edges),len(edges)), dtype=scipy.float32)

for face_id, face in enumerate(faces):
    vertex_a_id = face[0]
    vertex_b_id = face[1]
    vertex_c_id = face[2]

    A = vertices[vertex_a_id]
    B = vertices[vertex_b_id]
    C = vertices[vertex_c_id]

    a = distance(B, C)
    b = distance(A, C)
    c = distance(A, B)

    edge_a_id = edges_lookup[','.join([str(v) for v in sorted([vertex_b_id, vertex_c_id])])]
    edge_b_id = edges_lookup[','.join([str(v) for v in sorted([vertex_a_id, vertex_c_id])])]
    edge_c_id = edges_lookup[','.join([str(v) for v in sorted([vertex_a_id, vertex_b_id])])]

    angle_A = math.acos((b * b + c * c - a * a) / (2 * b * c))
    angle_B = math.acos((c * c + a * a - b * b) / (2 * c * a))
    angle_C = math.pi - (angle_A + angle_B)

    edge_cotans[edge_a_id, edge_a_id] += 0.5 * (1 / math.tan(angle_A))
    edge_cotans[edge_b_id, edge_b_id] += 0.5 * (1 / math.tan(angle_B))
    edge_cotans[edge_c_id, edge_c_id] += 0.5 * (1 / math.tan(angle_C))

    '''
    u = A - B
    v = C - B

    vertex_cotans[vertex_a_id, vertex_c_id] += 0.5 * (np.dot(u,v) / np.linalg.norm(np.cross(u,v)))
    vertex_cotans[vertex_c_id, vertex_a_id] += 0.5 * (np.dot(u,v) / np.linalg.norm(np.cross(u,v)))

    u = B - A
    v = C - A

    vertex_cotans[vertex_b_id, vertex_c_id] += 0.5 * (np.dot(u,v) / np.linalg.norm(np.cross(u,v)))
    vertex_cotans[vertex_c_id, vertex_b_id] += 0.5 * (np.dot(u,v) / np.linalg.norm(np.cross(u,v)))

    u = A - C
    v = B - C

    vertex_cotans[vertex_a_id, vertex_b_id] += 0.5 * (np.dot(u,v) / np.linalg.norm(np.cross(u,v)))
    vertex_cotans[vertex_b_id, vertex_a_id] += 0.5 * (np.dot(u,v) / np.linalg.norm(np.cross(u,v)))
    '''

    '''
    a = distance(B, C)
    b = distance(A, C)
    c = distance(A, B)

    #angle_A = math.acos((b * b + c * c − a * a) / (2 * b * c))
    angle_A = math.acos((b * b + c * c - a * a) / (2 * b * c))
    #angle_B = math.acos((c * c + a * a − b * b) / (2 * c * a))
    angle_B = math.acos((c * c + a * a - b * b) / (2 * c * a))
    angle_C = math.pi - (angle_A + angle_B)
    '''
            
    area = triangle_area(distance(A, B), distance(B, C), distance(A, C))

    '''
    vertex_cotans[vertex_a_id, vertex_b_id] += 0.5 * (1 / math.tan(angle_C))
    vertex_cotans[vertex_b_id, vertex_a_id] += 0.5 * (1 / math.tan(angle_C))

    vertex_cotans[vertex_b_id, vertex_c_id] += 0.5 * (1 / math.tan(angle_A))
    vertex_cotans[vertex_c_id, vertex_b_id] += 0.5 * (1 / math.tan(angle_A))

    vertex_cotans[vertex_a_id, vertex_c_id] += 0.5 * (1 / math.tan(angle_B))
    vertex_cotans[vertex_c_id, vertex_a_id] += 0.5 * (1 / math.tan(angle_B))
    '''


    for vertex_id in face:
        vertex_areas[vertex_id, vertex_id] += area / 3

edge_deriv_zero = scipy.sparse.dok_matrix((len(edges),len(vertices)), dtype=scipy.float32)
        
for edge_id, edge in enumerate(edges):
    #print(edge[0])
    edge_deriv_zero[edge_id, edge[0]] = 1.0
    edge_deriv_zero[edge_id, edge[1]] = -1.0

vertex_cotans = np.transpose(edge_deriv_zero) * edge_cotans * edge_deriv_zero
#print(vertex_cotans)
vertex_cotans += 0.00000001 * vertex_areas
print(np.all(np.linalg.eigvals(vertex_cotans.todense()) > 0))

u = spsolve(vertex_areas - edge_length_avg * vertex_cotans, np.array([1.0 if i == 398 else 0.0 for i in range(len(vertices))]))

face_vectors = []
for face_id, face in enumerate(faces):
    normal = np.cross(vertices[face[1]] - vertices[face[0]], vertices[face[2]] - vertices[face[0]])
    normal = normal / np.linalg.norm(normal)

    v0 = vertices[face[0]]
    v1 = vertices[face[1]]
    v2 = vertices[face[2]]

    u0 = u[face[0]]
    u1 = u[face[1]]
    u2 = u[face[2]]

    face_vector = 0.0

    face_vector += u0 * np.cross(normal, v2 - v1)
    face_vector += u1 * np.cross(normal, v0 - v2)
    face_vector += u2 * np.cross(normal, v1 - v0)

    face_vector /= (2 * triangle_area(distance(v0, v1), distance(v1, v2), distance(v0, v2)))
    face_vectors.append(face_vector)

#for face_id, face in enumerate(faces):
    
#print(u)

#vertex_cotans += 0.00000001 * vertex_areas


#print(vertex_areas)
#print(np.all(np.linalg.eigvals(vertex_cotans) > 0))
#print(check_symmetric(vertex_cotans))

'''
vertex_cotans_definite = nearestPD(vertex_cotans)
print(np.all(np.linalg.eigvals(vertex_cotans_definite) > 0))
print(vertex_cotans_definite - vertex_cotans)
'''











#faces = [[v-1 for v in face] for face in mesh_in.cells['triangle']]

mesh = Mesh(mesh_in.points, mesh_in.cells['triangle'])
#mesh = Mesh(mesh_in.points, faces)
#print(np.all(np.linalg.eigvals(mesh.vertex_cotans.todense()) > 0))

'''
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
phi_max = np.amax(phi)

phi /= phi_max

with open('vertex_colors.js', 'w') as f:
    json.dump([elem for elem in phi], f)


#print(x)
'''