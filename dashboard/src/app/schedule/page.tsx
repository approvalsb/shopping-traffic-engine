"use client";

import { useEffect, useState, useCallback } from "react";
import { Nav } from "@/components/nav";
import {
  Clock,
  CheckCircle2,
  XCircle,
  Loader2,
  Timer,
  RefreshCw,
  ChevronDown,
  ChevronRight,
  Heart,
} from "lucide-react";

interface Job {
  job_id: number;
  campaign_id: number;
  type: string;
  keyword: string;
  customer_name: string;
  product_name: string;
  engage_like: boolean;
  options: string[] | string;
  status: string;
  started_at: string | null;
  completed_at: string | null;
  duration_sec: number | null;
  error: string | null;
}

// L2/L3 option keys
const L2_OPTIONS = new Set([
  "wish_click", "cart_add", "review_dwell", "compare_behavior", "category_entry",
  "store_browse", "sort_filter", "revisit_sim", "price_compare", "inquiry_click",
  "conversion_sim", "save_click", "map_traffic",
  "blog_like", "blog_comment_view", "blog_series",
]);
const L3_OPTIONS = new Set(["regional_targeting"]);

function parseOptions(opts?: string[] | string): string[] {
  if (!opts) return [];
  if (typeof opts === "string") {
    try { return JSON.parse(opts); } catch { return []; }
  }
  return opts;
}

function JobLayerBadges({ options }: { options?: string[] | string }) {
  const opts = parseOptions(options);
  const hasL2 = opts.some((k) => L2_OPTIONS.has(k));
  const hasL3 = opts.some((k) => L3_OPTIONS.has(k));
  return (
    <span className="inline-flex gap-0.5">
      <span className="rounded px-1 py-px text-[8px] font-extrabold text-black bg-[#00e676]">L1</span>
      <span className={`rounded px-1 py-px text-[8px] font-extrabold ${hasL2 ? "text-black bg-[#ff9052]" : "text-[#555] bg-[#2a2a5a]"}`}>L2</span>
      <span className={`rounded px-1 py-px text-[8px] font-extrabold ${hasL3 ? "text-black bg-[#448aff]" : "text-[#555] bg-[#2a2a5a]"}`}>L3</span>
    </span>
  );
}

interface HourBlock {
  hour: number;
  total: number;
  completed: number;
  failed: number;
  running: number;
  pending: number;
  jobs: Job[];
}

interface ScheduleData {
  date: string;
  total: number;
  completed: number;
  failed: number;
  timeline: HourBlock[];
  error?: string;
}

const statusConfig: Record<string, { icon: React.ReactNode; color: string; label: string; bg: string }> = {
  completed: {
    icon: <CheckCircle2 className="h-3.5 w-3.5" />,
    color: "text-[#00e676]",
    label: "완료",
    bg: "bg-[#00e676]",
  },
  failed: {
    icon: <XCircle className="h-3.5 w-3.5" />,
    color: "text-[#ff5252]",
    label: "실패",
    bg: "bg-[#ff5252]",
  },
  running: {
    icon: <Loader2 className="h-3.5 w-3.5 animate-spin" />,
    color: "text-[#ffd740]",
    label: "진행 중",
    bg: "bg-[#ffd740]",
  },
  pending: {
    icon: <Clock className="h-3.5 w-3.5" />,
    color: "text-[#8888aa]",
    label: "대기",
    bg: "bg-[#8888aa]",
  },
};

const typeLabel: Record<string, string> = {
  blog: "블로그",
  place: "플레이스",
  shopping: "쇼핑",
};

const typeColor: Record<string, string> = {
  blog: "bg-[#ffd740]/15 text-[#ffd740]",
  place: "bg-[#448aff]/15 text-[#448aff]",
  shopping: "bg-[#00e676]/15 text-[#00e676]",
};

export default function SchedulePage() {
  const [data, setData] = useState<ScheduleData | null>(null);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<Set<number>>(new Set());
  const [selectedDate, setSelectedDate] = useState(() => {
    const now = new Date();
    const y = now.getFullYear();
    const m = String(now.getMonth() + 1).padStart(2, "0");
    const d = String(now.getDate()).padStart(2, "0");
    return `${y}-${m}-${d}`;
  });

  const fetchSchedule = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`/api/schedule?date=${selectedDate}`);
      if (res.ok) setData(await res.json());
    } catch {
      // silently handle
    } finally {
      setLoading(false);
    }
  }, [selectedDate]);

  useEffect(() => {
    fetchSchedule();
    const timer = setInterval(fetchSchedule, 30000);
    return () => clearInterval(timer);
  }, [fetchSchedule]);

  const toggleHour = (hour: number) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(hour)) next.delete(hour);
      else next.add(hour);
      return next;
    });
  };

  const expandAll = () => {
    if (!data) return;
    const hours = data.timeline.filter((h) => h.total > 0).map((h) => h.hour);
    setExpanded(new Set(hours));
  };

  const collapseAll = () => setExpanded(new Set());

  const currentHour = new Date().getHours();
  const isToday = selectedDate === (() => {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
  })();

  return (
    <>
      <Nav />
      <main className="mx-auto max-w-7xl px-4 pt-20 pb-12">
        {/* Header */}
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white">
              <Clock className="mr-2 inline h-6 w-6 text-[#448aff]" />
              작업 스케줄
            </h1>
            <p className="mt-1 text-sm text-[#8888aa]">
              시간대별 작업 현황을 실시간으로 확인합니다
            </p>
          </div>
          <div className="flex items-center gap-3">
            <input
              type="date"
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
              className="rounded-lg border border-[#2a2a5a] bg-[#0a0a1a] px-3 py-1.5 text-sm text-white focus:border-[#448aff] focus:outline-none"
            />
            <button
              onClick={fetchSchedule}
              className="flex items-center gap-1.5 rounded-lg border border-[#2a2a5a] px-3 py-1.5 text-sm text-[#8888aa] transition-colors hover:bg-[#16163a] hover:text-white"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            </button>
          </div>
        </div>

        {/* Summary Cards */}
        {data && (
          <div className="mb-6 grid grid-cols-2 gap-3 md:grid-cols-4">
            <div className="rounded-xl border border-[#2a2a5a] bg-[#111127] p-4">
              <p className="text-xs text-[#8888aa]">전체 작업</p>
              <p className="mt-1 text-2xl font-bold text-white">{data.total}</p>
            </div>
            <div className="rounded-xl border border-[#2a2a5a] bg-[#111127] p-4">
              <p className="text-xs text-[#8888aa]">완료</p>
              <p className="mt-1 text-2xl font-bold text-[#00e676]">{data.completed}</p>
            </div>
            <div className="rounded-xl border border-[#2a2a5a] bg-[#111127] p-4">
              <p className="text-xs text-[#8888aa]">실패</p>
              <p className="mt-1 text-2xl font-bold text-[#ff5252]">{data.failed}</p>
            </div>
            <div className="rounded-xl border border-[#2a2a5a] bg-[#111127] p-4">
              <p className="text-xs text-[#8888aa]">남은 작업</p>
              <p className="mt-1 text-2xl font-bold text-[#ffd740]">
                {data.total - data.completed - data.failed}
              </p>
            </div>
          </div>
        )}

        {/* Expand/Collapse */}
        <div className="mb-3 flex gap-2">
          <button
            onClick={expandAll}
            className="rounded-md border border-[#2a2a5a] px-2.5 py-1 text-xs text-[#8888aa] hover:bg-[#16163a] hover:text-white"
          >
            전체 펼치기
          </button>
          <button
            onClick={collapseAll}
            className="rounded-md border border-[#2a2a5a] px-2.5 py-1 text-xs text-[#8888aa] hover:bg-[#16163a] hover:text-white"
          >
            전체 접기
          </button>
        </div>

        {/* Timeline */}
        {loading && !data ? (
          <p className="py-16 text-center text-sm text-[#8888aa]">로딩 중...</p>
        ) : data?.error ? (
          <div className="rounded-xl border border-[#ff5252]/30 bg-[#ff5252]/10 p-6 text-center text-sm text-[#ff5252]">
            서버 연결 실패: {data.error}
          </div>
        ) : (
          <div className="space-y-1">
            {data?.timeline.map((block) => {
              const isNow = isToday && block.hour === currentHour;
              const isPast = isToday && block.hour < currentHour;
              const isEmpty = block.total === 0;
              const isOpen = expanded.has(block.hour);

              return (
                <div
                  key={block.hour}
                  className={`rounded-xl border transition-all ${
                    isNow
                      ? "border-[#448aff] bg-[#448aff]/5"
                      : "border-[#2a2a5a] bg-[#111127]"
                  } ${isEmpty ? "opacity-40" : ""}`}
                >
                  {/* Hour Header */}
                  <button
                    onClick={() => !isEmpty && toggleHour(block.hour)}
                    disabled={isEmpty}
                    className={`flex w-full items-center gap-3 px-4 py-3 text-left ${
                      isEmpty ? "cursor-default" : "cursor-pointer hover:bg-[#16163a]/50"
                    }`}
                  >
                    {/* Time */}
                    <div className="flex w-16 items-center gap-1.5">
                      {isNow && (
                        <span className="h-2 w-2 rounded-full bg-[#448aff] animate-pulse" />
                      )}
                      <span
                        className={`font-mono text-lg font-bold ${
                          isNow
                            ? "text-[#448aff]"
                            : isPast
                            ? "text-[#555]"
                            : "text-white"
                        }`}
                      >
                        {String(block.hour).padStart(2, "0")}:00
                      </span>
                    </div>

                    {/* Status pills */}
                    {!isEmpty && (
                      <div className="flex items-center gap-2">
                        {block.completed > 0 && (
                          <span className="flex items-center gap-1 rounded-full bg-[#00e676]/10 px-2 py-0.5 text-xs text-[#00e676]">
                            <CheckCircle2 className="h-3 w-3" />
                            {block.completed}
                          </span>
                        )}
                        {block.running > 0 && (
                          <span className="flex items-center gap-1 rounded-full bg-[#ffd740]/10 px-2 py-0.5 text-xs text-[#ffd740]">
                            <Loader2 className="h-3 w-3 animate-spin" />
                            {block.running}
                          </span>
                        )}
                        {block.pending > 0 && (
                          <span className="flex items-center gap-1 rounded-full bg-[#8888aa]/10 px-2 py-0.5 text-xs text-[#8888aa]">
                            <Clock className="h-3 w-3" />
                            {block.pending}
                          </span>
                        )}
                        {block.failed > 0 && (
                          <span className="flex items-center gap-1 rounded-full bg-[#ff5252]/10 px-2 py-0.5 text-xs text-[#ff5252]">
                            <XCircle className="h-3 w-3" />
                            {block.failed}
                          </span>
                        )}
                      </div>
                    )}

                    {/* Progress bar mini */}
                    {!isEmpty && (
                      <div className="ml-auto flex items-center gap-3">
                        <div className="hidden h-1.5 w-24 overflow-hidden rounded-full bg-[#0a0a1a] sm:block">
                          <div
                            className="h-full rounded-full bg-[#00e676] transition-all"
                            style={{
                              width: `${(block.completed / block.total) * 100}%`,
                            }}
                          />
                        </div>
                        <span className="text-xs text-[#8888aa]">
                          {block.completed}/{block.total}
                        </span>
                        {isOpen ? (
                          <ChevronDown className="h-4 w-4 text-[#8888aa]" />
                        ) : (
                          <ChevronRight className="h-4 w-4 text-[#8888aa]" />
                        )}
                      </div>
                    )}

                    {isEmpty && (
                      <span className="ml-auto text-xs text-[#555]">작업 없음</span>
                    )}
                  </button>

                  {/* Expanded job list */}
                  {isOpen && block.jobs.length > 0 && (
                    <div className="border-t border-[#2a2a5a]/50 px-4 py-2">
                      <div className="space-y-1.5">
                        {block.jobs.map((job) => {
                          const st = statusConfig[job.status] || statusConfig.pending;
                          return (
                            <div
                              key={job.job_id}
                              className="flex items-center gap-3 rounded-lg bg-[#0a0a1a]/60 px-3 py-2 text-sm"
                            >
                              {/* Status icon */}
                              <span className={st.color}>{st.icon}</span>

                              {/* Type badge */}
                              <span
                                className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${
                                  typeColor[job.type] || "bg-[#8888aa]/15 text-[#8888aa]"
                                }`}
                              >
                                {typeLabel[job.type] || job.type}
                              </span>

                              {/* Campaign info */}
                              <div className="flex-1 min-w-0">
                                <span className="font-medium text-white">
                                  {job.keyword}
                                </span>
                                <span className="ml-2 text-xs text-[#8888aa]">
                                  {job.customer_name}
                                </span>
                                {job.engage_like && (
                                  <Heart className="ml-1.5 inline h-3 w-3 text-[#ff6eb4]" />
                                )}
                                <span className="ml-1.5"><JobLayerBadges options={job.options} /></span>
                              </div>

                              {/* Duration / Status label */}
                              <div className="text-right">
                                {job.status === "completed" && job.duration_sec != null ? (
                                  <span className="flex items-center gap-1 text-xs text-[#00e676]">
                                    <Timer className="h-3 w-3" />
                                    {job.duration_sec.toFixed(0)}s
                                  </span>
                                ) : job.status === "failed" ? (
                                  <span className="text-xs text-[#ff5252]" title={job.error || ""}>
                                    {job.error ? job.error.slice(0, 20) : "실패"}
                                  </span>
                                ) : (
                                  <span className={`text-xs ${st.color}`}>{st.label}</span>
                                )}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </main>
    </>
  );
}
