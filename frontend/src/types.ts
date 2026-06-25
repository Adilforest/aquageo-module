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
