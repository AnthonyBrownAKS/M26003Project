import tkinter as tk
from PIL import Image, ImageTk
import cv2
import os
import time


class MonitorWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("处理结果监测界面")
        self.root.geometry("900x600")  # 稍微调高一点给控制栏留空间

        # 设置图片路径
        self.left_image_path = "../tmp/left.jpg"
        self.right_image_path = "../tmp/right.jpg"

        # 刷新间隔（毫秒）
        self.refresh_interval = 1000  # 1000ms = 1秒

        # 控制刷新标志
        self.is_running = True

        # ========== 上方：图片显示区域（左右相邻）==========
        image_container = tk.Frame(self.root)
        image_container.pack(fill="both", expand=True, padx=10, pady=10)

        # 创建左右面板（相邻）
        self.left_label = self.create_panel(image_container, "左侧相机")
        self.right_label = self.create_panel(image_container, "右侧相机")

        self.left_label.pack(side="left", expand=True, fill="both", padx=5, pady=5)
        self.right_label.pack(side="left", expand=True, fill="both", padx=5, pady=5)

        # ========== 下方：控制栏（单独一行）==========
        self.create_control_bar()

        # 启动定时刷新
        self.start_auto_refresh()

        # 设置窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # 初始加载图片
        self.refresh_images()

    def create_panel(self, parent, title):
        """创建显示面板"""
        frame = tk.Frame(parent, bd=2, relief="groove")

        # 标题
        title_label = tk.Label(frame, text=title, font=("微软雅黑", 14))
        title_label.pack(pady=5)

        # 图片显示区域
        img_label = tk.Label(frame, bg="#dfe6e9", text="等待图片...", font=("微软雅黑", 12))
        img_label.pack(expand=True, fill="both", padx=10, pady=10)

        # 状态标签
        status_label = tk.Label(frame, text="未加载", font=("微软雅黑", 10), fg="gray")
        status_label.pack(pady=5)

        frame.img_label = img_label
        frame.status_label = status_label
        return frame

    def create_control_bar(self):
        """创建底部控制栏（单独一行）"""
        control_frame = tk.Frame(self.root, bd=1, relief="raised", height=60)
        control_frame.pack(side="bottom", fill="x", padx=10, pady=5)
        control_frame.pack_propagate(False)  # 固定高度

        # 内部容器，用于居中对齐
        inner_frame = tk.Frame(control_frame)
        inner_frame.pack(expand=True)

        # 刷新间隔设置
        tk.Label(inner_frame, text="刷新间隔(秒):", font=("微软雅黑", 10)).pack(side="left", padx=5)

        self.interval_var = tk.StringVar(value="1")
        interval_entry = tk.Entry(inner_frame, textvariable=self.interval_var, width=5)
        interval_entry.pack(side="left", padx=5)

        tk.Button(inner_frame, text="设置", command=self.set_interval,
                  bg="#3498db", fg="white", padx=10).pack(side="left", padx=5)

        # 手动刷新按钮
        tk.Button(inner_frame, text="手动刷新", command=self.refresh_images,
                  bg="#2ecc71", fg="white", padx=10).pack(side="left", padx=20)

        # 状态显示
        self.status_var = tk.StringVar(value="状态: 运行中")
        status_label = tk.Label(inner_frame, textvariable=self.status_var,
                                font=("微软雅黑", 9), fg="blue")
        status_label.pack(side="left", padx=10)

        # 刷新计数
        self.refresh_count = 0
        self.count_label = tk.Label(inner_frame, text="刷新次数: 0", font=("微软雅黑", 9))
        self.count_label.pack(side="left", padx=10)

    def load_image(self, image_path):
        """加载图片并返回PhotoImage对象"""
        if not os.path.exists(image_path):
            return None, f"文件不存在: {os.path.basename(image_path)}"

        try:
            # 读取图片
            img = cv2.imread(image_path)
            if img is None:
                return None, "无法读取图片"

            # 转换颜色空间
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

            # 转换为PIL Image
            img = Image.fromarray(img)

            # 计算缩放比例（保持宽高比）
            target_size = (400, 400)
            img.thumbnail(target_size, Image.Resampling.LANCZOS)

            # 创建空白背景图（400x400）
            background = Image.new('RGB', target_size, (223, 230, 233))  # #dfe6e9
            # 计算居中位置
            x = (target_size[0] - img.size[0]) // 2
            y = (target_size[1] - img.size[1]) // 2
            # 粘贴图片到中心
            background.paste(img, (x, y))

            # 转换为PhotoImage
            imgtk = ImageTk.PhotoImage(background)

            return imgtk, f"成功 ({img.size[0]}x{img.size[1]})"

        except Exception as e:
            return None, f"错误: {str(e)}"

    def refresh_images(self):
        """刷新左右两侧图片"""
        # 加载左侧图片
        left_img, left_status = self.load_image(self.left_image_path)
        if left_img:
            self.left_label.img_label.config(image=left_img, text="")
            self.left_label.img_label.image = left_img  # 保持引用
            self.left_label.status_label.config(text=left_status, fg="green")
        else:
            self.left_label.img_label.config(image="", text=left_status)
            self.left_label.status_label.config(text=left_status, fg="red")

        # 加载右侧图片
        right_img, right_status = self.load_image(self.right_image_path)
        if right_img:
            self.right_label.img_label.config(image=right_img, text="")
            self.right_label.img_label.image = right_img  # 保持引用
            self.right_label.status_label.config(text=right_status, fg="green")
        else:
            self.right_label.img_label.config(image="", text=right_status)
            self.right_label.status_label.config(text=right_status, fg="red")

        # 更新计数
        self.refresh_count += 1
        self.count_label.config(text=f"刷新次数: {self.refresh_count}")

        # 更新时间戳
        current_time = time.strftime("%H:%M:%S")
        self.status_var.set(f"状态: 运行中 (最后刷新: {current_time})")

    def set_interval(self):
        """设置刷新间隔"""
        try:
            new_interval = float(self.interval_var.get())
            if new_interval >= 0.5:  # 最小0.5秒
                self.refresh_interval = int(new_interval * 1000)
                self.status_var.set(f"状态: 刷新间隔已改为 {new_interval} 秒")
            else:
                self.status_var.set("状态: 间隔不能小于0.5秒")
        except ValueError:
            self.status_var.set("状态: 请输入有效数字")

    def auto_refresh(self):
        """自动刷新循环"""
        if self.is_running:
            self.refresh_images()
            # 再次调用
            self.root.after(self.refresh_interval, self.auto_refresh)

    def start_auto_refresh(self):
        """启动自动刷新"""
        self.root.after(self.refresh_interval, self.auto_refresh)

    def on_closing(self):
        """窗口关闭时的处理"""
        self.is_running = False
        self.root.destroy()

    def run(self):
        """运行主循环"""
        self.root.mainloop()


# 独立运行
if __name__ == "__main__":
    # 检查图片路径是否存在
    left_path = "../tmp/left.jpg"
    right_path = "../tmp/right.jpg"

    print("=" * 50)
    print("监测界面启动")
    print(f"左侧图片路径: {os.path.abspath(left_path)}")
    print(f"右侧图片路径: {os.path.abspath(right_path)}")
    print(f"文件存在: 左侧={os.path.exists(left_path)}, 右侧={os.path.exists(right_path)}")
    print("=" * 50)

    # 创建并运行窗口
    monitor = MonitorWindow()
    monitor.run()


