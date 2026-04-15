import cv2
import numpy as np
import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox
from PIL import Image, ImageTk
import json, os

DATA_FILE = "data.json"


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


# ========= 核心检测 =========
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

    p1 = tuple(center.astype(int))
    p2 = (int(center[0] + 200 * direction[0]),
          int(center[1] + 200 * direction[1]))

    cv2.line(img, p1, p2, (0, 0, 255), 3)
    cv2.putText(img, f"{angle:.2f}", (40, 60),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    return img, f"偏移角度: {angle:.2f}"


# ========= GUI =========
class App:
    def __init__(self, root):
        self.root = root
        self.root.title("工件角度检测系统")
        self.root.geometry("900x550")

        self.presets = load_presets()
        self.current_preset = ""
        self.image_path = None

        # ===== 左侧图像区 =====
        left_frame = tk.Frame(root, bg="#2c3e50", width=520, height=520)
        left_frame.pack(side="left", padx=10, pady=10)
        left_frame.pack_propagate(False)

        self.image_label = tk.Label(
            left_frame, text="暂无图片",
            bg="#34495e", fg="white",
            font=("Arial", 14)
        )
        self.image_label.place(relx=0.5, rely=0.5, anchor="center")

        # ===== 右侧控制区 =====
        right = tk.Frame(root, bg="#ecf0f1")
        right.pack(side="right", fill="both", expand=True)

        # 标题
        tk.Label(right, text="参数控制",
                 font=("Arial", 16, "bold"),
                 bg="#ecf0f1").pack(pady=10)

        # 当前预设
        self.preset_label = tk.Label(
            right, text="当前预设: 无",
            fg="#2980b9", bg="#ecf0f1",
            font=("Arial", 12, "bold"))
        self.preset_label.pack()

        # 下拉框
        self.preset_var = tk.StringVar()
        self.menu = tk.OptionMenu(
            right, self.preset_var, *self.presets.keys(),
            command=self.load_preset)
        self.menu.pack(pady=5)

        # 参数区域
        self.entries = {}
        params_frame = tk.Frame(right, bg="#ecf0f1")
        params_frame.pack()

        keys = ["canny_low", "canny_high", "ksize", "thresh",
                "kernel", "minDist", "minRadius", "maxRadius"]

        for i, k in enumerate(keys):
            tk.Label(params_frame, text=k, bg="#ecf0f1").grid(row=i, column=0)
            e = tk.Entry(params_frame, width=10)
            e.grid(row=i, column=1)
            self.entries[k] = e

        # 按钮区
        btn_frame = tk.Frame(right, bg="#ecf0f1")
        btn_frame.pack(pady=10)

        tk.Button(btn_frame, text="上传图片", width=12,
                  command=self.load_image).grid(row=0, column=0, padx=5)

        tk.Button(btn_frame, text="开始检测", width=12,
                  command=self.run).grid(row=0, column=1, padx=5)

        tk.Button(btn_frame, text="保存预设", width=12,
                  command=self.save_current).grid(row=1, column=0, pady=5)

        tk.Button(btn_frame, text="删除预设", width=12,
                  command=self.delete_preset, bg="#e74c3c", fg="white").grid(row=1, column=1, pady=5)

        self.result_label = tk.Label(right, text="偏移结果:",
                                     bg="#ecf0f1", font=("Arial", 12))
        self.result_label.pack(pady=10)

    # ===== 显示图片 =====
    def show_image(self, img):
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(img)
        img.thumbnail((500, 500))

        imgtk = ImageTk.PhotoImage(img)
        self.image_label.config(image=imgtk, text="")
        self.image_label.image = imgtk

    # ===== 加载预设 =====
    def load_preset(self, name):
        self.current_preset = name
        self.preset_label.config(text=f"当前预设: {name}")

        for k, v in self.presets[name].items():
            self.entries[k].delete(0, tk.END)
            self.entries[k].insert(0, str(v))

    # ===== 获取参数 =====
    def get_params(self):
        return {k: int(e.get()) for k, e in self.entries.items()}

    # ===== 保存 =====
    def save_current(self):
        name = simpledialog.askstring("保存预设", "输入名称:")
        if not name:
            return

        self.presets[name] = self.get_params()
        save_presets(self.presets)

        self.refresh_menu()
        self.preset_label.config(text=f"当前预设: {name}")

    # ===== 删除预设 =====
    def delete_preset(self):
        name = self.preset_var.get()
        if not name:
            messagebox.showinfo("提示", "请选择预设")
            return

        if messagebox.askyesno("确认", f"删除 {name}?"):
            del self.presets[name]
            save_presets(self.presets)
            self.refresh_menu()
            self.preset_label.config(text="当前预设: 无")

    # ===== 刷新菜单 =====
    def refresh_menu(self):
        menu = self.menu["menu"]
        menu.delete(0, "end")
        for k in self.presets:
            menu.add_command(label=k,
                             command=lambda v=k: self.load_preset(v))

    # ===== 上传 =====
    def load_image(self):
        path = filedialog.askopenfilename()
        if path:
            self.image_path = path
            img = cv2.imread(path)
            self.show_image(img)

    # ===== 检测 =====
    def run(self):
        if not self.image_path:
            self.result_label.config(text="请先选择图片")
            return

        img, text = process_image(self.image_path, self.get_params())
        self.show_image(img)
        self.result_label.config(text=text)


# ========= 启动 =========
if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()