import cv2
import numpy as np
import os

import math
import cv2

def check_safe_range(img, x, y, cx, cy, safe_radius):
    """
    (x, y): 当前点（你已有）
    (cx, cy): 圆心
    safe_radius: 安全半径
    """

    # ===== 计算距离 =====
    dist = math.hypot(x - cx, y - cy)

    # ===== 画安全范围（圆）=====
    vis = img.copy()
    cv2.circle(vis, (int(cx), int(cy)), int(safe_radius), (0, 255, 0), 2)

    # 画中心点
    cv2.circle(vis, (int(cx), int(cy)), 6, (255, 0, 0), -1)

    # 画检测点
    cv2.circle(vis, (int(x), int(y)), 6, (0, 0, 255), -1)

    # 连线（方便看偏移）
    cv2.line(vis, (int(cx), int(cy)), (int(x), int(y)), (255, 255, 0), 2)

    cv2.imwrite("test1.jpg", vis)

    # ===== 判断是否越界 =====
    if dist > safe_radius:
        cv2.putText(vis, "OUT OF RANGE", (50, 100),
                    cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 4)

        cv2.imshow("safe_check", vis)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

        raise ValueError("超过安全范围")

    else:
        cv2.putText(vis, "SAFE", (50, 100),
                    cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 255, 0), 4)

        cv2.imshow("safe_check", vis)
        cv2.waitKey(0)
        cv2.destroyAllWindows()



    return True

# 角度检测

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
        median = cv2.medianBlur(gray, 7)

        # ===== 边缘 =====
        canny = cv2.Canny(median, 100, 200)
        cv2.imwrite(r"D:\M26003Project\src\logs\Results\1canny.jpg", canny)

        # ===== 二值 =====
        _, binary = cv2.threshold(
            canny, 0, 255,
            cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )
        cv2.imwrite(r"D:\M26003Project\src\logs\Results\2binary.jpg", binary)

        # ===== 膨胀（你原来写成 erosion 其实是 dilate）=====
        kernel = np.ones((11, 11), np.uint8)
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

        # check_safe_range(img, x, y, 1430, 1050, 300)

        inv = cv2.bitwise_not(dilation)

        # ===== ROI（只保留圆区域）=====
        mask = np.zeros(inv.shape, dtype=np.uint8)
        cv2.circle(mask, (x, y), int(r * 0.93), 255, -1)
        roi = cv2.bitwise_and(inv, inv, mask=mask)

        # cv2.circle(roi, (int(x), int(y)), int(r * 0.70), (0, 0, 0), -1)

        cv2.imwrite(r"D:\M26003Project\src\logs\Results\4roi.jpg", roi)


        print(f"当前半径：{r}")


        # ===== 轮廓 =====
        contours, _ = cv2.findContours(
            roi, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE
        )

        if not contours:
            raise ValueError("未找到轮廓")

        contour = max(contours, key=cv2.contourArea)

        # ===== 轮廓点 =====
        points = contour.reshape(-1, 2)
        center_pt = np.array([x, y])

        # ===== 距离 =====
        distances = np.linalg.norm(points - center_pt, axis=1)

        # ===== 主半径（用中位数更稳）=====
        r_mean = np.median(distances)

        # ===== 找“明显凹进去”的点 =====
        threshold = r_mean * 0.98  # 这个很关键（0.95~0.98调）
        mask = distances < threshold

        notch_points = points[mask]

        # 防止没检测到
        if len(notch_points) < 10:
            raise ValueError("未检测到缺口")

        # ===== 求缺口中心 =====
        notch_center = np.mean(notch_points, axis=0)

        # ===== 方向 =====
        direction = notch_center - center_pt

        # ===== 角度 =====
        dx = direction[0]
        dy = direction[1]

        angle = np.degrees(np.arctan2(dx, dy))

        # 角度优化
        # if angle < 0:
        #     angle += 360

        # ===== 画图 =====
        # 圆
        cv2.circle(img, (x, y), r, (0, 0, 255), 2)

        # 轮廓
        cv2.drawContours(img, [contour], -1, (0, 255, 0), 2)

        # 方向线（红）
        p1 = (x, y)
        p2 = (int(x + 200 * direction[0]),
              int(y + 200 * direction[1]))
        cv2.line(img, p1, p2, (0, 0, 255), 5)

        # 十字参考线
        h, w = img.shape[:2]
        cv2.line(img, (0, y), (w, y), (255, 0, 0), 3)
        cv2.line(img, (x, 0), (x, h), (255, 0, 0), 3)

        # 角度显示
        cv2.putText(img, f"{angle:.2f}", (100, 120),
                    cv2.FONT_HERSHEY_SIMPLEX, 5, (0, 255, 0), 5)

        # 缺口点（绿色）
        for p in notch_points:
            cv2.circle(img, tuple(p), 1, (0, 255, 0), -1)

        # 缺口中心（蓝）
        cv2.circle(img, tuple(notch_center.astype(int)), 8, (255, 0, 0), -1)

        # 方向线（红）
        p2 = (int(x + 200 * direction[0]),
              int(y + 200 * direction[1]))
        cv2.line(img, (x, y), p2, (0, 0, 255), 3)

        print(f"角度: {angle:.2f}")

        # if angle > 10 or angle < -35:
        #     cv2.imwrite(r"D:\M26003Project\tmp\right.jpg", img)
        #     raise ValueError("角度偏移过大")

        cv2.imwrite(r"D:\M26003Project\src\logs\Results\6result.jpg",img)

        return img, round(angle, 2)

    except Exception as e:

        raise RuntimeError(f"图像处理失败，异常报告: {e}")




if __name__ == "__main__":
    path = r"D:\M26003Project\camImg\Right\20260508_143726_Right.jpg"

    if not os.path.exists(path):
        raise FileNotFoundError(f"文件不存在: {path}")

    img = cv2.imread(path)

    result_img, angle = process_image(img)
