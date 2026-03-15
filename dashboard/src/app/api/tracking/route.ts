import { NextRequest, NextResponse } from "next/server";
import { readFile } from "fs/promises";
import path from "path";

export const dynamic = "force-dynamic";

const CACHE_PATH = path.join(process.cwd(), "..", "data", "tracking_cache.json");

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

interface CampaignCache {
  latest: TrackingEntry | null;
  history: TrackingEntry[];
  trend: "up" | "down" | "stable";
}

export async function GET(req: NextRequest) {
  const campaignId = req.nextUrl.searchParams.get("campaignId");
  const days = parseInt(req.nextUrl.searchParams.get("days") || "30", 10);

  try {
    let raw: string;
    try {
      raw = await readFile(CACHE_PATH, "utf-8");
    } catch {
      // No cache file yet — return empty state
      return NextResponse.json({
        history: [],
        latest: null,
        trend: "stable",
        campaigns: [],
      });
    }

    const cache: Record<string, CampaignCache> = JSON.parse(raw);

    // If no campaignId, return list of available campaigns
    if (!campaignId) {
      const campaigns = Object.entries(cache).map(([id, data]) => ({
        id: parseInt(id, 10),
        customer_name: data.latest?.customer_name || `Campaign ${id}`,
        keyword: data.latest?.keyword || "",
        type: data.latest?.type || "",
        latest_rank: data.latest?.rank ?? null,
        trend: data.trend,
      }));
      return NextResponse.json({ campaigns, history: [], latest: null, trend: "stable" });
    }

    const entry = cache[campaignId];
    if (!entry) {
      return NextResponse.json({
        history: [],
        latest: null,
        trend: "stable",
      });
    }

    // Filter history by days
    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - days);
    const filtered = entry.history.filter((h) => {
      if (!h.checked_at) return true;
      return new Date(h.checked_at) >= cutoff;
    });

    return NextResponse.json({
      history: filtered,
      latest: entry.latest,
      trend: entry.trend || "stable",
    });
  } catch (e: unknown) {
    const message = e instanceof Error ? e.message : "Unknown error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
