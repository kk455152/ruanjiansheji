import customtkinter as ctk
import time

# ==========================================
# 第一部分：虚拟音箱后台逻辑 (Model层)
# ==========================================
class VirtualSpeaker:
    def __init__(self):
        # 模拟歌单数据
        self.playlist = [
            {"title": "夜曲", "artist": "周杰伦", "duration": 226}, # duration 单位是秒
            {"title": "Bohemian Rhapsody", "artist": "Queen", "duration": 354},
            {"title": "Hotel California", "artist": "Eagles", "duration": 390},
            {"title": "后来", "artist": "刘若英", "duration": 341},
        ]
        self.current_index = 0  # 当前播放歌曲的索引
        self.is_playing = False # 播放状态
        self.current_progress = 0.0 # 当前播放进度（秒）

    def get_current_song_info(self):
        """获取当前歌曲的完整信息"""
        return self.playlist[self.current_index]

    def toggle_play(self):
        """切换播放/暂停状态"""
        self.is_playing = not self.is_playing
        return self.is_playing

    def next_song(self):
        """切下一首"""
        # 使用取余数实现循环播放
        self.current_index = (self.current_index + 1) % len(self.playlist)
        self.reset_progress()

    def prev_song(self):
        """切上一首"""
        # 使用取余数实现循环播放，+len防止负数
        self.current_index = (self.current_index - 1 + len(self.playlist)) % len(self.playlist)
        self.reset_progress()

    def reset_progress(self):
        """重置进度条（切歌时用）"""
        self.current_progress = 0.0
        # 切歌后默认自动播放
        self.is_playing = True

    def tick(self, delta_time):
        """
        模拟时间流逝的核心函数。
        外部需要不断调用这个函数来让音箱“走字”。
        delta_time: 距离上次调用过去了多少秒
        """
        if self.is_playing:
            self.current_progress += delta_time
            
            # 检查是否播放完成
            current_song_duration = self.playlist[self.current_index]["duration"]
            if self.current_progress >= current_song_duration:
                self.next_song() # 自动切下一首

# ==========================================
# 第二部分：CustomTkinter 界面 (View & Controller层)
# ==========================================

# 设置全局主题 (可选: "System" (默认), "Dark", "Light")
ctk.set_appearance_mode("System") 
# 设置主题颜色 (可选: "blue" (默认), "green", "dark-blue")
ctk.set_default_color_theme("blue")

class SpeakerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # 1. 初始化后台音箱引擎
        self.speaker = VirtualSpeaker()
        
        # 用于计算时间间隔
        self.last_update_time = time.time()

        # 2. 搭建界面布局
        self.setup_ui()

        # 3. 启动定时更新循环 (让界面动起来的关键!)
        self.update_ui_loop()

    def setup_ui(self):
        self.title("智能音箱模拟器")
        self.geometry("400x500")
        # 禁止调整窗口大小，保持界面紧凑
        self.resizable(False, False)

        # --- 顶部：歌曲信息区域 ---
        self.info_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.info_frame.pack(pady=(40, 20))

        # 模拟专辑封面 (用一个 colored frame 代替)
        self.album_cover = ctk.CTkFrame(self.info_frame, width=150, height=150, corner_radius=20, fg_color=["#DDDDDD", "#333333"])
        self.album_cover.pack(pady=10)
        
        self.song_title_label = ctk.CTkLabel(self.info_frame, text="歌名加载中...", font=ctk.CTkFont(size=24, weight="bold"))
        self.song_title_label.pack()

        self.artist_label = ctk.CTkLabel(self.info_frame, text="歌手加载中...", font=ctk.CTkFont(size=16))
        self.artist_label.pack()

        # --- 中部：进度条区域 ---
        self.progress_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.progress_frame.pack(fill="x", padx=30, pady=20)

        self.progress_bar = ctk.CTkProgressBar(self.progress_frame)
        self.progress_bar.pack(fill="x")
        self.progress_bar.set(0) # 初始化为0

        # 时间显示 (左侧当前时间，右侧总时间)
        self.time_info_frame = ctk.CTkFrame(self.progress_frame, fg_color="transparent")
        self.time_info_frame.pack(fill="x", pady=(5, 0))
        
        self.current_time_label = ctk.CTkLabel(self.time_info_frame, text="00:00", font=ctk.CTkFont(size=12))
        self.current_time_label.pack(side="left")
        
        self.total_time_label = ctk.CTkLabel(self.time_info_frame, text="00:00", font=ctk.CTkFont(size=12))
        self.total_time_label.pack(side="right")

        # --- 底部：控制按钮区域 ---
        self.control_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.control_frame.pack(pady=20)

        # 上一首按钮
        self.prev_btn = ctk.CTkButton(self.control_frame, text="<<", width=60, command=self.on_prev_click)
        self.prev_btn.grid(row=0, column=0, padx=10)

        # 播放/暂停按钮 (重点)
        self.play_pause_btn = ctk.CTkButton(self.control_frame, text="▶", width=80, height=80, corner_radius=40, font=ctk.CTkFont(size=30), command=self.on_play_pause_click)
        self.play_pause_btn.grid(row=0, column=1, padx=10)

        # 下一首按钮
        self.next_btn = ctk.CTkButton(self.control_frame, text=">>", width=60, command=self.on_next_click)
        self.next_btn.grid(row=0, column=2, padx=10)

    # --- 格式化时间的辅助函数 (把秒数变成 mm:ss 格式) ---
    def format_time(self, seconds):
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins:02d}:{secs:02d}"

    # --- 按钮点击事件处理 ---
    def on_play_pause_click(self):
        is_playing = self.speaker.toggle_play()
        # 点击后立刻更新按钮文本，无需等待下一次循环
        new_text = "||" if is_playing else "▶"
        self.play_pause_btn.configure(text=new_text)

    def on_next_click(self):
        self.speaker.next_song()
        # 切歌后强制更新一次界面
        self.update_view_data()

    def on_prev_click(self):
        self.speaker.prev_song()
        self.update_view_data()

    # --- 核心循环：更新界面数据 ---
    def update_view_data(self):
        """从音箱后台拉取最新数据，并刷新界面显示"""
        song_info = self.speaker.get_current_song_info()
        current_progress = self.speaker.current_progress
        duration = song_info["duration"]

        # 1. 更新文本信息
        self.song_title_label.configure(text=song_info["title"])
        self.artist_label.configure(text=song_info["artist"])
        self.current_time_label.configure(text=self.format_time(current_progress))
        self.total_time_label.configure(text=self.format_time(duration))

        # 2. 更新播放按钮状态 (防止状态不同步)
        btn_text = "||" if self.speaker.is_playing else "▶"
        if self.play_pause_btn.cget("text") != btn_text:
             self.play_pause_btn.configure(text=btn_text)

        # 3. 更新进度条 (值范围是 0.0 到 1.0)
        if duration > 0:
            progress_percent = current_progress / duration
            self.progress_bar.set(progress_percent)
        else:
            self.progress_bar.set(0)

    def update_ui_loop(self):
        """
        这是一个无限循环，每隔一小段时间执行一次。
        """
        # 计算距离上一次调用过去了多久，保证时间准确性
        now = time.time()
        delta_time = now - self.last_update_time
        self.last_update_time = now

        # 1. 告诉后台音箱：时间过去了 delta_time 秒，请更新你的状态
        self.speaker.tick(delta_time)

        # 2. 刷新界面显示
        self.update_view_data()

        # 3. 安排下一次执行 (例如 100毫秒后再次调用自己)
        # 这是 GUI 编程中替代 while True 循环的标准做法，不会卡死界面
        self.after(100, self.update_ui_loop)

# ==========================================
# 主程序入口
# ==========================================
if __name__ == "__main__":
    app = SpeakerApp()
    # 初始状态先暂停，让用户点击播放
    app.speaker.is_playing = False
    app.on_play_pause_click() # 触发一次点击让按钮变成播放状态

    print("模拟器已启动。请在弹出的窗口中操作。")
    app.mainloop()