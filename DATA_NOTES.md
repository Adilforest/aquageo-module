# DATA_NOTES.md — исходные данные и маппинг для импортёра

Файлы лежат в `backend/data/`. Это конкретный маппинг для issue #8 (импортёр).
Проверено на реальных файлах.

## Инвентарь

- `qazsu_hydroposts_334.csv`: 334 гидропоста по 8 бассейнам. Шу-Талас 15,
  Жамбылская область 16. Есть координаты.
- `export.geojson`: Overpass по Жамбылу, 2359 точек (центроиды из `out center`).
- `hotosm_kaz_waterways_lines_geojson.geojson`: HDX, ВСЯ страна, ~94 МБ,
  LineString. Каналы, канавы, реки, ручьи.
- `hotosm_kaz_waterways_polygons_geojson.geojson`: HDX, вся страна, ~86 МБ,
  Polygon. Водоёмы и водохранилища.
- Дубликат: `hotosm_kaz_waterways_lines_geojson__1_.zip` идентичен основному
  lines-архиву, удалить.

## Правила маппинга

Базовое разделение: реки и ручьи (river, stream) это **WaterBody** (водные
объекты), каналы и канавы (canal, ditch) это **Structure**. Не путать.
`name:kk` всегда кладём в `name_kk` (i18n).

### 1. qazsu_hydroposts_334.csv  ->  ObjectType = hydropost

Колонки: id, code, name, bassein, region, longitude, latitude, danger_level,
level_mean, water_temp, date.

- geom = Point(longitude, latitude)
- name_ru = name
- basin = по bassein (значения: Шу-Талас, Иртыш, Балхаш-Алаколь и т.д.)
- admin_unit = по region (например Жамбылская область)
- HydropostReading: ts = date, water_level = level_mean, water_temp = water_temp,
  status_code = danger_level (low | no_data | unfavorable | danger)

Импортируем все 334 (для скейла на регионы). Для демо Жамбыла фильтр
region = Жамбылская область или bassein = Шу-Талас.

### 2. export.geojson (Overpass, точки)  ->  точечные сооружения

Берём только точечные объекты:
- waterway = dam (19) -> dam
- waterway = weir (12) -> spillway
- waterway = lock_gate (2) -> lock
- man_made = dyke (25) -> dike
- man_made = clarifier (18) -> treatment (или пропустить)

НЕ берём отсюда canal, ditch, river, stream: это центроиды, линии берём из HDX.
Имена: name, name:ru, name:kk.

### 3. HDX lines (~94 МБ, LineString, вся страна)

Свойства: name, name:ru, name:kk, name:en, waterway, width, depth, covered,
tunnel, natural, water, osm_id.

- waterway = canal -> Structure(canal) с LineString
- waterway = ditch -> canal или пропустить (их очень много)
- waterway = river | stream -> WaterBody(kind = river), НЕ Structure

ВАЖНО: фильтровать по Жамбылу ДО загрузки. Файл большой, не делать
`json.load` целиком. Варианты: потоковый парсинг (fiona или ijson) с bbox,
либо фильтр по полигону Шу-Таласского бассейна (у Basin есть geom).
Примерный bbox Жамбыла: lon 69.0..76.0, lat 42.0..46.0.

### 4. HDX polygons (~86 МБ, Polygon, вся страна)

- natural = water, water = reservoir | lake -> WaterBody (полигон)
- Фильтр по Жамбылу как в п.3. Сюда попадёт Тасоткельское и другие водохранилища.

## Именованные гидроузлы

Таласский, Темирбекский, Жеимбетский, Уюкский (на Таласе), Ассинский (на Асе),
Фурмановский (на Шу), Тасоткель. В OSM могут быть как точки (weir/plant) или
отсутствовать. Если в данных нет, геокодить по имени через Nominatim и заводить
как Structure нужного типа (hydro_unit или dam).

## Чего нет в источниках

- Насосные станции (pumping_station) в OSM по Жамбылу почти не размечены.
- Износ, дата осмотра, тех. состояние: в источниках нет, генерировать
  правдоподобно для демо (см. CLAUDE.md п.13).
