"""
純 Python SVG 迷你走勢圖 (Sparkline) 生成模組
特點：
- 零外部相依 (無須載入任何 CDN 或 JavaScript，100% 離線可用)
- 支援正常 / 異常色彩切換 (藍 / 紅)
- 漸層半透明區域填色 (Gradient Fill)
- 內建 SVG <title> 懸停提示 (Hover Tooltip)，滑鼠移上去即顯示各時間點數據
- 終點 (當期) 醒目標示
"""

import uuid
from typing import List, Optional, Union


def generate_sparkline_svg(
    values: List[Union[int, float]],
    labels: Optional[List[str]] = None,
    is_anomaly: bool = False,
    width: int = 110,
    height: int = 28,
    unit: str = "件"
) -> str:
    """
    生成輕量級向量 SVG 迷你折線走勢圖

    :param values: 各期數值清單，例如 [3, 4, 3, 5, 4, 6, 15]
    :param labels: 各期對應的時間標籤，例如 ["08/17", "08/18", ..., "08/23"]
    :param is_anomaly: 是否為異常狀態 (True: 紅色警示, False: 科技藍)
    :param width: SVG 寬度 (px)
    :param height: SVG 高度 (px)
    :param unit: 數值單位 (預設: "件")
    :return: 內嵌 SVG 標籤字串
    """
    # 顏色配置
    if is_anomaly:
        stroke_color = "#d93025"  # 警示紅
        fill_start = "rgba(217, 48, 37, 0.35)"
        fill_end = "rgba(217, 48, 37, 0.02)"
        dot_color = "#d93025"
    else:
        stroke_color = "#1a73e8"  # 科技藍
        fill_start = "rgba(26, 115, 232, 0.28)"
        fill_end = "rgba(26, 115, 232, 0.02)"
        dot_color = "#1a73e8"

    # 若無數據或全部為 0
    if not values:
        values = [0]
    
    clean_values = [float(v) if v is not None else 0.0 for v in values]
    n = len(clean_values)
    
    # 補齊 labels
    if not labels or len(labels) != n:
        labels = [f"P{i+1}" for i in range(n)]

    pad_x = 6.0
    pad_y = 5.0
    usable_w = max(width - 2 * pad_x, 1.0)
    usable_h = max(height - 2 * pad_y, 1.0)

    min_val = min(clean_values)
    max_val = max(clean_values)
    val_range = max_val - min_val

    # 計算各點坐標
    points = []
    for i, val in enumerate(clean_values):
        if n == 1:
            x = pad_x + usable_w / 2.0
        else:
            x = pad_x + i * (usable_w / (n - 1))

        if val_range == 0:
            y = pad_y + usable_h / 2.0
        else:
            # y 軸由上至下 (0 在最上方)
            y = height - pad_y - ((val - min_val) / val_range) * usable_h
        
        points.append((x, y, val, labels[i]))

    # 構造折線路徑 (Polyline / Path)
    path_d_list = []
    for i, (x, y, _, _) in enumerate(points):
        cmd = "M" if i == 0 else "L"
        path_d_list.append(f"{cmd} {x:.1f},{y:.1f}")
    line_path_d = " ".join(path_d_list)

    # 構造面積填色路徑 (Area Path)
    first_x = points[0][0]
    last_x = points[-1][0]
    bottom_y = height - pad_y
    area_path_d = f"{line_path_d} L {last_x:.1f},{bottom_y:.1f} L {first_x:.1f},{bottom_y:.1f} Z"

    # 生成唯一的 Gradient ID
    grad_id = f"spark_grad_{uuid.uuid4().hex[:8]}"

    # 生成各點圓形與 Tooltip
    circles_svg = []
    for i, (x, y, val, lbl) in enumerate(points):
        is_last = (i == n - 1)
        r = 3.2 if is_last else 2.0
        c_fill = dot_color if is_last else "#ffffff"
        c_stroke = dot_color
        c_sw = 1.5 if is_last else 1.0
        
        # 格式化數值 (整數或一位小數)
        val_str = f"{int(val)}" if val.is_integer() else f"{val:.1f}"
        tooltip_text = f"{lbl}: {val_str} {unit}"
        
        circle_elem = (
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" '
            f'fill="{c_fill}" stroke="{c_stroke}" stroke-width="{c_sw}" style="cursor: pointer;">'
            f'<title>{tooltip_text}</title>'
            f'</circle>'
        )
        circles_svg.append(circle_elem)

    svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" style="vertical-align: middle; overflow: visible;">
  <defs>
    <linearGradient id="{grad_id}" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="{fill_start}" />
      <stop offset="100%" stop-color="{fill_end}" />
    </linearGradient>
  </defs>
  <path d="{area_path_d}" fill="url(#{grad_id})" />
  <path d="{line_path_d}" fill="none" stroke="{stroke_color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
  {''.join(circles_svg)}
</svg>"""
    return svg_content
