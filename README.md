# EdgeTools

[🇷🇺 Русский](#русский) | [🇬🇧 English](#english) | [🇰🇿 Қазақша](#қазақша)

---

## Русский

Десктопная утилита для Windows в стиле Samsung Edge Panel — набор инструментов для повседневных задач.

![Python](https://img.shields.io/badge/Python-3.11-blue)
![PySide6](https://img.shields.io/badge/PySide6-Qt6-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

### 📋 Описание

EdgeTools — это модульная программная оболочка, которая предоставляет быстрый доступ к различным утилитам через выдвижную панель с правого края экрана.

**Основные модули:**

- **Edge Panel** — главная панель с кнопками запуска утилит
- **Media Player** — MPV плеер + встроенный браузер (WebView2) для YouTube
- **Image Enhancer** — AI-улучшение фотографий (landmark-based pipeline)
- **File Sorter** — автоматическая сортировка файлов по правилам
- **OCR** — распознавание текста с экрана (Tesseract)
- **Todo** — менеджер задач с напоминаниями

---

### 🚀 Установка

#### 1. Требования

- **OS**: Windows 10/11
- **Python**: 3.11
- **GPU**: NVIDIA с CUDA (рекомендуется для Image Enhancer)
- **RAM**: минимум 8GB, рекомендуется 16GB

#### 2. Клонирование репозитория

```bash
git clone https://github.com/yourusername/EdgeTools.git
cd EdgeTools
```

#### 3. Установка зависимостей

```bash
pip install -r requirements.txt
```

**Основные библиотеки:**

**UI и система:**
- `PySide6` — Qt6 интерфейс
- `pywebview` — WebView2 браузер
- `pywin32` — WinAPI интеграция

**Медиа:**
- `python-mpv` — MPV плеер
- `yt-dlp` — загрузка YouTube видео

**ML и обработка изображений:**
- `torch==2.1.1` — PyTorch
- `torchvision==0.16.1` — Computer Vision
- `opencv-python` — OpenCV
- `Pillow` — PIL
- `scikit-image` — обработка изображений
- `mediapipe` — FaceMesh landmarks
- `onnxruntime` — ArcFace identity preservation
- `basicsr` — базовые модели super-resolution
- `facexlib` — детекция и обработка лиц
- `realesrgan` — Real-ESRGAN модели

**OCR:**
- `pytesseract` — Python обёртка для Tesseract
- Tesseract OCR: https://github.com/UB-Mannheim/tesseract/wiki

#### 4. Скачивание моделей для Image Enhancer

Создайте папку `bin/` в корне проекта и скачайте следующие модели:

| Модель | Размер | Ссылка |
|--------|--------|--------|
| RetinaFace (детекция лиц) | 105 MB | [detection_Resnet50_Final.pth](https://github.com/xinntao/facexlib/releases/download/v0.1.0/detection_Resnet50_Final.pth) |
| CodeFormer (восстановление лиц) | 360 MB | [codeformer.pth](https://github.com/sczhou/CodeFormer/releases/download/v0.1.0/codeformer.pth) |
| ParseNet (сегментация лица) | 82 MB | [parsing_parsenet.pth](https://github.com/xinntao/facexlib/releases/download/v0.2.2/parsing_parsenet.pth) |
| SwinIR x4 (апскейл) | 136 MB | [003_realSR_BSRGAN_DFOWMFC_s64w8_SwinIR-L_x4_GAN.pth](https://github.com/JingyunLiang/SwinIR/releases/download/v0.0/003_realSR_BSRGAN_DFOWMFC_s64w8_SwinIR-L_x4_GAN.pth) |
| SwinIR x2 (резервный) | 65 MB | [001_classicalSR_DF2K_s64w8_SwinIR-M_x2.pth](https://github.com/JingyunLiang/SwinIR/releases/download/v0.0/001_classicalSR_DF2K_s64w8_SwinIR-M_x2.pth) |
| ArcFace (identity) | 167 MB | [w600k_r50.onnx](https://github.com/onnx/models/raw/main/vision/body_analysis/arcface/model/arcface_r100_v1.onnx) (переименуйте) |

**Структура папки `bin/`:**
```
bin/
├── detection_Resnet50_Final.pth
├── codeformer.pth
├── parsing_parsenet.pth
├── 003_realSR_BSRGAN_DFOWMFC_s64w8_SwinIR-L_x4_GAN.pth
├── 001_classicalSR_DF2K_s64w8_SwinIR-M_x2.pth
└── w600k_r50.onnx
```

#### 5. YouTube cookies (опционально)

Для работы с YouTube создайте файл `cookies.txt` в корне проекта (экспортируйте из браузера).

#### 6. Запуск

```bash
python main.py
```

---

### 🏗️ Архитектура проекта

**Паттерн:** MVC (Model-View-Controller)

```
EdgeTools/
├── main.py                          # Точка входа
├── app/
│   ├── controllers/                 # Бизнес-логика
│   ├── features/                    # Модули
│   │   ├── edge_panel/
│   │   ├── player/
│   │   ├── image_enhancer/
│   │   ├── file_sorter/
│   │   ├── ocr/
│   │   ├── todo/
│   │   └── settings/
│   ├── core/                        # Общие утилиты
│   └── data/                        # Данные приложения
├── bin/                             # ML модели (не в git)
└── cookies.txt                      # YouTube cookies (не в git)
```

---

### 🎨 Модули

#### 1. Edge Panel
Главная панель, выезжает с правого края экрана при наведении мыши.

#### 2. Media Player
MPV плеер + встроенный WebView2 браузер для YouTube.

**Возможности:**
- Воспроизведение локальных файлов и YouTube
- Переключение между MPV плеером и браузером
- Управление через UI: play/pause, громкость, прогресс-бар
- Выбор качества видео (авто, 1080p, 720p, 480p, 360p)
- Drag & Drop файлов

#### 3. Image Enhancer
AI-улучшение фотографий с landmark-based pipeline.

**Pipeline обработки:**
1. Анализ качества изображения
2. Грубая сегментация (DeepLabV3 + RetinaFace)
3. SwinIR x4 апскейл
4. Точная сегментация
5. Landmark Analysis (MediaPipe 468 точек)
6. Зональная обработка (CodeFormer + landmark-based)
7. Постобработка + Frequency Separation

**Ключевые фичи:**
- Landmark-based зональная обработка (каждая часть лица отдельно)
- Identity preservation через ArcFace (threshold 0.85)
- Гибридная выгрузка моделей (GPU→CPU→unload)
- Использование памяти: старт ~50MB, полная загрузка ~1120MB

#### 4. File Sorter
Автоматическая сортировка файлов по правилам (расширения, ключевые слова).

#### 5. OCR
Распознавание текста с экрана через Tesseract (русский/английский).

#### 6. Todo
Менеджер задач с напоминаниями, приоритетами и автокатегориями.

---

### 📊 Статистика проекта

- **47 Python файлов**
- **~7,559 строк кода**
- image_enhancer: 48% | player: 18% | file_sorter: 9% | todo: 8%

---

### 📄 Лицензия

MIT License

---

## English

Desktop utility for Windows in Samsung Edge Panel style — a set of tools for everyday tasks.

### 📋 Description

EdgeTools is a modular software shell that provides quick access to various utilities through a sliding panel from the right edge of the screen.

**Main modules:**

- **Edge Panel** — main panel with utility launch buttons
- **Media Player** — MPV player + built-in browser (WebView2) for YouTube
- **Image Enhancer** — AI photo enhancement (landmark-based pipeline)
- **File Sorter** — automatic file sorting by rules
- **OCR** — screen text recognition (Tesseract)
- **Todo** — task manager with reminders

---

### 🚀 Installation

#### 1. Requirements

- **OS**: Windows 10/11
- **Python**: 3.11
- **GPU**: NVIDIA with CUDA (recommended for Image Enhancer)
- **RAM**: minimum 8GB, recommended 16GB

#### 2. Clone repository

```bash
git clone https://github.com/yourusername/EdgeTools.git
cd EdgeTools
```

#### 3. Install dependencies

```bash
pip install -r requirements.txt
```

**Main libraries:**

**UI and system:**
- `PySide6` — Qt6 interface
- `pywebview` — WebView2 browser
- `pywin32` — WinAPI integration

**Media:**
- `python-mpv` — MPV player
- `yt-dlp` — YouTube video download

**ML and image processing:**
- `torch==2.1.1` — PyTorch
- `torchvision==0.16.1` — Computer Vision
- `opencv-python` — OpenCV
- `Pillow` — PIL
- `scikit-image` — image processing
- `mediapipe` — FaceMesh landmarks
- `onnxruntime` — ArcFace identity preservation
- `basicsr` — basic super-resolution models
- `facexlib` — face detection and processing
- `realesrgan` — Real-ESRGAN models

**OCR:**
- `pytesseract` — Python wrapper for Tesseract
- Tesseract OCR: https://github.com/UB-Mannheim/tesseract/wiki

#### 4. Download models for Image Enhancer

Create `bin/` folder in project root and download the following models:

| Model | Size | Link |
|-------|------|------|
| RetinaFace (face detection) | 105 MB | [detection_Resnet50_Final.pth](https://github.com/xinntao/facexlib/releases/download/v0.1.0/detection_Resnet50_Final.pth) |
| CodeFormer (face restoration) | 360 MB | [codeformer.pth](https://github.com/sczhou/CodeFormer/releases/download/v0.1.0/codeformer.pth) |
| ParseNet (face segmentation) | 82 MB | [parsing_parsenet.pth](https://github.com/xinntao/facexlib/releases/download/v0.2.2/parsing_parsenet.pth) |
| SwinIR x4 (upscale) | 136 MB | [003_realSR_BSRGAN_DFOWMFC_s64w8_SwinIR-L_x4_GAN.pth](https://github.com/JingyunLiang/SwinIR/releases/download/v0.0/003_realSR_BSRGAN_DFOWMFC_s64w8_SwinIR-L_x4_GAN.pth) |
| SwinIR x2 (backup) | 65 MB | [001_classicalSR_DF2K_s64w8_SwinIR-M_x2.pth](https://github.com/JingyunLiang/SwinIR/releases/download/v0.0/001_classicalSR_DF2K_s64w8_SwinIR-M_x2.pth) |
| ArcFace (identity) | 167 MB | [w600k_r50.onnx](https://github.com/onnx/models/raw/main/vision/body_analysis/arcface/model/arcface_r100_v1.onnx) (rename) |

**`bin/` folder structure:**
```
bin/
├── detection_Resnet50_Final.pth
├── codeformer.pth
├── parsing_parsenet.pth
├── 003_realSR_BSRGAN_DFOWMFC_s64w8_SwinIR-L_x4_GAN.pth
├── 001_classicalSR_DF2K_s64w8_SwinIR-M_x2.pth
└── w600k_r50.onnx
```

#### 5. YouTube cookies (optional)

For YouTube support, create `cookies.txt` file in project root (export from browser).

#### 6. Run

```bash
python main.py
```

---

### 🏗️ Project Architecture

**Pattern:** MVC (Model-View-Controller)

```
EdgeTools/
├── main.py                          # Entry point
├── app/
│   ├── controllers/                 # Business logic
│   ├── features/                    # Modules
│   │   ├── edge_panel/
│   │   ├── player/
│   │   ├── image_enhancer/
│   │   ├── file_sorter/
│   │   ├── ocr/
│   │   ├── todo/
│   │   └── settings/
│   ├── core/                        # Common utilities
│   └── data/                        # Application data
├── bin/                             # ML models (not in git)
└── cookies.txt                      # YouTube cookies (not in git)
```

---

### 🎨 Modules

#### 1. Edge Panel
Main panel that slides out from the right edge of the screen on mouse hover.

#### 2. Media Player
MPV player + built-in WebView2 browser for YouTube.

**Features:**
- Play local files and YouTube videos
- Switch between MPV player and browser mode
- UI controls: play/pause, volume, progress bar
- Quality selection (auto, 1080p, 720p, 480p, 360p)
- Drag & Drop files

#### 3. Image Enhancer
AI photo enhancement with landmark-based pipeline.

**Processing pipeline:**
1. Image quality analysis
2. Coarse segmentation (DeepLabV3 + RetinaFace)
3. SwinIR x4 upscale
4. Fine segmentation
5. Landmark Analysis (MediaPipe 468 points)
6. Zone processing (CodeFormer + landmark-based)
7. Post-processing + Frequency Separation

**Key features:**
- Landmark-based zone processing (each face part separately)
- Identity preservation via ArcFace (threshold 0.85)
- Hybrid model unloading (GPU→CPU→unload)
- Memory usage: start ~50MB, full load ~1120MB

#### 4. File Sorter
Automatic file sorting by rules (extensions, keywords).

#### 5. OCR
Screen text recognition via Tesseract (Russian/English).

#### 6. Todo
Task manager with reminders, priorities, and auto-categories.

---

### 📊 Project Statistics

- **47 Python files**
- **~7,559 lines of code**
- image_enhancer: 48% | player: 18% | file_sorter: 9% | todo: 8%

---

### 📄 License

MIT License

---

## Қазақша

Windows үшін Samsung Edge Panel стилінде жасалған десктоптық утилита — күнделікті тапсырмалар үшін құралдар жинағы.

### 📋 Сипаттама

EdgeTools — бұл экранның оң жағынан шығатын панель арқылы әртүрлі утилиталарға жылдам қол жеткізуді қамтамасыз ететін модульдік бағдарламалық қабық.

**Негізгі модульдер:**

- **Edge Panel** — утилиталарды іске қосу батырмалары бар негізгі панель
- **Media Player** — MPV плеер + YouTube үшін кіріктірілген браузер (WebView2)
- **Image Enhancer** — AI арқылы фотосуреттерді жақсарту (landmark-based pipeline)
- **File Sorter** — ережелер бойынша файлдарды автоматты сұрыптау
- **OCR** — экраннан мәтінді тану (Tesseract)
- **Todo** — еске салғыштары бар тапсырмалар менеджері

---

### 🚀 Орнату

#### 1. Талаптар

- **OS**: Windows 10/11
- **Python**: 3.11
- **GPU**: CUDA бар NVIDIA (Image Enhancer үшін ұсынылады)
- **RAM**: минимум 8GB, ұсынылады 16GB

#### 2. Репозиторийді клондау

```bash
git clone https://github.com/yourusername/EdgeTools.git
cd EdgeTools
```

#### 3. Тәуелділіктерді орнату

```bash
pip install -r requirements.txt
```

**Негізгі кітапханалар:**

**UI және жүйе:**
- `PySide6` — Qt6 интерфейсі
- `pywebview` — WebView2 браузері
- `pywin32` — WinAPI интеграциясы

**Медиа:**
- `python-mpv` — MPV плеер
- `yt-dlp` — YouTube бейне жүктеу

**ML және кескінді өңдеу:**
- `torch==2.1.1` — PyTorch
- `torchvision==0.16.1` — Computer Vision
- `opencv-python` — OpenCV
- `Pillow` — PIL
- `scikit-image` — кескінді өңдеу
- `mediapipe` — FaceMesh landmarks
- `onnxruntime` — ArcFace identity preservation
- `basicsr` — негізгі super-resolution модельдері
- `facexlib` — бетті анықтау және өңдеу
- `realesrgan` — Real-ESRGAN модельдері

**OCR:**
- `pytesseract` — Tesseract үшін Python орамы
- Tesseract OCR: https://github.com/UB-Mannheim/tesseract/wiki

#### 4. Image Enhancer үшін модельдерді жүктеу

Жоба түбірінде `bin/` қалтасын жасаңыз және келесі модельдерді жүктеңіз:

| Модель | Өлшемі | Сілтеме |
|--------|--------|---------|
| RetinaFace (бетті анықтау) | 105 MB | [detection_Resnet50_Final.pth](https://github.com/xinntao/facexlib/releases/download/v0.1.0/detection_Resnet50_Final.pth) |
| CodeFormer (бетті қалпына келтіру) | 360 MB | [codeformer.pth](https://github.com/sczhou/CodeFormer/releases/download/v0.1.0/codeformer.pth) |
| ParseNet (бет сегментациясы) | 82 MB | [parsing_parsenet.pth](https://github.com/xinntao/facexlib/releases/download/v0.2.2/parsing_parsenet.pth) |
| SwinIR x4 (апскейл) | 136 MB | [003_realSR_BSRGAN_DFOWMFC_s64w8_SwinIR-L_x4_GAN.pth](https://github.com/JingyunLiang/SwinIR/releases/download/v0.0/003_realSR_BSRGAN_DFOWMFC_s64w8_SwinIR-L_x4_GAN.pth) |
| SwinIR x2 (резервтік) | 65 MB | [001_classicalSR_DF2K_s64w8_SwinIR-M_x2.pth](https://github.com/JingyunLiang/SwinIR/releases/download/v0.0/001_classicalSR_DF2K_s64w8_SwinIR-M_x2.pth) |
| ArcFace (identity) | 167 MB | [w600k_r50.onnx](https://github.com/onnx/models/raw/main/vision/body_analysis/arcface/model/arcface_r100_v1.onnx) (атын өзгерту) |

**`bin/` қалтасының құрылымы:**
```
bin/
├── detection_Resnet50_Final.pth
├── codeformer.pth
├── parsing_parsenet.pth
├── 003_realSR_BSRGAN_DFOWMFC_s64w8_SwinIR-L_x4_GAN.pth
├── 001_classicalSR_DF2K_s64w8_SwinIR-M_x2.pth
└── w600k_r50.onnx
```

#### 5. YouTube cookies (қосымша)

YouTube қолдауы үшін жоба түбірінде `cookies.txt` файлын жасаңыз (браузерден экспорттаңыз).

#### 6. Іске қосу

```bash
python main.py
```

---

### 🏗️ Жоба архитектурасы

**Үлгі:** MVC (Model-View-Controller)

```
EdgeTools/
├── main.py                          # Кіру нүктесі
├── app/
│   ├── controllers/                 # Бизнес логикасы
│   ├── features/                    # Модульдер
│   │   ├── edge_panel/
│   │   ├── player/
│   │   ├── image_enhancer/
│   │   ├── file_sorter/
│   │   ├── ocr/
│   │   ├── todo/
│   │   └── settings/
│   ├── core/                        # Жалпы утилиталар
│   └── data/                        # Қолданба деректері
├── bin/                             # ML модельдері (git-те жоқ)
└── cookies.txt                      # YouTube cookies (git-те жоқ)
```

---

### 🎨 Модульдер

#### 1. Edge Panel
Тінтуірді жақындатқанда экранның оң жағынан шығатын негізгі панель.

#### 2. Media Player
MPV плеер + YouTube үшін кіріктірілген WebView2 браузері.

**Мүмкіндіктер:**
- Жергілікті файлдар мен YouTube бейнелерін ойнату
- MPV плеер мен браузер режимі арасында ауысу
- UI басқару: play/pause, дыбыс, прогресс-бар
- Сапа таңдау (авто, 1080p, 720p, 480p, 360p)
- Drag & Drop файлдар

#### 3. Image Enhancer
Landmark-based pipeline бар AI фотосуреттерді жақсарту.

**Өңдеу конвейері:**
1. Кескін сапасын талдау
2. Дөрекі сегментация (DeepLabV3 + RetinaFace)
3. SwinIR x4 апскейл
4. Нақты сегментация
5. Landmark Analysis (MediaPipe 468 нүкте)
6. Аймақтық өңдеу (CodeFormer + landmark-based)
7. Постөңдеу + Frequency Separation

**Негізгі мүмкіндіктер:**
- Landmark-based аймақтық өңдеу (беттің әр бөлігі бөлек)
- ArcFace арқылы identity preservation (threshold 0.85)
- Гибридті модельдерді түсіру (GPU→CPU→unload)
- Жад пайдалану: бастау ~50MB, толық жүктеу ~1120MB

#### 4. File Sorter
Ережелер бойынша файлдарды автоматты сұрыптау (кеңейтімдер, кілт сөздер).

#### 5. OCR
Tesseract арқылы экраннан мәтінді тану (орыс/ағылшын).

#### 6. Todo
Еске салғыштары, басымдықтары және авто-санаттары бар тапсырмалар менеджері.

---

### 📊 Жоба статистикасы

- **47 Python файлдары**
- **~7,559 код жолдары**
- image_enhancer: 48% | player: 18% | file_sorter: 9% | todo: 8%

---

### 📄 Лицензия

MIT License

---

### 🙏 Алғыс

- [CodeFormer](https://github.com/sczhou/CodeFormer) — face restoration
- [SwinIR](https://github.com/JingyunLiang/SwinIR) — image super-resolution
- [RetinaFace](https://github.com/biubug6/Pytorch_Retinaface) — face detection
- [MediaPipe](https://github.com/google/mediapipe) — face landmarks
- [MPV](https://mpv.io/) — media player
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) — YouTube downloader
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) — text recognition
