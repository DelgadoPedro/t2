"""
Módulo para geometria 3D: pontos, transformações e projeções
"""
import math
from typing import List, Tuple, Optional
import numpy as np

Point3D = Tuple[float, float, float]
Point2D = Tuple[float, float]


class Vector3D:
    """Classe para representar um vetor 3D"""
    def __init__(self, x: float = 0.0, y: float = 0.0, z: float = 0.0):
        self.x = float(x)
        self.y = float(y)
        self.z = float(z)
    
    def __add__(self, other):
        return Vector3D(self.x + other.x, self.y + other.y, self.z + other.z)
    
    def __sub__(self, other):
        return Vector3D(self.x - other.x, self.y - other.y, self.z - other.z)
    
    def __mul__(self, scalar):
        return Vector3D(self.x * scalar, self.y * scalar, self.z * scalar)
    
    def __rmul__(self, scalar):
        return self.__mul__(scalar)
    
    def dot(self, other):
        return self.x * other.x + self.y * other.y + self.z * other.z
    
    def cross(self, other):
        return Vector3D(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x
        )
    
    def length(self):
        return math.sqrt(self.x**2 + self.y**2 + self.z**2)
    
    def normalize(self):
        l = self.length()
        if l > 0:
            return Vector3D(self.x / l, self.y / l, self.z / l)
        return Vector3D(0, 0, 0)
    
    def to_tuple(self) -> Point3D:
        return (self.x, self.y, self.z)
    
    @staticmethod
    def from_tuple(p: Point3D):
        return Vector3D(p[0], p[1], p[2])


class Transform3D:
    """Classe para matrizes de transformação 3D"""
    def __init__(self):
        # Matriz 4x4 de transformação (homogênea)
        self.matrix = np.eye(4, dtype=float)
    
    @staticmethod
    def translation(tx: float, ty: float, tz: float):
        """Cria matriz de translação"""
        T = Transform3D()
        T.matrix[0, 3] = tx
        T.matrix[1, 3] = ty
        T.matrix[2, 3] = tz
        return T
    
    @staticmethod
    def scale(sx: float, sy: float, sz: float):
        """Cria matriz de escala"""
        S = Transform3D()
        S.matrix[0, 0] = sx
        S.matrix[1, 1] = sy
        S.matrix[2, 2] = sz
        return S
    
    @staticmethod
    def rotation_x(angle_rad: float):
        """Rotação em torno do eixo X"""
        R = Transform3D()
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)
        R.matrix[1, 1] = cos_a
        R.matrix[1, 2] = -sin_a
        R.matrix[2, 1] = sin_a
        R.matrix[2, 2] = cos_a
        return R
    
    @staticmethod
    def rotation_y(angle_rad: float):
        """Rotação em torno do eixo Y"""
        R = Transform3D()
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)
        R.matrix[0, 0] = cos_a
        R.matrix[0, 2] = sin_a
        R.matrix[2, 0] = -sin_a
        R.matrix[2, 2] = cos_a
        return R
    
    @staticmethod
    def rotation_z(angle_rad: float):
        """Rotação em torno do eixo Z"""
        R = Transform3D()
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)
        R.matrix[0, 0] = cos_a
        R.matrix[0, 1] = -sin_a
        R.matrix[1, 0] = sin_a
        R.matrix[1, 1] = cos_a
        return R
    
    @staticmethod
    def rotation_euler(rx: float, ry: float, rz: float):
        """Rotação usando ângulos de Euler (em radianos)"""
        return (Transform3D.rotation_x(rx) * 
                Transform3D.rotation_y(ry) * 
                Transform3D.rotation_z(rz))
    
    def __mul__(self, other):
        """Composição de transformações"""
        if isinstance(other, Transform3D):
            result = Transform3D()
            result.matrix = np.dot(self.matrix, other.matrix)
            return result
        elif isinstance(other, Vector3D):
            # Aplicar transformação a um ponto
            p = np.array([other.x, other.y, other.z, 1.0])
            transformed = np.dot(self.matrix, p)
            return Vector3D(transformed[0], transformed[1], transformed[2])
        return None
    
    def apply_to_point(self, point: Point3D) -> Point3D:
        """Aplica transformação a um ponto"""
        v = Vector3D.from_tuple(point)
        result = self * v
        return result.to_tuple()


class Projection:
    """Classe base para projeções 3D -> 2D"""
    def project(self, point: Point3D) -> Point2D:
        raise NotImplementedError


class OrthographicProjection(Projection):
    """Projeção Ortográfica"""
    def __init__(self, center_x: float = 0, center_y: float = 0, scale: float = 1.0):
        self.center_x = center_x
        self.center_y = center_y
        self.scale = scale
    
    def project(self, point: Point3D) -> Point2D:
        """Projeção ortográfica: ignora Z, projeta X e Y"""
        x = point[0] * self.scale + self.center_x
        y = point[1] * self.scale + self.center_y
        return (x, y)


class PerspectiveProjection(Projection):
    """Projeção Perspectiva"""
    def __init__(self, 
                 center_x: float = 0, 
                 center_y: float = 0,
                 distance: float = 500.0,  # Distância do observador (d)
                 scale: float = 1.0):
        self.center_x = center_x
        self.center_y = center_y
        self.distance = distance  # Distância do plano de projeção
        self.scale = scale
    
    def project(self, point: Point3D) -> Point2D:
        """Projeção perspectiva usando fórmulas:
        x' = (x * d) / (z + d)
        y' = (y * d) / (z + d)
        """
        x, y, z = point
        
        # Evitar divisão por zero ou valores muito próximos
        if z + self.distance <= 0:
            z = -self.distance + 0.1
        
        # Fórmula de projeção perspectiva
        z_factor = self.distance / (z + self.distance)
        x_proj = x * z_factor * self.scale + self.center_x
        y_proj = y * z_factor * self.scale + self.center_y
        
        return (x_proj, y_proj)


class Object3D:
    """Classe base para objetos 3D"""
    def __init__(self, vertices: List[Point3D], edges: List[Tuple[int, int]], 
                 faces: Optional[List[List[int]]] = None, color: Optional[Tuple[float, float, float, float]] = None):
        self.vertices = vertices.copy()  # Cópia dos vértices originais
        self.current_vertices = vertices.copy()  # Vértices após transformações
        self.edges = edges  # Lista de arestas: [(i1, i2), ...]
        self.faces = faces if faces else []  # Lista de faces: [[i1, i2, i3, ...], ...]
        self.transform = Transform3D()
        # Cor do objeto (R, G, B, Alpha) - valores de 0.0 a 1.0
        self.color = color if color is not None else (0.5, 0.6, 0.8, 1.0)  # Cor padrão azul claro
    
    def apply_transform(self, transform: Transform3D):
        """Aplica uma transformação ao objeto"""
        self.transform = transform * self.transform
        self._update_vertices()
    
    def _update_vertices(self):
        """Atualiza os vértices após transformação"""
        self.current_vertices = [self.transform.apply_to_point(v) for v in self.vertices]
    
    def reset_transform(self):
        """Reseta as transformações"""
        self.transform = Transform3D()
        self._update_vertices()
    
    def get_transformed_vertices(self) -> List[Point3D]:
        """Retorna os vértices transformados"""
        return self.current_vertices


def create_cube(size: float = 100.0) -> Object3D:
    """Cria um cubo centrado na origem"""
    s = size / 2.0
    vertices = [
        (-s, -s, -s), (s, -s, -s), (s, s, -s), (-s, s, -s),  # Face inferior
        (-s, -s, s), (s, -s, s), (s, s, s), (-s, s, s)  # Face superior
    ]
    edges = [
        # Arestas da face inferior
        (0, 1), (1, 2), (2, 3), (3, 0),
        # Arestas da face superior
        (4, 5), (5, 6), (6, 7), (7, 4),
        # Arestas conectando faces
        (0, 4), (1, 5), (2, 6), (3, 7)
    ]
    faces = [
        [0, 1, 2, 3],  # Face inferior
        [4, 5, 6, 7],  # Face superior
        [0, 1, 5, 4],  # Face frontal
        [2, 3, 7, 6],  # Face traseira
        [0, 3, 7, 4],  # Face esquerda
        [1, 2, 6, 5]   # Face direita
    ]
    return Object3D(vertices, edges, faces)


def create_pyramid(size: float = 100.0, height: float = 150.0) -> Object3D:
    """Cria uma pirâmide quadrada"""
    s = size / 2.0
    vertices = [
        (-s, -s, 0), (s, -s, 0), (s, s, 0), (-s, s, 0),  # Base
        (0, 0, height)  # Topo
    ]
    edges = [
        # Arestas da base
        (0, 1), (1, 2), (2, 3), (3, 0),
        # Arestas do topo
        (0, 4), (1, 4), (2, 4), (3, 4)
    ]
    faces = [
        [0, 1, 2, 3],  # Base
        [0, 1, 4],     # Face frontal
        [1, 2, 4],     # Face direita
        [2, 3, 4],     # Face traseira
        [3, 0, 4]      # Face esquerda
    ]
    return Object3D(vertices, edges, faces)


def extrude_polygon_2d(points_2d: List[Tuple[int, int]], depth: float = 1.0) -> Object3D:
    """
    Extrusão de um polígono 2D para criar um objeto 3D
    
    Args:
        points_2d: Lista de pontos 2D (x, y) em coordenadas de tela
        depth: Profundidade da extrusão (ao longo do eixo Z)
    
    Returns:
        Object3D criado pela extrusão
    """
    if len(points_2d) < 3:
        raise ValueError("Polígono precisa de pelo menos 3 pontos")
    
    # Calcular centro do polígono para centralizar na origem
    min_x = min(p[0] for p in points_2d)
    max_x = max(p[0] for p in points_2d)
    min_y = min(p[1] for p in points_2d)
    max_y = max(p[1] for p in points_2d)
    center_x = (min_x + max_x) / 2.0
    center_y = (min_y + max_y) / 2.0
    
    n = len(points_2d)
    vertices = []
    edges = []
    faces = []
    
    # Criar vértices: face inferior (z=-depth/2) e face superior (z=depth/2)
    # Centralizar e inverter Y (coordenadas de tela para 3D: Y cresce para cima)
    for x, y in points_2d:
        # Centralizar e converter coordenadas
        x3d = float(x - center_x)
        y3d = float(center_y - y)  # Inverter Y
        vertices.append((x3d, y3d, -depth / 2.0))  # Face inferior
    
    for x, y in points_2d:
        x3d = float(x - center_x)
        y3d = float(center_y - y)  # Inverter Y
        vertices.append((x3d, y3d, depth / 2.0))  # Face superior
    
    # Arestas da face inferior
    for i in range(n):
        edges.append((i, (i + 1) % n))
    
    # Arestas da face superior
    for i in range(n):
        edges.append((n + i, n + (i + 1) % n))
    
    # Arestas conectando faces (extrusão)
    for i in range(n):
        edges.append((i, n + i))
    
    # Face inferior
    faces.append(list(range(n)))
    
    # Face superior (ordem reversa para normal correta)
    faces.append([n + i for i in range(n - 1, -1, -1)])
    
    # Faces laterais
    for i in range(n):
        next_i = (i + 1) % n
        faces.append([i, next_i, n + next_i, n + i])
    
    return Object3D(vertices, edges, faces)


def create_cylinder(radius: float = 50.0, height: float = 100.0, segments: int = 32) -> Object3D:
    """
    Cria um cilindro
    
    Args:
        radius: Raio da base do cilindro
        height: Altura do cilindro
        segments: Número de segmentos na circunferência (mais segmentos = mais suave)
    
    Returns:
        Object3D criado
    """
    vertices = []
    edges = []
    faces = []
    
    # Gerar vértices da base inferior (z = -height/2)
    for i in range(segments):
        angle = 2.0 * math.pi * i / segments
        x = radius * math.cos(angle)
        y = radius * math.sin(angle)
        z = -height / 2.0
        vertices.append((x, y, z))
    
    # Gerar vértices da base superior (z = height/2)
    for i in range(segments):
        angle = 2.0 * math.pi * i / segments
        x = radius * math.cos(angle)
        y = radius * math.sin(angle)
        z = height / 2.0
        vertices.append((x, y, z))
    
    # Arestas da base inferior
    for i in range(segments):
        edges.append((i, (i + 1) % segments))
    
    # Arestas da base superior
    for i in range(segments):
        edges.append((segments + i, segments + (i + 1) % segments))
    
    # Arestas verticais (lateral do cilindro)
    for i in range(segments):
        edges.append((i, segments + i))
    
    # Face inferior (base)
    faces.append(list(range(segments)))
    
    # Face superior (base) - ordem reversa
    faces.append([segments + i for i in range(segments - 1, -1, -1)])
    
    # Faces laterais (retângulos)
    for i in range(segments):
        next_i = (i + 1) % segments
        faces.append([i, next_i, segments + next_i, segments + i])
    
    return Object3D(vertices, edges, faces)


def create_hemisphere(radius: float = 50.0, segments: int = 16) -> Object3D:
    """
    Cria uma semiesfera
    
    Args:
        radius: Raio da semiesfera
        segments: Número de segmentos na circunferência e na altura
    
    Returns:
        Object3D criado
    """
    vertices = []
    edges = []
    faces = []
    
    # Vértice do topo (polo norte)
    top_idx = 0
    vertices.append((0.0, 0.0, radius))
    
    # Gerar vértices em camadas circulares (do topo até a base)
    vertices_per_layer = segments
    for layer in range(1, segments + 1):
        # Ângulo vertical: de 0 (topo) até π/2 (base)
        theta = math.pi / 2.0 * layer / segments
        z = radius * math.cos(theta)
        layer_radius = radius * math.sin(theta)
        
        # Vértices nesta camada circular
        for i in range(vertices_per_layer):
            # Ângulo horizontal na camada
            phi = 2.0 * math.pi * i / vertices_per_layer
            x = layer_radius * math.cos(phi)
            y = layer_radius * math.sin(phi)
            vertices.append((x, y, z))
    
    # Arestas: conectar vértice do topo à primeira camada
    first_layer_start = 1
    for i in range(vertices_per_layer):
        next_i = (i + 1) % vertices_per_layer
        edges.append((top_idx, first_layer_start + i))
        edges.append((first_layer_start + i, first_layer_start + next_i))
    
    # Arestas entre camadas
    for layer in range(1, segments):
        layer_start = 1 + (layer - 1) * vertices_per_layer
        next_layer_start = 1 + layer * vertices_per_layer
        
        for i in range(vertices_per_layer):
            next_i = (i + 1) % vertices_per_layer
            # Arestas verticais
            edges.append((layer_start + i, next_layer_start + i))
            # Arestas horizontais
            edges.append((next_layer_start + i, next_layer_start + next_i))
    
    # Faces do topo (triângulos do topo para a primeira camada)
    for i in range(vertices_per_layer):
        next_i = (i + 1) % vertices_per_layer
        faces.append([top_idx, first_layer_start + i, first_layer_start + next_i])
    
    # Faces entre camadas (quadriláteros)
    for layer in range(1, segments):
        layer_start = 1 + (layer - 1) * vertices_per_layer
        next_layer_start = 1 + layer * vertices_per_layer
        
        for i in range(vertices_per_layer):
            next_i = (i + 1) % vertices_per_layer
            faces.append([
                layer_start + i,
                layer_start + next_i,
                next_layer_start + next_i,
                next_layer_start + i
            ])
    
    # Face da base (círculo plano - última camada)
    base_start = 1 + (segments - 1) * vertices_per_layer
    base_face = list(range(base_start, base_start + vertices_per_layer))
    if len(base_face) > 2:
        faces.append(base_face)
    
    return Object3D(vertices, edges, faces)


def create_sphere(radius: float = 50.0, segments: int = 16, stacks: int = 16) -> Object3D:
    """
    Cria uma esfera completa
    
    Args:
        radius: Raio da esfera
        segments: Número de segmentos na circunferência horizontal
        stacks: Número de camadas verticais
    
    Returns:
        Object3D criado
    """
    vertices = []
    edges = []
    faces = []
    
    # Gerar vértices
    for i in range(stacks + 1):
        theta = math.pi * i / stacks  # De 0 a π
        sin_theta = math.sin(theta)
        cos_theta = math.cos(theta)
        y = radius * cos_theta
        
        for j in range(segments):
            phi = 2.0 * math.pi * j / segments  # De 0 a 2π
            sin_phi = math.sin(phi)
            cos_phi = math.cos(phi)
            
            x = radius * sin_theta * cos_phi
            z = radius * sin_theta * sin_phi
            vertices.append((x, y, z))
    
    # Gerar arestas
    for i in range(stacks):
        for j in range(segments):
            idx = i * segments + j
            next_idx = i * segments + (j + 1) % segments
            below_idx = (i + 1) * segments + j
            below_next_idx = (i + 1) * segments + (j + 1) % segments
            
            # Arestas horizontais
            edges.append((idx, next_idx))
            if i < stacks - 1:
                edges.append((below_idx, below_next_idx))
            
            # Arestas verticais
            if i < stacks:
                edges.append((idx, below_idx))
    
    # Gerar faces
    for i in range(stacks):
        for j in range(segments):
            idx = i * segments + j
            next_idx = i * segments + (j + 1) % segments
            below_idx = (i + 1) * segments + j
            below_next_idx = (i + 1) * segments + (j + 1) % segments
            
            # Criar quad (ou dois triângulos)
            if i == 0:
                # Topo: triângulo
                faces.append([idx, below_next_idx, below_idx])
            elif i == stacks - 1:
                # Base: triângulo
                faces.append([idx, next_idx, below_idx])
            else:
                # Meio: quadrilátero
                faces.append([idx, next_idx, below_next_idx, below_idx])
    
    return Object3D(vertices, edges, faces)


def create_torus(major_radius: float = 50.0, minor_radius: float = 20.0, 
                 major_segments: int = 32, minor_segments: int = 16) -> Object3D:
    """
    Cria um torus (rosquinha)
    
    Args:
        major_radius: Raio maior (distância do centro ao centro do tubo)
        minor_radius: Raio menor (raio do tubo)
        major_segments: Número de segmentos no círculo maior
        minor_segments: Número de segmentos no círculo menor
    
    Returns:
        Object3D criado
    """
    vertices = []
    edges = []
    faces = []
    
    # Gerar vértices
    for i in range(major_segments):
        major_angle = 2.0 * math.pi * i / major_segments
        cos_major = math.cos(major_angle)
        sin_major = math.sin(major_angle)
        center_x = major_radius * cos_major
        center_z = major_radius * sin_major
        
        for j in range(minor_segments):
            minor_angle = 2.0 * math.pi * j / minor_segments
            cos_minor = math.cos(minor_angle)
            sin_minor = math.sin(minor_angle)
            
            # Posição relativa ao centro do tubo
            rel_x = minor_radius * cos_minor * cos_major
            rel_y = minor_radius * sin_minor
            rel_z = minor_radius * cos_minor * sin_major
            
            x = center_x + rel_x
            y = rel_y
            z = center_z + rel_z
            
            vertices.append((x, y, z))
    
    # Gerar arestas e faces
    for i in range(major_segments):
        for j in range(minor_segments):
            idx = i * minor_segments + j
            next_j = (j + 1) % minor_segments
            next_i = (i + 1) % major_segments
            
            next_j_idx = i * minor_segments + next_j
            next_i_idx = next_i * minor_segments + j
            next_both_idx = next_i * minor_segments + next_j
            
            # Arestas
            edges.append((idx, next_j_idx))  # Horizontal (ao redor do tubo)
            edges.append((idx, next_i_idx))  # Vertical (ao redor do torus)
            
            # Faces (quadriláteros)
            faces.append([idx, next_j_idx, next_both_idx, next_i_idx])
    
    return Object3D(vertices, edges, faces)


def create_cone(base_radius: float = 50.0, height: float = 100.0, segments: int = 32) -> Object3D:
    """
    Cria um cone
    
    Args:
        base_radius: Raio da base
        height: Altura do cone
        segments: Número de segmentos na base circular
    
    Returns:
        Object3D criado
    """
    vertices = []
    edges = []
    faces = []
    
    # Vértice do topo
    top_idx = 0
    vertices.append((0.0, height / 2.0, 0.0))
    
    # Vértices da base
    base_start = 1
    for i in range(segments):
        angle = 2.0 * math.pi * i / segments
        x = base_radius * math.cos(angle)
        z = base_radius * math.sin(angle)
        vertices.append((x, -height / 2.0, z))
    
    # Arestas da base
    for i in range(segments):
        edges.append((base_start + i, base_start + (i + 1) % segments))
    
    # Arestas do topo para a base
    for i in range(segments):
        edges.append((top_idx, base_start + i))
    
    # Face da base
    base_face = list(range(base_start, base_start + segments))
    faces.append(base_face)
    
    # Faces laterais (triângulos)
    for i in range(segments):
        next_i = (i + 1) % segments
        faces.append([top_idx, base_start + i, base_start + next_i])
    
    return Object3D(vertices, edges, faces)


def create_teapot(size: float = 50.0) -> Object3D:
    """
    Cria uma versão simplificada do Utah Teapot
    Usa uma aproximação geométrica simples baseada em formas paramétricas
    
    Args:
        size: Tamanho geral do teapot
    
    Returns:
        Object3D criado
    """
    vertices = []
    edges = []
    faces = []
    
    scale = size / 50.0
    
    # Simplificação: criar teapot usando múltiplos cilindros e esferas
    # Corpo do bule (esfera achatada)
    body_segments = 16
    body_stacks = 12
    body_radius_x = 30.0 * scale
    body_radius_y = 25.0 * scale
    body_radius_z = 30.0 * scale
    body_center_y = 0.0
    
    for i in range(body_stacks + 1):
        theta = math.pi * i / body_stacks
        sin_theta = math.sin(theta)
        cos_theta = math.cos(theta)
        y = body_center_y + body_radius_y * cos_theta
        
        for j in range(body_segments):
            phi = 2.0 * math.pi * j / body_segments
            sin_phi = math.sin(phi)
            cos_phi = math.cos(phi)
            
            x = body_radius_x * sin_theta * cos_phi
            z = body_radius_z * sin_theta * sin_phi
            vertices.append((x, y, z))
    
    num_body_vertices = len(vertices)
    
    # Bico (cone alongado)
    spout_segments = 12
    spout_length = 25.0 * scale
    spout_start_y = body_center_y
    spout_radius_start = 8.0 * scale
    spout_radius_end = 3.0 * scale
    
    for i in range(spout_segments):
        angle = 2.0 * math.pi * i / spout_segments
        # Base do bico
        x_start = (body_radius_x + 5.0 * scale) * math.cos(angle)
        z_start = (body_radius_z + 5.0 * scale) * math.sin(angle)
        y_start = spout_start_y
        vertices.append((x_start, y_start, z_start))
        
        # Fim do bico (mais estreito)
        x_end = x_start + spout_length * math.cos(angle) * 0.3
        z_end = z_start + spout_length * math.sin(angle) * 0.3
        y_end = spout_start_y + 5.0 * scale
        vertices.append((x_end, y_end, z_end))
    
    num_spout_vertices = len(vertices) - num_body_vertices
    
    # Alça (torus parcial)
    handle_segments = 16
    handle_radius = 8.0 * scale
    handle_major = 15.0 * scale
    
    for i in range(handle_segments):
        major_angle = math.pi * (i / handle_segments)  # Apenas meio círculo
        for j in range(8):
            minor_angle = 2.0 * math.pi * j / 8
            x = (handle_major + handle_radius * math.cos(minor_angle)) * math.cos(major_angle)
            y = body_center_y + handle_radius * math.sin(minor_angle) + 10.0 * scale
            z = -(body_radius_z + handle_major) + (handle_major + handle_radius * math.cos(minor_angle)) * math.sin(major_angle)
            vertices.append((x, y, z))
    
    num_handle_vertices = len(vertices) - num_body_vertices - num_spout_vertices
    
    # Tampa (disco com pequeno botão)
    lid_segments = 16
    lid_radius = 20.0 * scale
    lid_y = body_radius_y + 5.0 * scale
    
    # Centro da tampa
    vertices.append((0.0, lid_y, 0.0))
    lid_center_idx = len(vertices) - 1
    
    # Borda da tampa
    lid_start = len(vertices)
    for i in range(lid_segments):
        angle = 2.0 * math.pi * i / lid_segments
        x = lid_radius * math.cos(angle)
        z = lid_radius * math.sin(angle)
        vertices.append((x, lid_y, z))
    
    # Arestas do corpo
    for i in range(body_stacks):
        for j in range(body_segments):
            idx = i * body_segments + j
            next_j = (j + 1) % body_segments
            next_i_idx = (i + 1) * body_segments + j
            next_j_idx = i * body_segments + next_j
            next_both_idx = (i + 1) * body_segments + next_j
            
            edges.append((idx, next_j_idx))
            if i < body_stacks:
                edges.append((idx, next_i_idx))
            
            if i == 0:
                faces.append([idx, next_j_idx, next_both_idx, next_i_idx])
            elif i == body_stacks - 1:
                faces.append([idx, next_j_idx, next_both_idx, next_i_idx])
            else:
                faces.append([idx, next_j_idx, next_both_idx, next_i_idx])
    
    # Arestas e faces do bico
    spout_start = num_body_vertices
    for i in range(spout_segments):
        base_idx = spout_start + i * 2
        tip_idx = spout_start + i * 2 + 1
        next_base_idx = spout_start + ((i + 1) % spout_segments) * 2
        next_tip_idx = spout_start + ((i + 1) % spout_segments) * 2 + 1
        
        edges.append((base_idx, tip_idx))
        edges.append((base_idx, next_base_idx))
        edges.append((tip_idx, next_tip_idx))
        
        faces.append([base_idx, next_base_idx, next_tip_idx, tip_idx])
    
    # Arestas e faces da alça
    handle_start = num_body_vertices + num_spout_vertices
    for i in range(handle_segments - 1):
        for j in range(8):
            idx = handle_start + i * 8 + j
            next_j = (j + 1) % 8
            next_i_idx = handle_start + (i + 1) * 8 + j
            next_j_idx = handle_start + i * 8 + next_j
            next_both_idx = handle_start + (i + 1) * 8 + next_j
            
            edges.append((idx, next_j_idx))
            edges.append((idx, next_i_idx))
            
            faces.append([idx, next_j_idx, next_both_idx, next_i_idx])
    
    # Faces da tampa
    for i in range(lid_segments):
        next_i = (i + 1) % lid_segments
        vertex_idx = lid_start + i
        next_vertex_idx = lid_start + next_i
        
        edges.append((lid_center_idx, vertex_idx))
        edges.append((vertex_idx, next_vertex_idx))
        faces.append([lid_center_idx, vertex_idx, next_vertex_idx])
    
    return Object3D(vertices, edges, faces)

