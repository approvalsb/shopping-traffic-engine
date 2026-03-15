"use client";

import { Nav } from "@/components/nav";
import { Server, TrendingUp, Calculator } from "lucide-react";

const proxyConfigs = [
  { name: "PC 1대 (로컬)", sub: "지금 민서님 PC로 바로 가능", cost: "~13원", color: "#ff9052", monthly: "~230,000원", daily: "600회", monthlyVol: "18,000회", breakdown: [{ label: "VPS 비용", val: "0원" }, { label: "프록시 (Residential)", val: "~200,000원/월" }, { label: "전기/인터넷", val: "~30,000원/월" }], highlight: "230,000 ÷ 18,000 = 약 12.8원/회", best: false },
  { name: "VPS 3대", sub: "가성비 최적 구성 ★", cost: "~5원", color: "#00e676", monthly: "~610,000원", daily: "5,000회", monthlyVol: "150,000회", breakdown: [{ label: "VPS 비용 (3 × $20)", val: "~80,000원/월" }, { label: "프록시 (Residential)", val: "~500,000원/월" }, { label: "Master 서버", val: "~30,000원/월" }], highlight: "610,000 ÷ 150,000 = 약 4.1원/회", best: true },
  { name: "VPS 10대", sub: "대규모 에이전시 구성", cost: "~4원", color: "#8b6cff", monthly: "~3,800,000원", daily: "30,000회", monthlyVol: "900,000회", breakdown: [{ label: "VPS 비용 (10 × $20)", val: "~270,000원/월" }, { label: "프록시 (Residential)", val: "~3,500,000원/월" }, { label: "Master 서버", val: "~30,000원/월" }], highlight: "3,800,000 ÷ 900,000 = 약 4.2원/회", best: false },
];

const noProxyConfigs = [
  { name: "PC 1대", cost: "~1.7원", color: "#ffd740", vol: "18,000회", expense: "전기세만 (~30,000원)", risk: "IP 1개 = 위험" },
  { name: "VPS 3대", cost: "~0.7원", color: "#ffd740", vol: "150,000회", expense: "VPS만 (~110,000원)", risk: "IP 3개 = 보통" },
  { name: "VPS 10대", cost: "~0.3원", color: "#ffd740", vol: "900,000회", expense: "VPS만 (~300,000원)", risk: "IP 10개 = 매우 안전" },
];

const vpsComparison = [
  { item: "IP 분산", pc: { val: "1개 (집 IP 고정)", color: "#ff5252" }, vps3: { val: "3개 (자연 분산)", color: "#ffd740" }, vps5: { val: "5개 (충분한 분산)", color: "#00e676" } },
  { item: "지역 분산", pc: { val: "1곳 고정", color: "#ff5252" }, vps3: { val: "서울/부산/대전", color: "#ffd740" }, vps5: { val: "서울/부산/대전/인천/대구", color: "#00e676" } },
  { item: "가동 시간", pc: { val: "PC 켜둬야 함 (12~16시간)", color: "#ff5252" }, vps3: { val: "24시간 무중단", color: "#00e676" }, vps5: { val: "24시간 무중단", color: "#00e676" } },
  { item: "새벽 트래픽", pc: { val: "불가 (PC 꺼짐)", color: "#ff5252" }, vps3: { val: "소량 투입 → 자연스러운 24h", color: "#00e676" }, vps5: { val: "소량 투입 → 자연스러운 24h", color: "#00e676" } },
  { item: "안정성", pc: { val: "윈도우 업데이트/재부팅 중단", color: "#ffd740" }, vps3: { val: "서버급 안정성", color: "#00e676" }, vps5: { val: "서버급 안정성", color: "#00e676" } },
  { item: "IP당 일일 부하", pc: { val: "600회/IP ← 위험", color: "#ff5252" }, vps3: { val: "~1,700회/IP", color: "#ffd740" }, vps5: { val: "~1,700회/IP", color: "#00e676" } },
  { item: "프록시 필요성", pc: { val: "거의 필수", color: "#ff5252" }, vps3: { val: "선택적", color: "#ffd740" }, vps5: { val: "없어도 운영 가능", color: "#00e676" } },
  { item: "Layer 3 (지역 타겟팅)", pc: { val: "프록시 없이 불가", color: "#ff5252" }, vps3: { val: "3개 지역 자동 커버", color: "#ffd740" }, vps5: { val: "5개 지역 자동 커버", color: "#00e676" } },
];

const roadmap = [
  { stage: "START", color: "#00e676", config: "VPS 3대 (프록시 없음)", detail: "서울/부산/대전 리전", cost: "~0.5원", safety: "IP 3개 분산 + 3개 지역", monthly: "~8만원", when: "지금 즉시" },
  { stage: "SCALE", color: "#ff9052", config: "VPS 5대 (프록시 없음)", detail: "+인천/대구 추가", cost: "~0.5원", safety: "IP 5개 + 5개 지역", monthly: "~14만원", when: "고객 5명 이상" },
  { stage: "PRO", color: "#8b6cff", config: "VPS 5대 + 프록시", detail: "지역 타겟팅 옵션 고객용", cost: "~3.7원", safety: "IP 수백개 + 정밀 지역", monthly: "~94만원", when: "유료 옵션 고객 있을 때" },
];

const optionCosts = [
  { cat: "공통 옵션 (7종)", color: "#448aff", items: [
    { name: "모바일 트래픽", price: "+10만", ourCost: "~0원", margin: "100%", note: "UA 변경만 (비용 없음)" },
    { name: "다중 키워드 유입", price: "+15만", ourCost: "~0원", margin: "100%", note: "키워드 추가 (비용 없음)" },
    { name: "지역 타겟팅", price: "+10만", ourCost: "~5만원", margin: "50%", note: "Residential 프록시 비용" },
    { name: "점진적 증가 모드", price: "+5만", ourCost: "~0원", margin: "100%", note: "스케줄 조절 (비용 없음)" },
    { name: "경쟁업체 비교 클릭", price: "+10만", ourCost: "~1만원", margin: "90%", note: "추가 트래픽 소량" },
    { name: "스크린샷 증빙", price: "+10만", ourCost: "~0원", margin: "100%", note: "자동 캡처 (비용 없음)" },
    { name: "스크린샷 리포트", price: "+15만", ourCost: "~0원", margin: "100%", note: "자동 보고서 생성" },
  ]},
  { cat: "쇼핑 전용 옵션 (10종)", color: "#ff9052", items: [
    { name: "찜(위시) 클릭", price: "+10만", ourCost: "~0원", margin: "100%", note: "클릭 시뮬레이션" },
    { name: "장바구니 담기", price: "+10만", ourCost: "~0원", margin: "100%", note: "클릭 시뮬레이션" },
    { name: "리뷰 정독 체류", price: "+8만", ourCost: "~0원", margin: "100%", note: "스크롤+체류 시간" },
    { name: "비교 행동 시뮬", price: "+8만", ourCost: "~0원", margin: "100%", note: "탭 전환 시뮬레이션" },
    { name: "카테고리 경유 유입", price: "+10만", ourCost: "~0원", margin: "100%", note: "경로 변경" },
    { name: "스토어 탐색", price: "+8만", ourCost: "~0원", margin: "100%", note: "스토어 내 브라우징" },
    { name: "정렬/필터 사용", price: "+5만", ourCost: "~0원", margin: "100%", note: "UI 인터랙션" },
    { name: "재방문 시뮬", price: "+10만", ourCost: "~1만원", margin: "90%", note: "쿠키 저장 후 재방문" },
    { name: "가격비교 탐색", price: "+8만", ourCost: "~0원", margin: "100%", note: "가격비교 탭 이동" },
    { name: "상품문의 클릭", price: "+8만", ourCost: "~0원", margin: "100%", note: "문의 폼 진입" },
  ]},
  { cat: "플레이스 전용 옵션 (3종)", color: "#00e676", items: [
    { name: "전환 시뮬레이션", price: "+15만", ourCost: "~0원", margin: "100%", note: "전화/길찾기/리뷰 클릭" },
    { name: "저장 클릭", price: "+10만", ourCost: "~0원", margin: "100%", note: "저장 버튼 클릭" },
    { name: "네이버 지도 유입", price: "+10만", ourCost: "~0원", margin: "100%", note: "지도 검색 경유" },
  ]},
  { cat: "블로그 전용 옵션 (3종)", color: "#8b6cff", items: [
    { name: "공감 클릭", price: "+8만", ourCost: "~0원", margin: "100%", note: "공감 버튼 클릭" },
    { name: "댓글 체류", price: "+8만", ourCost: "~0원", margin: "100%", note: "댓글 영역 스크롤" },
    { name: "시리즈 탐색", price: "+10만", ourCost: "~0원", margin: "100%", note: "같은 블로그 추가 글" },
  ]},
  { cat: "이벤트 옵션 (2종)", color: "#ffd740", items: [
    { name: "이벤트 부스팅", price: "+5만/회", ourCost: "~1만원", margin: "80%", note: "2~3배 집중 투입" },
    { name: "시즌 캠페인", price: "+10만/회", ourCost: "~2만원", margin: "80%", note: "특정 기간 집중 + 리포트" },
  ]},
];

const revenueSimulation = [
  { scenario: "Basic 1명", config: "VPS 3대", infra: "8만", revenue: "30만", options: "0", total: "30만", margin: "22만", rate: "73%" },
  { scenario: "Basic 3명 + 옵션", config: "VPS 3대", infra: "8만", revenue: "90만", options: "~45만", total: "~135만", margin: "~127만", rate: "94%", best: false },
  { scenario: "Standard 5명 ★", config: "VPS 3대", infra: "8만", revenue: "350만", options: "~100만", total: "~450만", margin: "~442만", rate: "98%", best: true },
  { scenario: "Standard 8명 풀옵션", config: "VPS 5대", infra: "14만", revenue: "560만", options: "~400만", total: "~960만", margin: "~946만", rate: "98%" },
  { scenario: "Premium 5명", config: "VPS 5대", infra: "14만", revenue: "750만", options: "~250만", total: "~1,000만", margin: "~986만", rate: "99%" },
  { scenario: "에이전시 20명", config: "VPS 10대 + 프록시", infra: "377만", revenue: "1,400만", options: "~800만", total: "~2,200만", margin: "~1,823만", rate: "83%" },
];

const clientScenarios = [
  { type: "쇼핑", icon: "🛒", name: "스마트스토어 A사", base: "Standard 70만", options: "찜+장바구니+리뷰정독+모바일+스크린샷", optionPrice: "+46만", total: "116만/월", margin: "~115만 (99%)" },
  { type: "플레이스", icon: "📍", name: "성수동 행정사사무소", base: "Standard 70만", options: "전환시뮬+저장+모바일+지역타겟팅+스크린샷", optionPrice: "+55만", total: "125만/월", margin: "~120만 (96%)" },
  { type: "블로그", icon: "📝", name: "뷰티 블로거 B", base: "Basic 30만", options: "공감+댓글체류+다중키워드", optionPrice: "+31만", total: "61만/월", margin: "~61만 (100%)" },
  { type: "복합", icon: "🏢", name: "대형 브랜드 C사", base: "Premium 150만", options: "쇼핑6종+플레이스3종+블로그2종+공통4종", optionPrice: "+143만", total: "293만/월", margin: "~287만 (98%)" },
];

export default function CostPage() {
  return (
    <>
      <Nav />
      <main className="mx-auto max-w-7xl px-4 pt-20 pb-12">
        <div className="mb-2">
          <p className="text-xs font-bold uppercase tracking-widest text-[#8b6cff]">Cost Analysis</p>
          <h1 className="text-2xl font-bold text-white">구성별 트래픽 원가 분석</h1>
          <p className="text-sm text-[#8888aa]">트래픽 1회당 원가를 구성별로 비교합니다 (프록시 포함 기준)</p>
        </div>

        {/* Proxy configs */}
        <div className="mt-6 grid gap-4 md:grid-cols-3">
          {proxyConfigs.map((c) => (
            <div key={c.name} className={`rounded-xl border p-5 ${c.best ? "border-[#00e676]/50 bg-[#00e676]/[0.03]" : "border-[#2a2a5a] bg-[#111127]"}`}>
              <div className="text-sm font-bold text-white">{c.name}</div>
              <div className="text-xs text-[#8888aa]">{c.sub}</div>
              <div className="my-3 text-4xl font-black" style={{ color: c.color }}>{c.cost}</div>
              <div className="text-xs text-[#8888aa]">트래픽 1회당</div>
              <div className="mt-3 space-y-1.5">
                <div className="flex justify-between text-xs"><span className="text-[#8888aa]">일일 처리량</span><span className="text-[#e0e0e0]">{c.daily}</span></div>
                <div className="flex justify-between text-xs"><span className="text-[#8888aa]">월간 처리량</span><span className="text-[#e0e0e0]">{c.monthlyVol}</span></div>
                {c.breakdown.map((b) => (
                  <div key={b.label} className="flex justify-between text-xs"><span className="text-[#8888aa]">{b.label}</span><span className="text-[#e0e0e0]">{b.val}</span></div>
                ))}
                <div className="flex justify-between border-t border-[#2a2a5a] pt-1.5 text-xs font-bold"><span className="text-[#8888aa]">월 총 비용</span><span className="text-white">{c.monthly}</span></div>
              </div>
              <div className="mt-3 rounded-lg p-2 text-center text-xs font-bold" style={{ color: c.color, background: `${c.color}15` }}>{c.highlight}</div>
            </div>
          ))}
        </div>

        {/* No proxy */}
        <h2 className="mt-10 text-lg font-extrabold text-white">프록시 없이 운영하면?</h2>
        <div className="mt-4 grid gap-4 md:grid-cols-3">
          {noProxyConfigs.map((c) => (
            <div key={c.name} className="rounded-xl border border-[#2a2a5a] bg-[#111127] p-5">
              <div className="text-sm font-bold text-white">{c.name} · 프록시 없음</div>
              <div className="my-2 text-3xl font-black" style={{ color: c.color }}>{c.cost}</div>
              <div className="text-xs text-[#8888aa]">트래픽 1회당</div>
              <div className="mt-2 space-y-1 text-xs">
                <div className="flex justify-between"><span className="text-[#8888aa]">월간 처리량</span><span className="text-[#e0e0e0]">{c.vol}</span></div>
                <div className="flex justify-between"><span className="text-[#8888aa]">비용</span><span className="text-[#e0e0e0]">{c.expense}</span></div>
              </div>
              <div className="mt-2 rounded-lg bg-[#ffd740]/10 p-2 text-center text-xs font-bold text-[#ffd740]">{c.risk}</div>
            </div>
          ))}
        </div>

        {/* VPS Strategy */}
        <div className="mt-10 flex items-center gap-2">
          <Server className="h-5 w-5 text-[#448aff]" />
          <h2 className="text-lg font-extrabold text-white">VPS 리전 분산 전략 (추천)</h2>
        </div>
        <p className="mt-1 mb-4 text-sm text-[#8888aa]">VPS를 다른 지역에 배치하면 프록시 없이도 IP 분산 + 지역 분산 + 24시간 무중단이 됩니다.</p>

        <div className="overflow-x-auto rounded-xl border border-[#2a2a5a] bg-[#111127]">
          <table className="w-full text-sm">
            <thead><tr className="border-b border-[#2a2a5a] text-left text-xs uppercase text-[#8888aa]">
              <th className="p-3">항목</th><th className="p-3">PC 1대 (로컬)</th><th className="p-3">VPS 3대</th><th className="p-3">VPS 5대 ★</th>
            </tr></thead>
            <tbody>
              {vpsComparison.map((row) => (
                <tr key={row.item} className="border-b border-[#2a2a5a]/50">
                  <td className="p-3 font-medium text-white">{row.item}</td>
                  <td className="p-3 text-xs" style={{ color: row.pc.color }}>{row.pc.val}</td>
                  <td className="p-3 text-xs" style={{ color: row.vps3.color }}>{row.vps3.val}</td>
                  <td className="p-3 text-xs" style={{ color: row.vps5.color }}>{row.vps5.val}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Recommended Roadmap */}
        <div className="mt-8 rounded-xl border border-[#00e676]/30 bg-[#00e676]/[0.03] p-6">
          <h3 className="mb-4 font-extrabold text-white">추천 구성 로드맵</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead><tr className="border-b border-[#2a2a5a] text-left text-xs uppercase text-[#8888aa]">
                <th className="pb-2">단계</th><th className="pb-2">구성</th><th className="pb-2">1회당 원가</th><th className="pb-2">안전도</th><th className="pb-2">월 비용</th><th className="pb-2">언제</th>
              </tr></thead>
              <tbody>
                {roadmap.map((r) => (
                  <tr key={r.stage} className="border-b border-[#2a2a5a]/50">
                    <td className="py-3"><span className="rounded px-2 py-0.5 text-[10px] font-extrabold text-black" style={{ background: r.color }}>{r.stage}</span></td>
                    <td className="py-3"><span className="font-bold text-white">{r.config}</span><br /><span className="text-xs text-[#8888aa]">{r.detail}</span></td>
                    <td className="py-3 font-mono font-bold text-[#00e676]">{r.cost}</td>
                    <td className="py-3 text-xs text-[#e0e0e0]">{r.safety}</td>
                    <td className="py-3 font-mono font-bold text-white">{r.monthly}</td>
                    <td className="py-3 text-xs text-[#8888aa]">{r.when}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mt-4 rounded-lg border border-[#00e676]/20 bg-[#00e676]/10 p-3 text-xs text-[#00e676]">
            <strong>핵심: 프록시는 처음부터 쓸 필요 없다.</strong> VPS 3~5대 리전 분산만으로 시작 → 차단 발생 시 프록시 추가 → &quot;지역 타겟팅&quot; 유료 옵션 고객에게만 프록시 비용 전가. 초기 투자 8~14만원으로 월 150,000~255,000회 처리 가능.
          </div>
        </div>

        {/* Option Cost Analysis - NEW */}
        <div className="mt-10 flex items-center gap-2">
          <Calculator className="h-5 w-5 text-[#ff9052]" />
          <h2 className="text-lg font-extrabold text-white">유료 옵션 원가 분석 (25종)</h2>
        </div>
        <p className="mt-1 mb-4 text-sm text-[#8888aa]">대부분의 옵션은 소프트웨어 시뮬레이션으로 추가 비용 없이 제공 가능합니다. 마진율 90~100%.</p>

        {optionCosts.map((group) => (
          <div key={group.cat} className="mt-4 rounded-xl border bg-[#111127] p-4" style={{ borderColor: `${group.color}30` }}>
            <h4 className="mb-3 text-sm font-bold" style={{ color: group.color }}>{group.cat}</h4>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead><tr className="border-b border-[#2a2a5a] text-left text-[10px] uppercase text-[#8888aa]">
                  <th className="pb-1.5">옵션명</th><th className="pb-1.5">고객가</th><th className="pb-1.5">우리 원가</th><th className="pb-1.5">마진율</th><th className="pb-1.5">비고</th>
                </tr></thead>
                <tbody>
                  {group.items.map((item) => (
                    <tr key={item.name} className="border-b border-[#2a2a5a]/30">
                      <td className="py-1.5 font-medium text-white">{item.name}</td>
                      <td className="py-1.5 font-mono" style={{ color: group.color }}>{item.price}</td>
                      <td className="py-1.5 font-mono text-[#8888aa]">{item.ourCost}</td>
                      <td className="py-1.5 font-mono font-bold text-[#00e676]">{item.margin}</td>
                      <td className="py-1.5 text-[#8888aa]">{item.note}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ))}

        <div className="mt-4 rounded-lg border border-[#ff9052]/20 bg-[#ff9052]/10 p-3 text-xs text-[#ff9052]">
          <strong>핵심 인사이트:</strong> 25개 옵션 중 22개는 원가 0원 (소프트웨어 시뮬레이션). 지역 타겟팅(프록시), 경쟁업체 클릭(추가 트래픽), 재방문(쿠키 저장), 이벤트 옵션만 소량 비용 발생. 옵션 매출의 평균 마진율 약 97%.
        </div>

        {/* Revenue Simulation - UPDATED */}
        <div className="mt-10 flex items-center gap-2">
          <TrendingUp className="h-5 w-5 text-[#00e676]" />
          <h2 className="text-lg font-extrabold text-white">서비스 수익 시뮬레이션</h2>
        </div>
        <p className="mt-1 mb-4 text-sm text-[#8888aa]">기본 요금 + 유료 옵션 업셀 기반 시뮬레이션 (VPS 프록시 없음 기준)</p>

        <div className="overflow-x-auto rounded-xl border border-[#2a2a5a] bg-[#111127]">
          <table className="w-full text-sm">
            <thead><tr className="border-b border-[#2a2a5a] text-left text-xs uppercase text-[#8888aa]">
              <th className="p-3">시나리오</th><th className="p-3">인프라</th><th className="p-3">기본 매출</th><th className="p-3">옵션 매출</th><th className="p-3">총 매출</th><th className="p-3">마진</th><th className="p-3">마진율</th>
            </tr></thead>
            <tbody>
              {revenueSimulation.map((r) => (
                <tr key={r.scenario} className={`border-b border-[#2a2a5a]/50 ${r.best ? "bg-[#00e676]/[0.04]" : ""}`}>
                  <td className={`p-3 font-medium ${r.best ? "text-[#00e676]" : "text-white"}`}>{r.scenario}</td>
                  <td className="p-3 font-mono text-[#8888aa]">{r.infra}</td>
                  <td className="p-3 font-mono text-[#e0e0e0]">{r.revenue}</td>
                  <td className="p-3 font-mono text-[#ff9052]">{r.options}</td>
                  <td className="p-3 font-mono font-bold text-white">{r.total}</td>
                  <td className="p-3 font-mono text-[#00e676]">{r.margin}</td>
                  <td className="p-3 font-mono font-bold text-[#00e676]">{r.rate}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Client Scenarios by Type - NEW */}
        <h3 className="mt-8 text-base font-extrabold text-white">타입별 고객 시나리오</h3>
        <p className="mt-1 mb-4 text-sm text-[#8888aa]">쇼핑 / 플레이스 / 블로그 / 복합 — 각 타입별 실제 고객 예시와 마진 구조</p>

        <div className="grid gap-4 md:grid-cols-2">
          {clientScenarios.map((s) => (
            <div key={s.name} className="rounded-xl border border-[#2a2a5a] bg-[#111127] p-5">
              <div className="mb-2 flex items-center gap-2">
                <span className="text-xl">{s.icon}</span>
                <div>
                  <span className="rounded bg-[#16163a] px-1.5 py-0.5 text-[10px] font-bold text-[#8888aa]">{s.type}</span>
                  <div className="text-sm font-bold text-white">{s.name}</div>
                </div>
              </div>
              <div className="space-y-1.5 text-xs">
                <div className="flex justify-between"><span className="text-[#8888aa]">기본 요금</span><span className="text-[#e0e0e0]">{s.base}</span></div>
                <div className="flex justify-between"><span className="text-[#8888aa]">추가 옵션</span><span className="text-[#ff9052]">{s.optionPrice}</span></div>
                <div className="text-[10px] text-[#8888aa]">{s.options}</div>
                <div className="flex justify-between border-t border-[#2a2a5a] pt-1.5 font-bold"><span className="text-[#8888aa]">월 청구</span><span className="text-white">{s.total}</span></div>
              </div>
              <div className="mt-2 rounded-lg bg-[#00e676]/10 p-2 text-center text-xs font-bold text-[#00e676]">{s.margin}</div>
            </div>
          ))}
        </div>

        <div className="mt-6 rounded-lg border border-[#00e676]/20 bg-[#00e676]/10 p-3 text-xs text-[#00e676]">
          <strong>업셀 전략 요약:</strong> 기본 요금 30~150만원에 타입별 맞춤 옵션 업셀 → 평균 객단가 80~120만원. 옵션 원가 대부분 0원이므로 옵션 매출이 늘수록 마진율 급상승. VPS 3대(8만원)로 Standard 5명만 받아도 월 마진 442만원.
        </div>
      </main>
    </>
  );
}
