"use client";

import { useEffect, useState, useCallback } from "react";
import { Nav } from "@/components/nav";
import { formatNumber } from "@/lib/utils";
import {
  CheckCircle2,
  XCircle,
  Clock,
  Loader2,
  Activity,
  RefreshCw,
} from "lucide-react";

interface Summary {
  date: string;
  total: number;
  completed: number;
  failed: number;
  pending: number;
  running: number;
  progress_pct: number;
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
  engage_like?: number;
}

interface StatsData {
  stats: {
    date: string;
    total: number;
    completed: number;
    failed: number;
    running: number;
    pending: number;
    campaigns: CampaignStat[];
  };
  workers: { id: string; status: string }[];
}

export default function DashboardPage() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [stats, setStats] = useState<StatsData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    try {
      const [sumRes, statsRes] = await Promise.all([
        fetch("/api/stats/summary"),
        fetch("/api/stats"),
      ]);
      if (sumRes.ok) setSummary(await sumRes.json());
      if (statsRes.ok) setStats(await statsRes.json());
      setError(null);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "연결 실패";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const timer = setInterval(fetchData, 15000);
    return () => clearInterval(timer);
  }, [fetchData]);

  const campaigns = stats?.stats?.campaigns || [];
  const onlineWorkers = (stats?.workers || []).filter(
    (w) => w.status === "online"
  ).length;
  const totalWorkers = (stats?.workers || []).length;

  return (
    <>
      <Nav />
      <main className="mx-auto max-w-7xl px-4 pt-20 pb-12">
        {error && (
          <div className="mb-4 rounded-lg border border-[#ff5252]/30 bg-[#ff5252]/10 px-4 py-3 text-sm text-[#ff5252]">
            Master 서버 연결 실패: {error}
            <br />
            <span className="text-xs text-[#8888aa]">
              master.py가 실행 중인지 확인하세요 (python master.py)
            </span>
          </div>
        )}

        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white">
              Traffic Engine Dashboard
            </h1>
            <p className="text-sm text-[#8888aa]">
              {summary?.date || (() => { const n = new Date(); return `${n.getFullYear()}-${String(n.getMonth()+1).padStart(2,"0")}-${String(n.getDate()).padStart(2,"0")}`; })()}
            </p>
          </div>
          <button
            onClick={() => { setLoading(true); fetchData(); }}
            className="flex items-center gap-1.5 rounded-md bg-[#16163a] px-3 py-1.5 text-sm text-[#8888aa] transition-colors hover:bg-[#2a2a5a] hover:text-white"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            새로고침
          </button>
        </div>

        {/* Stat Cards */}
        <div className="mb-8 grid grid-cols-2 gap-4 md:grid-cols-5">
          <StatCard
            label="전체 작업"
            value={summary?.total || 0}
            icon={<Activity className="h-5 w-5 text-[#448aff]" />}
          />
          <StatCard
            label="완료"
            value={summary?.completed || 0}
            icon={<CheckCircle2 className="h-5 w-5 text-[#00e676]" />}
            color="text-[#00e676]"
          />
          <StatCard
            label="진행 중"
            value={summary?.running || 0}
            icon={<Loader2 className="h-5 w-5 animate-spin text-[#ffd740]" />}
            color="text-[#ffd740]"
          />
          <StatCard
            label="대기"
            value={summary?.pending || 0}
            icon={<Clock className="h-5 w-5 text-[#8888aa]" />}
          />
          <StatCard
            label="실패"
            value={summary?.failed || 0}
            icon={<XCircle className="h-5 w-5 text-[#ff5252]" />}
            color="text-[#ff5252]"
          />
        </div>

        {/* Progress Bar */}
        <div className="mb-8 rounded-xl border border-[#2a2a5a] bg-[#111127] p-6">
          <div className="mb-2 flex items-center justify-between text-sm">
            <span className="text-[#8888aa]">오늘 진행률</span>
            <span className="font-mono text-lg font-bold text-[#00e676]">
              {summary?.progress_pct?.toFixed(1) || "0.0"}%
            </span>
          </div>
          <div className="h-4 overflow-hidden rounded-full bg-[#0a0a1a]">
            <div
              className="h-full rounded-full bg-gradient-to-r from-[#00e676] to-[#448aff] transition-all duration-700"
              style={{ width: `${summary?.progress_pct || 0}%` }}
            />
          </div>
          <div className="mt-2 flex justify-between text-xs text-[#8888aa]">
            <span>워커: {onlineWorkers}/{totalWorkers} 온라인</span>
            <span>
              {formatNumber(summary?.completed || 0)} /{" "}
              {formatNumber(summary?.total || 0)}
            </span>
          </div>
        </div>

        {/* Campaigns Table */}
        <div className="rounded-xl border border-[#2a2a5a] bg-[#111127] p-6">
          <h2 className="mb-4 text-lg font-semibold text-white">
            캠페인별 현황
          </h2>
          {campaigns.length === 0 ? (
            <p className="py-8 text-center text-sm text-[#8888aa]">
              {loading ? "로딩 중..." : "활성 캠페인이 없습니다"}
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-[#2a2a5a] text-left text-xs uppercase text-[#8888aa]">
                    <th className="pb-3 pr-4">ID</th>
                    <th className="pb-3 pr-4">타입</th>
                    <th className="pb-3 pr-4">고객</th>
                    <th className="pb-3 pr-4">키워드</th>
                    <th className="pb-3 pr-4 text-right">목표</th>
                    <th className="pb-3 pr-4 text-right">성공</th>
                    <th className="pb-3 pr-4 text-right">실패</th>
                    <th className="pb-3 pr-4 text-right">대기</th>
                    <th className="pb-3 text-right">진행률</th>
                  </tr>
                </thead>
                <tbody>
                  {campaigns.map((c) => {
                    const pct =
                      c.total > 0
                        ? ((c.success || 0) / c.total) * 100
                        : 0;
                    return (
                      <tr
                        key={c.id}
                        className="border-b border-[#2a2a5a]/50 transition-colors hover:bg-[#16163a]"
                      >
                        <td className="py-3 pr-4 font-mono text-[#8888aa]">
                          #{c.id}
                        </td>
                        <td className="py-3 pr-4">
                          <span
                            className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                              c.type === "place"
                                ? "bg-[#448aff]/15 text-[#448aff]"
                                : c.type === "blog"
                                ? "bg-[#ffd740]/15 text-[#ffd740]"
                                : "bg-[#00e676]/15 text-[#00e676]"
                            }`}
                          >
                            {c.type === "place" ? "📍 플레이스" : c.type === "blog" ? "📝 블로그" : "🛒 쇼핑"}
                          </span>
                        </td>
                        <td className="py-3 pr-4 font-medium text-white">
                          {c.customer_name}
                        </td>
                        <td className="py-3 pr-4 text-[#e0e0e0]">
                          {c.keyword}
                          {c.engage_like ? <span className="ml-1.5 text-[10px] text-[#ff6eb4]" title="공감 ON">👍</span> : null}
                        </td>
                        <td className="py-3 pr-4 text-right font-mono">
                          {formatNumber(c.daily_target)}
                        </td>
                        <td className="py-3 pr-4 text-right font-mono text-[#00e676]">
                          {formatNumber(c.success || 0)}
                        </td>
                        <td className="py-3 pr-4 text-right font-mono text-[#ff5252]">
                          {formatNumber(c.failed || 0)}
                        </td>
                        <td className="py-3 pr-4 text-right font-mono text-[#ffd740]">
                          {formatNumber(c.pending || 0)}
                        </td>
                        <td className="py-3 text-right">
                          <div className="flex items-center justify-end gap-2">
                            <div className="h-2 w-16 overflow-hidden rounded-full bg-[#0a0a1a]">
                              <div
                                className="h-full rounded-full bg-[#00e676]"
                                style={{ width: `${pct}%` }}
                              />
                            </div>
                            <span className="w-10 text-right font-mono text-xs">
                              {pct.toFixed(0)}%
                            </span>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </main>
    </>
  );
}

function StatCard({
  label,
  value,
  icon,
  color = "text-white",
}: {
  label: string;
  value: number;
  icon: React.ReactNode;
  color?: string;
}) {
  return (
    <div className="rounded-xl border border-[#2a2a5a] bg-[#111127] p-4">
      <div className="mb-2 flex items-center justify-between">
        <span className="text-xs text-[#8888aa]">{label}</span>
        {icon}
      </div>
      <div className={`text-2xl font-bold font-mono ${color}`}>
        {formatNumber(value)}
      </div>
    </div>
  );
}
