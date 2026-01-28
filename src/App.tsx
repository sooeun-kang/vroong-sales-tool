import { useState, useEffect } from 'react'
import './index.css'

// ==================== API Configuration ====================

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// ==================== Types ====================

interface MenuItem {
  name: string
  price: number
  description?: string
  image_url?: string
}

interface StoreInfo {
  name: string
  address: string
  phone?: string
  category?: string
  business_hours?: string
  image_url?: string
  menus: MenuItem[]
}

interface CrawlResponse {
  success: boolean
  message: string
  store?: StoreInfo
}

interface OnboardResponse {
  success: boolean
  message: string
  store_id?: string
  menu_count: number
  preview_url?: string
}

interface Category {
  value: string
  label: string
  emoji: string
}


// ==================== App Component ====================

function App() {
  // Input states
  const [naverMapUrl, setNaverMapUrl] = useState('')
  const [businessNumber, setBusinessNumber] = useState('')
  const [selectedCategory, setSelectedCategory] = useState('')
  
  // Loading & Result states
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<CrawlResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [onboardResult, setOnboardResult] = useState<OnboardResponse | null>(null)
  
  // Categories
  const [categories, setCategories] = useState<Category[]>([])
  
  // View mode
  const [viewMode, setViewMode] = useState<'result' | 'preview'>('result')

  // Fetch categories on mount
  useEffect(() => {
    fetch(`${API_BASE_URL}/api/categories`)
      .then(res => res.json())
      .then(data => setCategories(data.categories || []))
      .catch(() => {
        // 기본 카테고리 설정
        setCategories([
          { value: 'chicken', label: '치킨', emoji: '🍗' },
          { value: 'pizza', label: '피자', emoji: '🍕' },
          { value: 'korean', label: '한식', emoji: '🍚' },
          { value: 'chinese', label: '중식', emoji: '🥡' },
          { value: 'japanese', label: '일식', emoji: '🍣' },
          { value: 'western', label: '양식', emoji: '🍝' },
          { value: 'snack', label: '분식', emoji: '🍜' },
          { value: 'cafe', label: '카페', emoji: '☕' },
          { value: 'fastfood', label: '패스트푸드', emoji: '🍔' },
        ])
      })
  }, [])

  // ==================== Handlers ====================

  const handleCrawl = async () => {
    if (!naverMapUrl.trim()) {
      setError('네이버 지도 URL을 입력해주세요.')
      return
    }

    setLoading(true)
    setError(null)
    setResult(null)
    setOnboardResult(null)
    setViewMode('result')

    try {
      const response = await fetch(`${API_BASE_URL}/api/crawl`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          naver_map_url: naverMapUrl,
          business_number: businessNumber || null,
        }),
      })

      const data: CrawlResponse = await response.json()
      setResult(data)

      if (!data.success) {
        setError(data.message)
      } else if (data.store?.category) {
        // 자동 카테고리 매핑 시도
        autoSelectCategory(data.store.category)
      }
    } catch {
      setError('서버 연결에 실패했습니다. 백엔드 서버가 실행 중인지 확인해주세요.')
    } finally {
      setLoading(false)
    }
  }

  const autoSelectCategory = (naverCategory: string) => {
    const categoryMap: Record<string, string> = {
      '치킨': 'chicken',
      '피자': 'pizza',
      '한식': 'korean',
      '중식': 'chinese',
      '중국': 'chinese',
      '일식': 'japanese',
      '일본': 'japanese',
      '양식': 'western',
      '분식': 'snack',
      '카페': 'cafe',
      '디저트': 'cafe',
      '패스트푸드': 'fastfood',
      '햄버거': 'fastfood',
    }
    
    for (const [key, value] of Object.entries(categoryMap)) {
      if (naverCategory.includes(key)) {
        setSelectedCategory(value)
        return
      }
    }
  }

  const handleOnboard = async () => {
    if (!result?.store) return

    if (!selectedCategory) {
      setError('카테고리를 선택해주세요.')
      return
    }

    setLoading(true)
    setError(null)

    try {
      const response = await fetch(`${API_BASE_URL}/api/onboard`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          store: result.store,
          business_number: businessNumber || null,
          category_mapping: selectedCategory,
        }),
      })

      const data: OnboardResponse = await response.json()
      setOnboardResult(data)

      if (data.success) {
        setViewMode('preview')
      } else {
        setError(data.message)
      }
    } catch {
      setError('온보딩 중 오류가 발생했습니다.')
    } finally {
      setLoading(false)
    }
  }

  const formatPrice = (price: number) => {
    return new Intl.NumberFormat('ko-KR').format(price) + '원'
  }

  const resetForm = () => {
    setNaverMapUrl('')
    setBusinessNumber('')
    setSelectedCategory('')
    setResult(null)
    setOnboardResult(null)
    setError(null)
    setViewMode('result')
  }

  // ==================== Render ====================

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-100">
        <div className="max-w-6xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-vroong-blue rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-lg">V</span>
              </div>
              <div>
                <h1 className="text-xl font-bold text-gray-900">부릉 영업사원 도구</h1>
                <p className="text-sm text-gray-500">상점 온보딩 시스템 v2.0</p>
              </div>
            </div>
            {(result || onboardResult) && (
              <button
                onClick={resetForm}
                className="px-4 py-2 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
              >
                🔄 새로 시작
              </button>
            )}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-6xl mx-auto px-4 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          
          {/* ==================== Input Section ==================== */}
          <div className="card">
            <h2 className="text-lg font-semibold text-gray-900 mb-6">
              📍 상점 정보 입력
            </h2>
            
            <div className="space-y-4">
              {/* 네이버 지도 URL */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  네이버 지도 URL <span className="text-red-500">*</span>
                </label>
                <input
                  type="url"
                  className="input-field"
                  placeholder="https://map.naver.com/p/entry/place/..."
                  value={naverMapUrl}
                  onChange={(e) => setNaverMapUrl(e.target.value)}
                  disabled={loading}
                />
                <p className="text-xs text-gray-500 mt-1">
                  네이버 지도에서 상점을 검색한 후 URL을 복사해주세요.
                </p>
              </div>
              
              {/* 사업자등록번호 */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  사업자등록번호 (선택)
                </label>
                <input
                  type="text"
                  className="input-field"
                  placeholder="000-00-00000"
                  value={businessNumber}
                  onChange={(e) => setBusinessNumber(e.target.value)}
                  disabled={loading}
                />
              </div>

              {/* 카테고리 선택 (크롤링 후 표시) */}
              {result?.store && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    부릉 카테고리 <span className="text-red-500">*</span>
                  </label>
                  <div className="grid grid-cols-3 gap-2">
                    {categories.map((cat) => (
                      <button
                        key={cat.value}
                        type="button"
                        onClick={() => setSelectedCategory(cat.value)}
                        className={`p-3 rounded-lg border-2 text-center transition-all ${
                          selectedCategory === cat.value
                            ? 'border-vroong-blue bg-blue-50 text-vroong-blue'
                            : 'border-gray-200 hover:border-gray-300'
                        }`}
                      >
                        <span className="text-xl">{cat.emoji}</span>
                        <span className="block text-xs mt-1">{cat.label}</span>
                      </button>
                    ))}
                  </div>
                  {result.store.category && (
                    <p className="text-xs text-gray-500 mt-2">
                      네이버 카테고리: {result.store.category}
                    </p>
                  )}
                </div>
              )}
              
              {/* 크롤링 버튼 */}
              {!result?.store ? (
                <button
                  className="btn-primary w-full flex items-center justify-center gap-2"
                  onClick={handleCrawl}
                  disabled={loading}
                >
                  {loading ? (
                    <>
                      <LoadingSpinner />
                      크롤링 중...
                    </>
                  ) : (
                    <>🔍 상점 정보 가져오기</>
                  )}
                </button>
              ) : (
                <button
                  className="btn-primary w-full flex items-center justify-center gap-2"
                  onClick={handleOnboard}
                  disabled={loading || !selectedCategory}
                >
                  {loading ? (
                    <>
                      <LoadingSpinner />
                      등록 중...
                    </>
                  ) : (
                    <>✅ 부릉에 등록하기</>
                  )}
                </button>
              )}

              {/* 에러 메시지 */}
              {error && (
                <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
                  <p className="text-sm text-red-600">❌ {error}</p>
                </div>
              )}

              {/* 성공 메시지 */}
              {onboardResult?.success && (
                <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
                  <p className="text-sm text-green-600 font-medium">
                    ✅ {onboardResult.message}
                  </p>
                  <p className="text-xs text-green-500 mt-1">
                    등록된 메뉴: {onboardResult.menu_count}개
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* ==================== Result Section ==================== */}
          <div className="card">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-semibold text-gray-900">
                {viewMode === 'result' ? '📋 크롤링 결과' : '👀 미리보기'}
              </h2>
              {result?.store && (
                <div className="flex gap-2">
                  <button
                    onClick={() => setViewMode('result')}
                    className={`px-3 py-1 text-sm rounded-lg transition-colors ${
                      viewMode === 'result' 
                        ? 'bg-vroong-blue text-white' 
                        : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    }`}
                  >
                    데이터
                  </button>
                  <button
                    onClick={() => setViewMode('preview')}
                    className={`px-3 py-1 text-sm rounded-lg transition-colors ${
                      viewMode === 'preview' 
                        ? 'bg-vroong-blue text-white' 
                        : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    }`}
                  >
                    미리보기
                  </button>
                </div>
              )}
            </div>
            
            {!result?.store ? (
              <div className="text-center py-12 text-gray-400">
                <div className="text-5xl mb-4">🏪</div>
                <p>상점 정보를 가져오면 여기에 표시됩니다.</p>
              </div>
            ) : viewMode === 'result' ? (
              <ResultView store={result.store} formatPrice={formatPrice} />
            ) : (
              <PreviewView 
                store={result.store} 
                formatPrice={formatPrice}
                category={selectedCategory}
                categories={categories}
              />
            )}
          </div>
        </div>

        {/* ==================== Instructions ==================== */}
        <div className="mt-8 card">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            📖 사용 방법
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <StepCard step={1} title="네이버 지도 검색" desc="등록하려는 상점을 네이버 지도에서 검색하고 URL을 복사합니다." />
            <StepCard step={2} title="정보 가져오기" desc="URL을 입력하고 '상점 정보 가져오기' 버튼을 클릭합니다." />
            <StepCard step={3} title="카테고리 선택" desc="부릉에서 사용할 카테고리를 선택합니다." />
            <StepCard step={4} title="부릉에 등록" desc="크롤링된 정보를 확인하고 등록 버튼을 클릭합니다." />
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-200 mt-12 py-6">
        <p className="text-center text-sm text-gray-500">
          © 2026 부릉(Vroong). 영업사원 전용 도구
        </p>
      </footer>
    </div>
  )
}


// ==================== Sub Components ====================

function LoadingSpinner() {
  return (
    <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
    </svg>
  )
}

function StepCard({ step, title, desc }: { step: number; title: string; desc: string }) {
  return (
    <div className="text-center">
      <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-3">
        <span className="text-2xl">{step}️⃣</span>
      </div>
      <h4 className="font-medium text-gray-900">{title}</h4>
      <p className="text-sm text-gray-500 mt-1">{desc}</p>
    </div>
  )
}

function ResultView({ store, formatPrice }: { store: StoreInfo; formatPrice: (p: number) => string }) {
  return (
    <div className="space-y-6">
      {/* Store Info */}
      <div className="flex gap-4">
        {store.image_url && (
          <img 
            src={store.image_url} 
            alt={store.name}
            className="w-24 h-24 object-cover rounded-lg"
          />
        )}
        <div className="flex-1">
          <h3 className="text-xl font-bold text-gray-900">{store.name}</h3>
          {store.category && (
            <span className="inline-block px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded-full mt-1">
              {store.category}
            </span>
          )}
          <p className="text-sm text-gray-600 mt-2">📍 {store.address}</p>
          {store.phone && <p className="text-sm text-gray-600">📞 {store.phone}</p>}
        </div>
      </div>

      {/* Menu List */}
      {store.menus.length > 0 && (
        <div>
          <h4 className="font-semibold text-gray-900 mb-3">
            🍽️ 메뉴 ({store.menus.length}개)
          </h4>
          <div className="max-h-64 overflow-y-auto space-y-2">
            {store.menus.map((menu, idx) => (
              <div key={idx} className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                <div className="flex items-center gap-3">
                  {menu.image_url && (
                    <img src={menu.image_url} alt={menu.name} className="w-12 h-12 object-cover rounded" />
                  )}
                  <div>
                    <p className="font-medium text-gray-900">{menu.name}</p>
                    {menu.description && <p className="text-xs text-gray-500">{menu.description}</p>}
                  </div>
                </div>
                <span className="font-semibold text-vroong-blue">{formatPrice(menu.price)}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function PreviewView({ 
  store, 
  formatPrice, 
  category,
  categories 
}: { 
  store: StoreInfo; 
  formatPrice: (p: number) => string;
  category: string;
  categories: Category[];
}) {
  const categoryInfo = categories.find(c => c.value === category)
  
  return (
    <div className="space-y-4">
      {/* Preview Header */}
      <div className="bg-gradient-to-r from-teal-500 to-teal-600 text-white p-4 rounded-lg">
        <p className="text-xs opacity-80">부릉 직접주문 미리보기</p>
        <h3 className="text-lg font-bold">{store.name}</h3>
        <div className="flex items-center gap-2 mt-1">
          {categoryInfo && (
            <span className="text-sm bg-white/20 px-2 py-0.5 rounded">
              {categoryInfo.emoji} {categoryInfo.label}
            </span>
          )}
          <span className="text-sm">⭐ 4.5</span>
        </div>
      </div>

      {/* Preview Store Card */}
      <div className="border border-gray-200 rounded-lg overflow-hidden">
        {store.image_url && (
          <img src={store.image_url} alt={store.name} className="w-full h-32 object-cover" />
        )}
        <div className="p-3">
          <p className="text-xs text-gray-500">📍 {store.address}</p>
          {store.phone && (
            <p className="text-xs text-teal-600 mt-1">📞 {store.phone}</p>
          )}
        </div>
      </div>

      {/* Preview Menu Cards */}
      <div>
        <h4 className="font-medium text-gray-900 mb-2">메뉴 미리보기</h4>
        <div className="space-y-2 max-h-48 overflow-y-auto">
          {store.menus.slice(0, 5).map((menu, idx) => (
            <div key={idx} className="flex gap-3 p-2 bg-white border border-gray-100 rounded-lg shadow-sm">
              {menu.image_url ? (
                <img src={menu.image_url} alt={menu.name} className="w-16 h-16 object-cover rounded" />
              ) : (
                <div className="w-16 h-16 bg-gray-100 rounded flex items-center justify-center text-2xl">
                  {categoryInfo?.emoji || '🍽️'}
                </div>
              )}
              <div className="flex-1">
                <p className="font-medium text-gray-900 text-sm">{menu.name}</p>
                <p className="text-xs text-gray-400 line-through">{formatPrice(Math.floor(menu.price * 1.15))}</p>
                <p className="text-sm font-bold text-teal-600">{formatPrice(menu.price)}</p>
              </div>
              <span className="text-xs text-red-500 font-medium">-15%</span>
            </div>
          ))}
        </div>
        {store.menus.length > 5 && (
          <p className="text-xs text-gray-400 text-center mt-2">
            +{store.menus.length - 5}개 메뉴 더 있음
          </p>
        )}
      </div>
    </div>
  )
}

export default App
