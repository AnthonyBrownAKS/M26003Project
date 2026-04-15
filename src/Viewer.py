import tkinter as tk
import cv2
from PIL import Image, ImageTk


class CameraWindow:
    def __init__(self):
        self.root = tk.Toplevel()
        self.root.title("处理结果监测界面")
        self.root.geometry("900x500")

        # 左右面板
        self.left_label = self.create_panel("左侧相机处理结果")
        self.right_label = self.create_panel("右侧相机处理结果")

        self.left_label.pack(side="left", expand=True, fill="both", padx=10, pady=10)
        self.right_label.pack(side="right", expand=True, fill="both", padx=10, pady=10)

    def create_panel(self, title):
        frame = tk.Frame(self.root, bd=2, relief="groove")

        title_label = tk.Label(frame, text=title, font=("微软雅黑", 14))
        title_label.pack()

        img_label = tk.Label(frame, text="等待图像...", bg="#dfe6e9")
        img_label.pack(expand=True, fill="both")

        frame.image_label = img_label  # 绑定属性
        return frame

    def set_image(self, img, side):
        if img is None:
            return

        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(img)
        img = img.resize((400, 400))

        imgtk = ImageTk.PhotoImage(img)

        if side == "left":
            self.left_label.image_label.config(image=imgtk)
            self.left_label.image_label.image = imgtk
        else:
            self.right_label.image_label.config(image=imgtk)
            self.right_label.image_label.image = imgtk

    #  线程安全入口
    def safe_update(self, img, side):
        self.root.after(0, lambda: self.update_image(img, side))


