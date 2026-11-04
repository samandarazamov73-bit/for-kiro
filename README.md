# Советское учебное здание 1970-х — low-poly 3D-модель

![Вид с ракурса референса](soviet_building/renders/view_reference_match.png)

42 040 треугольников, реальный масштаб в метрах, 10 PBR-материалов с собственными текстурами. Модель включает рабочий пандус с поворотной площадкой.

## Посмотреть в 3D прямо в браузере

- [Открыть в Babylon.js Sandbox](https://sandbox.babylonjs.com/?assetUrl=https://raw.githubusercontent.com/samandarazamov73-bit/for-kiro/soviet-school-model/soviet_building/export/SovietSchool.glb&autoRotate=true)
- [Открыть в three.js glTF Viewer](https://gltf-viewer.donmccurdy.com/#model=https://raw.githubusercontent.com/samandarazamov73-bit/for-kiro/soviet-school-model/soviet_building/export/SovietSchool.glb)

Файл весит около 40 МБ, поэтому загрузка занимает некоторое время.

## Скачать

- [Всё одним ZIP-архивом](https://github.com/samandarazamov73-bit/for-kiro/archive/refs/heads/soviet-school-model.zip): модель во всех форматах, текстуры, рендеры, исходники
- [SovietSchool.glb](https://github.com/samandarazamov73-bit/for-kiro/raw/soviet-school-model/soviet_building/export/SovietSchool.glb): один файл, текстуры внутри (рекомендуется)
- FBX, OBJ, glTF — папка [`soviet_building/export`](soviet_building/export)
- PBR-текстуры (BaseColor, Normal, ORM, Roughness, AO, Metallic) — папка [`soviet_building/textures`](soviet_building/textures)

## Рендеры

| Спереди | Спереди слева, 3/4 |
|---|---|
| ![](soviet_building/renders/view_front.png) | ![](soviet_building/renders/view_front_left_34.png) |
| **Спереди справа, 3/4** | **Сзади** |
| ![](soviet_building/renders/view_front_right_34.png) | ![](soviet_building/renders/view_rear.png) |
| **Сверху** | **Кровля** |
| ![](soviet_building/renders/view_top.png) | ![](soviet_building/renders/view_roof_detail.png) |
| **Пандус** | **Пандус, от низа маршей** |
| ![](soviet_building/renders/view_closeup_ramp.png) | ![](soviet_building/renders/view_closeup_ramp_foot.png) |
| **Вход и лестница** | **Фасад и окна** |
| ![](soviet_building/renders/view_closeup_entrance.png) | ![](soviet_building/renders/view_closeup_facade.png) |

Техническое описание (размеры, иерархия, материалы, параметры пандуса, исправления относительно референса, импорт в движки) — в [`soviet_building/README.md`](soviet_building/README.md).
