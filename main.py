from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager
import time

from models.api_models import (
    RecommendationRequest,
    RecommendationResponse,
    HealthCheckResponse
)
from models.db_models import UserDB
from utils.database import get_db, SessionLocal
from utils.recommender import AuctionRecommender

# 전역 추천 인스턴스
recommender_instance: AuctionRecommender = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    서버 시작 시 실행되는 초기화 함수
    - 데이터 로드
    - 피처 매트릭스 생성
    - 유사도 행렬 계산
    """
    global recommender_instance

    print("서버 시작 중: AuctionRecommender 초기화...")
    
    db_session = SessionLocal()
    try:
        recommender_instance = AuctionRecommender(db_session)
    finally:
        db_session.close()
    
    print("서버가 요청을 처리할 준비가 되었습니다!")
    
    yield  # 서버 실행
    
    print("서버 종료 중...")

# FastAPI 애플리케이션 생성
app = FastAPI(
    title="Auction Recommendation API",
    description="경매 상품 추천 API - 협업 필터링 기반",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 설정 (Spring Boot에서 호출 가능하도록)
origins = [
    "http://localhost:8080",  # Spring Boot 로컬
    "http://localhost:3000",  # React 로컬
    # 프로덕션 도메인 추가
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_recommender_instance() -> AuctionRecommender:
    """FastAPI 의존성 주입용 함수"""
    if recommender_instance is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Recommender not initialized"
        )
    return recommender_instance

@app.get("/", response_model=HealthCheckResponse)
def health_check():
    """헬스체크 엔드포인트"""
    return HealthCheckResponse(
        status="ok",
        message="Auction Recommendation API is running!"
    )

@app.post("/recommend-auctions", response_model=RecommendationResponse)
def get_auction_recommendations(
    request: RecommendationRequest,
    db: Session = Depends(get_db),
    recommender: AuctionRecommender = Depends(get_recommender_instance)
):
    """
    경매 상품 추천 API
    
    Args:
        request: {"user_id": 123}
        
    Returns:
        {
            "recommended_items": [
                {
                    "item_id": 456,
                    "name": "아이폰 14 Pro",
                    "category": "DIGITAL",
                    ...
                },
                ...
            ]
        }
    """
    print(f"\n{'='*60}")
    print(f"[/recommend-auctions] 요청 시작: user_id={request.user_id}")
    start_time = time.time()
    
    # 1. 사용자 존재 확인
    user_exists = db.query(UserDB.id).filter(UserDB.id == request.user_id).first()
    if not user_exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {request.user_id} not found"
        )
    
    # 2. 추천 실행
    recommended_items = recommender.recommend_items(
        target_user_id=request.user_id,
        n_recommendations=10
    )
    
    elapsed = time.time() - start_time
    print(f"[/recommend-auctions] 요청 완료. 추천 수: {len(recommended_items)}, 소요 시간: {elapsed:.4f}초")
    print(f"{'='*60}\n")
    
    # 3. 응답 반환
    return RecommendationResponse(recommended_items=recommended_items)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True  # 개발 환경에서만 True
    )