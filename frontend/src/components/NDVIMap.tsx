import { useCallback, useEffect, useMemo } from "react";
import {
  GeoJSON,
  LayerGroup,
  MapContainer,
  TileLayer,
  useMap,
  useMapEvents,
} from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import "leaflet-draw/dist/leaflet.draw.css";
import "leaflet-draw";

type Roi = Record<string, unknown> | null;
export type MapStyle = "light" | "dark" | "satellite";

function FitBounds({ bounds }: { bounds: number[] | null | undefined }) {
  const map = useMap();
  useEffect(() => {
    if (!bounds || bounds.length !== 4) return;
    const b: L.LatLngBoundsExpression = [
      [bounds[1], bounds[0]],
      [bounds[3], bounds[2]],
    ];
    map.fitBounds(b, { padding: [24, 24], maxZoom: 14 });
  }, [map, bounds]);
  return null;
}

function FlyToTarget({ target }: { target: { lat: number; lng: number; zoom?: number } | null }) {
  const map = useMap();
  useEffect(() => {
    if (!target) return;
    map.flyTo([target.lat, target.lng], target.zoom ?? Math.max(map.getZoom(), 12), {
      animate: true,
      duration: 0.8,
    });
  }, [map, target]);
  return null;
}

function DrawToolbar({
  onPolygon,
}: {
  onPolygon: (gj: Record<string, unknown>) => void;
}) {
  const map = useMap();
  useEffect(() => {
    const fg = new L.FeatureGroup();
    map.addLayer(fg);
    const Draw = (L as unknown as { Control: { Draw: new (o: Record<string, unknown>) => L.Control } }).Control
      .Draw;
    const draw = new Draw({
      draw: {
        polygon: { allowIntersection: false, showArea: false },
        polyline: false,
        rectangle: false,
        circle: false,
        marker: false,
        circlemarker: false,
      },
      edit: { featureGroup: fg, remove: true },
    });
    map.addControl(draw);
    const onCreated = (e: L.LeafletEvent & { layer: L.Layer }) => {
      fg.clearLayers();
      const layer = e.layer;
      fg.addLayer(layer);
      const gj = layer.toGeoJSON() as Record<string, unknown>;
      onPolygon(gj);
    };
    map.on("draw:created", onCreated);
    return () => {
      map.off("draw:created", onCreated);
      map.removeControl(draw);
      map.removeLayer(fg);
    };
  }, [map, onPolygon]);
  return null;
}

function MapClick({
  enabled,
  onPick,
  onPickLocation,
}: {
  enabled: boolean;
  onPick: (lat: number, lng: number, map: L.Map) => void;
  onPickLocation?: (lat: number, lng: number) => void;
}) {
  const map = useMap();
  useMapEvents({
    click(e) {
      onPickLocation?.(e.latlng.lat, e.latlng.lng);
      if (!enabled) return;
      onPick(e.latlng.lat, e.latlng.lng, map);
    },
  });
  return null;
}

export default function NDVIMap({
  mapStyle,
  roi,
  bounds,
  ndviTileUrl,
  classTileUrl,
  rfTileUrl,
  kmeansTileUrl,
  showClassification,
  showRf,
  showKmeans,
  compareNdviUrl,
  compareOpacity,
  mapTarget,
  onDrawPolygon,
  onMapClick,
  onPickLocation,
  clickSampleEnabled,
}: {
  mapStyle: MapStyle;
  roi: Roi;
  bounds?: number[] | null;
  ndviTileUrl?: string | null;
  classTileUrl?: string | null;
  rfTileUrl?: string | null;
  kmeansTileUrl?: string | null;
  showClassification: boolean;
  showRf: boolean;
  showKmeans: boolean;
  compareNdviUrl?: string | null;
  compareOpacity: number;
  mapTarget?: { lat: number; lng: number; zoom?: number } | null;
  onDrawPolygon: (gj: Record<string, unknown>) => void;
  onMapClick: (lat: number, lng: number, map: L.Map) => void;
  onPickLocation?: (lat: number, lng: number) => void;
  clickSampleEnabled: boolean;
}) {
  const baseConfig = useMemo(() => {
    if (mapStyle === "satellite") {
      return {
        url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attribution: "Tiles &copy; Esri",
      };
    }
    if (mapStyle === "dark") {
      return {
        url: "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
        attribution: "&copy; CARTO",
      };
    }
    return {
      url: "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
      attribution: "&copy; CARTO",
    };
  }, [mapStyle]);

  const onPoly = useCallback(
    (gj: Record<string, unknown>) => {
      onDrawPolygon(gj);
    },
    [onDrawPolygon]
  );

  const center = useMemo(() => L.latLng(20.5937, 78.9629), []);

  return (
    <MapContainer center={center} zoom={5} className="h-full w-full rounded-xl z-0" scrollWheelZoom>
      <TileLayer attribution={baseConfig.attribution} url={baseConfig.url} />
      {mapStyle === "satellite" ? (
        <TileLayer
          attribution="&copy; OpenStreetMap contributors &copy; CARTO"
          url="https://{s}.basemaps.cartocdn.com/light_only_labels/{z}/{x}/{y}{r}.png"
          pane="overlayPane"
          zIndex={4}
        />
      ) : null}
      <FitBounds bounds={bounds ?? null} />
      <FlyToTarget target={mapTarget ?? null} />
      <DrawToolbar onPolygon={onPoly} />
      <MapClick enabled={clickSampleEnabled} onPick={onMapClick} onPickLocation={onPickLocation} />

      {ndviTileUrl ? (
        <TileLayer url={ndviTileUrl} opacity={compareNdviUrl ? 1 - compareOpacity : 0.82} zIndex={5} />
      ) : null}
      {compareNdviUrl ? (
        <TileLayer url={compareNdviUrl} opacity={compareOpacity} zIndex={6} />
      ) : null}

      {showClassification && classTileUrl ? (
        <TileLayer url={classTileUrl} opacity={0.72} zIndex={7} />
      ) : null}
      {showRf && rfTileUrl ? <TileLayer url={rfTileUrl} opacity={0.65} zIndex={8} /> : null}
      {showKmeans && kmeansTileUrl ? <TileLayer url={kmeansTileUrl} opacity={0.6} zIndex={9} /> : null}

      {roi ? (
        <LayerGroup>
          <GeoJSON
            data={roi as never}
            style={{
              color: "#22c55e",
              weight: 2,
              fillOpacity: 0.12,
            }}
          />
        </LayerGroup>
      ) : null}
    </MapContainer>
  );
}
