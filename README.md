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

> **Docker Hub 주소**: https://hub.docker.com/r/0chan1/ybigta-newbie-project

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

---

# 8. 프로젝트 회고

## 8.1 프로젝트를 진행하며 깨달은 점

### CI/CD 파이프라인의 중요성
수동으로 서버에 접속해서 코드를 배포하는 것은 번거롭고 실수가 발생하기 쉽습니다. GitHub Actions를 활용한 CI/CD 파이프라인을 구축하면서, 코드를 push하는 것만으로 자동으로 빌드-테스트-배포가 이루어지는 것이 얼마나 효율적인지 체감했습니다. 특히 팀 프로젝트에서는 누가 언제 배포했는지 기록이 남고, 문제가 생기면 이전 버전으로 쉽게 롤백할 수 있다는 점이 큰 장점이었습니다.

### Docker 컨테이너화의 장점
"내 컴퓨터에서는 되는데..."라는 문제를 Docker로 해결할 수 있었습니다. 로컬 개발 환경과 EC2 배포 환경이 달라서 발생할 수 있는 문제들을 Docker 이미지로 동일한 환경을 보장함으로써 예방할 수 있었습니다. 또한 `.dockerignore`를 통해 불필요한 파일(예: `.env`, `.pem`)이 이미지에 포함되지 않도록 관리하는 것이 보안상 중요하다는 것을 배웠습니다.

### 환경변수와 Secrets 관리
민감한 정보(DB 비밀번호, API 키 등)를 코드에 직접 작성하면 보안 문제가 발생합니다. GitHub Secrets를 활용하여 민감 정보를 안전하게 관리하고, 런타임에 환경변수로 주입하는 방식을 배웠습니다. `.env` 파일은 `.gitignore`에 추가하여 절대 Git에 커밋되지 않도록 주의해야 합니다.

---

## 8.2 마주친 오류와 해결 경험

### 오류 1: GitHub Actions에서 EC2 SSH 접속 실패

**증상**
```
ssh: connect to host x.x.x.x port 22: Connection timed out
```

**원인**
EC2 보안 그룹에서 SSH(22번 포트) 인바운드 규칙이 설정되지 않았거나, 특정 IP에서만 접속 가능하도록 제한되어 있었습니다.

**해결**
EC2 보안 그룹의 인바운드 규칙에 SSH(22번 포트)를 `0.0.0.0/0` 또는 GitHub Actions IP 대역에서 접속 가능하도록 설정했습니다.

---

### 오류 2: Docker 컨테이너 내에서 DB 연결 실패

**증상**
```
RuntimeError: MySQL env missing: MYSQL_HOST, MYSQL_PASSWORD ...
```

**원인**
Docker 컨테이너 실행 시 환경변수를 전달하지 않아서, 컨테이너 내부에서 `.env` 파일을 찾을 수 없었습니다.

**해결**
`docker run` 명령어에 `-e` 옵션으로 환경변수를 명시적으로 전달했습니다:
```bash
docker run -d \
  -e MYSQL_USER=${{ secrets.MYSQL_USER }} \
  -e MYSQL_PASSWORD=${{ secrets.MYSQL_PASSWORD }} \
  ...
```

---

### 오류 3: "User already Exists" 응답

**증상**
회원가입 API 호출 시 400 에러와 함께 `"User already Exists."` 메시지 반환

**원인**
이미 동일한 이메일로 가입된 사용자가 존재했습니다. 이는 오류가 아니라 **정상적인 비즈니스 로직**입니다.

**해결**
다른 이메일로 테스트하거나, 기존 사용자를 삭제 후 재시도했습니다. API가 정상 동작하고 있음을 확인했습니다.

---

## 8.3 관련 개념 정리

### GitHub Actions란?
GitHub에서 제공하는 CI/CD 플랫폼입니다. `.github/workflows/` 디렉토리에 YAML 파일로 워크플로우를 정의하면, 특정 이벤트(push, PR 등) 발생 시 자동으로 작업이 실행됩니다.

**주요 구성 요소:**
- **Workflow**: 자동화된 프로세스 전체 (`.yaml` 파일)
- **Job**: 워크플로우 내의 작업 단위 (예: build, deploy)
- **Step**: Job 내의 개별 명령어
- **Runner**: 워크플로우가 실행되는 서버 (GitHub 호스팅 또는 Self-hosted)

### Docker란?
애플리케이션을 컨테이너라는 격리된 환경에서 실행할 수 있게 해주는 플랫폼입니다.

**핵심 개념:**
- **Image**: 컨테이너 실행에 필요한 파일 시스템과 설정을 담은 템플릿
- **Container**: 이미지를 기반으로 실행된 인스턴스
- **Dockerfile**: 이미지를 빌드하기 위한 명령어 모음
- **Docker Hub**: Docker 이미지 저장소 (GitHub과 비슷한 역할)

### CI/CD란?
- **CI (Continuous Integration)**: 코드 변경 시 자동으로 빌드 및 테스트 수행
- **CD (Continuous Deployment/Delivery)**: 테스트 통과 후 자동으로 배포

**장점:**
- 빠른 피드백 (코드 문제 조기 발견)
- 일관된 배포 프로세스
- 수동 작업 최소화로 인한 휴먼 에러 감소

---

# 9. RAG + Agent 챗봇

## 9.1 개요

도서 리뷰 데이터를 활용한 **RAG(Retrieval-Augmented Generation) + Agent** 기반 챗봇입니다.
사용자 질문을 LLM이 자동 분류(라우팅)하여, 질문 유형에 따라 적절한 처리 파이프라인으로 분기합니다.

- **프레임워크**: LangGraph (StateGraph 기반 워크플로우)
- **LLM**: Upstage Solar Mini Chat
- **Embedding**: Upstage Solar Embedding Large
- **Vector Store**: FAISS (로컬 인덱스)
- **UI**: Streamlit

---

## 9.2 아키텍처

```
사용자 입력
    │
    ▼
┌──────────┐
│  Router  │  ← LLM이 입력을 3가지 유형으로 분류
└──────────┘
    │
    ├─ "chat"          → [Chat Node]          → 일반 대화 응답
    │
    ├─ "subject_info"  → [Subject Info Node]  → 도서 메타정보 조회
    │                          │                  (subjects.json)
    │                          ▼
    │                    [Chat Node]           → 초안 정리 후 최종 응답
    │
    └─ "rag_review"    → [RAG Review Node]    → FAISS 검색 → 리뷰 컨텍스트 생성
                               │                  → LLM이 컨텍스트 기반 답변 생성
                               ▼
                         [Chat Node]           → 초안 정리 후 최종 응답
```

### 라우팅 분류 기준

| 라벨 | 설명 | 예시 질문 |
|------|------|-----------|
| `chat` | 일반 대화, 인사, 잡담 | "안녕하세요", "오늘 날씨 어때?" |
| `subject_info` | 도서/상품의 기본 정보 요청 | "소년이 온다 정보 알려줘" |
| `rag_review` | 리뷰 기반 의견, 요약, 장단점 질문 | "이 책 리뷰 요약해줘", "평점은 어때?" |

---

## 9.3 주요 컴포넌트

### Router (`st_app/graph/router.py`)
- LLM에게 사용자 입력을 전달하여 `chat` / `subject_info` / `rag_review` 중 하나로 분류
- 분류가 불확실한 경우 기본값 `chat`으로 fallback

### RAG Review Node (`st_app/graph/nodes/rag_review_node.py`)
- FAISS 벡터스토어에서 사용자 질문과 유사한 리뷰 4건을 검색 (similarity search)
- 검색된 리뷰를 컨텍스트로 구성하여 LLM에게 전달
- LLM이 **컨텍스트에 근거한 답변만** 생성 (hallucination 방지)

### Subject Info Node (`st_app/graph/nodes/subject_info_node.py`)
- `st_app/db/subject_information/subjects.json`에 등록된 도서 메타정보를 조회
- LLM이 사용자 입력과 가장 관련 있는 도서를 매칭하여 제목/저자/요약/키워드를 반환

### Chat Node (`st_app/graph/nodes/chat_node.py`)
- **일반 대화**: 대화 히스토리를 포함하여 자연스러운 응답 생성
- **Finalizer 역할**: `subject_info` 또는 `rag_review`에서 생성한 초안(`draft_response`)을 간결하고 자연스럽게 정리

### RAG Retriever (`st_app/rag/retriever.py`)
- `database/preprocessed_reviews_*.csv`에서 리뷰 데이터를 로드
- Upstage Solar Embedding으로 벡터화 후 FAISS 인덱스 생성 및 저장
- 이미 빌드된 인덱스가 있으면 재사용하여 효율적으로 동작

---

## 9.4 상태 관리 (GraphState)

LangGraph의 각 노드가 공유하는 상태 객체입니다.

| 필드 | 타입 | 설명 |
|------|------|------|
| `user_input` | `str` | 사용자 입력 텍스트 |
| `messages` | `List[BaseMessage]` | 대화 히스토리 (Human/AI 메시지) |
| `route` | `Optional[str]` | Router가 결정한 분기 라벨 |
| `subject_key` | `Optional[str]` | 매칭된 도서 키 |
| `draft_response` | `Optional[str]` | 중간 단계 답변 초안 |
| `response` | `Optional[str]` | 최종 응답 |
| `retrieved_docs` | `Optional[list]` | RAG 검색 결과 문서 리스트 |

---

## 9.5 실행 방법

### 환경변수 설정

Upstage API 키가 필요합니다.

```bash
# 환경변수로 설정
export UPSTAGE_API_KEY="your-api-key-here"
```

또는 Streamlit secrets 사용:
```toml
# .streamlit/secrets.toml
UPSTAGE_API_KEY = "your-api-key-here"
```

### FAISS 인덱스 빌드 (최초 1회)

```bash
python -m st_app.rag.embedder
```

> 이미 `st_app/db/faiss_index/`에 인덱스 파일이 존재하면 자동으로 재사용되므로 생략 가능합니다.

### Streamlit 앱 실행

```bash
streamlit run streamlit_app.py
```

실행 후 `http://localhost:8501`에서 챗봇을 사용할 수 있습니다.

---

## 9.6 실행 결과 스크린샷

### 일반 대화 (chat 경로)
![Chat Example](screenshots/rag_chat.png)

### 리뷰 기반 RAG 질의 (rag_review 경로)
![RAG Review Example](screenshots/rag_review_query.png)

### 도서 정보 조회 (subject_info 경로)
![Subject Info Example](screenshots/rag_subject_info.png)

---

## 9.7 프로젝트 디렉토리 구조 (RAG/Agent 관련)

```
st_app/
├── __init__.py
├── db/
│   ├── faiss_index/          # FAISS 벡터 인덱스
│   │   ├── index.faiss
│   │   ├── index.pkl
│   │   └── meta.json
│   └── subject_information/  # 도서 메타정보
│       └── subjects.json
├── graph/
│   ├── __init__.py
│   ├── build_graph.py        # LangGraph 워크플로우 빌드
│   ├── router.py             # LLM 기반 라우터
│   └── nodes/
│       ├── __init__.py
│       ├── chat_node.py      # 일반 대화 + Finalizer
│       ├── rag_review_node.py  # RAG 리뷰 검색 + 답변
│       └── subject_info_node.py  # 도서 정보 조회
├── rag/
│   ├── __init__.py
│   ├── embedder.py           # FAISS 인덱스 빌드 CLI
│   ├── llm.py                # Upstage LLM/Embedding 초기화
│   ├── prompt.py             # RAG 프롬프트 템플릿
│   └── retriever.py          # FAISS 검색 + 인덱스 관리
└── utils/
    ├── __init__.py
    └── state.py              # GraphState 정의
```
