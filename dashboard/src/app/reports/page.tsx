"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Nav } from "@/components/nav";
import { FileText, BarChart3, Globe, ChevronRight } from "lucide-react";

interface CampaignSummary {
  id: number;
  customer_name: string;
  keyword: string;
  type: string;
  latest_rank: number | null;
  trend: string;
}

export default function ReportsPage() {
  const router = useRouter();
  const [campaigns, setCampaigns] = useState<CampaignSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedCustomer, setSelectedCustomer] = useState<string>("");
  const [days, setDays] = useState(30);

  useEffect(() => {
    (async () => {
      try {
        const res = await fetch("/api/tracking");
        if (res.ok) {
          const data = await res.json();
          setCampaigns(data.campaigns || []);
        }
      } catch {
        // silently handle
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  // Group campaigns by customer_name
  const customers = Array.from(
    new Set(campaigns.map((c) => c.customer_name).filter(Boolean))
  );

  // Auto-select first customer
  useEffect(() => {
    if (!selectedCustomer && customers.length > 0) {
      setSelectedCustomer(customers[0]);
    }
  }, [customers, selectedCustomer]);

  const customerCampaigns = campaigns.filter(
    (c) => c.customer_name === selectedCustomer
  );

  const reportTypes = [
    {
      id: "blog",
      title: "블로그 성과 보고서",
      description: "블로그 작성 서비스 고객용 — 키워드 순위 변화 리포트",
      icon: FileText,
      color: "#00e676",
      path: "/reports/blog",
    },
    {
      id: "traffic",
      title: "트래픽 종합 보고서",
      description: "블로그 + 트래픽 서비스 고객용 — 순위 + 방문 데이터",
      icon: Globe,
      color: "#448aff",
      path: "/reports/traffic",
    },
  ];

  return (
    <>
      <Nav />
      <main className="mx-auto max-w-7xl px-4 pt-20 pb-12">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-white">
            <BarChart3 className="mr-2 inline h-6 w-6 text-[#00e676]" />
            보고서
          </h1>
          <p className="mt-1 text-sm text-[#8888aa]">
            고객별 성과 보고서를 생성합니다.
          </p>
        </div>

        {loading ? (
          <p className="py-16 text-center text-sm text-[#8888aa]">로딩 중...</p>
        ) : customers.length === 0 ? (
          <div className="rounded-xl border border-[#2a2a5a] bg-[#111127] p-12 text-center">
            <FileText className="mx-auto mb-3 h-10 w-10 text-[#8888aa]" />
            <p className="text-sm text-[#8888aa]">
              등록된 캠페인이 없습니다. 캠페인을 먼저 등록하세요.
            </p>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Customer Selector + Period */}
            <div className="flex flex-wrap items-center gap-3">
              <div className="min-w-[200px] flex-1">
                <label className="mb-1 block text-xs text-[#8888aa]">
                  고객 선택
                </label>
                <select
                  value={selectedCustomer}
                  onChange={(e) => setSelectedCustomer(e.target.value)}
                  className="w-full rounded-lg border border-[#2a2a5a] bg-[#0a0a1a] px-3 py-2 text-sm text-white focus:border-[#00e676] focus:outline-none"
                >
                  <option value="">고객을 선택하세요</option>
                  {customers.map((name) => (
                    <option key={name} value={name}>
                      {name} ({campaigns.filter((c) => c.customer_name === name).length}개 캠페인)
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="mb-1 block text-xs text-[#8888aa]">
                  조회 기간
                </label>
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

            {/* Selected Customer Info */}
            {selectedCustomer && (
              <div className="rounded-xl border border-[#2a2a5a] bg-[#111127] p-4">
                <p className="text-xs text-[#8888aa]">선택된 고객</p>
                <p className="mt-1 text-lg font-semibold text-white">
                  {selectedCustomer}
                </p>
                <p className="mt-1 text-xs text-[#8888aa]">
                  {customerCampaigns.length}개 캠페인 /{" "}
                  {customerCampaigns.map((c) => c.keyword).join(", ")}
                </p>
              </div>
            )}

            {/* Report Type Cards */}
            <div className="grid gap-4 md:grid-cols-2">
              {reportTypes.map((report) => {
                const Icon = report.icon;
                const disabled = !selectedCustomer;
                return (
                  <button
                    key={report.id}
                    disabled={disabled}
                    onClick={() =>
                      router.push(
                        `${report.path}?customer=${encodeURIComponent(selectedCustomer)}&days=${days}`
                      )
                    }
                    className={`group rounded-xl border p-6 text-left transition-all ${
                      disabled
                        ? "cursor-not-allowed border-[#2a2a5a]/50 bg-[#111127]/50 opacity-50"
                        : "border-[#2a2a5a] bg-[#111127] hover:border-opacity-80 hover:bg-[#16163a]"
                    }`}
                    style={
                      !disabled
                        ? { borderColor: `${report.color}33` }
                        : undefined
                    }
                  >
                    <div className="flex items-start justify-between">
                      <div
                        className="flex h-12 w-12 items-center justify-center rounded-lg"
                        style={{ backgroundColor: `${report.color}15` }}
                      >
                        <Icon
                          className="h-6 w-6"
                          style={{ color: report.color }}
                        />
                      </div>
                      {!disabled && (
                        <ChevronRight className="h-5 w-5 text-[#8888aa] transition-transform group-hover:translate-x-1" />
                      )}
                    </div>
                    <h3
                      className="mt-4 text-lg font-semibold"
                      style={{ color: disabled ? "#8888aa" : report.color }}
                    >
                      {report.title}
                    </h3>
                    <p className="mt-1 text-sm text-[#8888aa]">
                      {report.description}
                    </p>
                  </button>
                );
              })}
            </div>
          </div>
        )}
      </main>
    </>
  );
}
