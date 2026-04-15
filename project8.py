import cv2
import numpy as np
import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox
from PIL import Image, ImageTk
import json, os

# from Camera import Camera

DATA_FILE = "data.json"

# 3.26版本
# 加入camera路径属性
# 不使用PLC


# ========= 数据 =========
def load_presets():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_presets(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ========= PCA =========
def get_pca_direction(points):
    mean, eigenvectors = cv2.PCACompute(points, mean=None)
    return mean[0], eigenvectors[0]


# ========= 图像处理 =========
def process_image(path, p):
    img = cv2.imread(path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    canny = cv2.Canny(gray, p["canny_low"], p["canny_high"])
    gauss = cv2.GaussianBlur(canny, (p["ksize"], p["ksize"]), 0)
    _, binary = cv2.threshold(gauss, p["thresh"], 255,
                              cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    kernel = np.ones((p["kernel"], p["kernel"]), np.uint8)
    erosion = cv2.erode(binary, kernel)

    circles = cv2.HoughCircles(
        erosion, cv2.HOUGH_GRADIENT, 1.2, p["minDist"],
        param1=170, param2=30,
        minRadius=p["minRadius"], maxRadius=p["maxRadius"]
    )

    # 霍夫圆错误
    if circles is None:
        return img, "未检测到圆"

    x, y, r = np.uint16(np.around(circles))[0][0]

    mask = np.zeros(erosion.shape, dtype=np.uint8)
    cv2.circle(mask, (x, y), int(r * 1.05), 255, -1)
    roi = cv2.bitwise_and(erosion, erosion, mask=mask)

    contours, _ = cv2.findContours(roi, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    contour = max(contours, key=cv2.contourArea)

    points = contour.reshape(-1, 2).astype(np.float32)
    center, direction = get_pca_direction(points)

    angle = np.degrees(np.arctan2(direction[0], direction[1]))

    cv2.circle(img, (x, y), r, (0, 0, 255), 2)
    cv2.drawContours(img, [contour], -1, (0, 255, 0), 2)

    p1 = (x, y)
    p2 = (int(center[0] + 200 * direction[0]),
          int(center[1] + 200 * direction[1]))

    cv2.line(img, p1, p2, (0, 0, 255), 3)
    # 水平竖直参考线
    h, w = img.shape[:2]
    # 水平线（左→右）
    cv2.line(img, (0, y), (w, y), (255, 0, 0), 1)
    # 垂直线（上→下）
    cv2.line(img, (x, 0), (x, h), (255, 0, 0), 1)


    cv2.putText(img, f"{angle:.2f}", (40, 60),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    return img, f"偏移角度: {angle:.2f}"


# ========= GUI =========
class App:
    def __init__(self, root):
        self.root = root
        self.root.title("工件角度检测系统")
        self.root.geometry("1000x600")
        self.root.configure(bg="#ecf0f1")

        # 自动检测控制
        self.running = False


        self.presets = load_presets()
        self.image_path = None

        # ===== 左：图像区域（固定尺寸）=====
        left = tk.LabelFrame(root, text="图像显示",
                             width=520, height=520)
        left.pack(side="left", padx=10, pady=10)
        left.pack_propagate(False)

        self.image_label = tk.Label(left, bg="#dfe6e9")
        self.image_label.pack(fill="both", expand=True)

        # ===== 中：控制区 =====
        center = tk.Frame(root, bg="#ecf0f1")
        center.pack(side="left", padx=10, pady=10)

        param_frame = tk.LabelFrame(center, text="参数配置",
                                    padx=10, pady=10)
        param_frame.pack()

        self.entries = {}
        keys = ["canny_low", "canny_high", "ksize", "thresh",
                "kernel", "minDist", "minRadius", "maxRadius"]

        for i, k in enumerate(keys):
            tk.Label(param_frame, text=k, width=12, anchor="w")\
                .grid(row=i, column=0, pady=3)
            e = tk.Entry(param_frame, width=10)
            e.grid(row=i, column=1, pady=3)
            self.entries[k] = e

        btn_frame = tk.LabelFrame(center, text="操作", padx=10, pady=10)
        btn_frame.pack(pady=10)

        tk.Button(btn_frame, text="上传图片", width=12,
                  command=self.load_image).grid(row=0, column=0, pady=5)

        tk.Button(btn_frame, text="开始检测", width=12,
                  command=self.run).grid(row=0, column=1)

        tk.Button(btn_frame, text="保存预设", width=12,
                  command=self.save_current).grid(row=1, column=0, pady=5)

        tk.Button(btn_frame, text="删除预设", width=12,
                  bg="#e74c3c", fg="white",
                  command=self.delete_preset).grid(row=1, column=1)

        # =========================自动检测====================================

        tk.Button(btn_frame, text="自动检测", width= 12,
                  command=self.start_auto).grid(row=2, column=0, pady=5)
        tk.Button(btn_frame, text="停止", width= 12,
                  command=self.stop_auto).grid(row=2, column=1)

        # ====================================================================

        # =============================结果提示=================================
        self.result_label = tk.Label(center, text="结果在这里展示:",
                                     bg="#ecf0f1")
        self.result_label.pack()

        # 相机控制
        self.camera = tk.Label(center, text="当前使用相机名称",
                                     bg="#ecf0f1")
        self.camera.pack()
        # ===================================================================

        # ===== 右：预设列表（固定宽度）==========================================
        right = tk.LabelFrame(root, text="预设列表",
                              width=150)
        right.pack(side="right", padx=10, pady=15, fill="y")
        right.pack_propagate(False)

        self.listbox = tk.Listbox(right, font=("微软雅黑", 15))
        self.listbox.pack(fill="both", expand=True)

        self.refresh_listbox()
        self.listbox.bind("<<ListboxSelect>>", self.on_select_preset)




    # ===========================方法==========================================

    def start_auto(self):
        self.running = True
        self.auto_loop()

    def stop_auto(self):
        self.running = False


    # ===== 显示图片=====
    def show_image(self, img):
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(img)

        # 强制填满
        img = img.resize((500, 500))

        imgtk = ImageTk.PhotoImage(img)
        self.image_label.config(image=imgtk)
        self.image_label.image = imgtk

    def refresh_listbox(self):
        self.listbox.delete(0, tk.END)
        for name in self.presets:
            if name.strip():
                self.listbox.insert(tk.END, name)

    def on_select_preset(self, event):
        sel = self.listbox.curselection()
        if not sel:
            return

        name = self.listbox.get(sel[0])
        data = self.presets[name]

        # 获取相机
        self.cameraName = data["camera"]

        for k, v in data.items():
            if k in self.entries:  # 关键！
                self.entries[k].delete(0, tk.END)
                self.entries[k].insert(0, str(v))

    def get_params(self):
        return {k: int(e.get()) for k, e in self.entries.items()}

    def save_current(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("保存预设")
        dialog.geometry("350x250")  # ⭐ 想多大就多大


        tk.Label(dialog, text="输入名称:", font=("微软雅黑", 12)).pack(pady=10)

        entry = tk.Entry(dialog, font=("微软雅黑", 12), width=20)
        entry.pack(pady=5)
        entry.focus()

        tk.Label(dialog, text="相机配置路径:", font=("微软雅黑", 12)).pack(pady=10)
        camera_entry = tk.Entry(dialog, font=("微软雅黑", 12), width=20)
        camera_entry.pack(pady=5)

        def confirm():
            name = entry.get().strip()
            if not name:
                return

            data = self.get_params()
            data["camera"] = camera_entry.get().strip()

            self.presets[name] = data

            save_presets(self.presets)
            self.refresh_listbox()

            dialog.destroy()

        tk.Button(dialog, text="确定", width=10,
                  command=confirm).pack(pady=10)

    def delete_preset(self):
        sel = self.listbox.curselection()
        if not sel:
            return

        name = self.listbox.get(sel[0])
        if messagebox.askyesno("确认", f"删除 {name}?"):
            del self.presets[name]
            save_presets(self.presets)
            self.refresh_listbox()

    def load_image(self):
        path = filedialog.askopenfilename()
        if path:
            self.image_path = path
            img = cv2.imread(path)
            self.show_image(img)

    def run(self):
        if not self.image_path:
            self.result_label.config(text="请先上传图片")
            return

        img, text = process_image(self.image_path, self.get_params())
        self.show_image(img)
        self.result_label.config(text=text)
        self.camera.config(text=self.cameraName)


    # 自动流程
    def auto_loop(self):
        if not self.running:
            return

        # ===== 1. 相机获取 =====
        # cam1.TriggerOnce()
        # img = cam1.AcqImg()

        # ===================测试区域=============

        # ===== 0. 初始化图片列表（只初始化一次）=====
        if not hasattr(self, "test_images"):
            self.test_images = ["Test1.jpg", "Test3.jpg"]
            self.img_index = 0

        # ===== 1. 读取当前图片 =====
        img_path = self.test_images[self.img_index]

        # ========================================

        if img_path is not None:
            # ===== 2. 算法处理 =====
            data = self.get_params()
            result_img, angle = process_image(img_path, data)

            # ===== 3. 显示 =====
            self.show_image(result_img)
            self.result_label.config(text=angle)

            # ===== 4. 切换到下一张 =====
            self.img_index = (self.img_index + 1) % len(self.test_images)

        # ===== 5. 定时下一轮 =====
        self.root.after(2000, self.auto_loop)



# ========= 启动 =========
if __name__ == "__main__":

    # 初始化相机1
    # cam1 = Camera()
    # cam1.Open("Camera1.json")
    # cam1.SetExposureTime(300000)



    root = tk.Tk()
    root.iconbitmap("temp.ico")

    App(root)
    root.mainloop()