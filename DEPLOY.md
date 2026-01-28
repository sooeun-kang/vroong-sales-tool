# 부릉 영업사원 도구 배포 가이드

## 아키텍처

```
┌─────────────────────────────────────────────────────┐
│                    Vercel                           │
│  ┌─────────────────────────────────────────────┐   │
│  │    프론트엔드 (React + Vite)                 │   │
│  │    https://vroong-sales-tool.vercel.app     │   │
│  └─────────────────────────────────────────────┘   │
└───────────────────────┬─────────────────────────────┘
                        │ API 호출
                        ▼
┌─────────────────────────────────────────────────────┐
│               Google Cloud Run                       │
│  ┌─────────────────────────────────────────────┐   │
│  │    백엔드 (FastAPI + Selenium)               │   │
│  │    - 네이버 지도 크롤링                       │   │
│  │    - Supabase 연동                           │   │
│  └─────────────────────────────────────────────┘   │
└───────────────────────┬─────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│                   Supabase                          │
│  ┌─────────────────────────────────────────────┐   │
│  │    PostgreSQL 데이터베이스                    │   │
│  │    - stores 테이블                           │   │
│  │    - menus 테이블                            │   │
│  └─────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

## 1. Supabase 설정

### 1.1 테이블 생성

SQL Editor에서 실행:

```sql
-- 상점 테이블
CREATE TABLE stores (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  address TEXT,
  phone TEXT,
  category TEXT,
  image_url TEXT,
  business_number TEXT,
  onboarded_at TIMESTAMPTZ DEFAULT NOW(),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 메뉴 테이블
CREATE TABLE menus (
  id TEXT PRIMARY KEY,
  restaurant_id TEXT REFERENCES stores(id) ON DELETE CASCADE,
  restaurant_name TEXT NOT NULL,
  menu_name TEXT NOT NULL,
  price INTEGER NOT NULL,
  original_price INTEGER,
  image_url TEXT,
  category TEXT,
  order_method TEXT DEFAULT 'phone',
  payment_method TEXT DEFAULT 'pay_on_delivery',
  phone_number TEXT,
  description TEXT,
  address TEXT,
  rating DECIMAL(2,1) DEFAULT 4.5,
  delivery_time TEXT DEFAULT '30-40분',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 인덱스
CREATE INDEX idx_menus_restaurant_id ON menus(restaurant_id);
CREATE INDEX idx_menus_category ON menus(category);

-- RLS 정책
ALTER TABLE stores ENABLE ROW LEVEL SECURITY;
ALTER TABLE menus ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Public read access" ON stores FOR SELECT USING (true);
CREATE POLICY "Public read access" ON menus FOR SELECT USING (true);
CREATE POLICY "Public insert access" ON stores FOR INSERT WITH CHECK (true);
CREATE POLICY "Public insert access" ON menus FOR INSERT WITH CHECK (true);
CREATE POLICY "Public update access" ON stores FOR UPDATE USING (true);
CREATE POLICY "Public update access" ON menus FOR UPDATE USING (true);
CREATE POLICY "Public delete access" ON menus FOR DELETE USING (true);
```

## 2. Google Cloud Run 배포

### 2.1 사전 준비

```bash
# gcloud CLI 설치 확인
gcloud --version

# 로그인
gcloud auth login

# 프로젝트 설정 (기존 프로젝트 사용)
gcloud config set project YOUR_PROJECT_ID
```

### 2.2 Docker 이미지 빌드 및 푸시

```bash
cd vroong-sales-tool/backend

# Cloud Build로 이미지 빌드 및 배포
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/vroong-sales-api

# 또는 Artifact Registry 사용 (권장)
gcloud builds submit --tag asia-northeast3-docker.pkg.dev/YOUR_PROJECT_ID/vroong/sales-api
```

### 2.3 Cloud Run 배포

```bash
gcloud run deploy vroong-sales-api \
  --image gcr.io/YOUR_PROJECT_ID/vroong-sales-api \
  --platform managed \
  --region asia-northeast3 \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300 \
  --set-env-vars "SUPABASE_URL=https://nuvorgfdclfrfwzrypls.supabase.co" \
  --set-env-vars "SUPABASE_ANON_KEY=YOUR_ANON_KEY"
```

### 2.4 배포 확인

배포 완료 후 URL 확인:
```
Service URL: https://vroong-sales-api-xxxxx-an.a.run.app
```

## 3. Vercel 프론트엔드 설정

### 3.1 환경변수 설정

Vercel Dashboard → vroong-sales-tool → Settings → Environment Variables

| Key | Value |
|-----|-------|
| `VITE_API_URL` | `https://vroong-sales-api-xxxxx-an.a.run.app` |

### 3.2 재배포

```bash
cd vroong-sales-tool
git add .
git commit -m "feat: Cloud Run 백엔드 연동"
git push origin main
```

Vercel이 자동으로 재배포합니다.

## 4. 테스트

1. https://vroong-sales-tool.vercel.app 접속
2. 네이버 지도 URL 입력
3. 크롤링 테스트
4. 온보딩 테스트
5. Supabase에서 데이터 확인

## 문제 해결

### Cloud Run 타임아웃
- 크롤링 시간이 길면 `--timeout 300` (5분)으로 늘림

### 메모리 부족
- Selenium + Chrome이 메모리를 많이 사용
- `--memory 2Gi` 이상 권장

### CORS 오류
- Cloud Run URL이 CORS allow_origins에 포함되어 있는지 확인
