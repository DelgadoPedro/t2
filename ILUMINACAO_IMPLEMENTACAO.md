# Implementação dos Modelos de Iluminação

Este documento explica detalhadamente como os modelos de iluminação foram implementados no projeto, tanto na versão OpenGL quanto na versão Scan Line customizada.
## Visão Geral

O projeto implementa três modelos de shading:
1. **Flat Shading**: Uma cor por face
2. **Gouraud Shading**: Interpolação de cores entre vértices
3. **Phong Shading**: Interpolação de normais (iluminação por pixel)

Existem duas implementações:
- **OpenGL**: Usa funções prontas do OpenGL para cálculos de iluminação
- **Scan Line**: Implementação manual completa do algoritmo

## Modelo de Iluminação Phong

O modelo de iluminação Phong calcula a cor final como a soma de três componentes:

```
I = I_ambient + I_diffuse + I_specular
```

### Componentes

#### 1. Ambiente (Ambient)
```
I_ambient = light_ambient × material_ambient
```
- Iluminação uniforme em toda a superfície
- Simula luz refletida do ambiente
- Não depende da posição da luz ou do observador

#### 2. Difusa (Diffuse)
```
I_diffuse = light_diffuse × material_diffuse × max(0, N·L)
```
- Depende do ângulo entre a normal (N) e a direção da luz (L)
- Superfícies perpendiculares à luz recebem mais iluminação
- Lei de Lambert: `N·L = cos(θ)`

#### 3. Especular (Specular)
```
I_specular = light_specular × material_specular × (R·V)^shininess
```
- Simula reflexos brilhantes (highlights)
- R = vetor de reflexão da luz
- V = vetor do observador
- `shininess` controla o tamanho do highlight (maior = menor e mais brilhante)

---

## Implementação OpenGL

### Resumo

A implementação OpenGL usa **funções prontas** para cálculos de iluminação, mas os **cálculos de normais são feitos manualmente**. O OpenGL faz o trabalho pesado de calcular a iluminação Phong automaticamente quando você fornece as normais e configura os parâmetros de luz e material.

### Arquivo: `src/opengl_viewer.py`

### 1. Flat Shading

#### Como funciona:
- **Uma cor por face**: Toda a face recebe a mesma cor calculada uma única vez
- Usa a **normal da face** (não dos vértices)

#### Implementação:

```python
# Define o modo de shading
if self.shading_model == 'flat':
    glShadeModel(GL_FLAT)  # ← Função pronta do OpenGL
```

```python
# Aplica normal da face uma vez por triângulo
if self.shading_model == 'flat' and face_idx < len(face_normals):
    normal = face_normals[face_idx]
    glNormal3f(normal[0], normal[1], normal[2])
    # Depois desenha os 3 vértices SEM especificar normais individuais
```

#### Cálculo de Normais (Manual):
```python
def _calculate_face_normals_from_original(self, obj):
    """Calcula normais das faces usando produto vetorial"""
    for face in obj.faces:
        # 1. Pega 3 vértices da face
        v0, v1, v2 = vertices[face[0]], vertices[face[1]], vertices[face[2]]
        
        # 2. Calcula dois vetores: edge1 = v1 - v0, edge2 = v2 - v0
        edge1 = v1 - v0
        edge2 = v2 - v0
        
        # 3. Calcula produto vetorial: normal = edge1 × edge2
        normal = edge1.cross(edge2)
        
        # 4. Normaliza o vetor resultante
        normal = normal.normalize()
```

**Resultado**: Faces com bordas visíveis, aparência "facetada"

---

### 2. Gouraud Shading

#### Como funciona:
- **Cores calculadas nos vértices**: A iluminação é calculada uma vez por vértice
- **Interpolação linear**: O OpenGL interpola as cores entre os vértices
- Usa **normais dos vértices** (média das normais das faces adjacentes)

#### Implementação:

```python
# Define modo de interpolação suave
else:  # gouraud ou phong
    glShadeModel(GL_SMOOTH)  # ← Função pronta do OpenGL
```

```python
# Aplica normal de cada vértice ANTES de desenhá-lo
if self.shading_model in ['gouraud', 'phong']:
    if idx0 < len(vertex_normals):
        normal = vertex_normals[idx0]
        glNormal3f(normal[0], normal[1], normal[2])  # Normal do vértice 0
    glVertex3f(v0[0], v0[1], v0[2])
    
    # Repete para vértice 1 e 2...
```

#### Cálculo de Normais dos Vértices (Manual):
```python
def _calculate_vertex_normals_from_original(self, obj, face_normals):
    """Calcula normais dos vértices (média das normais das faces adjacentes)"""
    for vertex_idx in range(len(vertices)):
        # 1. Encontra todas as faces que compartilham esse vértice
        # 2. Soma as normais dessas faces
        normal_sum = sum(face_normals[face_idx] for faces containing vertex)
        
        # 3. Normaliza o resultado
        vertex_normal = normal_sum.normalize()
```

**O que o OpenGL faz automaticamente:**
- Calcula a iluminação Phong **nos vértices** usando as normais fornecidas
- Interpola linearmente as cores RGB entre os vértices
- Aplica a cor interpolada em cada pixel

**Resultado**: Superfície suave, mas highlights especulares podem aparecer distorcidos

---

### 3. Phong Shading

#### Como funciona:
- **Normais interpoladas**: As normais são interpoladas entre os vértices
- **Iluminação por pixel**: O OpenGL calcula a iluminação em cada pixel usando a normal interpolada
- Usa **normais dos vértices** (igual ao Gouraud)

#### Implementação:

```python
# Mesmo modo suave do Gouraud
glShadeModel(GL_SMOOTH)  # ← Função pronta do OpenGL
```

```python
# Ajusta parâmetros para destacar especular
if self.shading_model == 'phong':
    material_specular = [1.2, 1.2, 1.2, alpha]  # Specular mais intenso
    shininess = [128.0]  # Brilho mais alto (vs 50.0 do Gouraud)
```

**O que o OpenGL faz automaticamente:**
- Interpola as **normais** entre os vértices (não as cores!)
- Para cada pixel, calcula a iluminação Phong usando a normal interpolada
- Isso permite highlights especulares mais precisos

**Resultado**: Superfície suave com highlights especulares realistas

---

### Configuração da Iluminação (OpenGL)

#### Configuração da Luz:
```python
glLightfv(GL_LIGHT0, GL_POSITION, self.light_position)  # Posição
glLightfv(GL_LIGHT0, GL_AMBIENT, self.light_ambient)    # Componente ambiente
glLightfv(GL_LIGHT0, GL_DIFFUSE, self.light_diffuse)    # Componente difusa
glLightfv(GL_LIGHT0, GL_SPECULAR, self.light_specular)  # Componente especular
```

#### Configuração do Material:
```python
glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT, material_ambient)
glMaterialfv(GL_FRONT_AND_BACK, GL_DIFFUSE, material_diffuse)
glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, material_specular)
glMaterialfv(GL_FRONT_AND_BACK, GL_SHININESS, shininess)
```

---

## Implementação Scan Line

### Resumo

A implementação Scan Line é **completamente manual**. Todos os cálculos de iluminação são feitos pelo código Python, incluindo:
- Interpolação de normais
- Cálculo de iluminação Phong por pixel
- Z-buffer para oclusão
- Renderização pixel a pixel

### Arquivo: `src/scanline_phong.py`

### Estrutura Geral

```python
class ScanLinePhong:
    def __init__(self, width, height):
        self.depth_buffer = np.full((height, width), np.inf)  # Z-buffer
        self.image = QImage(width, height, QImage.Format_RGB32)
        
    def render_triangle(self, v0_2d, v1_2d, v2_2d, v0_3d, v1_3d, v2_3d, n0, n1, n2):
        # Renderiza triângulo com Phong shading
```

### Algoritmo de Renderização (Phong Verdadeiro)

#### 1. Ordenação por Y
```python
# Ordena vértices por coordenada Y (y_min, y_mid, y_max)
indices = np.argsort(points_2d[:, 1])
p0, p1, p2 = points_2d[indices[0]], points_2d[indices[1]], points_2d[indices[2]]
```

#### 2. Normalização de Normais dos Vértices
```python
# Normaliza normais dos vértices uma vez (antes da interpolação)
n0_sorted = n0_sorted / np.linalg.norm(n0_sorted)
n1_sorted = n1_sorted / np.linalg.norm(n1_sorted)
n2_sorted = n2_sorted / np.linalg.norm(n2_sorted)
```

**Importante**: Não calculamos cores nos vértices! Interpolamos as normais.

#### 3. Interpolação de Normais e Posições 3D
```python
# Para cada linha de scan (y)
for y in range(y_min, y_max + 1):
    # Interpola normais entre left e right (não cores!)
    normal = normal_left + (normal_right - normal_left) * t_y
    
    # Interpola posições 3D
    pos3d = pos3d_left + (pos3d_right - pos3d_left) * t_y
    
    # Para cada pixel na linha
    for x in range(x_start, x_end):
        # Interpola normal horizontalmente
        normal_pixel = normal + (normal_right - normal_left) * t_x
        
        # Interpola posição 3D horizontalmente
        pos3d_pixel = pos3d + (pos3d_right - pos3d_left) * t_x
        
        # Teste de profundidade (Z-buffer)
        if z < self.depth_buffer[y, x]:
            self.depth_buffer[y, x] = z
            
            # PHONG VERDADEIRO: calcular iluminação por pixel
            color = self.phong_shading(normal_pixel, pos3d_pixel)
            self.image.setPixel(x, y, color)
```

### Cálculo de Iluminação Phong (por Pixel)

```python
def phong_shading(self, normal, pos3d):
    """
    Calcula iluminação Phong para um pixel
    Phong verdadeiro: calcula iluminação usando a normal interpolada
    """
    # 1. Normalizar normal (já interpolada)
    normal = normal / np.linalg.norm(normal)
    
    # 2. Vetor da luz (da posição do ponto até a luz)
    light_vec = (self.light_position - pos3d) / np.linalg.norm(...)
    
    # 3. Componente Ambiente
    I_amb = self.light_ambient * self.material_ambient
    
    # 4. Componente Difusa
    N_dot_L = np.dot(normal, light_vec)
    if N_dot_L < 0:
        return I_amb  # Superfície não voltada para a luz
    I_diff = self.light_diffuse * self.material_diffuse * N_dot_L
    
    # 5. Componente Especular (Phong completo)
    if self.use_simple_shading:
        final_color = I_amb + I_diff  # Sem especular (opcional)
    else:
        # Vetor do observador
        view_vec = (self.viewer_position - pos3d) / np.linalg.norm(...)
        
        # Vetor de reflexão: R = 2(N·L)N - L
        reflection_vec = normal * (2.0 * N_dot_L) - light_vec
        reflection_vec = reflection_vec / np.linalg.norm(reflection_vec)
        
        # R·V (produto escalar)
        R_dot_V = np.dot(reflection_vec, view_vec)
        if R_dot_V > 0:
            specular_factor = math.pow(R_dot_V, self.material_shininess)
            I_spec = self.light_specular * self.material_specular * specular_factor
            final_color = I_amb + I_diff + I_spec
        else:
            final_color = I_amb + I_diff
    
    return np.clip(final_color, 0.0, 1.0)
```

**Diferença chave**: Esta função é chamada **para cada pixel**, não apenas nos vértices!

### Implementação Phong Verdadeiro

A implementação atual calcula iluminação Phong **por pixel**, não por vértice:

1. **Interpolação de Normais**
   - Normais são interpoladas entre os vértices
   - Interpolação vertical (entre linhas) e horizontal (entre pixels)
   - Normal é normalizada antes de calcular iluminação

2. **Interpolação de Posições 3D**
   - Posições 3D são interpoladas para cada pixel
   - Necessário para calcular vetores de luz e vista corretamente

3. **Cálculo de Iluminação por Pixel**
   - Para cada pixel, calcula iluminação Phong usando:
     - Normal interpolada
     - Posição 3D interpolada
   - Isso permite highlights especulares precisos

### Triangulação Otimizada

Para melhorar a visualização de faces quadradas (como cubos), a implementação usa uma triangulação otimizada:

- **Faces com 4 vértices (quadrados)**: Divididas em 2 triângulos usando diagonal oposta
  - Triângulo 1: `(0, 1, 2)`
  - Triângulo 2: `(0, 2, 3)`
- **Outras faces**: Triangulação em fan a partir do primeiro vértice

A interpolação de normais do Phong verdadeiro suaviza a transição entre triângulos, eliminando divisões visíveis.

### Parâmetros de Iluminação

A implementação usa valores otimizados para melhor visibilidade:

```python
# Propriedades de iluminação
light_ambient = [0.5, 0.5, 0.5]      # Aumentado de 0.3 para melhor visibilidade
light_diffuse = [1.0, 1.0, 1.0]
light_specular = [1.0, 1.0, 1.0]

# Propriedades do material
material_ambient = [0.4, 0.4, 0.5]   # Aumentado de 0.2 para melhor visibilidade
material_diffuse = [0.9, 0.9, 1.0]  # Aumentado de 0.8
material_specular = [1.0, 1.0, 1.0]
material_shininess = 64.0
```

**Resultado**: Iluminação ambiente final de aproximadamente **0.20** (antes era ~0.06), proporcionando melhor visibilidade mesmo em áreas não diretamente iluminadas.

### Otimizações Implementadas

1. **NumPy para arrays**
   - Depth buffer como array NumPy (muito mais rápido)
   - Operações vetorizadas quando possível

2. **Shading simplificado (opcional)**
   - Flag `use_simple_shading` para desabilitar componente especular
   - Reduz cálculos de potência quando não necessário

3. **Normalização eficiente**
   - Normais dos vértices normalizadas uma vez
   - Normalização por pixel apenas quando necessário

4. **Triangulação inteligente**
   - Divisão otimizada de faces quadradas
   - Reduz artefatos visuais nas arestas

- **Scan Line**: Implementa todas as fórmulas manualmente

Isso proporciona uma compreensão completa dos algoritmos de iluminação em computação gráfica.
