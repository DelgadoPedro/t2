"""
Canvas 2D para desenho de polígonos e preenchimento com scanline
"""
from typing import List, Tuple, Optional
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QPainter, QPen, QColor
from PyQt5.QtWidgets import QWidget, QMessageBox
from polygon_fill import build_edge_table_and_fill
import geometry3d as geo3d

Point = Tuple[int, int]
Span = Tuple[int, int, int]  # (y, x_start, x_end)


class Canvas(QWidget):
    """Canvas 2D para desenho de polígonos"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.points: List[Point] = []
        self.is_closed: bool = False
        self.stroke_color = QColor(0, 0, 0)
        self.fill_color = QColor(10, 132, 255)
        self.stroke_width: int = 2
        self.filled_spans: Optional[List[Span]] = None
        self.extruded_object: Optional[geo3d.Object3D] = None
        self.extrusion_depth: float = 100.0
        self.on_polygon_changed = None  # Callback para notificar mudanças
        self.setMinimumSize(800, 600)

    def clear(self):
        """Limpa o canvas"""
        self.points.clear()
        self.is_closed = False
        self.filled_spans = None
        self.extruded_object = None
        if self.on_polygon_changed:
            self.on_polygon_changed()
        self.update()

    def undo(self):
        """Desfaz a última ação"""
        if self.filled_spans is not None:
            # Se já preenchido, undo limpa o preenchimento primeiro
            self.filled_spans = None
        elif self.points:
            self.points.pop()
            # Notificar mudança se há objeto extrudado
            if self.extruded_object and self.on_polygon_changed:
                self.on_polygon_changed()
        self.update()

    def set_stroke_color(self, color: QColor):
        """Define a cor do contorno"""
        self.stroke_color = color
        self.update()

    def set_fill_color(self, color: QColor):
        """Define a cor de preenchimento"""
        self.fill_color = color
        self.update()

    def set_stroke_width(self, width: int):
        """Define a espessura do contorno"""
        self.stroke_width = max(1, int(width))
        self.update()

    def mousePressEvent(self, event):
        """Trata eventos de clique do mouse"""
        if event.button() == Qt.LeftButton:
            if self.is_closed:
                if self.extruded_object:
                    # Se já tem objeto extrudado, permitir edição: reabrir polígono para adicionar ponto
                    self.is_closed = False
                else:
                    # Iniciar novo polígono após fechar (apenas se não há objeto extrudado)
                    self.clear()
            self.points.append((event.x(), event.y()))
            self.update()
        elif event.button() == Qt.RightButton:
            # Tentar fechar polígono com validação
            if len(self.points) < 3:
                self._show_alert(
                    "Polígono Inválido",
                    "Um polígono precisa de pelo menos 3 pontos.\n"
                    "Adicione mais pontos antes de fechar o polígono."
                )
                return
            
            # Verificar se os pontos são colineares
            if self._are_points_collinear(self.points):
                self._show_alert(
                    "Polígono Inválido",
                    "Os pontos são colineares (estão todos na mesma linha).\n"
                    "Um polígono válido precisa de pontos que formem uma área."
                )
                return
            
            was_closed = self.is_closed
            self.is_closed = True
            self.update()
            # Notificar mudança ao fechar polígono
            if self.extruded_object and self.on_polygon_changed:
                self.on_polygon_changed()

    def _are_points_collinear(self, points: List[Point], tolerance: float = 1e-6) -> bool:
        """
        Verifica se todos os pontos são colineares
        
        Args:
            points: Lista de pontos
            tolerance: Tolerância para considerar pontos colineares
            
        Returns:
            True se todos os pontos são colineares, False caso contrário
        """
        if len(points) < 3:
            return False
        
        # Para 3 pontos, verificar se estão na mesma linha
        if len(points) == 3:
            x1, y1 = points[0]
            x2, y2 = points[1]
            x3, y3 = points[2]
            
            # Calcular área do triângulo (determinante)
            # Se área = 0, pontos são colineares
            area = abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1))
            return area < tolerance
        
        # Para mais de 3 pontos, verificar se todos estão na mesma linha
        # Usar os dois primeiros pontos para definir a linha
        x1, y1 = points[0]
        x2, y2 = points[1]
        
        # Calcular vetor diretor
        dx = x2 - x1
        dy = y2 - y1
        
        # Se os dois primeiros pontos são iguais, não podemos definir uma linha
        if abs(dx) < tolerance and abs(dy) < tolerance:
            return True
        
        # Verificar se todos os outros pontos estão na mesma linha
        for i in range(2, len(points)):
            x3, y3 = points[i]
            
            # Calcular área do triângulo formado pelos pontos 0, 1 e i
            area = abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1))
            
            if area > tolerance:
                return False
        
        return True
    
    def _show_alert(self, title: str, message: str):
        """Mostra um alerta ao usuário"""
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec_()
    
    def close_polygon(self):
        """Fecha o polígono com validações"""
        # Verificar se há menos de 3 pontos
        if len(self.points) < 3:
            self._show_alert(
                "Polígono Inválido",
                "Um polígono precisa de pelo menos 3 pontos.\n"
                "Adicione mais pontos antes de fechar o polígono."
            )
            return
        
        # Verificar se os pontos são colineares
        if self._are_points_collinear(self.points):
            self._show_alert(
                "Polígono Inválido",
                "Os pontos são colineares (estão todos na mesma linha).\n"
                "Um polígono válido precisa de pontos que formem uma área."
            )
            return
        
        self.is_closed = True
        # Notificar mudança ao fechar polígono
        if self.extruded_object and self.on_polygon_changed:
            self.on_polygon_changed()
        self.update()
    
    def update_extruded_object(self, depth: Optional[float] = None):
        """Atualiza o objeto 3D extrudado quando o polígono muda"""
        # Verificar se há menos de 3 pontos
        if len(self.points) < 3:
            return None
        
        # Verificar se o polígono está fechado
        if not self.is_closed:
            return None
        
        # Verificar se os pontos são colineares
        if self._are_points_collinear(self.points):
            # Não mostrar alerta aqui, pois pode ser chamado automaticamente
            # O alerta já foi mostrado ao tentar fechar o polígono
            return None
        try:
            if depth is None:
                depth = self.extrusion_depth if hasattr(self, 'extrusion_depth') else 100.0
            else:
                self.extrusion_depth = depth
                
            obj_3d = geo3d.extrude_polygon_2d(self.points, depth)
            
            # Preservar transformações do objeto anterior se existir
            if self.extruded_object:
                old_transform = self.extruded_object.transform
                obj_3d.transform = old_transform
                obj_3d._update_vertices()
            
            self.extruded_object = obj_3d
            return obj_3d
        except Exception:
            return None

    def fill_polygon(self):
        """Preenche o polígono usando scanline com validações"""
        # Verificar se há menos de 3 pontos
        if len(self.points) < 3:
            self._show_alert(
                "Polígono Inválido",
                "Um polígono precisa de pelo menos 3 pontos.\n"
                "Adicione mais pontos antes de preencher."
            )
            return
        
        # Verificar se o polígono está fechado
        if not self.is_closed:
            self._show_alert(
                "Polígono Não Fechado",
                "O polígono precisa estar fechado antes de preencher.\n"
                "Clique com o botão direito ou use o botão 'Close Polygon' para fechar."
            )
            return
        
        # Verificar se os pontos são colineares
        if self._are_points_collinear(self.points):
            self._show_alert(
                "Polígono Inválido",
                "Os pontos são colineares (estão todos na mesma linha).\n"
                "Um polígono válido precisa de pontos que formem uma área."
            )
            return
        
        spans = build_edge_table_and_fill(self.points)
        self.filled_spans = spans
        self.update()

    def paintEvent(self, event):
        """Renderiza o canvas"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        # Desenhar preenchimento primeiro se existir
        if self.filled_spans:
            painter.save()
            painter.setPen(Qt.NoPen)
            painter.setBrush(self.fill_color)
            color_pen = QPen(self.fill_color)
            color_pen.setWidth(1)
            painter.setPen(color_pen)
            for (y, x0, x1) in self.filled_spans:
                painter.drawLine(x0, y, x1, y)
            painter.restore()

        # Desenhar arestas do polígono
        pen = QPen(self.stroke_color)
        pen.setWidth(self.stroke_width)
        painter.setPen(pen)

        for i in range(1, len(self.points)):
            x0, y0 = self.points[i - 1]
            x1, y1 = self.points[i]
            painter.drawLine(x0, y0, x1, y1)

        # Desenhar aresta de fechamento se fechado
        if self.is_closed and len(self.points) >= 2:
            x0, y0 = self.points[-1]
            x1, y1 = self.points[0]
            painter.drawLine(x0, y0, x1, y1)

        # Desenhar vértices
        painter.setPen(Qt.NoPen)
        painter.setBrush(self.stroke_color)
        r = max(2, self.stroke_width)
        for (x, y) in self.points:
            painter.drawEllipse(QPoint(x, y), r, r)

