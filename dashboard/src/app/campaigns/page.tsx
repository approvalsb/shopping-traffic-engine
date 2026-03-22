"use client";

import { useEffect, useState, useCallback } from "react";
import { Nav } from "@/components/nav";
import { INDUSTRY_PRESETS } from "@/lib/api";
import {
  Plus,
  Trash2,
  Power,
  PowerOff,
  ShoppingCart,
  MapPin,
  FileText,
  X,
  Pencil,
} from "lucide-react";

interface Campaign {
  id: number;
  type: string;
  customer_name: string;
  keyword: string;
  product_name: string;
  product_url: string;
  daily_target: number;
  dwell_time_min: number;
  dwell_time_max: number;
  active: number;
  created_at: string;
  hourly_weights?: string;
  engage_like?: number;
  options?: string[];
}

const paidOptions = [
  // ── 공통 옵션 ──
  { key: "mobile_traffic", name: "모바일 트래픽", price: "+10만", icon: "📱", layer: "", desc: "PC:모바일 30:70 비율 배분", color: "#ff6eb4" },
  { key: "multi_keyword", name: "다중 키워드 유입", price: "+15만", icon: "🔎", layer: "", desc: "5~10개 키워드 분산 유입", color: "#8b6cff" },
  { key: "regional_targeting", name: "지역 타겟팅", price: "+10만", icon: "📍", layer: "L3", desc: "소재지 중심 IP 분산", color: "#448aff" },
  { key: "gradual_increase", name: "점진적 증가 모드", price: "+5만", icon: "📈", layer: "", desc: "1주차100→2주차200→3주차300", color: "#ff9052" },
  { key: "competitor_rank", name: "경쟁업체 비교 클릭", price: "+12만", icon: "🏆", layer: "", desc: "경쟁 2~3곳 클릭 후 고객 업체 최종 선택 패턴", color: "#448aff" },
  { key: "screenshot", name: "스크린샷 증빙", price: "+10만", icon: "📷", layer: "", desc: "일일 캡처 자동 전송", color: "#00e676" },
  { key: "screenshot_report", name: "Before/After 리포트", price: "+18만", icon: "📊", layer: "", desc: "순위 변화 비교 리포트 + 통계 자동 보고서", color: "#8b6cff" },

  // ── 쇼핑 전용 옵션 ──
  { key: "wish_click", name: "찜(좋아요) 클릭", price: "+10만", icon: "❤️", layer: "L2", desc: "상품 찜 수 증가 → 인기도 상승", color: "#ff6eb4", typeOnly: "shopping" },
  { key: "cart_add", name: "장바구니 담기", price: "+15만", icon: "🛒", layer: "L2", desc: "장바구니 전환 시뮬레이션", color: "#ffd740", typeOnly: "shopping" },
  { key: "review_dwell", name: "리뷰 정독 체류", price: "+10만", icon: "⭐", layer: "L2", desc: "리뷰 탭 클릭 + 장시간 체류", color: "#ff9052", typeOnly: "shopping" },
  { key: "compare_behavior", name: "상품 비교 행동", price: "+10만", icon: "🔄", layer: "L2", desc: "타 상품 클릭 후 재방문 (관심도↑)", color: "#8b6cff", typeOnly: "shopping" },
  { key: "category_entry", name: "카테고리 경유 유입", price: "+10만", icon: "📂", layer: "L2", desc: "카테고리 탐색 후 상품 도달", color: "#448aff", typeOnly: "shopping" },
  { key: "store_browse", name: "스토어 내 탐색", price: "+10만", icon: "🏪", layer: "L2", desc: "스마트스토어 다른 상품도 구경", color: "#00e676", typeOnly: "shopping" },
  { key: "sort_filter", name: "정렬/필터 경유", price: "+5만", icon: "🔽", layer: "L2", desc: "리뷰순/가격순 정렬 후 클릭", color: "#ff9052", typeOnly: "shopping" },
  { key: "revisit_sim", name: "재방문 시뮬레이션", price: "+15만", icon: "🔁", layer: "L2", desc: "24~48h 후 동일 상품 재검색", color: "#8b6cff", typeOnly: "shopping" },
  { key: "price_compare", name: "가격비교 체류", price: "+10만", icon: "💰", layer: "L2", desc: "가격비교 탭 클릭 + 체류", color: "#ffd740", typeOnly: "shopping" },
  { key: "inquiry_click", name: "상품 문의 열기", price: "+10만", icon: "💬", layer: "L2", desc: "Q&A 탭 열람 시뮬레이션", color: "#448aff", typeOnly: "shopping" },

  // ── 플레이스 전용 옵션 ──
  { key: "conversion_sim", name: "전환 시뮬레이션", price: "+15만", icon: "📞", layer: "L2", desc: "전화/길찾기/리뷰 클릭", color: "#ff9052", typeOnly: "place" },
  { key: "save_click", name: "저장(찜) 클릭", price: "+10만", icon: "🔗", layer: "L2", desc: "플레이스 저장 → 관심도 상승", color: "#ffd740", typeOnly: "place" },
  { key: "map_traffic", name: "네이버 지도 유입", price: "+10만", icon: "🗺️", layer: "L2", desc: "지도 앱 경유 유입 경로", color: "#00e676", typeOnly: "place" },

  // ── 블로그 전용 옵션 ──
  { key: "blog_like", name: "공감 클릭", price: "+10만", icon: "👍", layer: "L2", desc: "블로그 공감 버튼 클릭", color: "#ff6eb4", typeOnly: "blog" },
  { key: "blog_comment_view", name: "댓글 영역 체류", price: "+10만", icon: "💬", layer: "L2", desc: "댓글 스크롤 + 읽기 시뮬레이션", color: "#448aff", typeOnly: "blog" },
  { key: "blog_series", name: "시리즈 글 탐색", price: "+12만", icon: "📚", layer: "L2", desc: "같은 블로그 다른 글도 방문", color: "#8b6cff", typeOnly: "blog" },

  // ── 이벤트 옵션 ──
  { key: "event_boost", name: "이벤트 부스팅", price: "+8만/회", icon: "⚡", layer: "", desc: "특정 날짜 2~3배 집중 투입", color: "#ffd740" },
  { key: "season_campaign", name: "시즌 캠페인", price: "+15만/회", icon: "🎯", layer: "", desc: "특정 기간 집중 + 전후 비교 리포트", color: "#ff9052" },
];

// L2/L3 option keys for layer detection
const L2_KEYS = new Set(paidOptions.filter((o) => o.layer === "L2").map((o) => o.key));
const L3_KEYS = new Set(paidOptions.filter((o) => o.layer === "L3").map((o) => o.key));

function parseOptions(opts?: string[] | string): string[] {
  if (!opts) return [];
  if (typeof opts === "string") {
    try { return JSON.parse(opts); } catch { return []; }
  }
  return opts;
}

function getActiveLayers(opts?: string[] | string): { l1: boolean; l2: boolean; l3: boolean } {
  const parsed = parseOptions(opts);
  const l2 = parsed.some((k) => L2_KEYS.has(k));
  const l3 = parsed.some((k) => L3_KEYS.has(k));
  return { l1: true, l2, l3 }; // L1 is always active
}

function LayerBadges({ options }: { options?: string[] | string }) {
  const layers = getActiveLayers(options);
  return (
    <span className="inline-flex gap-1">
      <span className="rounded px-1.5 py-0.5 text-[9px] font-extrabold text-black bg-[#00e676]">L1</span>
      <span className={`rounded px-1.5 py-0.5 text-[9px] font-extrabold ${layers.l2 ? "text-black bg-[#ff9052]" : "text-[#555] bg-[#2a2a5a]"}`}>L2</span>
      <span className={`rounded px-1.5 py-0.5 text-[9px] font-extrabold ${layers.l3 ? "text-black bg-[#448aff]" : "text-[#555] bg-[#2a2a5a]"}`}>L3</span>
    </span>
  );
}

const defaultForm = {
  type: "shopping",
  customer_name: "",
  keyword: "",
  product_name: "",
  product_url: "",
  daily_target: 300,
  dwell_time_min: 30,
  dwell_time_max: 90,
  preset: "natural",
  options: {} as Record<string, boolean>,
};

export default function CampaignsPage() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(defaultForm);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [expandedCustomer, setExpandedCustomer] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);

  const fetchCampaigns = useCallback(async () => {
    try {
      const res = await fetch("/api/campaigns?all=1");
      if (res.ok) {
        const data = await res.json();
        setCampaigns(data.campaigns || []);
      }
    } catch {
      // silently handle
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCampaigns();
  }, [fetchCampaigns]);

  const startEdit = (c: Campaign) => {
    const opts: Record<string, boolean> = {};
    parseOptions(c.options).forEach((k) => { opts[k] = true; });
    setForm({
      type: c.type,
      customer_name: c.customer_name,
      keyword: c.keyword,
      product_name: c.product_name,
      product_url: c.product_url,
      daily_target: c.daily_target,
      dwell_time_min: c.dwell_time_min,
      dwell_time_max: c.dwell_time_max,
      preset: "natural",
      options: opts,
    });
    setEditingId(c.id);
    setShowForm(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    const payload = {
      type: form.type,
      customer_name: form.customer_name,
      keyword: form.keyword,
      product_name: form.product_name,
      product_url: form.product_url,
      daily_target: form.daily_target,
      dwell_time_min: form.dwell_time_min,
      dwell_time_max: form.dwell_time_max,
      options: Object.entries(form.options)
        .filter(([, v]) => v)
        .map(([k]) => k),
    };
    try {
      const url = editingId ? `/api/campaigns/${editingId}` : "/api/campaigns";
      const method = editingId ? "PUT" : "POST";
      const res = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (res.ok) {
        setForm(defaultForm);
        setShowForm(false);
        setEditingId(null);
        fetchCampaigns();
      }
    } finally {
      setSubmitting(false);
    }
  };

  const toggleCampaign = async (id: number, active: boolean) => {
    await fetch(`/api/campaigns/${id}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ active }),
    });
    fetchCampaigns();
  };

  const deleteCampaign = async (id: number) => {
    if (!confirm("이 캠페인을 삭제하시겠습니까?")) return;
    await fetch(`/api/campaigns/${id}`, { method: "DELETE" });
    fetchCampaigns();
  };

  const selectedPreset = INDUSTRY_PRESETS[form.preset];

  return (
    <>
      <Nav />
      <main className="mx-auto max-w-7xl px-4 pt-20 pb-12">
        <div className="mb-6 flex items-center justify-between">
          <h1 className="text-2xl font-bold text-white">캠페인 관리</h1>
          <button
            onClick={() => { setShowForm(!showForm); if (showForm) { setEditingId(null); setForm(defaultForm); } }}
            className="flex items-center gap-1.5 rounded-lg bg-[#00e676] px-4 py-2 text-sm font-semibold text-black transition-colors hover:bg-[#00c853]"
          >
            {showForm ? <X className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
            {showForm ? "취소" : "새 캠페인"}
          </button>
        </div>

        {/* New Campaign Form */}
        {showForm && (
          <form
            onSubmit={handleSubmit}
            className="mb-8 rounded-xl border border-[#2a2a5a] bg-[#111127] p-6"
          >
            <h2 className="mb-4 text-lg font-semibold text-white">
              {editingId ? `캠페인 수정 (#${editingId})` : "새 캠페인 등록"}
            </h2>
            <div className="grid gap-4 md:grid-cols-2">
              {/* Campaign Type */}
              <div className="md:col-span-2">
                <label className="mb-1 block text-xs text-[#8888aa]">
                  캠페인 타입
                </label>
                <div className="flex gap-2">
                  {[
                    { value: "shopping", label: "🛒 쇼핑", icon: ShoppingCart },
                    { value: "place", label: "📍 플레이스", icon: MapPin },
                    { value: "blog", label: "📝 블로그", icon: FileText },
                  ].map((opt) => (
                    <button
                      key={opt.value}
                      type="button"
                      onClick={() => setForm({ ...form, type: opt.value })}
                      className={`flex items-center gap-2 rounded-lg border px-4 py-2 text-sm transition-colors ${
                        form.type === opt.value
                          ? "border-[#00e676] bg-[#00e676]/10 text-[#00e676]"
                          : "border-[#2a2a5a] text-[#8888aa] hover:border-[#448aff]"
                      }`}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="mb-1 block text-xs text-[#8888aa]">
                  고객명 *
                </label>
                <input
                  required
                  value={form.customer_name}
                  onChange={(e) =>
                    setForm({ ...form, customer_name: e.target.value })
                  }
                  className="w-full rounded-lg border border-[#2a2a5a] bg-[#0a0a1a] px-3 py-2 text-sm text-white placeholder-[#555] focus:border-[#00e676] focus:outline-none"
                  placeholder="예: 나이스한방병원"
                />
              </div>

              <div>
                <label className="mb-1 block text-xs text-[#8888aa]">
                  검색 키워드 *
                </label>
                <input
                  required
                  value={form.keyword}
                  onChange={(e) =>
                    setForm({ ...form, keyword: e.target.value })
                  }
                  className="w-full rounded-lg border border-[#2a2a5a] bg-[#0a0a1a] px-3 py-2 text-sm text-white placeholder-[#555] focus:border-[#00e676] focus:outline-none"
                  placeholder="예: 안산 한방병원"
                />
              </div>

              <div>
                <label className="mb-1 block text-xs text-[#8888aa]">
                  {form.type === "blog" ? "블로그 글 제목 *" : "상품/업체명 *"}
                </label>
                <input
                  required
                  value={form.product_name}
                  onChange={(e) =>
                    setForm({ ...form, product_name: e.target.value })
                  }
                  className="w-full rounded-lg border border-[#2a2a5a] bg-[#0a0a1a] px-3 py-2 text-sm text-white placeholder-[#555] focus:border-[#00e676] focus:outline-none"
                  placeholder={form.type === "blog" ? "예: 성수동 파스타 맛집 추천" : "예: 나이스한방병원"}
                />
              </div>

              <div>
                <label className="mb-1 block text-xs text-[#8888aa]">
                  {form.type === "blog" ? "블로그명 (선택)" : "URL (선택)"}
                </label>
                <input
                  value={form.product_url}
                  onChange={(e) =>
                    setForm({ ...form, product_url: e.target.value })
                  }
                  className="w-full rounded-lg border border-[#2a2a5a] bg-[#0a0a1a] px-3 py-2 text-sm text-white placeholder-[#555] focus:border-[#00e676] focus:outline-none"
                  placeholder={form.type === "blog" ? "예: 맛집탐방일기 (비워두면 제목만으로 검색)" : "https://..."}
                />
              </div>

              <div>
                <label className="mb-1 block text-xs text-[#8888aa]">
                  일일 목표 트래픽
                </label>
                <input
                  type="number"
                  min={1}
                  value={form.daily_target}
                  onChange={(e) =>
                    setForm({ ...form, daily_target: Number(e.target.value) })
                  }
                  className="w-full rounded-lg border border-[#2a2a5a] bg-[#0a0a1a] px-3 py-2 text-sm text-white focus:border-[#00e676] focus:outline-none"
                />
              </div>

              <div>
                <label className="mb-1 block text-xs text-[#8888aa]">
                  체류시간 (초) - 최소 / 최대
                </label>
                <div className="flex gap-2">
                  <input
                    type="number"
                    min={5}
                    value={form.dwell_time_min}
                    onChange={(e) =>
                      setForm({
                        ...form,
                        dwell_time_min: Number(e.target.value),
                      })
                    }
                    className="w-full rounded-lg border border-[#2a2a5a] bg-[#0a0a1a] px-3 py-2 text-sm text-white focus:border-[#00e676] focus:outline-none"
                  />
                  <input
                    type="number"
                    min={5}
                    value={form.dwell_time_max}
                    onChange={(e) =>
                      setForm({
                        ...form,
                        dwell_time_max: Number(e.target.value),
                      })
                    }
                    className="w-full rounded-lg border border-[#2a2a5a] bg-[#0a0a1a] px-3 py-2 text-sm text-white focus:border-[#00e676] focus:outline-none"
                  />
                </div>
              </div>

              {/* Industry Preset */}
              <div className="md:col-span-2">
                <label className="mb-1 block text-xs text-[#8888aa]">
                  업종별 시간 프리셋
                </label>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(INDUSTRY_PRESETS).map(([key, preset]) => (
                    <button
                      key={key}
                      type="button"
                      onClick={() => setForm({ ...form, preset: key })}
                      className={`rounded-lg border px-3 py-1.5 text-xs transition-colors ${
                        form.preset === key
                          ? "border-[#448aff] bg-[#448aff]/10 text-[#448aff]"
                          : "border-[#2a2a5a] text-[#8888aa] hover:border-[#448aff]/50"
                      }`}
                    >
                      {preset.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Preset Visualization */}
              <div className="md:col-span-2">
                <div className="flex h-20 items-end gap-px rounded-lg bg-[#0a0a1a] p-2">
                  {selectedPreset.weights.map((w, i) => {
                    const maxW = Math.max(...selectedPreset.weights);
                    const h = (w / maxW) * 100;
                    return (
                      <div
                        key={i}
                        className="group relative flex-1"
                        title={`${i}시: ${((w / selectedPreset.weights.reduce((a, b) => a + b, 0)) * form.daily_target).toFixed(0)}회`}
                      >
                        <div
                          className="w-full rounded-t bg-[#448aff]/60 transition-all hover:bg-[#448aff]"
                          style={{ height: `${h}%` }}
                        />
                      </div>
                    );
                  })}
                </div>
                <div className="mt-1 flex justify-between text-[10px] text-[#555]">
                  <span>0시</span>
                  <span>6시</span>
                  <span>12시</span>
                  <span>18시</span>
                  <span>23시</span>
                </div>
              </div>
            </div>

            {/* Paid Options */}
            <div className="mt-6 md:col-span-2">
              <div className="mb-3 flex items-center gap-2">
                <label className="text-sm font-bold text-white">유료 옵션 선택</label>
                <span className="rounded-full bg-[#16163a] px-2 py-0.5 text-[10px] text-[#8888aa]">L1 행동 패턴은 기본 포함</span>
              </div>
              <div className="grid gap-2 md:grid-cols-2 lg:grid-cols-3">
                {paidOptions
                  .filter((o) => !o.typeOnly || o.typeOnly === form.type)
                  .map((opt) => {
                    const checked = !!form.options[opt.key];
                    return (
                      <button
                        key={opt.key}
                        type="button"
                        onClick={() =>
                          setForm({
                            ...form,
                            options: { ...form.options, [opt.key]: !checked },
                          })
                        }
                        className={`flex items-center gap-3 rounded-lg border p-3 text-left transition-colors ${
                          checked
                            ? "border-[#00e676]/50 bg-[#00e676]/[0.06]"
                            : "border-[#2a2a5a] bg-[#0a0a1a] hover:border-[#448aff]/40"
                        }`}
                      >
                        <div className="text-xl">{opt.icon}</div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-1.5">
                            <span className={`text-xs font-bold ${checked ? "text-[#00e676]" : "text-white"}`}>{opt.name}</span>
                            {opt.layer && (
                              <span className="rounded px-1 py-0.5 text-[9px] font-bold" style={{ color: opt.color, background: `${opt.color}15` }}>{opt.layer}</span>
                            )}
                          </div>
                          <div className="text-[10px] text-[#8888aa] truncate">{opt.desc}</div>
                        </div>
                        <div className="text-xs font-bold whitespace-nowrap" style={{ color: opt.color }}>{opt.price}</div>
                        <div className={`flex h-5 w-5 shrink-0 items-center justify-center rounded border ${
                          checked ? "border-[#00e676] bg-[#00e676] text-black" : "border-[#555]"
                        }`}>
                          {checked && <span className="text-xs">✓</span>}
                        </div>
                      </button>
                    );
                  })}
              </div>
              {Object.values(form.options).some(Boolean) && (
                <div className="mt-2 flex items-center gap-2 text-xs text-[#8888aa]">
                  <span>선택된 옵션:</span>
                  {paidOptions.filter((o) => form.options[o.key]).map((o) => (
                    <span key={o.key} className="rounded-full px-2 py-0.5 text-[10px] font-bold" style={{ color: o.color, background: `${o.color}15` }}>
                      {o.name} {o.price}
                    </span>
                  ))}
                </div>
              )}
            </div>

            <div className="mt-4 flex justify-end">
              <button
                type="submit"
                disabled={submitting}
                className="rounded-lg bg-[#00e676] px-6 py-2 text-sm font-semibold text-black transition-colors hover:bg-[#00c853] disabled:opacity-50"
              >
                {submitting ? (editingId ? "수정 중..." : "등록 중...") : (editingId ? "캠페인 수정" : "캠페인 등록")}
              </button>
            </div>
          </form>
        )}

        {/* Campaign List — grouped by customer */}
        <div className="rounded-xl border border-[#2a2a5a] bg-[#111127] p-6">
          <h2 className="mb-4 text-lg font-semibold text-white">
            전체 캠페인 ({campaigns.length})
          </h2>

          {loading ? (
            <p className="py-8 text-center text-sm text-[#8888aa]">
              로딩 중...
            </p>
          ) : campaigns.length === 0 ? (
            <p className="py-8 text-center text-sm text-[#8888aa]">
              등록된 캠페인이 없습니다
            </p>
          ) : (
            <div className="space-y-4">
              {(() => {
                // Group campaigns by customer
                const customerMap = new Map<string, Campaign[]>();
                for (const c of campaigns) {
                  const list = customerMap.get(c.customer_name) || [];
                  list.push(c);
                  customerMap.set(c.customer_name, list);
                }
                return Array.from(customerMap.entries()).map(([customerName, customerCampaigns]) => {
                  const isCustomerOpen = expandedCustomer === customerName;
                  const activeCount = customerCampaigns.filter((c) => c.active).length;
                  const totalTarget = customerCampaigns.reduce((s, c) => s + (c.active ? c.daily_target : 0), 0);
                  const types = Array.from(new Set(customerCampaigns.map((c) => c.type)));

                  return (
                    <div key={customerName} className="rounded-lg border border-[#2a2a5a] overflow-hidden">
                      {/* Customer Header */}
                      <button
                        onClick={() => setExpandedCustomer(isCustomerOpen ? null : customerName)}
                        className={`flex w-full items-center justify-between p-4 text-left transition-colors ${
                          isCustomerOpen ? "bg-[#16163a] border-b border-[#2a2a5a]" : "bg-[#16163a]/50 hover:bg-[#16163a]"
                        }`}
                      >
                        <div className="flex items-center gap-3">
                          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#448aff]/15 text-lg font-bold text-[#448aff]">
                            {customerName.charAt(0)}
                          </div>
                          <div>
                            <div className="flex items-center gap-2">
                              <span className="font-semibold text-white">{customerName}</span>
                              <span className="rounded-full bg-[#448aff]/15 px-2 py-0.5 text-[10px] text-[#448aff]">
                                {customerCampaigns.length}개 캠페인
                              </span>
                              {types.map((t) => (
                                <span key={t} className="text-sm">
                                  {t === "blog" ? "📝" : t === "place" ? "📍" : "🛒"}
                                </span>
                              ))}
                            </div>
                            <div className="text-xs text-[#8888aa]">
                              활성 {activeCount}/{customerCampaigns.length}
                              {" · "}
                              일일 {totalTarget}회
                            </div>
                          </div>
                        </div>
                        <span className="text-xs text-[#8888aa]">
                          {isCustomerOpen ? "▲ 접기" : "▼ 펼치기"}
                        </span>
                      </button>

                      {/* Customer's campaigns */}
                      {isCustomerOpen && (
                        <div className="space-y-2 p-3 bg-[#0d0d25]">
                          {customerCampaigns.map((c) => {
                            const isExpanded = expandedId === c.id;
                            let weights: Record<number, number> = {};
                            try {
                              if (c.hourly_weights) {
                                const parsed = JSON.parse(c.hourly_weights);
                                weights = Object.fromEntries(
                                  Object.entries(parsed).map(([k, v]) => [Number(k), Number(v)])
                                );
                              }
                            } catch { /* ignore */ }
                            const maxWeight = Math.max(...Object.values(weights), 0.01);
                            const totalWeight = Object.values(weights).reduce((a, b) => a + b, 0) || 1;

                            const hourDist: Record<number, number> = {};
                            const sortedHours = Object.entries(weights)
                              .map(([h, w]) => ({ h: Number(h), w: Number(w) }))
                              .sort((a, b) => b.w - a.w);
                            if (c.daily_target <= 24) {
                              let assigned = 0;
                              for (const { h } of sortedHours) {
                                if (assigned >= c.daily_target) break;
                                hourDist[h] = 1;
                                assigned++;
                              }
                            } else {
                              let remaining = c.daily_target;
                              for (const { h, w } of sortedHours) {
                                const jobs = Math.round((w / totalWeight) * c.daily_target);
                                hourDist[h] = Math.min(jobs, remaining);
                                remaining -= hourDist[h];
                              }
                            }

                            return (
                            <div key={c.id}>
                              <div
                                onClick={() => setExpandedId(isExpanded ? null : c.id)}
                                className={`flex items-center justify-between rounded-lg border p-4 transition-colors cursor-pointer ${
                                  c.active
                                    ? isExpanded
                                      ? "border-[#448aff] bg-[#16163a]"
                                      : "border-[#2a2a5a] bg-[#16163a]/50 hover:border-[#448aff]/50"
                                    : "border-[#2a2a5a]/50 bg-[#0a0a1a] opacity-60"
                                }`}
                              >
                                <div className="flex items-center gap-4">
                                  <div
                                    className={`flex h-10 w-10 items-center justify-center rounded-lg text-lg ${
                                      c.type === "place"
                                        ? "bg-[#448aff]/15"
                                        : c.type === "blog"
                                        ? "bg-[#ffd740]/15"
                                        : "bg-[#00e676]/15"
                                    }`}
                                  >
                                    {c.type === "place" ? "📍" : c.type === "blog" ? "📝" : "🛒"}
                                  </div>
                                  <div>
                                    <div className="flex items-center gap-2">
                                      <span className="font-medium text-white">
                                        {c.keyword}
                                      </span>
                                      <span
                                        className={`rounded-full px-2 py-0.5 text-[10px] ${
                                          c.active
                                            ? "bg-[#00e676]/15 text-[#00e676]"
                                            : "bg-[#ff5252]/15 text-[#ff5252]"
                                        }`}
                                      >
                                        {c.active ? "활성" : "비활성"}
                                      </span>
                                      {c.engage_like ? (
                                        <span className="rounded-full bg-[#ff6eb4]/15 text-[#ff6eb4] px-2 py-0.5 text-[10px]">
                                          👍 공감ON
                                        </span>
                                      ) : null}
                                      <LayerBadges options={c.options} />
                                    </div>
                                    <div className="text-xs text-[#8888aa]">
                                      <span className="text-[#e0e0e0]">{c.product_name}</span>
                                      {" · "}
                                      일일 {c.daily_target}회
                                      {" · "}
                                      체류 {c.dwell_time_min}~{c.dwell_time_max}초
                                    </div>
                                  </div>
                                </div>

                                <div className="flex items-center gap-2">
                                  <span className="text-xs text-[#8888aa] mr-2">
                                    {isExpanded ? "▲ 접기" : "▼ 상세"}
                                  </span>
                                  <button
                                    onClick={(e) => { e.stopPropagation(); startEdit(c); }}
                                    className="rounded-lg border border-[#448aff]/30 p-2 text-[#448aff] transition-colors hover:bg-[#448aff]/10"
                                    title="수정"
                                  >
                                    <Pencil className="h-4 w-4" />
                                  </button>
                                  <button
                                    onClick={(e) => { e.stopPropagation(); toggleCampaign(c.id, !c.active); }}
                                    className={`rounded-lg border p-2 transition-colors ${
                                      c.active
                                        ? "border-[#ffd740]/30 text-[#ffd740] hover:bg-[#ffd740]/10"
                                        : "border-[#00e676]/30 text-[#00e676] hover:bg-[#00e676]/10"
                                    }`}
                                    title={c.active ? "비활성화" : "활성화"}
                                  >
                                    {c.active ? (
                                      <PowerOff className="h-4 w-4" />
                                    ) : (
                                      <Power className="h-4 w-4" />
                                    )}
                                  </button>
                                  <button
                                    onClick={(e) => { e.stopPropagation(); deleteCampaign(c.id); }}
                                    className="rounded-lg border border-[#ff5252]/30 p-2 text-[#ff5252] transition-colors hover:bg-[#ff5252]/10"
                                    title="삭제"
                                  >
                                    <Trash2 className="h-4 w-4" />
                                  </button>
                                </div>
                              </div>

                              {/* Expanded Detail */}
                              {isExpanded && (
                                <div className="mt-1 rounded-lg border border-[#448aff]/30 bg-[#0d0d25] p-5 space-y-5">
                                  <div>
                                    <h3 className="text-sm font-semibold text-[#448aff] mb-3">캠페인 설정</h3>
                                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                                      <DetailCard label="캠페인 ID" value={`#${c.id}`} />
                                      <DetailCard label="타입" value={c.type === "blog" ? "📝 블로그" : c.type === "place" ? "📍 플레이스" : "🛒 쇼핑"} />
                                      <DetailCard label="고객명" value={c.customer_name} />
                                      <DetailCard label="키워드" value={c.keyword} highlight />
                                      <DetailCard label="블로그명/상품명" value={c.product_name} />
                                      <DetailCard label="URL" value={c.product_url || "-"} small />
                                      <DetailCard label="일일 목표" value={`${c.daily_target}회`} highlight />
                                      <DetailCard label="체류시간" value={`${c.dwell_time_min}~${c.dwell_time_max}초`} />
                                      <DetailCard label="상태" value={c.active ? "✅ 활성" : "⛔ 비활성"} />
                                      <DetailCard label="공감" value={c.engage_like ? "👍 ON" : "OFF"} highlight={!!c.engage_like} />
                                      <DetailCard label="등록일" value={c.created_at?.split(" ")[0] || "-"} />
                                    </div>

                                    <div className="mt-3 rounded-lg border border-[#2a2a5a]/50 bg-[#111127] p-3">
                                      <div className="text-[10px] text-[#8888aa] mb-2">적용 레이어</div>
                                      <div className="flex items-center gap-3">
                                        <LayerBadges options={c.options} />
                                        {parseOptions(c.options).length > 0 && (
                                          <div className="flex flex-wrap gap-1.5">
                                            {parseOptions(c.options).map((key) => {
                                              const opt = paidOptions.find((o) => o.key === key);
                                              if (!opt) return null;
                                              return (
                                                <span key={key} className="rounded-full px-2 py-0.5 text-[10px] font-bold" style={{ color: opt.color, background: `${opt.color}15` }}>
                                                  {opt.icon} {opt.name}
                                                </span>
                                              );
                                            })}
                                          </div>
                                        )}
                                        {parseOptions(c.options).length === 0 && (
                                          <span className="text-[11px] text-[#555]">L1 기본만 적용 (유료 옵션 없음)</span>
                                        )}
                                      </div>
                                    </div>
                                  </div>

                                  <div>
                                    <h3 className="text-sm font-semibold text-[#448aff] mb-3">
                                      시간대별 트래픽 스케줄 (24시간)
                                    </h3>
                                    <div className="rounded-lg bg-[#0a0a1a] p-4">
                                      <div className="flex h-28 items-end gap-[3px]">
                                        {Array.from({ length: 24 }, (_, h) => {
                                          const w = weights[h] || 0;
                                          const pct = (w / maxWeight) * 100;
                                          const jobs = hourDist[h] || 0;
                                          const isActive = w > 0.5;
                                          return (
                                            <div key={h} className="group relative flex-1 h-full flex flex-col items-center justify-end">
                                              <div className="absolute -top-10 left-1/2 -translate-x-1/2 hidden group-hover:block z-10 whitespace-nowrap rounded bg-[#222] px-2 py-1 text-[10px] text-white shadow-lg">
                                                {h}시: 가중치 {w.toFixed(2)}{jobs > 0 && ` · ${jobs}건 배정`}
                                              </div>
                                              <div
                                                className={`w-full rounded-t transition-all ${
                                                  jobs > 0
                                                    ? "bg-[#00e676]"
                                                    : isActive
                                                    ? "bg-[#448aff]/60 hover:bg-[#448aff]"
                                                    : "bg-[#2a2a5a]/40"
                                                }`}
                                                style={{ height: `${Math.max(pct, 2)}%` }}
                                              />
                                              {jobs > 0 && (
                                                <span className="mt-0.5 text-[8px] font-bold text-[#00e676]">{jobs}</span>
                                              )}
                                            </div>
                                          );
                                        })}
                                      </div>
                                      <div className="mt-1 flex justify-between text-[10px] text-[#555]">
                                        {[0, 3, 6, 9, 12, 15, 18, 21].map((h) => (
                                          <span key={h}>{h}시</span>
                                        ))}
                                      </div>
                                    </div>
                                    <div className="mt-2 flex flex-wrap gap-3 text-[11px] text-[#8888aa]">
                                      <span className="flex items-center gap-1">
                                        <span className="inline-block h-2.5 w-2.5 rounded-sm bg-[#00e676]" /> 잡 배정됨
                                      </span>
                                      <span className="flex items-center gap-1">
                                        <span className="inline-block h-2.5 w-2.5 rounded-sm bg-[#448aff]/60" /> 가중치만 있음
                                      </span>
                                      <span className="flex items-center gap-1">
                                        <span className="inline-block h-2.5 w-2.5 rounded-sm bg-[#2a2a5a]/40" /> 비활성 시간대
                                      </span>
                                      <span className="ml-auto text-[#e0e0e0]">
                                        주요 시간대: {sortedHours.filter(s => s.w >= 1.0).map(s => `${s.h}시`).join(", ") || "없음"}
                                      </span>
                                    </div>
                                  </div>
                                </div>
                              )}
                            </div>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  );
                });
              })()}
            </div>
          )}
        </div>
      </main>
    </>
  );
}

function DetailCard({
  label,
  value,
  highlight = false,
  small = false,
}: {
  label: string;
  value: string;
  highlight?: boolean;
  small?: boolean;
}) {
  return (
    <div className="rounded-lg border border-[#2a2a5a]/50 bg-[#111127] px-3 py-2">
      <div className="text-[10px] text-[#8888aa] mb-0.5">{label}</div>
      <div
        className={`${small ? "text-[11px] break-all" : "text-sm"} ${
          highlight ? "text-[#00e676] font-semibold" : "text-white"
        }`}
      >
        {value}
      </div>
    </div>
  );
}
