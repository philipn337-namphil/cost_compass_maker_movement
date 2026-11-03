# -*- coding: utf-8 -*-
"""
보고서에 넣을 그림을 한 번에 만든다.

전제: 아래 세 JSON이 이미 있어야 한다.
    result.json                 기본 (t3.small, MySQL 8.0)
    result-large.json           t3.large
    result-db-supported.json    확장 지원 없는 엔진 버전

사용법
    python make_figures.py

결과
    fig_5_1_cost_breakdown.png   설계안별 비용 구성 (누적 막대)
    fig_5_2_instance_type.png    인스턴스 타입에 따른 비용 변화
    fig_5_3_engine_version.png   DB 엔진 버전에 따른 RDS 비용 구성
    (각각 .html 도 함께 저장)

디자인적 사고 (SWCON103) 중간 레포트 · Cost Compass
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import plotly.graph_objects as go

from analyze import load_breakdown, cost_rows

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

# 한글이 PNG에서 깨지지 않도록 Windows 기본 한글 폰트를 지정한다.
FONT = "Malgun Gothic, Arial, sans-serif"
PALETTE = ["#4C78A8", "#E4A14B", "#72B06B", "#B06B8F", "#8F7FB8", "#9C9C9C"]
ACCENT_RED = "#C0504D"

ROOT = Path(__file__).parent
FIGDIR = ROOT / "figure"
FIGDIR.mkdir(exist_ok=True)


def _layout(fig, title, xaxis, yaxis, height=520):
    # 그림 번호와 제목은 보고서의 LaTeX 캡션이 붙인다.
    # 이미지 안에도 제목을 넣으면 같은 제목이 두 번 보이므로 비워 둔다.
    # (title 인자는 HTML 파일 이름표 용도로만 남김)
    fig.update_layout(
        title=None,
        xaxis_title=xaxis,
        yaxis_title=yaxis,
        template="plotly_white",
        font=dict(family=FONT, size=14),
        height=height,
        margin=dict(t=40, b=60, l=70, r=40),
    )
    return fig


def _save(fig, name):
    html = FIGDIR / f"{name}.html"
    fig.write_html(html)
    try:
        png = FIGDIR / f"{name}.png"
        fig.write_image(png, scale=2, width=1000, height=fig.layout.height or 520)
        print(f"  저장: {png.name}  /  {html.name}")
    except Exception as exc:
        print(f"  저장: {html.name}  (PNG 실패: {exc})")
        print("        pip install kaleido 후 다시 시도하거나, HTML을 열어 캡처하세요.")


def _short(name):
    """'A안_최소구성' → 'A안<br>최소구성'. plotly는 줄바꿈에 <br>를 쓴다."""
    return name.replace("_", "<br>")


def _inside_labels(values, total, fmt="${:,.2f}", min_share=0.07):
    """막대 안에 넣을 라벨. 너무 얇은 구간은 글씨가 뭉개지므로 비운다."""
    out = []
    for v in values:
        if total > 0 and v / total >= min_share:
            out.append(fmt.format(v))
        else:
            out.append("")
    return out


# ---------------------------------------------------------------------
#  그림 5-1 · 설계안별 비용 구성
# ---------------------------------------------------------------------

def figure_cost_breakdown():
    df, totals, currency = load_breakdown(ROOT / "result.json")
    rows, _ = cost_rows(df, totals)

    designs = list(totals.keys())
    resources = list(rows.groupby("리소스")["월비용"].sum()
                         .sort_values(ascending=False).index)

    fig = go.Figure()
    for i, res in enumerate(resources):
        values = [rows[(rows["설계안"] == d) & (rows["리소스"] == res)]["월비용"].sum()
                  for d in designs]
        if sum(values) <= 0:
            continue
        # 라벨을 넣을지는 '축 전체 높이' 대비 구간 두께로 판단한다.
        # 막대 자기 총액을 기준으로 삼으면, 작은 막대의 얇은 구간에도
        # 라벨이 붙어 글씨가 뭉개진다.
        axis_max = max(totals.values()) or 1
        labels = [
            f"${v:,.2f}" if v / axis_max >= 0.06 else ""
            for v in values
        ]
        fig.add_bar(
            name=res, x=[_short(d) for d in designs], y=values,
            marker_color=PALETTE[i % len(PALETTE)],
            text=labels, textposition="inside",
            insidetextfont=dict(family=FONT, size=13),
        )

    # 총액을 막대 위에 적어 준다
    fig.add_scatter(
        x=[_short(d) for d in designs], y=[totals[d] for d in designs],
        mode="text", text=[f"<b>${totals[d]:,.2f}</b>" for d in designs],
        textposition="top center", showlegend=False,
        textfont=dict(family=FONT, size=15),
    )

    fig.update_layout(barmode="stack", legend_title="리소스")
    fig.update_yaxes(rangemode="tozero")
    return _layout(fig, "[그림 5-1] 설계안별 월 예상 비용 구성",
                   "설계안", f"월 예상 비용 ({currency})", height=560)


# ---------------------------------------------------------------------
#  그림 5-2 · 인스턴스 사양 비교
# ---------------------------------------------------------------------

def figure_instance_type():
    _, small, currency = load_breakdown(ROOT / "result.json")
    _, large, _ = load_breakdown(ROOT / "result-large.json")

    designs = list(small.keys())
    labels = [_short(d) for d in designs]

    fig = go.Figure()
    fig.add_bar(name="t3.small", x=labels, y=[small[d] for d in designs],
                marker_color=PALETTE[0],
                text=[f"${small[d]:,.2f}" for d in designs], textposition="outside")
    fig.add_bar(name="t3.large", x=labels, y=[large[d] for d in designs],
                marker_color=PALETTE[1],
                text=[f"${large[d]:,.2f}" for d in designs], textposition="outside")

    # 증가율을 주석으로
    for i, d in enumerate(designs):
        pct = (large[d] - small[d]) / small[d] * 100 if small[d] else 0
        fig.add_annotation(
            x=labels[i], y=max(large[d], small[d]),
            text=f"<b>+{pct:.0f}%</b>", showarrow=False,
            yshift=42, font=dict(family=FONT, size=14, color=ACCENT_RED),
        )

    fig.update_layout(barmode="group", legend_title="인스턴스 타입")
    fig.update_yaxes(rangemode="tozero")
    return _layout(fig, "[그림 5-2] 인스턴스 사양을 올렸을 때의 비용 변화",
                   "설계안", f"월 예상 비용 ({currency})", height=520)


# ---------------------------------------------------------------------
#  그림 5-3 · DB 엔진 버전
# ---------------------------------------------------------------------

def _rds_components(json_path):
    """RDS 리소스의 비용 항목을 {항목명: 금액} 으로 꺼낸다."""
    data = json.loads(Path(json_path).read_text(encoding="utf-8"))
    for proj in data.get("projects", []):
        for res in (proj.get("breakdown") or {}).get("resources") or []:
            if "db_instance" in (res.get("name") or ""):
                out = {}
                for cc in res.get("costComponents") or []:
                    try:
                        out[cc.get("name", "?")] = float(cc.get("monthlyCost") or 0)
                    except (TypeError, ValueError):
                        pass
                return out
    return {}


def figure_engine_version():
    with_ext = _rds_components(ROOT / "result.json")
    without = _rds_components(ROOT / "result-db-supported.json")

    def label(name):
        n = name.lower()
        if "extended support" in n:
            return "확장 지원"
        if "storage" in n:
            return "스토리지"
        return "DB 인스턴스"

    cats = ["MySQL 8.0<br>(표준 지원 종료)", "MySQL 9.0<br>(확장 지원 없음)"]
    series = {}
    for key, comps in (("a", with_ext), ("b", without)):
        for name, cost in comps.items():
            series.setdefault(label(name), {"a": 0.0, "b": 0.0})[key] += cost

    order = ["DB 인스턴스", "스토리지", "확장 지원"]
    colors = {"DB 인스턴스": PALETTE[0], "스토리지": PALETTE[2], "확장 지원": ACCENT_RED}

    tot_a = sum(with_ext.values())
    tot_b = sum(without.values())

    fig = go.Figure()
    for name in order:
        if name not in series:
            continue
        vals = [series[name]["a"], series[name]["b"]]
        # 축 전체 높이 대비 얇은 구간(스토리지)은 라벨을 비운다
        axis_max = max(tot_a, tot_b) or 1
        labels = [f"${v:,.2f}" if v / axis_max >= 0.06 else "" for v in vals]
        fig.add_bar(name=name, x=cats, y=vals, marker_color=colors[name],
                    text=labels, textposition="inside",
                    insidetextfont=dict(family=FONT, size=14))
    fig.add_scatter(x=cats, y=[tot_a, tot_b], mode="text",
                    text=[f"<b>${tot_a:,.2f}</b>", f"<b>${tot_b:,.2f}</b>"],
                    textposition="top center", showlegend=False,
                    textfont=dict(family=FONT, size=15))

    # 오른쪽 막대 위 빈 공간에 둔다 (왼쪽 막대와 겹치지 않도록)
    fig.add_annotation(
        xref="paper", yref="paper", x=0.78, y=0.72,
        text=(f"<b>engine_version 한 줄 차이로</b><br>"
              f"<b>월 ${tot_a - tot_b:,.2f}</b>"),
        showarrow=False, align="center",
        font=dict(family=FONT, size=15, color=ACCENT_RED),
        bgcolor="rgba(255,255,255,0.92)", bordercolor=ACCENT_RED, borderwidth=1,
        borderpad=8,
    )

    fig.update_layout(barmode="stack", legend_title="비용 항목")
    fig.update_yaxes(rangemode="tozero")
    return _layout(fig, "[그림 5-3] DB 엔진 버전에 따른 RDS 비용 구성",
                   "engine_version", "월 예상 비용 (USD)", height=560)


# ---------------------------------------------------------------------

def main():
    needed = ["result.json", "result-large.json", "result-db-supported.json"]
    missing = [f for f in needed if not (ROOT / f).exists()]
    if missing:
        raise SystemExit(
            "다음 파일이 없습니다: " + ", ".join(missing) +
            "\nREADME의 3단계와 '더 해 볼 것'을 먼저 실행하세요."
        )

    print("그림 생성 중...\n")
    print("[그림 5-1] 설계안별 비용 구성")
    _save(figure_cost_breakdown(), "fig_5_1_cost_breakdown")
    print("[그림 5-2] 인스턴스 사양 비교")
    _save(figure_instance_type(), "fig_5_2_instance_type")
    print("[그림 5-3] DB 엔진 버전")
    _save(figure_engine_version(), "fig_5_3_engine_version")
    print("\n완료. PNG를 LaTeX의 figure/ 폴더에 넣으면 됩니다.")


if __name__ == "__main__":
    main()
