// Single source of truth for condition colors (shared by map, legend, KPIs).
export const CONDITION_COLORS: Record<string, string> = {
  serviceable: "#1F9D57",
  monitoring: "#2F73E0",
  repair: "#E0921E",
  emergency: "#E0443E",
  nodata: "#8C97A7",
};

export const CONDITION_ORDER = [
  "serviceable",
  "monitoring",
  "repair",
  "emergency",
] as const;

export type ConditionKey = (typeof CONDITION_ORDER)[number];

export function conditionColor(status: string | null | undefined): string {
  if (!status) return CONDITION_COLORS.nodata;
  return CONDITION_COLORS[status] ?? CONDITION_COLORS.nodata;
}

// Material Symbols icon name per object type.
export const TYPE_ICONS: Record<string, string> = {
  canal: "water",
  hydropost: "sensors",
  lock: "lock",
  water_intake: "water_pump",
  pumping_station: "water_pump",
  dam: "water_drop",
  dike: "fence",
  reservoir: "water",
  hydro_unit: "hub",
  spillway: "waves",
  pond: "water",
};

export function typeIcon(code: string | null | undefined): string {
  if (!code) return "place";
  return TYPE_ICONS[code] ?? "place";
}
