import { MapContainer, TileLayer } from "react-leaflet";
import "leaflet/dist/leaflet.css";

// Jambyl region (Shu-Talas basin) center.
const CENTER: [number, number] = [43.2, 72.0];

export default function MapPage() {
  return (
    <div className="map-root">
      <MapContainer center={CENTER} zoom={7} scrollWheelZoom>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
      </MapContainer>
    </div>
  );
}
