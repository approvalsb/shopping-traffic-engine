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
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [history, setHistory] = useState<TrackingEntry[]>([]);
  const [latest, setLatest] = useState<TrackingEntry | null>(null);
  const [trend, setTrend] = useState<string>("stable");
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState(30);

  // Fetch campaign list
  const fetchCampaigns = useCallback(async () => {
    try {
      const res = await fetch("/api/tracking");
      if (res.ok) {
        const data = await res.json();
        setCampaigns(data.campaigns || []);
        // Auto-select first campaign
        if (data.campaigns?.length > 0 && !selectedId) {
          setSelectedId(data.campaigns[0].id);
        }
      }
    } catch {
      // silently handle
    } finally {
      setLoading(false);
    }
  }, [selectedId]);

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

  // Bar chart: show rank history (lower = better, so invert for visual)
  const maxRank = Math.max(
    50,
    ...history.filter((h) => h.rank !== null).map((h) => h.rank as number)
  );

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

        {/* Campaign Selector + Period */}
        <div className="mb-6 flex flex-wrap items-center gap-3">
          <div className="flex-1 min-w-[200px]">
            <label className="mb-1 block text-xs text-[#8888aa]">캠페인 선택</label>
            <select
              value={selectedId ?? ""}
              onChange={(e) => setSelectedId(Number(e.target.value) || null)}
              className="w-full rounded-lg border border-[#2a2a5a] bg-[#0a0a1a] px-3 py-2 text-sm text-white focus:border-[#00e676] focus:outline-none"
            >
              <option value="">캠페인을 선택하세요</option>
              {campaigns.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.customer_name} — {c.keyword} ({c.type})
                </option>
              ))}
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

        {loading ? (
          <p className="py-16 text-center text-sm text-[#8888aa]">로딩 중...</p>
        ) : !selectedId ? (
          <div className="rounded-xl border border-[#2a2a5a] bg-[#111127] p-12 text-center">
            <Search className="mx-auto mb-3 h-10 w-10 text-[#8888aa]" />
            <p className="text-sm text-[#8888aa]">
              캠페인을 선택하면 순위 추적 결과를 확인할 수 있습니다.
            </p>
            <p className="mt-1 text-xs text-[#555]">
              CLI에서 <code className="rounded bg-[#16163a] px-1.5 py-0.5 text-[#ffd740]">python rank_tracker.py --campaign-id N</code>으로 추적을 실행하세요.
            </p>
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

            {/* Rank History Bar Chart */}
            <div className="rounded-xl border border-[#2a2a5a] bg-[#111127] p-6">
              <h2 className="mb-4 text-lg font-semibold text-white">순위 변화 추이</h2>
              {history.length === 0 ? (
                <p className="py-8 text-center text-sm text-[#8888aa]">
                  아직 추적 데이터가 없습니다. rank_tracker.py를 실행하세요.
                </p>
              ) : (
                <>
                  <div className="flex items-end gap-1" style={{ height: 200 }}>
                    {[...history].reverse().map((entry, idx) => {
                      const rank = entry.rank;
                      if (rank === null) {
                        return (
                          <div key={idx} className="group relative flex flex-1 flex-col items-center justify-end" style={{ height: "100%" }}>
                            <div className="w-full rounded-t bg-[#2a2a5a]/50" style={{ height: "10%" }} />
                            <div className="absolute -top-6 hidden rounded bg-[#16163a] px-2 py-1 text-[10px] text-[#8888aa] group-hover:block whitespace-nowrap">
                              {entry.checked_at?.split(" ")[0] ?? ""}: 미발견
                            </div>
                          </div>
                        );
                      }
                      // Invert: lower rank = taller bar
                      const pct = Math.max(5, ((maxRank - rank + 1) / maxRank) * 100);
                      const color =
                        rank <= 10 ? "#00e676" : rank <= 30 ? "#ffd740" : "#ff5252";
                      return (
                        <div
                          key={idx}
                          className="group relative flex flex-1 flex-col items-center justify-end"
                          style={{ height: "100%" }}
                        >
                          <div
                            className="w-full rounded-t transition-all hover:opacity-80"
                            style={{ height: `${pct}%`, backgroundColor: `${color}cc` }}
                          />
                          <div className="absolute -top-6 hidden rounded bg-[#16163a] px-2 py-1 text-[10px] text-white group-hover:block whitespace-nowrap z-10">
                            {entry.checked_at?.split(" ")[0] ?? ""}: {rank}위
                          </div>
                        </div>
                      );
                    })}
                  </div>
                  <div className="mt-2 flex justify-between text-[10px] text-[#555]">
                    <span>{history[history.length - 1]?.checked_at?.split(" ")[0] ?? ""}</span>
                    <span>{history[0]?.checked_at?.split(" ")[0] ?? ""}</span>
                  </div>
                  {/* Legend */}
                  <div className="mt-3 flex items-center gap-4 text-[10px] text-[#8888aa]">
                    <span className="flex items-center gap-1">
                      <span className="inline-block h-2 w-2 rounded-full bg-[#00e676]" /> 1~10위
                    </span>
                    <span className="flex items-center gap-1">
                      <span className="inline-block h-2 w-2 rounded-full bg-[#ffd740]" /> 11~30위
                    </span>
                    <span className="flex items-center gap-1">
                      <span className="inline-block h-2 w-2 rounded-full bg-[#ff5252]" /> 30위+
                    </span>
                    <span className="ml-auto text-[#555]">* 막대가 높을수록 순위가 높음</span>
                  </div>
                </>
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
