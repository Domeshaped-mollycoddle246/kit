"""비서 — 개인용 맥 도구 모음 (메뉴바 앱)

메뉴는 카테고리별로 묶여 있습니다:
  📸 캡처 / 🎬 녹화·녹음 / 🗣️ 통역·번역 / 🌐 웹 도구 / 🧹 청소
"""

import os
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

import rumps

from features import (audio, autostart, capture, cleanup, config, record,
                      transcribe, translate)

APP_DIR = os.path.dirname(os.path.abspath(__file__))
ICON_PATH = os.path.join(APP_DIR, "assets", "icon_template.png")

WEB_TOOLS = [
    ("모든 변환(all-to-all)", "https://commme.github.io/all-to-all/"),
    ("파일 → PNG 변환", "https://commme.github.io/file-to-png/"),
    ("압축 풀기", "https://commme.github.io/unzip-tool/"),
    ("이미지 도구", "https://commme.github.io/image-tools/"),
    ("AI 도구 모음", "https://commme.github.io/ai-tools-hub/"),
]


def _fmt(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    return f"{m}:{s:02d}"


def _submenu(title, items):
    """제목과 (이름, 동작) 목록으로 하위 메뉴를 만듭니다."""
    menu = rumps.MenuItem(title)
    for entry in items:
        if isinstance(entry, rumps.MenuItem):
            menu.add(entry)
        else:
            label, cb = entry
            menu.add(rumps.MenuItem(label, callback=cb))
    return menu


class BiseoApp(rumps.App):
    def __init__(self):
        # 기본 종료 버튼 대신, 녹화·녹음을 정리하고 끄는 자체 종료 버튼을 씁니다.
        # 아이콘이 있으면 글자 대신 아이콘으로 표시 (다크모드 자동 대응)
        self._has_icon = os.path.exists(ICON_PATH)
        super().__init__("Kit",
                         icon=ICON_PATH if self._has_icon else None,
                         template=True, quit_button=None)

        # 글자가 바뀌는 토글 메뉴들
        self.rec_item = rumps.MenuItem("⏺︎ 화면 녹화 시작", callback=self.on_record)
        self.aud_item = rumps.MenuItem("⏺︎ 음성 녹음 시작", callback=self.on_audio)
        self.txt_item = rumps.MenuItem("⏺︎ 녹음을 글자로 변환…", callback=self.on_transcribe)
        self.interpret_item = rumps.MenuItem("⏺︎ 통역 시작 (말→번역)", callback=self.on_interpret)

        # 🌍 번역 (도착 언어 선택)
        self.translate_menu = _submenu("번역 (글)", [
            ("→ English", lambda _: self.do_translate("en")),
            ("→ 한국어", lambda _: self.do_translate("ko")),
            ("→ 日本語", lambda _: self.do_translate("ja")),
            ("→ 中文", lambda _: self.do_translate("zh")),
        ])

        # 🌐 웹 도구
        self.web_menu = _submenu("⏺︎ 웹 도구", [
            (label, lambda _, u=url: webbrowser.open(u)) for label, url in WEB_TOOLS
        ])

        # ⚙️ 설정
        self.autostart_item = rumps.MenuItem("로그인 시 자동 시작",
                                             callback=self.on_autostart)
        self.autostart_item.state = 1 if autostart.is_enabled() else 0
        self.settings_menu = _submenu("⏺︎ 설정", [
            self.autostart_item,
            ("저장 폴더 변경…", self.on_change_folder),
        ])

        # ===== 카테고리 메뉴 구성 =====
        self.menu = [
            rumps.MenuItem("⏺︎ 플로팅 팔레트 열기", callback=self.on_open_palette),
            None,
            _submenu("⏺︎ 캡처", [
                ("영역 캡처", self.on_area),
                ("전체화면 캡처", self.on_full),
                ("창 캡처", self.on_window),
                ("캡처 후 편집(모자이크/표시)", self.on_capture_edit),
                ("캡처 폴더 열기", self.on_open_folder),
            ]),
            _submenu("⏺︎ 녹화·녹음", [self.rec_item, self.aud_item, self.txt_item]),
            _submenu("⏺︎ 통역·번역", [
                self.interpret_item,
                ("실시간 통역 창", self.on_live),
                self.translate_menu,
            ]),
            self.web_menu,
            None,
            rumps.MenuItem("⏺︎ 바탕화면 청소", callback=self.on_cleanup),
            None,
            self.settings_menu,
            rumps.MenuItem("⏺︎ 정보", callback=self.on_info),
            None,
            rumps.MenuItem("종료", callback=self.on_quit),
        ]

        self._rec_start = None
        self._aud_start = None
        self._mic_purpose = None
        self._busy = False
        self._busy_title = ""
        self._pending = None

        self._timer = rumps.Timer(self._tick, 1)
        self._timer.start()

        # 첫 실행이면 환영 안내를 잠시 후 보여줍니다 (앱이 뜬 다음에)
        self._welcome_timer = rumps.Timer(self._maybe_welcome, 2)
        self._welcome_timer.start()

    # ===================== 캡처 =====================
    def on_area(self, _):
        capture.capture_area()

    def on_full(self, _):
        capture.capture_full()

    def on_window(self, _):
        capture.capture_window()

    def on_capture_edit(self, _):
        path = capture.capture_area_for_edit()
        if not path:
            return
        subprocess.Popen([sys.executable, os.path.join(APP_DIR, "editor.py"), path])

    def on_open_folder(self, _):
        capture.open_folder()

    # ===================== 화면 녹화 =====================
    def on_record(self, _):
        if record.is_recording():
            out = record.stop()
            self._rec_start = None
            self.rec_item.title = "⏺︎ 화면 녹화 시작"
            self._saved_alert("화면 녹화 완료", out)
        else:
            try:
                record.start()
                self._rec_start = time.time()
                self.rec_item.title = "⏹︎ 화면 녹화 중지"
            except Exception as e:
                rumps.alert(title="녹화 오류", message=str(e))

    # ===================== 음성 녹음 =====================
    def on_audio(self, _):
        if audio.is_recording():
            if self._mic_purpose != "record":
                rumps.alert("잠깐만요", "지금 통역 녹음 중이에요. 통역을 먼저 멈춰주세요.")
                return
            out = audio.stop()
            self._mic_purpose = None
            self._aud_start = None
            self.aud_item.title = "⏺︎ 음성 녹음 시작"
            if out and os.path.exists(out) and os.path.getsize(out) > 0:
                resp = rumps.alert(
                    title="음성 녹음 완료",
                    message=f"저장됨: {os.path.basename(out)}\n\n이 녹음을 글자(텍스트)로 변환할까요?",
                    ok="글자로 변환", cancel="나중에")
                if resp == 1:
                    self._start_bg("⏳ 글자 변환중…", self._do_transcription, out)
                else:
                    subprocess.run(["open", "-R", out])
            else:
                rumps.alert(title="녹음이 저장되지 않았어요 ⚠️",
                            message="마이크 권한을 확인해 주세요.")
        else:
            if self._start_mic("record"):
                self.aud_item.title = "⏹︎ 음성 녹음 중지"

    # ===================== 통역 (말 → 번역) =====================
    def on_interpret(self, _):
        if audio.is_recording():
            if self._mic_purpose != "interpret":
                rumps.alert("잠깐만요", "지금 음성 녹음 중이에요. 녹음을 먼저 멈춰주세요.")
                return
            out = audio.stop()
            self._mic_purpose = None
            self._aud_start = None
            self.interpret_item.title = "⏺︎ 통역 시작 (말→번역)"
            if out:
                self._start_bg("⏳ 통역 처리중…", self._do_interpretation, out)
        else:
            if self._start_mic("interpret"):
                self.interpret_item.title = "⏹︎ 통역 중지"

    def _start_mic(self, purpose) -> bool:
        try:
            audio.start()
            self._mic_purpose = purpose
            self._aud_start = time.time()
            return True
        except Exception as e:
            rumps.alert(title="마이크 오류", message=str(e))
            return False

    # ===================== 플로팅 팔레트 =====================
    def on_open_palette(self, _):
        subprocess.Popen([sys.executable, os.path.join(APP_DIR, "palette.py")])

    # ===================== 실시간 통역 창 =====================
    def on_live(self, _):
        subprocess.Popen([sys.executable, os.path.join(APP_DIR, "live_interpret.py")])

    # ===================== 번역 (글) =====================
    def do_translate(self, tgt):
        w = rumps.Window(
            message=f"{translate.LANGS[tgt]}(으)로 번역할 글을 입력/붙여넣으세요.\n(출발 언어는 자동 판별)",
            title="번역", default_text="", ok="번역", cancel="취소",
            dimensions=(360, 140))
        resp = w.run()
        if not (resp.clicked and resp.text.strip()):
            return
        try:
            direction, result = translate.translate_to(resp.text.strip(), tgt)
            rumps.alert(title=f"번역 결과 ({direction})", message=result)
        except Exception as e:
            rumps.alert(title="번역 오류", message=str(e))

    # ===================== 글자 변환 (파일 선택) =====================
    def on_transcribe(self, _):
        if self._busy:
            rumps.alert("잠깐만요", "이미 처리 중이에요. 끝나면 알려드릴게요.")
            return
        path = self._choose_audio()
        if path:
            self._start_bg("⏳ 글자 변환중…", self._do_transcription, path)

    def _choose_audio(self):
        script = 'POSIX path of (choose file with prompt "글자로 변환할 녹음 파일을 고르세요")'
        r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
        path = r.stdout.strip()
        return path if path and os.path.exists(path) else None

    # ===================== 백그라운드 작업 =====================
    def _start_bg(self, busy_title, worker, arg):
        self._busy = True
        self._busy_title = busy_title
        rumps.alert(title="시작했어요",
                    message="처리를 시작했어요. 메뉴바에 진행상태가 보여요.\n끝나면 결과 파일을 자동으로 열어드릴게요.")
        threading.Thread(target=worker, args=(arg,), daemon=True).start()

    def _do_transcription(self, audio_path):
        try:
            self._pending = ("done", transcribe.transcribe_to_file(audio_path))
        except Exception as e:
            self._pending = ("error", str(e))

    def _do_interpretation(self, audio_path):
        try:
            text = transcribe.transcribe_plain(audio_path, "ko")
            translated = translate.translate(text, "ko", "en") if text else ""
            out = str(Path(audio_path).with_suffix("")) + "_통역.txt"
            Path(out).write_text(
                f"[원문 한국어]\n{text}\n\n[번역 English]\n{translated}\n", encoding="utf-8")
            self._pending = ("done", out)
        except Exception as e:
            self._pending = ("error", str(e))

    # ===================== 바탕화면 청소 =====================
    def on_cleanup(self, _):
        if rumps.alert(title="바탕화면 청소",
                       message="바탕화면 파일들을 종류별로 '정리됨_날짜' 폴더에 정리할까요?\n(삭제하지 않고 옮기기만 합니다)",
                       ok="정리하기", cancel="취소") != 1:
            return
        moved, folders = cleanup.clean_desktop()
        rumps.alert(title="정리 완료",
                    message=f"파일 {moved}개를 정리했어요.\n폴더 {folders}개는 그대로 두었습니다.")

    # ===================== 설정 =====================
    def on_autostart(self, sender):
        try:
            if autostart.is_enabled():
                autostart.disable()
                sender.state = 0
                rumps.alert(title="자동 시작 끔",
                            message="다음 로그인부터 Kit이 자동으로 켜지지 않아요.")
            else:
                autostart.enable()
                sender.state = 1
                rumps.alert(title="자동 시작 켬 ✅",
                            message="다음부터 맥에 로그인하면 Kit이 자동으로 켜져요.")
        except Exception as e:
            rumps.alert(title="설정 오류", message=str(e))

    def on_change_folder(self, _):
        script = 'POSIX path of (choose folder with prompt "캡처·녹화·녹음을 저장할 폴더를 고르세요")'
        r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
        path = r.stdout.strip()
        if path and os.path.isdir(path):
            config.set("save_dir", path)
            rumps.alert(title="저장 폴더 변경됨 📂",
                        message=f"이제 캡처·녹화·녹음이 여기에 저장돼요:\n{path}")

    def _maybe_welcome(self, timer):
        timer.stop()
        if config.get("first_run_done"):
            return
        config.set("first_run_done", True)
        rumps.alert(
            title="Kit에 오신 걸 환영해요 👋",
            message="화면 맨 위 메뉴바의 당근 아이콘을 누르면 모든 기능이 나와요.\n\n"
                    "• 캡처·화면녹화를 쓰려면 '화면 기록' 권한이 필요해요:\n"
                    "  시스템 설정 → 개인정보 보호 및 보안 → 화면 및 시스템 오디오 기록에서\n"
                    "  목록에 보이는 항목(터미널 또는 Python)을 켜고 Kit을 재시작하세요.\n"
                    "• 녹음·통역은 첫 사용 때 마이크 권한만 허용하면 돼요.\n\n"
                    f"파일 저장 위치: {config.get('save_dir')}\n(⚙️ 설정에서 바꿀 수 있어요)")

    def on_info(self, _):
        rumps.alert(title="Kit v0.6",
                    message="캡처·편집(자르기·모자이크) · 화면녹화·음성녹음 · 글자변환 · "
                            "통역·번역(실시간) · 웹도구 · 청소 · 자동시작")

    def on_quit(self, _):
        # 녹화·녹음이 켜져 있으면 파일이 깨지지 않게 먼저 멈추고 종료합니다.
        try:
            if record.is_recording():
                record.stop()
            if audio.is_recording():
                audio.stop()
        finally:
            rumps.quit_application()

    # ===================== 상태 표시 =====================
    def _saved_alert(self, title, path):
        # 파일이 실제로 만들어졌는지 확인 (권한 없으면 빈손으로 끝나요)
        if path and os.path.exists(path) and os.path.getsize(path) > 0:
            rumps.alert(title=title, message=f"저장했어요:\n{os.path.basename(path)}")
            subprocess.run(["open", "-R", path])
        else:
            rumps.alert(
                title="녹화가 저장되지 않았어요 ⚠️",
                message="화면 기록 권한이 없어서 화면을 못 담았어요.\n\n"
                        "시스템 설정 → 개인정보 보호 및 보안 →\n"
                        "'화면 및 시스템 오디오 기록' 목록에 보이는 항목\n"
                        "(터미널 또는 Python)을 켠 뒤,\n"
                        "Kit을 종료하고 다시 실행해 주세요.")

    def _tick(self, _):
        if self._pending:
            kind, payload = self._pending
            self._pending = None
            self._busy = False
            if kind == "done":
                rumps.alert(title="완료 ✅", message=f"파일로 저장했어요:\n{os.path.basename(payload)}")
                subprocess.run(["open", payload])
            else:
                rumps.alert(title="오류", message=payload)

        if self._busy:
            self.title = self._busy_title
            return
        parts = []
        if record.is_recording() and self._rec_start:
            parts.append("화면 " + _fmt(time.time() - self._rec_start))
        if audio.is_recording() and self._aud_start:
            label = "통역" if self._mic_purpose == "interpret" else "녹음"
            parts.append(label + " " + _fmt(time.time() - self._aud_start))
        if parts:
            self.title = "🔴 " + "  ".join(parts)
        else:
            # 아이콘이 있으면 글자 없이 아이콘만, 없으면 'Kit' 글자
            self.title = None if self._has_icon else "Kit"


if __name__ == "__main__":
    BiseoApp().run()
