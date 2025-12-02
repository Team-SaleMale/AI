"""
AI 가격 추천 로직
- IQR 방식 이상치 제거
- 카테고리별 시작가 계산
"""

import numpy as np
from typing import List, Optional, Tuple
from models.enums import CategoryEnum
import logging

logger = logging.getLogger(__name__)


class PriceAI:
    """가격 추천 AI"""

    # 카테고리별 시작가 비율
    CATEGORY_RATIOS = {
        CategoryEnum.DIGITAL: 0.92,  # 디지털 기기 - 시세 안정적
        CategoryEnum.CLOTHES: 0.85,  # 의류 - 주관적 가치, 빠른 판매
        CategoryEnum.HOME_APPLIANCE: 0.90,  # 가전 - 실용성 위주
        CategoryEnum.BEAUTY: 0.85,  # 화장품 - 빠른 판매
        CategoryEnum.SPORTS: 0.88,  # 스포츠 용품
        CategoryEnum.DIGITAL: 0.92,  # 디지털
    }

    DEFAULT_RATIO = 0.90  # 기본 비율

    def remove_outliers_iqr(self, prices: List[int]) -> Tuple[List[int], dict]:
        """
        IQR 방식으로 이상치 제거

        Args:
            prices: 가격 리스트

        Returns:
            (필터링된 가격 리스트, 통계 정보)
        """
        if len(prices) < 3:
            # 샘플이 너무 적으면 그대로 반환
            logger.warning(f"샘플 수 부족 ({len(prices)}개), 이상치 제거 스킵")
            return prices, self._calculate_stats(prices)

        prices_array = np.array(prices)

        # Q1, Q3 계산
        q1 = np.percentile(prices_array, 25)
        q3 = np.percentile(prices_array, 75)
        iqr = q3 - q1

        # 유효 범위 계산
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr

        # 필터링
        filtered_prices = [p for p in prices if lower_bound <= p <= upper_bound]

        logger.info(
            f"IQR 이상치 제거: {len(prices)}개 -> {len(filtered_prices)}개 "
            f"(범위: {int(lower_bound):,}원 ~ {int(upper_bound):,}원)"
        )

        stats = self._calculate_stats(filtered_prices)
        stats.update({
            "q1": int(q1),
            "q3": int(q3),
            "iqr": int(iqr),
            "lower_bound": int(lower_bound),
            "upper_bound": int(upper_bound),
            "removed_count": len(prices) - len(filtered_prices)
        })

        return filtered_prices, stats

    def _calculate_stats(self, prices: List[int]) -> dict:
        """
        가격 통계 계산

        Args:
            prices: 가격 리스트

        Returns:
            통계 정보 딕셔너리
        """
        if not prices:
            return {
                "avg_price": None,
                "min_price": None,
                "max_price": None,
                "sample_count": 0
            }

        return {
            "avg_price": int(np.mean(prices)),
            "min_price": int(np.min(prices)),
            "max_price": int(np.max(prices)),
            "sample_count": len(prices)
        }

    def calculate_start_price(
        self,
        avg_price: int,
        category: Optional[CategoryEnum] = None
    ) -> int:
        """
        추천 시작가 계산

        Args:
            avg_price: 평균 시세
            category: 카테고리 (선택)

        Returns:
            추천 시작가 (천원 단위 반올림)
        """
        # 카테고리별 비율 적용
        ratio = self.CATEGORY_RATIOS.get(category, self.DEFAULT_RATIO)

        # 시작가 계산
        start_price = avg_price * ratio

        # 천원 단위 반올림
        start_price_rounded = round(start_price / 1000) * 1000

        logger.info(
            f"가격 계산: {avg_price:,}원 × {ratio} = {int(start_price):,}원 "
            f"-> {start_price_rounded:,}원 (카테고리: {category})"
        )

        return int(start_price_rounded)

    def process_prices(
        self,
        joongna_prices: List[int],
        daangn_prices: List[int],
        category: Optional[CategoryEnum] = None
    ) -> dict:
        """
        가격 데이터 처리 및 추천가 계산

        Args:
            joongna_prices: 중고나라 가격들
            daangn_prices: 당근마켓 가격들
            category: 카테고리 (선택)

        Returns:
            {
                "joongna_stats": {...},
                "daangn_stats": {...},
                "combined_stats": {...},
                "suggested_start_price": 720000,
                "category_ratio": 0.92
            }
        """
        result = {}

        # 중고나라 처리
        if joongna_prices:
            filtered_joongna, joongna_stats = self.remove_outliers_iqr(joongna_prices)
            result["joongna_stats"] = joongna_stats
        else:
            result["joongna_stats"] = self._calculate_stats([])

        # 당근마켓 처리
        if daangn_prices:
            filtered_daangn, daangn_stats = self.remove_outliers_iqr(daangn_prices)
            result["daangn_stats"] = daangn_stats
        else:
            result["daangn_stats"] = self._calculate_stats([])

        # 전체 통합 평균 계산
        all_filtered_prices = []
        if joongna_prices:
            all_filtered_prices.extend(filtered_joongna)
        if daangn_prices:
            all_filtered_prices.extend(filtered_daangn)

        if all_filtered_prices:
            _, combined_stats = self.remove_outliers_iqr(all_filtered_prices)
            result["combined_stats"] = combined_stats

            # 추천 시작가 계산
            avg_price = combined_stats["avg_price"]
            suggested_price = self.calculate_start_price(avg_price, category)

            result["suggested_start_price"] = suggested_price
            result["category_ratio"] = self.CATEGORY_RATIOS.get(category, self.DEFAULT_RATIO)
        else:
            result["combined_stats"] = self._calculate_stats([])
            result["suggested_start_price"] = None
            result["category_ratio"] = None

        return result


def format_price_message(stats: dict, keyword: str) -> str:
    """
    가격 추천 메시지 포맷팅 (크롤링 + 낙찰 데이터 통합)

    Args:
        stats: 통계 정보
        keyword: 검색 키워드

    Returns:
        메시지 문자열
    """
    if not stats.get("suggested_start_price"):
        return "시세 데이터를 찾을 수 없습니다"

    avg_price = stats["combined_stats"]["avg_price"]
    sample_count = stats["combined_stats"]["sample_count"]

    # 데이터 소스 정보
    data_source = stats.get("data_source", {})
    crawl_count = data_source.get("crawl_count", 0)
    auction_count = data_source.get("auction_count", 0)

    # 메시지 구성
    sources = []
    if crawl_count > 0:
        sources.append(f"중고나라 {crawl_count}개")
    if auction_count > 0:
        sources.append(f"실제 낙찰 {auction_count}개")

    source_info = " + ".join(sources) if sources else f"{sample_count}개"

    return f"평균 시세 {avg_price:,}원 기반 ({source_info} 분석)"
