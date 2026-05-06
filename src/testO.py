import cv2
import numpy as np
import os


def process_image(img):
    cv2.imwrite(r"D:\M26003Project\src\logs\Results\0Origin.jpg", img)
    try:
        if img is None:
            raise ValueError("输入图像为空！")

        # ===== 灰度 =====
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # ===== 去噪 =====
        median = cv2.medianBlur(gray, 5)

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
        center_pt = np.array([x, y])

        inv = cv2.bitwise_not(dilation)

        # ===== ROI =====
        mask = np.zeros(inv.shape, dtype=np.uint8)
        cv2.circle(mask, (x, y), int(r * 0.96), 255, -1)
        roi = cv2.bitwise_and(inv, inv, mask=mask)


        cv2.circle(roi, (int(x), int(y)), int(r * 0.93), (0, 0, 0), -1)

        cv2.imwrite(r"D:\M26003Project\src\logs\Results\4roi.jpg", roi)



        # ===== 轮廓 =====
        contours, _ = cv2.findContours(
            roi, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE
        )

        if not contours:
            raise ValueError("未找到轮廓")

        contour = max(contours, key=cv2.contourArea)
        points = contour.reshape(-1, 2)

        # ===== 极坐标角度 =====
        angles = np.degrees(np.arctan2(
            points[:, 1] - center_pt[1],
            points[:, 0] - center_pt[0]
        ))

        # 转 0~360
        angles = (angles + 360) % 360

        # ===== 角度直方图 =====
        hist, _ = np.histogram(angles, bins=360, range=(0, 360))

        # ===== 找空区间 =====
        threshold = 2  # 每个角度最少点数
        empty = hist < threshold

        # ===== 找最长连续空段（环形处理）=====
        max_len = 0
        start = -1
        cur_len = 0
        cur_start = 0

        for i in range(len(empty) * 2):
            idx = i % 360

            if empty[idx]:
                if cur_len == 0:
                    cur_start = i
                cur_len += 1

                if cur_len > max_len:
                    max_len = cur_len
                    start = cur_start
            else:
                cur_len = 0

        if max_len < 5:
            raise ValueError("未检测到明显断裂")

        # ===== 断裂中心角度 =====
        gap_center_angle = (start + max_len / 2) % 360

        # ===== 转方向向量 =====
        rad = np.radians(gap_center_angle)

        dx = np.cos(rad)
        dy = np.sin(rad)

        # ⚠️ 如果你要“y轴向下为0度”，用这个：
        angle = np.degrees(np.arctan2(dx, dy))

        # ===== 可视化 =====
        cv2.drawContours(img, [contour], -1, (0, 255, 0), 2)

        # 圆
        cv2.circle(img, (x, y), r, (0, 0, 255), 2)

        # 方向线
        p2 = (int(x + 700 * dx), int(y + 700 * dy))
        cv2.line(img, (x, y), p2, (0, 0, 255), 5)

        # 十字
        h, w = img.shape[:2]
        cv2.line(img, (0, y), (w, y), (255, 0, 0), 3)
        cv2.line(img, (x, 0), (x, h), (255, 0, 0), 3)

        # 显示角度
        cv2.putText(img, f"{angle:.2f}", (100, 120),
                    cv2.FONT_HERSHEY_SIMPLEX, 5, (0, 255, 0), 5)

        print(f"断裂角度: {angle:.2f}")

        return img, round(angle, 2)

    except Exception as e:
        raise RuntimeError(f"图像处理失败，异常报告: {e}")


if __name__ == "__main__":
    path = r"D:\M26003Project\camImg\Left\6.jpg"

    if not os.path.exists(path):
        raise FileNotFoundError(f"文件不存在: {path}")

    img = cv2.imread(path)

    result_img, angle = process_image(img)

    cv2.imwrite(r"D:\M26003Project\src\logs\Results\6result.jpg", result_img)
