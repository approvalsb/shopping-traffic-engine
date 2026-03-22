"use client";

import { Suspense, useEffect, useState, useCallback } from "react";
import { useSearchParams } from "next/navigation";
import { ArrowLeft, Printer, TrendingUp, TrendingDown, Minus } from "lucide-react";

/* -- Interfaces -- */

interface RelatedRanking {
  keyword: string;
  rank: number | null;
}

interface CampaignSummary {
  id: number;
  customer_name: string;
  keyword: string;
  type: string;
  latest_rank: number | null;
  trend: string;
}

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
  related_rankings?: RelatedRanking[];
}

interface KeywordStrategy {
  keyword: string;
  current_status: string;
  action: string;
}

interface CustomerStrategy {
  keyword_strategies: KeywordStrategy[];
  overall_strategy: string;
  generated_at: string;
}

interface CampaignStat {
  id: number;
  type: string;
  customer_name: string;
  keyword: string;
  daily_target: number;
  success: number;
  failed: number;
  pending: number;
  total: number;
}

interface CampaignRanking {
  campaign: CampaignSummary;
  history: TrackingEntry[];
  latest: TrackingEntry | null;
  trend: string;
}

/* -- Component -- */

export default function TrafficReportPage() {
  return (
    <Suspense
      fallback={
        <div style={{ minHeight: "100vh", background: "#0a0a1a", display: "flex", alignItems: "center", justifyContent: "center" }}>
          <div style={{ textAlign: "center" }}>
            <div style={{ width: 32, height: 32, border: "4px solid #333", borderTopColor: "#fff", borderRadius: "50%", animation: "spin 1s linear infinite", margin: "0 auto 16px" }} />
            <p style={{ color: "#8888aa", fontSize: 14 }}>보고서를 불러오는 중...</p>
          </div>
        </div>
      }
    >
      <TrafficReportContent />
    </Suspense>
  );
}

function TrafficReportContent() {
  const searchParams = useSearchParams();
  const customer = searchParams.get("customer") || "";
  const days = parseInt(searchParams.get("days") || "30", 10);

  const [rankings, setRankings] = useState<CampaignRanking[]>([]);
  const [trafficStats, setTrafficStats] = useState<CampaignStat[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [firstTrackedDate, setFirstTrackedDate] = useState<string | null>(null);
  const [strategy, setStrategy] = useState<CustomerStrategy | null>(null);

  const today = new Date().toISOString().split("T")[0];
  const periodStart = new Date(Date.now() - days * 86400000).toISOString().split("T")[0];

  const fetchData = useCallback(async () => {
    if (!customer) {
      setLoading(false);
      return;
    }

    try {
      setLoading(true);

      // 1. Get campaign list
      const campRes = await fetch("/api/tracking");
      const campData = await campRes.json();
      const allCampaigns: CampaignSummary[] = campData.campaigns || [];

      // Save strategy data
      const strategyMap = campData.strategy || {};
      if (strategyMap[customer]) {
        setStrategy(strategyMap[customer]);
      } else {
        setStrategy(null);
      }

      const filtered = allCampaigns.filter(
        (c) => c.customer_name === customer
      );

      // 2. Get ranking history for each campaign
      let earliestDate = "";
      const rankingResults: CampaignRanking[] = await Promise.all(
        filtered.map(async (campaign) => {
          try {
            const res = await fetch(
              `/api/tracking?campaignId=${campaign.id}&days=${days}`
            );
            const data = await res.json();
            const history: TrackingEntry[] = data.history || [];

            // Track earliest date
            if (history.length > 0) {
              const oldest = history[history.length - 1];
              const oldestDate = oldest.checked_at?.split(" ")[0] || "";
              if (oldestDate && (!earliestDate || oldestDate < earliestDate)) {
                earliestDate = oldestDate;
              }
            }

            return {
              campaign,
              history,
              latest: data.latest || null,
              trend: data.trend || "stable",
            };
          } catch {
            return { campaign, history: [], latest: null, trend: "stable" };
          }
        })
      );
      setRankings(rankingResults);
      setFirstTrackedDate(earliestDate || null);

      // 3. Get today's stats
      const statsRes = await fetch(`/api/stats?date=${today}`);
      if (statsRes.ok) {
        const statsData = await statsRes.json();
        const campaigns: CampaignStat[] = statsData.stats?.campaigns || [];
        const customerCampaigns = campaigns.filter(
          (c) => c.customer_name === customer
        );
        setTrafficStats(customerCampaigns);
      }

      setError(null);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "데이터를 불러올 수 없습니다");
    } finally {
      setLoading(false);
    }
  }, [customer, days, today]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  /* -- Computed values -- */
  const totalKeywords = rankings.length;
  const ranksWithValue = rankings
    .map((r) => r.campaign.latest_rank)
    .filter((r): r is number => r !== null);
  const avgRank =
    ranksWithValue.length > 0
      ? Math.round(
          ranksWithValue.reduce((a, b) => a + b, 0) / ranksWithValue.length
        )
      : null;

  const totalVisits = trafficStats.reduce((sum, c) => sum + c.success, 0);
  const totalJobs = trafficStats.reduce((sum, c) => sum + c.total, 0);
  const overallSuccessRate =
    totalJobs > 0 ? Math.round((totalVisits / totalJobs) * 100) : 0;

  const totalHistoryCount = rankings.reduce((sum, r) => sum + r.history.length, 0);

  const allUnranked = rankings.length > 0 && ranksWithValue.length === 0;

  // Calculate service days
  const serviceDays = firstTrackedDate
    ? Math.max(
        1,
        Math.ceil(
          (Date.now() - new Date(firstTrackedDate).getTime()) / 86400000
        )
      )
    : null;

  // Collect related rankings
  const relatedRankingsData = rankings
    .filter((r) => r.latest?.related_rankings && r.latest.related_rankings.length > 0)
    .map((r) => ({
      mainKeyword: r.campaign.keyword,
      related: r.latest!.related_rankings!,
    }));

  /* -- Helpers -- */
  const rankColor = (rank: number | null) => {
    if (rank === null) return "color: #999";
    if (rank <= 10) return "color: #16a34a";
    if (rank <= 30) return "color: #d97706";
    return "color: #dc2626";
  };

  const trendIcon = (trend: string) => {
    if (trend === "up") return <TrendingUp style={{ display: "inline", width: 14, height: 14, color: "#16a34a", verticalAlign: "middle" }} />;
    if (trend === "down") return <TrendingDown style={{ display: "inline", width: 14, height: 14, color: "#dc2626", verticalAlign: "middle" }} />;
    return <Minus style={{ display: "inline", width: 14, height: 14, color: "#999", verticalAlign: "middle" }} />;
  };

  const successRateColor = (rate: number) => {
    if (rate >= 80) return "#16a34a";
    if (rate >= 50) return "#d97706";
    return "#dc2626";
  };

  /* -- Empty / Error states -- */
  if (!customer) {
    return (
      <div style={{ minHeight: "100vh", background: "#0a0a1a", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <div style={{ textAlign: "center", color: "#8888aa" }}>
          <p style={{ fontSize: 18, marginBottom: 8 }}>고객명이 지정되지 않았습니다</p>
          <p style={{ fontSize: 13 }}>
            URL에 <code style={{ background: "#16163a", padding: "2px 6px", borderRadius: 4, color: "#ffd740" }}>?customer=고객명</code>을 추가하세요
          </p>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div style={{ minHeight: "100vh", background: "#0a0a1a", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <p style={{ color: "#8888aa", fontSize: 14 }}>보고서 생성 중...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ minHeight: "100vh", background: "#0a0a1a", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <div style={{ textAlign: "center", color: "#ff5252" }}>
          <p style={{ fontSize: 16, marginBottom: 8 }}>데이터 로딩 실패</p>
          <p style={{ fontSize: 13, color: "#8888aa" }}>{error}</p>
        </div>
      </div>
    );
  }

  if (rankings.length === 0 && trafficStats.length === 0) {
    return (
      <div style={{ minHeight: "100vh", background: "#0a0a1a", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <div style={{ textAlign: "center", color: "#8888aa" }}>
          <p style={{ fontSize: 18, marginBottom: 8 }}>데이터가 없습니다</p>
          <p style={{ fontSize: 13 }}>
            &quot;{customer}&quot; 고객의 캠페인이 존재하지 않습니다.
          </p>
          <a href="/tracking" style={{ display: "inline-block", marginTop: 16, color: "#448aff", fontSize: 13 }}>
            <ArrowLeft style={{ display: "inline", width: 14, height: 14, verticalAlign: "middle", marginRight: 4 }} />
            대시보드로 돌아가기
          </a>
        </div>
      </div>
    );
  }

  return (
    <>
      {/* -- Print styles -- */}
      <style>{`
        @media print {
          nav, .no-print { display: none !important; }
          body { background: white !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
          .screen-wrapper { background: white !important; padding: 0 !important; min-height: auto !important; }
          .report-page { box-shadow: none !important; margin: 0 !important; max-width: 100% !important; border-radius: 0 !important; }
          @page { margin: 15mm 10mm; size: A4; }
        }
      `}</style>

      {/* -- Screen wrapper (dark) -- */}
      <div className="screen-wrapper" style={{ minHeight: "100vh", background: "#0a0a1a", padding: "24px 16px" }}>
        {/* Top bar */}
        <div className="no-print" style={{ maxWidth: 800, margin: "0 auto 16px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <a href="/tracking" style={{ color: "#8888aa", fontSize: 13, textDecoration: "none", display: "flex", alignItems: "center", gap: 4 }}>
            <ArrowLeft style={{ width: 16, height: 16 }} />
            대시보드
          </a>
          <button
            onClick={() => window.print()}
            style={{ display: "flex", alignItems: "center", gap: 6, background: "#16163a", border: "1px solid #2a2a5a", color: "#fff", borderRadius: 8, padding: "8px 16px", fontSize: 13, cursor: "pointer" }}
          >
            <Printer style={{ width: 14, height: 14 }} />
            인쇄 / PDF
          </button>
        </div>

        {/* -- Report content (white, print-ready) -- */}
        <div className="report-page" style={{ maxWidth: 800, margin: "0 auto", background: "#fff", borderRadius: 12, boxShadow: "0 4px 24px rgba(0,0,0,0.3)", padding: "48px 40px", color: "#1a1a1a", fontFamily: "'Pretendard', -apple-system, sans-serif", lineHeight: 1.6 }}>

          {/* -- Header -- */}
          <div style={{ borderBottom: "3px solid #1a2a4a", paddingBottom: 24, marginBottom: 32 }}>
            <h1 style={{ fontSize: 28, fontWeight: 800, color: "#1a2a4a", margin: 0 }}>
              트래픽 종합 보고서
            </h1>
            <p style={{ fontSize: 18, fontWeight: 600, color: "#2563eb", margin: "8px 0 0" }}>
              {customer}
            </p>
            <div style={{ marginTop: 16, display: "flex", justifyContent: "space-between", alignItems: "flex-end", flexWrap: "wrap", gap: 8 }}>
              <div style={{ fontSize: 12, color: "#666" }}>
                <span>조회 기간: {periodStart} ~ {today}</span>
                <span style={{ margin: "0 12px", color: "#ccc" }}>|</span>
                <span>생성일: {today}</span>
              </div>
              <div style={{ fontSize: 11, color: "#999" }}>
                승인행정사사무소 | approval-admin.com
              </div>
            </div>
          </div>

          {/* -- Service Status Banner -- */}
          <div style={{
            marginBottom: 24,
            padding: "16px 24px",
            borderRadius: 8,
            border: "1px solid #bfdbfe",
            background: "linear-gradient(to right, #eff6ff, #ecfdf5)",
          }}>
            <p style={{ fontSize: 15, fontWeight: 600, color: "#1e40af", margin: 0 }}>
              {serviceDays !== null
                ? `서비스 시작 ${serviceDays}일차`
                : "데이터 수집 중"}
            </p>
            {allUnranked && (
              <p style={{ fontSize: 13, color: "#2563eb", margin: "4px 0 0" }}>
                순위 반영까지 보통 1~2주가 소요됩니다
              </p>
            )}
          </div>

          {/* -- Summary Cards -- */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 12, marginBottom: 32 }}>
            <SummaryCard label="추적 키워드 수" value={`${totalKeywords}개`} color="#2563eb" />
            <SummaryCard label="평균 순위" value={avgRank !== null ? `${avgRank}위` : "-"} color="#7c3aed" />
            <SummaryCard label="오늘 완료" value={`${totalVisits.toLocaleString()}회`} color="#16a34a" />
            <SummaryCard label="성공률" value={`${overallSuccessRate}%`} color={successRateColor(overallSuccessRate)} />
            <SummaryCard label="누적 추적 횟수" value={`${totalHistoryCount}`} color="#0891b2" />
          </div>

          {/* -- Keyword Ranking Table -- */}
          <div style={{ marginBottom: 32 }}>
            <h2 style={{ fontSize: 16, fontWeight: 700, color: "#1a2a4a", marginBottom: 12, paddingBottom: 8, borderBottom: "1px solid #e5e7eb" }}>
              키워드 순위 현황
            </h2>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr style={{ background: "#f8fafc" }}>
                  <th style={thStyle}>키워드</th>
                  <th style={{ ...thStyle, textAlign: "center" }}>현재 순위</th>
                  <th style={{ ...thStyle, textAlign: "center" }}>이전 순위</th>
                  <th style={{ ...thStyle, textAlign: "center" }}>변화</th>
                  <th style={{ ...thStyle, textAlign: "center" }}>추세</th>
                </tr>
              </thead>
              <tbody>
                {rankings.map((r) => {
                  const currentRank = r.latest?.rank ?? null;
                  const prevEntry = r.history.length > 1 ? r.history[1] : null;
                  const prevRank = prevEntry?.rank ?? null;
                  const diff =
                    currentRank !== null && prevRank !== null
                      ? prevRank - currentRank
                      : null;

                  return (
                    <tr key={r.campaign.id} style={{ borderBottom: "1px solid #f0f0f0" }}>
                      <td style={tdStyle}>
                        <span style={{ fontWeight: 500 }}>{r.campaign.keyword}</span>
                        <span style={{ fontSize: 11, color: "#999", marginLeft: 6 }}>({r.campaign.type})</span>
                      </td>
                      <td style={{ ...tdStyle, textAlign: "center" }}>
                        {currentRank !== null ? (
                          <span style={{
                            display: "inline-block",
                            padding: "2px 10px",
                            borderRadius: 12,
                            fontSize: 12,
                            fontWeight: 700,
                            ...(currentRank <= 10
                              ? { background: "#ecfdf5", color: "#16a34a", border: "1px solid #bbf7d0" }
                              : currentRank <= 30
                              ? { background: "#fffbeb", color: "#d97706", border: "1px solid #fde68a" }
                              : { background: "#fef2f2", color: "#dc2626", border: "1px solid #fecaca" }),
                          }}>
                            {currentRank}위
                          </span>
                        ) : (
                          <span style={{
                            display: "inline-block",
                            padding: "2px 10px",
                            borderRadius: 12,
                            fontSize: 12,
                            fontWeight: 700,
                            background: "#f3f4f6",
                            color: "#9ca3af",
                          }}>
                            50위 밖
                          </span>
                        )}
                      </td>
                      <td style={{ ...tdStyle, textAlign: "center", color: "#666" }}>
                        {prevRank !== null ? `${prevRank}위` : "-"}
                      </td>
                      <td style={{ ...tdStyle, textAlign: "center", fontWeight: 600, ...(diff !== null && diff > 0 ? { color: "#16a34a" } : diff !== null && diff < 0 ? { color: "#dc2626" } : { color: "#999" }) }}>
                        {diff !== null ? (diff > 0 ? `+${diff}` : `${diff}`) : "-"}
                      </td>
                      <td style={{ ...tdStyle, textAlign: "center" }}>
                        {trendIcon(r.trend)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* -- Related Keywords Section -- */}
          {relatedRankingsData.length > 0 && (
            <div style={{ marginBottom: 32 }}>
              <h2 style={{ fontSize: 16, fontWeight: 700, color: "#1a2a4a", marginBottom: 12, paddingBottom: 8, borderBottom: "1px solid #e5e7eb" }}>
                연관 키워드 순위
              </h2>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <thead>
                  <tr style={{ background: "#f8fafc" }}>
                    <th style={thStyle}>메인 키워드</th>
                    <th style={thStyle}>연관 키워드</th>
                    <th style={{ ...thStyle, textAlign: "center" }}>순위</th>
                  </tr>
                </thead>
                <tbody>
                  {relatedRankingsData.flatMap((item) =>
                    item.related.map((rel, idx) => (
                      <tr
                        key={`${item.mainKeyword}-${rel.keyword}-${idx}`}
                        style={{ borderBottom: "1px solid #f0f0f0" }}
                      >
                        <td style={{ ...tdStyle, fontWeight: 500 }}>
                          {idx === 0 ? item.mainKeyword : ""}
                        </td>
                        <td style={{ ...tdStyle, color: "#374151" }}>
                          {rel.keyword}
                        </td>
                        <td style={{ ...tdStyle, textAlign: "center" }}>
                          {rel.rank !== null ? (
                            <span style={{
                              display: "inline-block",
                              padding: "2px 10px",
                              borderRadius: 12,
                              fontSize: 12,
                              fontWeight: 700,
                              background: "#ecfdf5",
                              color: "#16a34a",
                              border: "1px solid #bbf7d0",
                            }}>
                              {rel.rank}위
                            </span>
                          ) : (
                            <span style={{
                              display: "inline-block",
                              padding: "2px 10px",
                              borderRadius: 12,
                              fontSize: 12,
                              fontWeight: 700,
                              background: "#f3f4f6",
                              color: "#9ca3af",
                            }}>
                              50위 밖
                            </span>
                          )}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
              <p style={{ marginTop: 12, fontSize: 11, color: "#6b7280" }}>
                * 연관 키워드에서의 노출은 메인 키워드 순위 상승의 선행 지표입니다
              </p>
            </div>
          )}

          {/* -- Traffic Stats Table -- */}
          <div style={{ marginBottom: 32 }}>
            <h2 style={{ fontSize: 16, fontWeight: 700, color: "#1a2a4a", marginBottom: 12, paddingBottom: 8, borderBottom: "1px solid #e5e7eb" }}>
              트래픽 현황 ({today})
            </h2>
            {trafficStats.length === 0 ? (
              <p style={{ fontSize: 13, color: "#999", textAlign: "center", padding: "24px 0" }}>
                오늘의 트래픽 데이터가 없습니다.
              </p>
            ) : (
              <>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                  <thead>
                    <tr style={{ background: "#f8fafc" }}>
                      <th style={thStyle}>키워드</th>
                      <th style={{ ...thStyle, textAlign: "center" }}>목표</th>
                      <th style={{ ...thStyle, textAlign: "center" }}>완료</th>
                      <th style={{ ...thStyle, textAlign: "center" }}>실패</th>
                      <th style={{ ...thStyle, textAlign: "center" }}>대기</th>
                      <th style={{ ...thStyle, textAlign: "center" }}>성공률</th>
                    </tr>
                  </thead>
                  <tbody>
                    {trafficStats.map((c) => {
                      const rate = c.total > 0 ? Math.round((c.success / c.total) * 100) : 0;
                      return (
                        <tr key={c.id} style={{ borderBottom: "1px solid #f0f0f0" }}>
                          <td style={tdStyle}>
                            <span style={{ fontWeight: 500 }}>{c.keyword}</span>
                            <span style={{ fontSize: 11, color: "#999", marginLeft: 6 }}>({c.type})</span>
                          </td>
                          <td style={{ ...tdStyle, textAlign: "center" }}>{c.daily_target}</td>
                          <td style={{ ...tdStyle, textAlign: "center", fontWeight: 600, color: "#16a34a" }}>{c.success}</td>
                          <td style={{ ...tdStyle, textAlign: "center", fontWeight: 600, color: c.failed > 0 ? "#dc2626" : "#999" }}>{c.failed}</td>
                          <td style={{ ...tdStyle, textAlign: "center", color: "#666" }}>{c.pending}</td>
                          <td style={{ ...tdStyle, textAlign: "center" }}>
                            <span style={{
                              display: "inline-block",
                              padding: "2px 10px",
                              borderRadius: 12,
                              fontSize: 12,
                              fontWeight: 600,
                              color: "#fff",
                              background: successRateColor(rate),
                            }}>
                              {rate}%
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                  <tfoot>
                    <tr style={{ borderTop: "2px solid #e5e7eb", fontWeight: 700 }}>
                      <td style={tdStyle}>합계</td>
                      <td style={{ ...tdStyle, textAlign: "center" }}>{trafficStats.reduce((s, c) => s + c.daily_target, 0)}</td>
                      <td style={{ ...tdStyle, textAlign: "center", color: "#16a34a" }}>{totalVisits}</td>
                      <td style={{ ...tdStyle, textAlign: "center", color: "#dc2626" }}>{trafficStats.reduce((s, c) => s + c.failed, 0)}</td>
                      <td style={{ ...tdStyle, textAlign: "center", color: "#666" }}>{trafficStats.reduce((s, c) => s + c.pending, 0)}</td>
                      <td style={{ ...tdStyle, textAlign: "center" }}>
                        <span style={{
                          display: "inline-block",
                          padding: "2px 10px",
                          borderRadius: 12,
                          fontSize: 12,
                          fontWeight: 600,
                          color: "#fff",
                          background: successRateColor(overallSuccessRate),
                        }}>
                          {overallSuccessRate}%
                        </span>
                      </td>
                    </tr>
                  </tfoot>
                </table>

                {/* Service success messaging */}
                <div style={{ marginTop: 12, textAlign: "right" }}>
                  {overallSuccessRate >= 80 ? (
                    <span style={{ fontSize: 12, fontWeight: 600, color: "#16a34a" }}>
                      &#10003; 정상 운영 중
                    </span>
                  ) : overallSuccessRate >= 50 ? (
                    <span style={{ fontSize: 12, fontWeight: 600, color: "#d97706" }}>
                      &#9651; 일부 지연 발생
                    </span>
                  ) : (
                    <span style={{ fontSize: 12, fontWeight: 600, color: "#dc2626" }}>
                      점검 중
                    </span>
                  )}
                </div>
              </>
            )}
          </div>

          {/* -- Before / After Section -- */}
          {rankings.some((r) => r.history.length >= 2) && (
            <div style={{ marginBottom: 32 }}>
              <h2 style={{ fontSize: 16, fontWeight: 700, color: "#1a2a4a", marginBottom: 12, paddingBottom: 8, borderBottom: "1px solid #e5e7eb" }}>
                Before / After 순위 비교
              </h2>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(340px, 1fr))", gap: 16 }}>
                {rankings
                  .filter((r) => r.history.length >= 2)
                  .map((r) => {
                    const first = r.history[r.history.length - 1];
                    const last = r.history[0];
                    const diff =
                      first.rank !== null && last.rank !== null
                        ? first.rank - last.rank
                        : null;

                    return (
                      <div key={r.campaign.id} style={{ border: "1px solid #e5e7eb", borderRadius: 8, padding: 16 }}>
                        <p style={{ fontSize: 13, fontWeight: 600, color: "#1a2a4a", marginBottom: 12 }}>
                          {r.campaign.keyword}
                          <span style={{ fontSize: 11, color: "#999", marginLeft: 6 }}>({r.campaign.type})</span>
                        </p>
                        <div style={{ display: "grid", gridTemplateColumns: "1fr auto 1fr", alignItems: "center", gap: 12 }}>
                          <div style={{ textAlign: "center", background: "#f8fafc", borderRadius: 8, padding: 12 }}>
                            <p style={{ fontSize: 10, color: "#999", marginBottom: 4 }}>
                              {first.checked_at?.split(" ")[0] ?? ""}
                            </p>
                            <p style={{ fontSize: 28, fontWeight: 800, ...parseStyle(rankColor(first.rank)) }}>
                              {first.rank ?? "-"}
                              {first.rank !== null && <span style={{ fontSize: 12, fontWeight: 400, color: "#999" }}>위</span>}
                            </p>
                          </div>
                          <div style={{ fontSize: 20, color: "#ccc" }}>→</div>
                          <div style={{ textAlign: "center", background: "#f8fafc", borderRadius: 8, padding: 12 }}>
                            <p style={{ fontSize: 10, color: "#999", marginBottom: 4 }}>
                              {last.checked_at?.split(" ")[0] ?? ""}
                            </p>
                            <p style={{ fontSize: 28, fontWeight: 800, ...parseStyle(rankColor(last.rank)) }}>
                              {last.rank ?? "-"}
                              {last.rank !== null && <span style={{ fontSize: 12, fontWeight: 400, color: "#999" }}>위</span>}
                            </p>
                          </div>
                        </div>
                        {diff !== null && (
                          <p style={{ textAlign: "center", marginTop: 8, fontSize: 13, fontWeight: 600, color: diff > 0 ? "#16a34a" : diff < 0 ? "#dc2626" : "#999" }}>
                            {diff > 0 ? `${diff}단계 상승` : diff < 0 ? `${Math.abs(diff)}단계 하락` : "변화 없음"}
                          </p>
                        )}
                      </div>
                    );
                  })}
              </div>
            </div>
          )}

          {/* -- Keyword Strategy Section -- */}
          <div style={{ marginBottom: 32 }}>
            <h2 style={{ fontSize: 16, fontWeight: 700, color: "#1a2a4a", marginBottom: 12, paddingBottom: 8, borderBottom: "1px solid #e5e7eb" }}>
              🎯 키워드별 전략
            </h2>
            {strategy && strategy.keyword_strategies.length > 0 ? (
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <thead>
                  <tr style={{ background: "#f8fafc" }}>
                    <th style={thStyle}>키워드</th>
                    <th style={{ ...thStyle, textAlign: "center" }}>현재 상태</th>
                    <th style={thStyle}>추천 액션</th>
                  </tr>
                </thead>
                <tbody>
                  {strategy.keyword_strategies.map((ks, idx) => (
                    <tr key={idx} style={{ borderBottom: "1px solid #f0f0f0", background: idx % 2 === 0 ? "#fff" : "#f9fafb" }}>
                      <td style={{ ...tdStyle, fontWeight: 500 }}>{ks.keyword}</td>
                      <td style={{ ...tdStyle, textAlign: "center" }}>
                        <span style={{
                          display: "inline-block",
                          padding: "2px 10px",
                          borderRadius: 12,
                          fontSize: 12,
                          fontWeight: 600,
                          background: "#f3f4f6",
                          color: "#374151",
                          border: "1px solid #e5e7eb",
                        }}>
                          {ks.current_status}
                        </span>
                      </td>
                      <td style={{ ...tdStyle, color: "#374151" }}>{ks.action}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div style={{ border: "2px dashed #d1d5db", borderRadius: 8, padding: "32px 24px", textAlign: "center", background: "#f9fafb" }}>
                <p style={{ fontSize: 13, color: "#6b7280" }}>
                  전략 리포트는 매일 18시에 자동 생성됩니다
                </p>
              </div>
            )}
          </div>

          {/* -- Overall Strategy Section -- */}
          <div style={{ marginBottom: 32 }}>
            <h2 style={{ fontSize: 16, fontWeight: 700, color: "#1a2a4a", marginBottom: 12, paddingBottom: 8, borderBottom: "1px solid #e5e7eb" }}>
              📋 블로그 운영 전략
            </h2>
            {strategy && strategy.overall_strategy ? (
              <div style={{ background: "#f9fafb", border: "1px solid #e5e7eb", borderLeft: "4px solid #2563eb", borderRadius: 8, padding: 24 }}>
                <p style={{ fontSize: 13, lineHeight: 1.8, color: "#1f2937", whiteSpace: "pre-line", margin: 0 }}>
                  {strategy.overall_strategy}
                </p>
                {strategy.generated_at && (
                  <p style={{ textAlign: "right", fontSize: 11, color: "#9ca3af", marginTop: 16, marginBottom: 0 }}>
                    생성일시: {strategy.generated_at}
                  </p>
                )}
              </div>
            ) : (
              <div style={{ border: "2px dashed #d1d5db", borderRadius: 8, padding: "32px 24px", textAlign: "center", background: "#f9fafb" }}>
                <p style={{ fontSize: 13, color: "#6b7280" }}>
                  전략 리포트는 매일 18시에 자동 생성됩니다
                </p>
              </div>
            )}
          </div>

          {/* -- Footer -- */}
          <div style={{ borderTop: "2px solid #1a2a4a", paddingTop: 20, marginTop: 40 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 16 }}>
              <div>
                <p style={{ fontSize: 13, fontWeight: 700, color: "#1a2a4a" }}>승인행정사사무소</p>
                <p style={{ fontSize: 11, color: "#999", marginTop: 4 }}>approval-admin.com</p>
              </div>
              <div style={{ textAlign: "right" }}>
                <p style={{ fontSize: 11, color: "#999" }}>
                  본 보고서는 자동 생성된 데이터 기반 리포트입니다.
                </p>
                <p style={{ fontSize: 11, color: "#999", marginTop: 2 }}>
                  문의: 카카오톡 오픈채팅 또는 이메일
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

/* -- Sub-components -- */

function SummaryCard({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div style={{ border: "1px solid #e5e7eb", borderRadius: 8, padding: "16px 8px", textAlign: "center" }}>
      <p style={{ fontSize: 10, color: "#999", marginBottom: 6 }}>{label}</p>
      <p style={{ fontSize: 20, fontWeight: 800, color }}>{value}</p>
    </div>
  );
}

/* -- Style constants -- */

const thStyle: React.CSSProperties = {
  padding: "10px 8px",
  fontSize: 12,
  fontWeight: 600,
  color: "#666",
  textAlign: "left",
  borderBottom: "2px solid #e5e7eb",
};

const tdStyle: React.CSSProperties = {
  padding: "10px 8px",
};

function parseStyle(cssText: string): React.CSSProperties {
  const result: Record<string, string> = {};
  cssText.split(";").forEach((pair) => {
    const [key, val] = pair.split(":").map((s) => s.trim());
    if (key && val) {
      const camelKey = key.replace(/-([a-z])/g, (_, c) => c.toUpperCase());
      result[camelKey] = val;
    }
  });
  return result;
}
