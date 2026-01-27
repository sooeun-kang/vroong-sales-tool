"""
네이버 지도 크롤러 v2
Selenium을 사용하여 상점 정보 및 메뉴를 크롤링합니다.

개선 사항:
- 다양한 셀렉터 fallback 지원
- 에러 핸들링 강화
- 상세한 로깅
- 메뉴 탭 자동 탐색
"""

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from typing import Optional, List, Tuple
import asyncio
import re
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NaverMapCrawler:
    """네이버 지도 상점 정보 크롤러"""
    
    # 셀렉터 정의 (여러 버전 지원)
    SELECTORS = {
        "name": [
            "span.GHAhO",
            "span.Fc1rA",
            ".place_section_content h2",
            "div.zD5Nm h2",
            ".O8qbU"
        ],
        "category": [
            "span.lnJFt",
            "span.DJJvD",
            ".LDgIH + span",
        ],
        "address": [
            "span.LDgIH",
            ".O8qbU.tQY7D span",
            "div.vV_z_ span",
        ],
        "phone": [
            "span.xlx7Q",
            "span.dry01",
            "a[href^='tel:']",
        ],
        "image": [
            ".K0PDV img",
            ".place_thumb img",
            ".fNygA img",
            "div.K0PDV._div img",
        ],
        "menu_tab": [
            "a.tpj9w",
            "a[href*='menu']",
            "span.veBoZ",
        ],
        "menu_item": [
            "li.E2jtL",
            "div.place_section_content li",
            ".tQY7D li",
        ],
        "menu_name": [
            ".lPzHi",
            ".tit_item",
            "span.A_cdD",
        ],
        "menu_price": [
            ".GXS1X",
            ".price",
            "div.CLSES em",
        ],
        "menu_desc": [
            ".kPogF",
            ".detail_txt",
        ],
    }
    
    def __init__(self):
        self.driver = None
    
    def _init_driver(self):
        """Chrome WebDriver 초기화"""
        options = Options()
        options.add_argument("--headless=new")  # 새 헤드리스 모드
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
        
        # 자동화 탐지 방지
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        self.driver.implicitly_wait(5)
        
        # 자동화 탐지 우회
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        logger.info("WebDriver 초기화 완료")
    
    def _close_driver(self):
        """WebDriver 종료"""
        if self.driver:
            self.driver.quit()
            self.driver = None
            logger.info("WebDriver 종료")
    
    def _find_element_multi(self, selectors: List[str], parent=None) -> Tuple[Optional[any], str]:
        """여러 셀렉터 중 첫 번째로 찾은 요소 반환"""
        root = parent or self.driver
        for selector in selectors:
            try:
                elem = root.find_element(By.CSS_SELECTOR, selector)
                if elem:
                    return elem, selector
            except NoSuchElementException:
                continue
        return None, ""
    
    def _find_elements_multi(self, selectors: List[str], parent=None) -> Tuple[List[any], str]:
        """여러 셀렉터 중 첫 번째로 찾은 요소들 반환"""
        root = parent or self.driver
        for selector in selectors:
            try:
                elems = root.find_elements(By.CSS_SELECTOR, selector)
                if elems:
                    return elems, selector
            except:
                continue
        return [], ""
    
    async def crawl(self, naver_map_url: str) -> Optional[dict]:
        """
        네이버 지도 URL에서 상점 정보 크롤링
        
        Args:
            naver_map_url: 네이버 지도 상점 URL
            
        Returns:
            상점 정보 딕셔너리 또는 None
        """
        logger.info(f"크롤링 시작: {naver_map_url}")
        
        try:
            self._init_driver()
            
            # URL 접속
            self.driver.get(naver_map_url)
            await asyncio.sleep(3)
            
            # iframe 전환 시도
            await self._switch_to_iframe()
            
            # 상점 기본 정보 추출
            store_info = await self._extract_store_info()
            logger.info(f"상점 정보: {store_info.get('name', 'Unknown')}")
            
            # 메뉴 정보 추출
            menus = await self._extract_menus()
            store_info["menus"] = menus
            logger.info(f"메뉴 {len(menus)}개 추출 완료")
            
            return store_info
            
        except Exception as e:
            logger.error(f"크롤링 오류: {e}")
            import traceback
            traceback.print_exc()
            return None
        finally:
            self._close_driver()
    
    async def _switch_to_iframe(self):
        """iframe으로 전환"""
        iframe_selectors = ["iframe#entryIframe", "iframe#searchIframe"]
        
        for selector in iframe_selectors:
            try:
                iframe = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                self.driver.switch_to.frame(iframe)
                logger.info(f"iframe 전환 성공: {selector}")
                return
            except TimeoutException:
                continue
        
        logger.warning("iframe을 찾지 못함, 기본 페이지에서 진행")
    
    async def _extract_store_info(self) -> dict:
        """상점 기본 정보 추출"""
        store_info = {
            "name": "",
            "address": "",
            "phone": None,
            "category": None,
            "business_hours": None,
            "image_url": None,
        }
        
        # 상점명
        name_elem, _ = self._find_element_multi(self.SELECTORS["name"])
        if name_elem:
            store_info["name"] = name_elem.text.strip()
        
        # 카테고리
        cat_elem, _ = self._find_element_multi(self.SELECTORS["category"])
        if cat_elem:
            store_info["category"] = cat_elem.text.strip()
        
        # 주소
        addr_elem, _ = self._find_element_multi(self.SELECTORS["address"])
        if addr_elem:
            store_info["address"] = addr_elem.text.strip()
        
        # 전화번호
        phone_elem, _ = self._find_element_multi(self.SELECTORS["phone"])
        if phone_elem:
            phone_text = phone_elem.text.strip()
            if not phone_text:
                phone_text = phone_elem.get_attribute("href") or ""
                phone_text = phone_text.replace("tel:", "")
            store_info["phone"] = phone_text
        
        # 대표 이미지
        img_elem, _ = self._find_element_multi(self.SELECTORS["image"])
        if img_elem:
            store_info["image_url"] = img_elem.get_attribute("src")
        
        return store_info
    
    async def _extract_menus(self) -> List[dict]:
        """메뉴 정보 추출"""
        menus = []
        
        try:
            # 메뉴 탭 클릭 시도
            await self._click_menu_tab()
            await asyncio.sleep(2)
            
            # 메뉴 아이템 추출
            menu_items, selector_used = self._find_elements_multi(self.SELECTORS["menu_item"])
            logger.info(f"메뉴 아이템 {len(menu_items)}개 발견 (셀렉터: {selector_used})")
            
            for item in menu_items[:30]:  # 최대 30개
                try:
                    menu = await self._extract_single_menu(item)
                    if menu and menu["name"]:
                        menus.append(menu)
                except Exception as e:
                    logger.debug(f"메뉴 아이템 추출 실패: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"메뉴 추출 오류: {e}")
        
        return menus
    
    async def _click_menu_tab(self):
        """메뉴 탭 클릭"""
        try:
            tabs, _ = self._find_elements_multi(self.SELECTORS["menu_tab"])
            for tab in tabs:
                tab_text = tab.text.strip()
                if "메뉴" in tab_text:
                    tab.click()
                    logger.info("메뉴 탭 클릭 성공")
                    return
            
            # "메뉴" 텍스트가 없으면 모든 탭 순회
            all_tabs = self.driver.find_elements(By.CSS_SELECTOR, "a, button, span")
            for tab in all_tabs:
                try:
                    if tab.text.strip() == "메뉴":
                        tab.click()
                        logger.info("메뉴 탭 클릭 성공 (전체 탐색)")
                        return
                except:
                    continue
                    
        except Exception as e:
            logger.warning(f"메뉴 탭 클릭 실패: {e}")
    
    async def _extract_single_menu(self, item) -> dict:
        """단일 메뉴 아이템 추출"""
        menu = {
            "name": "",
            "price": 0,
            "description": None,
            "image_url": None
        }
        
        # 메뉴명
        name_elem, _ = self._find_element_multi(self.SELECTORS["menu_name"], item)
        if name_elem:
            menu["name"] = name_elem.text.strip()
        else:
            # fallback: 첫 번째 텍스트 요소
            try:
                text_elem = item.find_element(By.CSS_SELECTOR, "span, div, p")
                menu["name"] = text_elem.text.strip()
            except:
                pass
        
        # 가격
        price_elem, _ = self._find_element_multi(self.SELECTORS["menu_price"], item)
        if price_elem:
            price_text = price_elem.text.strip()
            price_num = re.sub(r'[^\d]', '', price_text)
            menu["price"] = int(price_num) if price_num else 0
        
        # 설명
        desc_elem, _ = self._find_element_multi(self.SELECTORS["menu_desc"], item)
        if desc_elem:
            menu["description"] = desc_elem.text.strip()
        
        # 이미지
        try:
            img_elem = item.find_element(By.CSS_SELECTOR, "img")
            src = img_elem.get_attribute("src")
            if src and not src.startswith("data:"):
                menu["image_url"] = src
        except:
            pass
        
        return menu


# 테스트용
if __name__ == "__main__":
    import asyncio
    
    async def test():
        crawler = NaverMapCrawler()
        # 테스트 URL
        test_url = "https://map.naver.com/p/entry/place/1234567890"
        result = await crawler.crawl(test_url)
        print("=" * 50)
        print("크롤링 결과:")
        print(f"상점명: {result.get('name')}")
        print(f"주소: {result.get('address')}")
        print(f"전화: {result.get('phone')}")
        print(f"메뉴 수: {len(result.get('menus', []))}")
        for menu in result.get('menus', [])[:5]:
            print(f"  - {menu['name']}: {menu['price']}원")
    
    asyncio.run(test())
