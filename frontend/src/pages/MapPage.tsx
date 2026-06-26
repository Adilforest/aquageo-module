import { useQuery } from "@tanstack/react-query";
import type { TFunction } from "i18next";
import L from "leaflet";
import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import { MapContainer, Marker, Polyline, Popup, TileLayer } from "react-leaflet";
import MarkerClusterGroup from "react-leaflet-cluster";
import { useSearchParams } from "react-router-dom";
import "leaflet/dist/leaflet.css";
import "leaflet.markercluster/dist/MarkerCluster.css";
import "leaflet.markercluster/dist/MarkerCluster.Default.css";

import { apiGet } from "../api/client";
import FilterPanel from "../components/FilterPanel";
import Legend from "../components/Legend";
import { conditionColor, typeIcon } from "../theme";
import type { StructureFeature, StructureFeatureCollection } from "../types";

const CENTER: [number, number] = [43.2, 72.0];

// [lon, lat] -> [lat, lon] for Leaflet.
type LatLng = [number, number];

function markerIcon(code: string, condition: string): L.DivIcon {
  const color = conditionColor(condition);
  const icon = typeIcon(code);
  return L.divIcon({
    className: "",
    iconSize: [28, 28],
    iconAnchor: [14, 14],
    popupAnchor: [0, -14],
    html:
      `<div style="background:${color};width:28px;height:28px;border-radius:50%;` +
      `display:flex;align-items:center;justify-content:center;border:2px solid #fff;` +
      `box-shadow:0 1px 4px rgba(0,0,0,.4)">` +
      `<span class="material-symbols-outlined" style="color:#fff;font-size:16px">${icon}</span></div>`,
  });
}

export default function MapPage() {
  const { t } = useTranslation();
  const [searchParams] = useSearchParams();
  const qs = searchParams.toString();
  const { data, isLoading, isError } = useQuery({
    queryKey: ["structures-geojson", qs],
    queryFn: () =>
      apiGet<StructureFeatureCollection>(`/structures/geojson/${qs ? `?${qs}` : ""}`),
  });

  const features = useMemo(
    () => (data?.features ?? []).filter((f) => f.geometry),
    [data],
  );

  const points = useMemo(
    () => features.filter((f) => f.geometry!.type === "Point"),
    [features],
  );
  const lines = useMemo(
    () => features.filter((f) => f.geometry!.type === "LineString"),
    [features],
  );
  const typesPresent = useMemo(
    () => Array.from(new Set(features.map((f) => f.properties.type))).sort(),
    [features],
  );

  return (
    <div className="map-root">
      <MapContainer center={CENTER} zoom={7} scrollWheelZoom preferCanvas>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {lines.map((f) => {
          const coords = f.geometry!.coordinates as [number, number][];
          const positions = coords.map(([lon, lat]) => [lat, lon] as LatLng);
          return (
            <Polyline
              key={`l-${f.properties.id}`}
              positions={positions}
              pathOptions={{ color: conditionColor(f.properties.condition_status), weight: 3 }}
            >
              <Popup>{popupContent(f, t)}</Popup>
            </Polyline>
          );
        })}

        <MarkerClusterGroup chunkedLoading maxClusterRadius={50}>
          {points.map((f) => {
            const [lon, lat] = f.geometry!.coordinates as [number, number];
            return (
              <Marker
                key={`p-${f.properties.id}`}
                position={[lat, lon]}
                icon={markerIcon(f.properties.type, f.properties.condition_status)}
              >
                <Popup>{popupContent(f, t)}</Popup>
              </Marker>
            );
          })}
        </MarkerClusterGroup>
      </MapContainer>

      <FilterPanel count={features.length} />
      {isLoading && <div className="map-overlay-count">{t("map.loading")}</div>}
      {isError && <div className="map-overlay-count">{t("map.error")}</div>}

      <Legend types={typesPresent} />
    </div>
  );
}

function popupContent(f: StructureFeature, t: TFunction) {
  const p = f.properties;
  return (
    <div style={{ minWidth: 180 }}>
      <strong>{p.name_ru}</strong>
      <div style={{ marginTop: 4 }}>
        {t(`types.${p.type}`, { defaultValue: p.type_name })}
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 4 }}>
        <span
          className="dot"
          style={{ background: conditionColor(p.condition_status), width: 10, height: 10 }}
        />
        {t(`condition.${p.condition_status}`, { defaultValue: t("condition.nodata") })}
      </div>
    </div>
  );
}
