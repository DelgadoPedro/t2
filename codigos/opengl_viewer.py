"""
Widget OpenGL para renderização 3D com iluminação
"""
from PyQt5.QtWidgets import QOpenGLWidget
from PyQt5.QtGui import QSurfaceFormat
from PyQt5.QtCore import Qt
from OpenGL.GL import *
from OpenGL.GLU import *
import math
import geometry3d as geo3d
from typing import List, Optional, Tuple
import numpy as np


class OpenGLViewer(QOpenGLWidget):
    """Widget OpenGL para renderização 3D com iluminação"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Configurar formato OpenGL
        fmt = QSurfaceFormat()
        fmt.setVersion(2, 1)
        fmt.setProfile(QSurfaceFormat.CoreProfile)
        fmt.setDepthBufferSize(24)
        fmt.setSamples(4)  # Anti-aliasing
        self.setFormat(fmt)
        
        self.objects: List[geo3d.Object3D] = []
        self.current_object: Optional[geo3d.Object3D] = None
        
        # Iluminação
        self.light_position = [200.0, 200.0, 200.0, 1.0]  # Posição da luz (x, y, z, w)
        # Aumentar luz ambiente para que todas as faces sempre sejam visíveis
        self.light_ambient = [0.6, 0.6, 0.6, 1.0]  # Cor ambiente branca (não colorida)
        self.light_diffuse = [1.0, 1.0, 1.0, 1.0]  # Cor difusa branca
        self.light_specular = [1.0, 1.0, 1.0, 1.0]  # Cor especular branca
        # Material será definido pela cor escolhida pelo usuário
        self.material_ambient = [0.5, 0.5, 0.7, 1.0]  # Material ambiente (será sobrescrito)
        self.material_diffuse = [0.5, 0.5, 0.8, 1.0]  # Material difuso (será sobrescrito)
        self.material_specular = [1.0, 1.0, 1.0, 1.0]  # Material especular
        self.material_shininess = [50.0]  # Brilho
        
        # Modelo de iluminação: 'flat', 'gouraud' ou 'phong'
        self.shading_model = 'flat'
        
        # Projeção
        self.is_perspective = False
        self.distance = 500.0
        
        # Câmera
        self.camera_rot_x = 30.0
        self.camera_rot_y = 45.0
        self.camera_distance = 300.0
        
        # Controle de mouse para rotação
        self.last_mouse_pos = None
        self.mouse_sensitivity = 0.5
        self.setMouseTracking(True)
        
        # Mostrar representação visual da luz
        self.show_light_representation = True
        
        # Callback para notificar mudanças na posição da luz
        self.on_light_position_changed = None
        
        # Habilitar foco para receber eventos de teclado
        self.setFocusPolicy(Qt.StrongFocus)
        
        self.setMinimumSize(800, 600)
    
    def initializeGL(self):
        """Inicializa o contexto OpenGL"""
        glEnable(GL_DEPTH_TEST)
        glDepthFunc(GL_LEQUAL)
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        # Desabilitar GL_COLOR_MATERIAL para ter controle total sobre as cores do material
        glDisable(GL_COLOR_MATERIAL)
        glEnable(GL_NORMALIZE)  # Normalizar normais automaticamente
        
        # Habilitar iluminação de dois lados para melhor visibilidade
        glLightModeli(GL_LIGHT_MODEL_TWO_SIDE, GL_TRUE)
        
        glClearColor(0.1, 0.1, 0.15, 1.0)
        glShadeModel(GL_SMOOTH)  # Inicia com Gouraud
        
        # Desabilitar face culling completamente para objetos pré-criados
        # Isso garante que todas as faces sejam renderizadas independente da ordem dos vértices
        glDisable(GL_CULL_FACE)
    
    def resizeGL(self, width, height):
        """Atualiza viewport quando o widget é redimensionado"""
        glViewport(0, 0, width, height)
        self.update()
    
    def paintGL(self):
        """Renderiza a cena"""
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        
        # Configurar projeção
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        
        width = self.width()
        height = self.height()
        aspect = width / height if height > 0 else 1.0
        
        if self.is_perspective:
            # Calcular FOV baseado na distância da projeção
            # Distância maior = FOV menor (menos distorção perspectiva)
            # Fórmula: FOV é inversamente proporcional à distância
            # Usar uma distância base de 500 para FOV de 45 graus
            base_distance = 500.0
            base_fov = 45.0
            # FOV ajustado proporcionalmente à distância
            fov_degrees = base_fov * (base_distance / self.distance)
            # Limitar FOV entre 10 e 90 graus para evitar valores extremos
            fov_degrees = max(10.0, min(90.0, fov_degrees))
            gluPerspective(fov_degrees, aspect, 1.0, 2000.0)
        else:
            glOrtho(-200.0 * aspect, 200.0 * aspect, -200.0, 200.0, -1000.0, 1000.0)
        
        # Configurar view
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        
        # Configurar iluminação ANTES das transformações da câmera
        # A luz fica fixa no espaço do mundo - não acompanha o objeto
        # Quando o objeto rotaciona, as faces mudam de posição relativa à luz
        # w=1.0 indica uma fonte posicional (ponto), w=0.0 seria direcional
        glLightfv(GL_LIGHT0, GL_POSITION, self.light_position)
        glLightfv(GL_LIGHT0, GL_AMBIENT, self.light_ambient)
        glLightfv(GL_LIGHT0, GL_DIFFUSE, self.light_diffuse)
        glLightfv(GL_LIGHT0, GL_SPECULAR, self.light_specular)
        
        # Habilitar normalização de normais (importante quando há escalas não uniformes)
        glEnable(GL_NORMALIZE)
        
        # Posicionar câmera (após definir a luz)
        glTranslatef(0.0, 0.0, -self.camera_distance)
        glRotatef(self.camera_rot_x, 1.0, 0.0, 0.0)
        glRotatef(self.camera_rot_y, 0.0, 1.0, 0.0)
        
        # Garantir que face culling esteja desabilitado antes de desenhar objetos
        glDisable(GL_CULL_FACE)
        
        # Configurar material - usar as cores definidas pelo usuário
        # Aplicar as cores diretamente no material
        glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT, self.material_ambient)
        glMaterialfv(GL_FRONT_AND_BACK, GL_DIFFUSE, self.material_diffuse)
        glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, self.material_specular)
        glMaterialfv(GL_FRONT_AND_BACK, GL_SHININESS, self.material_shininess)
        
        # Definir modelo de shading
        if self.shading_model == 'flat':
            glShadeModel(GL_FLAT)
        else:  # gouraud ou phong (ambos usam interpolação suave)
            glShadeModel(GL_SMOOTH)
        
        # Desenhar todos os objetos na cena
        for obj in self.objects:
            self._draw_object(obj)
        
        # Desenhar representação visual da fonte de luz
        if self.show_light_representation:
            self._draw_light_representation()
    
    def _draw_object(self, obj: geo3d.Object3D):
        """Desenha um objeto 3D"""
        vertices = obj.get_transformed_vertices()
        
        if not vertices:
            return
        
        # Calcular normais das faces para iluminação
        # IMPORTANTE: Calcular normais a partir dos vértices originais e depois
        # aplicar apenas a rotação da transformação (não a translação)
        face_normals = self._calculate_face_normals_from_original(obj)
        vertex_normals = self._calculate_vertex_normals_from_original(obj, face_normals)
        
        # Aplicar rotação às normais (extrair apenas parte de rotação/escala da transformação)
        rotation_matrix = obj.transform.matrix[:3, :3]  # Parte superior esquerda 3x3
        
        # Transformar normais das faces
        transformed_face_normals = []
        for normal_tuple in face_normals:
            normal_vec = np.array([normal_tuple[0], normal_tuple[1], normal_tuple[2], 0.0])
            transformed_normal = np.dot(rotation_matrix, normal_vec[:3])
            # Normalizar após transformação
            normal_length = np.linalg.norm(transformed_normal)
            if normal_length > 0.0001:
                transformed_normal = transformed_normal / normal_length
            else:
                transformed_normal = np.array([0.0, 0.0, 1.0])
            transformed_face_normals.append(tuple(transformed_normal))
        
        # Transformar normais dos vértices
        transformed_vertex_normals = []
        for normal_tuple in vertex_normals:
            normal_vec = np.array([normal_tuple[0], normal_tuple[1], normal_tuple[2], 0.0])
            transformed_normal = np.dot(rotation_matrix, normal_vec[:3])
            # Normalizar após transformação
            normal_length = np.linalg.norm(transformed_normal)
            if normal_length > 0.0001:
                transformed_normal = transformed_normal / normal_length
            else:
                transformed_normal = np.array([0.0, 0.0, 1.0])
            transformed_vertex_normals.append(tuple(transformed_normal))
        
        face_normals = transformed_face_normals
        vertex_normals = transformed_vertex_normals
        
        # Desabilitar culling temporariamente para garantir que todas as faces sejam renderizadas
        glDisable(GL_CULL_FACE)
        
        # Aplicar cor do objeto
        r, g, b, alpha = obj.color if hasattr(obj, 'color') else (0.5, 0.6, 0.8, 1.0)
        material_diffuse = [min(1.0, r * 1.2), min(1.0, g * 1.2), min(1.0, b * 1.2), alpha]
        material_ambient = [r * 0.3, g * 0.3, b * 0.3, alpha]
        # Para Phong, usar specular mais intenso para destacar highlights
        if self.shading_model == 'phong':
            material_specular = [1.2, 1.2, 1.2, alpha]  # Specular mais intenso
            shininess = [128.0]  # Brilho mais alto
        else:
            material_specular = [1.0, 1.0, 1.0, alpha]
            shininess = self.material_shininess
        
        glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT, material_ambient)
        glMaterialfv(GL_FRONT_AND_BACK, GL_DIFFUSE, material_diffuse)
        glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, material_specular)
        glMaterialfv(GL_FRONT_AND_BACK, GL_SHININESS, shininess)
        
        # Desenhar faces
        glBegin(GL_TRIANGLES)
        for face_idx, face in enumerate(obj.faces):
            if len(face) < 3:
                continue
            
            # Se for flat shading, usar normal da face
            if self.shading_model == 'flat' and face_idx < len(face_normals):
                normal = face_normals[face_idx]
                glNormal3f(normal[0], normal[1], normal[2])
            
            # Triangulizar face (assumindo que é convexa)
            for i in range(1, len(face) - 1):
                idx0 = face[0]
                idx1 = face[i]
                idx2 = face[i + 1]
                
                if idx0 < len(vertices) and idx1 < len(vertices) and idx2 < len(vertices):
                    v0 = vertices[idx0]
                    v1 = vertices[idx1]
                    v2 = vertices[idx2]
                    
                    # Se for Gouraud ou Phong, usar normal do vértice
                    if self.shading_model in ['gouraud', 'phong']:
                        if idx0 < len(vertex_normals):
                            normal = vertex_normals[idx0]
                            glNormal3f(normal[0], normal[1], normal[2])
                    glVertex3f(v0[0], v0[1], v0[2])
                    
                    if self.shading_model in ['gouraud', 'phong'] and idx1 < len(vertex_normals):
                        normal = vertex_normals[idx1]
                        glNormal3f(normal[0], normal[1], normal[2])
                    glVertex3f(v1[0], v1[1], v1[2])
                    
                    if self.shading_model in ['gouraud', 'phong'] and idx2 < len(vertex_normals):
                        normal = vertex_normals[idx2]
                        glNormal3f(normal[0], normal[1], normal[2])
                    glVertex3f(v2[0], v2[1], v2[2])
        glEnd()
    
    def _calculate_face_normals_from_original(self, obj: geo3d.Object3D) -> List[Tuple[float, float, float]]:
        """Calcula normais das faces a partir dos vértices originais (não transformados)"""
        normals = []
        
        for face in obj.faces:
            if len(face) < 3:
                normals.append((0.0, 0.0, 1.0))
                continue
            
            # Pegar três vértices da face em ordem CCW - usar vértices ORIGINAIS
            idx0, idx1, idx2 = face[0], face[1], face[2]
            
            if idx0 >= len(obj.vertices) or idx1 >= len(obj.vertices) or idx2 >= len(obj.vertices):
                normals.append((0.0, 0.0, 1.0))
                continue
            
            v0 = geo3d.Vector3D.from_tuple(obj.vertices[idx0])
            v1 = geo3d.Vector3D.from_tuple(obj.vertices[idx1])
            v2 = geo3d.Vector3D.from_tuple(obj.vertices[idx2])
            
            # Calcular vetores da face
            edge1 = v1 - v0
            edge2 = v2 - v0
            
            # Calcular normal (produto vetorial): edge1 x edge2
            # Em CCW, isso aponta para fora
            normal = edge1.cross(edge2)
            
            # Normalizar
            normal_length = normal.length()
            if normal_length > 0.0001:  # Evitar divisão por zero
                normal = normal.normalize()
            else:
                normal = geo3d.Vector3D(0.0, 0.0, 1.0)
            
            normals.append(normal.to_tuple())
        
        return normals
    
    def _calculate_vertex_normals_from_original(self, obj: geo3d.Object3D, 
                                  face_normals: List[Tuple[float, float, float]]) -> List[Tuple[float, float, float]]:
        """Calcula normais dos vértices a partir dos vértices originais (média das normais das faces adjacentes)"""
        vertex_normals = [(0.0, 0.0, 0.0) for _ in obj.vertices]
        vertex_face_count = [0 for _ in obj.vertices]
        
        # Para cada face, adicionar sua normal aos vértices
        for face_idx, face in enumerate(obj.faces):
            if face_idx >= len(face_normals):
                continue
            
            normal = geo3d.Vector3D.from_tuple(face_normals[face_idx])
            
            for vertex_idx in face:
                if vertex_idx < len(obj.vertices):
                    current_normal = geo3d.Vector3D.from_tuple(vertex_normals[vertex_idx])
                    vertex_normals[vertex_idx] = (current_normal + normal).to_tuple()
                    vertex_face_count[vertex_idx] += 1
        
        # Normalizar normais dos vértices
        result = []
        for i, normal in enumerate(vertex_normals):
            if vertex_face_count[i] > 0:
                normal_vec = geo3d.Vector3D.from_tuple(normal)
                normal_length = normal_vec.length()
                if normal_length > 0.0001:  # Evitar divisão por zero
                    result.append(normal_vec.normalize().to_tuple())
                else:
                    # Se a normal é zero, usar normal padrão
                    result.append((0.0, 0.0, 1.0))
            else:
                result.append((0.0, 0.0, 1.0))
        
        return result
    
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
    
    def set_light_position(self, x: float, y: float, z: float):
        """Define a posição da luz"""
        self.light_position = [float(x), float(y), float(z), 1.0]
        self.update()
    
    def set_shading_model(self, model: str):
        """Define o modelo de shading: 'flat', 'gouraud' ou 'phong'"""
        if model.lower() in ['flat', 'gouraud', 'phong']:
            self.shading_model = model.lower()
            # Para Phong, aumentar o brilho para destacar highlights especulares
            if model.lower() == 'phong':
                self.material_shininess = [128.0]  # Brilho mais alto para Phong
            else:
                self.material_shininess = [50.0]  # Brilho padrão
            self.update()
    
    def set_projection(self, is_perspective: bool, distance: float = 500.0):
        """Alterna entre projeção perspectiva e ortográfica"""
        self.is_perspective = is_perspective
        self.distance = distance
        self.update()
    
    def set_camera_rotation(self, rot_x: float, rot_y: float):
        """Define rotação da câmera"""
        self.camera_rot_x = rot_x
        self.camera_rot_y = rot_y
        self.update()
    
    def set_camera_distance(self, distance: float):
        """Define distância da câmera"""
        self.camera_distance = distance
        self.update()
    
    def set_material_color(self, r: float, g: float, b: float, alpha: float = 1.0):
        """Define a cor do material"""
        # Usar a cor escolhida diretamente para o material difuso (principal)
        # Aumentar um pouco para compensar a iluminação
        self.material_diffuse = [min(1.0, r * 1.2), min(1.0, g * 1.2), min(1.0, b * 1.2), alpha]
        # Ambiente com a mesma cor mas mais escuro para dar profundidade sem amarelar
        self.material_ambient = [r * 0.3, g * 0.3, b * 0.3, alpha]
        # Manter especular branco para highlights realistas
        self.material_specular = [1.0, 1.0, 1.0, alpha]
        self.update()
    
    def mousePressEvent(self, event):
        """Inicia rotação quando o botão esquerdo é pressionado"""
        if event.button() == Qt.LeftButton:
            self.last_mouse_pos = event.pos()
            # Garantir foco para receber eventos de teclado
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
        """Mover fonte de luz com setas do teclado e zoom com teclas 1 e 2"""
        step = 10.0  # Passo de movimento
        moved = False
        zoomed = False
        
        # Zoom com teclas 1 e 2
        if event.key() == Qt.Key_1:
            # Zoom in (tecla 1)
            zoom_factor = 1.1
            self.camera_distance *= zoom_factor
            self.camera_distance = max(50.0, min(1000.0, self.camera_distance))
            zoomed = True
        elif event.key() == Qt.Key_2:
            # Zoom out (tecla 2)
            zoom_factor = 0.9
            self.camera_distance *= zoom_factor
            self.camera_distance = max(50.0, min(1000.0, self.camera_distance))
            zoomed = True
        
        # Mover fonte de luz
        if event.key() == Qt.Key_Left:
            self.light_position[0] -= step
            moved = True
        elif event.key() == Qt.Key_Right:
            self.light_position[0] += step
            moved = True
        elif event.key() == Qt.Key_Up:
            self.light_position[1] += step
            moved = True
        elif event.key() == Qt.Key_Down:
            self.light_position[1] -= step
            moved = True
        elif event.key() == Qt.Key_PageUp:
            self.light_position[2] += step
            moved = True
        elif event.key() == Qt.Key_PageDown:
            self.light_position[2] -= step
            moved = True
        
        if moved or zoomed:
            # Limitar valores da luz
            for i in range(3):
                self.light_position[i] = max(-500.0, min(500.0, self.light_position[i]))
            
            # Notificar mudança
            if hasattr(self, 'on_light_position_changed') and self.on_light_position_changed:
                self.on_light_position_changed(
                    self.light_position[0],
                    self.light_position[1],
                    self.light_position[2]
                )
            
            self.update()
    
    def _draw_light_representation(self):
        """Desenha uma representação visual da fonte de luz"""
        # Salvar estado atual (já tem transformações da câmera aplicadas)
        glPushMatrix()
        
        # Desfazer transformações da câmera para voltar ao espaço do mundo
        # A luz está fixa no espaço do mundo, não acompanha o objeto
        glRotatef(-self.camera_rot_y, 0.0, 1.0, 0.0)
        glRotatef(-self.camera_rot_x, 1.0, 0.0, 0.0)
        glTranslatef(0.0, 0.0, self.camera_distance)
        
        # Desabilitar iluminação temporariamente para desenhar a luz
        glDisable(GL_LIGHTING)
        glDisable(GL_CULL_FACE)  # Desabilitar culling para ver a esfera de qualquer ângulo
        
        # Posicionar na posição da luz (fixa no espaço do mundo)
        x, y, z = self.light_position[0], self.light_position[1], self.light_position[2]
        glTranslatef(x, y, z)
        
        # Desenhar esfera brilhante amarela
        glColor3f(1.0, 1.0, 0.6)  # Amarelo brilhante
        
        # Desenhar esfera simples (usando gluSphere se disponível)
        try:
            import math
            # Criar uma esfera usando primitivas
            slices = 20
            stacks = 20
            radius = 10.0
            
            # Desenhar esfera
            glBegin(GL_TRIANGLES)
            for i in range(stacks):
                lat1 = math.pi * (-0.5 + float(i) / stacks)
                lat2 = math.pi * (-0.5 + float(i + 1) / stacks)
                z1 = math.sin(lat1) * radius
                z2 = math.sin(lat2) * radius
                r1 = math.cos(lat1) * radius
                r2 = math.cos(lat2) * radius
                
                for j in range(slices):
                    lng1 = 2.0 * math.pi * float(j) / slices
                    lng2 = 2.0 * math.pi * float(j + 1) / slices
                    x1 = math.cos(lng1) * r1
                    y1 = math.sin(lng1) * r1
                    x2 = math.cos(lng2) * r1
                    y2 = math.sin(lng2) * r1
                    x3 = math.cos(lng1) * r2
                    y3 = math.sin(lng1) * r2
                    x4 = math.cos(lng2) * r2
                    y4 = math.sin(lng2) * r2
                    
                    # Primeiro triângulo
                    glVertex3f(x1, y1, z1)
                    glVertex3f(x2, y2, z1)
                    glVertex3f(x3, y3, z2)
                    
                    # Segundo triângulo
                    glVertex3f(x2, y2, z1)
                    glVertex3f(x4, y4, z2)
                    glVertex3f(x3, y3, z2)
            glEnd()
            
            # Desenhar raios de luz (linhas)
            glColor3f(1.0, 1.0, 0.8)  # Amarelo mais claro para raios
            glLineWidth(2.0)
            glBegin(GL_LINES)
            num_rays = 8
            for i in range(num_rays):
                angle = 2.0 * math.pi * i / num_rays
                ray_length = 15.0
                x_end = math.cos(angle) * ray_length
                y_end = math.sin(angle) * ray_length
                glVertex3f(0, 0, 0)
                glVertex3f(x_end, y_end, 0)
                glVertex3f(0, 0, 0)
                glVertex3f(0, 0, ray_length)
            glEnd()
            
        except Exception:
            # Fallback: desenhar um cubo simples se houver problema
            glBegin(GL_QUADS)
            size = 5.0
            # Cubo simples
            glVertex3f(-size, -size, -size)
            glVertex3f(size, -size, -size)
            glVertex3f(size, size, -size)
            glVertex3f(-size, size, -size)
            
            glVertex3f(-size, -size, size)
            glVertex3f(size, -size, size)
            glVertex3f(size, size, size)
            glVertex3f(-size, size, size)
            glEnd()
        
        # Restaurar iluminação e culling
        glEnable(GL_LIGHTING)
        glEnable(GL_CULL_FACE)
        
        # Restaurar estado (volta para o espaço da câmera)
        glPopMatrix()

