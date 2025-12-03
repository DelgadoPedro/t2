"""
Módulo widgets - Componentes de interface gráfica

Estrutura modular:
- canvas_2d.py: Canvas 2D para desenho de polígonos
- widgets.py: Canvas3D, CanvasPhong e MainWindow (este arquivo)
- opengl_viewer.py: Visualizador OpenGL com iluminação
- scanline_phong.py: Renderizador Phong com scan line

Organização:
- Canvas3D: Visualização 3D com QPainter (projeção manual)
- CanvasPhong: Renderização 3D com Phong shading (scan line)
- MainWindow: Janela principal com controles e abas
"""
from typing import List, Tuple, Optional
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QPainter, QPen, QColor
from PyQt5.QtWidgets import (
    QWidget, QMainWindow, QAction, QColorDialog, QSpinBox, QLabel,
    QToolBar, QMessageBox, QFileDialog, QStatusBar, QDoubleSpinBox,
    QComboBox, QPushButton, QVBoxLayout, QHBoxLayout, QGroupBox,
    QSplitter, QCheckBox
)
import geometry3d as geo3d
import math
import numpy as np
from opengl_viewer import OpenGLViewer
from scanline_phong import ScanLinePhong

# Importar Canvas 2D do módulo separado
from canvas_2d import Canvas

Point = Tuple[int, int]
Span = Tuple[int, int, int]  # (y, x_start, x_end)


# ============================================================================
# Canvas3D - Visualização 3D com QPainter
# ============================================================================

class Canvas3D(QWidget):
    """
    Canvas para visualização 3D usando QPainter
    
    Características:
    - Projeção perspectiva e ortográfica
    - Rotação de câmera com mouse
    - Zoom com roda do mouse ou teclas 1/2
    - Renderização de faces e arestas
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.objects: List[geo3d.Object3D] = []
        self.current_object: Optional[geo3d.Object3D] = None
        self.projection: geo3d.Projection = geo3d.OrthographicProjection()
        self.is_perspective = False
        self.edge_color = QColor(0, 0, 0)
        self.fill_color = QColor(100, 150, 255, 100)
        self.show_faces = True
        self.show_edges = True
        
        # Controle de câmera (rotação com mouse)
        self.camera_rot_x = 30.0  # Rotação X inicial
        self.camera_rot_y = 45.0  # Rotação Y inicial
        self.camera_distance = 300.0  # Distância da câmera
        self.last_mouse_pos = None
        self.mouse_sensitivity = 0.5
        
        self.setMinimumSize(800, 600)
        self.setMouseTracking(True)
        # Habilitar foco para receber eventos de teclado
        self.setFocusPolicy(Qt.StrongFocus)
    
    def add_object(self, obj: geo3d.Object3D):
        """Adiciona um objeto 3D"""
        self.objects.append(obj)
        if self.current_object is None:
            self.current_object = obj
        self.update()
    
    def clear_objects(self):
        """Limpa todos os objetos"""
        self.objects.clear()
        self.current_object = None
        self.update()
    
    def set_current_object(self, index: int):
        """Define o objeto atual"""
        if 0 <= index < len(self.objects):
            self.current_object = self.objects[index]
            self.update()
    
    def set_projection(self, is_perspective: bool, distance: float = 500.0):
        """Alterna entre projeção perspectiva e ortográfica"""
        self.is_perspective = is_perspective
        width = self.width()
        height = self.height()
        center_x = width / 2
        center_y = height / 2
        
        if is_perspective:
            self.projection = geo3d.PerspectiveProjection(
                center_x=center_x, center_y=center_y,
                distance=distance, scale=1.0
            )
        else:
            self.projection = geo3d.OrthographicProjection(
                center_x=center_x, center_y=center_y, scale=1.0
            )
        self.update()
    
    def set_edge_color(self, color: QColor):
        self.edge_color = color
        self.update()
    
    def set_fill_color(self, color: QColor):
        self.fill_color = color
        self.update()
    
    def set_show_faces(self, show: bool):
        self.show_faces = show
        self.update()
    
    def set_show_edges(self, show: bool):
        self.show_edges = show
        self.update()
    
    def resizeEvent(self, event):
        """Atualiza projeção quando o canvas é redimensionado"""
        super().resizeEvent(event)
        width = self.width()
        height = self.height()
        center_x = width / 2
        center_y = height / 2
        
        if self.is_perspective:
            distance = self.projection.distance if hasattr(self.projection, 'distance') else 500.0
            self.projection = geo3d.PerspectiveProjection(
                center_x=center_x, center_y=center_y,
                distance=distance, scale=1.0
            )
        else:
            self.projection = geo3d.OrthographicProjection(
                center_x=center_x, center_y=center_y, scale=1.0
            )
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.fillRect(self.rect(), Qt.white)
        
        if not self.objects:
            return
        
        # Criar transformação de câmera (rotação + translação) - mesma para todos os objetos
        camera_transform = geo3d.Transform3D()
        
        # Aplicar translação (afastar câmera)
        camera_transform = geo3d.Transform3D.translation(0, 0, -self.camera_distance) * camera_transform
        
        # Aplicar rotações da câmera
        rot_x_rad = math.radians(self.camera_rot_x)
        rot_y_rad = math.radians(self.camera_rot_y)
        
        # Rotação X (pitch)
        camera_transform = geo3d.Transform3D.rotation_euler(rot_x_rad, 0, 0) * camera_transform
        
        # Rotação Y (yaw)
        camera_transform = geo3d.Transform3D.rotation_euler(0, rot_y_rad, 0) * camera_transform
        
        # Desenhar todos os objetos
        for obj in self.objects:
            # Aplicar transformações da câmera aos vértices
            vertices_3d = obj.get_transformed_vertices()
            
            # Aplicar transformação da câmera aos vértices
            vertices_camera = []
            for v3d in vertices_3d:
                v_camera = camera_transform.apply_to_point(v3d)
                vertices_camera.append(v_camera)
            
            # Projeta os vértices
            vertices_2d = []
            for v3d in vertices_camera:
                v2d = self.projection.project(v3d)
                vertices_2d.append(v2d)
            
            # Desenha faces se habilitado
            if self.show_faces and obj.faces:
                painter.setPen(Qt.NoPen)
                # Usar cor do objeto se existir, senão usar cor padrão
                if hasattr(obj, 'color'):
                    r, g, b, alpha = obj.color
                    obj_color = QColor(int(r * 255), int(g * 255), int(b * 255), int(alpha * 255))
                else:
                    obj_color = self.fill_color
                painter.setBrush(obj_color)
                
                for face in obj.faces:
                    if len(face) >= 3:
                        points = []
                        for idx in face:
                            if idx < len(vertices_2d):
                                x, y = vertices_2d[idx]
                                points.append(QPoint(int(x), int(y)))
                        
                        if len(points) >= 3:
                            from PyQt5.QtGui import QPolygon
                            polygon = QPolygon(points)
                            painter.drawPolygon(polygon)
            
            # Desenha arestas se habilitado
            if self.show_edges:
                pen = QPen(self.edge_color)
                pen.setWidth(2)
                painter.setPen(pen)
                
                for i1, i2 in obj.edges:
                    if i1 < len(vertices_2d) and i2 < len(vertices_2d):
                        x1, y1 = vertices_2d[i1]
                        x2, y2 = vertices_2d[i2]
                        painter.drawLine(int(x1), int(y1), int(x2), int(y2))
    
    def mousePressEvent(self, event):
        """Inicia rotação quando o botão esquerdo é pressionado"""
        if event.button() == Qt.LeftButton:
            self.last_mouse_pos = event.pos()
            self.setFocus()
    
    def mouseMoveEvent(self, event):
        """Rotaciona a câmera quando o mouse se move com botão pressionado"""
        if event.buttons() & Qt.LeftButton and self.last_mouse_pos is not None:
            # Calcular diferença de movimento
            dx = event.x() - self.last_mouse_pos.x()
            dy = event.y() - self.last_mouse_pos.y()
            
            # Atualizar rotação da câmera
            self.camera_rot_y += dx * self.mouse_sensitivity
            self.camera_rot_x += dy * self.mouse_sensitivity
            
            # Limitar rotação X para evitar gimbal lock
            self.camera_rot_x = max(-90.0, min(90.0, self.camera_rot_x))
            
            self.last_mouse_pos = event.pos()
            self.update()
    
    def mouseReleaseEvent(self, event):
        """Para a rotação quando o botão é solto"""
        if event.button() == Qt.LeftButton:
            self.last_mouse_pos = None
    
    def wheelEvent(self, event):
        """Zoom com a roda do mouse"""
        delta = event.angleDelta().y() / 120.0  # Normalizar
        zoom_factor = 1.1 if delta > 0 else 0.9
        self.camera_distance *= zoom_factor
        self.camera_distance = max(50.0, min(1000.0, self.camera_distance))
        self.update()
    
    def keyPressEvent(self, event):
        """Zoom com teclas 1 e 2"""
        if event.key() == Qt.Key_1:
            # Zoom in (tecla 1)
            zoom_factor = 1.1
            self.camera_distance *= zoom_factor
            self.camera_distance = max(50.0, min(1000.0, self.camera_distance))
            self.update()
        elif event.key() == Qt.Key_2:
            # Zoom out (tecla 2)
            zoom_factor = 0.9
            self.camera_distance *= zoom_factor
            self.camera_distance = max(50.0, min(1000.0, self.camera_distance))
            self.update()
        else:
            super().keyPressEvent(event)


# ============================================================================
# CanvasPhong - Renderização com Phong Shading (Scan Line)
# ============================================================================

class CanvasPhong(QWidget):
    """
    Canvas para renderização 3D com Phong shading usando scan line
    
    Características:
    - Renderização por scan line com interpolação Gouraud
    - Z-buffer para oclusão
    - Iluminação Phong simplificada
    - Controle de câmera e luz
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.objects: List[geo3d.Object3D] = []
        self.current_object: Optional[geo3d.Object3D] = None
        self.projection: geo3d.Projection = geo3d.OrthographicProjection()
        self.is_perspective = False
        
        # Renderizador Phong
        self.phong_renderer: Optional[ScanLinePhong] = None
        
        # Controle de câmera
        self.camera_rot_x = 30.0
        self.camera_rot_y = 45.0
        self.camera_distance = 300.0
        self.last_mouse_pos = None
        self.mouse_sensitivity = 0.5
        
        # Posição da luz (sincronizada com OpenGL)
        self.light_position = geo3d.Vector3D(200.0, 200.0, 200.0)
        
        self.setMinimumSize(800, 600)
        self.setMouseTracking(True)
        # Habilitar foco para receber eventos de teclado
        self.setFocusPolicy(Qt.StrongFocus)
    
    def add_object(self, obj: geo3d.Object3D):
        """Adiciona um objeto 3D"""
        self.objects.append(obj)
        if self.current_object is None:
            self.current_object = obj
        self.update()
    
    def clear_objects(self):
        """Limpa todos os objetos"""
        self.objects.clear()
        self.current_object = None
        self.update()
    
    def set_projection(self, is_perspective: bool, distance: float = 500.0):
        """Define o tipo de projeção"""
        self.is_perspective = is_perspective
        if is_perspective:
            self.projection = geo3d.PerspectiveProjection(distance)
        else:
            self.projection = geo3d.OrthographicProjection()
        self.phong_renderer = None  # Reinicializar renderizador
        self.update()
    
    def set_light_position(self, x: float, y: float, z: float):
        """Define a posição da fonte de luz"""
        self.light_position = geo3d.Vector3D(x, y, z)
        if self.phong_renderer:
            self.phong_renderer.set_light_position(x, y, z)
        self.update()
    
    def resizeEvent(self, event):
        """Reinicializa o renderizador quando o tamanho muda"""
        self.phong_renderer = None
        super().resizeEvent(event)
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Limpar fundo
        painter.fillRect(self.rect(), QColor(20, 20, 30))
        
        if not self.objects:
            # Mostrar aviso quando não há objetos
            painter.setPen(QColor(200, 200, 200))
            painter.drawText(self.rect(), Qt.AlignCenter, "Adicione objetos para visualizar com Phong Shading (Scan Line)")
            return
        
        # Inicializar renderizador se necessário
        if self.phong_renderer is None or (
            self.phong_renderer.width != self.width() or 
            self.phong_renderer.height != self.height()
        ):
            self.phong_renderer = ScanLinePhong(self.width(), self.height())
        
        # Limpar buffers
        self.phong_renderer.clear(QColor(20, 20, 30))
        
        # Configurar luz
        self.phong_renderer.set_light_position(
            self.light_position.x,
            self.light_position.y,
            self.light_position.z
        )
        
        # Configurar posição do observador
        rot_x_rad = math.radians(self.camera_rot_x)
        rot_y_rad = math.radians(self.camera_rot_y)
        
        # Calcular posição do observador baseada na rotação da câmera
        viewer_x = self.camera_distance * math.sin(rot_y_rad) * math.cos(rot_x_rad)
        viewer_y = self.camera_distance * math.sin(rot_x_rad)
        viewer_z = self.camera_distance * math.cos(rot_y_rad) * math.cos(rot_x_rad)
        
        self.phong_renderer.set_viewer_position(viewer_x, viewer_y, viewer_z)
        
        # Transformação da câmera
        camera_transform = geo3d.Transform3D.translation(
            self.width() / 2.0,
            self.height() / 2.0,
            0.0
        )
        
        # Rotação X (pitch)
        rot_x_transform = geo3d.Transform3D.rotation_euler(rot_x_rad, 0, 0)
        camera_transform = camera_transform * rot_x_transform
        
        # Rotação Y (yaw)
        rot_y_transform = geo3d.Transform3D.rotation_euler(0, rot_y_rad, 0)
        camera_transform = camera_transform * rot_y_transform
        
        # Renderizar todos os objetos
        for obj in self.objects:
            vertices_3d = obj.get_transformed_vertices()
            
            # Calcular normais
            face_normals = self._calculate_face_normals(obj, vertices_3d)
            vertex_normals = self._calculate_vertex_normals(obj, vertices_3d, face_normals)
            
            # Aplicar transformação da câmera
            vertices_camera = []
            for v3d in vertices_3d:
                v_camera = camera_transform.apply_to_point(v3d)
                vertices_camera.append(v_camera)
            
            # Projetar vértices
            vertices_2d = []
            for v3d in vertices_camera:
                v2d = self.projection.project(v3d)
                vertices_2d.append(v2d)
            
            # Configurar material baseado na cor do objeto
            if hasattr(obj, 'color'):
                r, g, b, alpha = obj.color
            else:
                r, g, b, alpha = 0.5, 0.6, 0.8, 1.0
            
            self.phong_renderer.set_material_properties(
                ambient=(r * 0.5, g * 0.5, b * 0.5),  # Aumentado de 0.3 para 0.5
                diffuse=(r, g, b),
                specular=(1.0, 1.0, 1.0),
                shininess=128.0
            )
            
            # Renderizar faces como triângulos
            for face in obj.faces:
                if len(face) < 3:
                    continue
                
                # Triangulizar face de forma mais equilibrada
                # Para faces com 4 vértices (quadrados), usar divisão diagonal oposta
                if len(face) == 4:
                    # Dividir quadrado em 2 triângulos usando diagonal oposta
                    # Triângulo 1: (0, 1, 2)
                    idx0, idx1, idx2 = face[0], face[1], face[2]
                    if (idx0 < len(vertices_2d) and idx1 < len(vertices_2d) and 
                        idx2 < len(vertices_2d) and
                        idx0 < len(vertices_camera) and idx1 < len(vertices_camera) and
                        idx2 < len(vertices_camera) and
                        idx0 < len(vertex_normals) and idx1 < len(vertex_normals) and
                        idx2 < len(vertex_normals)):
                        self.phong_renderer.render_triangle(
                            vertices_2d[idx0], vertices_2d[idx1], vertices_2d[idx2],
                            vertices_camera[idx0], vertices_camera[idx1], vertices_camera[idx2],
                            vertex_normals[idx0], vertex_normals[idx1], vertex_normals[idx2]
                        )
                    
                    # Triângulo 2: (0, 2, 3) - usando diagonal oposta
                    idx0, idx1, idx2 = face[0], face[2], face[3]
                    if (idx0 < len(vertices_2d) and idx1 < len(vertices_2d) and 
                        idx2 < len(vertices_2d) and
                        idx0 < len(vertices_camera) and idx1 < len(vertices_camera) and
                        idx2 < len(vertices_camera) and
                        idx0 < len(vertex_normals) and idx1 < len(vertex_normals) and
                        idx2 < len(vertex_normals)):
                        self.phong_renderer.render_triangle(
                            vertices_2d[idx0], vertices_2d[idx1], vertices_2d[idx2],
                            vertices_camera[idx0], vertices_camera[idx1], vertices_camera[idx2],
                            vertex_normals[idx0], vertex_normals[idx1], vertex_normals[idx2]
                        )
                else:
                    # Para outras faces (triângulos ou polígonos com mais de 4 vértices)
                    # Usar triangulação em fan a partir do primeiro vértice
                    for i in range(1, len(face) - 1):
                        idx0 = face[0]
                        idx1 = face[i]
                        idx2 = face[i + 1]
                        
                        if (idx0 < len(vertices_2d) and idx1 < len(vertices_2d) and 
                            idx2 < len(vertices_2d) and
                            idx0 < len(vertices_camera) and idx1 < len(vertices_camera) and
                            idx2 < len(vertices_camera) and
                            idx0 < len(vertex_normals) and idx1 < len(vertex_normals) and
                            idx2 < len(vertex_normals)):
                            
                            self.phong_renderer.render_triangle(
                                vertices_2d[idx0], vertices_2d[idx1], vertices_2d[idx2],
                                vertices_camera[idx0], vertices_camera[idx1], vertices_camera[idx2],
                                vertex_normals[idx0], vertex_normals[idx1], vertex_normals[idx2]
                            )
        
        # Desenhar a imagem renderizada
        painter.drawImage(0, 0, self.phong_renderer.get_image())
        
        # Desenhar representação visual da fonte de luz
        self._draw_light_representation(painter)
    
    def _calculate_face_normals(self, obj: geo3d.Object3D, vertices: List[geo3d.Point3D]) -> List[Tuple[float, float, float]]:
        """Calcula normais das faces"""
        normals = []
        for face in obj.faces:
            if len(face) < 3:
                normals.append((0.0, 0.0, 1.0))
                continue
            
            idx0, idx1, idx2 = face[0], face[1], face[2]
            if idx0 >= len(vertices) or idx1 >= len(vertices) or idx2 >= len(vertices):
                normals.append((0.0, 0.0, 1.0))
                continue
            
            v0 = geo3d.Vector3D.from_tuple(vertices[idx0])
            v1 = geo3d.Vector3D.from_tuple(vertices[idx1])
            v2 = geo3d.Vector3D.from_tuple(vertices[idx2])
            
            edge1 = v1 - v0
            edge2 = v2 - v0
            normal = edge1.cross(edge2).normalize()
            
            normals.append(normal.to_tuple())
        return normals
    
    def _calculate_vertex_normals(self, obj: geo3d.Object3D, vertices: List[geo3d.Point3D],
                                  face_normals: List[Tuple[float, float, float]]) -> List[Tuple[float, float, float]]:
        """Calcula normais dos vértices (média das normais das faces adjacentes)"""
        vertex_normals = [(0.0, 0.0, 0.0) for _ in vertices]
        vertex_face_count = [0 for _ in vertices]
        
        for face_idx, face in enumerate(obj.faces):
            if face_idx >= len(face_normals):
                continue
            
            normal = geo3d.Vector3D.from_tuple(face_normals[face_idx])
            
            for vertex_idx in face:
                if vertex_idx < len(vertices):
                    current_normal = geo3d.Vector3D.from_tuple(vertex_normals[vertex_idx])
                    vertex_normals[vertex_idx] = (current_normal + normal).to_tuple()
                    vertex_face_count[vertex_idx] += 1
        
        # Normalizar
        result = []
        for i, normal in enumerate(vertex_normals):
            if vertex_face_count[i] > 0:
                normal_vec = geo3d.Vector3D.from_tuple(normal).normalize()
                result.append(normal_vec.to_tuple())
            else:
                result.append((0.0, 0.0, 1.0))
        
        return result
    
    def _draw_light_representation(self, painter: QPainter):
        """Desenha uma representação visual da fonte de luz"""
        if not self.objects:
            return
        
        # Aplicar a mesma transformação de câmera usada para os objetos
        rot_x_rad = math.radians(self.camera_rot_x)
        rot_y_rad = math.radians(self.camera_rot_y)
        
        camera_transform = geo3d.Transform3D.translation(
            self.width() / 2.0,
            self.height() / 2.0,
            0.0
        )
        
        # Rotação X (pitch)
        rot_x_transform = geo3d.Transform3D.rotation_euler(rot_x_rad, 0, 0)
        camera_transform = camera_transform * rot_x_transform
        
        # Rotação Y (yaw)
        rot_y_transform = geo3d.Transform3D.rotation_euler(0, rot_y_rad, 0)
        camera_transform = camera_transform * rot_y_transform
        
        # Posição 3D da luz
        light_pos_3d = (self.light_position.x, self.light_position.y, self.light_position.z)
        
        # Aplicar transformação da câmera
        light_camera = camera_transform.apply_to_point(light_pos_3d)
        
        # Projetar para 2D
        light_2d = self.projection.project(light_camera)
        
        # Verificar se a luz está visível na tela
        x, y = light_2d
        if x < -100 or x > self.width() + 100 or y < -100 or y > self.height() + 100:
            return  # Luz fora da tela
        
        # Desenhar círculo amarelo brilhante para a luz
        painter.save()
        
        # Círculo principal (amarelo brilhante)
        light_color = QColor(255, 255, 100)  # Amarelo brilhante
        painter.setPen(QPen(light_color, 2))
        painter.setBrush(QColor(255, 255, 150, 200))  # Amarelo com transparência
        
        radius = 12.0
        painter.drawEllipse(int(x - radius), int(y - radius), int(radius * 2), int(radius * 2))
        
        # Desenhar raios de luz (linhas amarelas)
        painter.setPen(QPen(QColor(255, 255, 200), 1.5))
        num_rays = 8
        ray_length = 18.0
        
        for i in range(num_rays):
            angle = 2.0 * math.pi * i / num_rays
            end_x = x + math.cos(angle) * ray_length
            end_y = y + math.sin(angle) * ray_length
            painter.drawLine(int(x), int(y), int(end_x), int(end_y))
        
        # Círculo interno mais brilhante
        painter.setBrush(QColor(255, 255, 200))
        inner_radius = 6.0
        painter.drawEllipse(int(x - inner_radius), int(y - inner_radius), 
                           int(inner_radius * 2), int(inner_radius * 2))
        
        painter.restore()
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.last_mouse_pos = event.pos()
            # Garantir foco para receber eventos de teclado
            self.setFocus()
    
    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton and self.last_mouse_pos:
            dx = event.x() - self.last_mouse_pos.x()
            dy = event.y() - self.last_mouse_pos.y()
            
            self.camera_rot_y += dx * self.mouse_sensitivity
            self.camera_rot_x -= dy * self.mouse_sensitivity
            
            # Limitar rotação X
            self.camera_rot_x = max(-90.0, min(90.0, self.camera_rot_x))
            
            self.last_mouse_pos = event.pos()
            self.update()
    
    def mouseReleaseEvent(self, event):
        self.last_mouse_pos = None
    
    def wheelEvent(self, event):
        delta = event.angleDelta().y() / 120.0
        self.camera_distance = max(50.0, min(1000.0, self.camera_distance - delta * 10.0))
        self.update()
    
    def keyPressEvent(self, event):
        """Zoom com teclas 1 e 2"""
        if event.key() == Qt.Key_1:
            # Zoom in (tecla 1)
            zoom_factor = 1.1
            self.camera_distance *= zoom_factor
            self.camera_distance = max(50.0, min(1000.0, self.camera_distance))
            self.update()
        elif event.key() == Qt.Key_2:
            # Zoom out (tecla 2)
            zoom_factor = 0.9
            self.camera_distance *= zoom_factor
            self.camera_distance = max(50.0, min(1000.0, self.camera_distance))
            self.update()
        else:
            super().keyPressEvent(event)


# ============================================================================
# MainWindow - Janela Principal
# ============================================================================

class MainWindow(QMainWindow):
    """
    Janela principal da aplicação
    
    Organização:
    - Abas: Canvas 2D, Visualização 2D, OpenGL, Phong Scan Line
    - Painel de controles: Transformações, Iluminação, Projeção, etc.
    """
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SimplePaint - Computação Gráfica")
        
        # Definir ícone da aplicação
        from PyQt5.QtGui import QIcon
        import os
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'icon.ico')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        # Criar splitter para dividir visualização e controles (50/50)
        splitter = QSplitter(Qt.Horizontal, self)
        
        # Painel esquerdo: Visualização (50% da tela)
        from PyQt5.QtWidgets import QTabWidget, QScrollArea
        self.viewer_tabs = QTabWidget()
        
        # Canvas 2D como primeira aba
        self.canvas = Canvas(self)
        self.viewer_tabs.addTab(self.canvas, "Desenho 2D")
        
        # Viewer 2D (QPainter)
        self.canvas3d = Canvas3D(self)
        self.viewer_tabs.addTab(self.canvas3d, "Visualização 2D")
        
        # Viewer OpenGL com iluminação
        self.opengl_viewer = OpenGLViewer(self)
        self.viewer_tabs.addTab(self.opengl_viewer, "OpenGL (Iluminação)")
        
        # Viewer Phong com scan line
        self.phong_viewer = CanvasPhong(self)
        self.viewer_tabs.addTab(self.phong_viewer, "Phong (Scan Line)")
        
        # Conectar callback para sincronizar posição da luz
        self.opengl_viewer.on_light_position_changed = self._sync_light_controls
        
        # Conectar callback para atualizar 3D quando polígono 2D mudar
        self.canvas.on_polygon_changed = self._on_polygon_2d_changed
        
        # Painel direito: Controles (50% da tela)
        controls_panel = QWidget()
        controls_layout = QVBoxLayout(controls_panel)
        
        # Criar área com scroll para os controles
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # Controles 3D
        controls_3d = self._create_3d_controls()
        scroll.setWidget(controls_3d)
        controls_layout.addWidget(scroll)
        
        # Adicionar ao splitter com proporção 50/50
        splitter.addWidget(self.viewer_tabs)
        splitter.addWidget(controls_panel)
        
        # Definir tamanhos iniciais (50/50)
        splitter.setSizes([500, 500])
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        
        self.setCentralWidget(splitter)
        self.status = QStatusBar(self)
        self.setStatusBar(self.status)
        self._create_toolbar()
        self.resize(1400, 800)

    def _create_toolbar(self):
        """Cria a barra de ferramentas organizada por categorias"""
        tb = QToolBar("Ferramentas", self)
        tb.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.addToolBar(tb)

        # === SEÇÃO 1: OBJETOS 3D ===
        tb.addWidget(QLabel("📦 Objetos 3D:"))
        self.create_elements_combo = QComboBox()
        self.create_elements_combo.addItems([
            "-- Selecionar Forma --",
            "Cubo",
            "Pirâmide",
            "Cilindro",
            "Semiesfera",
            "Esfera"
        ])
        self.create_elements_combo.currentIndexChanged.connect(self._on_create_element_selected)
        self.create_elements_combo.setMaximumWidth(150)
        tb.addWidget(self.create_elements_combo)
        
        self.create_element_btn = QPushButton("Criar")
        self.create_element_btn.clicked.connect(lambda: self._on_create_element_selected(self.create_elements_combo.currentIndex()))
        tb.addWidget(self.create_element_btn)
        
        tb.addSeparator()

        # === SEÇÃO 2: DESENHO 2D ===
        tb.addWidget(QLabel("✏️ Desenho:"))
        
        act_clear = QAction("Limpar", self)
        act_clear.triggered.connect(self.canvas.clear)
        tb.addAction(act_clear)

        act_undo = QAction("Desfazer", self)
        act_undo.triggered.connect(self.canvas.undo)
        tb.addAction(act_undo)

        act_close = QAction("Fechar", self)
        act_close.triggered.connect(self.canvas.close_polygon)
        tb.addAction(act_close)

        act_fillpoly = QAction("Preencher", self)
        act_fillpoly.triggered.connect(self.canvas.fill_polygon)
        tb.addAction(act_fillpoly)
        
        tb.addSeparator()

        # === SEÇÃO 3: CORES E ESTILO ===
        tb.addWidget(QLabel("🎨 Cores:"))
        
        act_stroke = QAction("Contorno", self)
        act_stroke.triggered.connect(self._choose_stroke_color)
        tb.addAction(act_stroke)

        act_fill = QAction("Preenchimento", self)
        act_fill.triggered.connect(self._choose_fill_color)
        tb.addAction(act_fill)

        tb.addWidget(QLabel("Espessura:"))
        spin = QSpinBox(self)
        spin.setRange(1, 20)
        spin.setValue(self.canvas.stroke_width)
        spin.setMaximumWidth(60)
        spin.valueChanged.connect(self.canvas.set_stroke_width)
        tb.addWidget(spin)
        
        tb.addSeparator()

        # === SEÇÃO 4: EXTRUSÃO ===
        act_extrude = QAction("Extrudar", self)
        act_extrude.triggered.connect(self._extrude_polygon)
        tb.addAction(act_extrude)
        
        act_clear_3d = QAction("Limpar 3D", self)
        act_clear_3d.triggered.connect(self._clear_3d_objects)
        tb.addAction(act_clear_3d)
    
    def _create_3d_controls(self) -> QWidget:
        """Cria os controles para transformações 3D organizados por seções"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # === SEÇÃO 1: SELEÇÃO DE OBJETO ===
        obj_selection_group = QGroupBox("📦 Objeto Ativo")
        obj_selection_layout = QVBoxLayout()
        
        self.object_selection_combo = QComboBox()
        self.object_selection_combo.currentIndexChanged.connect(self._on_object_selected)
        obj_selection_layout.addWidget(self.object_selection_combo)
        
        obj_selection_group.setLayout(obj_selection_layout)
        layout.addWidget(obj_selection_group)
        
        # === SEÇÃO 2: PROJEÇÃO ===
        proj_group = QGroupBox("📐 Projeção")
        proj_layout = QVBoxLayout()
        
        self.proj_combo = QComboBox()
        self.proj_combo.addItems(["Ortográfica", "Perspectiva"])
        self.proj_combo.currentIndexChanged.connect(self._on_projection_changed)
        proj_layout.addWidget(QLabel("Tipo:"))
        proj_layout.addWidget(self.proj_combo)
        
        self.distance_spin = QDoubleSpinBox()
        self.distance_spin.setRange(100.0, 2000.0)
        self.distance_spin.setValue(500.0)
        self.distance_spin.setSuffix(" px")
        self.distance_spin.valueChanged.connect(self._on_distance_changed)
        proj_layout.addWidget(QLabel("Distância (Perspectiva):"))
        proj_layout.addWidget(self.distance_spin)
        
        proj_group.setLayout(proj_layout)
        layout.addWidget(proj_group)
        
        # === SEÇÃO 3: TRANSFORMAÇÕES ===
        transform_group = QGroupBox("🔄 Transformações")
        transform_layout = QVBoxLayout()
        
        # Translação
        trans_layout = QHBoxLayout()
        trans_layout.addWidget(QLabel("Translação:"))
        self.tx_spin = QDoubleSpinBox()
        self.tx_spin.setRange(-500.0, 500.0)
        self.tx_spin.setValue(0.0)
        self.tx_spin.setSingleStep(10.0)
        self.tx_spin.valueChanged.connect(self._update_transform)
        trans_layout.addWidget(QLabel("X:"))
        trans_layout.addWidget(self.tx_spin)
        
        self.ty_spin = QDoubleSpinBox()
        self.ty_spin.setRange(-500.0, 500.0)
        self.ty_spin.setValue(0.0)
        self.ty_spin.setSingleStep(10.0)
        self.ty_spin.valueChanged.connect(self._update_transform)
        trans_layout.addWidget(QLabel("Y:"))
        trans_layout.addWidget(self.ty_spin)
        
        self.tz_spin = QDoubleSpinBox()
        self.tz_spin.setRange(-500.0, 500.0)
        self.tz_spin.setValue(0.0)
        self.tz_spin.setSingleStep(10.0)
        self.tz_spin.valueChanged.connect(self._update_transform)
        trans_layout.addWidget(QLabel("Z:"))
        trans_layout.addWidget(self.tz_spin)
        transform_layout.addLayout(trans_layout)
        
        # Rotação (em graus)
        rot_layout = QHBoxLayout()
        rot_layout.addWidget(QLabel("Rotação (graus):"))
        self.rx_spin = QDoubleSpinBox()
        self.rx_spin.setRange(-360.0, 360.0)
        self.rx_spin.setValue(0.0)
        self.rx_spin.setSingleStep(10.0)
        self.rx_spin.valueChanged.connect(self._update_transform)
        rot_layout.addWidget(QLabel("X:"))
        rot_layout.addWidget(self.rx_spin)
        
        self.ry_spin = QDoubleSpinBox()
        self.ry_spin.setRange(-360.0, 360.0)
        self.ry_spin.setValue(0.0)
        self.ry_spin.setSingleStep(10.0)
        self.ry_spin.valueChanged.connect(self._update_transform)
        rot_layout.addWidget(QLabel("Y:"))
        rot_layout.addWidget(self.ry_spin)
        
        self.rz_spin = QDoubleSpinBox()
        self.rz_spin.setRange(-360.0, 360.0)
        self.rz_spin.setValue(0.0)
        self.rz_spin.setSingleStep(10.0)
        self.rz_spin.valueChanged.connect(self._update_transform)
        rot_layout.addWidget(QLabel("Z:"))
        rot_layout.addWidget(self.rz_spin)
        transform_layout.addLayout(rot_layout)
        
        # Escala
        scale_layout = QHBoxLayout()
        scale_layout.addWidget(QLabel("Escala:"))
        self.sx_spin = QDoubleSpinBox()
        self.sx_spin.setRange(0.1, 5.0)
        self.sx_spin.setValue(1.0)
        self.sx_spin.setSingleStep(0.1)
        self.sx_spin.valueChanged.connect(self._update_transform)
        scale_layout.addWidget(QLabel("X:"))
        scale_layout.addWidget(self.sx_spin)
        
        self.sy_spin = QDoubleSpinBox()
        self.sy_spin.setRange(0.1, 5.0)
        self.sy_spin.setValue(1.0)
        self.sy_spin.setSingleStep(0.1)
        self.sy_spin.valueChanged.connect(self._update_transform)
        scale_layout.addWidget(QLabel("Y:"))
        scale_layout.addWidget(self.sy_spin)
        
        self.sz_spin = QDoubleSpinBox()
        self.sz_spin.setRange(0.1, 5.0)
        self.sz_spin.setValue(1.0)
        self.sz_spin.setSingleStep(0.1)
        self.sz_spin.valueChanged.connect(self._update_transform)
        scale_layout.addWidget(QLabel("Z:"))
        scale_layout.addWidget(self.sz_spin)
        transform_layout.addLayout(scale_layout)
        
        # Botão reset
        reset_btn = QPushButton("Reset Transformações")
        reset_btn.clicked.connect(self._reset_transform)
        transform_layout.addWidget(reset_btn)
        
        transform_group.setLayout(transform_layout)
        layout.addWidget(transform_group)
        
        # === SEÇÃO 4: VISUALIZAÇÃO ===
        vis_group = QGroupBox("👁️ Visualização")
        vis_layout = QVBoxLayout()
        
        self.show_edges_check = QCheckBox("Mostrar Arestas")
        self.show_edges_check.setChecked(True)
        self.show_edges_check.toggled.connect(self.canvas3d.set_show_edges)
        vis_layout.addWidget(self.show_edges_check)
        
        self.show_faces_check = QCheckBox("Mostrar Faces")
        self.show_faces_check.setChecked(True)
        self.show_faces_check.toggled.connect(self.canvas3d.set_show_faces)
        vis_layout.addWidget(self.show_faces_check)
        
        # Cor do objeto 3D
        color_3d_layout = QHBoxLayout()
        color_3d_layout.addWidget(QLabel("Cor do Objeto 3D:"))
        self.color_3d_btn = QPushButton()
        self.color_3d_btn.setFixedSize(60, 30)
        self.color_3d_btn.setStyleSheet(f"background-color: rgb(100, 150, 255);")
        self.color_3d_btn.clicked.connect(self._choose_3d_color)
        color_3d_layout.addWidget(self.color_3d_btn)
        color_3d_layout.addStretch()
        vis_layout.addLayout(color_3d_layout)
        
        vis_group.setLayout(vis_layout)
        layout.addWidget(vis_group)
        
        # === SEÇÃO 5: ILUMINAÇÃO ===
        light_group = QGroupBox("💡 Iluminação (OpenGL)")
        light_layout = QVBoxLayout()
        
        # Modelo de iluminação
        self.shading_combo = QComboBox()
        self.shading_combo.addItems(["Flat", "Gouraud", "Phong"])
        self.shading_combo.currentIndexChanged.connect(self._on_shading_changed)
        light_layout.addWidget(QLabel("Modelo:"))
        light_layout.addWidget(self.shading_combo)
        
        # Posição da luz
        light_pos_layout = QHBoxLayout()
        light_pos_layout.addWidget(QLabel("Posição da Luz:"))
        
        self.light_x_spin = QDoubleSpinBox()
        self.light_x_spin.setRange(-500.0, 500.0)
        self.light_x_spin.setValue(200.0)
        self.light_x_spin.valueChanged.connect(self._update_light_position)
        light_pos_layout.addWidget(QLabel("X:"))
        light_pos_layout.addWidget(self.light_x_spin)
        
        self.light_y_spin = QDoubleSpinBox()
        self.light_y_spin.setRange(-500.0, 500.0)
        self.light_y_spin.setValue(200.0)
        self.light_y_spin.valueChanged.connect(self._update_light_position)
        light_pos_layout.addWidget(QLabel("Y:"))
        light_pos_layout.addWidget(self.light_y_spin)
        
        self.light_z_spin = QDoubleSpinBox()
        self.light_z_spin.setRange(-500.0, 500.0)
        self.light_z_spin.setValue(200.0)
        self.light_z_spin.valueChanged.connect(self._update_light_position)
        light_pos_layout.addWidget(QLabel("Z:"))
        light_pos_layout.addWidget(self.light_z_spin)
        light_layout.addLayout(light_pos_layout)
        
        light_group.setLayout(light_layout)
        layout.addWidget(light_group)
        
        # === SEÇÃO 6: CONTROLES OPENGL ===
        opengl_group = QGroupBox("🎮 Controles OpenGL")
        opengl_layout = QVBoxLayout()
        
        self.show_light_vis_check = QCheckBox("Mostrar Fonte de Luz")
        self.show_light_vis_check.setChecked(True)
        self.show_light_vis_check.toggled.connect(self._toggle_light_representation)
        opengl_layout.addWidget(self.show_light_vis_check)
        
        opengl_layout.addWidget(QLabel("🖱️ Rotação: Arraste com botão esquerdo"))
        opengl_layout.addWidget(QLabel("🔍 Zoom: Roda do mouse ou teclas 1/2"))
        opengl_layout.addWidget(QLabel("💡 Mover Luz: Setas (←→↑↓) e PgUp/PgDn"))
        
        opengl_group.setLayout(opengl_layout)
        layout.addWidget(opengl_group)
        
        # === SEÇÃO 7: CONTROLES VISUALIZAÇÃO 2D ===
        view2d_group = QGroupBox("🎮 Controles Visualização 2D")
        view2d_layout = QVBoxLayout()
        view2d_layout.addWidget(QLabel("🖱️ Rotação: Arraste com botão esquerdo"))
        view2d_layout.addWidget(QLabel("🔍 Zoom: Roda do mouse ou teclas 1/2"))
        view2d_group.setLayout(view2d_layout)
        layout.addWidget(view2d_group)
        
        layout.addStretch()
        return widget

    def _choose_stroke_color(self):
        color = QColorDialog.getColor(self.canvas.stroke_color, self, "Choose Stroke Color")
        if color.isValid():
            self.canvas.set_stroke_color(color)
            self.canvas3d.set_edge_color(color)

    def _choose_fill_color(self):
        color = QColorDialog.getColor(self.canvas.fill_color, self, "Choose Fill Color")
        if color.isValid():
            self.canvas.set_fill_color(color)
            self.canvas3d.set_fill_color(color)
            # Atualizar cor do material no OpenGL
            r = color.red() / 255.0
            g = color.green() / 255.0
            b = color.blue() / 255.0
            alpha = color.alpha() / 255.0
            self.opengl_viewer.set_material_color(r, g, b, alpha)
            # Atualizar botão de cor 3D também
            self._update_3d_color_button(color)
    
    def _choose_3d_color(self):
        """Abre diálogo para escolher cor do objeto 3D ativo"""
        if not self.canvas3d.current_object:
            QMessageBox.warning(self, "Aviso", "Selecione um objeto primeiro!")
            return
        
        # Obter cor atual do objeto selecionado
        if hasattr(self.canvas3d.current_object, 'color'):
            r, g, b, alpha = self.canvas3d.current_object.color
            current_color = QColor(int(r * 255), int(g * 255), int(b * 255), int(alpha * 255))
        else:
            current_color = self.canvas3d.fill_color
        
        color = QColorDialog.getColor(current_color, self, "Escolher Cor do Objeto 3D")
        if color.isValid():
            # Atualizar cor apenas do objeto selecionado
            r = color.red() / 255.0
            g = color.green() / 255.0
            b = color.blue() / 255.0
            alpha = color.alpha() / 255.0
            self.canvas3d.current_object.color = (r, g, b, alpha)
            
            # Atualizar visualizações
            self.canvas3d.update()
            self.opengl_viewer.update()
            
            # Atualizar botão com a nova cor
            self._update_3d_color_button(color)
    
    def _update_3d_color_button(self, color: QColor):
        """Atualiza a aparência do botão de cor 3D"""
        r, g, b = color.red(), color.green(), color.blue()
        self.color_3d_btn.setStyleSheet(f"background-color: rgb({r}, {g}, {b});")
    
    def _on_projection_changed(self, index: int):
        """Muda o tipo de projeção"""
        is_perspective = (index == 1)
        distance = self.distance_spin.value()
        self.canvas3d.set_projection(is_perspective, distance)
        self.opengl_viewer.set_projection(is_perspective, distance)
        self.phong_viewer.set_projection(is_perspective, distance)
        self.distance_spin.setEnabled(is_perspective)
    
    def _on_distance_changed(self, value: float):
        """Atualiza distância da projeção perspectiva"""
        if self.canvas3d.is_perspective:
            self.canvas3d.set_projection(True, value)
        self.opengl_viewer.set_projection(True, value)
        self.phong_viewer.set_projection(True, value)
    
    def _on_shading_changed(self, index: int):
        """Muda o modelo de shading"""
        if index == 0:
            model = 'flat'
        elif index == 1:
            model = 'gouraud'
        else:  # index == 2
            model = 'phong'
        self.opengl_viewer.set_shading_model(model)
    
    def _update_light_position(self):
        """Atualiza a posição da luz"""
        x = self.light_x_spin.value()
        y = self.light_y_spin.value()
        z = self.light_z_spin.value()
        self.opengl_viewer.set_light_position(x, y, z)
        self.phong_viewer.set_light_position(x, y, z)
    
    def _sync_light_controls(self, x: float, y: float, z: float):
        """Sincroniza os controles com a posição da luz (quando movida por teclado)"""
        self.light_x_spin.blockSignals(True)
        self.light_y_spin.blockSignals(True)
        self.light_z_spin.blockSignals(True)
        
        self.light_x_spin.setValue(x)
        self.light_y_spin.setValue(y)
        self.light_z_spin.setValue(z)
        
        self.light_x_spin.blockSignals(False)
        self.light_y_spin.blockSignals(False)
        self.light_z_spin.blockSignals(False)
    
    def _toggle_light_representation(self, checked: bool):
        """Alterna a visualização da fonte de luz"""
        self.opengl_viewer.show_light_representation = checked
        self.opengl_viewer.update()
    
    def _update_transform(self):
        """Atualiza transformações do objeto 3D atual"""
        if not self.canvas3d.current_object:
            return
        
        # Reset transformação antes de aplicar novas
        self.canvas3d.current_object.reset_transform()
        
        # Criar todas as transformações e compor
        tx = self.tx_spin.value()
        ty = self.ty_spin.value()
        tz = self.tz_spin.value()
        T = geo3d.Transform3D.translation(tx, ty, tz)
        
        # Rotação (convertendo graus para radianos)
        rx = math.radians(self.rx_spin.value())
        ry = math.radians(self.ry_spin.value())
        rz = math.radians(self.rz_spin.value())
        R = geo3d.Transform3D.rotation_euler(rx, ry, rz)
        
        # Escala
        sx = self.sx_spin.value()
        sy = self.sy_spin.value()
        sz = self.sz_spin.value()
        S = geo3d.Transform3D.scale(sx, sy, sz)
        
        # Compor transformações: Scale -> Rotate -> Translate (ordem correta)
        combined = T * R * S
        self.canvas3d.current_object.apply_transform(combined)
        if self.opengl_viewer.current_object == self.canvas3d.current_object:
            # Compartilhar o mesmo objeto, já aplicou transformação
            pass
        
        self.canvas3d.update()
        self.opengl_viewer.update()
        self.phong_viewer.update()
    
    def _on_object_selected(self, index: int):
        """Handler para quando um objeto é selecionado na lista"""
        if index < 0 or index >= len(self.canvas3d.objects):
            return
        
        # Definir o objeto atual
        selected_obj = self.canvas3d.objects[index]
        self.canvas3d.current_object = selected_obj
        self.opengl_viewer.current_object = selected_obj
        self.phong_viewer.current_object = selected_obj
        
        # Atualizar controles de transformação com os valores do objeto
        self._update_transform_controls_from_object(selected_obj)
        
        # Atualizar botão de cor com a cor do objeto selecionado
        if hasattr(selected_obj, 'color'):
            r, g, b, alpha = selected_obj.color
            obj_color = QColor(int(r * 255), int(g * 255), int(b * 255), int(alpha * 255))
        else:
            obj_color = self.canvas3d.fill_color
        self._update_3d_color_button(obj_color)
        
        # Atualizar visualizações
        self.canvas3d.update()
        self.opengl_viewer.update()
        self.phong_viewer.update()
    
    def _update_transform_controls_from_object(self, obj: geo3d.Object3D):
        """Atualiza os controles de transformação com os valores do objeto"""
        # Extrair transformações do objeto (simplificado - pode não ser preciso para todos os casos)
        # Por enquanto, apenas resetar os controles quando selecionar um objeto
        # O usuário pode ajustar manualmente
        pass
    
    def _update_object_list(self):
        """Atualiza a lista de objetos na interface"""
        self.object_selection_combo.blockSignals(True)
        self.object_selection_combo.clear()
        
        for i, obj in enumerate(self.canvas3d.objects):
            obj_name = f"Objeto {i + 1}"
            # Tentar identificar o tipo de objeto
            if hasattr(obj, 'vertices') and len(obj.vertices) == 8:
                obj_name = f"Cubo {i + 1}"
            elif hasattr(obj, 'vertices') and len(obj.vertices) == 5:
                obj_name = f"Pirâmide {i + 1}"
            # Adicionar mais identificações conforme necessário
            
            self.object_selection_combo.addItem(obj_name)
        
        # Selecionar o objeto atual
        if self.canvas3d.current_object and self.canvas3d.current_object in self.canvas3d.objects:
            current_idx = self.canvas3d.objects.index(self.canvas3d.current_object)
            self.object_selection_combo.setCurrentIndex(current_idx)
        elif len(self.canvas3d.objects) > 0:
            self.object_selection_combo.setCurrentIndex(0)
        
        self.object_selection_combo.blockSignals(False)
    
    def _reset_transform(self):
        """Reseta todas as transformações"""
        self.tx_spin.setValue(0.0)
        self.ty_spin.setValue(0.0)
        self.tz_spin.setValue(0.0)
        self.rx_spin.setValue(0.0)
        self.ry_spin.setValue(0.0)
        self.rz_spin.setValue(0.0)
        self.sx_spin.setValue(1.0)
        self.sy_spin.setValue(1.0)
        self.sz_spin.setValue(1.0)
        
        if self.canvas3d.current_object:
            self.canvas3d.current_object.reset_transform()
            self.canvas3d.update()
            self.opengl_viewer.update()
    
    def _extrude_polygon(self):
        """Extrui o polígono 2D atual para 3D"""
        if not self.canvas.is_closed or len(self.canvas.points) < 3:
            QMessageBox.warning(self, "Erro", "Feche o polígono primeiro (botão direito) antes de extrudar.")
            return
        
        # Perguntar profundidade (ou usar a profundidade anterior se já existir)
        from PyQt5.QtWidgets import QInputDialog
        current_depth = self.canvas.extrusion_depth if hasattr(self.canvas, 'extrusion_depth') else 100.0
        depth, ok = QInputDialog.getDouble(
            self, "Profundidade", "Digite a profundidade da extrusão:",
            current_depth, 10.0, 500.0, 1
        )
        
        if not ok:
            return
        
        try:
            obj_3d = geo3d.extrude_polygon_2d(self.canvas.points, depth)
            # Definir cor inicial do objeto
            fill_color = self.canvas3d.fill_color
            obj_3d.color = (fill_color.red() / 255.0, fill_color.green() / 255.0, 
                            fill_color.blue() / 255.0, fill_color.alpha() / 255.0)
            
            self.canvas.extruded_object = obj_3d
            self.canvas.extrusion_depth = depth
            
            # Se já existe objeto 3D, substituir; senão adicionar
            if self.canvas3d.current_object and self.canvas3d.current_object in self.canvas3d.objects:
                idx = self.canvas3d.objects.index(self.canvas3d.current_object)
                self.canvas3d.objects[idx] = obj_3d
                self.canvas3d.current_object = obj_3d
                
                # Atualizar também no OpenGL e Phong
                if idx < len(self.opengl_viewer.objects):
                    self.opengl_viewer.objects[idx] = obj_3d
                    if self.opengl_viewer.current_object == self.canvas3d.objects[idx]:
                        self.opengl_viewer.current_object = obj_3d
                if idx < len(self.phong_viewer.objects):
                    self.phong_viewer.objects[idx] = obj_3d
                    if self.phong_viewer.current_object == self.canvas3d.objects[idx]:
                        self.phong_viewer.current_object = obj_3d
            else:
                # Adicionar novo objeto sem limpar os existentes
                self.canvas3d.add_object(obj_3d)
                # Adicionar também no OpenGL e Phong
                self.opengl_viewer.objects = list(self.canvas3d.objects)
                self.opengl_viewer.current_object = self.canvas3d.current_object
                self.phong_viewer.objects = list(self.canvas3d.objects)
                self.phong_viewer.current_object = self.canvas3d.current_object
            
            # Atualizar lista de objetos
            self._update_object_list()
            
            # Atualizar botão de cor
            self._update_3d_color_button(fill_color)
            
            self.canvas3d.update()
            self.opengl_viewer.update()
            self.phong_viewer.update()
            self.status.showMessage(f"Polígono extrudado com profundidade {depth}", 3000)
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao extrudar polígono: {str(e)}")
    
    def _on_polygon_2d_changed(self):
        """Callback chamado quando o polígono 2D é modificado"""
        # Se há um objeto extrudado, atualizar automaticamente
        if self.canvas.extruded_object and self.canvas.is_closed and len(self.canvas.points) >= 3:
            obj_3d = self.canvas.update_extruded_object()
            
            if obj_3d:
                # Atualizar o objeto no canvas 3D
                old_obj = self.canvas.extruded_object
                
                # Preservar cor do objeto antigo
                if hasattr(old_obj, 'color'):
                    obj_3d.color = old_obj.color
                
                # Encontrar e substituir o objeto antigo na lista
                if old_obj in self.canvas3d.objects:
                    idx = self.canvas3d.objects.index(old_obj)
                    self.canvas3d.objects[idx] = obj_3d
                    
                    # Atualizar também no OpenGL e Phong
                    if idx < len(self.opengl_viewer.objects):
                        self.opengl_viewer.objects[idx] = obj_3d
                    if idx < len(self.phong_viewer.objects):
                        self.phong_viewer.objects[idx] = obj_3d
                    
                    # Se era o objeto atual, atualizar referência
                    if self.canvas3d.current_object == old_obj:
                        self.canvas3d.current_object = obj_3d
                    if self.opengl_viewer.current_object == old_obj:
                        self.opengl_viewer.current_object = obj_3d
                    if self.phong_viewer.current_object == old_obj:
                        self.phong_viewer.current_object = obj_3d
                    
                    self.canvas3d.update()
                    self.opengl_viewer.update()
                    self.phong_viewer.update()
                    # Atualizar transformações visuais também
                    self._update_transform()
    
    def _on_create_element_selected(self, index: int):
        """Handler para quando uma forma é selecionada na lista suspensa"""
        if index == 0:  # "-- Selecionar Forma --"
            return
        
        if index == 1:  # Cubo
            self._create_cube()
        elif index == 2:  # Pirâmide
            self._create_pyramid()
        elif index == 3:  # Cilindro
            self._create_cylinder()
        elif index == 4:  # Semiesfera
            self._create_hemisphere()
        elif index == 5:  # Esfera
            self._create_sphere()
        elif index == 6:  # Torus
            self._create_torus()
        elif index == 7:  # Cone
            self._create_cone()
        elif index == 8:  # Teapot
            self._create_teapot()
        
        # Resetar combo box após criar
        self.create_elements_combo.blockSignals(True)
        self.create_elements_combo.setCurrentIndex(0)
        self.create_elements_combo.blockSignals(False)
    
    def _create_cube(self):
        """Cria um cubo 3D"""
        from PyQt5.QtWidgets import QInputDialog
        size, ok = QInputDialog.getDouble(
            self, "Tamanho do Cubo", "Digite o tamanho do cubo:",
            100.0, 10.0, 500.0, 1
        )
        
        if not ok:
            return
        
        cube = geo3d.create_cube(size)
        # Definir cor inicial do objeto
        fill_color = self.canvas3d.fill_color
        cube.color = (fill_color.red() / 255.0, fill_color.green() / 255.0, 
                      fill_color.blue() / 255.0, fill_color.alpha() / 255.0)
        
        # Adicionar o mesmo objeto em ambos os viewers
        self.canvas3d.add_object(cube)
        # Sincronizar objetos: copiar a lista mas manter as mesmas instâncias
        self.opengl_viewer.objects = list(self.canvas3d.objects)
        self.opengl_viewer.current_object = self.canvas3d.current_object
        self.phong_viewer.objects = list(self.canvas3d.objects)
        self.phong_viewer.current_object = self.canvas3d.current_object
        
        # Atualizar lista de objetos
        self._update_object_list()
        
        # Atualizar botão de cor
        self._update_3d_color_button(fill_color)
        
        self.canvas3d.update()
        self.opengl_viewer.update()
        self.phong_viewer.update()
        self.status.showMessage(f"Cubo criado com tamanho {size}. Veja na aba 'Phong (Scan Line)'", 3000)
    
    def _create_pyramid(self):
        """Cria uma pirâmide 3D"""
        from PyQt5.QtWidgets import QInputDialog
        size, ok1 = QInputDialog.getDouble(
            self, "Base da Pirâmide", "Digite o tamanho da base:",
            100.0, 10.0, 500.0, 1
        )
        if not ok1:
            return
        
        height, ok2 = QInputDialog.getDouble(
            self, "Altura da Pirâmide", "Digite a altura:",
            150.0, 10.0, 500.0, 1
        )
        if not ok2:
            return
        
        pyramid = geo3d.create_pyramid(size, height)
        # Definir cor inicial do objeto
        fill_color = self.canvas3d.fill_color
        pyramid.color = (fill_color.red() / 255.0, fill_color.green() / 255.0, 
                         fill_color.blue() / 255.0, fill_color.alpha() / 255.0)
        
        self.canvas3d.add_object(pyramid)
        self.opengl_viewer.objects = list(self.canvas3d.objects)
        self.opengl_viewer.current_object = self.canvas3d.current_object
        self.phong_viewer.objects = list(self.canvas3d.objects)
        self.phong_viewer.current_object = self.canvas3d.current_object
        
        # Atualizar lista de objetos
        self._update_object_list()
        
        # Atualizar botão de cor
        self._update_3d_color_button(fill_color)
        
        self.canvas3d.update()
        self.opengl_viewer.update()
        self.phong_viewer.update()
        self.status.showMessage(f"Pirâmide criada (base: {size}, altura: {height})", 3000)
    
    def _create_cylinder(self):
        """Cria um cilindro 3D"""
        from PyQt5.QtWidgets import QInputDialog
        radius, ok1 = QInputDialog.getDouble(
            self, "Raio do Cilindro", "Digite o raio:",
            50.0, 10.0, 250.0, 1
        )
        if not ok1:
            return
        
        height, ok2 = QInputDialog.getDouble(
            self, "Altura do Cilindro", "Digite a altura:",
            100.0, 10.0, 500.0, 1
        )
        if not ok2:
            return
        
        cylinder = geo3d.create_cylinder(radius, height)
        # Definir cor inicial do objeto
        fill_color = self.canvas3d.fill_color
        cylinder.color = (fill_color.red() / 255.0, fill_color.green() / 255.0, 
                          fill_color.blue() / 255.0, fill_color.alpha() / 255.0)
        
        self.canvas3d.add_object(cylinder)
        self.opengl_viewer.objects = list(self.canvas3d.objects)
        self.opengl_viewer.current_object = self.canvas3d.current_object
        self.phong_viewer.objects = list(self.canvas3d.objects)
        self.phong_viewer.current_object = self.canvas3d.current_object
        
        # Atualizar lista de objetos
        self._update_object_list()
        
        # Atualizar botão de cor
        self._update_3d_color_button(fill_color)
        
        self.canvas3d.update()
        self.opengl_viewer.update()
        self.phong_viewer.update()
        self.status.showMessage(f"Cilindro criado (raio: {radius}, altura: {height})", 3000)
    
    def _create_hemisphere(self):
        """Cria uma semiesfera 3D"""
        from PyQt5.QtWidgets import QInputDialog
        radius, ok = QInputDialog.getDouble(
            self, "Raio da Semiesfera", "Digite o raio:",
            50.0, 10.0, 250.0, 1
        )
        
        if not ok:
            return
        
        hemisphere = geo3d.create_hemisphere(radius)
        # Definir cor inicial do objeto
        fill_color = self.canvas3d.fill_color
        hemisphere.color = (fill_color.red() / 255.0, fill_color.green() / 255.0, 
                            fill_color.blue() / 255.0, fill_color.alpha() / 255.0)
        
        self.canvas3d.add_object(hemisphere)
        self.opengl_viewer.objects = list(self.canvas3d.objects)
        self.opengl_viewer.current_object = self.canvas3d.current_object
        self.phong_viewer.objects = list(self.canvas3d.objects)
        self.phong_viewer.current_object = self.canvas3d.current_object
        
        # Atualizar lista de objetos
        self._update_object_list()
        
        # Atualizar botão de cor
        self._update_3d_color_button(fill_color)
        
        self.canvas3d.update()
        self.opengl_viewer.update()
        self.phong_viewer.update()
        self.status.showMessage(f"Semiesfera criada com raio {radius}", 3000)
    
    def _create_sphere(self):
        """Cria uma esfera 3D"""
        from PyQt5.QtWidgets import QInputDialog
        radius, ok = QInputDialog.getDouble(
            self, "Raio da Esfera", "Digite o raio:",
            50.0, 10.0, 250.0, 1
        )
        
        if not ok:
            return
        
        sphere = geo3d.create_sphere(radius)
        # Definir cor inicial do objeto
        fill_color = self.canvas3d.fill_color
        sphere.color = (fill_color.red() / 255.0, fill_color.green() / 255.0, 
                        fill_color.blue() / 255.0, fill_color.alpha() / 255.0)
        
        self.canvas3d.add_object(sphere)
        self.opengl_viewer.objects = list(self.canvas3d.objects)
        self.opengl_viewer.current_object = self.canvas3d.current_object
        self.phong_viewer.objects = list(self.canvas3d.objects)
        self.phong_viewer.current_object = self.canvas3d.current_object
        
        # Atualizar lista de objetos
        self._update_object_list()
        
        # Atualizar botão de cor
        self._update_3d_color_button(fill_color)
        
        self.canvas3d.update()
        self.opengl_viewer.update()
        self.phong_viewer.update()
        self.status.showMessage(f"Esfera criada com raio {radius}", 3000)
    
    def _create_torus(self):
        """Cria um torus 3D"""
        from PyQt5.QtWidgets import QInputDialog
        major_radius, ok1 = QInputDialog.getDouble(
            self, "Raio Maior do Torus", "Digite o raio maior:",
            50.0, 10.0, 250.0, 1
        )
        if not ok1:
            return
        
        minor_radius, ok2 = QInputDialog.getDouble(
            self, "Raio Menor do Torus", "Digite o raio menor:",
            20.0, 5.0, 100.0, 1
        )
        if not ok2:
            return
        
        torus = geo3d.create_torus(major_radius, minor_radius)
        # Definir cor inicial do objeto
        fill_color = self.canvas3d.fill_color
        torus.color = (fill_color.red() / 255.0, fill_color.green() / 255.0, 
                       fill_color.blue() / 255.0, fill_color.alpha() / 255.0)
        
        self.canvas3d.add_object(torus)
        self.opengl_viewer.objects = list(self.canvas3d.objects)
        self.opengl_viewer.current_object = self.canvas3d.current_object
        self.phong_viewer.objects = list(self.canvas3d.objects)
        self.phong_viewer.current_object = self.canvas3d.current_object
        
        # Atualizar lista de objetos
        self._update_object_list()
        
        # Atualizar botão de cor
        self._update_3d_color_button(fill_color)
        
        self.canvas3d.update()
        self.opengl_viewer.update()
        self.phong_viewer.update()
        self.status.showMessage(f"Torus criado (raios: {major_radius}, {minor_radius})", 3000)
    
    def _create_cone(self):
        """Cria um cone 3D"""
        from PyQt5.QtWidgets import QInputDialog
        radius, ok1 = QInputDialog.getDouble(
            self, "Raio da Base do Cone", "Digite o raio:",
            50.0, 10.0, 250.0, 1
        )
        if not ok1:
            return
        
        height, ok2 = QInputDialog.getDouble(
            self, "Altura do Cone", "Digite a altura:",
            100.0, 10.0, 500.0, 1
        )
        if not ok2:
            return
        
        cone = geo3d.create_cone(radius, height)
        # Definir cor inicial do objeto
        fill_color = self.canvas3d.fill_color
        cone.color = (fill_color.red() / 255.0, fill_color.green() / 255.0, 
                      fill_color.blue() / 255.0, fill_color.alpha() / 255.0)
        
        self.canvas3d.add_object(cone)
        self.opengl_viewer.objects = list(self.canvas3d.objects)
        self.opengl_viewer.current_object = self.canvas3d.current_object
        self.phong_viewer.objects = list(self.canvas3d.objects)
        self.phong_viewer.current_object = self.canvas3d.current_object
        
        # Atualizar lista de objetos
        self._update_object_list()
        
        # Atualizar botão de cor
        self._update_3d_color_button(fill_color)
        
        self.canvas3d.update()
        self.opengl_viewer.update()
        self.phong_viewer.update()
        self.status.showMessage(f"Cone criado (raio: {radius}, altura: {height})", 3000)
    
    def _create_teapot(self):
        """Cria um teapot 3D (Utah Teapot simplificado)"""
        from PyQt5.QtWidgets import QInputDialog
        size, ok = QInputDialog.getDouble(
            self, "Tamanho do Teapot", "Digite o tamanho:",
            50.0, 20.0, 200.0, 1
        )
        
        if not ok:
            return
        
        teapot = geo3d.create_teapot(size)
        # Definir cor inicial do objeto
        fill_color = self.canvas3d.fill_color
        teapot.color = (fill_color.red() / 255.0, fill_color.green() / 255.0, 
                        fill_color.blue() / 255.0, fill_color.alpha() / 255.0)
        
        self.canvas3d.add_object(teapot)
        self.opengl_viewer.objects = list(self.canvas3d.objects)
        self.opengl_viewer.current_object = self.canvas3d.current_object
        self.phong_viewer.objects = list(self.canvas3d.objects)
        self.phong_viewer.current_object = self.canvas3d.current_object
        
        # Atualizar lista de objetos
        self._update_object_list()
        
        # Atualizar botão de cor
        self._update_3d_color_button(fill_color)
        
        self.canvas3d.update()
        self.opengl_viewer.update()
        self.phong_viewer.update()
        self.status.showMessage(f"Teapot criado com tamanho {size}", 3000)
    
    def _clear_3d_objects(self):
        """Limpa todos os objetos 3D"""
        self.canvas3d.clear_objects()
        self.opengl_viewer.clear_objects()
        self.phong_viewer.clear_objects()
        self.canvas.extruded_object = None
        self._reset_transform()
        # Atualizar lista de objetos
        self._update_object_list()
        self.status.showMessage("Objetos 3D removidos", 2000)
