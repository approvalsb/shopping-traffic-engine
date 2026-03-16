"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { BarChart3, Settings, Monitor, Zap, Shield, Calculator, CreditCard, Rocket, Search, CalendarClock } from "lucide-react";
import { cn } from "@/lib/utils";

const links = [
  { href: "/", label: "대시보드", icon: BarChart3 },
  { href: "/campaigns", label: "캠페인", icon: Settings },
  { href: "/workers", label: "워커", icon: Monitor },
  { href: "/stealth", label: "감지방지", icon: Shield },
  { href: "/cost", label: "원가분석", icon: Calculator },
  { href: "/pricing", label: "요금제", icon: CreditCard },
  { href: "/schedule", label: "작업 스케줄", icon: CalendarClock },
  { href: "/tracking", label: "성과 추적", icon: Search },
  { href: "/roadmap", label: "로드맵", icon: Rocket },
];

export function Nav() {
  const pathname = usePathname();

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 border-b border-[#2a2a5a] bg-[#0a0a1a]/95 backdrop-blur-sm">
      <div className="mx-auto flex h-14 max-w-7xl items-center gap-6 px-4">
        <Link href="/" className="flex items-center gap-2 font-bold text-[#00e676]">
          <Zap className="h-5 w-5" />
          <span>Traffic Engine</span>
        </Link>
        <div className="flex gap-1 overflow-x-auto scrollbar-hide">
          {links.map((link) => {
            const Icon = link.icon;
            const active =
              link.href === "/" ? pathname === "/" : pathname.startsWith(link.href);
            return (
              <Link
                key={link.href}
                href={link.href}
                className={cn(
                  "flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm transition-colors",
                  active
                    ? "bg-[#00e676]/15 text-[#00e676]"
                    : "text-[#8888aa] hover:bg-[#16163a] hover:text-[#e0e0e0]"
                )}
              >
                <Icon className="h-4 w-4" />
                {link.label}
              </Link>
            );
          })}
        </div>
      </div>
    </nav>
  );
}
