"use client";

import { useEffect, useState, useCallback } from "react";
import { Nav } from "@/components/nav";
import { timeAgo } from "@/lib/utils";
import {
  Monitor,
  Wifi,
  WifiOff,
  CheckCircle2,
  RefreshCw,
  Chrome,
} from "lucide-react";

interface Worker {
  id: string;
  hostname: string;
  max_chrome: number;
  status: string;
  last_heartbeat: string | null;
  jobs_completed: number;
  jobs_failed: number;
}

export default function WorkersPage() {
  const [workers, setWorkers] = useState<Worker[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchWorkers = useCallback(async () => {
    try {
      const res = await fetch("/api/workers");
      if (res.ok) {
        const data = await res.json();
        setWorkers(data.workers || []);
      }
    } catch {
      // silently handle
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchWorkers();
    const timer = setInterval(fetchWorkers, 10000);
    return () => clearInterval(timer);
  }, [fetchWorkers]);

  const onlineCount = workers.filter((w) => w.status === "online").length;
  const totalCompleted = workers.reduce((a, w) => a + w.jobs_completed, 0);
  const totalFailed = workers.reduce((a, w) => a + w.jobs_failed, 0);
  const totalChrome = workers.reduce((a, w) => a + w.max_chrome, 0);

  return (
    <>
      <Nav />
      <main className="mx-auto max-w-7xl px-4 pt-20 pb-12">
        <div className="mb-6 flex items-center justify-between">
          <h1 className="text-2xl font-bold text-white">워커 모니터</h1>
          <button
            onClick={() => {
              setLoading(true);
              fetchWorkers();
            }}
            className="flex items-center gap-1.5 rounded-md bg-[#16163a] px-3 py-1.5 text-sm text-[#8888aa] transition-colors hover:bg-[#2a2a5a] hover:text-white"
          >
            <RefreshCw
              className={`h-4 w-4 ${loading ? "animate-spin" : ""}`}
            />
            새로고침
          </button>
        </div>

        {/* Summary Cards */}
        <div className="mb-8 grid grid-cols-2 gap-4 md:grid-cols-4">
          <div className="rounded-xl border border-[#2a2a5a] bg-[#111127] p-4">
            <div className="mb-2 flex items-center justify-between">
              <span className="text-xs text-[#8888aa]">전체 워커</span>
              <Monitor className="h-5 w-5 text-[#448aff]" />
            </div>
            <div className="text-2xl font-bold font-mono text-white">
              {workers.length}
            </div>
          </div>
          <div className="rounded-xl border border-[#2a2a5a] bg-[#111127] p-4">
            <div className="mb-2 flex items-center justify-between">
              <span className="text-xs text-[#8888aa]">온라인</span>
              <Wifi className="h-5 w-5 text-[#00e676]" />
            </div>
            <div className="text-2xl font-bold font-mono text-[#00e676]">
              {onlineCount}
            </div>
          </div>
          <div className="rounded-xl border border-[#2a2a5a] bg-[#111127] p-4">
            <div className="mb-2 flex items-center justify-between">
              <span className="text-xs text-[#8888aa]">Chrome 슬롯</span>
              <Chrome className="h-5 w-5 text-[#ffd740]" />
            </div>
            <div className="text-2xl font-bold font-mono text-[#ffd740]">
              {totalChrome}
            </div>
          </div>
          <div className="rounded-xl border border-[#2a2a5a] bg-[#111127] p-4">
            <div className="mb-2 flex items-center justify-between">
              <span className="text-xs text-[#8888aa]">성공률</span>
              <CheckCircle2 className="h-5 w-5 text-[#00e676]" />
            </div>
            <div className="text-2xl font-bold font-mono text-white">
              {totalCompleted + totalFailed > 0
                ? (
                    (totalCompleted / (totalCompleted + totalFailed)) *
                    100
                  ).toFixed(1)
                : "0.0"}
              %
            </div>
          </div>
        </div>

        {/* Worker Cards */}
        {loading ? (
          <p className="py-12 text-center text-sm text-[#8888aa]">
            로딩 중...
          </p>
        ) : workers.length === 0 ? (
          <div className="rounded-xl border border-[#2a2a5a] bg-[#111127] p-12 text-center">
            <WifiOff className="mx-auto mb-4 h-12 w-12 text-[#555]" />
            <p className="text-[#8888aa]">등록된 워커가 없습니다</p>
            <p className="mt-1 text-xs text-[#555]">
              python worker.py로 워커를 시작하세요
            </p>
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {workers.map((w) => {
              const isOnline = w.status === "online";
              const successRate =
                w.jobs_completed + w.jobs_failed > 0
                  ? (
                      (w.jobs_completed / (w.jobs_completed + w.jobs_failed)) *
                      100
                    ).toFixed(1)
                  : "0.0";

              return (
                <div
                  key={w.id}
                  className={`rounded-xl border p-5 transition-colors ${
                    isOnline
                      ? "border-[#00e676]/30 bg-[#111127]"
                      : "border-[#2a2a5a] bg-[#0a0a1a] opacity-70"
                  }`}
                >
                  <div className="mb-3 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div
                        className={`h-2.5 w-2.5 rounded-full ${
                          isOnline
                            ? "bg-[#00e676] shadow-[0_0_8px_#00e676]"
                            : "bg-[#555]"
                        }`}
                      />
                      <span className="font-mono text-sm font-medium text-white">
                        {w.id}
                      </span>
                    </div>
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs ${
                        isOnline
                          ? "bg-[#00e676]/15 text-[#00e676]"
                          : "bg-[#ff5252]/15 text-[#ff5252]"
                      }`}
                    >
                      {isOnline ? "온라인" : "오프라인"}
                    </span>
                  </div>

                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-[#8888aa]">호스트</span>
                      <span className="font-mono text-[#e0e0e0]">
                        {w.hostname}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[#8888aa]">Chrome 슬롯</span>
                      <span className="font-mono text-[#e0e0e0]">
                        {w.max_chrome}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[#8888aa]">완료</span>
                      <span className="font-mono text-[#00e676]">
                        {w.jobs_completed.toLocaleString()}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[#8888aa]">실패</span>
                      <span className="font-mono text-[#ff5252]">
                        {w.jobs_failed.toLocaleString()}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[#8888aa]">성공률</span>
                      <span className="font-mono text-white">
                        {successRate}%
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[#8888aa]">마지막 신호</span>
                      <span className="font-mono text-xs text-[#e0e0e0]">
                        {timeAgo(w.last_heartbeat)}
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </main>
    </>
  );
}
