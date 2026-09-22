# Конфиги Custom FFF (Cura 5.10)

Снимок рабочих файлов принтера. Копировать в Cura **только** эти пары, и только при открытой/закрытой Cura осознанно: если Cura запущена, она может перезаписать файлы при выходе.

## Куда класть (Windows)

Живой профиль: `%APPDATA%\cura\5.10\`

В AppData символ `#` в имени экструдера кодируется как `%23`.

| Файл в этой папке | Живой путь |
|---|---|
| `definition_changes/Custom+FFF+printer_settings.inst.cfg` | `definition_changes/Custom+FFF+printer_settings.inst.cfg` |
| `definition_changes/custom_extruder_1+#2_settings.inst.cfg` | `definition_changes/custom_extruder_1+%232_settings.inst.cfg` |
| `user/Custom+FFF+printer_user.inst.cfg` | `user/Custom+FFF+printer_user.inst.cfg` |
| `user/custom_extruder_1+#2_user.inst.cfg` | `user/custom_extruder_1+%232_user.inst.cfg` |
| `machine_instances/Custom+FFF+printer.global.cfg` | `machine_instances/Custom+FFF+printer.global.cfg` |
| `extruders/custom_extruder_1+#2.extruder.cfg` | `extruders/custom_extruder_1+%232.extruder.cfg` |

## Что в каком файле

- **printer_settings** — размер стола 360, start/end G-code (`G28`, `G29`, линии очистки). Это самое ценное. Не затирать.
- **extruder settings** — диаметр 1.75, сопло 0.6.
- **user** — текущие пользовательскиеoverrides печати (скорости, brim, infill и т.д.). Это стартовая точка, не закон для каждой новой детали.
- **machine instance** — стек контейнеров. `quality_changes` должен быть `empty_quality_changes`. Не линковать кастомный профиль качества в instance — Cura уже один раз из‑за этого пересоздала машину и стёрла start/end G-code.

Экструдеры 2–8 в Cura есть, но не используются. Их не копировали.
