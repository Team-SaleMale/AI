from pydantic import BaseModel
from typing import List, Optional
from models.enums import CategoryEnum, ItemStatusEnum
from datetime import datetime

class RecommendationRequest(BaseModel):
    """추천 요청 모델"""
    user_id: int
    
class ItemRecommendation(BaseModel):
    """추천 상품 정보"""
    item_id: int
    name: str
    title: str
    category: CategoryEnum
    current_price: int
    end_time: datetime
    item_status: ItemStatusEnum
    region_name: Optional[str] = None  # "강남구" 형태
    view_count: int
    bid_count: int
    recommendation_score: Optional[float] = None  # 추천 점수 (내부 계산용)
    
class RecommendationResponse(BaseModel):
    """추천 응답 모델"""
    recommended_items: List[ItemRecommendation]
    
class HealthCheckResponse(BaseModel):
    """헬스체크 응답"""
    status: str
    message: str