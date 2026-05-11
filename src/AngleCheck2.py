import cv2
import numpy as np
import os


def resizeImg(img, scale_percent=50):
    width = int(img.shape[1] * scale_percent / 100)
    height = int(img.shape[0] * scale_percent / 100)
    return cv2.resize(img, (width, height), interpolation=cv2.INTER_AREA)


def process_image(img):
    cv2.imwrite(r"D:\M26003Project\src\logs\Results\0Origin.jpg", img)
    try:
        if img is None:
            raise ValueError("输入图像为空！")

        # ===== 灰度 =====
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # ===== 去噪 =====
        median = cv2.medianBlur(gray, 3)

        # ===== 边缘 =====
        canny = cv2.Canny(median, 20, 80)
        cv2.imwrite(r"D:\M26003Project\src\logs\Results\1canny.jpg", canny)

        # ===== 二值 =====
        _, binary = cv2.threshold(
            canny, 0, 255,
            cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )
        cv2.imwrite(r"D:\M26003Project\src\logs\Results\2binary.jpg", binary)

        # ===== 膨胀 =====
        kernel = np.ones((15, 15), np.uint8)
        dilation = cv2.dilate(binary, kernel)
        cv2.imwrite(r"D:\M26003Project\src\logs\Results\3dilation.jpg", dilation)

        # ===== 找圆 =====
        circles = cv2.HoughCircles(
            dilation, cv2.HOUGH_GRADIENT, 2, minDist=100,
            param1=100, param2=30,
            minRadius=700, maxRadius=800
        )

        if circles is None:
            raise ValueError("未检测到圆！")

        x, y, r = np.uint16(np.around(circles))[0][0]

        inv = cv2.bitwise_not(dilation)

        # ===== ROI（只保留圆区域）=====
        mask = np.zeros(inv.shape, dtype=np.uint8)
        cv2.circle(mask, (x, y), int(r * 0.90), 255, -1)
        roi = cv2.bitwise_and(inv, inv, mask=mask)

        cv2.circle(roi, (int(x), int(y)), int(r * 0.70), (0, 0, 0), -1)

        cv2.imwrite(r"D:\M26003Project\src\logs\Results\4roi.jpg", roi)

        # ===== 轮廓 =====
        contours, _ = cv2.findContours(
            roi, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE
        )

        if not contours:
            raise ValueError("未找到轮廓")

        contour = max(contours, key=cv2.contourArea)

        cv2.drawContours(img, [contour], -1, (0, 255, 0), 2)
        cv2.imwrite(r"D:\M26003Project\src\logs\Results\5contours.jpg", img)

        # ===== 轮廓点 =====
        points = contour.reshape(-1, 2)
        center_pt = np.array([x, y])

        # ===== 距离 =====
        distances = np.linalg.norm(points - center_pt, axis=1)

        # ===== 主半径 =====
        r_mean = np.median(distances)

        # ===== 找凸起（核心）=====
        # 方法1：固定阈值
        # threshold = r_mean * 1.02
        # mask = distances > threshold

        # 取最远的2%
        max_dist = np.max(distances)
        mask = distances > max_dist * 0.995

        protrusion_points = points[mask]

        if len(protrusion_points) < 10:
            raise ValueError("未检测到凸起")

        # ===== 凸起中心 =====
        protrusion_center = np.mean(protrusion_points, axis=0)

        # ===== 方向 =====
        direction = protrusion_center - center_pt

        dx = direction[0]
        dy = direction[1]

        # ⚠️ 注意你原来的角度定义（y轴向下为0）
        angle = np.degrees(np.arctan2(dx, dy))


        # ===== 可视化 =====
        # 圆
        cv2.circle(img, (x, y), r, (0, 0, 255), 2)

        # 凸起点（绿色）
        for p in protrusion_points:
            cv2.circle(img, tuple(p), 1, (0, 255, 0), -1)

        # 凸起中心（蓝）
        cv2.circle(img, tuple(protrusion_center.astype(int)), 8, (255, 0, 0), -1)

        # 方向线（红）
        p2 = (int(x + 200 * direction[0]),
              int(y + 200 * direction[1]))
        cv2.line(img, (x, y), p2, (0, 0, 255), 5)

        # 十字参考线
        h, w = img.shape[:2]
        cv2.line(img, (0, y), (w, y), (255, 0, 0), 3)
        cv2.line(img, (x, 0), (x, h), (255, 0, 0), 3)

        # 角度显示
        cv2.putText(img, f"{angle:.2f}", (100, 120),
                    cv2.FONT_HERSHEY_SIMPLEX, 5, (0, 255, 0), 5)

        print(f"角度: {angle:.2f}")

        cv2.imwrite(r"D:\M26003Project\src\logs\Results\6result.jpg", img)

        return img, round(angle, 2)

    except Exception as e:
        raise RuntimeError(f"图像处理失败，异常报告: {e}")


if __name__ == "__main__":
    path = r"D:\M26003Project\camImg\Left\20260508_123857_Left.jpg"

    if not os.path.exists(path):
        raise FileNotFoundError(f"文件不存在: {path}")

    img = cv2.imread(path)

    result_img, angle = process_image(img)