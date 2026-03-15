"use client";

import { Nav } from "@/components/nav";
import { Rocket } from "lucide-react";

const phases = [
  {
    phase: "PHASE 1",
    title: "즉시 (대시보드 MVP)",
    color: "#ff5252",
    items: [
      { title: "Next.js 대시보드 구축", desc: "캠페인 CRUD, 고객 관리, 실시간 현황, Worker 모니터링", tag: "Core", tagColor: "#00e676", done: true },
      { title: "업종별 자동 스케줄링", desc: "업종 선택 → 시간대 자동 배분 + 커스텀 슬라이더", tag: "Core", tagColor: "#00e676", done: true },
      { title: "캠페인별 시간 전략 DB 반영", desc: "기존 글로벌 가중치 → 캠페인별 개별 가중치로 변경 (쇼핑/블로그/플레이스 프리셋)", tag: "Backend", tagColor: "#00e676", done: true },
    ],
  },
  {
    phase: "PHASE 2",
    title: "서비스 고도화",
    color: "#ff9052",
    items: [
      { title: "성과 검증 시스템", desc: "네이버 검색 순위 추적, Before/After 리포트, 대시보드 /tracking 페이지", tag: "High", tagColor: "#ff9052", done: true },
      { title: "블로그 트래픽 엔진", desc: "세 번째 캠페인 타입 + 네이버 로그인 모듈 + 공감/댓글 액션", tag: "High", tagColor: "#ff9052", done: true },
      { title: "알림 시스템", desc: "Telegram 일간 리포트, 이상 감지 알림, 목표 달성 알림 (notifier.py)", tag: "High", tagColor: "#ff9052", done: true },
    ],
  },
  {
    phase: "PHASE 3",
    title: "스케일업",
    color: "#448aff",
    items: [
      { title: "VPS 워커 배포", desc: "deploy_vps.sh 자동 배포, systemd 서비스, 그레이스풀 셧다운", tag: "Medium", tagColor: "#8888aa", done: true },
      { title: "VPS 자동 스케일 + 키워드 리서치", desc: "클라우드 auto-scale, 네이버 광고 API 연동, 모바일 트래픽", tag: "Medium", tagColor: "#8888aa", done: false },
    ],
  },
];

export default function RoadmapPage() {
  return (
    <>
      <Nav />
      <main className="mx-auto max-w-7xl px-4 pt-20 pb-12">
        <div className="mb-6">
          <p className="text-xs font-bold uppercase tracking-widest text-[#8b6cff]">Development Roadmap</p>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Rocket className="h-6 w-6 text-[#00e676]" />
            개발 로드맵
          </h1>
          <p className="text-sm text-[#8888aa]">우선순위별 개발 계획</p>
        </div>

        <div className="space-y-8">
          {phases.map((p) => (
            <div key={p.phase}>
              <div className="mb-3 flex items-center gap-2">
                <span className="rounded-md px-2.5 py-0.5 text-xs font-extrabold text-black" style={{ background: p.color }}>{p.phase}</span>
                <span className="text-base font-bold text-white">{p.title}</span>
              </div>
              <div className="space-y-3">
                {p.items.map((item) => (
                  <div
                    key={item.title}
                    className={`rounded-xl border p-5 transition-colors ${
                      item.done
                        ? "border-[#00e676]/30 bg-[#00e676]/[0.03]"
                        : "border-[#2a2a5a] bg-[#111127]"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className={`flex h-6 w-6 items-center justify-center rounded-full text-sm ${item.done ? "bg-[#00e676]/20 text-[#00e676]" : "bg-[#2a2a5a] text-[#555]"}`}>
                          {item.done ? "✓" : "○"}
                        </div>
                        <div>
                          <h3 className={`font-bold ${item.done ? "text-[#00e676]" : "text-white"}`}>{item.title}</h3>
                          <p className="text-xs text-[#8888aa]">{item.desc}</p>
                        </div>
                      </div>
                      <div className="flex gap-2">
                        <span className="rounded-full px-2 py-0.5 text-[10px] font-bold" style={{ color: item.tagColor, background: `${item.tagColor}15` }}>{item.tag}</span>
                        {item.done && <span className="rounded-full bg-[#00e676]/15 px-2 py-0.5 text-[10px] font-bold text-[#00e676]">완료</span>}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* Progress summary */}
        <div className="mt-10 rounded-xl border border-[#2a2a5a] bg-[#111127] p-6">
          <h3 className="mb-3 font-bold text-white">진행 현황</h3>
          <div className="grid gap-4 md:grid-cols-3">
            {phases.map((p) => {
              const total = p.items.length;
              const done = p.items.filter((i) => i.done).length;
              const pct = (done / total) * 100;
              return (
                <div key={p.phase} className="rounded-lg border border-[#2a2a5a] bg-[#0a0a1a] p-4">
                  <div className="mb-2 flex items-center justify-between text-sm">
                    <span className="font-bold" style={{ color: p.color }}>{p.phase}</span>
                    <span className="font-mono text-xs text-[#8888aa]">{done}/{total}</span>
                  </div>
                  <div className="h-2 overflow-hidden rounded-full bg-[#16163a]">
                    <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, background: p.color }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </main>
    </>
  );
}
