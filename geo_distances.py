import numpy as np

#def build_vertex_area(vertices, faces)

def initHeat(vertices, start_idxs):
    # shape: num vertices x 1, 1 if the vertex is a heat source, 0 else
    init_heat = np.array([1.0 if i in start_idxs else 0 for i in range(len(vertices))])
