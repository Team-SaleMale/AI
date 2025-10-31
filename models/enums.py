from enum import Enum

class CategoryEnum(str, Enum):
    """상품 카테고리 (17개)"""
    HOME_APPLIANCE = "HOME_APPLIANCE"    # 생활가전
    HEALTH_FOOD = "HEALTH_FOOD"          # 건강기능식품
    BEAUTY = "BEAUTY"                    # 뷰티_미용
    FOOD_PROCESSED = "FOOD_PROCESSED"    # 가공식품
    PET = "PET"                          # 반려동물
    DIGITAL = "DIGITAL"                  # 디지털기기
    LIVING_KITCHEN = "LIVING_KITCHEN"    # 생활_주방
    WOMEN_ACC = "WOMEN_ACC"              # 여성잡화
    SPORTS = "SPORTS"                    # 스포츠_레저
    PLANT = "PLANT"                      # 식물
    GAME_HOBBY = "GAME_HOBBY"            # 게임_취미_음반
    TICKET = "TICKET"                    # 티켓
    FURNITURE = "FURNITURE"              # 가구_인테리어
    BOOK = "BOOK"                        # 도서
    KIDS = "KIDS"                        # 유아동
    CLOTHES = "CLOTHES"                  # 의류
    ETC = "ETC"                          # 기타물품

class ItemStatusEnum(str, Enum):
    """상품 상태"""
    BIDDING = "BIDDING"  # 입찰중
    SUCCESS = "SUCCESS"  # 낙찰 완료
    FAIL = "FAIL"        # 유찰

class RangeSettingEnum(str, Enum):
    """거리 설정"""
    VERY_NEAR = "VERY_NEAR"  # 2km
    NEAR = "NEAR"            # 5km
    MEDIUM = "MEDIUM"        # 20km
    FAR = "FAR"              # 50km
    ALL = "ALL"              # 전국