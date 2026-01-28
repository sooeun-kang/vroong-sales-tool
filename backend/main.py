"""
부릉 영업사원용 온보딩 도구 - Backend API
네이버 지도에서 상점 정보 및 메뉴를 크롤링하고, Supabase에 등록합니다.
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import uvicorn
import os
import uuid
from datetime import datetime
from dotenv import load_dotenv

# Supabase 클라이언트
from supabase import create_client, Client

from crawler import NaverMapCrawler

# 환경변수 로드
load_dotenv()

# Supabase 설정
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://nuvorgfdclfrfwzrypls.supabase.co")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im51dm9yZ2ZkY2xmcmZ3enJ5cGxzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njk1MjMyNDksImV4cCI6MjA4NTA5OTI0OX0.ZnoIBrhpAEGmUmD325MBmm2nvII10We1N4vFuR32dow")

# Supabase 클라이언트 초기화
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

app = FastAPI(
    title="부릉 영업사원 도구 API",
    description="네이버 지도 크롤링을 통한 상점 온보딩 (Supabase 연동)",
    version="3.0.0"
)

# CORS 설정 (프론트엔드 연동)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "https://vroong-sales-tool.vercel.app",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
    hash_part = str(uuid.uuid4())[:8]
    return f"menu-{hash_part}"


def generate_store_id(store_name: str) -> str:
    """스토어 ID 생성"""
    # 한글, 영문, 숫자만 남기고 나머지는 하이픈으로
    store_id = store_name.lower().replace(" ", "-").replace("/", "-").replace("(", "").replace(")", "")[:30]
    return store_id


def create_vroong_menu_item(store: StoreInfo, menu: MenuItem, category: str, store_id: str) -> dict:
    """부릉 직접주문 웹용 메뉴 아이템 생성"""
    return {
        "id": generate_menu_id(store.name, menu.name),
        "restaurant_id": store_id,
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
        "version": "3.0.0",
        "status": "running",
        "database": "Supabase",
        "endpoints": {
            "crawl": "POST /api/crawl",
            "onboard": "POST /api/onboard",
            "stores": "GET /api/stores",
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


@app.get("/api/stores")
async def get_stores():
    """등록된 모든 상점 목록 조회"""
    try:
        response = supabase.table("stores").select("*").execute()
        return {
            "success": True,
            "stores": response.data,
            "count": len(response.data)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"상점 조회 오류: {str(e)}")


@app.get("/api/stores/{store_id}")
async def get_store(store_id: str):
    """특정 상점 및 메뉴 조회"""
    try:
        # 상점 정보
        store_response = supabase.table("stores").select("*").eq("id", store_id).single().execute()
        
        # 메뉴 정보
        menus_response = supabase.table("menus").select("*").eq("restaurant_id", store_id).execute()
        
        return {
            "success": True,
            "store": store_response.data,
            "menus": menus_response.data
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"상점을 찾을 수 없습니다: {str(e)}")


@app.get("/api/menus")
async def get_menus(category: Optional[str] = None):
    """메뉴 목록 조회 (카테고리 필터 가능)"""
    try:
        query = supabase.table("menus").select("*")
        
        if category:
            query = query.eq("category", category)
        
        response = query.execute()
        
        return {
            "success": True,
            "menus": response.data,
            "count": len(response.data)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"메뉴 조회 오류: {str(e)}")


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


@app.post("/api/onboard", response_model=OnboardResponse)
async def onboard_store(request: OnboardRequest):
    """
    크롤링한 상점 정보를 Supabase에 등록
    """
    try:
        store = request.store
        
        # 카테고리 매핑
        category = request.category_mapping or map_category_to_vroong(store.category)
        
        # 스토어 ID 생성
        store_id = generate_store_id(store.name)
        
        # 메뉴 아이템 생성
        menu_items = []
        for menu in store.menus:
            if menu.name and menu.price > 0:
                menu_item = create_vroong_menu_item(store, menu, category, store_id)
                menu_items.append(menu_item)
        
        if not menu_items:
            return OnboardResponse(
                success=False,
                message="등록 가능한 메뉴가 없습니다. (이름과 가격이 필요합니다)",
                menu_count=0
            )
        
        # 스토어 정보 생성
        store_data = {
            "id": store_id,
            "name": store.name,
            "address": store.address,
            "phone": store.phone,
            "category": category,
            "image_url": store.image_url,
            "business_number": request.business_number,
            "onboarded_at": datetime.now().isoformat()
        }
        
        # 기존 상점 확인
        existing = supabase.table("stores").select("id").eq("id", store_id).execute()
        
        if existing.data:
            # 기존 상점 업데이트
            supabase.table("stores").update(store_data).eq("id", store_id).execute()
            # 기존 메뉴 삭제
            supabase.table("menus").delete().eq("restaurant_id", store_id).execute()
        else:
            # 새 상점 추가
            supabase.table("stores").insert(store_data).execute()
        
        # 메뉴 추가
        supabase.table("menus").insert(menu_items).execute()
        
        return OnboardResponse(
            success=True,
            message=f"'{store.name}' 상점이 부릉에 등록되었습니다!",
            store_id=store_id,
            menu_count=len(menu_items),
            preview_url=f"https://vroong-direct-order.vercel.app/restaurant/{store_id}"
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"온보딩 오류: {str(e)}")


@app.delete("/api/stores/{store_id}")
async def delete_store(store_id: str):
    """상점 삭제 (메뉴도 함께 삭제됨 - CASCADE)"""
    try:
        supabase.table("stores").delete().eq("id", store_id).execute()
        return {"success": True, "message": f"상점 '{store_id}'가 삭제되었습니다."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"삭제 오류: {str(e)}")


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
