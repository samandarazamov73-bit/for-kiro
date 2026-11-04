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

## Интерьер санатория (около 1975 г.)

Внутри этого же здания построен полный интерьер советского санатория. Экстерьер не изменён. Сцена собрана в Blender 4.5 LTS.

- 4 этажа, 209 помещений, 234 двери и проёма. Все 217 окон фасада выходят в реальные комнаты.
- **1-й этаж:** вестибюль, регистратура, гардероб, камера хранения, охрана, администрация (12 кабинетов), медотделение (14 помещений), столовая с кухней и пищеблоком (11 помещений), технические помещения (11). Палат на 1-м этаже нет.
- **2–4 этажи:** 90 палат (одно- и двухместные) и 2 палаты для маломобильных пациентов. На каждом этаже пост медсестры, процедурная, бельевые, санузлы и душевые, доступный санузел. Есть клубный зал, холлы отдыха и кинопроекционная.
- Три лестницы и служебный лифт **по ключу**: шахта, кабина, машинное помещение, механический указатель этажа, ключ-выключатели, таблички. Двери лифта закрыты.
- Около 2000 предметов советской мебели и оборудования, 365 светильников (часть мигает или не работает), процедурные текстуры: краска, обои, плитка, линолеум, терраццо.
- Интерьер — 63 639 треугольников, вместе с экстерьером около 105 700.

| Вестибюль и регистратура | Коридор 1-го этажа |
|---|---|
| ![](soviet_building/renders/interior/int_reception.png) | ![](soviet_building/renders/interior/int_corridor_ground.png) |
| **Служебный лифт по ключу** | **Кабина лифта** |
| ![](soviet_building/renders/interior/int_elevator.png) | ![](soviet_building/renders/interior/int_elevator_cabin.png) |
| **Кабинет главного врача** | **Двухместная палата** |
| ![](soviet_building/renders/interior/int_director.png) | ![](soviet_building/renders/interior/int_patient_double.png) |
| **Столовая** | **Клубный зал** |
| ![](soviet_building/renders/interior/int_dining.png) | ![](soviet_building/renders/interior/int_club_hall.png) |

Планы этажей: [1](soviet_building/plans/plan_floor1.png), [2](soviet_building/plans/plan_floor2.png), [3](soviet_building/plans/plan_floor3.png), [4](soviet_building/plans/plan_floor4.png). Ведомость помещений: [`rooms.csv`](soviet_building/plans/rooms.csv). Остальные рендеры лежат в [`soviet_building/renders/interior`](soviet_building/renders/interior).

Файлы:
- [`SovietSanatorium.blend`](soviet_building/export/blend/SovietSanatorium.blend): сцена Blender, текстуры берутся из `soviet_building/textures`
- [`SovietSanatorium.glb`](soviet_building/export/SovietSanatorium.glb): здание целиком с интерьером, текстуры внутри файла
- [`SovietSanatorium_Interior.glb`](soviet_building/export/SovietSanatorium_Interior.glb): только интерьер
- [`SovietSanatorium.fbx`](soviet_building/export/fbx/SovietSanatorium.fbx)

Подробное описание (конструкции, планировка, лифт, доступность, материалы, свойства объектов для движков, пересборка) — в [`soviet_building/INTERIOR.md`](soviet_building/INTERIOR.md).
