# 부릉 영업사원 도구 (Vroong Sales Tool)

네이버 지도 URL을 입력하면 상점 정보와 메뉴를 자동으로 크롤링하여 부릉 시스템에 온보딩하는 도구입니다.

## 🛠️ 기술 스택

| 영역 | 기술 |
|------|------|
| Frontend | React + Vite + TypeScript + Tailwind CSS |
| Backend | Python + FastAPI |
| Crawling | Selenium + WebDriver Manager |

## 📁 프로젝트 구조

```
vroong-sales-tool/
├── src/                    # React 프론트엔드
│   ├── App.tsx
│   └── index.css
├── backend/                # Python 백엔드
│   ├── main.py            # FastAPI 서버
│   ├── crawler.py         # Selenium 크롤러
│   └── requirements.txt
├── package.json
└── README.md
```

## 🚀 실행 방법

### 1. 백엔드 설정 및 실행

```bash
# 백엔드 디렉토리로 이동
cd backend

# Python 가상환경 생성 (권장)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 서버 실행
python main.py
# 또는
uvicorn main:app --reload --port 8000
```

백엔드 서버가 `http://localhost:8000`에서 실행됩니다.

### 2. 프론트엔드 실행

```bash
# 프로젝트 루트에서
npm install
npm run dev
```

프론트엔드가 `http://localhost:5173`에서 실행됩니다.

## 📖 사용 방법

1. **네이버 지도 검색**: 등록하려는 상점을 네이버 지도에서 검색
2. **URL 복사**: 상점 페이지의 URL을 복사
3. **URL 입력**: 도구에 URL을 붙여넣기
4. **정보 가져오기**: '상점 정보 가져오기' 버튼 클릭
5. **확인 및 등록**: 크롤링된 정보 확인 후 '부릉에 등록하기' 클릭

## 🔧 API 엔드포인트

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | API 상태 확인 |
| GET | `/health` | 헬스체크 |
| POST | `/api/crawl` | 네이버 지도 크롤링 |
| POST | `/api/onboard` | 상점 등록 |

### 크롤링 요청 예시

```json
POST /api/crawl
{
  "naver_map_url": "https://map.naver.com/p/entry/place/...",
  "business_number": "000-00-00000"
}
```

## ⚠️ 주의사항

- Chrome 브라우저가 설치되어 있어야 합니다.
- 네이버 지도 구조가 변경되면 크롤러 업데이트가 필요할 수 있습니다.
- 과도한 크롤링은 IP 차단의 원인이 될 수 있습니다.

## 📝 TODO

- [ ] 사용자 인증 추가
- [ ] 크롤링 결과 편집 기능
- [ ] 배치 크롤링 (여러 상점 한 번에)
- [ ] 크롤링 이력 관리
- [ ] 실제 부릉 시스템 API 연동
