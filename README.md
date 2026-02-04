# 팀 및 팀원 소개

## 팀 소개
- YBIGTA 뉴비 팀 프로젝트 과제를 수행하는 3인 팀입니다.
- GitHub 기반으로 협업합니다.

## 팀원 소개

### 임예찬 (팀장)
- 첨단컴퓨팅학부 25학번(06년생)
- MBTI : INTP
- 안녕하세요! DE팀입니다~ 음악 좋아하구 특히 10CM 좋아합니다!

### 전영찬
- 응용통계학과 22학번(03년생)
- MBTI : ISTP
- 음악 들으면서 사진찍기 / 운동(헬스, 배드민턴, 탁구..)에 관심이 있습니다
### 문형서
- 산업공학과 22학번(03년생)
- 안녕하세요! DS team에 있고, 열심히 참여하도록 하겠습니다!

## GitHub 협업 과제 증빙 이미지

브랜치 보호 규칙 적용, main 푸시 거부, PR 리뷰/머지 과정을 아래 이미지로 첨부합니다.

### 1) Branch protection rule 적용

![Branch protection rule](github/branch_protection.png)

### 2) main 브랜치 push 거부

![Push rejected on main](github/push_rejected.png)

### 3) Pull Request + Review + Merge 확인

![Review and merged](github/review_and_merged.png)

---

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

**1) 별점 분포**
- **현상**: 알라딘은 5점 만점 체계이며, 교보문고와 마찬가지로 고득점 비중이 높습니다.
![Aladin Sc](review_analysis/plots/aladin_rating_hist.png)

**2) 리뷰 길이 특성**
- **현상**: 리뷰 길이가 전반적으로 짧고 균일합니다. 다만 간혹 긴 내용이 존재합니다.
![Aladin text len](review_analysis/plots/aladin_textlen_hist.png)

**3) 시계열 추이**
- **현상**: 2015년과 2025년에 리뷰 수가 상대적으로 크게 증가하는 구간(스파이크)이 관측됩니다.
![Aladin Trend](review_analysis/plots/aladin_monthly_count.png)


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
- **현상** : 2024년 이전까지는 낮은 빈도를 유지하다가 최근(2024년 하반기 이후) 급격한 스파이크(Spike)가 관측됩니다. 2016년에도 한번의 spike가 관측됩니다.
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

## 3.1 키워드 비교 (한글 토큰 빈도, 정규화)
- 방법: 각 사이트 리뷰 텍스트에서 한글 토큰(2글자 이상)을 추출한 뒤, 사이트별 전체 토큰 수 차이를 보정하기 위해 10,000 토큰당 빈도로 정규화하여 비교함.
- 목적: 리뷰 수/리뷰 길이(표본 크기) 차이가 커도, **사이트 내에서 상대적으로 자주 등장하는 표현**을 공정하게 비교하기 위함.

![Korean Token Frequency (normalized)](review_analysis/plots/compare_korean_tokenfreq_normalized.png)

- **관찰**
  - 공통적으로 “너무/정말/감사합니다/좋은/책입니다” 같은 **일반 감상 표현**이 상위권에 등장함.
  - 같은 상위 토큰이라도 사이트별 막대 높이가 다른데, 이는 **리뷰 문화(짧은 감상 vs 비교적 긴 서술)** 및 **작성자 성향** 차이로 해석 가능함.
- **해석(주의 포함)**
  - 상위 토큰이 “감사합니다/좋은/책입니다”처럼 **정형 문구** 위주라면, 사이트의 ‘콘텐츠 주제’보다는 **리뷰 작성 관행**이 강하게 반영된 결과일 수 있음.
  - 보다 “주제성 키워드”를 보고 싶다면, (선택) 조사/감탄사 제거, 불용어(stopwords) 추가, 형태소 기반 명사 추출을 적용하면 개선 여지가 있음.

---

## 3.2 시계열 비교 1: 월별 리뷰 수 추이 (라인 겹치기)
- 방법: 각 사이트 리뷰를 월 단위로 집계(resample)하여 **월별 리뷰 개수**를 라인 그래프로 비교함.

![Monthly Review Count by Site](review_analysis/plots/compare_monthly_review_count.png)

- **관찰**
  - 2024~2025 구간에서 특정 사이트(그래프상 kyobo)가 리뷰 수가 급격히 증가하는 구간이 보임.
  - aladin/yes24는 기간 전반에 걸쳐 낮은 수준이 유지되다가, 특정 시점에 스파이크(급증)가 나타남.
- **해석**
  - 리뷰 수 급증은 보통 (1) 크롤링 대상 페이지/상품의 인기 변화, (2) 해당 기간에 이벤트/프로모션, (3) 수집 범위(페이지네이션/더보기) 차이, (4) 크롤러가 특정 구간만 성공적으로 수집한 경우 등으로 발생함.
  - 따라서 “사이트 특성”으로 단정하기 전에, 각 사이트별 수집 성공 구간(날짜 커버리지)과 총 수집량을 함께 확인하는 것이 안전함.

---

## 3.3 시계열 비교 2: 월별 평균 별점 추이 (라인 겹치기)
- 방법: 월별로 별점 평균을 계산하여 사이트별로 비교함.

![Monthly Mean Rating by Site](review_analysis/plots/compare_monthly_mean_rating.png)

- **관찰**
  - aladin/yes24는 대부분 구간에서 평균이 **약 4~5 근처**로 유지됨.
  - kyobo는 2025년 근처에서 평균이 **9~10 수준**으로 표시되는 구간이 존재함.
- **해석(중요: 스케일 점검 필요)**
  - aladin/yes24가 5점 만점이라면, kyobo의 9~10은 동일 스케일로 보기 어렵고 **별점 스케일(10점제) 혼입 또는 파싱 오류** 가능성이 큼.
  - 결론을 내기 전에 아래를 점검해야 함:
    1) kyobo 원본 CSV의 rating 값 범위(min/max)  
    2) 10점제라면 5점제로 환산(예: `rating_5 = rating_10 / 2`) 후 비교  
    3) 혹은 별점이 아닌 다른 숫자를 rating으로 읽은 경우(셀렉터/텍스트 파싱 오류) 수정
  - 스케일을 통일한 뒤 다시 그리면 “사이트별 별점 성향” 비교가 의미 있어짐.

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

## 4.4 웹 과제 실행 (FastAPI)
```bash
# 서버 실행 (실행 후 http://localhost:8000/docs에서 기능 테스트 가능)
uvicorn app.main:app --reload
```

---

# 5. Docker & AWS 배포

## 5.1 Docker Hub 이미지

> **Docker Hub 주소**: `https://hub.docker.com/r/<DOCKER_USERNAME>/ybigta-newbie-project`
>
> (팀원 B가 Docker Hub에 Push 후 위 주소를 실제 값으로 업데이트해주세요)

### 로컬에서 Docker 이미지 빌드 및 실행

```bash
# 이미지 빌드
docker build -t ybigta-newbie-project .

# 컨테이너 실행 (환경변수 파일 사용)
docker run -d \
  --name ybigta-app \
  -p 8000:8000 \
  --env-file .env \
  ybigta-newbie-project

# 또는 환경변수 직접 지정
docker run -d \
  --name ybigta-app \
  -p 8000:8000 \
  -e MYSQL_USER=<user> \
  -e MYSQL_PASSWORD=<password> \
  -e MYSQL_HOST=<host> \
  -e MYSQL_PORT=3306 \
  -e MYSQL_DATABASE=<database> \
  -e MONGO_URL=<mongo_url> \
  -e MONGO_DB_NAME=ybigta \
  ybigta-newbie-project
```

---

## 5.2 CI/CD 파이프라인 (GitHub Actions)

`main` 브랜치에 push하면 자동으로 다음 작업이 실행됩니다:

1. **Job 1: Build & Push** - Docker 이미지를 빌드하고 Docker Hub에 Push
2. **Job 2: Deploy to EC2** - EC2 서버에 SSH 접속 후 최신 이미지로 컨테이너 재배포

### GitHub Repository Secrets 설정 (필수)

GitHub Repository → Settings → Secrets and variables → Actions에서 아래 Secrets를 등록해야 합니다:

| Secret Name | 설명 | 예시 |
|-------------|------|------|
| `DOCKER_USERNAME` | Docker Hub 사용자명 | `myusername` |
| `DOCKER_PASSWORD` | Docker Hub 비밀번호 또는 Access Token | `dckr_pat_xxxxx` |
| `EC2_HOST` | EC2 인스턴스 퍼블릭 IP | `3.35.xxx.xxx` |
| `EC2_USER` | EC2 접속 사용자 | `ec2-user` (Amazon Linux) 또는 `ubuntu` |
| `EC2_SSH_KEY` | EC2 .pem 키 내용 (전체 복사) | `-----BEGIN RSA PRIVATE KEY-----...` |
| `MYSQL_USER` | RDS MySQL 사용자명 | `admin` |
| `MYSQL_PASSWORD` | RDS MySQL 비밀번호 | `yourpassword` |
| `MYSQL_HOST` | RDS Endpoint | `mydb.xxxxx.ap-northeast-2.rds.amazonaws.com` |
| `MYSQL_PORT` | MySQL 포트 | `3306` |
| `MYSQL_DATABASE` | 데이터베이스 이름 | `ybigta` |
| `MONGO_URL` | MongoDB Atlas 연결 문자열 | `mongodb+srv://user:pass@cluster.xxxxx.mongodb.net/` |
| `MONGO_DB_NAME` | MongoDB 데이터베이스 이름 | `ybigta` |

---

## 5.3 EC2 보안 그룹 설정

EC2 인스턴스의 보안 그룹에서 다음 인바운드 규칙이 필요합니다:

| 유형 | 포트 | 소스 | 용도 |
|------|------|------|------|
| SSH | 22 | 내 IP 또는 0.0.0.0/0 | SSH 접속 |
| Custom TCP | 8000 | 0.0.0.0/0 | FastAPI 서버 |

---

# 6. API 실행 결과 (배포 완료 후)

> 아래 캡처는 EC2에 배포 완료 후 Swagger (`http://<EC2_IP>:8000/docs`)에서 API를 테스트한 결과입니다.
> IP 주소가 보이도록 캡처해주세요.

## 6.1 User API

### POST /api/user/register (회원가입)
![User Register](screenshots/api_user_register.png)

### POST /api/user/login (로그인)
![User Login](screenshots/api_user_login.png)

### PUT /api/user/update-password (비밀번호 변경)
![User Update Password](screenshots/api_update_password.png)

### DELETE /api/user/delete (회원 탈퇴)
![User Delete](screenshots/api_user_delete.png)

## 6.2 Review API

### POST /review/preprocess/{site_name} (리뷰 전처리)
![Review Preprocess](screenshots/api_review_preprocess.png)

---

# 7. GitHub Actions 실행 결과

> CI/CD 파이프라인이 성공적으로 실행된 화면을 캡처합니다.

## 7.1 GitHub Actions 성공 화면
![GitHub Actions Success](screenshots/github_actions_success.png)

## 7.2 Build & Push Job 상세
![Build Job](screenshots/github_actions_build.png)

## 7.3 Deploy to EC2 Job 상세
![Deploy Job](screenshots/github_actions_deploy.png)
