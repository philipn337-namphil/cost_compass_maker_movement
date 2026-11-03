# -*- coding: utf-8 -*-
"""
④ Plotly — 비교표를 차트로 바꾼다.

보고서 [그림 5-1]과 Streamlit 화면에서 함께 쓴다.

사용법
    python charts.py result.json          # HTML 파일로 저장
    python charts.py result.json --png    # PNG도 저장 (kaleido 필요)

디자인적 사고 (SWCON103) 중간 레포트 · Cost Compass
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import plotly.graph_objects as go

from analyze import load_breakdown, cost_rows

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass

# 설계안 구분용 색. 색만으로 구분되지 않도록 범례와 값 라벨을 함께 쓴다.
PALETTE = ["#4C78A8", "#E4A14B", "#72B06B", "#B06B8F", "#8F7FB8", "#9C9C9C"]


def stacked_resource_bar(df, totals, currency="USD", top_n=6):
    """설계안별 비용 구성 — 어떤 리소스가 차이를 만드는지 보여 준다."""
    designs = list(totals.keys())

    # 부모·자식 이중 계산을 피해 합산에 쓸 행만 고른다
    rows, _mode = cost_rows(df, totals)

    # 전체에서 비중이 큰 리소스만 개별 표시하고 나머지는 '기타'로 묶는다
    ranked = (rows.groupby("리소스")["월비용"].sum()
                  .sort_values(ascending=False))
    major = list(ranked.head(top_n).index)

    fig = go.Figure()
    for i, resource in enumerate(major):
        values = [
            rows[(rows["설계안"] == d) & (rows["리소스"] == resource)]["월비용"].sum()
            for d in designs
        ]
        fig.add_bar(name=resource, x=designs, y=values,
                    marker_color=PALETTE[i % len(PALETTE)])

    others = [
        rows[(rows["설계안"] == d) & (~rows["리소스"].isin(major))]["월비용"].sum()
        for d in designs
    ]
    if sum(others) > 0:
        fig.add_bar(name="기타", x=designs, y=others, marker_color="#C9CDD2")

    fig.update_layout(
        barmode="stack",
        title=f"[그림 5-1] 설계안별 월 예상 비용 구성 ({currency})",
        xaxis_title="설계안",
        yaxis_title=f"월 예상 비용 ({currency})",
        legend_title="리소스",
        template="plotly_white",
        height=520,
    )
    return fig


def total_comparison_bar(totals, currency="USD", baseline=None):
    """총액만 비교 — 한눈에 순위를 본다."""
    designs = list(totals.keys())
    values = [totals[d] for d in designs]

    if baseline is None:
        baseline = next((d for d in designs if "A" in d), designs[0])
    base = totals[baseline]

    labels = []
    for d in designs:
        if d == baseline or not base:
            labels.append(f"{totals[d]:,.2f}")
        else:
            labels.append(f"{totals[d]:,.2f}  ({(totals[d]-base)/base*100:+.0f}%)")

    fig = go.Figure(go.Bar(
        x=designs, y=values, text=labels, textposition="outside",
        marker_color=[PALETTE[i % len(PALETTE)] for i in range(len(designs))],
    ))
    fig.update_layout(
        title=f"설계안별 월 예상 비용 총액 ({currency})",
        xaxis_title="설계안",
        yaxis_title=f"월 예상 비용 ({currency})",
        template="plotly_white",
        height=420,
        showlegend=False,
    )
    fig.update_yaxes(rangemode="tozero")
    return fig


def traffic_curve(curve_rows, currency="USD"):
    """트래픽에 따른 비용 곡선 — 설계안 순위가 뒤집히는 지점을 찾는다.

    curve_rows: [{"트래픽GB": 100, "설계안": "A안", "월비용": 12.3}, ...]
    """
    import pandas as pd

    data = pd.DataFrame(curve_rows)
    fig = go.Figure()
    for i, design in enumerate(data["설계안"].unique()):
        sub = data[data["설계안"] == design].sort_values("트래픽GB")
        fig.add_scatter(
            x=sub["트래픽GB"], y=sub["월비용"], mode="lines+markers",
            name=design, line=dict(color=PALETTE[i % len(PALETTE)], width=2),
        )

    fig.update_layout(
        title=f"월 데이터 전송량에 따른 비용 변화 ({currency})",
        xaxis_title="월 데이터 전송량 (GB)",
        yaxis_title=f"월 예상 비용 ({currency})",
        template="plotly_white",
        height=460,
    )
    return fig


def main():
    parser = argparse.ArgumentParser(description="설계안 비용 차트 생성")
    parser.add_argument("json_path", nargs="?", default="result.json")
    parser.add_argument("--png", action="store_true", help="PNG도 저장 (kaleido 필요)")
    args = parser.parse_args()

    df, totals, currency = load_breakdown(args.json_path)

    figures = {
        "chart_total": total_comparison_bar(totals, currency),
        "chart_stacked": stacked_resource_bar(df, totals, currency),
    }

    for name, fig in figures.items():
        html = Path(f"{name}.html")
        fig.write_html(html)
        print(f"저장: {html}")

        if args.png:
            try:
                fig.write_image(f"{name}.png", scale=2)
                print(f"저장: {name}.png")
            except Exception as exc:
                print(f"  PNG 저장 실패 ({exc}). `pip install kaleido` 후 다시 시도하세요.")
                print("  HTML을 열어 화면 캡처해도 보고서에 쓰기 충분합니다.")


if __name__ == "__main__":
    main()
