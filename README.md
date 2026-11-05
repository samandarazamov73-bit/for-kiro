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

## Игра на Godot: электроколяска в полузаброшенном санатории

Внутри этого же здания построен полный интерьер советского санатория для пожилых. Санаторий давно не обслуживают: мебель на месте, но везде пыль и паутина, цветы почти засохли, часть ламп перегорела или мигает. Атмосфера страшноватая, но без перебора. Экстерьер не изменён.

Из этого здания сделана игра на **Godot 4.7**: вы в электроколяске, вид от первого лица, можно заехать в любую комнату.

![Кадры из игры](soviet_building/renders/game_overview.jpg)

**Как играть:** скачайте [Godot 4.7](https://godotengine.org/download), нажмите Import, выберите `soviet_building/game/project.godot` и нажмите F5. Управление: W/A/S/D — ехать, мышь — смотреть, E — открыть дверь или нажать выключатель и кнопку лифта, колесо мыши — скорость 1–5, H — гудок, Esc — пауза. Подробнее — в [`soviet_building/game/README.md`](soviet_building/game/README.md).

- **Коляска** ведёт себя как настоящая: 5 скоростей до 6,3 км/ч, плавный разгон, тормоза щёлкают, разворот на месте, о стену останавливается с ударом. Видны подлокотники, джойстик и колени под пледом.
- **Двери:** 218 дверей открываются, некоторые приоткрыты, технические помещения заперты. Двери стали больше: 2,3 м в высоту, обычные 1,0 м в ширину, двойные 1,5–1,6 м.
- **Свет:** в каждой комнате выключатель у двери (181 шт.), 75 ламп перегорели, 29 мигают.
- **Лифт** работает: кнопки вызова на этажах и 1–4 в кабине, автоматические двери. По лестнице на коляске не проехать.
- **Крысы и тараканы:** их немного, 12 крыс и 39 тараканов. Они убегают от коляски и от света.
- **Звук:** мотор коляски, двери, лифт, выключатели, гул ламп, писк крыс, дальние скрипы, капли и ветер.
- Исправлены модели: у стульев и столов настоящие ножки вместо плоских картинок, люстры больше не мерцают, кресла и диваны с мягкими подушками. На всех текстурах лёгкий шум и немного грязи.
- 212 помещений, 237 дверных проёмов, около 3400 предметов. Модель — 189 528 треугольников (лимит 200 000). Работа игры проверена 27 автоматическими тестами.

Рендеры Cycles в [`soviet_building/renders/interior`](soviet_building/renders/interior) сделаны до этой переделки: на них чистая уютная версия. Текущий вид — на кадрах из игры в [`soviet_building/renders/game`](soviet_building/renders/game).

Планы этажей: [1](soviet_building/plans/plan_floor1.png), [2](soviet_building/plans/plan_floor2.png), [3](soviet_building/plans/plan_floor3.png), [4](soviet_building/plans/plan_floor4.png). Ведомость помещений: [`rooms.csv`](soviet_building/plans/rooms.csv).

Файлы:
- [`soviet_building/game`](soviet_building/game): проект Godot
- [`SovietSanatorium.glb`](soviet_building/export/SovietSanatorium.glb): здание целиком с интерьером, текстуры внутри файла
- [`SovietSanatorium_Interior.glb`](soviet_building/export/SovietSanatorium_Interior.glb): только интерьер
- [`SovietSanatorium.blend`](soviet_building/export/blend/SovietSanatorium.blend), [`SovietSanatorium.fbx`](soviet_building/export/fbx/SovietSanatorium.fbx)

Подробное описание модели (планировка, оснащение, двери, свет, материалы, свойства объектов, пересборка) — в [`soviet_building/INTERIOR.md`](soviet_building/INTERIOR.md).
