"""
중고 시세 크롤링 모듈 (Selenium 버전)
- Selenium + Chrome WebDriver 사용
- JavaScript 렌더링 지원
"""

import re
import time
from typing import List, Optional
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
import logging

logger = logging.getLogger(__name__)


class PriceCrawlerSelenium:
    """중고 시세 크롤링 클래스 (Selenium 버전)"""

    def __init__(self, timeout: int = 10):
        """
        Args:
            timeout: 페이지 로딩 타임아웃 (초)
        """
        self.timeout = timeout

    def _create_driver(self):
        """Chrome WebDriver 생성 (자동 다운로드)"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')  # 백그라운드 실행
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        chrome_options.add_argument('--log-level=3')  # 로그 최소화

        try:
            # ChromeDriver 자동 다운로드 및 설치
            driver_path = ChromeDriverManager().install()
            logger.info(f"ChromeDriver 경로: {driver_path}")

            # 실제 chromedriver.exe 파일 찾기
            import os
            if os.path.isfile(driver_path) and driver_path.endswith('.exe'):
                service = Service(driver_path)
            else:
                # 디렉토리가 반환된 경우 chromedriver.exe 찾기
                driver_dir = driver_path if os.path.isdir(driver_path) else os.path.dirname(driver_path)
                exe_path = os.path.join(driver_dir, 'chromedriver.exe')
                if os.path.exists(exe_path):
                    service = Service(exe_path)
                    logger.info(f"ChromeDriver 실행 파일: {exe_path}")
                else:
                    # 폴더 내 검색
                    for root, dirs, files in os.walk(driver_dir):
                        for file in files:
                            if file == 'chromedriver.exe':
                                exe_path = os.path.join(root, file)
                                service = Service(exe_path)
                                logger.info(f"ChromeDriver 실행 파일 발견: {exe_path}")
                                break
                        if 'service' in locals():
                            break

            driver = webdriver.Chrome(service=service, options=chrome_options)
            driver.set_page_load_timeout(self.timeout)
            return driver
        except Exception as e:
            logger.error(f"ChromeDriver 생성 실패: {e}", exc_info=True)
            raise

    def crawl_joongna(self, keyword: str, max_items: int = 20) -> List[int]:
        """중고나라 크롤링"""
        prices = []
        driver = None

        try:
            driver = self._create_driver()
            search_url = f"https://web.joongna.com/search/{keyword}"
            logger.info(f"중고나라 크롤링: URL 접속 중 - {search_url}")

            driver.get(search_url)
            time.sleep(3)  # JavaScript 렌더링 대기

            # 페이지 스크롤 (lazy loading 트리거)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
            time.sleep(2)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)

            logger.info(f"중고나라 크롤링: 페이지 로딩 완료")

            # 상품 카드 요소 찾기 (다양한 접근 방식)
            product_selectors = [
                'a[href*="/product/"]',  # 상품 링크
                'article',  # 상품 카드
                'div[class*="item"]',  # 아이템 컨테이너
                'div[class*="product"]',  # 제품 컨테이너
                'li[class*="item"]',  # 리스트 아이템
            ]

            product_elements = []
            for selector in product_selectors:
                product_elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if product_elements:
                    logger.info(f"중고나라: 선택자 '{selector}'로 {len(product_elements)}개 상품 발견")
                    break

            if not product_elements:
                logger.warning(f"중고나라: 상품 요소를 찾을 수 없음")
                # 디버깅 정보 출력
                page_text = driver.find_element(By.TAG_NAME, 'body').text[:1000]
                logger.warning(f"중고나라: 페이지 텍스트 샘플: {page_text[:300]}")
                screenshot_path = "debug_joongna.png"
                driver.save_screenshot(screenshot_path)
                logger.info(f"중고나라: 디버깅 스크린샷 저장 - {screenshot_path}")

                # HTML 구조 일부 저장
                html_sample = driver.page_source[:3000]
                with open("debug_joongna.html", "w", encoding="utf-8") as f:
                    f.write(html_sample)
                logger.info(f"중고나라: HTML 샘플 저장 - debug_joongna.html")
                return prices

            logger.info(f"중고나라: 총 {len(product_elements)}개 상품 요소 발견")

            # 각 상품 카드에서 가격 추출
            for idx, product in enumerate(product_elements[:max_items]):
                try:
                    # 상품 카드 내에서 가격 찾기
                    price_text = None

                    # 방법 1: 전체 텍스트에서 가격 패턴 찾기
                    product_text = product.text
                    if product_text:
                        price = self._extract_price(product_text)
                        if price:
                            prices.append(price)
                            logger.info(f"중고나라: 상품 {idx+1} - 가격 추출 성공: {price:,}원")
                            continue

                    # 방법 2: 하위 요소에서 가격 찾기
                    price_candidates = product.find_elements(By.CSS_SELECTOR,
                        'span, div, p, strong, b')
                    for candidate in price_candidates:
                        text = candidate.text.strip()
                        if text and ('원' in text or '만원' in text or text.replace(',','').isdigit()):
                            price = self._extract_price(text)
                            if price:
                                prices.append(price)
                                logger.info(f"중고나라: 상품 {idx+1} - 가격 추출 성공: {price:,}원")
                                break

                except Exception as e:
                    logger.warning(f"중고나라: 상품 {idx+1} 파싱 에러 - {e}")
                    continue

        except TimeoutException:
            logger.error(f"중고나라 크롤링 타임아웃: {keyword}")
        except WebDriverException as e:
            logger.error(f"중고나라 WebDriver 에러: {e}")
        except Exception as e:
            logger.error(f"중고나라 크롤링 에러: {type(e).__name__}: {str(e)}", exc_info=True)
        finally:
            if driver:
                driver.quit()

        logger.info(f"중고나라 크롤링 완료: {keyword} -> {len(prices)}개")
        return prices

    def crawl_all(self, keyword: str, max_items_per_platform: int = 20) -> dict:
        """중고나라 크롤링"""
        logger.info(f"크롤링 시작: {keyword}")

        joongna_prices = self.crawl_joongna(keyword, max_items_per_platform)

        total_count = len(joongna_prices)
        logger.info(f"크롤링 완료: 총 {total_count}개 수집")

        return {
            "joongna": joongna_prices
        }

    def _extract_price(self, text: str) -> Optional[int]:
        """텍스트에서 가격 추출"""
        # 공백, 쉼표 제거
        text = text.replace(',', '').replace(' ', '').replace('\n', '')

        # "만원" 표기 처리 (예: "49만원", "49.9만원")
        if '만원' in text:
            # 소수점 포함 (예: 49.9만원 -> 499000)
            match = re.search(r'(\d+\.?\d*)만원', text)
            if match:
                value = float(match.group(1))
                price = int(value * 10000)
                if 1000 <= price <= 100000000:
                    return price

        # "만" 표기 처리 (예: "49만", "49.9만")
        if '만' in text and '만원' not in text:
            match = re.search(r'(\d+\.?\d*)만', text)
            if match:
                value = float(match.group(1))
                price = int(value * 10000)
                if 1000 <= price <= 100000000:
                    return price

        # "원" 표기 처리 (예: "490000원")
        if '원' in text:
            match = re.search(r'(\d+)원', text)
            if match:
                price = int(match.group(1))
                if 1000 <= price <= 100000000:
                    return price

        # 숫자만 있는 경우 (예: "490000")
        match = re.search(r'(\d{4,})', text)
        if match:
            price = int(match.group(1))
            if 1000 <= price <= 100000000:
                return price

        return None

    def reduce_keyword(self, keyword: str) -> Optional[str]:
        """키워드 축소"""
        words = keyword.split()
        if len(words) <= 1:
            return None
        reduced = ' '.join(words[:-1])
        logger.info(f"키워드 축소: {keyword} -> {reduced}")
        return reduced


def crawl_with_fallback_selenium(keyword: str, min_samples: int = 3) -> dict:
    """키워드 축소 재시도 포함 크롤링 (중고나라 전용)"""
    crawler = PriceCrawlerSelenium()
    current_keyword = keyword

    while current_keyword:
        results = crawler.crawl_all(current_keyword)
        total_count = len(results["joongna"])

        if total_count >= min_samples:
            results["final_keyword"] = current_keyword
            return results

        logger.warning(f"샘플 부족 ({total_count}개 < {min_samples}개), 키워드 축소 시도")
        current_keyword = crawler.reduce_keyword(current_keyword)

    logger.warning(f"키워드 축소 한계 도달, 수집된 데이터로 진행")
    results["final_keyword"] = keyword
    return results
