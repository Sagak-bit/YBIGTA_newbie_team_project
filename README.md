# 📊 도서 리뷰 데이터 수집 및 분석 프로젝트

본 문서는 **교보문고(Kyobo), 알라딘(Aladin), YES24** 등 주요 도서 사이트에서 수집한 리뷰 데이터를 대상으로 진행한 프로젝트입니다.
**크롤링**부터 **EDA(탐색적 데이터 분석)**, 그리고 모델링을 위한 **전처리(Preprocessing) 및 Feature Engineering** 과정을 상세히 기술합니다.

---

## 0. 프로젝트 개요
- **목표**: 각 도서 사이트의 리뷰 수집 및 특성 비교 분석
- **수집 데이터**: 평점(`rating`), 작성일(`date`), 리뷰 본문(`content`)
- **대상 사이트**: Kyobo, Aladin, YES24
- **최소 수집 목표**: 사이트별 500건 이상

---

# 1. EDA: 사이트별 시각화 & 인사이트

각 사이트별로 수집된 데이터의 분포와 이상치를 시각화하여 분석했습니다.
*(그래프 저장 경로: `review_analysis/plots/`)*

## 1.1 Kyobo (교보문고)
**1) 별점 분포 (Rating Distribution)**
- **현상**: 별점이 10점 만점에 압도적으로 쏠려 있어(Skewed), 중간 점수(5~8점)가 희소합니다.
- **해석**: 평점의 변별력이 낮으므로, 텍스트 내용 기반의 분석이 중요합니다.
![Kyobo Rating](review_analysis/plots/rating_distribution.png)

**2) 리뷰 길이 분포 (Review Length)**
- **현상**: 50자 미만의 단문이 대다수인 **Heavy-tail** 분포를 보입니다.
- **해석**: 상위 1%에 해당하는 초장문 리뷰는 스팸이거나 정성 리뷰일 수 있어 별도 확인이 필요합니다.
![Kyobo Length](review_analysis/plots/review_char_len_hist_kde.png)

**3) 시계열 추이 (Monthly Trend)**
- **현상**: 2025년 3월경 리뷰 수가 급증(Spike)한 후 하향 안정화되었습니다.
- **해석**: 출간 이벤트나 프로모션 등 특정 트리거가 있었던 것으로 추정됩니다.
![Kyobo Trend](review_analysis/plots/monthly_trend_rolling.png)

---

## 1.2 Aladin (알라딘)
> *[알라딘 크롤러 실행 결과 그래프를 바탕으로 작성해주세요]*

**1) 별점 분포**
- **현상**: [예: 알라딘은 5점 만점 체계이며, 교보문고와 마찬가지로 고득점 비중이 높습니다.]
- **해석**: [내용 채우기]
**2) 리뷰 길이 특성**
- **현상**: [예: '100자평' 위주로 수집되어 리뷰 길이가 전반적으로 짧고 균일합니다.]
- **해석**: [내용 채우기]
---

## 1.3 YES24 (예스24)

**1) 별점 및 리뷰 특성 (Rating Distribution)**
- **현상**: 5점 만점 체계이며, 교보문고와 마찬가지로 5점의 비율이 압도적으로 높습니다. 
- **해석**: 평점의 대부분이 고득점이므로 텍스트 내용 기반의 분석이 중요합니다. 
<img width="1280" height="960" alt="yes24_eda_rating_hist" src="https://github.com/user-attachments/assets/fa35c5de-7acf-49cc-a3e5-9ff7c2fe94d6" />


**2) 리뷰 길이 특성 (Review Length)**
- **현상** : 대부분의 리뷰가 단문의 리뷰로 right-skew 형태의 그래프를 보이나, 4000자, 6000자, 12000자 정도              의 outlier도 존재합니다. 
- **해석** : 초장문의 리뷰를 쓰는 정성 리뷰어들이 존재하는 것으로 보입니다. 장문 리뷰는 책의 내용을 포함하는 경우가 많으므로, 토픽 모델링이나 키워드 추출 시 핵심적인 역할을 할 것으로 보입니다. 
<img width="1280" height="960" alt="yes24_eda_textlen_hist" src="https://github.com/user-attachments/assets/cbb49b0d-b8c8-412b-ac86-84c90dc93e62" />


**3) 시계열 추이 (Monthly Trend)**
- **현상** : 2024년 이전까지는 낮은 빈도를 유지하다가 **최근(2024년 하반기 이후) 급격한 스파이크(Spike)**가 관측됩니다. 2016년에도 한번의 spike가 관측됩니다.
- **해석** : 2016년은 맨부커상, 2024~2025년은 노벨상 수상의 영향으로 리뷰 수가 증가한 것으로 보입니다.
   <img width="1280" height="960" alt="yes24_eda_monthly_count_line" src="https://github.com/user-attachments/assets/230b438c-9155-4be3-8712-387107d33448" />

---

# 2. 전처리 & Feature Engineering (FE)

수집된 Raw Data(`csv`)를 분석 가능한 형태의 Clean Data로 변환하는 공통 파이프라인입니다.

## 2.1 결측치 처리 (Missing Values)
- **Date**: 날짜 파싱 실패(`NaT`) 시 시계열 분석의 정확도를 위해 해당 행 제거 (`dropna`)
- **Rating**: 숫자 변환이 불가능한 오류 값은 제거
- **Content**: 빈 문자열(Empty string)이나 `NaN`은 텍스트 분석이 불가능하므로 제거

## 2.2 이상치 처리 (Outliers)
- **리뷰 길이 (Length Outliers)**
    - EDA 결과 모든 사이트에서 Heavy-tail 분포가 확인됨.
    - **99th Percentile(상위 1%)** 이상의 초장문 리뷰는 스팸/광고/복사글 가능성이 있어 분석 목적에 따라 **Clipping**하거나 **제거** 처리.
- **날짜 (Date Outliers)**
    - 수집 시점보다 미래의 날짜(오류)가 포함된 경우 제거.

## 2.3 텍스트 전처리 (Text Cleaning)
- **정규화(Normalization)**: 한글, 영문, 숫자, 기본 공백을 제외한 특수문자/이모티콘 제거 (`re.sub`)
- **공백 정리**: 다중 공백(`   `)을 단일 공백(` `)으로 치환
- **불용어(Stopwords) 제거**:
    - 분석에 노이즈가 되는 도메인 상투어 제거
    - 예: *"책", "구매", "배송", "포장", "진짜", "너무", "좋아요"*

## 2.4 파생변수 생성 (Feature Engineering)
- **`review_len`**: 리뷰 글자 수 (단문/장문 분류 및 필터링 기준)
- **`weekday`**: 요일 정보 (요일별 리뷰 패턴 분석용)
- **`year_month`**: 월별 트렌드 분석용 (YYYY-MM)

## 2.5 텍스트 벡터화 (Text Vectorization)
- **TF-IDF (Term Frequency - Inverse Document Frequency)**
    - 단순 빈도(Count)가 아닌, 문서 내 **상대적 중요도**를 반영하기 위해 사용.
    - **설정**: `min_df=2` (희귀 단어 제외), `max_features=1000` (상위 1,000개 단어만 추출)
    - **활용**: `tfidf_sum`(정보량 합계) 등의 파생변수를 생성하여 리뷰의 정보 밀도 측정.

---

# 3. 비교 분석: 사이트별 특성 비교
*아직 안함*

## 3.1 키워드/토픽 비교
각 사이트의 **Top 20 키워드(TF-IDF 기준)**를 비교 분석했습니다.

| 구분 | Kyobo 주요 키워드 | Aladin 주요 키워드 | YES24 주요 키워드 |
|:---:|:---:|:---:|:---:|
| **특징** | [예: 배송, 포장 등 서비스 관련] | [예: 내용, 편집 등 책 자체] | [예: 굿즈, 사은품 등] |

- **해석**:
    - **Kyobo**는 오프라인 연계나 배송/포장 상태에 대한 키워드 비중이 높았습니다.
    - **Aladin**은 '마니아' 층이 많아 책의 내용이나 편집 상태(번역 등)에 대한 구체적 언급이 많았습니다.
    - **YES24**는 특정 굿즈나 이벤트와 연관된 키워드가 상위에 등장했습니다.

## 3.2 리뷰 길이 및 패턴 비교
- **리뷰 길이**: Aladin(100자평 위주) < Kyobo < YES24(회원리뷰 활성) 순으로 평균 길이가 길게 나타났습니다.
- **별점 경향**: 3개 사이트 모두 **J-Curve(고득점 쏠림)** 현상을 보였으나, 상대적으로 [특정 사이트]가 낮은 점수 비율이 조금 더 높았습니다.

---

# 4. 실행 방법

## 4.1 환경 설정
```bash
pip install -r requirements.txt
```

## 4.2 전체 프로세스 실행 (크롤링 ~ 전처리)
```bash
# 모든 사이트 크롤링 및 전처리 일괄 실행
python -m review_analysis.crawling.main --output_dir database --all
python -m review_analysis.preprocessing.main --output_dir database --all
```

## 4.3 개별 실행 예시
```bash
# 교보문고만 크롤링
python -m review_analysis.crawling.main --output_dir database --crawler kyobo

# 교보문고 결과만 전처리
python -m review_analysis.preprocessing.main --output_dir database --preprocessor reviews_kyobo
```
