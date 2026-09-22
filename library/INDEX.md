# Индекс сценариев

После [AGENTS.md](../AGENTS.md) и [HARDWARE.md](../printer_configs/HARDWARE.md) открой **одну** карточку. Не читай всю папку. Интернет — только если строки нет.

Сопло и материал сейчас — в HARDWARE, не в этой таблице.

Статус: **ориентир** — база из практики, на Tornado не гоняли. **★** — проверяли на этом принтере. **★ частично** — часть цифр с этого стола, не весь сценарий.

## Материал

| Когда | Файл | Статус |
|---|---|---|
| PLA / PLA+, температуры, обдув, стартовые скорости | [materials/pla.md](materials/pla.md) | ★ температуры с профиля; остальное ориентир |
| PETG, не копировать PLA | [materials/petg.md](materials/petg.md) | ориентир, на Tornado не гоняли |

## Тип детали

| Когда | Файл | Статус |
|---|---|---|
| Первый слой, стол, brim/skirt, слон | [scenarios/first_layer.md](scenarios/first_layer.md) | ориентир + старт G28/G29 ★ |
| Мелкая крышка с рисунком (лотос ~33 мм) | [scenarios/small_relief.md](scenarios/small_relief.md) | ★ эталон: `logo/logo_n06_gyroid50.gcode` |
| Большая видимая корка, пластик не жечь | [scenarios/large_shell.md](scenarios/large_shell.md) | ★ частично |
| Силовая деталь: кронштейн, шестерня | [scenarios/functional.md](scenarios/functional.md) | ориентир |
| Свесы, мосты, внешние поддержки | [scenarios/overhangs.md](scenarios/overhangs.md) | ориентир |
| Отверстия, посадка, размер | [scenarios/holes.md](scenarios/holes.md) | ориентир |
| Тонкие стенки, ваза | [scenarios/thin_walls.md](scenarios/thin_walls.md) | ориентир |

## Дефект

| Симптом | Файл | Статус |
|---|---|---|
| Дырки / яма в центре крыши | [defects/roof_sag.md](defects/roof_sag.md) | ★ |
| Рельеф заплыл, «оплавленная» деталь | [defects/flooded_contour.md](defects/flooded_contour.md) | ★ |
| Экструдер визжит, пруток стёрт | [defects/bowden_grind.md](defects/bowden_grind.md) | ★ |

## Пресет захода

Не карточка сценария. Конкретные числа, утверждение на странице настройщика и итог печати.

| Когда | Файл | Статус |
|---|---|---|
| Эталон лотоса, gyroid 50%, сопло 0.6 | [presets/logo_n06_gyroid50.json](presets/logo_n06_gyroid50.json) | ★ напечатан |

## Железо в настройщике

Принтер, филамент и сопло — отдельные карточки. Заход на деталь только ссылается на них. В шапке настройщика «Из Cura» берёт машину, катушку или диаметр сопла из установленной Cura 5.10. У чужого филамента копируются температуры и обдув; ретракт этой машины не берётся.

| Когда | Файл |
|---|---|
| Tornado 2 Pro, стол 360, G28+G29 | [machines/tornado2pro.json](machines/tornado2pro.json) |
| VolgoBot FFF1.4, стол 200, прямой, только G28 | [machines/volgobot_fff14.json](machines/volgobot_fff14.json) |
| eSUN PLA+ gray, проверенный ретракт | [filaments/esun_pla_plus_gray.json](filaments/esun_pla_plus_gray.json) |
| PLA 205–235, точка 215/220, без ретракта | [filaments/pla_205_235.json](filaments/pla_205_235.json) |
| PETG, на этом столе не печатали | [filaments/petg_orientir.json](filaments/petg_orientir.json) |
| Сопло 0.6 и запасное 0.4 | [nozzles/](nozzles/) |

Как устроена полка «Ориентир / У нас»: [README.md](README.md).
