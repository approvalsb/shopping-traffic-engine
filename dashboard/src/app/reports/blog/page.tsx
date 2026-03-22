"use client";

import { Suspense, useEffect, useState, useCallback } from "react";
import { useSearchParams } from "next/navigation";
import {
  TrendingUp,
  TrendingDown,
  Minus,
  Printer,
  ArrowLeft,
} from "lucide-react";

interface RelatedRanking {
  keyword: string;
  rank: number | null;
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

interface CampaignSummary {
  id: number;
  customer_name: string;
  keyword: string;
  type: string;
  latest_rank: number | null;
  trend: string;
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

interface KeywordData {
  keyword: string;
  campaignId: number;
  currentRank: number | null;
  previousRank: number | null;
  firstRank: number | null;
  latestRank: number | null;
  trend: string;
  firstDate: string;
  latestDate: string;
  historyCount: number;
  relatedRankings: RelatedRanking[];
}

export default function BlogReportPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center bg-gray-900">
          <div className="text-center">
            <div className="mx-auto mb-4 h-8 w-8 animate-spin rounded-full border-4 border-gray-600 border-t-white" />
            <p className="text-sm text-gray-400">보고서를 불러오는 중...</p>
          </div>
        </div>
      }
    >
      <BlogReportContent />
    </Suspense>
  );
}

function BlogReportContent() {
  const searchParams = useSearchParams();
  const customer = searchParams.get("customer") || "";
  const days = parseInt(searchParams.get("days") || "30", 10);

  const [loading, setLoading] = useState(true);
  const [keywords, setKeywords] = useState<KeywordData[]>([]);
  const [dateRange, setDateRange] = useState({ from: "", to: "" });
  const [firstTrackedDate, setFirstTrackedDate] = useState<string | null>(null);
  const [strategy, setStrategy] = useState<CustomerStrategy | null>(null);

  const fetchReport = useCallback(async () => {
    if (!customer) {
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      // 1) Get all campaigns
      const res = await fetch("/api/tracking");
      if (!res.ok) throw new Error("Failed to fetch campaigns");
      const data = await res.json();
      const campaigns: CampaignSummary[] = data.campaigns || [];

      // Save strategy data
      const strategyMap = data.strategy || {};
      if (strategyMap[customer]) {
        setStrategy(strategyMap[customer]);
      } else {
        setStrategy(null);
      }

      // Filter by customer name
      const matched = campaigns.filter(
        (c) => c.customer_name === customer
      );

      if (matched.length === 0) {
        setKeywords([]);
        setLoading(false);
        return;
      }

      // 2) Fetch history for each campaign
      const results: KeywordData[] = [];
      let minDate = "";
      let maxDate = "";
      let earliestDate = "";

      await Promise.all(
        matched.map(async (campaign) => {
          const hRes = await fetch(
            `/api/tracking?campaignId=${campaign.id}&days=${days}`
          );
          if (!hRes.ok) return;
          const hData = await hRes.json();
          const history: TrackingEntry[] = hData.history || [];

          if (history.length === 0) {
            results.push({
              keyword: campaign.keyword,
              campaignId: campaign.id,
              currentRank: campaign.latest_rank,
              previousRank: null,
              firstRank: null,
              latestRank: campaign.latest_rank,
              trend: campaign.trend,
              firstDate: "",
              latestDate: "",
              historyCount: 0,
              relatedRankings: [],
            });
            return;
          }

          // history[0] = latest, history[last] = oldest
          const latest = history[0];
          const previous = history.length > 1 ? history[1] : null;
          const first = history[history.length - 1];

          const firstDate = first.checked_at?.split(" ")[0] || "";
          const latestDate = latest.checked_at?.split(" ")[0] || "";

          if (!minDate || firstDate < minDate) minDate = firstDate;
          if (!maxDate || latestDate > maxDate) maxDate = latestDate;
          if (!earliestDate || firstDate < earliestDate) earliestDate = firstDate;

          results.push({
            keyword: campaign.keyword,
            campaignId: campaign.id,
            currentRank: latest.rank,
            previousRank: previous?.rank ?? null,
            firstRank: first.rank,
            latestRank: latest.rank,
            trend: hData.trend || "stable",
            firstDate,
            latestDate,
            historyCount: history.length,
            relatedRankings: latest.related_rankings || [],
          });
        })
      );

      setKeywords(results);
      setDateRange({ from: minDate, to: maxDate });
      setFirstTrackedDate(earliestDate || null);
    } catch {
      setKeywords([]);
    } finally {
      setLoading(false);
    }
  }, [customer, days]);

  useEffect(() => {
    fetchReport();
  }, [fetchReport]);

  // Summary calculations
  const totalKeywords = keywords.length;
  const rankedKeywords = keywords.filter((k) => k.currentRank !== null);
  const avgRank =
    rankedKeywords.length > 0
      ? Math.round(
          rankedKeywords.reduce((sum, k) => sum + (k.currentRank as number), 0) /
            rankedKeywords.length
        )
      : null;
  const totalHistoryCount = keywords.reduce((sum, k) => sum + k.historyCount, 0);

  const allUnranked = keywords.length > 0 && rankedKeywords.length === 0;

  // Calculate service days
  const serviceDays = firstTrackedDate
    ? Math.max(
        1,
        Math.ceil(
          (Date.now() - new Date(firstTrackedDate).getTime()) / 86400000
        )
      )
    : null;

  // Collect related rankings from all keywords
  const relatedRankingsData = keywords
    .filter((k) => k.relatedRankings.length > 0)
    .map((k) => ({
      mainKeyword: k.keyword,
      related: k.relatedRankings,
    }));

  const today = new Date().toLocaleDateString("ko-KR", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });

  const rankChange = (current: number | null, previous: number | null) => {
    if (current === null || previous === null) return null;
    return previous - current; // positive = improved
  };

  const rankBadgeClass = (rank: number | null) => {
    if (rank === null) return "bg-gray-100 text-gray-500";
    if (rank <= 10) return "bg-emerald-50 text-emerald-700 border border-emerald-200";
    if (rank <= 30) return "bg-amber-50 text-amber-700 border border-amber-200";
    return "bg-red-50 text-red-700 border border-red-200";
  };

  if (!customer) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-900">
        <div className="text-center">
          <p className="text-lg text-gray-400">
            고객명이 지정되지 않았습니다.
          </p>
          <p className="mt-2 text-sm text-gray-500">
            URL에 <code className="rounded bg-gray-800 px-2 py-0.5 text-amber-400">?customer=고객명</code>을 추가하세요.
          </p>
        </div>
      </div>
    );
  }

  return (
    <>
      <style jsx global>{`
        @media print {
          nav,
          .no-print {
            display: none !important;
          }
          body {
            background: white !important;
            -webkit-print-color-adjust: exact;
            print-color-adjust: exact;
          }
          .report-content {
            box-shadow: none !important;
            margin: 0 !important;
          }
          .page-wrapper {
            background: white !important;
            padding: 0 !important;
            min-height: auto !important;
          }
        }
      `}</style>

      <div className="page-wrapper min-h-screen bg-gray-900">
        {/* Top bar - hidden in print */}
        <div className="no-print border-b border-gray-800 bg-gray-950 px-6 py-4">
          <div className="mx-auto flex max-w-4xl items-center justify-between">
            <a
              href="/tracking"
              className="flex items-center gap-2 text-sm text-gray-400 transition-colors hover:text-white"
            >
              <ArrowLeft className="h-4 w-4" />
              대시보드로 돌아가기
            </a>
            <button
              onClick={() => window.print()}
              className="flex items-center gap-2 rounded-lg bg-white px-4 py-2 text-sm font-medium text-gray-900 transition-colors hover:bg-gray-100"
            >
              <Printer className="h-4 w-4" />
              인쇄 / PDF 저장
            </button>
          </div>
        </div>

        {/* Report Content - white background */}
        <div className="mx-auto max-w-4xl px-6 py-8">
          <div className="report-content rounded-xl bg-white shadow-xl">
            {loading ? (
              <div className="flex items-center justify-center py-32">
                <div className="text-center">
                  <div className="mx-auto mb-4 h-8 w-8 animate-spin rounded-full border-4 border-gray-200 border-t-gray-600" />
                  <p className="text-sm text-gray-500">보고서를 생성하고 있습니다...</p>
                </div>
              </div>
            ) : keywords.length === 0 ? (
              <div className="flex items-center justify-center py-32">
                <div className="text-center">
                  <p className="text-lg font-medium text-gray-700">
                    데이터가 없습니다
                  </p>
                  <p className="mt-2 text-sm text-gray-500">
                    &quot;{customer}&quot; 고객의 추적 데이터를 찾을 수 없습니다.
                  </p>
                </div>
              </div>
            ) : (
              <div className="p-10">
                {/* Report Header */}
                <div className="mb-10 border-b-2 border-gray-900 pb-8">
                  <h1 className="text-3xl font-bold tracking-tight text-gray-900">
                    블로그 성과 보고서
                  </h1>
                  <p className="mt-2 text-xl text-gray-600">{customer}</p>
                  <div className="mt-4 flex flex-wrap gap-x-8 gap-y-1 text-sm text-gray-500">
                    <span>
                      보고 기간: {dateRange.from || "—"} ~ {dateRange.to || "—"} ({days}일)
                    </span>
                    <span>작성일: {today}</span>
                  </div>
                  <p className="mt-2 text-xs text-gray-400">
                    승인행정사사무소 | approval-admin.com
                  </p>
                </div>

                {/* Service Status Banner */}
                <div className="mb-8 rounded-lg border border-blue-200 bg-gradient-to-r from-blue-50 to-emerald-50 px-6 py-4">
                  <p className="text-base font-semibold text-blue-800">
                    {serviceDays !== null
                      ? `서비스 시작 ${serviceDays}일차`
                      : "데이터 수집 중"}
                  </p>
                  {allUnranked && (
                    <p className="mt-1 text-sm text-blue-600">
                      순위 반영까지 보통 1~2주가 소요됩니다
                    </p>
                  )}
                </div>

                {/* Summary Cards */}
                <div className="mb-10 grid grid-cols-3 gap-4">
                  <div className="rounded-lg border border-gray-200 bg-gray-50 p-5 text-center">
                    <p className="text-xs font-medium uppercase tracking-wider text-gray-500">
                      추적 키워드 수
                    </p>
                    <p className="mt-2 text-4xl font-bold text-gray-900">
                      {totalKeywords}
                    </p>
                  </div>
                  <div className="rounded-lg border border-gray-200 bg-gray-50 p-5 text-center">
                    <p className="text-xs font-medium uppercase tracking-wider text-gray-500">
                      평균 순위
                    </p>
                    <p className="mt-2 text-4xl font-bold text-gray-900">
                      {avgRank !== null ? `${avgRank}위` : "—"}
                    </p>
                  </div>
                  <div className="rounded-lg border border-gray-200 bg-gray-50 p-5 text-center">
                    <p className="text-xs font-medium uppercase tracking-wider text-gray-500">
                      누적 추적 횟수
                    </p>
                    <p className="mt-2 text-4xl font-bold text-blue-600">
                      {totalHistoryCount}
                    </p>
                  </div>
                </div>

                {/* Keyword Ranking Table */}
                <div className="mb-10">
                  <h2 className="mb-4 text-lg font-bold text-gray-900">
                    키워드 순위 현황
                  </h2>
                  <div className="overflow-hidden rounded-lg border border-gray-200">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-gray-200 bg-gray-50 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                          <th className="px-4 py-3">키워드</th>
                          <th className="px-4 py-3 text-center">현재 순위</th>
                          <th className="px-4 py-3 text-center">이전 순위</th>
                          <th className="px-4 py-3 text-center">변화</th>
                          <th className="px-4 py-3 text-center">추세</th>
                        </tr>
                      </thead>
                      <tbody>
                        {keywords.map((kw, idx) => {
                          const change = rankChange(kw.currentRank, kw.previousRank);
                          return (
                            <tr
                              key={kw.campaignId}
                              className={
                                idx % 2 === 0
                                  ? "bg-white"
                                  : "bg-gray-50"
                              }
                            >
                              <td className="px-4 py-3 font-medium text-gray-900">
                                {kw.keyword}
                              </td>
                              <td className="px-4 py-3 text-center">
                                <span
                                  className={`inline-block rounded-full px-3 py-1 text-xs font-bold ${rankBadgeClass(kw.currentRank)}`}
                                >
                                  {kw.currentRank !== null
                                    ? `${kw.currentRank}위`
                                    : "50위 밖"}
                                </span>
                              </td>
                              <td className="px-4 py-3 text-center text-gray-500">
                                {kw.previousRank !== null
                                  ? `${kw.previousRank}위`
                                  : "—"}
                              </td>
                              <td className="px-4 py-3 text-center">
                                {change !== null ? (
                                  change > 0 ? (
                                    <span className="font-bold text-emerald-600">
                                      +{change}
                                    </span>
                                  ) : change < 0 ? (
                                    <span className="font-bold text-red-600">
                                      {change}
                                    </span>
                                  ) : (
                                    <span className="text-gray-400">0</span>
                                  )
                                ) : (
                                  <span className="text-gray-400">—</span>
                                )}
                              </td>
                              <td className="px-4 py-3 text-center">
                                {kw.trend === "up" ? (
                                  <TrendingUp className="mx-auto h-4 w-4 text-emerald-600" />
                                ) : kw.trend === "down" ? (
                                  <TrendingDown className="mx-auto h-4 w-4 text-red-600" />
                                ) : (
                                  <Minus className="mx-auto h-4 w-4 text-gray-400" />
                                )}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Related Keywords Section */}
                {relatedRankingsData.length > 0 && (
                  <div className="mb-10">
                    <h2 className="mb-4 text-lg font-bold text-gray-900">
                      연관 키워드 순위
                    </h2>
                    <div className="overflow-hidden rounded-lg border border-gray-200">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="border-b border-gray-200 bg-gray-50 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                            <th className="px-4 py-3">메인 키워드</th>
                            <th className="px-4 py-3">연관 키워드</th>
                            <th className="px-4 py-3 text-center">순위</th>
                          </tr>
                        </thead>
                        <tbody>
                          {relatedRankingsData.flatMap((item) =>
                            item.related.map((rel, idx) => (
                              <tr
                                key={`${item.mainKeyword}-${rel.keyword}-${idx}`}
                                className={idx % 2 === 0 ? "bg-white" : "bg-gray-50"}
                              >
                                <td className="px-4 py-3 font-medium text-gray-900">
                                  {idx === 0 ? item.mainKeyword : ""}
                                </td>
                                <td className="px-4 py-3 text-gray-700">
                                  {rel.keyword}
                                </td>
                                <td className="px-4 py-3 text-center">
                                  {rel.rank !== null ? (
                                    <span className="inline-block rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-bold text-emerald-700">
                                      {rel.rank}위
                                    </span>
                                  ) : (
                                    <span className="inline-block rounded-full bg-gray-100 px-3 py-1 text-xs font-bold text-gray-500">
                                      50위 밖
                                    </span>
                                  )}
                                </td>
                              </tr>
                            ))
                          )}
                        </tbody>
                      </table>
                    </div>
                    <p className="mt-3 text-xs text-gray-500">
                      * 연관 키워드에서의 노출은 메인 키워드 순위 상승의 선행 지표입니다
                    </p>
                  </div>
                )}

                {/* Before / After Section */}
                <div className="mb-10">
                  <h2 className="mb-4 text-lg font-bold text-gray-900">
                    Before / After 비교
                  </h2>
                  <div className="space-y-3">
                    {keywords.map((kw) => {
                      const diff =
                        kw.firstRank !== null && kw.latestRank !== null
                          ? kw.firstRank - kw.latestRank
                          : null;
                      return (
                        <div
                          key={kw.campaignId}
                          className="rounded-lg border border-gray-200 p-4"
                        >
                          <p className="mb-3 text-sm font-semibold text-gray-700">
                            {kw.keyword}
                          </p>
                          <div className="flex items-center gap-4">
                            {/* Before */}
                            <div className="flex-1 rounded-md border border-gray-200 bg-gray-50 p-3 text-center">
                              <p className="text-[10px] uppercase tracking-wider text-gray-400">
                                시작 ({kw.firstDate || "—"})
                              </p>
                              <p
                                className={`mt-1 text-2xl font-bold ${
                                  kw.firstRank !== null
                                    ? "text-gray-700"
                                    : "text-gray-400"
                                }`}
                              >
                                {kw.firstRank !== null
                                  ? `${kw.firstRank}위`
                                  : "—"}
                              </p>
                            </div>

                            {/* Arrow */}
                            <div className="flex flex-col items-center">
                              {diff !== null ? (
                                diff > 0 ? (
                                  <>
                                    <TrendingUp className="h-5 w-5 text-emerald-600" />
                                    <span className="mt-0.5 text-xs font-bold text-emerald-600">
                                      {diff}단계 상승
                                    </span>
                                  </>
                                ) : diff < 0 ? (
                                  <>
                                    <TrendingDown className="h-5 w-5 text-red-600" />
                                    <span className="mt-0.5 text-xs font-bold text-red-600">
                                      {Math.abs(diff)}단계 하락
                                    </span>
                                  </>
                                ) : (
                                  <>
                                    <Minus className="h-5 w-5 text-gray-400" />
                                    <span className="mt-0.5 text-xs text-gray-400">
                                      변화 없음
                                    </span>
                                  </>
                                )
                              ) : (
                                <Minus className="h-5 w-5 text-gray-300" />
                              )}
                            </div>

                            {/* After */}
                            <div
                              className={`flex-1 rounded-md border p-3 text-center ${
                                diff !== null && diff > 0
                                  ? "border-emerald-200 bg-emerald-50"
                                  : diff !== null && diff < 0
                                  ? "border-red-200 bg-red-50"
                                  : "border-gray-200 bg-gray-50"
                              }`}
                            >
                              <p className="text-[10px] uppercase tracking-wider text-gray-400">
                                현재 ({kw.latestDate || "—"})
                              </p>
                              <p
                                className={`mt-1 text-2xl font-bold ${
                                  diff !== null && diff > 0
                                    ? "text-emerald-700"
                                    : diff !== null && diff < 0
                                    ? "text-red-700"
                                    : "text-gray-700"
                                }`}
                              >
                                {kw.latestRank !== null
                                  ? `${kw.latestRank}위`
                                  : "—"}
                              </p>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Keyword Strategy Section */}
                <div className="mb-10">
                  <h2 className="mb-4 text-lg font-bold text-gray-900">
                    🎯 키워드별 전략
                  </h2>
                  {strategy && strategy.keyword_strategies.length > 0 ? (
                    <div className="overflow-hidden rounded-lg border border-gray-200">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="border-b border-gray-200 bg-gray-50 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                            <th className="px-4 py-3">키워드</th>
                            <th className="px-4 py-3 text-center">현재 상태</th>
                            <th className="px-4 py-3">추천 액션</th>
                          </tr>
                        </thead>
                        <tbody>
                          {strategy.keyword_strategies.map((ks, idx) => (
                            <tr
                              key={idx}
                              className={idx % 2 === 0 ? "bg-white" : "bg-gray-50"}
                            >
                              <td className="px-4 py-3 font-medium text-gray-900">
                                {ks.keyword}
                              </td>
                              <td className="px-4 py-3 text-center">
                                <span className="inline-block rounded-full border border-gray-200 bg-gray-50 px-3 py-1 text-xs font-semibold text-gray-700">
                                  {ks.current_status}
                                </span>
                              </td>
                              <td className="px-4 py-3 text-gray-700">
                                {ks.action}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <div className="rounded-lg border border-dashed border-gray-300 bg-gray-50 px-6 py-8 text-center">
                      <p className="text-sm text-gray-500">
                        전략 리포트는 매일 18시에 자동 생성됩니다
                      </p>
                    </div>
                  )}
                </div>

                {/* Overall Strategy Section */}
                <div className="mb-10">
                  <h2 className="mb-4 text-lg font-bold text-gray-900">
                    📋 블로그 운영 전략
                  </h2>
                  {strategy && strategy.overall_strategy ? (
                    <div className="rounded-lg border border-gray-200 bg-gray-50 p-6" style={{ borderLeft: "4px solid #2563eb" }}>
                      <p className="whitespace-pre-line text-sm leading-relaxed text-gray-800">
                        {strategy.overall_strategy}
                      </p>
                      {strategy.generated_at && (
                        <p className="mt-4 text-right text-xs text-gray-400">
                          생성일시: {strategy.generated_at}
                        </p>
                      )}
                    </div>
                  ) : (
                    <div className="rounded-lg border border-dashed border-gray-300 bg-gray-50 px-6 py-8 text-center">
                      <p className="text-sm text-gray-500">
                        전략 리포트는 매일 18시에 자동 생성됩니다
                      </p>
                    </div>
                  )}
                </div>

                {/* Footer */}
                <div className="border-t-2 border-gray-200 pt-6 text-center">
                  <p className="text-xs text-gray-500">
                    본 보고서는 네이버 검색 기준으로 작성되었습니다.
                  </p>
                  <p className="mt-1 text-xs text-gray-400">
                    승인행정사사무소 | 문의: 카카오톡 오픈채팅
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
