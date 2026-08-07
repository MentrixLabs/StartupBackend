import numpy as np
import cv2
import matplotlib.pyplot as plt

def analyze_mask_grid(mask: np.ndarray, grid_size=(10, 10), threshold=0.05) -> np.ndarray:
    h, w = mask.shape
    grid_h, grid_w = grid_size
    cell_h, cell_w = h // grid_h, w // grid_w
    
    grid_matrix = np.zeros((grid_h, grid_w), dtype=np.uint8)

    for i in range(grid_h):
        for j in range(grid_w):
            cell = mask[i*cell_h:(i+1)*cell_h, j*cell_w:(j+1)*cell_w]
            white_ratio = np.sum(cell == 255) / (cell_h * cell_w)
            grid_matrix[i, j] = 1 if white_ratio > threshold else 0
    
    return grid_matrix

def find_max_rectangles(matrix):
    """Находит все максимальные прямоугольники из 1 в бинарной матрице."""
    if matrix.size == 0:
        return []
    
    matrix = matrix.copy()
    rows, cols = matrix.shape
    rectangles = []
    
    for i in range(rows):
        for j in range(cols):
            if matrix[i, j] == 1:
                # Начальные координаты прямоугольника
                x1, y1 = i, j
                x2, y2 = i, j
                
                # Расширяем вправо
                while y2 + 1 < cols and matrix[x1, y2 + 1] == 1:
                    y2 += 1
                
                # Расширяем вниз
                expand_down = True
                while expand_down and x2 + 1 < rows:
                    for y in range(y1, y2 + 1):
                        if matrix[x2 + 1, y] != 1:
                            expand_down = False
                            break
                    if expand_down:
                        x2 += 1
                
                # Добавляем прямоугольник
                rectangles.append((x1, y1, x2, y2))
                
                # Обнуляем найденный прямоугольник, чтобы не учитывать его снова
                matrix[x1:x2+1, y1:y2+1] = 0
                
    return rectangles

def find_free_space_rectangles(grid_matrix):
    """Находит прямоугольники свободного пространства в матрице."""
    # Инвертируем матрицу: 0 (свободное) → 1, 1 (объект) → 0
    inverted = 1 - grid_matrix
    rectangles = find_max_rectangles(inverted)
    
    # Преобразуем координаты сетки в координаты и размеры прямоугольников
    result = []
    for x1, y1, x2, y2 in rectangles:
        width = y2 - y1 + 1
        height = x2 - x1 + 1
        result.append({
            'x': y1,  # столбец (ширина)
            'y': x1,  # строка (высота)
            'width': width,
            'height': height,
            'area': width * height
        })
    
    # Сортируем по площади (от большего к меньшему)
    result.sort(key=lambda r: r['area'], reverse=True)
    
    return result
