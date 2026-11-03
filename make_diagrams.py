# -*- coding: utf-8 -*-
"""
보고서 2장의 다이어그램 두 장을 그린다.

    fig_2_1_pipeline.png      Cost Compass의 오픈소스 파이프라인
    fig_2_2_infracost_flow.png  Infracost의 비용 산출 흐름

아스키 그림 대신 PNG로 만들어 LaTeX에 바로 넣을 수 있게 한다.

사용법
    python make_diagrams.py

디자인적 사고 (SWCON103) 중간 레포트 · Cost Compass
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).parent

# --- 한글 폰트 -------------------------------------------------------
_KOREAN = r"C:\Windows\Fonts\malgun.ttf"
try:
    fm.fontManager.addfont(_KOREAN)
    plt.rcParams["font.family"] = fm.FontProperties(fname=_KOREAN).get_name()
except Exception:
    plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False

# --- 색 --------------------------------------------------------------
NAVY = "#1F3564"
BLUE = "#4C78A8"
AMBER = "#E4A14B"
GREEN = "#72B06B"
PLUM = "#B06B8F"
GREY = "#9AA3B2"
LINE = "#C9CDD2"
BG_SOFT = "#F4F6F9"


def box(ax, x, y, w, h, title, subtitle=None, note=None,
        face="#FFFFFF", edge=NAVY, lw=1.6, title_size=12, radius=0.025):
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h,
        boxstyle=f"round,pad=0.008,rounding_size={radius}",
        facecolor=face, edgecolor=edge, linewidth=lw, zorder=3,
    ))
    cx = x + w / 2
    if subtitle is None and note is None:
        ax.text(cx, y + h / 2, title, ha="center", va="center",
                fontsize=title_size, fontweight="bold", color=NAVY, zorder=4)
        return
    ax.text(cx, y + h * 0.68, title, ha="center", va="center",
            fontsize=title_size, fontweight="bold", color=NAVY, zorder=4)
    if subtitle:
        ax.text(cx, y + h * 0.40, subtitle, ha="center", va="center",
                fontsize=9.5, color="#3C4450", zorder=4)
    if note:
        ax.text(cx, y + h * 0.17, note, ha="center", va="center",
                fontsize=8.5, color=GREY, zorder=4, style="italic")


def arrow(ax, x1, y1, x2, y2, color=NAVY, lw=1.8, style="-|>", ls="-"):
    ax.add_patch(FancyArrowPatch(
        (x1, y1), (x2, y2), arrowstyle=style, mutation_scale=16,
        linewidth=lw, color=color, zorder=5, linestyle=ls,
        shrinkA=0, shrinkB=0,
    ))


def canvas(w, h):
    fig, ax = plt.subplots(figsize=(w, h))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, h / w * 10)
    ax.axis("off")
    return fig, ax


def save(fig, name):
    out = ROOT / f"{name}.png"
    fig.savefig(out, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  저장: {out.name}")


# =====================================================================
#  그림 2-1 · 오픈소스 파이프라인
# =====================================================================

def diagram_pipeline():
    fig, ax = canvas(11, 5.0)
    top = ax.get_ylim()[1]

    stages = ["설계안", "비용", "지표", "화면"]
    items = [
        ("OpenTofu", "설계안 3종을 코드로", "MPL-2.0", BLUE),
        ("Infracost", "월 예상 비용 산출", "Apache-2.0", AMBER),
        ("pandas", "비교표 · 기여도", "BSD-3-Clause", GREEN),
        ("Plotly + Streamlit", "차트 · 슬라이더", "MIT / Apache-2.0", PLUM),
    ]

    bw, bh = 2.10, 1.25
    gap = 0.40
    x0 = 0.20          # 마지막 박스 오른쪽 끝 = 0.20 + 3*2.50 + 2.10 = 9.80
    ytop = top - 1.95

    for i, ((title, sub, lic, color), stage) in enumerate(zip(items, stages)):
        x = x0 + i * (bw + gap)
        # 단계 라벨
        ax.text(x + bw / 2, ytop + bh + 0.52, stage, ha="center", va="center",
                fontsize=11, fontweight="bold", color=color)
        ax.plot([x + 0.25, x + bw - 0.25], [ytop + bh + 0.30, ytop + bh + 0.30],
                color=color, linewidth=2.2, solid_capstyle="round")
        box(ax, x, ytop, bw, bh, title, sub, lic, edge=color, lw=1.8)
        if i < len(items) - 1:
            arrow(ax, x + bw + 0.06, ytop + bh / 2,
                  x + bw + gap - 0.06, ytop + bh / 2, color=GREY, lw=2.0)

    # 사용량 파일 → Infracost
    ux, uw, uh = x0 + (bw + gap) * 1 - 0.1, 2.35, 0.95
    uy = ytop - 1.55
    box(ax, ux, uy, uw, uh, "infracost-usage.yml",
        "트래픽 등 사용량 가정", None, face=BG_SOFT, edge=AMBER,
        lw=1.4, title_size=10)
    arrow(ax, ux + uw / 2, uy + uh + 0.05,
          x0 + (bw + gap) * 1 + bw / 2, ytop - 0.05, color=AMBER, lw=1.8)

    # 아래 설명
    ax.text(5.0, 0.18,
            "코드만 읽어 비용을 계산한다. 클라우드 계정도, 배포도 필요하지 않다.",
            ha="center", va="center", fontsize=10, color="#3C4450")

    save(fig, "fig_2_1_pipeline")


# =====================================================================
#  그림 2-2 · Infracost 동작 흐름
# =====================================================================

def diagram_infracost_flow():
    # xlim 0~10, ylim 0~6
    fig, ax = canvas(11, 6.6)

    # --- 로컬 영역 테두리 ---
    lx, ly, lw_, lh = 0.30, 1.35, 6.45, 4.20
    ax.add_patch(FancyBboxPatch(
        (lx, ly), lw_, lh, boxstyle="round,pad=0.02,rounding_size=0.06",
        facecolor=BG_SOFT, edgecolor=LINE, linewidth=1.6,
        linestyle=(0, (6, 4)), zorder=1,
    ))
    ax.text(lx + 0.22, ly + lh - 0.28, "내 컴퓨터 (로컬)", ha="left", va="center",
            fontsize=11, fontweight="bold", color=GREY)

    bh = 0.95
    lw1, lx1 = 2.45, 0.65     # 왼쪽 열
    lw2, lx2 = 2.50, 4.00     # 오른쪽 열
    row1, row2 = 4.05, 2.05   # 두 행의 바닥 y

    # 1행 — 입력과 파싱
    box(ax, lx1, row1, lw1, bh, "main.tf", "또는 terraform show -json",
        None, edge=BLUE, title_size=11)
    box(ax, lx2, row1, lw2, bh, "리소스 종류 · 수량",
        "인스턴스 타입 · 리전 · 용량", None, edge=NAVY, title_size=11)
    arrow(ax, lx1 + lw1 + 0.08, row1 + bh / 2, lx2 - 0.08, row1 + bh / 2,
          color=NAVY, lw=1.8)
    ax.text((lx1 + lw1 + lx2) / 2, row1 + bh + 0.18, "①  파싱",
            ha="center", va="center", fontsize=10, fontweight="bold", color=NAVY)

    # 2행 — 사용량 가정과 집계
    box(ax, lx1, row2, lw1, bh, "infracost-usage.yml", "월 사용량 가정값",
        None, face="#FFFFFF", edge=AMBER, title_size=11)
    box(ax, lx2, row2, lw2, bh, "④  집계 · 출력", "표 / JSON / PR 코멘트",
        None, edge=GREEN, title_size=11)
    arrow(ax, lx1 + lw1 + 0.08, row2 + bh / 2, lx2 - 0.08, row2 + bh / 2,
          color=AMBER, lw=1.8)
    ax.text((lx1 + lw1 + lx2) / 2, row2 + bh + 0.18, "③  가정 주입",
            ha="center", va="center", fontsize=10, fontweight="bold", color=NAVY)

    # 세로 — 리소스 목록에서 집계로
    arrow(ax, lx2 + lw2 / 2, row1 - 0.06, lx2 + lw2 / 2, row2 + bh + 0.06,
          color=NAVY, lw=1.8)

    # --- 외부 API ---
    apx, apy, apw, aph = 7.25, 3.60, 2.40, 1.25
    box(ax, apx, apy, apw, aph, "Cloud Pricing API",
        "pricing.api.infracost.io", None, face="#FFF6E8", edge=AMBER,
        lw=1.8, title_size=11)

    # 로컬 ↔ 외부 (양방향 하나로)
    arrow(ax, lx2 + lw2 + 0.08, row1 + bh / 2, apx - 0.08, row1 + bh / 2,
          color=AMBER, lw=2.0, style="<|-|>")
    ax.text((lx2 + lw2 + apx) / 2, row1 + bh + 0.18, "②  단가 조회",
            ha="center", va="center", fontsize=10, fontweight="bold", color=NAVY)

    # 전송 / 비전송
    ax.text(apx + apw / 2, apy - 0.22,
            "보내는 것 · 리전, 인스턴스 타입,\n운영체제 등 가격 조회용 속성",
            ha="center", va="top", fontsize=9, color="#3C4450",
            linespacing=1.5)
    ax.text(apx + apw / 2, apy - 1.00,
            "보내지 않는 것 · 클라우드 자격 증명,\n시크릿, 플랜 JSON 파일",
            ha="center", va="top", fontsize=9, color="#B03A3A",
            fontweight="bold", linespacing=1.5)

    ax.text(5.0, 0.42,
            "파싱과 집계는 로컬에서 수행되고, 외부로 나가는 것은 단가 조회뿐이다.",
            ha="center", va="center", fontsize=10, color="#3C4450")

    save(fig, "fig_2_2_infracost_flow")


def main():
    print("다이어그램 생성 중...\n")
    print("[그림 2-1] 오픈소스 파이프라인")
    diagram_pipeline()
    print("[그림 2-2] Infracost 동작 흐름")
    diagram_infracost_flow()
    print("\n완료.")


if __name__ == "__main__":
    main()
