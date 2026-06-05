<div align="center">

# EdgeTools

**Модульная десктопная оболочка для Windows в стиле Samsung Edge Panel**

![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python&logoColor=white)
![PySide6](https://img.shields.io/badge/PySide6-Qt6-41CD52?style=flat-square&logo=qt&logoColor=white)
![Windows](https://img.shields.io/badge/Windows-10%2F11-0078D4?style=flat-square&logo=windows&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-F9A825?style=flat-square)

**Дипломный проект · КВПТК · 2026**  
**Автор: Сидорин Артём (Sidorin Artem)**

[🇷🇺 Русский](#русский) · [🇬🇧 English](#english) · [🇰🇿 Қазақша](#қазақша)

</div>

---

## Русский

### О проекте

**EdgeTools** — программная оболочка для повседневных задач на Windows. Выдвижная **Edge Panel** с правого края экрана даёт быстрый доступ к плееру, улучшению фото, сортировке файлов, OCR и контекстным заметкам.

Проект разработан **Сидориным Артёмом** в **2026 году** как **дипломная работа** в **КВПТК**.

| Модуль | Назначение |
|--------|------------|
| **Edge Panel** | Лаунчер модулей, настройки, выход |
| **Media Player** | MPV + WebView2, YouTube через yt-dlp, история |
| **Image Enhancer** | AI-улучшение лиц: SwinIR, CodeFormer, MediaPipe, ArcFace |
| **AutoSort** | Сортировка файлов по правилам + автосортировка из папки-входящих |
| **OCR** | Захват области экрана, Tesseract, автозагрузка языков |
| **Smart Notes** | Стикеры по контексту приложения, задачи, напоминания |
| **Settings** | Единые настройки всех модулей, привязка Google/YouTube |

**Стек:** Python 3.11 · PySide6 · SQLite · PyTorch · MPV · WebView2 · Tesseract

---

### Быстрый старт

```bash
git clone https://github.com/Sidrr1/Diplom.git
cd Diplom
pip install -r requirements.txt
pip install -r requirements-ml.txt --index-url https://download.pytorch.org/whl/cu121
```

Скачайте модели в `bin/` (см. ниже), установите Tesseract, положите `libmpv-2.dll` в `bin/`, затем:

```bash
python main.py
```

Без консоли (фоновый запуск): двойной клик по `run.vbs`.

---

### Требования

| Компонент | Минимум | Рекомендуется |
|-----------|---------|---------------|
| ОС | Windows 10 | Windows 11 |
| Python | 3.11 | 3.11.5 |
| RAM | 8 GB | 16 GB |
| GPU | — | NVIDIA + CUDA 12.1 (Image Enhancer) |
| Диск | ~2 GB свободно | SSD (модели ~1 GB) |

---

### Установка Python-зависимостей

**1. Базовые пакеты**

```bash
pip install -r requirements.txt
```

**2. PyTorch (Image Enhancer)**

С NVIDIA GPU (CUDA 12.1):

```bash
pip install -r requirements-ml.txt --index-url https://download.pytorch.org/whl/cu121
```

Только CPU:

```bash
pip install -r requirements-ml.txt
```

**Проверенное окружение (июнь 2026):**

| Пакет | Версия |
|-------|--------|
| Python | 3.11.5 |
| PySide6 | 6.10.2 |
| torch / torchvision | 2.5.1 / 0.20.1 |
| yt-dlp | 2026.3.17 |
| mediapipe | 0.10.33 |
| opencv-python | 4.6.0.66 |

Полный список библиотек: [`EdgeTools/libs/Dependencies.md`](EdgeTools/libs/Dependencies.md)

---

### Внешние компоненты (обязательно / рекомендуется)

#### Tesseract OCR

1. Установите [Tesseract для Windows](https://github.com/UB-Mannheim/tesseract/wiki) (путь по умолчанию: `C:\Program Files\Tesseract-OCR\`).
2. Языки **rus** и **eng** копируются в EdgeTools автоматически.
3. Остальные языки (kaz, deu, …) скачиваются из настроек **🔍 OCR** в `%AppData%\EdgeTools\tessdata`.

#### MPV (плеер)

| Файл | Назначение | Где взять |
|------|------------|-----------|
| `libmpv-2.dll` | Движок воспроизведения (локальные файлы, YouTube через yt-dlp) | [mpv-winbuild-cmake](https://github.com/shinchiro/mpv-winbuild-cmake/releases) → положить в `bin/` |

#### WebView2 Runtime

Нужен для входа Google/YouTube и встроенного браузера. Обычно уже установлен в Windows 11; иначе — [Microsoft Edge WebView2](https://developer.microsoft.com/microsoft-edge/webview2/).

#### YouTube cookies (опционально)

**Настройки → ▶ Плеер → YouTube → «Файл…»** — укажите экспорт cookies (расширение *Get cookies.txt LOCALLY*). Нужно, если ролики через yt-dlp не открываются без входа. Альтернатива — встроенный браузер WebView2.

Legacy: `cookies.txt` в корне проекта тоже подхватывается, если путь в настройках пуст.

---

### Модели Image Enhancer (`bin/`)

Создайте папку `bin/` в корне проекта. Файлы **не в git** (~1 GB суммарно).

| Файл | ~Размер | Ссылка |
|------|---------|--------|
| `detection_Resnet50_Final.pth` | 105 MB | [facexlib RetinaFace](https://github.com/xinntao/facexlib/releases/download/v0.1.0/detection_Resnet50_Final.pth) |
| `codeformer.pth` | 360 MB | [CodeFormer](https://github.com/sczhou/CodeFormer/releases/download/v0.1.0/codeformer.pth) |
| `parsing_parsenet.pth` | 82 MB | [ParseNet](https://github.com/sczhou/CodeFormer/releases/download/v0.1.0/parsing_parsenet.pth) |
| `003_realSR_BSRGAN_DFOWMFC_s64w8_SwinIR-L_x4_GAN.pth` | 136 MB | [SwinIR x4](https://github.com/JingyunLiang/SwinIR/releases/download/v0.0/003_realSR_BSRGAN_DFOWMFC_s64w8_SwinIR-L_x4_GAN.pth) |
| `001_classicalSR_DF2K_s64w8_SwinIR-M_x2.pth` | 65 MB | [SwinIR x2](https://github.com/JingyunLiang/SwinIR/releases/download/v0.0/001_classicalSR_DF2K_s64w8_SwinIR-M_x2.pth) |
| `w600k_r50.onnx` | 167 MB | [ArcFace w600k](https://github.com/deepinsight/insightface/releases/download/v0.7/w600k_r50.onnx) |

```
bin/
├── libmpv-2.dll
├── detection_Resnet50_Final.pth
├── codeformer.pth
├── parsing_parsenet.pth
├── 003_realSR_BSRGAN_DFOWMFC_s64w8_SwinIR-L_x4_GAN.pth
├── 001_classicalSR_DF2K_s64w8_SwinIR-M_x2.pth
└── w600k_r50.onnx
```

При первом запуске Enhancer приложение покажет список недостающих файлов, если что-то не скачано.

---

### Модули (подробно)

#### Edge Panel
Выдвижная панель при наведении на правый край. Кнопки модулей, индикатор загрузки, настройки, выход.

#### Media Player
- Локальные файлы через **MPV** (`libmpv-2.dll` в `bin/`)
- **YouTube**: yt-dlp, выбор качества, история; cookies — в настройках плеера
- **WebView2**: отдельный процесс, вход через Google-аккаунт
- Перемотка с учётом split/muxed потоков; корректные слайдеры громкости и позиции

#### Image Enhancer
**Natural pipeline:** SwinIR (адаптивно ×2 на крупных кадрах / ×4 на мелких) → CodeFormer с высокой fidelity → мягкая зональная обработка → blend с чистым апскейлом (меньше «пластика»). Дедуп лиц RetinaFace, экономия VRAM на сегментации. Слайдеры **Похожесть** / **Сила**, палитра оттенков кожи для раскраски. **Настройки → Image Enhancer:** папка сохранения, формат, «быстрое сохранение» (кнопка «В папку»).

#### AutoSort (File Sorter)
Правила по расширениям и ключевым словам. Папка-входящие, автосортировка пока запущен EdgeTools, история с поиском.

#### OCR
Выделение области на экране → Tesseract. Автовыбор PSM, постобработка кириллицы, карусель языков в настройках, автозагрузка `.traineddata`.

#### Smart Notes
Контекстные стикеры (привязка к активному окну). Режимы: обычные заметки / список задач. Напоминания: ежедневный дайджест и оповещения перед дедлайном.

#### Settings
Вкладки: общие, плеер (качество, cookies YouTube, аккаунты), сортировщик, OCR, заметки, Image Enhancer (сохранение). Конфиг и профили: `%AppData%\EdgeTools\`.

#### Брендинг
Иконки приложения: `assets/Иконка 1.png` (основная), `assets/Иконка 2.png` (альтернатива).

---

### Архитектура

**Паттерн:** MVC (Model–View–Controller)

```
Diplom/
├── main.py                 # Точка входа
├── run.vbs                 # Запуск без консоли
├── requirements.txt
├── requirements-ml.txt
├── bin/                    # ML-модели, MPV, FFmpeg (не в git)
├── app/
│   ├── controllers/        # player, sorter, ocr, enhancer, todo
│   ├── features/           # edge_panel, player, image_enhancer,
│   │                       # file_sorter, ocr, todo, settings, accounts
│   └── core/               # config, database, paths, migrations
├── EdgeTools/              # Obsidian-документация проекта
└── cookies.txt             # опционально, не коммитить
```

---

### Статистика

- **~87** файлов `.py`
- **~17 200** строк кода
- Данные: SQLite (`app/data/edgetools.db`), настройки в `%AppData%\EdgeTools\`

---

### Лицензия

MIT License · © 2026 Сидорин Артём

---

## English

### About

**EdgeTools** is a modular Windows desktop shell inspired by Samsung Edge Panel. A slide-out **Edge Panel** provides quick access to a media player, AI photo enhancement, file sorting, OCR, and context-aware sticky notes.

Developed by **Artem Sidorin** in **2026** as a **diploma project** at **KVPTK**.

| Module | Purpose |
|--------|---------|
| **Edge Panel** | Module launcher, settings, quit |
| **Media Player** | MPV + WebView2, YouTube via yt-dlp, history |
| **Image Enhancer** | AI face enhancement: SwinIR, CodeFormer, MediaPipe, ArcFace |
| **AutoSort** | Rule-based file sorting + inbox auto-watch |
| **OCR** | Screen region capture, Tesseract, auto language download |
| **Smart Notes** | App-context sticky notes, tasks, reminders |
| **Settings** | Unified module settings, Google/YouTube account binding |

**Stack:** Python 3.11 · PySide6 · SQLite · PyTorch · MPV · WebView2 · Tesseract

---

### Quick start

```bash
git clone https://github.com/Sidrr1/Diplom.git
cd Diplom
pip install -r requirements.txt
pip install -r requirements-ml.txt --index-url https://download.pytorch.org/whl/cu121
```

Download models to `bin/` (see below), install Tesseract, place `libmpv-2.dll` in `bin/`, then:

```bash
python main.py
```

Silent launch: double-click `run.vbs`.

---

### Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| OS | Windows 10 | Windows 11 |
| Python | 3.11 | 3.11.5 |
| RAM | 8 GB | 16 GB |
| GPU | — | NVIDIA + CUDA 12.1 (Image Enhancer) |
| Disk | ~2 GB free | SSD (~1 GB for models) |

---

### Python dependencies

**Base:**

```bash
pip install -r requirements.txt
```

**PyTorch (Image Enhancer)**

With NVIDIA GPU (CUDA 12.1):

```bash
pip install -r requirements-ml.txt --index-url https://download.pytorch.org/whl/cu121
```

CPU only:

```bash
pip install -r requirements-ml.txt
```

**Tested (June 2026):** Python 3.11.5, PySide6 6.10.2, torch 2.5.1, yt-dlp 2026.3.17. Full list: [`EdgeTools/libs/Dependencies.md`](EdgeTools/libs/Dependencies.md)

---

### External components

#### Tesseract OCR

1. Install [Tesseract for Windows](https://github.com/UB-Mannheim/tesseract/wiki).
2. **rus** and **eng** are bootstrapped automatically.
3. Other languages download from **🔍 OCR** settings into `%AppData%\EdgeTools\tessdata`.

#### MPV (player)

| File | Purpose | Source |
|------|---------|--------|
| `libmpv-2.dll` | Playback engine | [mpv-winbuild-cmake releases](https://github.com/shinchiro/mpv-winbuild-cmake/releases) → `bin/` |

#### WebView2 Runtime

Required for Google/YouTube login. [WebView2 Runtime](https://developer.microsoft.com/microsoft-edge/webview2/)

#### YouTube cookies (optional)

**Settings → ▶ Player → YouTube → File…** — export via *Get cookies.txt LOCALLY*. Legacy: `cookies.txt` in project root.

---

### Image Enhancer models (`bin/`)

Create `bin/` in project root (~1 GB total, not in git).

| File | ~Size | Link |
|------|-------|------|
| `detection_Resnet50_Final.pth` | 105 MB | [RetinaFace](https://github.com/xinntao/facexlib/releases/download/v0.1.0/detection_Resnet50_Final.pth) |
| `codeformer.pth` | 360 MB | [CodeFormer](https://github.com/sczhou/CodeFormer/releases/download/v0.1.0/codeformer.pth) |
| `parsing_parsenet.pth` | 82 MB | [ParseNet](https://github.com/sczhou/CodeFormer/releases/download/v0.1.0/parsing_parsenet.pth) |
| `003_realSR_BSRGAN_DFOWMFC_s64w8_SwinIR-L_x4_GAN.pth` | 136 MB | [SwinIR x4](https://github.com/JingyunLiang/SwinIR/releases/download/v0.0/003_realSR_BSRGAN_DFOWMFC_s64w8_SwinIR-L_x4_GAN.pth) |
| `001_classicalSR_DF2K_s64w8_SwinIR-M_x2.pth` | 65 MB | [SwinIR x2](https://github.com/JingyunLiang/SwinIR/releases/download/v0.0/001_classicalSR_DF2K_s64w8_SwinIR-M_x2.pth) |
| `w600k_r50.onnx` | 167 MB | [ArcFace](https://github.com/deepinsight/insightface/releases/download/v0.7/w600k_r50.onnx) |

---

### Modules

- **Edge Panel** — hover launcher from screen edge
- **Media Player** — MPV, YouTube (yt-dlp), WebView2, cookies in settings, watch history
- **Image Enhancer** — natural SwinIR + CodeFormer pipeline, adaptive upscale, save folder in settings
- **AutoSort** — rules, inbox folder, auto-watch while app runs
- **OCR** — screen capture, multi-language Tesseract, auto tessdata download
- **Smart Notes** — per-app context notes, tasks, daily/deadline reminders
- **Settings** — all modules in one dialog; config in `%AppData%\EdgeTools\`

---

### Architecture

MVC pattern — see Russian section for folder tree (same structure).

---

### Statistics

- **~87** Python files
- **~17,200** lines of code
- SQLite + `%AppData%\EdgeTools\` for persistence

---

### License

MIT License · © 2026 Artem Sidorin

---

## Қазақша

### Жоба туралы

**EdgeTools** — Windows үшін Samsung Edge Panel стиліндегі модульдік десктоп қабығы. Экранның оң жағыndan шығатын **Edge Panel** арқылы плеер, фото жақсарту, файл сұрыптау, OCR және контекстік жазбаларға жылдам қол жеткізу.

Жобаны **Сидорин Артём** **2026 жылы** **КВПТК** дипломдық жұмысы ретінде әзірледі.

| Модуль | Мақсаты |
|--------|---------|
| **Edge Panel** | Модульдерді іске қосу, баптаулар |
| **Media Player** | MPV + WebView2, YouTube (yt-dlp) |
| **Image Enhancer** | AI арқылы бетті жақсарту (SwinIR, CodeFormer) |
| **AutoSort** | Ережелер бойынша файл сұрыптау + автокүзету |
| **OCR** | Экраннан мәтін, Tesseract, тілдерді автожүктеу |
| **Smart Notes** | Контекстік стикерлер, тапсырмалар, еске салғыштар |
| **Settings** | Барлық модульдердің баптаулары |

---

### Жылдам бастау

```bash
git clone https://github.com/Sidrr1/Diplom.git
cd Diplom
pip install -r requirements.txt
pip install -r requirements-ml.txt --index-url https://download.pytorch.org/whl/cu121
```

`bin/` қалтасына модельдерді жүктеңіз, Tesseract орнатыңыз, `libmpv-2.dll` қойыңыз:

```bash
python main.py
```

Консольсіз: `run.vbs` екі рет шертіңіз.

---

### Талаптар

| Компонент | Минимум | Ұсынылады |
|-----------|---------|-----------|
| ОС | Windows 10 | Windows 11 |
| Python | 3.11 | 3.11.5 |
| RAM | 8 GB | 16 GB |
| GPU | — | NVIDIA + CUDA 12.1 |
| Диск | ~2 GB | SSD |

---

### Python тәуелділіктері

```bash
pip install -r requirements.txt
pip install -r requirements-ml.txt --index-url https://download.pytorch.org/whl/cu121
```

CPU ғана: `pip install -r requirements-ml.txt`

Толық тізім: [`EdgeTools/libs/Dependencies.md`](EdgeTools/libs/Dependencies.md)

---

### Сыртқы компоненттер

#### Tesseract OCR

[Windows үшін Tesseract](https://github.com/UB-Mannheim/tesseract/wiki) орнатыңыз. **rus** және **eng** автоматты көшіріледі. Басқа тілдер **🔍 OCR** баптауларынан `%AppData%\EdgeTools\tessdata` жүктеледі.

#### MPV

| Файл | Мақсаты | Сілтеме |
|------|---------|---------|
| `libmpv-2.dll` | Ойнату | [mpv-winbuild-cmake](https://github.com/shinchiro/mpv-winbuild-cmake/releases) |

#### WebView2

Google/YouTube кіру үшін: [WebView2 Runtime](https://developer.microsoft.com/microsoft-edge/webview2/)

#### YouTube cookies (қосымша)

Жоба түбірінде `cookies.txt` — браузерден экспорт.

---

### Image Enhancer модельдері (`bin/`)

| Файл | ~Көлемі | Сілтеме |
|------|---------|---------|
| `detection_Resnet50_Final.pth` | 105 MB | [RetinaFace](https://github.com/xinntao/facexlib/releases/download/v0.1.0/detection_Resnet50_Final.pth) |
| `codeformer.pth` | 360 MB | [CodeFormer](https://github.com/sczhou/CodeFormer/releases/download/v0.1.0/codeformer.pth) |
| `parsing_parsenet.pth` | 82 MB | [ParseNet](https://github.com/sczhou/CodeFormer/releases/download/v0.1.0/parsing_parsenet.pth) |
| `003_realSR_BSRGAN_DFOWMFC_s64w8_SwinIR-L_x4_GAN.pth` | 136 MB | [SwinIR x4](https://github.com/JingyunLiang/SwinIR/releases/download/v0.0/003_realSR_BSRGAN_DFOWMFC_s64w8_SwinIR-L_x4_GAN.pth) |
| `001_classicalSR_DF2K_s64w8_SwinIR-M_x2.pth` | 65 MB | [SwinIR x2](https://github.com/JingyunLiang/SwinIR/releases/download/v0.0/001_classicalSR_DF2K_s64w8_SwinIR-M_x2.pth) |
| `w600k_r50.onnx` | 167 MB | [ArcFace](https://github.com/deepinsight/insightface/releases/download/v0.7/w600k_r50.onnx) |

---

### Модульдер

- **Edge Panel** — тінтуірді жақындатқанда панель
- **Media Player** — MPV, YouTube, WebView2, тарих
- **Image Enhancer** — landmark pipeline, бетті қалпына келтіру
- **AutoSort** — ережелер, кіріс қалтасы, автосұрыптау
- **OCR** — экраннан мәтін, тіл каруселі, автожүктеу
- **Smart Notes** — контекстік стикерлер, еске салғыштар (күндізгі дайджест / дедлайн)
- **Settings** — `%AppData%\EdgeTools\` конфигі

---

### Статистика

- **~87** Python файлы
- **~17 200** код жолы

---

### Лицензия

MIT License · © 2026 Сидорин Артём

---

<div align="center">

### Благодарности / Acknowledgments / Алғыс

[CodeFormer](https://github.com/sczhou/CodeFormer) · [SwinIR](https://github.com/JingyunLiang/SwinIR) · [facexlib](https://github.com/xinntao/facexlib) · [InsightFace](https://github.com/deepinsight/insightface) · [MediaPipe](https://github.com/google/mediapipe) · [MPV](https://mpv.io/) · [yt-dlp](https://github.com/yt-dlp/yt-dlp) · [Tesseract](https://github.com/tesseract-ocr/tesseract)

</div>
