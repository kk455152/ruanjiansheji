import random
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
from data_gen import DataGen

class MultiDeviceGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("多设备并行模拟器")
        self.root.geometry("600x700")
        self.dg = DataGen()
        self.running = False
        self._setup_ui()

    def _setup_ui(self):
        # 1. 参数设置
        frame = ttk.LabelFrame(self.root, text="仿真配置", padding=10)
        frame.pack(fill="x", padx=10, pady=5)

        # 输入项布局
        labels = ["信号均值/方差", "音量均值/方差", "低音均值/方差", "喜欢概率(0-1)"]
        self.entries = []
        for i, text in enumerate(labels):
            ttk.Label(frame, text=text).grid(row=i, column=0, sticky="w", pady=2)
            e1 = ttk.Entry(frame, width=10); e1.grid(row=i, column=1, padx=5)
            e2 = ttk.Entry(frame, width=10); e2.grid(row=i, column=2, padx=5)
            self.entries.append((e1, e2))
        
        # 默认值填充
        self.entries[0][0].insert(0, "-39.2"); self.entries[0][1].insert(0, "5")
        self.entries[1][0].insert(0, "50"); self.entries[1][1].insert(0, "10")
        self.entries[2][0].insert(0, "8"); self.entries[2][1].insert(0, "1.5")
        self.entries[3][0].insert(0, "0.3")

        # 2. 线程数与周期
        config_f = ttk.Frame(frame)
        config_f.grid(row=4, column=0, columnspan=3, sticky="w", pady=10)
        
        ttk.Label(config_f, text="模拟设备数(线程数):").pack(side="left")
        self.thread_count = ttk.Spinbox(config_f, from_=1, to=50, width=5); self.thread_count.set(5)
        self.thread_count.pack(side="left", padx=5)
        
        ttk.Label(config_f, text="采样周期(秒):").pack(side="left", padx=5)
        self.interval = ttk.Entry(config_f, width=5); self.interval.insert(0, "1")
        self.interval.pack(side="left")

        # 3. 日志区
        self.log_text = tk.Text(self.root, height=20, bg="#1e1e1e", fg="#00ff00") # 黑底绿字更有模拟感
        self.log_text.pack(fill="both", expand=True, padx=10, pady=5)

        # 4. 控制按钮
        btn_f = ttk.Frame(self.root, padding=10)
        btn_f.pack(fill="x")
        self.start_btn = ttk.Button(btn_f, text="批量启动设备", command=self.start)
        self.start_btn.pack(side="left", expand=True)
        self.stop_btn = ttk.Button(btn_f, text="全部停止", command=self.stop, state="disabled")
        self.stop_btn.pack(side="right", expand=True)

    def device_worker(self, device_id, s_in, v_in, b_in, lp, delay):
        """每个线程代表一个独立运行的设备"""
        while self.running:
            # 获取数据
            data = self.dg.get_single_device_packet(device_id, s_in, v_in, b_in, lp)
            
            # 构建日志
            msg = f"设备#{data['id']} [{data['time']}] -> 信号:{data['signal']} | 音量:{data['volume']} | 低音:{data['bass']} | 喜欢:{data['like']}\n"
            
            # 线程安全地更新UI
            self.root.after(0, lambda m=msg: self.update_log(m))
            
            time.sleep(delay + random.uniform(0, 0.5)) # 增加随机偏移模拟异步

    def update_log(self, msg):
        self.log_text.insert("end", msg)
        self.log_text.see("end")

    def start(self):
        try:
            num_threads = int(self.thread_count.get())
            s_in = (float(self.entries[0][0].get()), float(self.entries[0][1].get()))
            v_in = (float(self.entries[1][0].get()), float(self.entries[1][1].get()))
            b_in = (float(self.entries[2][0].get()), float(self.entries[2][1].get()))
            lp = float(self.entries[3][0].get())
            delay = float(self.interval.get())

            self.running = True
            self.start_btn.config(state="disabled")
            self.stop_btn.config(state="normal")
            self.log_text.delete(1.0, "end")
            self.update_log(f"--- 已开启 {num_threads} 个设备线程 ---\n")

            # 批量创建并启动线程
            for i in range(1, num_threads + 1):
                t = threading.Thread(target=self.device_worker, args=(i, s_in, v_in, b_in, lp, delay), daemon=True)
                t.start()
        except:
            messagebox.showerror("错误", "请检查参数输入")

    def stop(self):
        self.running = False
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")

if __name__ == "__main__":
    root = tk.Tk()
    app = MultiDeviceGUI(root)
    root.mainloop()