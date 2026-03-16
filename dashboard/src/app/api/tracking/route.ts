import { NextRequest, NextResponse } from "next/server";
import { fetchMaster } from "@/lib/api";

export const dynamic = "force-dynamic";

export async function GET(req: NextRequest) {
  const campaignId = req.nextUrl.searchParams.get("campaignId");
  const days = req.nextUrl.searchParams.get("days") || "30";

  try {
    let path = "/api/tracking";
    const params: string[] = [];
    if (campaignId) params.push(`campaignId=${campaignId}`);
    if (days) params.push(`days=${days}`);
    if (params.length > 0) path += `?${params.join("&")}`;

    const data = await fetchMaster(path);
    return NextResponse.json(data);
  } catch (e: unknown) {
    const message = e instanceof Error ? e.message : "Unknown error";
    return NextResponse.json({
      campaigns: [],
      history: [],
      latest: null,
      trend: "stable",
      error: message,
    });
  }
}
