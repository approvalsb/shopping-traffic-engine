"use client";

import { useEffect, useState, useCallback } from "react";
import { Nav } from "@/components/nav";
import { TrendingUp, TrendingDown, Search, BarChart3, Minus, Clock, RefreshCw } from "lucide-react";

interface TrackingEntry {
  rank: number | null;
  page: number;
  total_results: string;
  checked_at: string;
  keyword: string;
  target: string;
  type: string;
  campaign_id?: number;
  customer_name?: string;
}

interface CampaignSummary {
  id: number;
  customer_name: string;
  keyword: string;
  type: string;
  latest_rank: number | null;
  trend: string;
}

export default function TrackingPage() {
  const [campaigns, setCampaigns] = useState<CampaignSummary[]>([]);
  const [selectedCustomer, setSelectedCustomer] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [history, setHistory] = useState<TrackingEntry[]>([]);
  const [latest, setLatest] = useState<TrackingEntry | null>(null);
  const [trend, setTrend] = useState<string>("stable");
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState(30);

  // Group campaigns by customer
  const customers = Array.from(new Set(campaigns.map((c) => c.customer_name)));
  const customerCampaigns = campaigns.filter(
    (c) => c.customer_name === selectedCustomer
  );

  // Fetch campaign list
  const fetchCampaigns = useCallback(async () => {
    try {
      const res = await fetch("/api/tracking");
      if (res.ok) {
        const data = await res.json();
        const list: CampaignSummary[] = data.campaigns || [];
        setCampaigns(list);
        // Auto-select first customer
        if (list.length > 0 && !selectedCustomer) {
          const firstCustomer = list[0].customer_name;
          setSelectedCustomer(firstCustomer);
          setSelectedId(list[0].id);
        }
      }
    } catch {
      // silently handle
    } finally {
      setLoading(false);
    }
  }, [selectedCustomer]);

  // Fetch tracking data for selected campaign
  const fetchTracking = useCallback(async () => {
    if (!selectedId) return;
    try {
      const res = await fetch(`/api/tracking?campaignId=${selectedId}&days=${days}`);
      if (res.ok) {
        const data = await res.json();
        setHistory(data.history || []);
        setLatest(data.latest || null);
        setTrend(data.trend || "stable");
      }
    } catch {
      // silently handle
    }
  }, [selectedId, days]);

  useEffect(() => {
    fetchCampaigns();
  }, [fetchCampaigns]);

  useEffect(() => {
    fetchTracking();
  }, [fetchTracking]);

  // When customer changes, auto-select first campaign of that customer
  const handleCustomerChange = (name: string) => {
    setSelectedCustomer(name);
    const first = campaigns.find((c) => c.customer_name === name);
    setSelectedId(first?.id ?? null);
  };

  const rankColor = (rank: number | null) => {
    if (rank === null) return "text-[#8888aa]";
    if (rank <= 10) return "text-[#00e676]";
    if (rank <= 30) return "text-[#ffd740]";
    return "text-[#ff5252]";
  };

  const rankBg = (rank: number | null) => {
    if (rank === null) return "bg-[#8888aa]/10 border-[#8888aa]/30";
    if (rank <= 10) return "bg-[#00e676]/10 border-[#00e676]/30";
    if (rank <= 30) return "bg-[#ffd740]/10 border-[#ffd740]/30";
    return "bg-[#ff5252]/10 border-[#ff5252]/30";
  };

  const TrendIcon = trend === "up" ? TrendingUp : trend === "down" ? TrendingDown : Minus;
  const trendColor = trend === "up" ? "text-[#00e676]" : trend === "down" ? "text-[#ff5252]" : "text-[#8888aa]";
  const trendLabel = trend === "up" ? "상승 중" : trend === "down" ? "하락 중" : "유지";

  // Before/After comparison
  const firstEntry = history.length > 0 ? history[history.length - 1] : null;
  const lastEntry = history.length > 0 ? history[0] : null;

  return (
    <>
      <Nav />
      <main className="mx-auto max-w-7xl px-4 pt-20 pb-12">
        <div className="mb-6 flex items-center justify-between">
          <h1 className="text-2xl font-bold text-white">
            <BarChart3 className="mr-2 inline h-6 w-6 text-[#00e676]" />
            성과 추적
          </h1>
          <button
            onClick={() => { fetchCampaigns(); fetchTracking(); }}
            className="flex items-center gap-1.5 rounded-lg border border-[#2a2a5a] px-3 py-1.5 text-sm text-[#8888aa] transition-colors hover:bg-[#16163a] hover:text-white"
          >
            <RefreshCw className="h-4 w-4" />
            새로고침
          </button>
        </div>

        {/* Customer Selector + Period */}
        <div className="mb-4 flex flex-wrap items-center gap-3">
          <div className="flex-1 min-w-[200px]">
            <label className="mb-1 block text-xs text-[#8888aa]">고객 선택</label>
            <select
              value={selectedCustomer ?? ""}
              onChange={(e) => handleCustomerChange(e.target.value)}
              className="w-full rounded-lg border border-[#2a2a5a] bg-[#0a0a1a] px-3 py-2 text-sm text-white focus:border-[#00e676] focus:outline-none"
            >
              <option value="">고객을 선택하세요</option>
              {customers.map((name) => {
                const count = campaigns.filter((c) => c.customer_name === name).length;
                return (
                  <option key={name} value={name}>
                    {name} ({count}개 키워드)
                  </option>
                );
              })}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs text-[#8888aa]">조회 기간</label>
            <div className="flex gap-1">
              {[7, 14, 30].map((d) => (
                <button
                  key={d}
                  onClick={() => setDays(d)}
                  className={`rounded-lg border px-3 py-2 text-sm transition-colors ${
                    days === d
                      ? "border-[#00e676] bg-[#00e676]/10 text-[#00e676]"
                      : "border-[#2a2a5a] text-[#8888aa] hover:border-[#448aff]"
                  }`}
                >
                  {d}일
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Campaign Cards for selected customer */}
        {selectedCustomer && customerCampaigns.length > 0 && (
          <div className="mb-6 grid gap-2 grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
            {customerCampaigns.map((c) => {
              const isActive = selectedId === c.id;
              const rColor = c.latest_rank === null ? "#8888aa"
                : c.latest_rank <= 10 ? "#00e676"
                : c.latest_rank <= 30 ? "#ffd740" : "#ff5252";
              return (
                <button
                  key={c.id}
                  onClick={() => setSelectedId(c.id)}
                  className={`rounded-xl border p-3 text-left transition-all ${
                    isActive
                      ? "border-[#00e676] bg-[#00e676]/5 ring-1 ring-[#00e676]/30"
                      : "border-[#2a2a5a] bg-[#111127] hover:border-[#448aff] hover:bg-[#16163a]"
                  }`}
                >
                  <p className="text-xs text-[#8888aa] truncate">{c.keyword}</p>
                  <div className="mt-1 flex items-baseline gap-2">
                    <span className="text-2xl font-black" style={{ color: rColor }}>
                      {c.latest_rank ?? "—"}
                    </span>
                    <span className="text-xs text-[#8888aa]">
                      {c.latest_rank !== null ? "위" : "미발견"}
                    </span>
                  </div>
                  <div className="mt-1 flex items-center gap-1 text-[10px]">
                    <span className={`rounded-full px-1.5 py-px font-medium ${
                      c.type === "blog" ? "bg-[#ffd740]/15 text-[#ffd740]"
                        : c.type === "place" ? "bg-[#448aff]/15 text-[#448aff]"
                        : "bg-[#00e676]/15 text-[#00e676]"
                    }`}>
                      {c.type === "blog" ? "블로그" : c.type === "place" ? "플레이스" : "쇼핑"}
                    </span>
                    {c.trend === "up" && <TrendingUp className="h-3 w-3 text-[#00e676]" />}
                    {c.trend === "down" && <TrendingDown className="h-3 w-3 text-[#ff5252]" />}
                  </div>
                </button>
              );
            })}
          </div>
        )}

        {loading ? (
          <p className="py-16 text-center text-sm text-[#8888aa]">로딩 중...</p>
        ) : !selectedCustomer ? (
          <div className="rounded-xl border border-[#2a2a5a] bg-[#111127] p-12 text-center">
            <Search className="mx-auto mb-3 h-10 w-10 text-[#8888aa]" />
            <p className="text-sm text-[#8888aa]">
              고객을 선택하면 키워드별 순위 추적 결과를 확인할 수 있습니다.
            </p>
          </div>
        ) : !selectedId ? (
          <div className="rounded-xl border border-[#2a2a5a] bg-[#111127] p-8 text-center">
            <p className="text-sm text-[#8888aa]">위에서 키워드를 선택하세요.</p>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Top Cards Row */}
            <div className="grid gap-4 md:grid-cols-3">
              {/* Current Rank Badge */}
              <div className={`rounded-xl border p-6 text-center ${rankBg(latest?.rank ?? null)}`}>
                <p className="mb-1 text-xs text-[#8888aa]">현재 순위</p>
                <p className={`text-5xl font-black ${rankColor(latest?.rank ?? null)}`}>
                  {latest?.rank ?? "—"}
                </p>
                <p className="mt-1 text-xs text-[#8888aa]">
                  {latest?.rank !== null && latest?.rank !== undefined
                    ? latest.rank <= 10
                      ? "TOP 10"
                      : latest.rank <= 30
                      ? "TOP 30"
                      : `${latest.rank}위`
                    : "측정 전"}
                </p>
              </div>

              {/* Trend Card */}
              <div className="rounded-xl border border-[#2a2a5a] bg-[#111127] p-6 text-center">
                <p className="mb-1 text-xs text-[#8888aa]">추세</p>
                <TrendIcon className={`mx-auto h-10 w-10 ${trendColor}`} />
                <p className={`mt-2 text-lg font-bold ${trendColor}`}>{trendLabel}</p>
                <p className="mt-1 text-xs text-[#8888aa]">
                  최근 {Math.min(history.length, 3)}회 기준
                </p>
              </div>

              {/* Last Checked */}
              <div className="rounded-xl border border-[#2a2a5a] bg-[#111127] p-6 text-center">
                <p className="mb-1 text-xs text-[#8888aa]">마지막 체크</p>
                <Clock className="mx-auto h-10 w-10 text-[#448aff]" />
                <p className="mt-2 text-sm font-medium text-white">
                  {latest?.checked_at ?? "—"}
                </p>
                <p className="mt-1 text-xs text-[#8888aa]">
                  {latest?.keyword ? `키워드: ${latest.keyword}` : ""}
                </p>
              </div>
            </div>

            {/* Before / After Card */}
            {firstEntry && lastEntry && (
              <div className="rounded-xl border border-[#2a2a5a] bg-[#111127] p-6">
                <h2 className="mb-4 text-lg font-semibold text-white">Before / After 비교</h2>
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="rounded-lg border border-[#2a2a5a] bg-[#0a0a1a] p-4 text-center">
                    <p className="text-xs text-[#8888aa]">첫 측정 ({firstEntry.checked_at?.split(" ")[0] ?? ""})</p>
                    <p className={`mt-1 text-3xl font-black ${rankColor(firstEntry.rank)}`}>
                      {firstEntry.rank ?? "—"}
                      <span className="text-base font-normal text-[#8888aa]">위</span>
                    </p>
                  </div>
                  <div className="rounded-lg border border-[#2a2a5a] bg-[#0a0a1a] p-4 text-center">
                    <p className="text-xs text-[#8888aa]">최근 측정 ({lastEntry.checked_at?.split(" ")[0] ?? ""})</p>
                    <p className={`mt-1 text-3xl font-black ${rankColor(lastEntry.rank)}`}>
                      {lastEntry.rank ?? "—"}
                      <span className="text-base font-normal text-[#8888aa]">위</span>
                    </p>
                  </div>
                </div>
                {firstEntry.rank !== null && lastEntry.rank !== null && (
                  <div className="mt-3 text-center">
                    {(() => {
                      const diff = (firstEntry.rank as number) - (lastEntry.rank as number);
                      if (diff > 0)
                        return (
                          <span className="text-sm font-bold text-[#00e676]">
                            <TrendingUp className="mr-1 inline h-4 w-4" />
                            {diff}단계 상승
                          </span>
                        );
                      if (diff < 0)
                        return (
                          <span className="text-sm font-bold text-[#ff5252]">
                            <TrendingDown className="mr-1 inline h-4 w-4" />
                            {Math.abs(diff)}단계 하락
                          </span>
                        );
                      return <span className="text-sm text-[#8888aa]">변화 없음</span>;
                    })()}
                  </div>
                )}
              </div>
            )}

            {/* Rank History Line Chart */}
            <div className="rounded-xl border border-[#2a2a5a] bg-[#111127] p-6">
              <h2 className="mb-4 text-lg font-semibold text-white">순위 변화 추이</h2>
              {history.length === 0 ? (
                <p className="py-8 text-center text-sm text-[#8888aa]">
                  아직 추적 데이터가 없습니다. rank_tracker.py를 실행하세요.
                </p>
              ) : (
                <RankLineChart history={history} />
              )}
            </div>

            {/* History Table */}
            <div className="rounded-xl border border-[#2a2a5a] bg-[#111127] p-6">
              <h2 className="mb-4 text-lg font-semibold text-white">상세 기록</h2>
              {history.length === 0 ? (
                <p className="py-4 text-center text-sm text-[#8888aa]">기록 없음</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-[#2a2a5a] text-left text-xs text-[#8888aa]">
                        <th className="pb-2 pr-4">일시</th>
                        <th className="pb-2 pr-4">키워드</th>
                        <th className="pb-2 pr-4">순위</th>
                        <th className="pb-2 pr-4">페이지</th>
                        <th className="pb-2">타입</th>
                      </tr>
                    </thead>
                    <tbody>
                      {history.map((h, idx) => (
                        <tr key={idx} className="border-b border-[#2a2a5a]/50">
                          <td className="py-2 pr-4 text-[#8888aa]">{h.checked_at}</td>
                          <td className="py-2 pr-4 text-white">{h.keyword}</td>
                          <td className={`py-2 pr-4 font-bold ${rankColor(h.rank)}`}>
                            {h.rank ?? "미발견"}
                          </td>
                          <td className="py-2 pr-4 text-[#8888aa]">{h.page || "—"}</td>
                          <td className="py-2 text-[#8888aa]">{h.type}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        )}
      </main>
    </>
  );
}

/* ──────────────────────────────────────────────
   SVG Line Chart for Rank History
   ────────────────────────────────────────────── */
function RankLineChart({ history }: { history: TrackingEntry[] }) {
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);

  // Deduplicate by date (keep last entry per day)
  const byDay = new Map<string, TrackingEntry>();
  for (const h of [...history].reverse()) {
    const day = h.checked_at?.split(" ")[0] ?? "";
    byDay.set(day, h);
  }
  const daily = Array.from(byDay.values());

  // Chart dimensions
  const W = 700, H = 220;
  const padL = 40, padR = 20, padT = 20, padB = 35;
  const chartW = W - padL - padR;
  const chartH = H - padT - padB;

  // Y-axis: rank 1 (top) to 50 (bottom)
  const yMin = 1, yMax = 50;
  const yTicks = [1, 10, 20, 30, 40, 50];

  const toY = (rank: number) =>
    padT + ((rank - yMin) / (yMax - yMin)) * chartH;
  const toX = (idx: number) =>
    padL + (daily.length === 1 ? chartW / 2 : (idx / (daily.length - 1)) * chartW);

  // Build points (only ranked entries)
  const points = daily.map((entry, idx) => ({
    x: toX(idx),
    y: entry.rank !== null ? toY(Math.min(entry.rank, yMax)) : null,
    rank: entry.rank,
    date: entry.checked_at?.split(" ")[0] ?? "",
    entry,
    idx,
  }));

  // Build line path (skip nulls, create segments)
  const segments: string[] = [];
  let currentPath = "";
  for (const p of points) {
    if (p.y !== null) {
      if (!currentPath) {
        currentPath = `M${p.x},${p.y}`;
      } else {
        currentPath += ` L${p.x},${p.y}`;
      }
    } else {
      if (currentPath) {
        segments.push(currentPath);
        currentPath = "";
      }
    }
  }
  if (currentPath) segments.push(currentPath);

  // Build area path (for gradient fill)
  const areaSegments: string[] = [];
  let areaStart: number | null = null;
  let areaPath = "";
  for (const p of points) {
    if (p.y !== null) {
      if (!areaPath) {
        areaStart = p.x;
        areaPath = `M${p.x},${padT + chartH} L${p.x},${p.y}`;
      } else {
        areaPath += ` L${p.x},${p.y}`;
      }
    } else {
      if (areaPath && areaStart !== null) {
        const lastRanked = points.filter((pp, pi) => pi < p.idx && pp.y !== null).pop();
        if (lastRanked) {
          areaPath += ` L${lastRanked.x},${padT + chartH} Z`;
          areaSegments.push(areaPath);
        }
        areaPath = "";
        areaStart = null;
      }
    }
  }
  if (areaPath) {
    const lastRanked = [...points].reverse().find((pp) => pp.y !== null);
    if (lastRanked) {
      areaPath += ` L${lastRanked.x},${padT + chartH} Z`;
      areaSegments.push(areaPath);
    }
  }

  const dotColor = (rank: number | null) => {
    if (rank === null) return "#555";
    if (rank <= 10) return "#00e676";
    if (rank <= 30) return "#ffd740";
    return "#ff5252";
  };

  return (
    <div>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="w-full"
        style={{ maxHeight: 280 }}
        onMouseLeave={() => setHoveredIdx(null)}
      >
        <defs>
          <linearGradient id="rankGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#00e676" stopOpacity="0.3" />
            <stop offset="100%" stopColor="#00e676" stopOpacity="0.02" />
          </linearGradient>
        </defs>

        {/* Grid lines */}
        {yTicks.map((tick) => (
          <g key={tick}>
            <line
              x1={padL} y1={toY(tick)} x2={W - padR} y2={toY(tick)}
              stroke="#2a2a5a" strokeWidth="0.5"
              strokeDasharray={tick === 1 ? "0" : "4,4"}
            />
            <text
              x={padL - 6} y={toY(tick) + 3}
              fill="#555" fontSize="10" textAnchor="end"
            >
              {tick}위
            </text>
          </g>
        ))}

        {/* Area fill */}
        {areaSegments.map((d, i) => (
          <path key={`area-${i}`} d={d} fill="url(#rankGrad)" />
        ))}

        {/* Line */}
        {segments.map((d, i) => (
          <path
            key={`line-${i}`} d={d}
            fill="none" stroke="#00e676" strokeWidth="2.5"
            strokeLinecap="round" strokeLinejoin="round"
          />
        ))}

        {/* Null markers (미발견) */}
        {points.filter((p) => p.y === null).map((p) => (
          <g key={`null-${p.idx}`}>
            <line
              x1={p.x} y1={padT} x2={p.x} y2={padT + chartH}
              stroke="#ff5252" strokeWidth="0.5" strokeDasharray="3,3" opacity="0.4"
            />
            <text
              x={p.x} y={padT + chartH - 4}
              fill="#ff5252" fontSize="8" textAnchor="middle" opacity="0.6"
            >
              ×
            </text>
          </g>
        ))}

        {/* Data points */}
        {points.map((p) => {
          if (p.y === null) return null;
          const isHovered = hoveredIdx === p.idx;
          return (
            <g key={`dot-${p.idx}`}>
              {isHovered && (
                <circle cx={p.x} cy={p.y} r="8" fill={dotColor(p.rank)} opacity="0.2" />
              )}
              <circle
                cx={p.x} cy={p.y}
                r={isHovered ? 5 : 3.5}
                fill={dotColor(p.rank)}
                stroke="#111127" strokeWidth="2"
                className="cursor-pointer transition-all"
              />
            </g>
          );
        })}

        {/* Hover areas (invisible rect per point) */}
        {points.map((p) => (
          <rect
            key={`hover-${p.idx}`}
            x={p.x - (daily.length > 1 ? chartW / daily.length / 2 : 30)}
            y={padT}
            width={daily.length > 1 ? chartW / daily.length : 60}
            height={chartH}
            fill="transparent"
            onMouseEnter={() => setHoveredIdx(p.idx)}
          />
        ))}

        {/* X-axis date labels */}
        {points.filter((_, i) => {
          if (daily.length <= 7) return true;
          if (daily.length <= 14) return i % 2 === 0;
          return i % Math.ceil(daily.length / 7) === 0 || i === daily.length - 1;
        }).map((p) => (
          <text
            key={`xlabel-${p.idx}`}
            x={p.x} y={H - 5}
            fill="#555" fontSize="9" textAnchor="middle"
          >
            {p.date.slice(5)}
          </text>
        ))}

        {/* Hover tooltip */}
        {hoveredIdx !== null && (() => {
          const p = points[hoveredIdx];
          const label = p.rank !== null ? `${p.rank}위` : "미발견";
          const tipW = 90, tipH = 36;
          let tipX = p.x - tipW / 2;
          if (tipX < padL) tipX = padL;
          if (tipX + tipW > W - padR) tipX = W - padR - tipW;
          const tipY = (p.y !== null ? p.y : padT + chartH / 2) - tipH - 12;
          return (
            <g>
              <rect
                x={tipX} y={tipY}
                width={tipW} height={tipH}
                rx="6" fill="#16163a" stroke="#2a2a5a" strokeWidth="1"
              />
              <text x={tipX + tipW / 2} y={tipY + 14} fill="#8888aa" fontSize="10" textAnchor="middle">
                {p.date}
              </text>
              <text x={tipX + tipW / 2} y={tipY + 28} fill={dotColor(p.rank)} fontSize="13" fontWeight="bold" textAnchor="middle">
                {label}
              </text>
            </g>
          );
        })()}
      </svg>

      {/* Legend */}
      <div className="mt-2 flex items-center gap-4 text-[10px] text-[#8888aa]">
        <span className="flex items-center gap-1">
          <span className="inline-block h-2 w-2 rounded-full bg-[#00e676]" /> 1~10위
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block h-2 w-2 rounded-full bg-[#ffd740]" /> 11~30위
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block h-2 w-2 rounded-full bg-[#ff5252]" /> 30위+
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block h-1 w-3 border-t border-dashed border-[#ff5252] opacity-40" /> 미발견
        </span>
        <span className="ml-auto text-[#555]">* 위쪽일수록 순위가 높음</span>
      </div>
    </div>
  );
}
