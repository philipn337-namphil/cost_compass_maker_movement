# -*- coding: utf-8 -*-
"""
③ pandas — Infracost JSON을 설계안 비교표로 바꾼다.

Infracost는 설계안 하나에 대한 비용 내역을 JSON으로 내놓는다.
이 스크립트는 그 JSON을 읽어 설계안끼리 나란히 놓고,
보고서 [표 5-3]에 바로 넣을 수 있는 형태로 정리한다.

사용법
    python analyze.py result.json
    python analyze.py result.json --inspect     # JSON 구조만 확인
    python analyze.py result.json --out report  # report.md / report.csv 저장

디자인적 사고 (SWCON103) 중간 레포트 · Cost Compass
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

# Windows 한글 콘솔(cp949)에서 특수문자 출력 시 죽지 않도록 한다.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass


# ---------------------------------------------------------------------
#  JSON 파싱
# ---------------------------------------------------------------------

def _to_float(value) -> float:
    """Infracost는 비용을 문자열로 준다. 지원하지 않는 리소스는 null."""
    if value is None:
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _walk_resources(resources, project_name, rows, prefix="", depth=0):
    """리소스 목록을 재귀적으로 훑는다. EBS 볼륨처럼 하위 리소스가 있는 경우가 있다.

    주의: 부모 리소스의 monthlyCost가 하위 리소스를 포함하는 경우가 있다.
    그대로 다 더하면 이중 계산이 되므로, 깊이와 리프 여부를 함께 기록해 두고
    cost_rows()에서 어느 쪽을 쓸지 총액과 대조해 판별한다.
    """
    for res in resources or []:
        name = res.get("name") or "(이름 없음)"
        full_name = f"{prefix}{name}"
        raw_cost = res.get("monthlyCost")
        subs = res.get("subresources") or []

        rows.append({
            "설계안": project_name,
            "리소스": full_name,
            "월비용": _to_float(raw_cost),
            "가격없음": raw_cost is None,
            "깊이": depth,
            "리프": len(subs) == 0,
        })

        _walk_resources(subs, project_name, rows, prefix=f"{full_name} / ", depth=depth + 1)


def cost_rows(df, totals):
    """이중 계산을 피해 '합산에 쓸 행'만 골라 준다.

    최상위 리소스만 더한 값과 리프 리소스만 더한 값을 각각 구해,
    Infracost가 보고한 총액에 더 가까운 쪽을 선택한다.
    """
    if df.empty:
        return df, "없음"

    grand_total = sum(totals.values())
    top = df[df["깊이"] == 0]
    leaf = df[df["리프"]]

    if abs(top["월비용"].sum() - grand_total) <= abs(leaf["월비용"].sum() - grand_total):
        return top, "최상위"
    return leaf, "리프"


def load_breakdown(json_path):
    """Infracost JSON → (리소스 단위 DataFrame, 설계안별 총액, 통화)"""
    path = Path(json_path)
    if not path.exists():
        raise SystemExit(
            f"파일을 찾을 수 없습니다: {path}\n"
            "먼저 아래를 실행하세요.\n"
            "  infracost breakdown --config-file infracost.yml --format json --out-file result.json"
        )

    data = json.loads(path.read_text(encoding="utf-8"))
    projects = data.get("projects") or []

    if not projects:
        raise SystemExit(
            "JSON 안에 projects가 없습니다. --inspect 로 구조를 먼저 확인하세요.\n"
            f"최상위 키: {list(data.keys())}"
        )

    rows = []
    totals = {}

    for proj in projects:
        name = proj.get("name") or proj.get("path") or "(이름 없음)"
        breakdown = proj.get("breakdown") or {}
        totals[name] = _to_float(breakdown.get("totalMonthlyCost"))
        _walk_resources(breakdown.get("resources"), name, rows)

    df = pd.DataFrame(rows)
    currency = data.get("currency") or "USD"
    return df, totals, currency


def inspect(json_path):
    """스키마가 예상과 다를 때 구조를 들여다본다."""
    data = json.loads(Path(json_path).read_text(encoding="utf-8"))
    print("최상위 키 :", list(data.keys()))
    projects = data.get("projects") or []
    print("프로젝트 수:", len(projects))
    for proj in projects:
        print("\n---", proj.get("name") or proj.get("path"))
        bd = proj.get("breakdown") or {}
        print("  breakdown 키:", list(bd.keys()))
        print("  totalMonthlyCost:", bd.get("totalMonthlyCost"))
        for res in (bd.get("resources") or [])[:3]:
            print("   · 리소스 키:", list(res.keys()))
            print("     name =", res.get("name"), "| monthlyCost =", res.get("monthlyCost"))


# ---------------------------------------------------------------------
#  보고서용 표 만들기
# ---------------------------------------------------------------------

def summary_table(df, totals, baseline=None):
    """보고서 [표 5-3] 형태로 정리한다."""
    names = list(totals.keys())
    if not names:
        raise SystemExit("설계안이 하나도 없습니다.")

    # 기준안(A안)을 정한다. 이름에 'A'가 들어간 것을 우선, 없으면 첫 번째.
    if baseline is None:
        baseline = next((n for n in names if "A" in n), names[0])

    base_total = totals[baseline]
    records = []

    rows, _mode = cost_rows(df, totals)

    for name in names:
        total = totals[name]

        sub = rows[rows["설계안"] == name]
        if len(sub) and total > 0:
            top = sub.loc[sub["월비용"].idxmax()]
            top_name = top["리소스"]
            top_share = top["월비용"] / total * 100
        else:
            top_name, top_share = "-", 0.0

        if name == baseline:
            diff_text = "기준"
        else:
            diff = total - base_total
            pct = (diff / base_total * 100) if base_total else 0.0
            diff_text = f"{diff:+,.2f} ({pct:+.1f}%)"

        records.append({
            "설계안": name,
            "월 예상 비용": round(total, 2),
            f"{baseline} 대비 증감": diff_text,
            "비용 1위 리소스": top_name,
            "1위 비중(%)": round(top_share, 1),
        })

    return pd.DataFrame(records), baseline


def contribution_table(df, totals, top_n=5):
    """설계안별 비용 기여도 상위 N개 — 보고서 5.3 해석에 쓴다."""
    rows, _mode = cost_rows(df, totals)
    out = []
    for name, total in totals.items():
        sub = rows[rows["설계안"] == name].sort_values("월비용", ascending=False).head(top_n)
        for _, row in sub.iterrows():
            out.append({
                "설계안": name,
                "리소스": row["리소스"],
                "월비용": round(row["월비용"], 2),
                "비중(%)": round(row["월비용"] / total * 100, 1) if total else 0.0,
            })
    return pd.DataFrame(out)


def reconcile(df, totals, tolerance=0.01):
    """합산 결과가 Infracost가 보고한 총액과 일치하는지 검증한다.

    차트와 기여도 비중은 리소스 단위 합산에 기대고 있으므로,
    여기서 어긋나면 보고서에 틀린 숫자가 들어간다. 조용히 넘기지 않는다.
    """
    rows, mode = cost_rows(df, totals)
    problems = []
    for name, total in totals.items():
        summed = rows[rows["설계안"] == name]["월비용"].sum()
        if abs(summed - total) > max(tolerance, total * 0.005):
            problems.append({
                "설계안": name,
                "리소스 합계": round(summed, 2),
                "보고된 총액": round(total, 2),
                "차이": round(summed - total, 2),
            })
    return pd.DataFrame(problems), mode


def unpriced_resources(df):
    """가격이 잡히지 않은 리소스 — 보고서 5.4 한계점 재료."""
    return df[df["가격없음"]][["설계안", "리소스"]].reset_index(drop=True)


def to_markdown(frame):
    """보고서에 붙여 넣을 마크다운 표. tabulate가 없어도 동작하도록 직접 만든다."""
    cols = list(frame.columns)
    lines = ["| " + " | ".join(str(c) for c in cols) + " |",
             "|" + "|".join(["---"] * len(cols)) + "|"]
    for _, row in frame.iterrows():
        lines.append("| " + " | ".join(str(row[c]) for c in cols) + " |")
    return "\n".join(lines)


# ---------------------------------------------------------------------
#  실행
# ---------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Infracost JSON → 설계안 비교표")
    parser.add_argument("json_path", nargs="?", default="result.json")
    parser.add_argument("--inspect", action="store_true", help="JSON 구조만 출력")
    parser.add_argument("--baseline", default=None, help="기준 설계안 이름 (기본: A안)")
    parser.add_argument("--out", default=None, help="저장할 파일 이름 (확장자 없이)")
    args = parser.parse_args()

    if args.inspect:
        inspect(args.json_path)
        return

    df, totals, currency = load_breakdown(args.json_path)
    summary, baseline = summary_table(df, totals, args.baseline)
    contrib = contribution_table(df, totals)
    unpriced = unpriced_resources(df)

    print(f"\n[표 5-3] 설계안별 월 예상 비용  (통화: {currency}, 기준: {baseline})\n")
    print(to_markdown(summary))

    print("\n\n[참고] 설계안별 비용 기여도 상위 5개\n")
    print(to_markdown(contrib))

    if len(unpriced):
        print("\n\n[주의] 가격이 산출되지 않은 리소스 — 보고서 5.4 한계점에 쓰세요\n")
        print(to_markdown(unpriced))
        print("\n  Infracost가 지원하지 않거나, 무료이거나, 사용량 가정이 없어서일 수 있습니다.")

    mismatch, mode = reconcile(df, totals)
    if len(mismatch):
        print("\n\n[경고] 리소스 합계가 Infracost 총액과 맞지 않습니다\n")
        print(to_markdown(mismatch))
        print(
            f"\n  현재 '{mode}' 리소스를 기준으로 합산했습니다.\n"
            "  총액 자체는 Infracost가 보고한 값이므로 표 5-3의 '월 예상 비용'은 정확합니다.\n"
            "  다만 '1위 비중'과 누적 막대그래프의 비율이 어긋날 수 있으니,\n"
            "  --inspect 로 JSON 구조를 확인한 뒤 쓰세요."
        )
    else:
        print(f"\n\n[확인] 리소스 합계가 총액과 일치합니다. (합산 기준: {mode} 리소스)")

    if args.out:
        md = Path(f"{args.out}.md")
        md.write_text(
            f"# 설계안 비교 결과 (통화: {currency})\n\n"
            f"## 표 5-3\n\n{to_markdown(summary)}\n\n"
            f"## 비용 기여도 상위 5개\n\n{to_markdown(contrib)}\n",
            encoding="utf-8",
        )
        csv = Path(f"{args.out}.csv")
        summary.to_csv(csv, index=False, encoding="utf-8-sig")
        print(f"\n\n저장: {md}, {csv}")


if __name__ == "__main__":
    main()
