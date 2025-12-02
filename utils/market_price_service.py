"""
시세 서비스 (캐시 + 크롤링 + 실제 낙찰 데이터 통합)
- DB 캐시 조회 (24시간)
- 캐시 미스 시:
  1. 실시간 크롤링 (중고나라)
  2. 실제 낙찰 데이터 (item 테이블)
  3. 두 데이터 통합하여 더 정확한 시세 계산
- DB에 결과 저장/업데이트
"""

from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from models.db_models import MarketPriceDB, ItemDB
from models.enums import CategoryEnum, ItemStatusEnum
from utils.price_crawler_selenium import crawl_with_fallback_selenium
from utils.price_ai import PriceAI
import logging

logger = logging.getLogger(__name__)


class MarketPriceService:
    """시세 서비스"""

    def __init__(self, cache_hours: int = 24, auction_days: int = 30):
        """
        Args:
            cache_hours: 캐시 유효 시간 (기본 24시간)
            auction_days: 낙찰 데이터 조회 기간 (기본 30일)
        """
        self.cache_hours = cache_hours
        self.auction_days = auction_days
        self.price_ai = PriceAI()

    def get_auction_prices(self, db: Session, keyword: str) -> List[int]:
        """
        실제 낙찰된 상품 가격 조회 (최근 30일)

        Args:
            db: DB 세션
            keyword: 검색 키워드

        Returns:
            낙찰가 리스트
        """
        threshold = datetime.utcnow() - timedelta(days=self.auction_days)

        # item_status = COMPLETED인 낙찰 완료 상품 조회
        completed_items = db.query(ItemDB).filter(
            ItemDB.item_status == ItemStatusEnum.SUCCESS,
            ItemDB.name.ilike(f"%{keyword}%"),  # 부분 매칭
            ItemDB.created_at > threshold
        ).all()

        prices = [item.current_price for item in completed_items if item.current_price]

        logger.info(f"낙찰 데이터: '{keyword}' 키워드로 {len(prices)}개 발견 (최근 {self.auction_days}일)")
        return prices

    def get_cached_price(self, db: Session, keyword: str) -> Optional[dict]:
        """
        DB 캐시에서 시세 조회

        Args:
            db: DB 세션
            keyword: 검색 키워드

        Returns:
            캐시된 시세 정보 또는 None
        """
        cache_threshold = datetime.utcnow() - timedelta(hours=self.cache_hours)

        # 중고나라 또는 당근마켓 중 하나라도 캐시 있으면 사용
        cached_records = db.query(MarketPriceDB).filter(
            MarketPriceDB.keyword == keyword,
            MarketPriceDB.crawled_at > cache_threshold
        ).all()

        if not cached_records:
            logger.info(f"캐시 미스: {keyword}")
            return None

        # 플랫폼별로 분리
        result = {"joongna": None, "daangn": None}

        for record in cached_records:
            platform_data = {
                "avg_price": record.avg_price,
                "min_price": record.min_price,
                "max_price": record.max_price,
                "sample_count": record.sample_count,
                "crawled_at": record.crawled_at
            }

            if record.platform == "joongna":
                result["joongna"] = platform_data
            elif record.platform == "daangn":
                result["daangn"] = platform_data

        logger.info(f"캐시 히트: {keyword} (조회 시간: ~0.1초)")
        return result

    def crawl_and_save(
        self,
        db: Session,
        keyword: str,
        category: Optional[CategoryEnum] = None
    ) -> dict:
        """
        실시간 크롤링 + 실제 낙찰 데이터 통합 및 DB 저장

        Args:
            db: DB 세션
            keyword: 검색 키워드
            category: 카테고리 (선택)

        Returns:
            처리 결과 (통계 + 추천가)
        """
        logger.info(f"실시간 데이터 수집 시작: {keyword}")

        # 1. 중고나라 크롤링 실행 (키워드 축소 재시도 포함)
        crawl_results = crawl_with_fallback_selenium(keyword, min_samples=3)
        joongna_prices = crawl_results.get("joongna", [])
        final_keyword = crawl_results.get("final_keyword", keyword)

        logger.info(f"중고나라 크롤링: {len(joongna_prices)}개 가격 수집")

        # 2. 실제 낙찰 데이터 조회 (최근 30일)
        auction_prices = self.get_auction_prices(db, final_keyword)
        logger.info(f"실제 낙찰 데이터: {len(auction_prices)}개 발견")

        # 3. 두 데이터 소스 통합
        all_prices = joongna_prices + auction_prices
        total_count = len(all_prices)

        if total_count == 0:
            logger.warning(f"데이터 없음: 크롤링 {len(joongna_prices)}개 + 낙찰 {len(auction_prices)}개")
            return {
                "joongna_stats": None,
                "auction_stats": None,
                "combined_stats": None,
                "suggested_start_price": None,
                "final_keyword": final_keyword,
                "data_source": {
                    "crawl_count": len(joongna_prices),
                    "auction_count": len(auction_prices),
                    "total_count": 0
                }
            }

        logger.info(f"통합 데이터: 총 {total_count}개 (크롤링 {len(joongna_prices)}개 + 낙찰 {len(auction_prices)}개)")

        # 4. IQR 이상치 제거 및 통계 계산
        filtered_prices, combined_stats = self.price_ai.remove_outliers_iqr(all_prices)
        avg_price = combined_stats["avg_price"]

        # 5. 추천 시작가 계산
        suggested_price = self.price_ai.calculate_start_price(avg_price, category)

        # 6. 개별 데이터 소스 통계
        joongna_stats = None
        if joongna_prices:
            _, joongna_stats = self.price_ai.remove_outliers_iqr(joongna_prices)

        auction_stats = None
        if auction_prices:
            _, auction_stats = self.price_ai.remove_outliers_iqr(auction_prices)

        # 7. DB 저장 (크롤링 데이터만 캐시)
        self._save_to_db(db, final_keyword, "joongna", joongna_stats)
        db.commit()

        logger.info(f"실시간 데이터 수집 완료: {keyword} -> {final_keyword} (추천가: {suggested_price:,}원)")

        return {
            "joongna_stats": joongna_stats,
            "auction_stats": auction_stats,
            "combined_stats": combined_stats,
            "suggested_start_price": suggested_price,
            "category_ratio": self.price_ai.CATEGORY_RATIOS.get(
                category, self.price_ai.DEFAULT_RATIO
            ),
            "final_keyword": final_keyword,
            "data_source": {
                "crawl_count": len(joongna_prices),
                "auction_count": len(auction_prices),
                "total_count": total_count
            }
        }

    def _save_to_db(
        self,
        db: Session,
        keyword: str,
        platform: str,
        stats: Optional[dict]
    ):
        """
        시세 데이터를 DB에 저장 (UPSERT)

        Args:
            db: DB 세션
            keyword: 키워드
            platform: 플랫폼 (joongna, daangn)
            stats: 통계 정보
        """
        if not stats or stats.get("sample_count", 0) == 0:
            logger.warning(f"저장 스킵: {platform} - 데이터 없음")
            return

        # 기존 레코드 조회
        existing = db.query(MarketPriceDB).filter(
            MarketPriceDB.keyword == keyword,
            MarketPriceDB.platform == platform
        ).first()

        if existing:
            # 업데이트
            existing.avg_price = stats.get("avg_price")
            existing.min_price = stats.get("min_price")
            existing.max_price = stats.get("max_price")
            existing.sample_count = stats.get("sample_count")
            existing.crawled_at = datetime.utcnow()
            logger.info(f"DB 업데이트: {platform} - {keyword}")
        else:
            # 신규 생성
            new_record = MarketPriceDB(
                keyword=keyword,
                platform=platform,
                avg_price=stats.get("avg_price"),
                min_price=stats.get("min_price"),
                max_price=stats.get("max_price"),
                sample_count=stats.get("sample_count"),
                crawled_at=datetime.utcnow()
            )
            db.add(new_record)
            logger.info(f"DB 생성: {platform} - {keyword}")

    def get_or_crawl(
        self,
        db: Session,
        keyword: str,
        category: Optional[CategoryEnum] = None
    ) -> dict:
        """
        캐시 조회 또는 실시간 크롤링

        Args:
            db: DB 세션
            keyword: 검색 키워드
            category: 카테고리 (선택)

        Returns:
            처리 결과 (통계 + 추천가)
        """
        # 1. 캐시 조회
        cached = self.get_cached_price(db, keyword)

        if cached:
            # 캐시 히트 - 크롤링 캐시 + 실시간 낙찰 데이터 통합
            joongna_stats = cached.get("joongna", {})

            # 실시간 낙찰 데이터 조회 (항상 최신 데이터)
            auction_prices = self.get_auction_prices(db, keyword)

            # 통합 평균 계산
            all_prices = []

            # 캐시된 크롤링 데이터 (가중 평균)
            if joongna_stats and joongna_stats.get("avg_price"):
                count = joongna_stats.get("sample_count", 1)
                all_prices.extend([joongna_stats["avg_price"]] * count)

            # 실시간 낙찰 데이터
            all_prices.extend(auction_prices)

            if all_prices:
                _, combined_stats = self.price_ai.remove_outliers_iqr(all_prices)
                avg_price = combined_stats["avg_price"]
                suggested_price = self.price_ai.calculate_start_price(avg_price, category)

                # 낙찰 데이터 통계
                auction_stats = None
                if auction_prices:
                    _, auction_stats = self.price_ai.remove_outliers_iqr(auction_prices)

                logger.info(f"캐시 + 낙찰 데이터 통합: 크롤링 {joongna_stats.get('sample_count', 0)}개 + 낙찰 {len(auction_prices)}개")

                return {
                    "joongna_stats": joongna_stats,
                    "auction_stats": auction_stats,
                    "combined_stats": combined_stats,
                    "suggested_start_price": suggested_price,
                    "category_ratio": self.price_ai.CATEGORY_RATIOS.get(
                        category, self.price_ai.DEFAULT_RATIO
                    ),
                    "from_cache": True,
                    "final_keyword": keyword,
                    "data_source": {
                        "crawl_count": joongna_stats.get("sample_count", 0),
                        "auction_count": len(auction_prices),
                        "total_count": len(all_prices)
                    }
                }

        # 2. 캐시 미스 - 실시간 크롤링
        result = self.crawl_and_save(db, keyword, category)
        result["from_cache"] = False
        return result
