"""Сохранение настроек по вкладкам и отслеживание изменений."""
from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from PySide6.QtWidgets import QMessageBox

from app.core import config
from app.core.autostart import set_autostart

if TYPE_CHECKING:
    from app.features.settings.ui.settings_dialog import SettingsDialog

# Ключи config, сохраняемые при нажатии «Сохранить» на каждой вкладке
TAB_CFG_KEYS: dict[str, set[str]] = {
    "general": {"autostart"},
    "player": {
        "player_quality", "player_opacity", "player_history_days",
        "player_cookies_path",
    },
    "sorter": {
        "sorter_source", "sorter_auto_enabled",
        "sorter_opacity", "sorter_history_days",
    },
    "enhancer": {
        "enhancer_autosave", "enhancer_save_path",
        "enhancer_format", "enhancer_jpeg_quality",
    },
    "notes": {
        "notes_edge_position", "notes_width", "notes_height",
        "notes_opacity", "notes_mode",
        "reminder_enabled", "reminder_mode", "reminder_offsets",
    },
}


class SettingsPersistenceMixin:
    """Per-tab snapshot, dirty-state и сохранение текущей вкладки."""

    def _init_persistence(self) -> None:
        self._tab_baselines: dict[str, str] = {}
        self._tab_dirty: set[str] = set()

    def _snapshot_json(self, data: Any) -> str:
        return json.dumps(data, sort_keys=True, ensure_ascii=False, default=str)

    def _mark_tab_dirty(self, tab: str | None = None) -> None:
        tab = tab or self._current_tab
        if not tab:
            return
        self._tab_dirty.add(tab)
        self._update_save_button_state()

    def _clear_tab_dirty(self, tab: str) -> None:
        self._tab_dirty.discard(tab)
        self._update_save_button_state()

    def _update_save_button_state(self) -> None:
        btn = getattr(self, "_save_btn", None)
        if btn is None:
            return
        tab = self._current_tab
        dirty = tab in self._tab_dirty if tab else False
        btn.setEnabled(dirty)
        btn.setStyleSheet(
            self._STYLE_SAVE_ACTIVE if dirty else self._STYLE_SAVE_IDLE
        )

    def _bind_dirty(self, widget, tab: str | None = None) -> None:
        tab = tab or self._current_tab
        if hasattr(widget, "valueChanged"):
            widget.valueChanged.connect(lambda *_: self._mark_tab_dirty(tab))
        if hasattr(widget, "textChanged"):
            widget.textChanged.connect(lambda *_: self._mark_tab_dirty(tab))
        if hasattr(widget, "currentTextChanged"):
            widget.currentTextChanged.connect(lambda *_: self._mark_tab_dirty(tab))
        if hasattr(widget, "toggled"):
            widget.toggled.connect(lambda *_: self._mark_tab_dirty(tab))
        if hasattr(widget, "timeChanged"):
            widget.timeChanged.connect(lambda *_: self._mark_tab_dirty(tab))

    def _collect_tab_state(self, tab: str) -> dict | None:
        """Снять снимок значений виджетов вкладки для сравнения с baseline."""
        if tab not in self._pages_loaded:
            return None
        if tab == "general":
            return {"autostart": self._cb_autostart.isChecked()}
        if tab == "player":
            return {
                "player_quality": self._combo_quality.currentText(),
                "player_opacity": self._slider_player_opacity.value(),
                "player_history_days": self._spin_player_hist_days.value(),
                "player_cookies_path": getattr(self, "_player_cookies_stored", "")
                or self._player_cookies_edit.text().strip(),
            }
        if tab == "sorter":
            return {
                "sorter_source": self._sorter_src_edit.text().strip(),
                "sorter_auto_enabled": self._cb_sorter_auto.isChecked(),
                "sorter_opacity": self._slider_sorter_opacity.value(),
                "sorter_history_days": self._spin_sorter_hist_days.value(),
            }
        if tab == "ocr":
            return {
                "ocr_langs": sorted(self._collect_ocr_langs()),
                "ocr_postprocess": self._cb_ocr_postprocess.isChecked(),
            }
        if tab == "notes":
            pos = next(
                (p for p, b in self._notes_position_btns.items() if b.isChecked()),
                "right",
            )
            mode = "work" if self._mode_work_radio.isChecked() else "normal"
            state = {
                "notes_edge_position": pos,
                "notes_width": self._notes_width_slider.value(),
                "notes_height": self._notes_height_slider.value(),
                "notes_opacity": self._slider_notes_opacity.value(),
                "notes_mode": mode,
            }
            if hasattr(self, "_cb_reminder_enabled"):
                t = self._time_reminder_daily.time()
                state.update({
                    "reminder_enabled": self._cb_reminder_enabled.isChecked(),
                    "reminder_mode": getattr(self, "_reminder_mode", "both"),
                    "reminder_daily": f"{t.hour():02d}:{t.minute():02d}",
                    "reminder_offsets": sorted(self._collect_reminder_offsets()),
                })
            return state
        if tab == "enhancer":
            return {
                "enhancer_autosave": self._cb_enhancer_autosave.isChecked(),
                "enhancer_save_path": self._enhancer_path_edit.text().strip(),
                "enhancer_format": self._combo_enhancer_format.currentText(),
                "enhancer_jpeg_quality": self._slider_enhancer_quality.value(),
            }
        return None

    def _set_tab_baseline(self, tab: str) -> None:
        state = self._collect_tab_state(tab)
        if state is not None:
            self._tab_baselines[tab] = self._snapshot_json(state)
        self._tab_dirty.discard(tab)

    def _is_tab_dirty(self, tab: str) -> bool:
        if tab in self._tab_dirty:
            return True
        state = self._collect_tab_state(tab)
        if state is None:
            return False
        base = self._tab_baselines.get(tab)
        if base is None:
            return False
        return self._snapshot_json(state) != base

    def _refresh_tab_dirty(self, tab: str | None = None) -> None:
        tab = tab or self._current_tab
        if not tab:
            return
        if self._is_tab_dirty(tab):
            self._tab_dirty.add(tab)
        else:
            self._tab_dirty.discard(tab)
        self._update_save_button_state()

    def _wire_page_dirty(self, tab: str) -> None:
        if tab == "general" and hasattr(self, "_cb_autostart"):
            self._bind_dirty(self._cb_autostart, tab)
        elif tab == "player":
            for w in (
                getattr(self, "_combo_quality", None),
                getattr(self, "_slider_player_opacity", None),
                getattr(self, "_player_cookies_edit", None),
            ):
                if w:
                    self._bind_dirty(w, tab)
            if hasattr(self, "_spin_player_hist_days"):
                self._bind_dirty(self._spin_player_hist_days, tab)
        elif tab == "sorter":
            for w in (getattr(self, "_sorter_src_edit", None),
                      getattr(self, "_cb_sorter_auto", None),
                      getattr(self, "_slider_sorter_opacity", None)):
                if w:
                    self._bind_dirty(w, tab)
            if hasattr(self, "_spin_sorter_hist_days"):
                self._bind_dirty(self._spin_sorter_hist_days, tab)
        elif tab == "ocr" and hasattr(self, "_cb_ocr_postprocess"):
            self._bind_dirty(self._cb_ocr_postprocess, tab)
        elif tab == "notes":
            for w in (
                getattr(self, "_notes_width_slider", None),
                getattr(self, "_notes_height_slider", None),
                getattr(self, "_slider_notes_opacity", None),
                getattr(self, "_cb_reminder_enabled", None),
                getattr(self, "_time_reminder_daily", None),
            ):
                if w:
                    self._bind_dirty(w, tab)
        elif tab == "enhancer":
            for w in (
                getattr(self, "_cb_enhancer_autosave", None),
                getattr(self, "_enhancer_path_edit", None),
                getattr(self, "_combo_enhancer_format", None),
                getattr(self, "_slider_enhancer_quality", None),
            ):
                if w:
                    self._bind_dirty(w, tab)

    def _save(self: "SettingsDialog") -> None:
        """Сохранить только текущую вкладку, если она изменена."""
        tab = self._current_tab
        if not tab:
            return
        if tab not in self._pages_loaded:
            self._ensure_page(tab)
        if not self._is_tab_dirty(tab):
            return

        emitted = self._save_tab(tab)
        if emitted is None:
            return

        self._set_tab_baseline(tab)
        self._clear_tab_dirty(tab)
        if emitted:
            self.settings_changed.emit(emitted)

    def _save_tab(self: "SettingsDialog", tab: str) -> dict | None:
        if tab == "general":
            return self._save_general_tab()
        if tab == "player":
            return self._save_player_tab()
        if tab == "sorter":
            return self._save_sorter_tab()
        if tab == "ocr":
            return self._save_ocr_tab()
        if tab == "notes":
            return self._save_notes_tab()
        if tab == "enhancer":
            return self._save_enhancer_tab()
        return {}

    def _save_general_tab(self) -> dict:
        self.cfg["autostart"] = self._cb_autostart.isChecked()
        config.save_keys(self.cfg, TAB_CFG_KEYS["general"])
        set_autostart(self.cfg["autostart"])
        return {"autostart": self.cfg["autostart"]}

    def _save_player_tab(self) -> dict:
        from app.core.paths import normalize_path

        self.cfg["player_quality"] = self._combo_quality.currentText()
        self.cfg["player_opacity"] = self._slider_player_opacity.value()
        self.cfg["player_history_days"] = self._spin_player_hist_days.value()
        stored = getattr(self, "_player_cookies_stored", "") or self._player_cookies_edit.text().strip()
        self.cfg["player_cookies_path"] = normalize_path(stored)
        self._player_cookies_stored = self.cfg["player_cookies_path"]
        config.save_keys(self.cfg, TAB_CFG_KEYS["player"])
        from app.core.database import db
        db.purge_expired_histories()
        return {k: self.cfg[k] for k in TAB_CFG_KEYS["player"]}

    def _save_sorter_tab(self) -> dict | None:
        from app.core.database import db
        from app.features.file_sorter.core.auto_watcher import get_auto_watcher
        from app.features.file_sorter.core.source_folder import (
            is_source_valid,
            set_source_folder,
        )

        self.cfg["sorter_source"] = set_source_folder(self._sorter_src_edit.text())
        auto = self._cb_sorter_auto.isChecked()
        if auto and not is_source_valid():
            auto = False
            self._cb_sorter_auto.setChecked(False)
        self.cfg["sorter_auto_enabled"] = auto
        self.cfg["sorter_opacity"] = self._slider_sorter_opacity.value()
        self.cfg["sorter_history_days"] = self._spin_sorter_hist_days.value()
        config.save_keys(self.cfg, TAB_CFG_KEYS["sorter"])
        get_auto_watcher().reload()
        db.purge_expired_histories()
        return {k: self.cfg[k] for k in TAB_CFG_KEYS["sorter"]}

    def _save_ocr_tab(self) -> dict | None:
        from app.features.ocr.core.ocr_settings import set_ocr_langs, set_postprocess_enabled
        from app.features.ocr.core.tesseract_env import missing_lang_packs

        langs = self._collect_ocr_langs()
        if not langs:
            QMessageBox.warning(self, "OCR", "Выберите хотя бы один язык Tesseract.")
            langs = ["rus", "eng"]
        to_fetch = missing_lang_packs(langs)
        if to_fetch and not self._run_ocr_lang_download(to_fetch):
            return None
        set_ocr_langs(langs)
        set_postprocess_enabled(self._cb_ocr_postprocess.isChecked())
        self.cfg["ocr_langs"] = langs
        return {"ocr_langs": langs}

    def _save_notes_tab(self) -> dict:
        from app.features.todo.core import reminder_settings as rs

        selected_position = next(
            (p for p, b in self._notes_position_btns.items() if b.isChecked()),
            "right",
        )
        self.cfg["notes_edge_position"] = selected_position
        self.cfg["notes_width"] = self._notes_width_slider.value()
        self.cfg["notes_height"] = self._notes_height_slider.value()
        self.cfg["notes_opacity"] = self._slider_notes_opacity.value()
        notes_mode = "work" if self._mode_work_radio.isChecked() else "normal"
        self.cfg["notes_mode"] = notes_mode

        config.save_keys(self.cfg, {
            "notes_edge_position", "notes_width", "notes_height",
            "notes_opacity", "notes_mode",
        })

        if hasattr(self, "_cb_reminder_enabled"):
            rs.set_enabled(self._cb_reminder_enabled.isChecked())
            mode = getattr(self, "_reminder_mode", "both")
            rs.set_mode(mode)
            t = self._time_reminder_daily.time()
            rs.set_daily_time(t.hour(), t.minute())
            rs.set_offsets(self._collect_reminder_offsets())
            self.cfg["reminder_enabled"] = self._cb_reminder_enabled.isChecked()
            self.cfg["reminder_mode"] = mode
            self.cfg["reminder_offsets"] = self._collect_reminder_offsets()

        return {
            "notes_edge_position": selected_position,
            "notes_width": self.cfg["notes_width"],
            "notes_height": self.cfg["notes_height"],
            "notes_opacity": self.cfg["notes_opacity"],
            "notes_mode": notes_mode,
        }

    def _save_enhancer_tab(self) -> dict:
        from app.core.paths import normalize_path
        from app.features.image_enhancer.core.save_utils import default_save_folder

        path = normalize_path(self._enhancer_path_edit.text().strip())
        self.cfg["enhancer_save_path"] = path or default_save_folder()
        self._enhancer_path_edit.setText(self.cfg["enhancer_save_path"])
        self.cfg["enhancer_autosave"] = self._cb_enhancer_autosave.isChecked()
        self.cfg["enhancer_format"] = self._combo_enhancer_format.currentText()
        self.cfg["enhancer_jpeg_quality"] = self._slider_enhancer_quality.value()
        config.save_keys(self.cfg, TAB_CFG_KEYS["enhancer"])
        return {k: self.cfg[k] for k in TAB_CFG_KEYS["enhancer"]}
