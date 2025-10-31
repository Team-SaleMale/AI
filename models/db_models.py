from sqlalchemy import Column, BigInteger, String, Integer, Text, DateTime, Boolean, ForeignKey, Enum as SQLEnum, Double
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from models.enums import CategoryEnum, ItemStatusEnum, RangeSettingEnum
from datetime import datetime

Base = declarative_base()

class UserDB(Base):
    """사용자 테이블"""
    __tablename__ = "users"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    nickname = Column(String(15), nullable=False, unique=True)
    email = Column(String(254), nullable=True)
    manner_score = Column(Integer, nullable=False, default=50)
    range_setting = Column(SQLEnum(RangeSettingEnum), nullable=False, default=RangeSettingEnum.NEAR)
    profile_image = Column(String(200), nullable=True)
    phone_number = Column(String(20), unique=True, nullable=True)
    phone_verified_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 관계 정의
    transactions = relationship("ItemTransactionDB", back_populates="buyer", foreign_keys="ItemTransactionDB.buyer_id")
    liked_items = relationship("UserLikedDB", back_populates="user")

class ItemDB(Base):
    """경매 물품 테이블"""
    __tablename__ = "item"
    
    item_id = Column(BigInteger, primary_key=True, autoincrement=True)
    seller_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    winner_id = Column(BigInteger, ForeignKey("users.id"), nullable=True)
    name = Column(String(30), nullable=False)
    title = Column(String(30), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(SQLEnum(CategoryEnum), nullable=False)  # 🔥 핵심 Feature
    current_price = Column(Integer, nullable=False)
    start_price = Column(Integer, nullable=False)
    bid_increment = Column(Integer, nullable=False)
    end_time = Column(DateTime, nullable=False)
    item_status = Column(SQLEnum(ItemStatusEnum), nullable=False, default=ItemStatusEnum.BIDDING)
    region_id = Column(BigInteger, ForeignKey("region.region_id"), nullable=False)
    view_count = Column(BigInteger, nullable=False, default=0)
    bid_count = Column(BigInteger, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 관계 정의
    seller = relationship("UserDB", foreign_keys=[seller_id])
    winner = relationship("UserDB", foreign_keys=[winner_id])
    transactions = relationship("ItemTransactionDB", back_populates="item")
    liked_by = relationship("UserLikedDB", back_populates="item")
    region = relationship("RegionDB", foreign_keys=[region_id])

class ItemTransactionDB(Base):
    """입찰 내역 테이블 (AI 추천의 핵심 데이터)"""
    __tablename__ = "item_transaction"
    
    transaction_id = Column(BigInteger, primary_key=True, autoincrement=True)
    buyer_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)  # 입찰자
    item_id = Column(BigInteger, ForeignKey("item.item_id"), nullable=False)  # 입찰한 상품
    bid_price = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 관계 정의
    buyer = relationship("UserDB", back_populates="transactions", foreign_keys=[buyer_id])
    item = relationship("ItemDB", back_populates="transactions", foreign_keys=[item_id])

class UserLikedDB(Base):
    """위시리스트 (찜하기) 테이블 (AI 추천의 핵심 데이터)"""
    __tablename__ = "user_liked"
    
    liked_id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)  # 찜한 사용자
    item_id = Column(BigInteger, ForeignKey("item.item_id"), nullable=False)  # 찜한 상품
    liked = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 관계 정의
    user = relationship("UserDB", back_populates="liked_items", foreign_keys=[user_id])
    item = relationship("ItemDB", back_populates="liked_by", foreign_keys=[item_id])

class RegionDB(Base):
    """지역 테이블 (Spring Boot Region 엔티티와 매핑)"""
    __tablename__ = "region"
    
    region_id = Column(BigInteger, primary_key=True, autoincrement=True)
    sido = Column(String(50), nullable=False)  # 시/도 (예: 서울특별시, 경기도)
    sigungu = Column(String(50), nullable=False)  # 시/군/구 (예: 강남구, 수원시)
    eupmyeondong = Column(String(50), nullable=False)  # 읍/면/동 (예: 역삼동)
    latitude = Column(Double, nullable=False)
    longitude = Column(Double, nullable=False)