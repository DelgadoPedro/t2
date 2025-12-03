"""
Algoritmo de Scan Line para renderização com Phong Shading (Verdadeiro)
"""
from typing import List, Tuple, Optional
import math
from PyQt5.QtGui import QImage, QColor
import geometry3d as geo3d
import numpy as np

Point3D = Tuple[float, float, float]
Point2D = Tuple[float, float]
ColorRGB = Tuple[float, float, float]


class ScanLinePhong:
    """Renderizador Scan Line com Phong Shading Verdadeiro (iluminação por pixel)"""
    
    def __init__(self, width: int, height: int, use_simple_shading: bool = False):
        self.width = width
        self.height = height
        self.image = QImage(width, height, QImage.Format_RGB32)
        # Usar numpy array para depth buffer (muito mais rápido)
        self.depth_buffer = np.full((height, width), np.inf, dtype=np.float32)
        
        # Flag para usar shading simplificado (sem especular)
        self.use_simple_shading = use_simple_shading
        
        # Propriedades de iluminação
        self.light_position = np.array([200.0, 200.0, 200.0], dtype=np.float32)
        self.light_ambient = np.array([0.5, 0.5, 0.5], dtype=np.float32)  # Aumentado de 0.3 para 0.5
        self.light_diffuse = np.array([1.0, 1.0, 1.0], dtype=np.float32)
        self.light_specular = np.array([1.0, 1.0, 1.0], dtype=np.float32)
        
        # Propriedades do material
        self.material_ambient = np.array([0.4, 0.4, 0.5], dtype=np.float32)  # Aumentado de 0.2 para 0.4
        self.material_diffuse = np.array([0.9, 0.9, 1.0], dtype=np.float32)  # Aumentado de 0.8 para 0.9
        self.material_specular = np.array([1.0, 1.0, 1.0], dtype=np.float32)
        self.material_shininess = 64.0  # Brilho para highlights especulares
        
        # Posição do observador (para cálculo do vetor de vista)
        self.viewer_position = np.array([0.0, 0.0, 300.0], dtype=np.float32)
        
        # Cache de valores pré-calculados
        self._ambient_color = self.light_ambient * self.material_ambient
    
    def clear(self, bg_color: QColor = QColor(20, 20, 30)):
        """Limpa o buffer de imagem e depth buffer"""
        self.image.fill(bg_color)
        self.depth_buffer.fill(np.inf)
    
    def set_light_position(self, x: float, y: float, z: float):
        """Define posição da fonte de luz"""
        self.light_position = np.array([x, y, z], dtype=np.float32)
    
    def set_viewer_position(self, x: float, y: float, z: float):
        """Define posição do observador (câmera)"""
        self.viewer_position = np.array([x, y, z], dtype=np.float32)
    
    def set_material_properties(self, ambient: ColorRGB, diffuse: ColorRGB, 
                               specular: ColorRGB, shininess: float):
        """Define propriedades do material"""
        self.material_ambient = np.array(ambient, dtype=np.float32)
        self.material_diffuse = np.array(diffuse, dtype=np.float32)
        self.material_specular = np.array(specular, dtype=np.float32)
        self.material_shininess = shininess
        self._ambient_color = self.light_ambient * self.material_ambient
    
    def phong_shading(self, normal: np.ndarray, pos3d: np.ndarray) -> np.ndarray:
        """
        Calcula iluminação Phong para um pixel
        Phong verdadeiro: calcula iluminação usando a normal interpolada
        
        Args:
            normal: Normal interpolada do pixel (já normalizada)
            pos3d: Posição 3D interpolada do pixel
            
        Returns:
            Cor RGB (0.0-1.0) como array numpy
        """
        # Normal já deve estar normalizada, mas garantir
        normal_len = np.linalg.norm(normal)
        if normal_len < 1e-6:
            return self._ambient_color
        if abs(normal_len - 1.0) > 1e-3:
            normal = normal / normal_len
        
        # Vetor da luz (da posição do ponto até a luz)
        light_vec = self.light_position - pos3d
        light_len = np.linalg.norm(light_vec)
        if light_len < 1e-6:
            return self._ambient_color
        light_vec = light_vec / light_len
        
        # N·L (produto escalar)
        N_dot_L = np.dot(normal, light_vec)
        if N_dot_L < 0:
            # Superfície não está voltada para a luz
            return self._ambient_color
        
        # Componente Difusa
        I_diff = self.light_diffuse * self.material_diffuse * N_dot_L
        
        if self.use_simple_shading:
            # Versão simplificada: apenas ambiente + difusa
            final_color = self._ambient_color + I_diff
        else:
            # Componente Especular (Phong completo)
            # Vetor do observador
            view_vec = self.viewer_position - pos3d
            view_len = np.linalg.norm(view_vec)
            if view_len < 1e-6:
                final_color = self._ambient_color + I_diff
            else:
                view_vec = view_vec / view_len
                
                # Vetor de reflexão: R = 2(N·L)N - L
                reflection_vec = normal * (2.0 * N_dot_L) - light_vec
                reflection_len = np.linalg.norm(reflection_vec)
                if reflection_len > 1e-6:
                    reflection_vec = reflection_vec / reflection_len
                    
                    # R·V (produto escalar)
                    R_dot_V = np.dot(reflection_vec, view_vec)
                    if R_dot_V > 0:
                        specular_factor = math.pow(R_dot_V, self.material_shininess)
                        I_spec = self.light_specular * self.material_specular * specular_factor
                        final_color = self._ambient_color + I_diff + I_spec
                    else:
                        final_color = self._ambient_color + I_diff
                else:
                    final_color = self._ambient_color + I_diff
        
        # Clamp para [0, 1]
        return np.clip(final_color, 0.0, 1.0)
    
    def render_triangle(self, v0_2d: Point2D, v1_2d: Point2D, v2_2d: Point2D,
                       v0_3d: Point3D, v1_3d: Point3D, v2_3d: Point3D,
                       n0: Point3D, n1: Point3D, n2: Point3D):
        """
        Renderiza um triângulo usando scan line com Phong shading VERDADEIRO
        
        Phong verdadeiro: interpola normais e posições 3D, calcula iluminação por pixel
        """
        # Converter para numpy arrays
        points_2d = np.array([
            [int(round(v0_2d[0])), int(round(v0_2d[1]))],
            [int(round(v1_2d[0])), int(round(v1_2d[1]))],
            [int(round(v2_2d[0])), int(round(v2_2d[1]))]
        ], dtype=np.int32)
        
        # Ordenar por Y
        indices = np.argsort(points_2d[:, 1])
        p0 = points_2d[indices[0]]
        p1 = points_2d[indices[1]]
        p2 = points_2d[indices[2]]
        
        # Vértices 3D e normais correspondentes
        verts_3d = np.array([v0_3d, v1_3d, v2_3d], dtype=np.float32)
        normals = np.array([n0, n1, n2], dtype=np.float32)
        
        v0_3d_sorted = verts_3d[indices[0]]
        v1_3d_sorted = verts_3d[indices[1]]
        v2_3d_sorted = verts_3d[indices[2]]
        n0_sorted = normals[indices[0]]
        n1_sorted = normals[indices[1]]
        n2_sorted = normals[indices[2]]
        
        y_min, y_mid, y_max = p0[1], p1[1], p2[1]
        
        # Caso especial: triângulo degenerado
        if y_min == y_max:
            return
        
        # Normalizar normais dos vértices
        n0_len = np.linalg.norm(n0_sorted)
        if n0_len > 1e-6:
            n0_sorted = n0_sorted / n0_len
        else:
            n0_sorted = np.array([0.0, 0.0, 1.0], dtype=np.float32)
        
        n1_len = np.linalg.norm(n1_sorted)
        if n1_len > 1e-6:
            n1_sorted = n1_sorted / n1_len
        else:
            n1_sorted = np.array([0.0, 0.0, 1.0], dtype=np.float32)
        
        n2_len = np.linalg.norm(n2_sorted)
        if n2_len > 1e-6:
            n2_sorted = n2_sorted / n2_len
        else:
            n2_sorted = np.array([0.0, 0.0, 1.0], dtype=np.float32)
        
        # Renderizar parte superior do triângulo
        if y_mid != y_min:
            dy = float(y_mid - y_min)
            if dy > 0:
                t_factor = 1.0 / dy
                
                # Interpolação de X
                x_left = float(p0[0])
                x_right = float(p0[0])
                x_left_inv_slope = (p1[0] - p0[0]) * t_factor
                x_right_inv_slope = (p2[0] - p0[0]) / float(y_max - y_min) if (y_max - y_min) > 0 else 0.0
                
                # Interpolação de Z
                z_left = v0_3d_sorted[2]
                z_right = v0_3d_sorted[2]
                z_left_inv_slope = (v1_3d_sorted[2] - v0_3d_sorted[2]) * t_factor
                z_right_inv_slope = (v2_3d_sorted[2] - v0_3d_sorted[2]) / float(y_max - y_min) if (y_max - y_min) > 0 else 0.0
                
                # Interpolação de posições 3D (para Phong verdadeiro)
                pos3d_left = v0_3d_sorted.copy()
                pos3d_right = v0_3d_sorted.copy()
                pos3d_left_inv_slope = (v1_3d_sorted - v0_3d_sorted) * t_factor
                pos3d_right_inv_slope = (v2_3d_sorted - v0_3d_sorted) / float(y_max - y_min) if (y_max - y_min) > 0 else np.zeros(3, dtype=np.float32)
                
                # Interpolação de normais (PHONG VERDADEIRO - não cores!)
                normal_left = n0_sorted.copy()
                normal_right = n0_sorted.copy()
                normal_left_inv_slope = (n1_sorted - n0_sorted) * t_factor
                normal_right_inv_slope = (n2_sorted - n0_sorted) / float(y_max - y_min) if (y_max - y_min) > 0 else np.zeros(3, dtype=np.float32)
                
                for y in range(y_min, y_mid + 1):
                    if 0 <= y < self.height:
                        x_start = int(round(x_left))
                        x_end = int(round(x_right))
                        if x_start > x_end:
                            x_start, x_end = x_end, x_start
                        
                        if x_end > x_start:
                            dx = float(x_end - x_start)
                            x_start_clamped = max(0, x_start)
                            x_end_clamped = min(self.width, x_end + 1)
                            
                            # Interpolação horizontal
                            z_step = (z_right - z_left) / dx if dx > 0 else 0.0
                            pos3d_step = (pos3d_right - pos3d_left) / dx if dx > 0 else np.zeros(3, dtype=np.float32)
                            normal_step = (normal_right - normal_left) / dx if dx > 0 else np.zeros(3, dtype=np.float32)
                            
                            z = z_left + (x_start_clamped - x_start) * z_step
                            pos3d = pos3d_left + (x_start_clamped - x_start) * pos3d_step
                            normal = normal_left + (x_start_clamped - x_start) * normal_step
                            
                            for x in range(x_start_clamped, x_end_clamped):
                                # Teste de profundidade
                                if z < self.depth_buffer[y, x]:
                                    self.depth_buffer[y, x] = z
                                    
                                    # PHONG VERDADEIRO: calcular iluminação por pixel
                                    color = self.phong_shading(normal, pos3d)
                                    
                                    # Desenhar pixel
                                    r = int(color[0] * 255)
                                    g = int(color[1] * 255)
                                    b = int(color[2] * 255)
                                    self.image.setPixel(x, y, QColor(r, g, b).rgb())
                                
                                # Atualizar para próximo pixel
                                z += z_step
                                pos3d += pos3d_step
                                normal += normal_step
                        
                        # Atualizar para próxima linha
                        x_left += x_left_inv_slope
                        x_right += x_right_inv_slope
                        z_left += z_left_inv_slope
                        z_right += z_right_inv_slope
                        pos3d_left += pos3d_left_inv_slope
                        pos3d_right += pos3d_right_inv_slope
                        normal_left += normal_left_inv_slope
                        normal_right += normal_right_inv_slope
        
        # Renderizar parte inferior do triângulo
        if y_max != y_mid:
            dy = float(y_max - y_mid)
            if dy > 0:
                t_factor = 1.0 / dy
                
                # Interpolação de X
                x_left = float(p1[0])
                x_right = float(p0[0]) + (y_mid - y_min) * (p2[0] - p0[0]) / float(y_max - y_min) if (y_max - y_min) > 0 else float(p0[0])
                x_left_inv_slope = (p2[0] - p1[0]) * t_factor
                x_right_inv_slope = (p2[0] - p0[0]) / float(y_max - y_min) if (y_max - y_min) > 0 else 0.0
                
                # Interpolação de Z
                z_left = v1_3d_sorted[2]
                z_right = v0_3d_sorted[2] + (y_mid - y_min) * (v2_3d_sorted[2] - v0_3d_sorted[2]) / float(y_max - y_min) if (y_max - y_min) > 0 else v0_3d_sorted[2]
                z_left_inv_slope = (v2_3d_sorted[2] - v1_3d_sorted[2]) * t_factor
                z_right_inv_slope = (v2_3d_sorted[2] - v0_3d_sorted[2]) / float(y_max - y_min) if (y_max - y_min) > 0 else 0.0
                
                # Interpolação de posições 3D
                pos3d_left = v1_3d_sorted.copy()
                pos3d_right_interp = v0_3d_sorted + (y_mid - y_min) * (v2_3d_sorted - v0_3d_sorted) / float(y_max - y_min) if (y_max - y_min) > 0 else v0_3d_sorted
                pos3d_right = pos3d_right_interp.copy()
                pos3d_left_inv_slope = (v2_3d_sorted - v1_3d_sorted) * t_factor
                pos3d_right_inv_slope = (v2_3d_sorted - pos3d_right_interp) * t_factor
                
                # Interpolação de normais (PHONG VERDADEIRO)
                normal_left = n1_sorted.copy()
                normal_right_interp = n0_sorted + (y_mid - y_min) * (n2_sorted - n0_sorted) / float(y_max - y_min) if (y_max - y_min) > 0 else n0_sorted
                normal_right = normal_right_interp.copy()
                normal_left_inv_slope = (n2_sorted - n1_sorted) * t_factor
                normal_right_inv_slope = (n2_sorted - normal_right_interp) * t_factor
                
                for y in range(y_mid + 1, y_max + 1):
                    if 0 <= y < self.height:
                        x_start = int(round(x_left))
                        x_end = int(round(x_right))
                        if x_start > x_end:
                            x_start, x_end = x_end, x_start
                        
                        if x_end > x_start:
                            dx = float(x_end - x_start)
                            x_start_clamped = max(0, x_start)
                            x_end_clamped = min(self.width, x_end + 1)
                            
                            # Interpolação horizontal
                            z_step = (z_right - z_left) / dx if dx > 0 else 0.0
                            pos3d_step = (pos3d_right - pos3d_left) / dx if dx > 0 else np.zeros(3, dtype=np.float32)
                            normal_step = (normal_right - normal_left) / dx if dx > 0 else np.zeros(3, dtype=np.float32)
                            
                            z = z_left + (x_start_clamped - x_start) * z_step
                            pos3d = pos3d_left + (x_start_clamped - x_start) * pos3d_step
                            normal = normal_left + (x_start_clamped - x_start) * normal_step
                            
                            for x in range(x_start_clamped, x_end_clamped):
                                # Teste de profundidade
                                if z < self.depth_buffer[y, x]:
                                    self.depth_buffer[y, x] = z
                                    
                                    # PHONG VERDADEIRO: calcular iluminação por pixel
                                    color = self.phong_shading(normal, pos3d)
                                    
                                    # Desenhar pixel
                                    r = int(color[0] * 255)
                                    g = int(color[1] * 255)
                                    b = int(color[2] * 255)
                                    self.image.setPixel(x, y, QColor(r, g, b).rgb())
                                
                                # Atualizar para próximo pixel
                                z += z_step
                                pos3d += pos3d_step
                                normal += normal_step
                        
                        # Atualizar para próxima linha
                        x_left += x_left_inv_slope
                        x_right += x_right_inv_slope
                        z_left += z_left_inv_slope
                        z_right += z_right_inv_slope
                        pos3d_left += pos3d_left_inv_slope
                        pos3d_right += pos3d_right_inv_slope
                        normal_left += normal_left_inv_slope
                        normal_right += normal_right_inv_slope
    
    def get_image(self) -> QImage:
        """Retorna a imagem renderizada"""
        return self.image
