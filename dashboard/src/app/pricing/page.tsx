"use client";

import { Nav } from "@/components/nav";
import { CreditCard, ShoppingCart, MapPin, FileText } from "lucide-react";

const plans = [
  {
    name: "Basic", sub: "소규모 업체 · 테스트", price: "30", color: "#e0e0e0", best: false,
    features: [
      { label: "캠페인 타입", val: "1종 선택" }, { label: "키워드", val: "3개" },
      { label: "일일 트래픽", val: "~300회" }, { label: "월간 트래픽", val: "~9,000회" },
      { label: "페르소나 엔진", val: "포함 (무료)" }, { label: "리포트", val: "월 1회" },
      { label: "시간 전략", val: "자동 배분" },
    ],
    costLine: "원가 (0.5원/회) ~4,500원", margin: "마진 ~295,500원 (99%)",
  },
  {
    name: "Standard ★", sub: "일반 마케팅 대행", price: "70", color: "#00e676", best: true,
    features: [
      { label: "캠페인 타입", val: "2종 (쇼핑+플레이스 or 블로그)" }, { label: "키워드", val: "10개" },
      { label: "일일 트래픽", val: "~1,500회" }, { label: "월간 트래픽", val: "~45,000회" },
      { label: "페르소나 엔진", val: "포함 (무료)" }, { label: "리포트", val: "주 1회" },
      { label: "시간 전략", val: "자동 + 커스텀" }, { label: "순위 추적", val: "포함" },
    ],
    costLine: "원가 (0.5원/회) ~22,500원", margin: "마진 ~677,500원 (97%)",
  },
  {
    name: "Premium", sub: "대형 업체 · 에이전시", price: "150", color: "#e0e0e0", best: false,
    features: [
      { label: "캠페인 타입", val: "전체 (쇼핑+플레이스+블로그)" }, { label: "키워드", val: "30개" },
      { label: "일일 트래픽", val: "~5,000회" }, { label: "월간 트래픽", val: "~150,000회" },
      { label: "페르소나 엔진", val: "포함 (무료)" }, { label: "리포트", val: "일간 자동" },
      { label: "시간 전략", val: "풀 커스텀" }, { label: "전략 컨설팅", val: "키워드 추천" },
    ],
    costLine: "원가 (0.5원/회) ~75,000원", margin: "마진 ~1,425,000원 (95%)",
  },
];

const commonOptions = [
  { num: 1, name: "모바일 트래픽", price: "+10만", icon: "📱", desc: "PC:모바일 30:70 자동 배분. 실제 유입 비율 정상화.", tag: "탐지 방지", color: "#ff6eb4" },
  { num: 2, name: "다중 키워드 유입", price: "+15만", icon: "🔎", desc: "5~10개 다른 키워드로 분산 유입. 키워드 다양성 시그널.", tag: "키워드 확장", color: "#8b6cff" },
  { num: 3, name: "지역 타겟팅", price: "+10만", icon: "📍", desc: "업체 소재지 기준 IP 분산. Residential 프록시 지역 지정.", tag: "L3 Anti-Detection", color: "#448aff" },
  { num: 4, name: "점진적 증가 모드", price: "+5만", icon: "🚀", desc: "1주차 100 → 2주차 200 → 3주차 300으로 서서히 증가.", tag: "안전 모드", color: "#ff9052" },
  { num: 5, name: "경쟁업체 비교 클릭", price: "+10만", icon: "🔍", desc: "경쟁 2~3곳도 클릭 후 고객 업체 최종 선택 패턴.", tag: "L1 Anti-Detection", color: "#8b6cff" },
  { num: 6, name: "스크린샷 증빙", price: "+10만", icon: "📷", desc: "매일 검색 결과 + 클릭 후 페이지 자동 캡처.", tag: "고객 신뢰", color: "#00e676" },
  { num: 7, name: "스크린샷 리포트", price: "+15만", icon: "📊", desc: "캡처 + 순위 변동 + 트래픽 통계 자동 보고서.", tag: "프리미엄 리포트", color: "#00e676" },
];

const shoppingOptions = [
  { num: 8, name: "찜(위시) 클릭", price: "+10만", icon: "❤️", desc: "상품 찜 버튼 클릭. 관심도 지표 상승.", tag: "순위 영향", color: "#ff5252" },
  { num: 9, name: "장바구니 담기", price: "+10만", icon: "🛒", desc: "장바구니 추가 시뮬. 구매 의향 시그널.", tag: "순위 영향", color: "#ff9052" },
  { num: 10, name: "리뷰 정독 체류", price: "+8만", icon: "⭐", desc: "리뷰 탭 이동 + 스크롤 + 30~60초 체류.", tag: "체류 시간", color: "#ffd740" },
  { num: 11, name: "비교 행동 시뮬", price: "+8만", icon: "🔄", desc: "유사 상품 탭 전환 비교 후 타겟 상품 선택.", tag: "자연스러움", color: "#448aff" },
  { num: 12, name: "카테고리 경유 유입", price: "+10만", icon: "📂", desc: "카테고리 탐색 → 타겟 상품 발견 경로.", tag: "경로 다양화", color: "#8b6cff" },
  { num: 13, name: "스토어 탐색", price: "+8만", icon: "🏪", desc: "스토어 홈 → 다른 상품 → 타겟 상품 브라우징.", tag: "스토어 신뢰", color: "#00e676" },
  { num: 14, name: "정렬/필터 사용", price: "+5만", icon: "⚙️", desc: "가격순/인기순 정렬, 필터 적용 후 탐색.", tag: "UI 인터랙션", color: "#448aff" },
  { num: 15, name: "재방문 시뮬", price: "+10만", icon: "🔁", desc: "쿠키 저장 후 1~3일 뒤 재방문 시뮬레이션.", tag: "재방문율", color: "#ff6eb4" },
  { num: 16, name: "가격비교 탐색", price: "+8만", icon: "💰", desc: "네이버 가격비교 탭 이동 + 탐색 후 복귀.", tag: "가격 시그널", color: "#ffd740" },
  { num: 17, name: "상품문의 클릭", price: "+8만", icon: "💬", desc: "상품 문의 폼 진입. 구매 의향 고시그널.", tag: "전환 시그널", color: "#ff9052" },
];

const placeOptions = [
  { num: 18, name: "전환 시뮬레이션", price: "+15만", icon: "📞", desc: "전화/길찾기/리뷰 클릭을 업종 평균 전환율에 맞춰 시뮬.", tag: "L2 Anti-Detection", color: "#ff9052" },
  { num: 19, name: "저장 클릭", price: "+10만", icon: "🔗", desc: "플레이스 저장 버튼 클릭. 관심도 핵심 지표.", tag: "순위 영향 큼", color: "#ffd740" },
  { num: 20, name: "네이버 지도 유입", price: "+10만", icon: "🗺️", desc: "지도에서 직접 검색 → 업체 클릭 경로.", tag: "경로 다양화", color: "#00e676" },
];

const blogOptions = [
  { num: 21, name: "공감 클릭", price: "+8만", icon: "👍", desc: "블로그 글 하단 공감 버튼 클릭.", tag: "인게이지먼트", color: "#ff6eb4" },
  { num: 22, name: "댓글 체류", price: "+8만", icon: "💭", desc: "댓글 영역 스크롤 + 읽기 체류.", tag: "체류 시간", color: "#8b6cff" },
  { num: 23, name: "시리즈 탐색", price: "+10만", icon: "📚", desc: "같은 블로그 다른 글 1~2개 추가 방문.", tag: "블로그 신뢰", color: "#448aff" },
];

const eventOptions = [
  { num: 24, name: "이벤트 부스팅", price: "+5만/회", icon: "⚡", desc: "특정 날짜 2~3배 집중 투입.", tag: "시즌 마케팅", color: "#ffd740" },
  { num: 25, name: "시즌 캠페인", price: "+10만/회", icon: "🎯", desc: "특정 기간 집중 + 전후 비교 리포트.", tag: "캠페인", color: "#ff9052" },
];

const combos = [
  { scenario: "쇼핑 Basic 최소", config: "Basic + 모바일", price: "40만", margin: "~40만 (100%)", type: "🛒" },
  { scenario: "쇼핑 Standard 인기", config: "Standard + 찜+장바구니+리뷰정독+모바일+스크린샷", price: "116만", margin: "~115만 (99%)", type: "🛒" },
  { scenario: "쇼핑 풀옵션 ★", config: "Standard + 쇼핑10종+공통5종", price: "200만", margin: "~199만 (99%)", type: "🛒", best: true },
  { scenario: "플레이스 Standard", config: "Standard + 전환+저장+지도+모바일+지역", price: "125만", margin: "~120만 (96%)", type: "📍" },
  { scenario: "블로그 Basic", config: "Basic + 공감+댓글체류+다중키워드", price: "61만", margin: "~61만 (100%)", type: "📝" },
  { scenario: "블로그 Standard", config: "Standard + 블로그3종+모바일+스크린샷", price: "116만", margin: "~115만 (99%)", type: "📝" },
  { scenario: "복합 Premium", config: "Premium + 쇼핑5종+플레이스3종+블로그2종+공통3종", price: "293만", margin: "~287만 (98%)", type: "🏢" },
  { scenario: "에이전시 Premium", config: "Premium × 3계정 + 각 타입별 풀옵션", price: "~800만", margin: "~790만 (99%)", type: "🏢" },
];

function OptionCard({ o, size = "sm" }: { o: typeof commonOptions[0]; size?: "sm" | "lg" }) {
  if (size === "lg") {
    return (
      <div className="rounded-xl border bg-[#111127] p-5" style={{ borderColor: `${o.color}40` }}>
        <div className="mb-2 flex items-center justify-between">
          <h3 className="font-bold text-white">{o.icon} {o.name}</h3>
          <span className="text-xl font-black" style={{ color: o.color }}>{o.price}</span>
        </div>
        <p className="mb-2 text-xs text-[#8888aa]">{o.desc}</p>
        <span className="rounded-full px-2 py-0.5 text-[10px] font-bold" style={{ color: o.color, background: `${o.color}15` }}>{o.tag}</span>
      </div>
    );
  }
  return (
    <div className="rounded-xl border bg-[#111127] p-3" style={{ borderColor: `${o.color}25` }}>
      <div className="mb-1 flex items-center justify-between">
        <span className="text-base">{o.icon}</span>
        <span className="text-sm font-black" style={{ color: o.color }}>{o.price}</span>
      </div>
      <h3 className="text-xs font-bold text-white">{o.name}</h3>
      <p className="mt-0.5 text-[10px] text-[#8888aa] line-clamp-2">{o.desc}</p>
      <span className="mt-1 inline-block rounded-full px-1.5 py-0.5 text-[9px] font-bold" style={{ color: o.color, background: `${o.color}15` }}>{o.tag}</span>
    </div>
  );
}

export default function PricingPage() {
  return (
    <>
      <Nav />
      <main className="mx-auto max-w-7xl px-4 pt-20 pb-12">
        <div className="mb-2">
          <p className="text-xs font-bold uppercase tracking-widest text-[#8b6cff]">Service Plans</p>
          <h1 className="text-2xl font-bold text-white">고객 요금제 (안)</h1>
          <p className="text-sm text-[#8888aa]">기본 요금 + 25종 유료 옵션 업셀 구조 · 페르소나 엔진 기본 포함</p>
        </div>

        {/* Plans */}
        <div className="mt-6 grid gap-4 md:grid-cols-3">
          {plans.map((p) => (
            <div key={p.name} className={`rounded-xl border p-6 ${p.best ? "border-[#00e676]/50 bg-[#00e676]/[0.03]" : "border-[#2a2a5a] bg-[#111127]"}`}>
              <div className="text-lg font-extrabold" style={{ color: p.color }}>{p.name}</div>
              <div className="text-xs text-[#8888aa]">{p.sub}</div>
              <div className="my-3">
                <span className="text-4xl font-black" style={{ color: p.color }}>{p.price}</span>
                <span className="text-sm text-[#8888aa]">만원/월</span>
              </div>
              <div className="space-y-1.5">
                {p.features.map((f) => (
                  <div key={f.label} className="flex justify-between text-xs">
                    <span className="text-[#8888aa]">{f.label}</span>
                    <span className="text-[#e0e0e0]">{f.val}</span>
                  </div>
                ))}
                <div className="flex justify-between border-t border-[#2a2a5a] pt-1.5 text-xs font-bold">
                  <span className="text-[#8888aa]">{p.costLine.split(")")[0]})</span>
                  <span className="text-white">{p.costLine.split(") ")[1]}</span>
                </div>
              </div>
              <div className="mt-3 rounded-lg bg-[#00e676]/10 p-2 text-center text-xs font-bold text-[#00e676]">{p.margin}</div>
            </div>
          ))}
        </div>

        {/* Free included */}
        <div className="mt-6 rounded-xl border border-[#00e676]/30 bg-[#00e676]/[0.03] p-4">
          <h3 className="text-sm font-bold text-[#00e676]">모든 요금제에 무료 포함</h3>
          <div className="mt-2 grid grid-cols-2 gap-2 md:grid-cols-4">
            {["페르소나 엔진 (16개 성격 특성)", "3-Phase 세션 (워밍업→메인→마무리)", "한국 시간대 가중치 분배", "undetected-chromedriver 탐지 우회"].map((f) => (
              <div key={f} className="rounded-lg bg-[#00e676]/10 p-2 text-center text-[10px] font-medium text-[#00e676]">{f}</div>
            ))}
          </div>
        </div>

        {/* Common Options */}
        <div className="mt-10 flex items-center gap-2">
          <CreditCard className="h-5 w-5 text-[#448aff]" />
          <h2 className="text-lg font-extrabold text-white">공통 유료 옵션 (7종)</h2>
        </div>
        <p className="mt-1 mb-4 text-sm text-[#8888aa]">모든 캠페인 타입 (쇼핑/플레이스/블로그)에 적용 가능한 옵션</p>
        <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-4">
          {commonOptions.map((o) => <OptionCard key={o.num} o={o} />)}
        </div>

        {/* Shopping Options */}
        <div className="mt-8 flex items-center gap-2">
          <ShoppingCart className="h-5 w-5 text-[#ff9052]" />
          <h2 className="text-lg font-extrabold text-white">쇼핑 전용 옵션 (10종)</h2>
        </div>
        <p className="mt-1 mb-4 text-sm text-[#8888aa]">네이버 쇼핑 순위에 영향을 주는 전환 행동 시뮬레이션</p>
        <div className="grid gap-3 md:grid-cols-3 lg:grid-cols-5">
          {shoppingOptions.map((o) => <OptionCard key={o.num} o={o} />)}
        </div>

        {/* Place Options */}
        <div className="mt-8 flex items-center gap-2">
          <MapPin className="h-5 w-5 text-[#00e676]" />
          <h2 className="text-lg font-extrabold text-white">플레이스 전용 옵션 (3종)</h2>
        </div>
        <p className="mt-1 mb-4 text-sm text-[#8888aa]">네이버 플레이스/지도 순위에 영향을 주는 핵심 행동</p>
        <div className="grid gap-3 md:grid-cols-3">
          {placeOptions.map((o) => <OptionCard key={o.num} o={o} size="lg" />)}
        </div>

        {/* Blog Options */}
        <div className="mt-8 flex items-center gap-2">
          <FileText className="h-5 w-5 text-[#8b6cff]" />
          <h2 className="text-lg font-extrabold text-white">블로그 전용 옵션 (3종)</h2>
        </div>
        <p className="mt-1 mb-4 text-sm text-[#8888aa]">검색 CTR + 체류 시간 시그널을 강화하는 블로그 행동</p>
        <div className="grid gap-3 md:grid-cols-3">
          {blogOptions.map((o) => <OptionCard key={o.num} o={o} size="lg" />)}
        </div>

        {/* Event Options */}
        <div className="mt-8">
          <h3 className="text-base font-extrabold text-white">이벤트 옵션 (2종)</h3>
          <div className="mt-3 grid gap-3 md:grid-cols-2">
            {eventOptions.map((o) => <OptionCard key={o.num} o={o} size="lg" />)}
          </div>
        </div>

        {/* Summary Table */}
        <div className="mt-8 rounded-xl border border-[#2a2a5a] bg-[#111127] p-5">
          <h3 className="mb-3 font-bold text-white">전체 옵션 한눈에 보기 (25종)</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead><tr className="border-b border-[#2a2a5a] text-left text-[10px] uppercase text-[#8888aa]"><th className="pb-2">#</th><th className="pb-2">옵션명</th><th className="pb-2">가격</th><th className="pb-2">대상</th><th className="pb-2">태그</th></tr></thead>
              <tbody>
                {[
                  ...commonOptions.map((o) => ({ ...o, target: "전체" })),
                  ...shoppingOptions.map((o) => ({ ...o, target: "쇼핑" })),
                  ...placeOptions.map((o) => ({ ...o, target: "플레이스" })),
                  ...blogOptions.map((o) => ({ ...o, target: "블로그" })),
                  ...eventOptions.map((o) => ({ ...o, target: "이벤트" })),
                ].map((o) => (
                  <tr key={o.num} className="border-b border-[#2a2a5a]/30">
                    <td className="py-1.5 text-[#8888aa]">{o.num}</td>
                    <td className="py-1.5 font-medium text-white">{o.icon} {o.name}</td>
                    <td className="py-1.5 font-mono font-bold" style={{ color: o.color }}>{o.price}</td>
                    <td className="py-1.5"><span className="rounded bg-[#16163a] px-1.5 py-0.5 text-[9px] text-[#8888aa]">{o.target}</span></td>
                    <td className="py-1.5"><span className="rounded-full px-1.5 py-0.5 text-[9px] font-bold" style={{ color: o.color, background: `${o.color}15` }}>{o.tag}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Combo Scenarios */}
        <div className="mt-8 rounded-xl border border-[#00e676]/30 bg-[#00e676]/[0.03] p-6">
          <h3 className="mb-4 font-extrabold text-white">요금 조합 시나리오</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead><tr className="border-b border-[#2a2a5a] text-left text-xs uppercase text-[#8888aa]"><th className="pb-2">타입</th><th className="pb-2">시나리오</th><th className="pb-2">구성</th><th className="pb-2">월 요금</th><th className="pb-2">예상 마진</th></tr></thead>
              <tbody>
                {combos.map((c) => (
                  <tr key={c.scenario} className={`border-b border-[#2a2a5a]/50 ${c.best ? "bg-[#00e676]/[0.04]" : ""}`}>
                    <td className="py-2.5 text-base">{c.type}</td>
                    <td className={`py-2.5 font-medium ${c.best ? "text-[#00e676]" : "text-white"}`}>{c.scenario}</td>
                    <td className="py-2.5 text-xs text-[#e0e0e0]">{c.config}</td>
                    <td className="py-2.5 font-mono font-bold text-white">{c.price}</td>
                    <td className="py-2.5 font-mono text-[#00e676]">{c.margin}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mt-4 rounded-lg border border-[#00e676]/20 bg-[#00e676]/10 p-3 text-xs text-[#00e676]">
            <strong>업셀 전략:</strong> Basic(30만)으로 시작한 고객에게 &quot;모바일 안 넣으면 네이버가 이상하게 봅니다&quot; → +10만. &quot;찜/장바구니 안 누르면 순위에 영향 없어요&quot; → +20만. &quot;리포트 보실래요?&quot; → +15만. 자연스럽게 30만 → 75~120만으로 객단가 상승. 옵션 원가 대부분 0원이므로 업셀 = 순수익.
          </div>
        </div>
      </main>
    </>
  );
}
