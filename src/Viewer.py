import sys
import cv2
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel,
    QHBoxLayout, QVBoxLayout, QFrame
)
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtCore import Qt, QThread, Signal


# ================= 相机线程 =================
class CameraThread(QThread):
    image_signal = Signal(object, str)  # (图像, 左右标识)

    def __init__(self):
        super().__init__()
        self.running = True

    def run(self):
        cap = cv2.VideoCapture(0)

        while self.running:
            ret, frame = cap.read()
            if not ret:
                continue

            # 模拟左右不同处理
            left_img = frame
            right_img = cv2.Canny(frame, 100, 200)

            self.image_signal.emit(left_img, "left")
            self.image_signal.emit(right_img, "right")

        cap.release()

    def stop(self):
        self.running = False
        self.wait()


# ================= 单个相机面板 =================
class CameraPanel(QFrame):
    def __init__(self, title):
        super().__init__()

        self.setFrameShape(QFrame.Box)

        # 标题
        self.title_label = QLabel(title)
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("font-size:16px; font-weight:bold;")

        # 图像
        self.image_label = QLabel("等待图像...")
        self.image_label.setAlignment(Qt.AlignCenter)

        layout = QVBoxLayout()
        layout.addWidget(self.title_label)
        layout.addWidget(self.image_label)

        self.setLayout(layout)

    def set_image(self, img):
        if img is None:
            return

        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        h, w, ch = img_rgb.shape
        bytes_per_line = ch * w

        qimg = QImage(img_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qimg)

        self.image_label.setPixmap(
            pixmap.scaled(self.image_label.size(), Qt.KeepAspectRatio)
        )


# ================= 主窗口 =================
class CameraWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("双相机检测界面")
        self.resize(900, 500)

        # 左右面板
        self.left_panel = CameraPanel("左侧相机处理结果")
        self.right_panel = CameraPanel("右侧相机处理结果")

        layout = QHBoxLayout()
        layout.addWidget(self.left_panel)
        layout.addWidget(self.right_panel)

        self.setLayout(layout)

        # 启动线程
        self.thread = CameraThread()
        self.thread.image_signal.connect(self.show_image)
        self.thread.start()

    def show_image(self, img, side):
        if side == "left":
            self.left_panel.set_image(img)
        else:
            self.right_panel.set_image(img)

    # 关键：关闭时停止线程
    def closeEvent(self, event):
        self.thread.stop()
        event.accept()


# ================= 主函数 =================
if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = CameraWindow()
    window.show()

    sys.exit(app.exec())