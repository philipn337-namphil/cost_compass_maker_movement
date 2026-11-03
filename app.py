# -*- coding: utf-8 -*-
"""
⑤ Streamlit — Cost Compass 화면

학생이 트래픽 가정을 직접 움직여 가며 설계안의 비용과 순위가
어떻게 바뀌는지 확인한다.

보고서 2.4에서 밝혔듯, 이 프로젝트가 다루는 것은 '불안'이다.
불안은 고정된 표 하나로는 풀리지 않는다. 슬라이더를 직접 움직여
가정을 바꿔 가며 차이가 얼마나 벌어지는지 눈으로 볼 때
비용은 판단의 근거가 된다.

실행
    streamlit run app.py

디자인적 사고 (SWCON103) 중간 레포트 · Cost Compass
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

from analyze import load_breakdown, summary_table, contribution_table, unpriced_resources
from charts import stacked_resource_bar, total_comparison_bar, traffic_curve

ROOT = Path(__file__).parent
BASE_CONFIG = ROOT / "infracost.yml"
BASE_USAGE = ROOT / "infracost-usage.yml"
TMP_USAGE = ROOT / ".cc_usage.tmp.yml"
TMP_CONFIG = ROOT / ".cc_config.tmp.yml"
TMP_RESULT = ROOT / ".cc_result.tmp.json"
CACHED_RESULT = ROOT / "result.json"

# 트래픽 가정이 들어가는 키. --sync-usage-file 로 만든 파일에서
# 이 이름이 다르면 사이드바에서 바꿀 수 있게 해 둔다.
DEFAULT_TRAFFIC_KEY = "processed_bytes_gb"


# ---------------------------------------------------------------------
#  사용량 파일 조작
# ---------------------------------------------------------------------

def set_key_everywhere(node, key, value):
    """중첩된 dict 어디에 있든 해당 키를 찾아 값을 바꾼다.

    --sync-usage-file 로 생성한 파일의 구조를 모르더라도 동작하도록
    재귀적으로 훑는다. 바꾼 횟수를 돌려준다.
    """
    changed = 0
    if isinstance(node, dict):
        for k, v in node.items():
            if k == key and not isinstance(v, (dict, list)):
                node[k] = value
                changed += 1
            else:
                changed += set_key_everywhere(v, key, value)
    elif isinstance(node, list):
        for item in node:
            changed += set_key_everywhere(item, key, value)
    return changed


def write_temp_usage(traffic_gb, traffic_key):
    """기존 사용량 파일을 읽어 트래픽 값만 바꾼 임시 파일을 만든다."""
    try:
        import yaml
    except ImportError:
        st.error("PyYAML이 필요합니다.  pip install pyyaml")
        st.stop()

    if not BASE_USAGE.exists():
        st.error(f"사용량 파일이 없습니다: {BASE_USAGE}")
        st.stop()

    data = yaml.safe_load(BASE_USAGE.read_text(encoding="utf-8")) or {}
    changed = set_key_everywhere(data, traffic_key, traffic_gb)

    if changed == 0:
        # 키가 없으면 aws_lb 기본값으로 새로 넣는다
        data.setdefault("resource_type_default_usage", {}) \
            .setdefault("aws_lb", {})[traffic_key] = traffic_gb

    TMP_USAGE.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
                         encoding="utf-8")
    return changed


def write_temp_config(instance_type=None):
    """임시 사용량 파일과 변수값을 담은 설정 파일을 만든다.

    주의: infracost의 --config-file 은 --terraform-var / --usage-file 플래그와
    함께 쓸 수 없다("Cannot be used with path, terraform* or usage-file flags").
    그래서 변수도 명령행이 아니라 설정 파일의 terraform_vars 로 넘긴다.
    """
    try:
        import yaml
    except ImportError:
        st.error("PyYAML이 필요합니다.  pip install pyyaml")
        st.stop()

    cfg = yaml.safe_load(BASE_CONFIG.read_text(encoding="utf-8")) or {}
    for proj in cfg.get("projects", []):
        proj["usage_file"] = TMP_USAGE.name
        if instance_type:
            proj.setdefault("terraform_vars", {})["instance_type"] = instance_type

    TMP_CONFIG.write_text(yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False),
                          encoding="utf-8")


# ---------------------------------------------------------------------
#  Infracost 실행
# ---------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def run_infracost(traffic_gb, instance_type, traffic_key):
    """Infracost를 돌려 JSON 경로를 돌려준다. 같은 입력이면 캐시를 쓴다."""
    if shutil.which("infracost") is None:
        raise RuntimeError(
            "infracost 명령을 찾을 수 없습니다.\n"
            "설치 후 `infracost auth login` 까지 마친 뒤 다시 실행하세요."
        )

    write_temp_usage(traffic_gb, traffic_key)
    write_temp_config(instance_type)

    cmd = [
        "infracost", "breakdown",
        "--config-file", str(TMP_CONFIG.name),
        "--format", "json",
        "--out-file", str(TMP_RESULT.name),
    ]

    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")

    if proc.returncode != 0 or not TMP_RESULT.exists():
        message = (proc.stderr or proc.stdout or "").strip()
        if "API_KEY" in message.upper():
            raise RuntimeError(
                "Infracost API 키가 설정되지 않았습니다.\n\n"
                "터미널에서 아래를 먼저 실행하세요.\n"
                "    infracost auth login\n\n"
                "무료이며 이메일 가입만 하면 됩니다. AWS 계정은 필요하지 않습니다."
            )
        raise RuntimeError(f"infracost 실행 실패 (코드 {proc.returncode})\n\n{message[:2000]}")

    return str(TMP_RESULT), None


# ---------------------------------------------------------------------
#  화면
# ---------------------------------------------------------------------

st.set_page_config(page_title="Cost Compass", page_icon="🧭", layout="wide")

st.title("🧭 Cost Compass")
st.caption("크레딧이 걱정되는 학생을 위한 인프라 설계 비용 비교 도구 · "
           "디자인적 사고 (SWCON103)")

st.info(
    "**클라우드에 아무것도 배포하지 않습니다.** 코드만 읽어서 비용을 추정하므로 "
    "크레딧이 차감되지 않습니다.",
    icon="🔒",
)

with st.sidebar:
    st.header("가정 바꿔 보기")

    traffic = st.slider(
        "월 데이터 전송량 (GB)",
        min_value=0, max_value=2000, value=100, step=50,
        help="설계안 세 개에 똑같이 적용됩니다. 비교의 공정성을 위한 공통 가정입니다.",
    )

    instance = st.selectbox(
        "인스턴스 타입",
        ["t3.small", "t3.medium", "t3.large", "t3.xlarge"],
        index=0,
        help="서론에서 다룬 '겁이 나서 작은 사양만 고르는 문제'를 직접 확인해 보세요.",
    )

    st.divider()
    traffic_key = st.text_input(
        "트래픽 키 이름", value=DEFAULT_TRAFFIC_KEY,
        help="--sync-usage-file 로 만든 사용량 파일에서 키 이름이 다르면 여기서 바꾸세요.",
    )

    run = st.button("비용 계산", type="primary", use_container_width=True)
    st.caption("계산에 몇 초 걸립니다. 같은 조건은 캐시에서 바로 나옵니다.")

    st.divider()
    use_cached = st.checkbox(
        "저장된 result.json 보기",
        value=False,
        help="infracost 설치 전에도 미리 저장해 둔 결과로 화면을 확인할 수 있습니다.",
    )


# --- 데이터 확보 -------------------------------------------------------
json_path = None
warning = None

if use_cached:
    if CACHED_RESULT.exists():
        json_path = str(CACHED_RESULT)
        st.warning("저장된 result.json을 보고 있습니다. 사이드바 가정값은 반영되지 않습니다.")
    else:
        st.error(f"{CACHED_RESULT.name} 이 없습니다. 먼저 infracost를 한 번 실행하세요.")
        st.stop()
elif run or "last_json" in st.session_state:
    if run:
        try:
            with st.spinner("Infracost로 세 설계안의 비용을 계산하는 중..."):
                json_path, warning = run_infracost(traffic, instance, traffic_key)
            st.session_state["last_json"] = json_path
            st.session_state["last_warning"] = warning
        except RuntimeError as exc:
            st.error(str(exc))
            st.stop()
    else:
        json_path = st.session_state["last_json"]
        warning = st.session_state.get("last_warning")
else:
    st.markdown(
        "왼쪽에서 가정을 정하고 **비용 계산**을 누르세요.\n\n"
        "- 월 데이터 전송량을 바꾸면 로드 밸런서 비용이 달라집니다.\n"
        "- 인스턴스 타입을 올리면 설계안 전체의 비용이 함께 올라갑니다."
    )
    st.stop()

if warning:
    st.warning(warning)


# --- 표시 --------------------------------------------------------------
df, totals, currency = load_breakdown(json_path)
summary, baseline = summary_table(df, totals)

st.subheader("설계안별 월 예상 비용")

cols = st.columns(len(totals))
cheapest = min(totals, key=totals.get)
base_total = totals[baseline]

for col, (name, total) in zip(cols, totals.items()):
    if name == baseline:
        delta = None
    else:
        pct = (total - base_total) / base_total * 100 if base_total else 0
        delta = f"{total - base_total:+,.2f} ({pct:+.0f}%)"
    with col:
        st.metric(
            label=f"{name}{'  ✅ 최저' if name == cheapest else ''}",
            value=f"{total:,.2f} {currency}",
            delta=delta,
            delta_color="inverse",   # 비용은 적을수록 좋으므로 색을 뒤집는다
        )

st.plotly_chart(total_comparison_bar(totals, currency, baseline),
                use_container_width=True)

st.subheader("무엇이 차이를 만드는가")
st.plotly_chart(stacked_resource_bar(df, totals, currency),
                use_container_width=True)

left, right = st.columns([1, 1])

with left:
    st.subheader("비교표 (보고서 표 5-3)")
    st.dataframe(summary, use_container_width=True, hide_index=True)
    st.caption("이 표를 그대로 보고서 [표 5-3]에 옮기면 됩니다.")

with right:
    st.subheader("비용 기여도 상위")
    st.dataframe(contribution_table(df, totals), use_container_width=True, hide_index=True)

unpriced = unpriced_resources(df)
if len(unpriced):
    with st.expander(f"⚠️ 가격이 산출되지 않은 리소스 {len(unpriced)}건 — 보고서 5.4 재료"):
        st.dataframe(unpriced, use_container_width=True, hide_index=True)
        st.caption(
            "Infracost가 지원하지 않거나, 무료이거나, 사용량 가정이 없어서일 수 있습니다. "
            "왜 그런지 확인해서 한계점에 쓰세요."
        )

with st.expander("이 화면이 보고서와 어떻게 연결되는가"):
    st.markdown(
        """
- **슬라이더로 트래픽만 바꾸고 설계 코드는 건드리지 않는 것** → 4.3 **공간 분리**
  (`.tf`는 고정, `infracost-usage.yml`은 변수)
- **설계안 3종이 미리 코드로 준비되어 있는 것** → 4.3 **시간 분리**
  (구체화를 비교 시점보다 앞으로 옮김)
- **총액과 리소스별 구성을 함께 보여 주는 것** → 4.3 **전체와 부분 분리**
- **배포 없이 계산되는 것** → 2.2.2 (1) Infracost가 클라우드 자격 증명을 요구하지 않음
        """
    )
