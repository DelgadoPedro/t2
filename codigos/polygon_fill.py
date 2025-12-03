from typing import List, Tuple

Point = Tuple[int, int]
Span = Tuple[int, int, int]  # (y, x_start, x_end)


class Edge:
    def __init__(self, y_max: int, x_of_y_min: float, inv_slope: float):
        self.y_max = y_max
        self.x = x_of_y_min
        self.inv_slope = inv_slope

    def step(self):
        self.x += self.inv_slope


def build_edge_table(points: List[Point]):
    # Build Edge Table (ET) as dict: y_min -> list[Edge]
    if not points:
        return {}, 0, 0
    n = len(points)
    y_min_all = min(p[1] for p in points)
    y_max_all = max(p[1] for p in points)
    ET = {}

    for i in range(n):
        x0, y0 = points[i]
        x1, y1 = points[(i + 1) % n]
        # ignore horizontal edges per standard scanline rules
        if y0 == y1:
            continue
        if y0 < y1:
            y_min = y0
            y_max = y1
            x_at_y_min = x0
        else:
            y_min = y1
            y_max = y0
            x_at_y_min = x1
        inv_slope = (x1 - x0) / (y1 - y0)
        edge = Edge(y_max=y_max, x_of_y_min=float(x_at_y_min), inv_slope=float(inv_slope))
        ET.setdefault(y_min, []).append(edge)
    return ET, y_min_all, y_max_all


def build_edge_table_and_fill(points: List[Point]) -> List[Span]:
    ET, y_min, y_max = build_edge_table(points)
    if not ET and not points:
        return []

    AET: List[Edge] = []
    spans: List[Span] = []

    for y in range(y_min, y_max + 1):
        # Move edges starting at y into AET
        if y in ET:
            AET.extend(ET[y])
        # Remove edges where y == y_max
        AET = [e for e in AET if y < e.y_max]
        # Sort AET by current x
        AET.sort(key=lambda e: e.x)

        # Pair up intersections to form spans
        x_list = [e.x for e in AET]
        # Round to int pixel coverage using ceil for start, floor for end
        for i in range(0, len(x_list), 2):
            if i + 1 >= len(x_list):
                break
            x_start = int(round(x_list[i] + 0.5)) if x_list[i] % 1 != 0 else int(x_list[i])
            x_end = int(round(x_list[i + 1] - 0.5)) if x_list[i + 1] % 1 != 0 else int(x_list[i + 1])
            if x_end >= x_start:
                spans.append((y, x_start, x_end))

        # Increment x by inverse slope for active edges
        for e in AET:
            e.step()

    return spans
