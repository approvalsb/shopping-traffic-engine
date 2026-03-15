"use client";

import { Nav } from "@/components/nav";
import { Shield, Shuffle, MapPin, Fingerprint, ShoppingCart, FileText } from "lucide-react";

const personaTraits = [
  { group: "핵심 성격", traits: ["patience (인내심)", "curiosity (호기심)", "scroll_style (스크롤 습관)", "attention_span (집중력)", "tech_savvy (숙련도)"], color: "#00e676" },
  { group: "상호작용", traits: ["image_interest (이미지 관심)", "comment_interest (댓글 관심)", "tab_explorer (탭 탐색)", "re_reader (재독 성향)", "idle_tendency (멈춤 빈도)"], color: "#ff9052" },
  { group: "물리 행동", traits: ["scroll_speed (스크롤 속도)", "click_precision (클릭 정밀도)", "mouse_restless (마우스 움직임)"], color: "#448aff" },
  { group: "세션 형태", traits: ["warmup_ratio (시작 패턴)", "fatigue_rate (피로도)", "exit_style (퇴장 방식)"], color: "#8b6cff" },
];

const personaExamples = [
  { tag: "예시 1", color: "#00e676", desc: "PAT=0.82 CUR=0.31 → 느긋하지만 관심 적음 → 천천히 스크롤하다 빠르게 이탈" },
  { tag: "예시 2", color: "#8b6cff", desc: "PAT=0.15 CUR=0.95 → 급하지만 호기심 강함 → 이것저것 빠르게 클릭 후 비교" },
  { tag: "예시 3", color: "#ff9052", desc: "PAT=0.55 CUR=0.60 ATT=0.90 → 보통 속도, 높은 집중 → 리뷰 정독 후 전화" },
  { tag: "예시 4", color: "#448aff", desc: "PAT=0.90 CUR=0.20 SCR=0.70 → 매우 느긋, 관심 없지만 습관적 스크롤 → 길게 체류" },
  { tag: "예시 5", color: "#ffd740", desc: "PAT=0.40 CUR=0.80 TAB=0.85 → 약간 급함, 탭 탐색 활발 → 사진/리뷰/정보 순회" },
];

const randomFactors = [
  { factor: "체류 시간", range: "15초 ~ 180초 (감마 분포)" },
  { factor: "스크롤 깊이", range: "30% ~ 100% (성격 기반)" },
  { factor: "스크롤 속도", range: "연속값 0.0~1.0 (매번 고유)" },
  { factor: "읽기 멈춤", range: "감마 분포 (짧은 멈춤 다수 + 간헐적 긴 멈춤)" },
  { factor: "클릭 전 대기", range: "0.5초 ~ 8초 (숙련도 연동)" },
  { factor: "탭 순서", range: "리뷰→사진→정보 (셔플 + 스킵)" },
  { factor: "마우스 경로", range: "베지어 곡선 (매번 다른 궤적)" },
  { factor: "경쟁업체 클릭 수", range: "0~3개 (호기심 연동)" },
  { factor: "워밍업 패턴", range: "즉시 시작 ~ 느린 훑기 (연속값)" },
  { factor: "퇴장 스타일", range: "갑작스런 ~ 점진적 마무리 (연속값)" },
];

const shoppingL2Actions = [
  { icon: "❤️", title: "찜(좋아요) 클릭", desc: "상품 찜 수 증가 → 네이버 쇼핑 인기도 점수 직접 반영. 방문의 3~8%.", ratio: "3~8%", color: "#ff6eb4" },
  { icon: "🛒", title: "장바구니 담기", desc: "장바구니 전환 시뮬레이션. 구매 의도가 있는 고객 패턴으로 인식.", ratio: "2~5%", color: "#ffd740" },
  { icon: "⭐", title: "리뷰 정독 체류", desc: "리뷰 탭 클릭 후 장시간 체류. 리뷰를 꼼꼼히 읽는 진지한 구매 의도 패턴.", ratio: "15~25%", color: "#ff9052" },
  { icon: "🔄", title: "상품 비교 행동", desc: "경쟁 상품 1~3개 클릭 후 다시 돌아오는 패턴. 비교 후 선택한 관심 고객.", ratio: "10~20%", color: "#8b6cff" },
  { icon: "📂", title: "카테고리 경유", desc: "검색이 아닌 카테고리 탐색 후 상품 도달. 자연스러운 쇼핑 경로.", ratio: "5~10%", color: "#448aff" },
  { icon: "🏪", title: "스토어 내 탐색", desc: "스마트스토어 진입 후 다른 상품도 구경. 스토어 자체 관심도 상승.", ratio: "8~15%", color: "#00e676" },
  { icon: "🔽", title: "정렬/필터 경유", desc: "리뷰순, 가격순 등 정렬 후 상품 클릭. 자연스러운 쇼핑 행동.", ratio: "5~10%", color: "#ff9052" },
  { icon: "🔁", title: "재방문 시뮬레이션", desc: "24~48시간 후 동일 상품을 재검색. 구매 고민 패턴 재현.", ratio: "5~8%", color: "#8b6cff" },
  { icon: "💰", title: "가격비교 체류", desc: "가격비교 탭 클릭 후 체류. 가격을 꼼꼼히 따지는 소비자 행동.", ratio: "5~10%", color: "#ffd740" },
  { icon: "💬", title: "상품 문의 열기", desc: "Q&A 탭 열람. 문의를 확인하는 구매 의도 높은 고객 패턴.", ratio: "3~8%", color: "#448aff" },
];

const placeL2Actions = [
  { icon: "📞", title: "전화 버튼 클릭", desc: "플레이스 상세에서 전화 버튼 클릭. 네이버에 전화 의도 이벤트 기록.", ratio: "5~15%", color: "#ff9052" },
  { icon: "🗺️", title: "길찾기 클릭", desc: "길찾기 버튼 → 네이버 지도 경로 탐색 이벤트 발생.", ratio: "3~10%", color: "#00e676" },
  { icon: "🔗", title: "저장(찜) 클릭", desc: "플레이스 저장 버튼. 관심도 높은 업체로 판단하는 핵심 지표.", ratio: "3~8%", color: "#ffd740" },
  { icon: "📝", title: "블로그 리뷰 클릭", desc: "플레이스 내 블로그 리뷰 링크를 클릭하여 읽고 돌아옴.", ratio: "10~20%", color: "#8b6cff" },
];

const blogL2Actions = [
  { icon: "👍", title: "공감 클릭", desc: "블로그 공감 버튼 클릭. D.I.A. 알고리즘에 긍정 신호.", ratio: "5~15%", color: "#ff6eb4" },
  { icon: "💬", title: "댓글 영역 체류", desc: "댓글 스크롤 + 읽기 시뮬레이션. 체류시간 추가 확보.", ratio: "10~20%", color: "#448aff" },
  { icon: "📚", title: "시리즈 글 탐색", desc: "같은 블로그의 다른 글도 방문. 블로그 전체 체류시간 증가.", ratio: "5~10%", color: "#8b6cff" },
];

const conversionRates = [
  { industry: "병원/의원", phone: "5~8%", directions: "3~5%", wish: "-", cart: "-", target: "전화 6%, 길찾기 4%" },
  { industry: "음식점/카페", phone: "2~4%", directions: "8~12%", wish: "-", cart: "-", target: "전화 3%, 길찾기 10%" },
  { industry: "미용/네일", phone: "4~6%", directions: "2~4%", wish: "-", cart: "-", target: "전화 5%, 길찾기 3%" },
  { industry: "행정사/법무", phone: "6~10%", directions: "2~3%", wish: "-", cart: "-", target: "전화 8%, 길찾기 2%" },
  { industry: "스마트스토어", phone: "-", directions: "-", wish: "3~8%", cart: "2~5%", target: "찜 5%, 장바구니 3%" },
  { industry: "브랜드스토어", phone: "-", directions: "-", wish: "5~10%", cart: "3~7%", target: "찜 7%, 장바구니 5%" },
  { industry: "블로그", phone: "-", directions: "-", wish: "-", cart: "-", target: "공감 10%, 댓글체류 15%" },
];

const regionRules = [
  { region: "업체 소재지", ratio: "50~60%", desc: "가장 많은 유입 (동일 구/시)", color: "#00e676" },
  { region: "인접 지역", ratio: "25~30%", desc: "옆 구/시에서의 유입", color: "#e0e0e0" },
  { region: "같은 광역시/도", ratio: "10~15%", desc: "같은 도 내 원거리", color: "#8888aa" },
  { region: "기타 지역", ratio: "5~10%", desc: "출장/여행자 패턴", color: "#555" },
];

const industryRange = [
  { industry: "동네 맛집/카페", range: "반경 5km (같은 구)" },
  { industry: "병원/미용실", range: "반경 10km (같은 시)" },
  { industry: "전문 서비스 (행정사 등)", range: "같은 시/도 전역" },
  { industry: "온라인 쇼핑몰", range: "전국 (지역 무관)" },
  { industry: "관광/숙박", range: "전국 (타 지역 비율 높음)" },
];

const layerSummary = [
  { layer: "L1", label: "페르소나 기반 행동 생성", color: "#00e676", detail: "16개 성격 특성 → 무한 조합 → 매 방문 고유", problem: "봇 패턴 반복 감지", pricing: "기본 포함" },
  { layer: "L2", label: "전환 시뮬레이션 (타입별)", color: "#ff9052", detail: "쇼핑 10종 / 플레이스 4종 / 블로그 3종", problem: "전환율 이상 (방문만 있고 액션 없음)", pricing: "유료 옵션 (+5~15만)" },
  { layer: "L3", label: "지역 기반 최적화", color: "#448aff", detail: "소재지 중심 IP 분산 + 업종별 범위", problem: "지역 편중 (서울 업체에 부산 IP)", pricing: "유료 옵션 (+10만)" },
];

export default function StealthPage() {
  return (
    <>
      <Nav />
      <main className="mx-auto max-w-7xl px-4 pt-20 pb-12">
        <div className="mb-2">
          <p className="text-xs font-bold uppercase tracking-widest text-[#8b6cff]">Anti-Detection &amp; Behavior Design</p>
          <h1 className="text-2xl font-bold text-white">감지 방지 &amp; 행동 패턴 설계</h1>
          <p className="text-sm text-[#8888aa]">네이버와 고객 모두에게 자연스럽게 보이기 위한 3계층 위장 전략</p>
        </div>

        {/* LAYER 1 — Persona System */}
        <section className="mt-8">
          <div className="mb-4 flex items-center gap-2">
            <span className="rounded-md bg-[#00e676] px-2.5 py-0.5 text-[11px] font-extrabold text-black">LAYER 1</span>
            <h2 className="text-lg font-extrabold text-white">페르소나 기반 행동 생성 — &ldquo;진짜 매번 다르게&rdquo;</h2>
          </div>
          <p className="mb-4 text-sm text-[#8888aa]">고정된 시나리오 풀이 아닌, 매 방문마다 고유한 가상 인격(페르소나)을 생성합니다. 16개 연속 성격 특성의 조합으로 사실상 무한대의 행동 패턴을 만듭니다.</p>

          {/* Persona Traits */}
          <div className="rounded-xl border border-[#00e676]/30 bg-[#00e676]/[0.03] p-5 mb-4">
            <h3 className="mb-3 font-bold text-white flex items-center gap-2"><Fingerprint className="h-4 w-4 text-[#00e676]" />Visit Persona — 16개 성격 특성</h3>
            <p className="mb-3 text-xs text-[#8888aa]">각 특성은 0.00~1.00 사이의 연속값. 매 방문마다 새로운 조합이 생성되어 동일한 행동이 반복될 확률은 사실상 0%입니다.</p>
            <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-4">
              {personaTraits.map((g) => (
                <div key={g.group} className="rounded-lg bg-[#0a0a1a] p-3">
                  <div className="mb-2 text-xs font-bold" style={{ color: g.color }}>{g.group}</div>
                  {g.traits.map((t) => (
                    <div key={t} className="text-[11px] text-[#e0e0e0] py-0.5 font-mono">{t}</div>
                  ))}
                </div>
              ))}
            </div>
            <div className="mt-3 rounded-lg bg-[#0a0a1a] p-3 font-mono text-xs leading-relaxed text-[#e0e0e0]">
              방문#1: <span className="text-[#00e676]">PAT=0.72</span> CUR=0.73 SCR=0.81 ATT=0.29 → 참을성 있지만 집중력 낮음 → 넓게 훑으며 오래 체류<br />
              방문#2: <span className="text-[#ff9052]">PAT=0.26</span> CUR=0.90 SCR=0.57 ATT=0.06 → 급하지만 호기심 폭발 → 이것저것 빠르게 클릭<br />
              방문#3: <span className="text-[#448aff]">PAT=0.62</span> CUR=0.47 SCR=0.48 ATT=0.79 → 보통 속도, 높은 집중 → 한 섹션 깊이 읽기
            </div>
          </div>

          {/* 3-Phase Session */}
          <div className="grid gap-4 md:grid-cols-3 mb-4">
            {[
              { phase: "Phase 1", name: "워밍업", color: "#00e676", desc: "페이지 첫 인상 훑기. warmup_ratio에 따라 즉시 시작 ~ 느린 스캔.", detail: "tech_savvy 낮으면 긴 워밍업, 높으면 바로 읽기 시작" },
              { phase: "Phase 2", name: "메인 읽기", color: "#ff9052", desc: "성격 기반 행동 가중치로 액션 연속 생성. 피로도에 따라 점차 느려짐.", detail: "patience × curiosity × image_interest... 조합으로 액션 결정" },
              { phase: "Phase 3", name: "마무리", color: "#8b6cff", desc: "exit_style에 따라 갑작스런 이탈 ~ 점진적 마무리 (위로 돌아가기 등).", detail: "re_reader 높으면 상단 재확인 후 퇴장" },
            ].map((p) => (
              <div key={p.phase} className="rounded-xl border border-[#2a2a5a] bg-[#111127] p-4">
                <span className="rounded px-2 py-0.5 text-[10px] font-bold text-black" style={{ background: p.color }}>{p.phase}</span>
                <h4 className="mt-2 font-bold text-white">{p.name}</h4>
                <p className="mt-1 text-xs text-[#8888aa]">{p.desc}</p>
                <p className="mt-2 text-[11px] text-[#555]">{p.detail}</p>
              </div>
            ))}
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div className="rounded-xl border border-[#2a2a5a] bg-[#111127] p-5">
              <h3 className="mb-3 font-bold text-white flex items-center gap-2"><Shuffle className="h-4 w-4 text-[#00e676]" />페르소나 기반 행동 생성 (L1 무료)</h3>
              <p className="mb-3 text-sm text-[#8888aa]">고정 시나리오가 아닌, 16개 성격 특성 조합으로 매 방문 고유한 행동을 생성합니다.</p>
              <div className="space-y-2">
                {personaExamples.map((s) => (
                  <div key={s.tag} className="flex items-center gap-2 text-sm">
                    <span className="rounded px-2 py-0.5 text-[10px] font-bold" style={{ color: s.color, border: `1px solid ${s.color}30`, background: `${s.color}10` }}>
                      {s.tag}
                    </span>
                    <span className="text-[#e0e0e0] font-mono text-xs">{s.desc}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-xl border border-[#2a2a5a] bg-[#111127] p-5">
              <h3 className="mb-3 font-bold text-white">변동 요소 (매 방문 고유값)</h3>
              <table className="w-full text-sm">
                <thead><tr className="border-b border-[#2a2a5a] text-left text-xs uppercase text-[#8888aa]"><th className="pb-2">요소</th><th className="pb-2">범위</th></tr></thead>
                <tbody>
                  {randomFactors.map((f) => (
                    <tr key={f.factor} className="border-b border-[#2a2a5a]/50">
                      <td className="py-2 text-[#e0e0e0]">{f.factor}</td>
                      <td className="py-2 font-mono text-xs text-[#8888aa]">{f.range}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="mt-4 grid gap-4 md:grid-cols-2">
            <div className="rounded-xl border border-[#2a2a5a] bg-[#111127] p-5">
              <h3 className="mb-2 font-bold text-white">재방문 시뮬레이션</h3>
              <p className="mb-3 text-sm text-[#8888aa]">실제 사용자는 관심 있는 상품/가게를 며칠 후 다시 방문합니다. 프록시 IP + 쿠키를 보존하여 같은 사람이 재방문하는 패턴을 만듭니다.</p>
              <div className="rounded-lg bg-[#0a0a1a] p-3 font-mono text-xs leading-relaxed text-[#e0e0e0]">
                Day 1: 검색 → 3개 비교 → 고객 상품 클릭 → 리뷰 보고 이탈<br />
                Day 3: <span className="text-[#00e676]">같은 IP</span> → 직접 검색 → 가격비교 → 찜 클릭<br />
                Day 5: <span className="text-[#00e676]">같은 IP</span> → 재방문 → 장바구니 담기
              </div>
            </div>
            <div className="rounded-xl border border-[#2a2a5a] bg-[#111127] p-5">
              <h3 className="mb-2 font-bold text-white">일일 변동폭</h3>
              <p className="mb-3 text-sm text-[#8888aa]">매일 정확히 300회가 아니라, 자연스러운 흔들림을 줍니다.</p>
              <div className="rounded-lg bg-[#0a0a1a] p-3 font-mono text-xs leading-relaxed text-[#e0e0e0]">
                월: 287회 &nbsp; 화: 312회 &nbsp; 수: 265회<br />
                목: 331회 &nbsp; 금: 298회 &nbsp; <span className="text-[#555]">토: 198회</span><br />
                <span className="text-[#555]">일: 156회</span> &nbsp; ← 주말은 자동 감소
              </div>
              <p className="mt-2 text-xs text-[#555]">기본 ±15% 랜덤 + 주말 자동 감소 (업종별 다름)</p>
            </div>
          </div>
        </section>

        {/* LAYER 2 — Per-type conversion */}
        <section className="mt-10">
          <div className="mb-4 flex items-center gap-2">
            <span className="rounded-md bg-[#ff9052] px-2.5 py-0.5 text-[11px] font-extrabold text-black">LAYER 2</span>
            <h2 className="text-lg font-extrabold text-white">전환 시뮬레이션 — &ldquo;진짜 고객처럼&rdquo;</h2>
          </div>
          <p className="mb-4 text-sm text-[#8888aa]">방문만 하고 아무 행동 없이 나가면 네이버가 가치 없는 트래픽으로 판단합니다. 캠페인 타입별로 맞춤 전환 액션을 시뮬레이션합니다.</p>

          {/* Shopping L2 */}
          <div className="mb-6">
            <h3 className="mb-3 font-bold text-white flex items-center gap-2"><ShoppingCart className="h-4 w-4 text-[#ff6eb4]" />쇼핑 전용 전환 시뮬레이션 (10종)</h3>
            <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-5">
              {shoppingL2Actions.map((a) => (
                <div key={a.title} className="rounded-xl border bg-[#111127] p-4" style={{ borderColor: `${a.color}30` }}>
                  <div className="text-2xl mb-1">{a.icon}</div>
                  <h4 className="text-sm font-bold text-white">{a.title}</h4>
                  <p className="mt-1 text-[11px] text-[#8888aa] leading-relaxed">{a.desc}</p>
                  <div className="mt-2 flex gap-1.5">
                    <span className="rounded-full bg-[#ff9052]/10 px-2 py-0.5 text-[9px] font-bold text-[#ff9052]">유료</span>
                    <span className="rounded-full bg-[#16163a] px-2 py-0.5 text-[9px] text-[#8888aa]">{a.ratio}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Place L2 */}
          <div className="mb-6">
            <h3 className="mb-3 font-bold text-white flex items-center gap-2"><MapPin className="h-4 w-4 text-[#ff9052]" />플레이스 전용 전환 시뮬레이션 (4종)</h3>
            <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-4">
              {placeL2Actions.map((a) => (
                <div key={a.title} className="rounded-xl border bg-[#111127] p-4" style={{ borderColor: `${a.color}30` }}>
                  <div className="text-2xl mb-1">{a.icon}</div>
                  <h4 className="text-sm font-bold text-white">{a.title}</h4>
                  <p className="mt-1 text-[11px] text-[#8888aa] leading-relaxed">{a.desc}</p>
                  <div className="mt-2 flex gap-1.5">
                    <span className="rounded-full bg-[#ff9052]/10 px-2 py-0.5 text-[9px] font-bold text-[#ff9052]">유료</span>
                    <span className="rounded-full bg-[#16163a] px-2 py-0.5 text-[9px] text-[#8888aa]">{a.ratio}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Blog L2 */}
          <div className="mb-6">
            <h3 className="mb-3 font-bold text-white flex items-center gap-2"><FileText className="h-4 w-4 text-[#448aff]" />블로그 전용 전환 시뮬레이션 (3종)</h3>
            <div className="grid gap-3 md:grid-cols-3">
              {blogL2Actions.map((a) => (
                <div key={a.title} className="rounded-xl border bg-[#111127] p-4" style={{ borderColor: `${a.color}30` }}>
                  <div className="text-2xl mb-1">{a.icon}</div>
                  <h4 className="text-sm font-bold text-white">{a.title}</h4>
                  <p className="mt-1 text-[11px] text-[#8888aa] leading-relaxed">{a.desc}</p>
                  <div className="mt-2 flex gap-1.5">
                    <span className="rounded-full bg-[#ff9052]/10 px-2 py-0.5 text-[9px] font-bold text-[#ff9052]">유료</span>
                    <span className="rounded-full bg-[#16163a] px-2 py-0.5 text-[9px] text-[#8888aa]">{a.ratio}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Conversion Rate Table */}
          <div className="rounded-xl border border-[#2a2a5a] bg-[#111127] p-5">
            <h3 className="mb-3 font-bold text-white">업종별 전환율 자동 조절</h3>
            <p className="mb-3 text-sm text-[#8888aa]">업종 평균 전환율에 맞춰 자동으로 비율을 조절합니다.</p>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead><tr className="border-b border-[#2a2a5a] text-left text-xs uppercase text-[#8888aa]"><th className="pb-2">업종</th><th className="pb-2">전화</th><th className="pb-2">길찾기</th><th className="pb-2">찜</th><th className="pb-2">장바구니</th><th className="pb-2">맞출 비율</th></tr></thead>
                <tbody>
                  {conversionRates.map((r) => (
                    <tr key={r.industry} className="border-b border-[#2a2a5a]/50">
                      <td className="py-2 text-[#e0e0e0]">{r.industry}</td>
                      <td className="py-2 font-mono text-xs text-[#8888aa]">{r.phone}</td>
                      <td className="py-2 font-mono text-xs text-[#8888aa]">{r.directions}</td>
                      <td className="py-2 font-mono text-xs text-[#8888aa]">{r.wish}</td>
                      <td className="py-2 font-mono text-xs text-[#8888aa]">{r.cart}</td>
                      <td className="py-2 font-mono text-xs text-[#00e676]">{r.target}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>

        {/* LAYER 3 */}
        <section className="mt-10">
          <div className="mb-4 flex items-center gap-2">
            <span className="rounded-md bg-[#448aff] px-2.5 py-0.5 text-[11px] font-extrabold text-black">LAYER 3</span>
            <h2 className="text-lg font-extrabold text-white">지역 기반 최적화 — &ldquo;논리적으로 맞게&rdquo;</h2>
          </div>
          <p className="mb-4 text-sm text-[#8888aa]">서울 강남의 맛집인데 부산 IP에서 유입이 몰리면 비정상입니다. 업체 위치 기반으로 트래픽 지역을 맞춥니다.</p>

          <div className="grid gap-4 md:grid-cols-2">
            <div className="rounded-xl border border-[#2a2a5a] bg-[#111127] p-5">
              <h3 className="mb-3 font-bold text-white flex items-center gap-2"><MapPin className="h-4 w-4 text-[#448aff]" />지역 배분 로직</h3>
              <table className="w-full text-sm">
                <thead><tr className="border-b border-[#2a2a5a] text-left text-xs uppercase text-[#8888aa]"><th className="pb-2">유입 지역</th><th className="pb-2">비율</th><th className="pb-2">설명</th></tr></thead>
                <tbody>
                  {regionRules.map((r) => (
                    <tr key={r.region} className="border-b border-[#2a2a5a]/50">
                      <td className="py-2 font-medium" style={{ color: r.color }}>{r.region}</td>
                      <td className="py-2 font-mono text-xs font-bold" style={{ color: r.color }}>{r.ratio}</td>
                      <td className="py-2 text-xs text-[#8888aa]">{r.desc}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="rounded-xl border border-[#2a2a5a] bg-[#111127] p-5">
              <h3 className="mb-3 font-bold text-white">업종별 지역 범위</h3>
              <table className="w-full text-sm">
                <thead><tr className="border-b border-[#2a2a5a] text-left text-xs uppercase text-[#8888aa]"><th className="pb-2">업종</th><th className="pb-2">주 유입 범위</th></tr></thead>
                <tbody>
                  {industryRange.map((r) => (
                    <tr key={r.industry} className="border-b border-[#2a2a5a]/50">
                      <td className="py-2 text-[#e0e0e0]">{r.industry}</td>
                      <td className="py-2 text-xs text-[#8888aa]">{r.range}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div className="mt-4 space-y-2 text-sm">
                <div><span className="font-bold text-[#00e676]">스마트스토어</span> <span className="text-[#8888aa]">(전국 배송)</span><div className="text-xs text-[#8888aa] mt-0.5">→ 서울 35%, 경기 25%, 부산/대구/대전 각 5~8%, 기타 22%</div></div>
                <div><span className="font-bold text-[#ff9052]">안산 한방병원</span> <span className="text-[#8888aa]">(경기 안산시)</span><div className="text-xs text-[#8888aa] mt-0.5">→ 안산 IP 55%, 시흥/화성 IP 25%, 경기 기타 12%, 서울/기타 8%</div></div>
              </div>
            </div>
          </div>
        </section>

        {/* Summary */}
        <section className="mt-10">
          <div className="rounded-xl border border-[#00e676]/30 bg-[#00e676]/[0.03] p-6">
            <h3 className="mb-4 flex items-center gap-2 text-lg font-extrabold text-white">
              <Shield className="h-5 w-5 text-[#00e676]" />
              3계층 위장 전략 요약
            </h3>
            <table className="w-full text-sm">
              <thead><tr className="border-b border-[#2a2a5a] text-left text-xs uppercase text-[#8888aa]"><th className="pb-2">계층</th><th className="pb-2">전략</th><th className="pb-2">해결하는 문제</th><th className="pb-2">고객 과금</th></tr></thead>
              <tbody>
                {layerSummary.map((l) => (
                  <tr key={l.layer} className="border-b border-[#2a2a5a]/50">
                    <td className="py-3"><span className="rounded px-2 py-0.5 text-[10px] font-extrabold text-black" style={{ background: l.color }}>{l.layer}</span></td>
                    <td className="py-3"><span className="font-bold text-white">{l.label}</span><br /><span className="text-xs text-[#8888aa]">{l.detail}</span></td>
                    <td className="py-3 text-[#e0e0e0]">{l.problem}</td>
                    <td className="py-3 font-bold" style={{ color: l.layer === "L1" ? "#00e676" : "#ff9052" }}>{l.pricing}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </main>
    </>
  );
}
