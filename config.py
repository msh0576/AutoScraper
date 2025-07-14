import os
from fake_useragent import UserAgent

class Config:
    # 기본 설정
    BASE_URL = "https://www.coupang.com"
    SEARCH_URL = "https://www.coupang.com/np/search"
    
    # 크롤링 설정
    MAX_RETRY = 3
    PAGE_LOAD_TIMEOUT = 30
    IMPLICIT_WAIT = 10
    
    # 환경변수에서 가져오기
    KEYWORD = os.getenv('KEYWORD', '나이키 에어포스')
    MAX_PAGES = int(os.getenv('MAX_PAGES', '2'))
    WEBHOOK_URL = os.getenv('WEBHOOK_URL', '')
    
    
    # User-Agent 로테이션
    @staticmethod
    def get_random_user_agent():
        ua = UserAgent()
        return ua.random
    

    # Chrome 옵션
    @staticmethod
    def get_chrome_options():
        from selenium.webdriver.chrome.options import Options
        
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument(f'--user-agent={Config.get_random_user_agent()}')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        return options