const MASTER_URL = process.env.MASTER_URL || "http://localhost:5000";

export async function fetchMaster(path: string, options?: RequestInit) {
  const url = `${MASTER_URL}${path}`;
  const res = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });
  if (!res.ok) {
    throw new Error(`Master API error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

export interface Campaign {
  id: number;
  type: string;
  customer_name: string;
  keyword: string;
  product_name: string;
  product_url: string;
  daily_target: number;
  dwell_time_min: number;
  dwell_time_max: number;
  active: number;
  created_at: string;
}

export interface Worker {
  id: string;
  hostname: string;
  max_chrome: number;
  status: string;
  last_heartbeat: string | null;
  jobs_completed: number;
  jobs_failed: number;
}

export interface DailyStats {
  date: string;
  total: number;
  completed: number;
  failed: number;
  running: number;
  pending: number;
  campaigns: CampaignStats[];
}

export interface CampaignStats {
  id: number;
  type: string;
  customer_name: string;
  keyword: string;
  daily_target: number;
  success: number;
  failed: number;
  pending: number;
  total: number;
}

export interface Summary {
  date: string;
  total: number;
  completed: number;
  failed: number;
  pending: number;
  running: number;
  progress_pct: number;
}

// Industry scheduling presets
export const INDUSTRY_PRESETS: Record<string, { label: string; weights: number[] }> = {
  uniform: {
    label: "균등 배분",
    weights: [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
  },
  meal: {
    label: "식사시간 집중 (음식점/카페)",
    weights: [0.1,0.05,0.02,0.02,0.02,0.05,0.2,0.5,0.7,0.8,1.0,1.5,1.5,1.0,0.8,0.7,0.8,1.2,1.5,1.3,1.0,0.8,0.5,0.3],
  },
  evening: {
    label: "저녁 집중 (뷰티/패션)",
    weights: [0.3,0.1,0.05,0.02,0.02,0.05,0.1,0.3,0.5,0.7,0.8,0.8,0.7,0.8,0.9,0.8,0.9,1.0,1.2,1.5,1.8,2.0,1.5,0.8],
  },
  morning: {
    label: "오전 집중 (병원/클리닉)",
    weights: [0.1,0.05,0.02,0.02,0.02,0.1,0.3,0.8,1.5,2.0,1.8,1.5,1.0,1.2,1.5,1.2,1.0,0.8,0.5,0.3,0.2,0.2,0.15,0.1],
  },
  afternoon: {
    label: "오후~저녁 (학원/교육)",
    weights: [0.1,0.05,0.02,0.02,0.02,0.05,0.1,0.2,0.3,0.5,0.6,0.7,0.8,1.0,1.2,1.5,1.8,1.5,1.2,1.0,0.8,0.6,0.4,0.2],
  },
  natural: {
    label: "자연스러운 패턴 (기본)",
    weights: [0.3,0.1,0.05,0.02,0.02,0.05,0.2,0.5,0.7,1.0,1.2,1.0,0.8,1.0,1.2,1.1,1.0,0.9,0.8,1.0,1.3,1.5,1.2,0.8],
  },
};
