export const ROLE_RANK: Record<string, number> = {
  viewer: 0,
  engineer: 1,
  manager: 2,
  admin: 3,
};

export function canEdit(role: string | null | undefined): boolean {
  if (!role) return false;
  return (ROLE_RANK[role] ?? -1) >= ROLE_RANK.engineer;
}
