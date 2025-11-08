import time
from collections import Counter, defaultdict
from typing import List, Dict, Set
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy.orm import Session
from models.db_models import UserDB, ItemDB, ItemTransactionDB, UserLikedDB
from models.api_models import ItemRecommendation
from models.enums import ItemStatusEnum

class AuctionRecommender:
    """
    경매 상품 추천 엔진
    
    알고리즘: User-Based Collaborative Filtering
    - 사용자의 입찰 내역 + 위시리스트를 기반으로 프로필 생성
    - 카테고리 빈도를 Feature로 사용
    - 코사인 유사도로 유사 사용자 탐색
    - 유사 사용자가 관심 있는 상품 추천
    """
    
    def __init__(self, db: Session):
        print("AuctionRecommender 초기화 시작...")
        start_time = time.time()
        
        self.db = db
        
        # 데이터 로드
        print("데이터 로드 중...")
        self._load_data()
        
        # 피처 매트릭스 생성
        print("피처 매트릭스 생성 중...")
        self._create_feature_matrix()
        
        # 유사도 행렬 계산
        print("유사도 행렬 계산 중...")
        self._calculate_similarity()
        
        elapsed = time.time() - start_time
        print(f"AuctionRecommender 초기화 완료. 소요 시간: {elapsed:.2f}초")
    
    def _load_data(self):
        """DB에서 필요한 데이터 로드"""
        load_start = time.time()
        
        # 모든 사용자 조회
        users = self.db.query(UserDB).all()
        
        # 모든 상품을 딕셔너리로 저장 (빠른 조회를 위해)
        items = {item.item_id: item for item in self.db.query(ItemDB).all()}
        
        # 모든 입찰 내역 조회
        transactions = self.db.query(ItemTransactionDB).all()
        
        # 모든 위시리스트 조회
        liked_items = self.db.query(UserLikedDB).filter(UserLikedDB.liked == True).all()
        
        # 사용자별 입찰한 상품 ID 매핑
        self.user_bid_items: Dict[int, Set[int]] = defaultdict(set)
        for trans in transactions:
            self.user_bid_items[trans.buyer_id].add(trans.item_id)
        
        # 사용자별 찜한 상품 ID 매핑
        self.user_liked_items: Dict[int, Set[int]] = defaultdict(set)
        for liked in liked_items:
            self.user_liked_items[liked.user_id].add(liked.item_id)
        
        # 사용자 프로필 생성: 카테고리 빈도수 Counter
        self.user_profiles: Dict[int, Counter] = {}
        
        for user in users:
            profile = Counter()
            
            # 입찰한 상품의 카테고리 수집
            bid_item_ids = self.user_bid_items.get(user.id, set())
            for item_id in bid_item_ids:
                item = items.get(item_id)
                if item and item.category:
                    profile[item.category.value] += 1
            
            # 찜한 상품의 카테고리 수집
            liked_item_ids = self.user_liked_items.get(user.id, set())
            for item_id in liked_item_ids:
                item = items.get(item_id)
                if item and item.category:
                    profile[item.category.value] += 1
            
            self.user_profiles[user.id] = profile
        
        self.all_items = items
        
        load_time = time.time() - load_start
        print(f"데이터 로드 완료. Users: {len(users)}, Items: {len(items)}, "
              f"Transactions: {len(transactions)}, Liked: {len(liked_items)}. "
              f"소요 시간: {load_time:.2f}초")
    
    def _create_feature_matrix(self):
        """사용자별 카테고리 빈도 벡터를 행렬로 변환"""
        # 모든 카테고리를 수집하여 열(column) 정의
        all_categories = set()
        for profile in self.user_profiles.values():
            all_categories.update(profile.keys())
        
        # 카테고리를 정렬하여 일관된 순서 보장
        self.feature_columns = {category: idx for idx, category in enumerate(sorted(all_categories))}
        
        # 사용자별 벡터 생성
        feature_matrix = []
        user_ids = []
        
        for user_id, profile in self.user_profiles.items():
            # 벡터 초기화 (모든 카테고리에 대해 0)
            vec = [0] * len(self.feature_columns)
            
            # 해당 사용자의 카테고리 빈도 채우기
            for category, count in profile.items():
                idx = self.feature_columns.get(category)
                if idx is not None:
                    vec[idx] = count
            
            feature_matrix.append(vec)
            user_ids.append(user_id)
        
        # NumPy 배열로 변환
        self.feature_matrix = np.array(feature_matrix)
        self.user_id_list = user_ids
        
        print(f"피처 매트릭스 생성 완료. Shape: {self.feature_matrix.shape}")
    
    def _calculate_similarity(self):
        """코사인 유사도 행렬 계산"""
        # 피처가 없는 경우 (데이터가 없거나 카테고리가 없는 경우) 처리
        if self.feature_matrix.shape[1] == 0:
            print("경고: 피처가 없어 유사도 행렬을 생성할 수 없습니다. 빈 행렬로 초기화합니다.")
            # 빈 유사도 행렬 생성 (사용자 수 x 사용자 수)
            n_users = len(self.user_id_list)
            self.similarity_matrix = np.zeros((n_users, n_users))
            # 사용자 ID → 행렬 인덱스 매핑
            self.user_idx_map = {uid: idx for idx, uid in enumerate(self.user_id_list)}
            print(f"빈 유사도 행렬 생성 완료. Shape: {self.similarity_matrix.shape}")
            return
        
        # sklearn의 cosine_similarity 사용
        self.similarity_matrix = cosine_similarity(self.feature_matrix)
        
        # 사용자 ID → 행렬 인덱스 매핑
        self.user_idx_map = {uid: idx for idx, uid in enumerate(self.user_id_list)}
        
        print(f"유사도 행렬 계산 완료. Shape: {self.similarity_matrix.shape}")
    
    def get_similar_users(self, target_user_id: int, n_users: int = 5) -> List[int]:
        """
        대상 사용자와 유사한 상위 N명의 사용자 ID 반환
        
        Args:
            target_user_id: 대상 사용자 ID
            n_users: 반환할 유사 사용자 수 (기본값: 5)
        
        Returns:
            유사도가 높은 순서로 정렬된 사용자 ID 리스트
        """
        if target_user_id not in self.user_idx_map:
            return []
        
        # 대상 사용자의 행렬 인덱스
        idx = self.user_idx_map[target_user_id]
        
        # 유사도 점수 가져오기
        sim_scores = self.similarity_matrix[idx]
        
        # 자기 자신 제외하기 위한 마스크
        user_id_list_np = np.array(self.user_id_list)
        is_not_target = user_id_list_np != target_user_id
        
        # 유사도 점수 정렬 (내림차순)
        # 자기 자신의 유사도는 0으로 만들어 제외
        sorted_indices = np.argsort(sim_scores * is_not_target)[::-1]
        
        # 상위 N명 반환
        similar_user_ids = [user_id_list_np[i] for i in sorted_indices[:n_users]]
        
        return similar_user_ids
    
    def recommend_items(
        self, 
        target_user_id: int, 
        n_recommendations: int = 10
    ) -> List[ItemRecommendation]:
        """
        대상 사용자에게 경매 상품 추천
        
        Args:
            target_user_id: 추천 대상 사용자 ID
            n_recommendations: 추천할 상품 개수 (기본값: 10)
        
        Returns:
            추천 상품 리스트 (ItemRecommendation 객체)
        """
        from datetime import datetime
        
        print(f"사용자 {target_user_id}에 대한 추천 생성 시작...")
        
        # 1. 유사 사용자 찾기
        similar_users = self.get_similar_users(target_user_id, n_users=5)
        
        # Cold Start 대응: 유사 사용자가 없으면 인기 상품 추천
        if not similar_users:
            print(f"사용자 {target_user_id}의 유사 사용자를 찾을 수 없습니다. 인기 상품으로 대체합니다.")
            return self._get_popular_items(target_user_id, n_recommendations)
        
        print(f"유사 사용자 {len(similar_users)}명 발견: {similar_users}")
        
        # 2. 유사 사용자들이 입찰/찜한 상품 수집
        candidate_items = []
        for uid in similar_users:
            # 입찰한 상품
            candidate_items.extend(self.user_bid_items.get(uid, []))
            # 찜한 상품
            candidate_items.extend(self.user_liked_items.get(uid, []))
        
        # 3. 대상 사용자가 이미 접한 상품 제외
        user_interacted = self.user_bid_items.get(target_user_id, set()) | \
                         self.user_liked_items.get(target_user_id, set())
        
        # 4. 빈도수 계산 (많이 추천될수록 높은 점수)
        candidate_counts = Counter(candidate_items)
        
        # 이미 접한 상품 제거
        for item_id in user_interacted:
            candidate_counts.pop(item_id, None)
        
        # 5. 상위 N개 추출
        recommended_item_ids = [item_id for item_id, _ in candidate_counts.most_common(n_recommendations * 2)]
        
        # Cold Start 대응: 후보 아이템이 없으면 인기 상품 추천
        if not recommended_item_ids:
            print("협업 필터링 후보가 없습니다. 인기 상품으로 대체합니다.")
            return self._get_popular_items(target_user_id, n_recommendations)
        
        # 6. DB에서 상품 상세 정보 조회
        # 수정: 현재 시간 기준으로 실제 입찰 가능한 상품만 필터링
        now = datetime.utcnow()
        items = self.db.query(ItemDB).filter(
            ItemDB.item_id.in_(recommended_item_ids),
            ItemDB.item_status == ItemStatusEnum.BIDDING,
            ItemDB.end_time > now  # 추가: 경매 종료 시간 체크
        ).all()
        
        # 7. ItemRecommendation 객체로 변환
        recommended_items = []
        for item in items[:n_recommendations]:
            recommendation = ItemRecommendation(
                item_id=item.item_id,
                name=item.name,
                title=item.title,
                category=item.category,
                current_price=item.current_price,
                end_time=item.end_time,
                item_status=item.item_status,
                region_name=item.region.sigungu,
                view_count=item.view_count,
                bid_count=item.bid_count,
                recommendation_score=candidate_counts.get(item.item_id, 0)
            )
            recommended_items.append(recommendation)
        
        # Cold Start 대응: 결과가 부족하면 인기 상품으로 채우기
        if len(recommended_items) < n_recommendations:
            print(f"추천 결과가 부족합니다 ({len(recommended_items)}/{n_recommendations}). 인기 상품으로 보완합니다.")
            popular_items = self._get_popular_items(target_user_id, n_recommendations - len(recommended_items))
            
            # 중복 제거
            existing_ids = {item.item_id for item in recommended_items}
            for item in popular_items:
                if item.item_id not in existing_ids:
                    recommended_items.append(item)
                    if len(recommended_items) >= n_recommendations:
                        break
        
        print(f"추천 생성 완료. 추천 상품 수: {len(recommended_items)}")
        return recommended_items
    
    def _get_popular_items(self, target_user_id: int, n_items: int) -> List[ItemRecommendation]:
        """
        인기 상품 추천 (Cold Start 대응)
        - 최근 3일 내 생성
        - 입찰 수 많은 순
        - 사용자가 이미 접한 상품 제외
        
        Args:
            target_user_id: 대상 사용자 ID
            n_items: 추천할 상품 개수
        
        Returns:
            인기 상품 리스트
        """
        from datetime import datetime, timedelta
        
        # 사용자가 이미 접한 상품 제외
        user_interacted = self.user_bid_items.get(target_user_id, set()) | \
                         self.user_liked_items.get(target_user_id, set())
        
        # 최근 3일 내 생성된 입찰 가능한 인기 상품 조회
        three_days_ago = datetime.utcnow() - timedelta(days=3)
        now = datetime.utcnow()
        
        # 사용자가 접한 상품이 있을 때만 필터링
        if user_interacted:
            items = self.db.query(ItemDB).filter(
                ItemDB.item_status == ItemStatusEnum.BIDDING,
                ItemDB.end_time > now,
                ItemDB.created_at > three_days_ago,
                ~ItemDB.item_id.in_(user_interacted)
            ).order_by(
                ItemDB.bid_count.desc(),
                ItemDB.view_count.desc()
            ).limit(n_items * 2).all()
        else:
            items = self.db.query(ItemDB).filter(
                ItemDB.item_status == ItemStatusEnum.BIDDING,
                ItemDB.end_time > now,
                ItemDB.created_at > three_days_ago
            ).order_by(
                ItemDB.bid_count.desc(),
                ItemDB.view_count.desc()
            ).limit(n_items * 2).all()
        
        # ItemRecommendation 객체로 변환
        popular_items = []
        for item in items[:n_items]:
            recommendation = ItemRecommendation(
                item_id=item.item_id,
                name=item.name,
                title=item.title,
                category=item.category,
                current_price=item.current_price,
                end_time=item.end_time,
                item_status=item.item_status,
                region_name=item.region.sigungu,
                view_count=item.view_count,
                bid_count=item.bid_count,
                recommendation_score=0  # 인기 상품은 점수 0
            )
            popular_items.append(recommendation)
        
        return popular_items