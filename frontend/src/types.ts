export interface StructureProperties {
  id: string;
  name_ru: string;
  type: string;
  type_name: string;
  condition_status: string;
  status: string;
  significance: string;
}

export interface StructureFeature {
  type: "Feature";
  id?: string | number;
  geometry: {
    type: "Point" | "LineString" | "Polygon" | "MultiPolygon" | "MultiLineString";
    coordinates: unknown;
  } | null;
  properties: StructureProperties;
}

export interface StructureFeatureCollection {
  type: "FeatureCollection";
  features: StructureFeature[];
}

export interface SchemaProperty {
  type?: string;
  title?: string;
}

export interface ObjectTypeDetail {
  code: string;
  name_ru: string;
  geometry_kind: string;
  schema: {
    properties?: Record<string, SchemaProperty>;
    required?: string[];
  };
}

export interface InspectionDTO {
  id: string;
  inspected_at: string;
  inspector: string;
  condition_observed: string;
  wear_percent: string | null;
  notes: string;
}

export interface AttachmentDTO {
  id: string;
  kind: string;
  file_url: string | null;
  created_at: string;
}

export interface StructureDetail {
  id: string;
  type: string;
  type_name: string;
  type_detail: ObjectTypeDetail;
  name_ru: string;
  name_kk: string;
  name_en: string;
  geom: { type: string; coordinates: unknown } | null;
  basin: string | null;
  basin_name: string | null;
  admin_unit: string | null;
  admin_unit_name: string | null;
  water_body: string | null;
  water_body_name: string | null;
  commissioning_year: number | null;
  wear_percent: string | null;
  responsible_org: string;
  significance: string;
  condition_status: string;
  status: string;
  attributes: Record<string, unknown>;
  inspections: InspectionDTO[];
  attachments: AttachmentDTO[];
}

export interface WaterBodyOption {
  id: string;
  name_ru: string;
  kind: string;
}

export interface StructureListItem {
  id: string;
  name_ru: string;
  type: string;
  type_name: string;
  condition_status: string;
  basin_name: string | null;
  admin_unit_name: string | null;
  commissioning_year: number | null;
  wear_percent: string | null;
  needs_geocoding: boolean;
}

export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}
