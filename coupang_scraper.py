import os
import json
import time
import random
import requests
import pandas as pd
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from config import Config

class CoupangScraper:
    def __init__(self):
        self.config = Config()
        self.driver = None
        self.results = []
        
    def setup_driver(self):
        """웹드라이버 초기화"""
        try:
            service = webdriver.chrome.service.Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=self.config.get_chrome_options())
            
            # 봇 탐지 우회
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            self.driver.implicitly_wait(self.config.IMPLICIT_WAIT)
            print("✅ 웹드라이버 초기화 완료")
            return True
            
        except Exception as e:
            print(f"❌ 웹드라이버 초기화 실패: {str(e)}")
            return False
    
    def search_products(self, keyword, max_pages=2):
        """상품 검색 및 데이터 수집"""
        try:
            search_url = f"{self.config.SEARCH_URL}?q={keyword}"
            print(f"🔍 검색 시작: {keyword}")
            
            for page in range(1, max_pages + 1):
                page_url = f"{search_url}&page={page}"
                print(f"📄 페이지 {page} 크롤링 중...")
                
                if self._scrape_page(page_url, page):
                    # 페이지 간 랜덤 딜레이
                    time.sleep(random.uniform(2, 5))
                else:
                    print(f"⚠️ 페이지 {page} 크롤링 실패")
                    break
                    
            print(f"✅ 총 {len(self.results)}개 상품 수집 완료")
            return True
            
        except Exception as e:
            print(f"❌ 검색 실패: {str(e)}")
            return False
    
    def _scrape_page(self, url, page_num):
        """개별 페이지 크롤링"""
        try:
            self.driver.get(url)
            
            # 페이지 로딩 대기
            WebDriverWait(self.driver, self.config.PAGE_LOAD_TIMEOUT).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "li[data-component-type='s-search-result']"))
            )
            
            # 스크롤로 모든 상품 로딩
            self._scroll_to_load_products()
            
            # 상품 요소들 찾기
            product_elements = self.driver.find_elements(By.CSS_SELECTOR, "li[data-component-type='s-search-result']")
            
            page_results = []
            for idx, element in enumerate(product_elements):
                try:
                    product_data = self._extract_product_data(element, page_num, idx + 1)
                    if product_data:
                        page_results.append(product_data)
                        
                except Exception as e:
                    print(f"⚠️ 상품 {idx + 1} 추출 실패: {str(e)}")
                    continue
            
            self.results.extend(page_results)
            print(f"📦 페이지 {page_num}: {len(page_results)}개 상품 수집")
            return True
            
        except TimeoutException:
            print(f"⏰ 페이지 {page_num} 로딩 타임아웃")
            return False
        except Exception as e:
            print(f"❌ 페이지 {page_num} 크롤링 오류: {str(e)}")
            return False
    
    def _scroll_to_load_products(self):
        """페이지 스크롤하여 모든 상품 로딩"""
        try:
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            
            while True:
                # 페이지 끝까지 스크롤
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                
                # 로딩 대기
                time.sleep(2)
                
                # 새로운 높이 확인
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height
                
        except Exception as e:
            print(f"⚠️ 스크롤 로딩 오류: {str(e)}")
    
    def _extract_product_data(self, element, page_num, item_num):
        """개별 상품 데이터 추출"""
        try:
            # 기본 정보 추출
            name_elem = element.find_element(By.CSS_SELECTOR, "div.name")
            name = name_elem.text.strip() if name_elem else "정보 없음"
            
            # 가격 정보
            price_elem = element.find_element(By.CSS_SELECTOR, "strong.price-value")
            price_text = price_elem.text.strip() if price_elem else "0"
            price = self._parse_price(price_text)
            
            # 원가 (할인 전 가격)
            original_price = price
            try:
                original_elem = element.find_element(By.CSS_SELECTOR, "del.base-price")
                original_price_text = original_elem.text.strip()
                original_price = self._parse_price(original_price_text)
            except NoSuchElementException:
                pass
            
            # 할인율
            discount_rate = 0
            if original_price > price:
                discount_rate = round(((original_price - price) / original_price) * 100, 1)
            
            # 상품 링크
            link_elem = element.find_element(By.CSS_SELECTOR, "a")
            relative_url = link_elem.get_attribute('href') if link_elem else ""
            full_url = relative_url if relative_url.startswith('http') else f"{self.config.BASE_URL}{relative_url}"
            
            # 이미지 URL
            img_elem = element.find_element(By.CSS_SELECTOR, "img")
            image_url = img_elem.get_attribute('src') if img_elem else ""
            
            # 평점 정보
            rating = 0.0
            review_count = 0
            try:
                rating_elem = element.find_element(By.CSS_SELECTOR, "em.rating")
                rating = float(rating_elem.text.strip()) if rating_elem else 0.0
                
                review_elem = element.find_element(By.CSS_SELECTOR, "span.rating-total-review")
                review_text = review_elem.text.strip().replace('(', '').replace(')', '').replace(',', '')
                review_count = int(review_text) if review_text.isdigit() else 0
            except (NoSuchElementException, ValueError):
                pass
            
            # 배송 정보
            shipping_info = "일반배송"
            try:
                rocket_elem = element.find_element(By.CSS_SELECTOR, ".rocket-badge")
                if rocket_elem:
                    shipping_info = "로켓배송"
            except NoSuchElementException:
                pass
            
            # 결과 데이터 구성
            product_data = {
                'product_name': name,
                'price': price,
                'original_price': original_price,
                'discount_rate': f"{discount_rate}%",
                'url': full_url,
                'image_url': image_url,
                'rating': rating,
                'review_count': review_count,
                'shipping': shipping_info,
                'page': page_num,
                'position': item_num,
                'scraped_at': datetime.now().isoformat(),
                'source': 'coupang'
            }
            
            return product_data
            
        except Exception as e:
            print(f"❌ 상품 데이터 추출 실패: {str(e)}")
            return None
    
    def _parse_price(self, price_text):
        """가격 텍스트를 숫자로 변환"""
        try:
            # 숫자가 아닌 문자 제거
            cleaned_price = ''.join(filter(str.isdigit, price_text))
            return int(cleaned_price) if cleaned_price else 0
        except:
            return 0
    
    def save_results(self):
        """결과 저장"""
        try:
            # 결과 디렉토리 생성
            os.makedirs('results', exist_ok=True)
            
            if not self.results:
                print("⚠️ 저장할 데이터가 없습니다")
                return False
            
            # DataFrame 생성
            df = pd.DataFrame(self.results)
            
            # 타임스탬프
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            keyword_safe = self.config.KEYWORD.replace(' ', '_')
            
            # JSON 저장
            json_filename = f"results/coupang_{keyword_safe}_{timestamp}.json"
            with open(json_filename, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, ensure_ascii=False, indent=2)
            
            # CSV 저장
            csv_filename = f"results/coupang_{keyword_safe}_{timestamp}.csv"
            df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
            
            # 요약 통계
            summary = {
                'keyword': self.config.KEYWORD,
                'total_products': len(self.results),
                'avg_price': int(df['price'].mean()) if len(df) > 0 else 0,
                'min_price': int(df['price'].min()) if len(df) > 0 else 0,
                'max_price': int(df['price'].max()) if len(df) > 0 else 0,
                'scraped_at': datetime.now().isoformat(),
                'files': {
                    'json': json_filename,
                    'csv': csv_filename
                }
            }
            
            # 요약 저장
            summary_filename = f"results/summary_{keyword_safe}_{timestamp}.json"
            with open(summary_filename, 'w', encoding='utf-8') as f:
                json.dump(summary, f, ensure_ascii=False, indent=2)
            
            print(f"💾 결과 저장 완료:")
            print(f"   - JSON: {json_filename}")
            print(f"   - CSV: {csv_filename}")
            print(f"   - 요약: {summary_filename}")
            
            return summary
            
        except Exception as e:
            print(f"❌ 결과 저장 실패: {str(e)}")
            return False
    
    def send_to_webhook(self, summary):
        """n8n webhook으로 결과 전송"""
        if not self.config.WEBHOOK_URL:
            print("ℹ️ Webhook URL이 설정되지 않음")
            return True
            
        try:
            payload = {
                'status': 'success',
                'summary': summary,
                'products': self.results[:10],  # 상위 10개만 전송
                'message': f"쿠팡 '{self.config.KEYWORD}' 검색 완료: {len(self.results)}개 상품"
            }
            
            response = requests.post(
                self.config.WEBHOOK_URL,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            if response.status_code == 200:
                print("📡 Webhook 전송 성공")
                return True
            else:
                print(f"⚠️ Webhook 전송 실패: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Webhook 전송 오류: {str(e)}")
            return False
    
    def cleanup(self):
        """리소스 정리"""
        if self.driver:
            self.driver.quit()
            print("🧹 웹드라이버 종료")

def main():
    """메인 실행 함수"""
    scraper = CoupangScraper()
    
    try:
        print("🚀 쿠팡 크롤링 시작")
        print(f"📝 검색어: {scraper.config.KEYWORD}")
        print(f"📄 최대 페이지: {scraper.config.MAX_PAGES}")
        
        # 드라이버 초기화
        if not scraper.setup_driver():
            return
        
        # 상품 검색
        if scraper.search_products(scraper.config.KEYWORD, scraper.config.MAX_PAGES):
            # 결과 저장
            summary = scraper.save_results()
            
            if summary:
                # Webhook 전송
                scraper.send_to_webhook(summary)
                print("✅ 크롤링 완료!")
            else:
                print("❌ 결과 저장 실패")
        else:
            print("❌ 상품 검색 실패")
            
    except KeyboardInterrupt:
        print("\n⏹️ 사용자에 의해 중단됨")
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {str(e)}")
    finally:
        scraper.cleanup()

if __name__ == "__main__":
    main()