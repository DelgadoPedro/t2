# Polygon Fill - Aplicação de Computação Gráfica

Aplicação completa em PyQt5 para desenho de polígonos 2D, visualização 3D e renderização com diferentes modelos de iluminação. Implementa algoritmos de scanline, projeções 3D e shading (Flat, Gouraud e Phong).
**[Clique aqui](https://youtu.be/xbzDjTns7_w) para acessar o vídeo de demonstração do projeto!**

## Características

- **Desenho 2D**: Criação de polígonos com mouse e preenchimento usando scanline (ET/AET)
- **Visualização 3D**: Múltiplas abas com diferentes métodos de renderização
- **Modelos de Iluminação**: Flat, Gouraud e Phong shading
- **Projeções**: Perspectiva e ortográfica
- **Transformações 3D**: Rotação, translação, escala
- **Extrusão**: Conversão de polígonos 2D para objetos 3D
- **Controles Interativos**: Mouse e teclado para navegação e zoom

## Tecnologias Utilizadas

### Linguagem e Framework
- **Python 3.9+**: Linguagem principal
- **PyQt5 5.15.11**: Framework GUI para interface gráfica

### Bibliotecas de Computação Gráfica
- **PyOpenGL 3.1.0+**: Renderização OpenGL para iluminação avançada
- **PyOpenGL-accelerate**: Aceleração OpenGL
- **NumPy 1.21.0+**: Operações matemáticas e arrays eficientes

### Ferramentas de Build
- **PyInstaller**: Criação de executáveis standalone

## Funcionalidades

### Desenho 2D
- **Adicionar pontos**: Clique com botão esquerdo
- **Fechar polígono**: Clique com botão direito ou use o botão "Close Polygon"
- **Preencher**: Use o botão "Fill" para aplicar scanline
- **Cores**: Escolha cor de contorno e preenchimento
- **Validações**: Alertas automáticos para polígonos inválidos:
  - Polígonos com menos de 3 pontos
  - Polígonos com pontos colineares

### Visualização 3D
- **Rotação**: Arraste com botão esquerdo do mouse
- **Zoom**: Use a roda do mouse ou teclas **1** (zoom in) e **2** (zoom out)
- **Projeção**: Alterne entre perspectiva e ortográfica
  - **Perspectiva**: Ajuste a distância da projeção para controlar o FOV
  - **Ortográfica**: Projeção paralela sem distorção
- **Iluminação**: 
  - **OpenGL**: Controle posição da luz com setas do teclado
  - **Scan Line**: Fonte de luz visível na tela (representação gráfica)

### Modelos de Iluminação
- **Flat Shading**: Uma cor por face
- **Gouraud Shading**: Interpolação de cores entre vértices
- **Phong Shading**: Interpolação de normais com cálculo por pixel (mais realista)
  - **OpenGL**: Usa funções prontas do OpenGL
  - **Scan Line**: Implementação manual completa com Phong verdadeiro

### Extrusão
- Converta polígonos 2D em objetos 3D
- Ajuste a profundidade de extrusão
- Visualize em todas as abas 3D

## Algoritmos Implementados
- **[Clique aqui](docs/ILUMINACAO_IMPLEMENTACAO.md)** para acessar a explicação detalhada sobre a implementação dos modelos de iluminação (Flat, Gouraud, Phong) tanto no OpenGL quanto no Scan Line
### Scanline 2D (ET/AET)
- **Edge Table (ET)**: Tabela de arestas organizadas por Y mínimo
- **Active Edge Table (AET)**: Arestas ativas na linha atual
- Preenchimento eficiente de polígonos complexos

### Scanline 3D com Phong Shading Verdadeiro
- Interpolação de normais e posições 3D por pixel
- Z-buffer para oclusão
- Cálculo de iluminação Phong verdadeiro por pixel (não Gouraud)
- Triangulação otimizada para faces quadradas
- Iluminação ajustada para melhor visibilidade

### Projeções 3D
- **Perspectiva**: Projeção com ponto de fuga
- **Ortográfica**: Projeção paralela

### Transformações 3D
- Rotação
- Translação
- Escala
- Composição de transformações
