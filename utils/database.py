import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from dotenv import load_dotenv
from typing import Generator

# 환경 변수 로드
load_dotenv()

# 데이터베이스 접속 정보
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME")

# MySQL 연결 문자열 생성
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# SQLAlchemy 엔진 생성
engine = create_engine(
    DATABASE_URL,
    echo=False,  # SQL 쿼리 로그 출력 (개발 시 True, 운영 시 False)
    pool_pre_ping=True,  # 연결 유효성 자동 검사
    pool_size=10,  # 연결 풀 크기
    max_overflow=20  # 최대 추가 연결 수
)

# 세션 팩토리 생성
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

def get_db() -> Generator[Session, None, None]:
    """
    FastAPI 의존성 주입용 DB 세션 생성 함수
    
    사용 예시:
        @app.get("/users")
        def get_users(db: Session = Depends(get_db)):
            users = db.query(UserDB).all()
            return users
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()