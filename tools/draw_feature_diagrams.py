# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 YiningZi (SeventhSlice)

"""Generate editable SVG and antialiased PNG feature diagrams (Pillow required)."""
import argparse
import html
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
BG, CARD, BORDER = "#101a28", "#192839", "#31455c"
WHITE, MUTED, TEAL, AMBER, RED = "#edf4fc", "#aabbd0", "#63dec6", "#ffbd74", "#ffa3a0"
GRID, BODY = "#536e8a", "#23394f"


class Canvas:
    def __init__(self, width, height, title, description, font, bold):
        self.width, self.height = width, height
        self.scale = 2
        self.image = Image.new("RGB", (width * 2, height * 2), BG)
        self.draw = ImageDraw.Draw(self.image)
        self.font, self.bold = font, bold
        self.elements = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
                         f'viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
                         f'<title id="title">{html.escape(title)}</title>',
                         f'<desc id="desc">{html.escape(description)}</desc>',
                         f'<rect width="{width}" height="{height}" fill="{BG}"/>']

    def rect(self, x, y, w, h, fill=CARD, stroke=None, radius=0):
        attrs = f' fill="{fill}"'
        if stroke:
            attrs += f' stroke="{stroke}" stroke-width="1.5"'
        self.elements.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}"{attrs}/>')
        box = tuple(round(v * 2) for v in (x, y, x + w, y + h))
        self.draw.rounded_rectangle(box, radius=round(radius * 2), fill=fill, outline=stroke,
                                    width=3 if stroke else 1)

    def line(self, points, color=GRID, width=2, dashed=False):
        pts = " ".join(f"{x:.2f},{y:.2f}" for x, y in points)
        dash = ' stroke-dasharray="7 7"' if dashed else ''
        self.elements.append(f'<polyline points="{pts}" fill="none" stroke="{color}" '
                             f'stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round"{dash}/>')
        if not dashed:
            self.draw.line([(round(x * 2), round(y * 2)) for x, y in points],
                           fill=color, width=max(1, round(width * 2)), joint="curve")
        else:
            elapsed = 0
            for (x1, y1), (x2, y2) in zip(points, points[1:]):
                distance = math.hypot(x2 - x1, y2 - y1)
                steps = max(1, math.ceil(distance))
                for i in range(steps):
                    if int(elapsed + i * distance / steps) % 14 < 7:
                        t, u = i / steps, (i + 1) / steps
                        self.draw.line([(round((x1 + (x2 - x1) * t) * 2), round((y1 + (y2 - y1) * t) * 2)),
                                        (round((x1 + (x2 - x1) * u) * 2), round((y1 + (y2 - y1) * u) * 2))],
                                       fill=color, width=max(1, round(width * 2)))
                elapsed += distance

    def polygon(self, points, fill):
        pts = " ".join(f"{x:.2f},{y:.2f}" for x, y in points)
        self.elements.append(f'<polygon points="{pts}" fill="{fill}"/>')
        self.draw.polygon([(round(x * 2), round(y * 2)) for x, y in points], fill=fill)

    def ellipse(self, cx, cy, rx, ry, fill=None, stroke=GRID, width=2, dashed=False):
        points = [(cx + rx * math.cos(i * math.tau / 100),
                   cy + ry * math.sin(i * math.tau / 100)) for i in range(101)]
        if fill:
            self.polygon(points, fill)
        if stroke:
            self.line(points, stroke, width, dashed)

    def text(self, x, y, label, size=25, color=WHITE, bold=False, anchor="start"):
        font_path = self.bold if bold else self.font
        font = ImageFont.truetype(str(font_path), size * 2)
        length = self.draw.textlength(label, font=font)
        offset = length / 2 if anchor == "middle" else length if anchor == "end" else 0
        if not (0 <= x * 2 - offset and x * 2 - offset + length <= self.width * 2 + 2):
            raise ValueError(f"Text outside canvas: {label}")
        self.draw.text((x * 2 - offset, y * 2), label, font=font, fill=color, anchor="lt")
        self.elements.append(f'<text x="{x}" y="{y}" dominant-baseline="text-before-edge" '
                             f'text-anchor="{anchor}" font-family="Microsoft YaHei, Noto Sans CJK SC, sans-serif" '
                             f'font-size="{size}" font-weight="{700 if bold else 400}" '
                             f'fill="{color}">{html.escape(label)}</text>')

    def arrow(self, points, color=TEAL, width=3):
        self.line(points, color, width)
        (x1, y1), (x, y) = points[-2:]
        angle = math.atan2(y - y1, x - x1)
        back_x, back_y = x - 12 * math.cos(angle), y - 12 * math.sin(angle)
        self.polygon([(x, y), (back_x + 6 * math.sin(angle), back_y - 6 * math.cos(angle)),
                      (back_x - 6 * math.sin(angle), back_y + 6 * math.cos(angle))], color)

    def save(self, name):
        output = ROOT / "docs/images"
        output.mkdir(parents=True, exist_ok=True)
        (output / f"{name}.svg").write_text("\n".join(self.elements + ['</svg>']) + "\n", encoding="utf-8")
        self.image.resize((self.width, self.height), Image.Resampling.LANCZOS).save(output / f"{name}.png")
        print(f"Generated {name}.svg and {name}.png ({self.width} x {self.height})")


def tube(c, cx, top, bottom, radius, selected_y, deformation=0, highlight=True, tint=False):
    def influence(y):
        t = min(1, abs(y - selected_y) / 96)
        return 1 - t * t * (3 - 2 * t)

    ys = [top + (bottom - top) * i / 44 for i in range(45)]
    def r(y):
        return radius + deformation * influence(y)
    silhouette = [(cx - r(y), y) for y in ys] + [(cx + r(y), y) for y in reversed(ys)]
    c.polygon(silhouette, BODY)
    c.line([(cx - r(y), y) for y in ys], GRID)
    c.line([(cx + r(y), y) for y in ys], GRID)
    if tint:
        band = [y for y in ys if abs(y - selected_y) < 84]
        c.polygon([(cx - r(y), y) for y in band] + [(cx + r(y), y) for y in reversed(band)], "#544143")
    for level in range(13):
        y = top + (bottom - top) * level / 12
        near = abs(y - selected_y) < 84
        color = (AMBER if highlight else RED) if near else GRID
        c.ellipse(cx, y, r(y), radius * .23, stroke=color if (highlight or tint) else GRID, width=1.4)
    for factor in (-.65, -.3, .3, .65):
        c.line([(cx + r(y) * factor, y) for y in ys], GRID, 1.2)
    if highlight:
        c.ellipse(cx, selected_y, r(selected_y), radius * .23, stroke=AMBER, width=5)
        for side in range(12):
            a = side * math.tau / 12
            c.ellipse(cx + r(selected_y) * math.cos(a), selected_y + radius * .23 * math.sin(a),
                      3.6, 3.6, fill=AMBER, stroke=None)


def overview(font, bold):
    c = Canvas(1680, 950, "ZLoop 功能示意：测量环线、设置目标周长与局部平滑调整",
               "三步原理示意，尺寸为示例值，不是 Blender 界面截图或真实模型对比。", font, bold)
    c.text(52, 38, "ZLoop", 64, bold=True)
    c.text(56, 118, "环线测量与精确周长调整", 30, MUTED)
    c.rect(1328, 59, 298, 54, "#223c43", radius=27)
    c.text(1477, 72, "BLENDER · 环线工具", 23, TEAL, anchor="middle")
    cards = [(52, "01", "测量当前环线"), (587, "02", "设置目标周长"), (1122, "03", "局部平滑调整")]
    for x, number, title in cards:
        c.rect(x, 193, 506, 609, stroke=BORDER, radius=22)
        c.text(x + 26, 218, number, 26, TEAL, bold=True)
        c.text(x + 88, 213, title, 32, bold=True)
        c.line([(x + 26, 268), (x + 480, 268)], BORDER, 1)
    tube(c, 298, 318, 601, 104, 474)
    c.line([(405, 474), (475, 429)], AMBER)
    c.text(421, 392, "闭合环线", 22, AMBER)
    c.text(305, 649, "当前周长  60.0 mm", 29, AMBER, bold=True, anchor="middle")
    c.text(305, 706, "选中一条完整环线", 25, MUTED, anchor="middle")
    c.text(305, 745, "测量边数、总长与平均边长", 23, MUTED, anchor="middle")

    c.ellipse(729, 457, 72, 72, fill=BODY, stroke=AMBER, width=4)
    c.ellipse(950, 457, 79.2, 79.2, fill=BODY, stroke=TEAL, width=4)
    c.arrow([(824, 457), (851, 457)], TEAL)
    c.text(729, 566, "60.0 mm", 27, AMBER, anchor="middle")
    c.text(950, 566, "66.0 mm", 27, TEAL, anchor="middle")
    c.rect(670, 629, 338, 57, "#233c48", radius=12)
    c.text(839, 640, "缩放倍率  1.10 ×", 27, TEAL, bold=True, anchor="middle")
    c.text(839, 706, "输入目标周长并应用缩放", 25, MUTED, anchor="middle")
    c.text(839, 745, "等比例调整选中环线", 23, MUTED, anchor="middle")

    tube(c, 1375, 317, 601, 72, 467, deformation=29)
    c.line([(1303, 317), (1303, 601)], MUTED, 1.5, dashed=True)
    c.line([(1447, 317), (1447, 601)], MUTED, 1.5, dashed=True)
    c.line([(1503, 373), (1520, 373), (1520, 561), (1503, 561)], TEAL, 2)
    c.text(1375, 649, "有限半径 · 平滑过渡", 29, TEAL, bold=True, anchor="middle")
    c.text(1375, 706, "自动估算局部衰减半径", 25, MUTED, anchor="middle")
    c.text(1375, 745, "结合环线转角与邻层间距", 23, MUTED, anchor="middle")
    c.ellipse(68, 852, 6, 6, fill=AMBER, stroke=None)
    c.text(85, 836, "橙色：选中环线及附近影响", 23, MUTED)
    c.line([(466, 852), (496, 852)], MUTED, 2, dashed=True)
    c.text(509, 836, "虚线：原始轮廓", 23, MUTED)
    c.text(1627, 839, "尺寸为示例值 · 原理示意", 23, MUTED, anchor="end")
    c.text(53, 893, "调整指围建议同时开启「自动衰减」与「仅影响相连项」。", 24, WHITE)
    c.save("feature-overview")


def connected(font, bold):
    c = Canvas(1680, 956, "仅影响相连项：邻近手指的空间距离与网格连接距离对比",
               "两根手指在掌部相连，开启相连比例编辑并保持局部半径时，邻指不因靠近而变形。", font, bold)
    c.text(52, 37, "仅影响相连项", 49, bold=True)
    c.text(54, 107, "手指侧面靠近，网格路径却需要绕过掌部。", 27, MUTED)
    for x in (52, 864):
        c.rect(x, 180, 764, 619, stroke=BORDER, radius=22)
    c.rect(76, 203, 82, 43, "#523b42", radius=10)
    c.text(117, 208, "关闭", 23, RED, anchor="middle", bold=True)
    c.text(180, 205, "按空间距离衰减", 31, bold=True)
    c.rect(888, 203, 82, 43, "#24473f", radius=10)
    c.text(929, 208, "开启", 23, TEAL, anchor="middle", bold=True)
    c.text(992, 205, "沿网格连接衰减", 31, bold=True)

    for x in (52, 864):
        first, second = x + 238, x + 413
        c.rect(x + 151, 651, 348, 66, BODY, stroke=GRID, radius=14)
        for y in (669, 694):
            c.line([(x + 163, y), (x + 485, y)], GRID, 1)
        for offset in range(8):
            c.line([(x + 175 + offset * 42, 657), (x + 175 + offset * 42, 711)], GRID, 1)
        tube(c, first, 324, 662, 72, 449, deformation=13)
        tube(c, second, 335, 662, 67, 449, deformation=11 if x == 52 else 0,
             highlight=False, tint=(x == 52))
        c.text(first, 286, "当前手指", 22, AMBER, anchor="middle")
        c.text(second, 286, "相邻手指", 22, RED if x == 52 else TEAL, anchor="middle")
        c.text(x + 585, 680, "掌部相连", 22, MUTED, anchor="middle")
    c.ellipse(379, 449, 183, 108, stroke=RED, width=2.5, dashed=True)
    c.arrow([(382, 446), (410, 446)], RED, 3)
    c.line([(482, 449), (650, 449), (650, 474)], RED, 2)
    c.text(650, 490, "邻指也可能", 24, RED, anchor="middle")
    c.text(650, 527, "受到影响", 24, RED, anchor="middle")
    c.text(434, 744, "空间靠近 → 可能一起变形", 27, RED, anchor="middle", bold=True)

    c.ellipse(1102, 449, 100, 108, stroke=TEAL, width=2.5, dashed=True)
    c.arrow([(1102, 459), (1102, 686), (1277, 686), (1277, 527)], MUTED, 2.5)
    c.line([(1382, 450), (1457, 450), (1457, 475)], TEAL, 2)
    c.text(1455, 491, "局部半径内", 24, TEAL, anchor="middle")
    c.text(1455, 528, "邻指保持不动", 24, TEAL, anchor="middle")
    c.text(1246, 744, "沿网格路径 → 限定局部影响", 27, TEAL, anchor="middle", bold=True)

    c.rect(52, 831, 1576, 70, "#233441", radius=14)
    c.text(80, 849, "使用建议：开启自动衰减并保持局部半径；半径过大仍可能经掌部影响其他手指。", 25)
    c.text(54, 921, "虚线：影响范围示意    箭头：网格连接路径", 21, MUTED)
    c.text(1626, 921, "原理示意 · 非自动手指分割", 21, MUTED, anchor="end")
    c.save("connected-falloff")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--font", type=Path, default=Path("C:/Windows/Fonts/msyh.ttc"))
    parser.add_argument("--bold-font", type=Path, default=Path("C:/Windows/Fonts/msyhbd.ttc"))
    args = parser.parse_args()
    if not args.font.is_file() or not args.bold_font.is_file():
        parser.error("Supply --font and --bold-font paths to Chinese-capable TrueType fonts")
    overview(args.font, args.bold_font)
    connected(args.font, args.bold_font)


if __name__ == "__main__":
    main()
