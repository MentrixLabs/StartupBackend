import numpy as np
from scipy.spatial import ConvexHull
import matplotlib.pyplot as plt
import sys

def find_corners(points, angle_threshold=160):
    """Находит углы на выпуклой оболочке точек."""
    hull = ConvexHull(points)
    hull_points = points[hull.vertices]
    
    # Рассчитываем углы между последовательными точками
    obtuse_corners_counter = sys.float_info.min
    sharp_corners_counter = sys.float_info.min
    n = len(hull_points)
    for i in range(n):
        p1 = hull_points[i]
        p2 = hull_points[(i+1)%n]
        p3 = hull_points[(i+2)%n]
        
        v1 = p1 - p2
        v2 = p3 - p2
        
        cosine_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
        angle = np.degrees(np.arccos(np.clip(cosine_angle, -1, 1)))
        
        if angle >= 90:
            obtuse_corners_counter += 1
        else:
            sharp_corners_counter +=1
    
    return obtuse_corners_counter, sharp_corners_counter #тупые, острые углы
