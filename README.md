# ValueBid AI Server

경매 플랫폼을 위한 AI 추천 서버 (FastAPI)

## 기능
- AI 기반 적정가 제안
- 개인화된 경매 추천 (협업 필터링)

## 🏗️ 아키텍처

```
┌─────────────────┐         ┌─────────────────┐
│  Spring Boot    │────────▶│   FastAPI AI    │
│   (Port 8080)   │  HTTP   │   (Port 8000)   │
└─────────────────┘         └─────────────────┘
         │                           │
         └───────────┬─────────────────┘
                     │
              ┌──────▼──────┐
              │  RDS (PostgreSQL) │
              └───────────────────┘
```

## 🚀 로컬 실행 방법

### 방법 1: Docker Compose (권장)

```bash
# 1. 환경변수 파일 생성
cp env.ai.example .env

# 2. .env 파일 수정 (DB 정보 등 입력)
# DB_USER, DB_PASSWORD, DB_HOST, DB_NAME 등 설정

# 3. Docker Compose로 실행
docker compose up -d

# 4. 로그 확인
docker compose logs -f ai-server
```

### 방법 2: Python 가상환경 (개발용)

```bash
# Windows PowerShell
python -m venv venv
.\venv\Scripts\Activate.ps1

# 패키지 설치
pip install -r requirements.txt

# 환경변수 설정 (.env 파일 또는 환경변수)
# DB_USER, DB_PASSWORD, DB_HOST, DB_NAME 등

# 서버 실행
uvicorn main:app --reload
```

## 📦 Docker Compose 구조

이 레포지토리의 `docker-compose.yml`은 FastAPI 추천 서버(`ai-server`) 컨테이너 하나로 구성됩니다.

### Spring Boot와 통합

Spring Boot 서버와 통신하기 위해 **외부 네트워크** (`salemale-network`)를 사용합니다.

**BE 레포의 docker-compose.yml에 다음 추가 필요:**

```yaml
networks:
  default:
    name: salemale-network
    driver: bridge
```

그리고 Spring Boot의 `RECOMMENDATION_API_URL` 환경변수를:
```
RECOMMENDATION_API_URL=http://ai-server:8000
```

로 설정하면 내부 Docker 네트워크를 통해 통신합니다.

## 🔧 환경변수

`.env` 파일 또는 환경변수로 설정:

| 변수명 | 설명 | 기본값 |
|--------|------|--------|
| `UVICORN_WORKERS` | Uvicorn 워커 수 | `2` |
| `UVICORN_HOST` | 바인딩 호스트 | `0.0.0.0` |
| `UVICORN_PORT` | 서버 포트 | `8000` |
| `DB_USER` | PostgreSQL 사용자명 | (필수) |
| `DB_PASSWORD` | PostgreSQL 비밀번호 | (필수) |
| `DB_HOST` | RDS 엔드포인트 | (필수) |
| `DB_PORT` | PostgreSQL 포트 | `5432` |
| `DB_NAME` | 데이터베이스 이름 | (필수) |
| `DOCKERHUB_USERNAME` | Docker Hub 사용자명 | (필수) |
| `HF_SPACE_ID` | Hugging Face Space ID | `yisol/IDM-VTON` |
| `HF_API_TOKEN` | Hugging Face API 토큰 (Private Space 시) | (선택) |
| `HF_REQUEST_TIMEOUT` | Hugging Face 호출 타임아웃(초) | `600` |

## 📡 API 엔드포인트

### 헬스체크
```
GET http://localhost:8000/
```

### 경매 추천
```
POST http://localhost:8000/recommend-auctions
Content-Type: application/json

{
  "user_id": 123
}
```

### API 문서
서버 실행 후 http://localhost:8000/docs 접속

### 가상 피팅 (Virtual Try-On)
```
POST http://localhost:8000/virtual-tryon
Content-Type: multipart/form-data

background: <사용자 이미지 파일>
garment: <의상 이미지 파일>
garment_desc: "블루 셔츠"
crop: false
denoise_steps: 30
seed: 42
```
응답:
```
{
  "result_url": "data:image/png;base64,iVBORw0KGgoAAA...",
  "masked_url": "data:image/png;base64,iVBORw0KGgoAAA..."
}
```
결과는 `data:` URL 형태로 반환되므로, 브라우저나 클라이언트에서 그대로 보여 주거나 필요 시 파일로 저장하면 됩니다.

## 🚢 배포 (GitHub Actions CD)

### 필요한 GitHub Secrets

**CI (Docker 이미지 빌드/푸시):**
- `DOCKER_USERNAME`: Docker Hub 사용자명
- `DOCKER_PASSWORD`: Docker Hub 비밀번호

**CD (EC2 배포):**
- `EC2_HOST`: EC2 인스턴스 IP/도메인
- `EC2_USERNAME`: EC2 SSH 사용자명 (보통 `ubuntu`)
- `EC2_SSH_KEY`: EC2 SSH 개인키 (PEM 형식)
- `DB_USER`: RDS 사용자명
- `DB_PASSWORD`: RDS 비밀번호
- `DB_HOST`: RDS 엔드포인트
- `DB_PORT`: RDS 포트 (기본: `5432`)
- `DB_NAME`: 데이터베이스 이름
- `DOCKER_USERNAME`: Docker Hub 사용자명
- `HF_API_TOKEN`: Hugging Face Space 토큰 (필요시)

### 배포 흐름

1. **main 브랜치에 push** → CI 자동 실행
   - Docker 이미지 빌드
   - Docker Hub에 푸시 (`salemale-ai:latest`, `salemale-ai:sha`)

2. **CI 완료 후 CD 자동 실행**
   - EC2에 SSH 접속
   - 최신 코드 pull
   - `.env` 파일 생성 (Secrets에서 주입)
   - `docker compose up -d` 실행
   - 헬스체크 확인

### 수동 배포

GitHub Actions에서 "Run workflow" 버튼으로 수동 실행 가능

## 🔗 Spring Boot 연동

Spring Boot에서 FastAPI를 호출할 때:

```java
// application.yml 또는 환경변수
recommendation:
  api:
    url: http://ai-server:8000  # Docker 네트워크 내부 주소

// RestTemplate 사용 예시
String aiUrl = "http://ai-server:8000/recommend-auctions";
ResponseEntity<RecommendationResponse> response = restTemplate.postForEntity(
    aiUrl, 
    new RecommendationRequest(userId), 
    RecommendationResponse.class
);
```

**⚠️ 중요:** `localhost`가 아닌 **서비스 이름** (`ai-server`)을 사용해야 합니다.

### 가상 피팅 API 사용 예시

```java
public TryOnResponse callTryOn(MultipartFile human, MultipartFile garment, String desc) {
    MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
    body.add("background", new MultipartInputStreamFileResource(human.getInputStream(), human.getOriginalFilename()));
    body.add("garment", new MultipartInputStreamFileResource(garment.getInputStream(), garment.getOriginalFilename()));
    body.add("garment_desc", desc);
    body.add("crop", false);
    body.add("denoise_steps", 30);
    body.add("seed", 42);

    HttpHeaders headers = new HttpHeaders();
    headers.setContentType(MediaType.MULTIPART_FORM_DATA);

    HttpEntity<MultiValueMap<String, Object>> request = new HttpEntity<>(body, headers);
    ResponseEntity<TryOnResponse> response = restTemplate.postForEntity(
        "http://ai-server:8000/virtual-tryon",
        request,
        TryOnResponse.class
    );
    return response.getBody();
}
```

`MultipartInputStreamFileResource`는 Spring 공식 예제처럼 MultipartFile을 RestTemplate에 전달하기 위한 헬퍼 클래스입니다.

## 🛠️ 개발 가이드

### 프로젝트 구조
```
AI/
├── main.py                 # FastAPI 앱 진입점
├── models/
│   ├── api_models.py      # API 요청/응답 모델
│   ├── db_models.py       # SQLAlchemy ORM 모델
│   └── enums.py           # 열거형
├── utils/
│   ├── database.py        # DB 연결 설정
│   └── recommender.py     # 추천 알고리즘
├── docker-compose.yml      # 통합 배포 설정
├── Dockerfile             # Docker 이미지 빌드
└── requirements.txt        # Python 의존성
```