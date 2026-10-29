import ctypes
import sys
import threading
import time
from ctypes import byref, c_int, c_size_t, c_uint, c_void_p, Structure

import customtkinter as ctk
import keyboard
import pyautogui

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0

# ---------- Цвета интерфейса ----------
KEY = "#010101"        # "прозрачный" цвет: через него видно размытый фон
CARD = "#15151b"
ACCENT = "#7c5cff"
ACCENT_HOVER = "#9179ff"
STOP = "#ff4d6d"
STOP_HOVER = "#ff7089"
TEXT = "#f2f2f7"
MUTED = "#8b8b99"
GREEN = "#3ddc97"


# ---------- Эффект стекла (Windows) ----------
class ACCENT_POLICY(Structure):
    _fields_ = [
        ("AccentState", c_int),
        ("AccentFlags", c_int),
        ("GradientColor", c_uint),
        ("AnimationId", c_int),
    ]


class WINCOMPATTRDATA(Structure):
    _fields_ = [
        ("Attribute", c_int),
        ("Data", c_void_p),
        ("SizeOfData", c_size_t),
    ]


def apply_glass(window, tint=0xAA, color=0x14100E):
    """Акрил-размытие + тёмный заголовок + скруглённые углы.
    tint: 0..255, чем больше, тем темнее и менее прозрачно.
    color: BGR-цвет подложки."""
    if sys.platform != "win32":
        return
    try:
        window.update()
        hwnd = ctypes.windll.user32.GetParent(window.winfo_id()) or window.winfo_id()

        # тёмный заголовок окна
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, 20, byref(c_int(1)), 4)
        # скруглённые углы (Windows 11)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, 33, byref(c_int(2)), 4)

        # акрил-размытие
        accent = ACCENT_POLICY()
        accent.AccentState = 4  # ACCENT_ENABLE_ACRYLICBLURBEHIND
        accent.AccentFlags = 2
        accent.GradientColor = (tint << 24) | color
        data = WINCOMPATTRDATA()
        data.Attribute = 19  # WCA_ACCENT_POLICY
        data.Data = ctypes.cast(byref(accent), c_void_p)
        data.SizeOfData = ctypes.sizeof(accent)
        ctypes.windll.user32.SetWindowCompositionAttribute(hwnd, byref(data))
    except Exception as e:
        print(f"[WARN] Не удалось включить эффект стекла: {e}")


# ---------- Логика бота ----------
class Bot:
    def __init__(self):
        w, h = pyautogui.size()
        self.x, self.y = w // 2, h // 2
        self.tolerance = 15
        self.enabled = False
        self.clicks = 0
        self.holding = False
        self.alive = True
        self.current = (0, 0, 0)
        self._base = None

    @staticmethod
    def match(c1, c2, tol):
        return all(abs(a - b) <= tol for a, b in zip(c1[:3], c2[:3]))

    def run(self):
        while self.alive:
            try:
                if keyboard.is_pressed("esc"):
                    self.alive = False
                    break

                if self.enabled and keyboard.is_pressed("alt"):
                    self.holding = True
                    cur = pyautogui.pixel(self.x, self.y)
                    self.current = cur
                    if self._base is None:
                        self._base = cur
                    elif not self.match(cur, self._base, self.tolerance):
                        pyautogui.click()
                        self.clicks += 1
                        self._base = cur
                else:
                    self.holding = False
                    self._base = None
            except Exception as e:
                print(f"[ERROR] {e}")
            time.sleep(0.001)


# ---------- Интерфейс ----------
class App(ctk.CTk):
    def __init__(self, bot: Bot):
        super().__init__(fg_color=KEY)
        self.bot = bot

        ctk.set_appearance_mode("dark")
        self.title("ColorBot")
        self.geometry("340x470+40+40")  # слева сверху, чтобы не закрывать центр экрана
        self.resizable(False, False)
        self.attributes("-transparentcolor", KEY)
        self.attributes("-topmost", True)

        # --- шапка ---
        ctk.CTkLabel(self, text="ColorBot", text_color=TEXT,
                     font=ctk.CTkFont("Segoe UI", 26, "bold")
                     ).pack(anchor="w", padx=24, pady=(22, 0))
        ctk.CTkLabel(self, text="Удерживай ALT · ESC для выхода",
                     text_color=MUTED, font=ctk.CTkFont("Segoe UI", 12)
                     ).pack(anchor="w", padx=24, pady=(0, 14))

        # --- карточка статуса ---
        card = ctk.CTkFrame(self, fg_color=CARD, corner_radius=18)
        card.pack(fill="x", padx=20, pady=6)

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=18, pady=(14, 4))
        self.dot = ctk.CTkLabel(row, text="●", text_color=MUTED,
                                font=ctk.CTkFont(size=16))
        self.dot.pack(side="left")
        self.status = ctk.CTkLabel(row, text="Остановлен", text_color=TEXT,
                                   font=ctk.CTkFont("Segoe UI", 15, "bold"))
        self.status.pack(side="left", padx=8)

        row2 = ctk.CTkFrame(card, fg_color="transparent")
        row2.pack(fill="x", padx=18, pady=(4, 14))
        self.swatch = ctk.CTkFrame(row2, width=34, height=34, corner_radius=10,
                                   fg_color="#000000")
        self.swatch.pack(side="left")
        self.swatch.pack_propagate(False)
        info = ctk.CTkFrame(row2, fg_color="transparent")
        info.pack(side="left", padx=12)
        ctk.CTkLabel(info, text="Цвет в центре экрана", text_color=MUTED,
                     font=ctk.CTkFont("Segoe UI", 11)).pack(anchor="w")
        self.rgb = ctk.CTkLabel(info, text="RGB 0, 0, 0", text_color=TEXT,
                                font=ctk.CTkFont("Consolas", 13))
        self.rgb.pack(anchor="w")

        # --- карточка допуска ---
        card2 = ctk.CTkFrame(self, fg_color=CARD, corner_radius=18)
        card2.pack(fill="x", padx=20, pady=6)

        top = ctk.CTkFrame(card2, fg_color="transparent")
        top.pack(fill="x", padx=18, pady=(14, 0))
        ctk.CTkLabel(top, text="Допуск цвета", text_color=TEXT,
                     font=ctk.CTkFont("Segoe UI", 13, "bold")).pack(side="left")
        self.tol_label = ctk.CTkLabel(top, text=str(bot.tolerance),
                                      text_color=ACCENT,
                                      font=ctk.CTkFont("Segoe UI", 13, "bold"))
        self.tol_label.pack(side="right")

        self.slider = ctk.CTkSlider(card2, from_=1, to=100, number_of_steps=99,
                                    progress_color=ACCENT, button_color=TEXT,
                                    button_hover_color=ACCENT_HOVER,
                                    fg_color="#2a2a33", command=self.on_tol)
        self.slider.set(bot.tolerance)
        self.slider.pack(fill="x", padx=18, pady=(8, 16))

        # --- счётчик ---
        card3 = ctk.CTkFrame(self, fg_color=CARD, corner_radius=18)
        card3.pack(fill="x", padx=20, pady=6)
        r = ctk.CTkFrame(card3, fg_color="transparent")
        r.pack(fill="x", padx=18, pady=12)
        ctk.CTkLabel(r, text="Кликов", text_color=MUTED,
                     font=ctk.CTkFont("Segoe UI", 13)).pack(side="left")
        self.clicks = ctk.CTkLabel(r, text="0", text_color=TEXT,
                                   font=ctk.CTkFont("Segoe UI", 15, "bold"))
        self.clicks.pack(side="right")

        # --- кнопка ---
        self.btn = ctk.CTkButton(self, text="Старт", height=46, corner_radius=14,
                                 fg_color=ACCENT, hover_color=ACCENT_HOVER,
                                 font=ctk.CTkFont("Segoe UI", 15, "bold"),
                                 command=self.toggle)
        self.btn.pack(fill="x", padx=20, pady=(12, 18))

        apply_glass(self)
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.refresh()

    def on_tol(self, value):
        self.bot.tolerance = int(value)
        self.tol_label.configure(text=str(int(value)))

    def toggle(self):
        self.bot.enabled = not self.bot.enabled
        if self.bot.enabled:
            self.btn.configure(text="Стоп", fg_color=STOP, hover_color=STOP_HOVER)
        else:
            self.btn.configure(text="Старт", fg_color=ACCENT, hover_color=ACCENT_HOVER)

    def refresh(self):
        if not self.bot.alive:
            self.destroy()
            return

        if not self.bot.enabled:
            self.dot.configure(text_color=MUTED)
            self.status.configure(text="Остановлен")
        elif self.bot.holding:
            self.dot.configure(text_color=GREEN)
            self.status.configure(text="Работает")
        else:
            self.dot.configure(text_color=ACCENT)
            self.status.configure(text="Ожидание ALT")

        try:
            r, g, b = pyautogui.pixel(self.bot.x, self.bot.y)
            self.swatch.configure(fg_color=f"#{r:02x}{g:02x}{b:02x}")
            self.rgb.configure(text=f"RGB {r}, {g}, {b}")
        except Exception:
            pass

        self.clicks.configure(text=str(self.bot.clicks))
        self.after(100, self.refresh)

    def close(self):
        self.bot.alive = False
        self.destroy()


if __name__ == "__main__":
    bot = Bot()
    threading.Thread(target=bot.run, daemon=True).start()
    App(bot).mainloop()
