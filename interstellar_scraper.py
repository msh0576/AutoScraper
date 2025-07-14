import sys
import pandas as pd
from playwright.sync_api import sync_playwright
import time
import os

def scrape_coupang(url_list):
    """주어진 URL 리스트를 크롤링하여 가격 정보를 추출합니다."""
    results = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        for url in url_list:
            if not url.strip():
                continue
            
            print(f"크롤링 시도: {url}")
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=15000)
                page.wait_for_selector("span.total-price", timeout=10000)

                price_element = page.query_selector("span.total-price")
                price = price_element.inner_text().replace(",", "") if price_element else "가격 없음"
                
                name_element = page.query_selector("h2.prod-buy-header__title")
                name = name_element.inner_text() if name_element else "상품명 없음"
                
                results.append({"상품명": name, "가격": price, "URL": url})
                print(f"  - 성공: {name} / {price}원")

            except Exception as e:
                print(f"  - 실패: {e}")
                results.append({"상품명": "추출 실패", "가격": "N/A", "URL": url})
            
            time.sleep(2) # 예의 바른 대기 시간

        browser.close()
    return results

def main():
    # GitHub Actions에서 전달받은 인자를 처리
    input_arg = sys.argv[1]
    
    # URL 목록을 파일에서 읽거나, 직접 전달받음
    if os.path.exists(input_arg):
        with open(input_arg, 'r') as f:
            urls_to_scrape = f.read().splitlines()
    else:
        urls_to_scrape = input_arg.split(',')

    if not urls_to_scrape:
        print("크롤링할 URL이 없습니다.")
        return

    scraped_data = scrape_coupang(urls_to_scrape)

    # 기존 데이터가 있으면 불러오고, 없으면 새로 만듦
    try:
        df_existing = pd.read_csv("coupang_data.csv")
    except FileNotFoundError:
        df_existing = pd.DataFrame()
        
    df_new = pd.DataFrame(scraped_data)
    
    # 새로운 데이터와 기존 데이터를 합치고 중복 URL 제거 (최신 정보로 업데이트)
    df_combined = pd.concat([df_existing, df_new]).drop_duplicates(subset=['URL'], keep='last')
    
    df_combined.to_csv("coupang_data.csv", index=False, encoding="utf-8-sig")
    print("모든 작업 완료. coupang_data.csv 파일이 업데이트되었습니다.")

if __name__ == "__main__":
    main()