#!/usr/bin/env bash
# Загрузка реальных датасетов AquaGeo в работающий под через kubectl.
#
# Запуск из КОРНЯ репозитория:
#   ./scripts/load_real_data.sh [NAMESPACE] [RELEASE]
# По умолчанию: NAMESPACE=aquageo, RELEASE=aquageo.
#
# Что делает:
#   1) находит web-под релиза;
#   2) kubectl cp датасеты из backend/data и data/ в writable /tmp/data пода
#      (root-FS пода read-only, поэтому именно /tmp);
#   3) гонит seed_reference -> import_data -> import_org_dataset ->
#      generate_hydropost_history -> recompute_assessments.
#
# Идемпотентно: импортеры используют update_or_create, повторный прогон безопасен.
set -euo pipefail

NS="${1:-aquageo}"
RELEASE="${2:-aquageo}"
CONTAINER=web

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BD="$ROOT/backend/data"
ORG_XLS="$ROOT/data/datasetFromOrganizators.xls"

REQUIRED=(
  "$BD/qazsu_hydroposts_334.csv"
  "$BD/export.geojson"
  "$BD/hotosm_kaz_waterways_lines_geojson.zip"
  "$BD/hotosm_kaz_waterways_polygons_geojson.zip"
  "$ORG_XLS"
)
for f in "${REQUIRED[@]}"; do
  [ -f "$f" ] || { echo "ОШИБКА: нет файла $f"; exit 1; }
done

POD="$(kubectl -n "$NS" get pod \
  -l "app.kubernetes.io/component=web,app.kubernetes.io/instance=$RELEASE" \
  -o jsonpath='{.items[0].metadata.name}')"
[ -n "$POD" ] || { echo "ОШИБКА: web-под не найден в namespace $NS (release $RELEASE)"; exit 1; }
echo ">> web-под: $POD"

kx()  { kubectl -n "$NS" exec "$POD" -c "$CONTAINER" -- "$@"; }
kcp() { kubectl -n "$NS" cp "$1" "$NS/$POD:$2" -c "$CONTAINER"; }

echo ">> Готовлю /tmp/data в поде"
kx mkdir -p /tmp/data

echo ">> Копирую датасеты в под (~42MB, может занять минуту)"
kcp "$BD/qazsu_hydroposts_334.csv"                  /tmp/data/qazsu_hydroposts_334.csv
kcp "$BD/export.geojson"                            /tmp/data/export.geojson
kcp "$BD/hotosm_kaz_waterways_lines_geojson.zip"    /tmp/data/hotosm_kaz_waterways_lines_geojson.zip
kcp "$BD/hotosm_kaz_waterways_polygons_geojson.zip" /tmp/data/hotosm_kaz_waterways_polygons_geojson.zip
kcp "$ORG_XLS"                                       /tmp/data/datasetFromOrganizators.xls

echo ">> Справочники (типы, бассейны, КАТО)"
kx python manage.py seed_reference

echo ">> Демо-аккаунты (viewer/engineer/manager/admin)"
kx python manage.py create_demo_users

echo ">> Импорт открытых источников: гидропосты + Overpass + HDX линии/полигоны"
kx python manage.py import_data \
  --hydroposts /tmp/data/qazsu_hydroposts_334.csv \
  --overpass   /tmp/data/export.geojson \
  --lines      /tmp/data/hotosm_kaz_waterways_lines_geojson.zip \
  --polygons   /tmp/data/hotosm_kaz_waterways_polygons_geojson.zip

echo ">> Импорт датасета организаторов (.xls, без геометрии, needs_geocoding)"
kx python manage.py import_org_dataset --path /tmp/data/datasetFromOrganizators.xls \
  || echo "!! import_org_dataset завершился с ошибкой — см. вывод выше"

echo ">> Временные ряды гидропостов + пересчёт оценок"
kx python manage.py generate_hydropost_history --days 90
kx python manage.py recompute_assessments || true

echo ">> ГОТОВО. Объектов в базе:"
kx python manage.py shell -c "from catalog.models import Structure; print(Structure.objects.count())"
