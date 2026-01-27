"""
부릉 영업사원용 온보딩 도구 - Backend API
네이버 지도에서 상점 정보 및 메뉴를 크롤링하고, 부릉 직접주문 웹에 등록합니다.
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import uvicorn
import json
import os
import uuid
from datetime import datetime

from crawler import NaverMapCrawler

app = FastAPI(
    title="부릉 영업사원 도구 API",
    description="네이버 지도 크롤링을 통한 상점 온보딩",
    version="2.0.0"
)

# CORS 설정 (프론트엔드 연동)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 부릉 직접주문 웹 경로
VROONG_DIRECT_ORDER_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "vroong-direct-order"
)

# 온보딩 데이터 파일 경로
ONBOARDED_JSON_PATH = os.path.join(
    VROONG_DIRECT_ORDER_PATH,
    "src", "data", "onboarded.json"
)


# ==================== Request/Response Models ====================

class CrawlRequest(BaseModel):
    naver_map_url: str
    business_number: Optional[str] = None

class MenuItem(BaseModel):
    name: str
    price: int
    description: Optional[str] = None
    image_url: Optional[str] = None

class StoreInfo(BaseModel):
    name: str
    address: str
    phone: Optional[str] = None
    category: Optional[str] = None
    business_hours: Optional[str] = None
    image_url: Optional[str] = None
    menus: List[MenuItem] = []

class CrawlResponse(BaseModel):
    success: bool
    message: str
    store: Optional[StoreInfo] = None

class OnboardRequest(BaseModel):
    store: StoreInfo
    business_number: Optional[str] = None
    category_mapping: Optional[str] = None  # 부릉 카테고리로 매핑

class OnboardResponse(BaseModel):
    success: bool
    message: str
    store_id: Optional[str] = None
    menu_count: int = 0
    preview_url: Optional[str] = None


# ==================== Helper Functions ====================

def map_category_to_vroong(naver_category: str) -> str:
    """네이버 카테고리를 부릉 카테고리로 매핑"""
    category_map = {
        "치킨": "chicken",
        "피자": "pizza",
        "한식": "korean",
        "중식": "chinese",
        "중국집": "chinese",
        "일식": "japanese",
        "일본음식": "japanese",
        "양식": "western",
        "분식": "snack",
        "카페": "cafe",
        "디저트": "cafe",
        "패스트푸드": "fastfood",
        "햄버거": "fastfood",
    }
    
    if not naver_category:
        return "korean"  # 기본값
    
    for key, value in category_map.items():
        if key in naver_category:
            return value
    
    return "korean"  # 기본값


def generate_menu_id(store_name: str, menu_name: str) -> str:
    """메뉴 ID 생성"""
    base = f"{store_name}-{menu_name}"
    hash_part = str(uuid.uuid4())[:8]
    return f"menu-{hash_part}"


def create_vroong_menu_item(store: StoreInfo, menu: MenuItem, category: str) -> dict:
    """부릉 직접주문 웹용 메뉴 아이템 생성"""
    return {
        "id": generate_menu_id(store.name, menu.name),
        "restaurant_name": store.name,
        "menu_name": menu.name,
        "price": menu.price,
        "original_price": int(menu.price * 1.15),  # 배달앱 대비 15% 절약 가정
        "image_url": menu.image_url or "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=400&h=300&fit=crop",
        "category": category,
        "order_method": "phone",
        "payment_method": "pay_on_delivery",
        "phone_number": store.phone or "미등록",
        "description": menu.description or f"{store.name}의 {menu.name}",
        "address": store.address,
        "rating": 4.5,
        "delivery_time": "30-40분"
    }


# ==================== API Endpoints ====================

@app.get("/")
async def root():
    return {
        "message": "부릉 영업사원 도구 API",
        "version": "2.0.0",
        "status": "running",
        "endpoints": {
            "crawl": "POST /api/crawl",
            "onboard": "POST /api/onboard",
            "preview": "GET /api/preview/{store_id}",
            "categories": "GET /api/categories"
        }
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.get("/api/categories")
async def get_categories():
    """사용 가능한 카테고리 목록"""
    return {
        "categories": [
            {"value": "chicken", "label": "치킨", "emoji": "🍗"},
            {"value": "pizza", "label": "피자", "emoji": "🍕"},
            {"value": "korean", "label": "한식", "emoji": "🍚"},
            {"value": "chinese", "label": "중식", "emoji": "🥡"},
            {"value": "japanese", "label": "일식", "emoji": "🍣"},
            {"value": "western", "label": "양식", "emoji": "🍝"},
            {"value": "snack", "label": "분식", "emoji": "🍜"},
            {"value": "cafe", "label": "카페/디저트", "emoji": "☕"},
            {"value": "fastfood", "label": "패스트푸드", "emoji": "🍔"},
        ]
    }


@app.post("/api/crawl", response_model=CrawlResponse)
async def crawl_store(request: CrawlRequest):
    """
    네이버 지도 URL에서 상점 정보 및 메뉴 크롤링
    """
    try:
        # URL 유효성 검사
        if "map.naver.com" not in request.naver_map_url:
            return CrawlResponse(
                success=False,
                message="유효한 네이버 지도 URL이 아닙니다. (map.naver.com)",
                store=None
            )
        
        crawler = NaverMapCrawler()
        store_info = await crawler.crawl(request.naver_map_url)
        
        if not store_info:
            return CrawlResponse(
                success=False,
                message="상점 정보를 가져오지 못했습니다. URL을 확인해주세요.",
                store=None
            )
        
        if not store_info.get("name"):
            return CrawlResponse(
                success=False,
                message="상점명을 찾을 수 없습니다. 상점 상세 페이지 URL인지 확인해주세요.",
                store=None
            )
        
        return CrawlResponse(
            success=True,
            message=f"'{store_info.get('name')}' 크롤링 완료! 메뉴 {len(store_info.get('menus', []))}개",
            store=store_info
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"크롤링 오류: {str(e)}")


def load_onboarded_data() -> dict:
    """온보딩된 데이터 로드"""
    try:
        if os.path.exists(ONBOARDED_JSON_PATH):
            with open(ONBOARDED_JSON_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"온보딩 데이터 로드 실패: {e}")
    
    return {"stores": [], "menus": [], "last_updated": None}


def save_onboarded_data(data: dict):
    """온보딩된 데이터 저장"""
    # 디렉토리 확인
    os.makedirs(os.path.dirname(ONBOARDED_JSON_PATH), exist_ok=True)
    
    data["last_updated"] = datetime.now().isoformat()
    
    with open(ONBOARDED_JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


@app.post("/api/onboard", response_model=OnboardResponse)
async def onboard_store(request: OnboardRequest):
    """
    크롤링한 상점 정보를 부릉 직접주문 웹에 등록
    
    vroong-direct-order/src/data/onboarded.json에 데이터를 추가합니다.
    """
    try:
        store = request.store
        
        # 카테고리 매핑
        category = request.category_mapping or map_category_to_vroong(store.category)
        
        # 스토어 ID 생성
        store_id = store.name.lower().replace(" ", "-").replace("/", "-").replace("(", "").replace(")", "")[:30]
        
        # 메뉴 아이템 생성
        menu_items = []
        for menu in store.menus:
            if menu.name and menu.price > 0:
                menu_item = create_vroong_menu_item(store, menu, category)
                menu_items.append(menu_item)
        
        if not menu_items:
            return OnboardResponse(
                success=False,
                message="등록 가능한 메뉴가 없습니다. (이름과 가격이 필요합니다)",
                menu_count=0
            )
        
        # 기존 온보딩 데이터 로드
        onboarded_data = load_onboarded_data()
        
        # 스토어 정보 생성
        store_info = {
            "id": store_id,
            "name": store.name,
            "address": store.address,
            "phone": store.phone,
            "category": category,
            "image_url": store.image_url,
            "business_number": request.business_number,
            "onboarded_at": datetime.now().isoformat()
        }
        
        # 중복 체크 및 업데이트
        existing_store_ids = [s["id"] for s in onboarded_data["stores"]]
        if store_id in existing_store_ids:
            # 기존 상점 업데이트
            idx = existing_store_ids.index(store_id)
            onboarded_data["stores"][idx] = store_info
            # 기존 메뉴 삭제
            onboarded_data["menus"] = [m for m in onboarded_data["menus"] if m.get("restaurant_id") != store_id]
        else:
            # 새 상점 추가
            onboarded_data["stores"].append(store_info)
        
        # 메뉴에 restaurant_id 추가하고 저장
        for menu_item in menu_items:
            menu_item["restaurant_id"] = store_id
            onboarded_data["menus"].append(menu_item)
        
        # 저장
        save_onboarded_data(onboarded_data)
        
        return OnboardResponse(
            success=True,
            message=f"'{store.name}' 상점이 부릉 직접주문 웹에 등록되었습니다!",
            store_id=store_id,
            menu_count=len(menu_items),
            preview_url=f"/restaurant/{store_id}"
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"온보딩 오류: {str(e)}")


@app.get("/api/preview/{store_id}")
async def preview_store(store_id: str):
    """
    등록된 상점의 미리보기 데이터 반환
    """
    # 온보딩된 파일 찾기
    backend_dir = os.path.dirname(__file__)
    for filename in os.listdir(backend_dir):
        if filename.startswith("onboarded_") and filename.endswith(".json"):
            filepath = os.path.join(backend_dir, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if store_id in data.get("store_name", "").lower().replace(" ", "-"):
                    return {
                        "success": True,
                        "store": data
                    }
    
    return {
        "success": False,
        "message": "상점을 찾을 수 없습니다."
    }


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
