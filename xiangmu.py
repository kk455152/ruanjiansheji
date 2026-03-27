import argparse
import csv
import os
import queue
import random
import threading
import time
import tkinter as tk
from collections import defaultdict, deque
from datetime import datetime
from tkinter import ttk


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, "log")
CSV_FILE = os.path.join(LOG_DIR, "data.csv")
CSV_HEADERS = ["timestamp", "device_id", "metric_type", "value"]

BG = "#0f172a"
PANEL = "#111827"
PANEL_ALT = "#1f2937"
BORDER = "#334155"
TEXT = "#e5e7eb"
MUTED = "#94a3b8"
ACCENT = "#22c55e"
BLUE = "#38bdf8"
ORANGE = "#fb923c"
PINK = "#f472b6"
PURPLE = "#a78bfa"

METRIC_SIGNAL = "信号强度"
METRIC_VOLUME = "音量"
METRIC_BASS = "低音增益"
METRIC_GENRE = "播放风格"
METRIC_LIKE = "收藏状态"

NUMERIC_METRICS = {
    METRIC_SIGNAL: {"mu": 60.0, "sigma": 5.2, "min": 10.0, "max": 100.0, "interval": 3.0, "color": BLUE, "label": "信号强度"},
    METRIC_VOLUME: {"mu": 50.0, "sigma": 10.0, "min": 1.0, "max": 100.0, "interval": 3.0, "color": ACCENT, "label": "音量"},
    METRIC_BASS: {"mu": 6.5, "sigma": 1.8, "min": 0.1, "max": 12.0, "interval": 5.0, "color": ORANGE, "label": "低音增益"},
}

STATE_LABELS = {
    METRIC_GENRE: "播放风格",
    METRIC_LIKE: "收藏状态",
}

VALUE_RANGES = {
    METRIC_SIGNAL: (0.0, 100.0),
    METRIC_VOLUME: (0.0, 100.0),
    METRIC_BASS: (0.0, 12.0),
}

file_lock = threading.Lock()


def init_env():
    os.makedirs(LOG_DIR, exist_ok=True)
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, "w", newline="", encoding="utf-8-sig") as file:
            csv.writer(file).writerow(CSV_HEADERS)


def write_data_safe(device_id, metric_type, value):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with file_lock:
        with open(CSV_FILE, "a", newline="", encoding="utf-8-sig") as file:
            csv.writer(file).writerow([timestamp, device_id, metric_type, value])
    print(f"[{timestamp}] {device_id} | {metric_type}: {value}", flush=True)
    return timestamp


def generate_normal_data(mu, sigma, min_val, max_val):
    value = random.gauss(mu, sigma)
    value = max(min(value, max_val), min_val)
    if value <= 0:
        value = 0.01
    return round(value, 2)


class SmartSpeakerSimulator:
    def __init__(self, device_id, event_callback=None):
        self.device_id = device_id
        self.event_callback = event_callback
        self.stop_event = threading.Event()
        self.threads = []
        self.running = False

    def emit(self, metric_type, value):
        timestamp = write_data_safe(self.device_id, metric_type, value)
        if self.event_callback:
            self.event_callback(
                {
                    "timestamp": timestamp,
                    "device_id": self.device_id,
                    "metric_type": metric_type,
                    "value": value,
                }
            )

    def start(self):
        if self.running:
            return
        self.running = True
        self.stop_event.clear()
        self.threads = [
            threading.Thread(target=self.simulate_hardware_status, daemon=True),
            threading.Thread(target=self.simulate_playback_status, daemon=True),
        ]
        for thread in self.threads:
            thread.start()

    def stop(self):
        if not self.running:
            return
        self.stop_event.set()
        self.running = False

    def simulate_hardware_status(self):
        while not self.stop_event.is_set():
            current_hour = datetime.now().hour
            volume_mu = 50 if 7 <= current_hour < 22 else 20

            self.emit(
                METRIC_SIGNAL,
                generate_normal_data(
                    NUMERIC_METRICS[METRIC_SIGNAL]["mu"],
                    NUMERIC_METRICS[METRIC_SIGNAL]["sigma"],
                    NUMERIC_METRICS[METRIC_SIGNAL]["min"],
                    NUMERIC_METRICS[METRIC_SIGNAL]["max"],
                ),
            )
            self.emit(
                METRIC_VOLUME,
                generate_normal_data(
                    volume_mu,
                    NUMERIC_METRICS[METRIC_VOLUME]["sigma"],
                    NUMERIC_METRICS[METRIC_VOLUME]["min"],
                    NUMERIC_METRICS[METRIC_VOLUME]["max"],
                ),
            )
            time.sleep(NUMERIC_METRICS[METRIC_VOLUME]["interval"])

    def simulate_playback_status(self):
        genres = ["pop", "rock", "classical"]
        while not self.stop_event.is_set():
            genre = random.choice(genres)
            genre_mu = {"pop": 4.5, "rock": 8.0, "classical": 6.0}[genre]
            liked = "true" if random.random() < 0.3 else "false"

            self.emit(
                METRIC_BASS,
                generate_normal_data(
                    genre_mu,
                    NUMERIC_METRICS[METRIC_BASS]["sigma"],
                    NUMERIC_METRICS[METRIC_BASS]["min"],
                    NUMERIC_METRICS[METRIC_BASS]["max"],
                ),
            )
            self.emit(METRIC_GENRE, genre)
            self.emit(METRIC_LIKE, liked)
            time.sleep(NUMERIC_METRICS[METRIC_BASS]["interval"])


class SmartSpeakerGUI:
    def __init__(self, device_id):
        self.device_id = device_id
        self.event_queue = queue.Queue()
        self.simulator = SmartSpeakerSimulator(device_id, self.event_queue.put)
        self.history = {metric: deque(maxlen=25) for metric in NUMERIC_METRICS}
        self.counts = defaultdict(int)

        self.root = tk.Tk()
        self.root.title("智能音箱数据看板")
        self.root.geometry("1280x820")
        self.root.minsize(1120, 760)
        self.root.configure(bg=BG)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.status_text = tk.StringVar(value="未启动")
        self.device_text = tk.StringVar(value=f"设备编号：{self.device_id}")
        self.signal_text = tk.StringVar(value="--")
        self.volume_text = tk.StringVar(value="--")
        self.bass_text = tk.StringVar(value="--")
        self.genre_text = tk.StringVar(value="--")
        self.like_text = tk.StringVar(value="--")
        self.total_text = tk.StringVar(value="0 条数据")
        self.latest_time_text = tk.StringVar(value="暂无数据")

        self._configure_styles()
        self._build_layout()
        self.root.after(300, self.process_events)

    def _configure_styles(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(
            "Dark.Treeview",
            background=PANEL,
            foreground=TEXT,
            fieldbackground=PANEL,
            rowheight=28,
            bordercolor=BORDER,
            borderwidth=0,
        )
        style.configure(
            "Dark.Treeview.Heading",
            background=PANEL_ALT,
            foreground=TEXT,
            relief="flat",
        )
        style.map("Dark.Treeview", background=[("selected", "#1d4ed8")], foreground=[("selected", TEXT)])

    def _build_layout(self):
        root_frame = tk.Frame(self.root, bg=BG)
        root_frame.pack(fill="both", expand=True, padx=18, pady=18)
        root_frame.grid_columnconfigure(0, weight=3)
        root_frame.grid_columnconfigure(1, weight=2)
        root_frame.grid_rowconfigure(1, weight=1)
        root_frame.grid_rowconfigure(2, weight=1)

        header = tk.Frame(root_frame, bg=BG)
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 18))
        header.grid_columnconfigure(0, weight=1)
        tk.Label(header, text="智能音箱数据看板", bg=BG, fg=TEXT, font=("Segoe UI", 24, "bold")).grid(row=0, column=0, sticky="w")
        tk.Label(header, textvariable=self.device_text, bg=BG, fg=MUTED, font=("Segoe UI", 11)).grid(row=1, column=0, sticky="w", pady=(6, 0))

        control_panel = tk.Frame(header, bg=BG)
        control_panel.grid(row=0, column=1, rowspan=2, sticky="e")
        tk.Button(control_panel, text="启动模拟", command=self.start_simulation, bg=ACCENT, fg="#052e16", relief="flat", padx=16, pady=10, font=("Segoe UI", 11, "bold")).pack(side="left", padx=6)
        tk.Button(control_panel, text="停止模拟", command=self.stop_simulation, bg=ORANGE, fg="#431407", relief="flat", padx=16, pady=10, font=("Segoe UI", 11, "bold")).pack(side="left", padx=6)
        tk.Button(control_panel, text="清空数据", command=self.clear_history, bg=PANEL_ALT, fg=TEXT, relief="flat", padx=16, pady=10, font=("Segoe UI", 11, "bold")).pack(side="left", padx=6)

        summary = tk.Frame(root_frame, bg=BG)
        summary.grid(row=1, column=0, sticky="nsew", padx=(0, 14))
        for index in range(3):
            summary.grid_columnconfigure(index, weight=1)
        for index in range(2):
            summary.grid_rowconfigure(index, weight=1)

        self._make_stat_card(summary, "运行状态", self.status_text, 0, 0, ACCENT)
        self._make_stat_card(summary, "信号强度", self.signal_text, 0, 1, BLUE)
        self._make_stat_card(summary, "当前音量", self.volume_text, 0, 2, ACCENT)
        self._make_stat_card(summary, "低音增益", self.bass_text, 1, 0, ORANGE)
        self._make_stat_card(summary, "播放风格", self.genre_text, 1, 1, PINK)
        self._make_stat_card(summary, "收藏状态", self.like_text, 1, 2, PURPLE)

        right_panel = tk.Frame(root_frame, bg=BG)
        right_panel.grid(row=1, column=1, rowspan=2, sticky="nsew")
        right_panel.grid_rowconfigure(1, weight=1)
        right_panel.grid_columnconfigure(0, weight=1)

        overview = tk.Frame(right_panel, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        overview.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        tk.Label(overview, text="数据概览", bg=PANEL, fg=TEXT, font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=16, pady=(14, 4))
        tk.Label(overview, textvariable=self.total_text, bg=PANEL, fg=ACCENT, font=("Segoe UI", 22, "bold")).pack(anchor="w", padx=16)
        tk.Label(overview, textvariable=self.latest_time_text, bg=PANEL, fg=MUTED, font=("Segoe UI", 10)).pack(anchor="w", padx=16, pady=(4, 14))

        table_card = tk.Frame(right_panel, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        table_card.grid(row=1, column=0, sticky="nsew")
        table_card.grid_rowconfigure(1, weight=1)
        table_card.grid_columnconfigure(0, weight=1)
        tk.Label(table_card, text="最新生成数据", bg=PANEL, fg=TEXT, font=("Segoe UI", 14, "bold")).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 10))

        columns = ("timestamp", "metric", "value")
        self.data_table = ttk.Treeview(table_card, columns=columns, show="headings", style="Dark.Treeview")
        self.data_table.heading("timestamp", text="时间")
        self.data_table.heading("metric", text="指标")
        self.data_table.heading("value", text="数值")
        self.data_table.column("timestamp", width=160, anchor="center")
        self.data_table.column("metric", width=120, anchor="center")
        self.data_table.column("value", width=90, anchor="center")
        self.data_table.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))

        chart_card = tk.Frame(root_frame, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        chart_card.grid(row=2, column=0, sticky="nsew", padx=(0, 14))
        chart_card.grid_columnconfigure(0, weight=1)
        chart_card.grid_rowconfigure(1, weight=1)
        tk.Label(chart_card, text="实时趋势图", bg=PANEL, fg=TEXT, font=("Segoe UI", 14, "bold")).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 8))
        tk.Label(chart_card, text="展示最近 25 个数值点，并自动刷新。", bg=PANEL, fg=MUTED, font=("Segoe UI", 10)).grid(row=0, column=0, sticky="e", padx=16)
        self.chart_canvas = tk.Canvas(chart_card, bg="#0b1220", highlightthickness=0)
        self.chart_canvas.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))
        self.chart_canvas.bind("<Configure>", lambda _event: self.draw_chart())

    def _make_stat_card(self, parent, title, variable, row, column, accent_color):
        card = tk.Frame(parent, bg=PANEL, highlightbackground=BORDER, highlightthickness=1, padx=16, pady=16)
        card.grid(row=row, column=column, sticky="nsew", padx=6, pady=6)
        tk.Label(card, text=title, bg=PANEL, fg=MUTED, font=("Segoe UI", 11)).pack(anchor="w")
        tk.Label(card, textvariable=variable, bg=PANEL, fg=accent_color, font=("Segoe UI", 22, "bold")).pack(anchor="w", pady=(10, 0))

    def start_simulation(self):
        self.simulator.start()
        self.status_text.set("运行中")

    def stop_simulation(self):
        self.simulator.stop()
        self.status_text.set("已停止")

    def clear_history(self):
        for values in self.history.values():
            values.clear()
        for item in self.data_table.get_children():
            self.data_table.delete(item)
        self.counts.clear()
        self.total_text.set("0 条数据")
        self.latest_time_text.set("暂无数据")
        self.signal_text.set("--")
        self.volume_text.set("--")
        self.bass_text.set("--")
        self.genre_text.set("--")
        self.like_text.set("--")
        self.draw_chart()

    def process_events(self):
        updated = False
        while True:
            try:
                event = self.event_queue.get_nowait()
            except queue.Empty:
                break
            self.handle_event(event)
            updated = True
        if updated:
            self.draw_chart()
        self.root.after(300, self.process_events)

    def handle_event(self, event):
        metric = event["metric_type"]
        value = event["value"]
        timestamp = event["timestamp"]

        self.counts["total"] += 1
        self.total_text.set(f"{self.counts['total']} 条数据")
        self.latest_time_text.set(f"最近更新时间：{timestamp}")

        if metric in self.history:
            self.history[metric].append(float(value))

        if metric == METRIC_SIGNAL:
            self.signal_text.set(f"{value}%")
        elif metric == METRIC_VOLUME:
            self.volume_text.set(f"{value}%")
        elif metric == METRIC_BASS:
            self.bass_text.set(f"{value} dB")
        elif metric == METRIC_GENRE:
            self.genre_text.set(str(value))
        elif metric == METRIC_LIKE:
            self.like_text.set(str(value))

        self.data_table.insert("", 0, values=(timestamp, metric, value))
        children = self.data_table.get_children()
        if len(children) > 14:
            self.data_table.delete(children[-1])

    def draw_chart(self):
        canvas = self.chart_canvas
        canvas.delete("all")

        width = max(canvas.winfo_width(), 320)
        height = max(canvas.winfo_height(), 240)
        left = 56
        top = 24
        right = width - 26
        bottom = height - 42

        canvas.create_rectangle(0, 0, width, height, fill="#0b1220", outline="")
        canvas.create_rectangle(left, top, right, bottom, outline=BORDER, width=1)

        grid_lines = 4
        for index in range(grid_lines + 1):
            y = top + (bottom - top) * index / grid_lines
            label_value = 100 - (100 / grid_lines) * index
            canvas.create_line(left, y, right, y, fill="#1e293b", dash=(2, 4))
            canvas.create_text(left - 10, y, text=f"{label_value:.0f}", fill=MUTED, font=("Segoe UI", 9), anchor="e")

        legend_x = left
        for metric, config in NUMERIC_METRICS.items():
            canvas.create_line(legend_x, height - 16, legend_x + 18, height - 16, fill=config["color"], width=3)
            canvas.create_text(legend_x + 24, height - 16, text=config["label"], fill=TEXT, font=("Segoe UI", 9), anchor="w")
            legend_x += 120

        for metric, points in self.history.items():
            if len(points) < 2:
                continue

            min_val, max_val = VALUE_RANGES[metric]
            chart_points = []
            span_x = right - left
            span_y = bottom - top
            count = len(points) - 1

            for index, value in enumerate(points):
                x = left + (span_x * index / max(count, 1))
                y = bottom - ((value - min_val) / (max_val - min_val)) * span_y
                chart_points.extend((x, y))

            canvas.create_line(*chart_points, fill=NUMERIC_METRICS[metric]["color"], width=3, smooth=True)
            last_x, last_y = chart_points[-2], chart_points[-1]
            canvas.create_oval(last_x - 4, last_y - 4, last_x + 4, last_y + 4, fill=NUMERIC_METRICS[metric]["color"], outline="")
            canvas.create_text(last_x + 8, last_y - 10, text=str(points[-1]), fill=NUMERIC_METRICS[metric]["color"], font=("Segoe UI", 9, "bold"), anchor="w")

    def on_close(self):
        self.simulator.stop()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


def run_cli(device_id):
    simulator = SmartSpeakerSimulator(device_id)
    simulator.start()
    print(f"模拟器已启动，设备编号：{device_id}")
    print(f"CSV 输出位置：{CSV_FILE}")
    print("按 Ctrl+C 停止。")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        simulator.stop()
        print("\n模拟器已停止。")


def main():
    parser = argparse.ArgumentParser(description="带 GUI 可视化的智能音箱模拟器")
    parser.add_argument("--id", type=str, default="speaker_01", help="设备编号，例如 speaker_01")
    parser.add_argument("--cli", action="store_true", help="仅运行命令行模式")
    args = parser.parse_args()

    init_env()
    if args.cli:
        run_cli(args.id)
    else:
        SmartSpeakerGUI(args.id).run()


if __name__ == "__main__":
    main()
