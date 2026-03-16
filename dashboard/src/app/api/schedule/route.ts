import { NextRequest, NextResponse } from "next/server";
import { fetchMaster } from "@/lib/api";

export const dynamic = "force-dynamic";

export async function GET(req: NextRequest) {
  const date = req.nextUrl.searchParams.get("date") || "";

  try {
    const params = date ? `?date=${date}` : "";
    const data = await fetchMaster(`/api/schedule${params}`);
    return NextResponse.json(data);
  } catch (e: unknown) {
    const message = e instanceof Error ? e.message : "Unknown error";
    return NextResponse.json({
      date: "",
      total: 0,
      completed: 0,
      failed: 0,
      timeline: [],
      error: message,
    });
  }
}
