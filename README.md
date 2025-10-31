# ValueBid AI Server

경매 플랫폼을 위한 AI 추천 서버 (FastAPI)

## 기능
- AI 기반 적정가 제안
- 개인화된 경매 추천

## 실행 방법 (Windows)
```powershell
# 가상환경 생성 및 활성화
python -m venv {가상환경명}
.\{가상환경명}\Scripts\Activate.ps1

# 패키지 설치
pip install -r requirements.txt

# 서버 실행
uvicorn main:app --reload
```

## API 문서
서버 실행 후 http://localhost:8000/docs 접속