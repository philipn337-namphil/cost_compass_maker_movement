# 설계안 비용 비교 — 실행 방법

디자인적 사고 (SWCON103) 중간 레포트 5장 "결과 도출" 실습용.

## 구성

```
infracost-demo/
├── infracost.yml           ② 설계안 3종을 한 번에 비교하는 설정
├── infracost-usage.yml     ② 공통 사용량 가정 (세 안에 동일 적용)
├── design-a/main.tf        ① A안 · EC2 1대 (DB 포함)
├── design-b/main.tf        ① B안 · ALB + ASG(2대), DB는 인스턴스 내
├── design-c/main.tf        ① C안 · ALB + ASG(2대) + RDS 분리
│
├── analyze.py              ③ JSON → 비교표 (보고서 표 5-3)
├── charts.py               ④ 비교표 → 차트 (보고서 그림 5-1)
├── app.py                  ⑤ Streamlit 화면 (슬라이더)
└── requirements.txt
```

번호는 보고서 [표 2-1]의 오픈소스 번호와 같다.
① OpenTofu · ② Infracost · ③ pandas · ④ Plotly · ⑤ Streamlit

세 템플릿은 **리전·AMI·인스턴스 타입·볼륨 크기를 모두 같은 기본값**으로 맞춰 두었다.
달라지는 것은 구성(로드 밸런서 유무, 인스턴스 대수, DB 분리 여부)뿐이다.

> **이 템플릿은 `apply` 하지 않는다.** 비용 추정 전용이다.
> provider 블록에 `skip_credentials_validation` 등을 넣어 두어
> **AWS 자격 증명 없이 파싱만으로** 비용이 계산된다.
> VPC·서브넷 ID는 조회하지 않도록 더미 값을 변수 기본값으로 넣었다.

---

## 0단계 · 설치와 API 키

설치는 winget으로 끝냈다. (`winget install --id Infracost.Infracost`)
설치된 버전은 **v0.10.47** 이며, 최신은 v2.18.3 이다. 아래 명령은 0.10.47 기준으로 확인하였다.

```bash
infracost --version
```

남은 것은 **무료 API 키 발급 하나**다. 이메일 가입만 하면 되고, **AWS 계정은 필요 없다.**

```bash
infracost auth login
```

> 브라우저가 열리고 로그인하면 `C:\Users\<사용자>\.config\infracost\credentials.yml` 에 키가 저장된다.
> 이 키는 가격 조회용이며, 클라우드 자격 증명과는 무관하다. (보고서 2.5 참조)

> 가격 조회는 `pricing.api.infracost.io`로 나간다.
> 클라우드 자격 증명과 Terraform 플랜 JSON은 전송되지 않는다. (보고서 2.3 참조)

## 1단계 · 사용량 파일을 올바른 키로 생성 ★먼저 할 것

`infracost-usage.yml`에 들어 있는 것은 **손으로 적은 초안**이라 키 이름이 실제와 다를 수 있다.
리소스에 맞는 정확한 키로 다시 만든다.

```bash
infracost breakdown --path design-c --sync-usage-file --usage-file infracost-usage.yml
```

C안이 세 설계안의 리소스를 모두 포함하므로 C안 기준으로 생성하면 된다.
생성된 파일을 열어 **값만** 본인의 가정으로 바꾼다.

> 이 옵션 이름이 다르면 `infracost breakdown --help`로 확인한다.

## 2단계 · 세 설계안 한 번에 비교

```bash
infracost breakdown --config-file infracost.yml
```

터미널에 세 설계안의 월 예상 비용이 함께 출력된다. 이 화면을 캡처하면 **[그림 5-1]** 로 쓸 수 있다.

## 3단계 · JSON으로 저장 (보고서 표 5-3용)

```bash
infracost breakdown --config-file infracost.yml --format json --out-file result.json
```

설계안별 총액과 리소스별 내역이 들어 있다. 표 5-3의 "비용 1위 리소스"와 "1위 비중"은 여기서 뽑는다.

개별로 뽑고 싶으면:

```bash
infracost breakdown --path design-a --usage-file infracost-usage.yml --format json --out-file a.json
infracost breakdown --path design-b --usage-file infracost-usage.yml --format json --out-file b.json
infracost breakdown --path design-c --usage-file infracost-usage.yml --format json --out-file c.json
```

## 4단계 · A안 대비 증감 (표 5-3의 "A안 대비 증감")

```bash
infracost diff --path design-b --compare-to a.json --usage-file infracost-usage.yml
```

`diff`는 원래 코드 변경 전후를 비교하는 기능이지만, 여기서는 **설계안 사이의 차이**를 보는 데 쓴다.
보고서 4.1 SCAMPER의 **A(응용) — "코드 리뷰의 diff 개념을 설계안 비교에 적용"** 이 실제로 구현되는 지점이다.

> `--compare-to` 옵션 이름이 버전에 따라 다를 수 있으니 `infracost diff --help`로 확인한다.

## 5단계 · 비교표 만들기 (③ pandas)

```bash
pip install -r requirements.txt
python analyze.py result.json
```

보고서 **[표 5-3]** 형태의 마크다운 표가 그대로 출력된다. 복사해서 붙이면 된다.

같이 나오는 것:

- **비용 기여도 상위 5개** — 5.3 해석에 쓴다
- **가격이 산출되지 않은 리소스** — 5.4 한계점에 쓴다
- **합계 검증** — 리소스 합계가 Infracost 총액과 맞는지 확인한다

> 마지막 검증이 중요하다. 설계안 총액은 Infracost가 준 값이라 항상 정확하지만,
> "1위 비중"과 누적 막대그래프는 리소스 단위 합산에 기대고 있다.
> 여기서 **[경고]** 가 뜨면 비율 숫자를 그대로 쓰지 말고 `--inspect`로 구조를 확인한다.

파일로 저장하려면:

```bash
python analyze.py result.json --out report     # report.md, report.csv
```

JSON 구조가 예상과 다르면:

```bash
python analyze.py result.json --inspect
```

## 6단계 · 차트 만들기 (④ Plotly)

```bash
python charts.py result.json
```

`chart_total.html`과 `chart_stacked.html`이 만들어진다. 브라우저로 열어 캡처하면 **[그림 5-1]** 로 쓸 수 있다.

PNG로 바로 저장하려면 `pip install kaleido` 후:

```bash
python charts.py result.json --png
```

## 7단계 · 화면 띄우기 (⑤ Streamlit)

```bash
streamlit run app.py
```

사이드바에서 **월 데이터 전송량**과 **인스턴스 타입**을 바꾸고 `비용 계산`을 누르면,
세 설계안의 비용과 순위가 다시 계산된다.

- 같은 조건은 캐시에서 바로 나온다
- `infracost`가 아직 없으면 사이드바의 **저장된 result.json 보기**를 켜서 화면만 먼저 확인할 수 있다
- 사용량 파일의 트래픽 키 이름이 다르면 사이드바에서 바꿀 수 있다

> ⑤가 보고서에서 하는 역할은 2.4에 적어 두었다.
> 이 프로젝트가 다루는 것은 **불안**이고, 불안은 고정된 표 하나로 풀리지 않는다.
> 슬라이더를 직접 움직여 순위가 뒤집히는 지점을 볼 때 비용이 판단의 근거가 된다.
> 화면 캡처를 **[그림 4-1]** 로 쓰면 된다.

---

## 더 해 볼 것

**(1) 트래픽을 바꿔 가며 비교 (4.2 후보 2 · 손익분기)**

`infracost-usage.yml`의 `processed_bytes_gb`를 10 → 100 → 1000으로 바꿔 가며 2단계를 반복하면,
트래픽에 따라 설계안 간 순위가 바뀌는 지점을 찾을 수 있다.

**(2) DB 이중화 비용 (C안)**

```bash
infracost breakdown --path design-c --usage-file infracost-usage.yml \
  --terraform-var db_multi_az=true
```

`db_multi_az`를 켰을 때 얼마가 늘어나는지가 곧 "DB 가용성의 가격"이다.

**(3) 인스턴스 사양을 올려 보기 — 서론과 직접 연결되는 실험**

서론에서 "크레딧이 얼마나 깎일지 몰라 겁이 나서 가장 작은 사양만 골랐다"고 썼다.
`t3.small` → `t3.large`로 올렸을 때 월 얼마가 늘어나는지를 **배포하지 않고 확인하는 것**이
이 프로젝트가 해결하려던 문제 그 자체다. 보고서 **[표 5-4]** 에 들어간다.

> ⚠️ `--config-file` 은 `--terraform-var` 와 **같이 쓸 수 없다.**
> (도움말: "Cannot be used with path, terraform\* or usage-file flags")
> 그래서 변수는 **설정 파일 안에** 넣는다.

`infracost-large.yml` 을 만든다.

```yaml
version: 0.1
projects:
  - path: design-a
    name: A안_최소구성
    usage_file: infracost-usage.yml
    terraform_vars:
      instance_type: t3.large
  - path: design-b
    name: B안_가용성구성
    usage_file: infracost-usage.yml
    terraform_vars:
      instance_type: t3.large
  - path: design-c
    name: C안_관리형구성
    usage_file: infracost-usage.yml
    terraform_vars:
      instance_type: t3.large
```

```bash
infracost breakdown --config-file infracost-large.yml --format json --out-file result-large.json
python analyze.py result-large.json
```

설계안별로 하나씩 볼 때는 `--config-file` 없이 쓰면 `--terraform-var` 를 바로 쓸 수 있다.

```bash
infracost breakdown --path design-b --usage-file infracost-usage.yml --terraform-var instance_type=t3.large
```

---

## 막혔을 때

| 증상 | 확인할 것 |
|---|---|
| 비용이 0으로 나오는 리소스가 있음 | 해당 리소스가 Infracost 지원 목록에 있는지, 리전·인스턴스 타입 철자가 맞는지 |
| ALB 비용이 기본요금만 나옴 | 사용량 파일의 LCU 관련 키가 올바른지 (1단계로 재생성) |
| `usage_file` 경로 오류 | `infracost.yml`의 경로는 설정 파일 위치 기준이다. 안 되면 각 프로젝트에서 `--usage-file`로 직접 지정 |
| AWS 자격 증명을 요구함 | `data` 블록을 추가하지 않았는지 확인 (더미 변수를 쓴 이유가 이것이다) |
| ASG 비용이 1대분만 나옴 | `desired_capacity`가 2로 잡혀 있는지 확인 |

**여기서 겪은 오류와 해결 과정은 보고서 5.4 "어려웠던 점"에 그대로 쓰면 된다.**
강의자료 슬라이드 11에 "오류와 해결 과정도 좋은 보고서 재료"라고 명시되어 있다.
