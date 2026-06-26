export interface ByTypeRow {
  type: string;
  type_name: string;
  count: number;
}

export interface ByCondition {
  counts: Record<string, number>;
  total: number;
  index: number;
}

export interface TerritoryItem {
  id: string;
  name: string;
  count: number;
}
export interface ByTerritory {
  group: string;
  items: TerritoryItem[];
}

export interface RiskSummary {
  flood: Record<string, number>;
  low_water: Record<string, number>;
  forecast_crossing: number;
  hydroposts: number;
}

export interface LevelPoint {
  date: string;
  avg_level: number | null;
}
