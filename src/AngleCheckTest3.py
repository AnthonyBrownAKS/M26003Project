import cv2
import numpy as np
import os
import math


# 角度检测

def resizeImg(img, scale_percent=50):
    width = int(img.shape[1] * scale_percent / 100)
    height = int(img.shape[0] * scale_percent / 100)
    return cv2.resize(img, (width, height), interpolation=cv2.INTER_AREA)


def checkLine(cx, cy, angle, vis):
    cx, cy = int(cx), int(cy)
    angle = float(angle)

    # 转弧度
    theta = math.radians(angle)

    # 方向向量（根据你的角度定义）
    dx = math.sin(theta)
    dy = math.cos(theta)

    # 线长度（足够长，贯穿整张图）
    h, w = vis.shape[:2]
    length = max(h, w)

    # 两个方向延伸
    x1 = int(cx - dx * length)
    y1 = int(cy + dy * length)

    x2 = int(cx + dx * length)
    y2 = int(cy - dy * length)

    # 画线
    cv2.line(vis, (x1, y1), (x2, y2), (0, 0, 255), 2)

    # cv2.imshow("line", resizeImg(vis))
    # cv2.waitKey(0)
    # cv2.destroyAllWindows()


def far_point_mean(contour, center, ratio=0.3):
    """
    ratio: 选取最远的前多少比例点
    """

    pts = contour[:, 0, :]

    # 1. 计算每个点到圆心距离
    dists = np.linalg.norm(pts - center, axis=1)

    # 2. 排序索引（从远到近）
    idx = np.argsort(dists)[::-1]

    # 3. 取最远的一部分点
    k = max(1, int(len(pts) * ratio))
    far_pts = pts[idx[:k]]

    # 4. 求均值
    mean_point = np.mean(far_pts, axis=0).astype(int)

    return mean_point, far_pts


def process_image(img):
    try:
        if img is None:
            raise ValueError("输入图像为空！")

        # ===== 灰度 =====
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # ===== 去噪 =====
        median = cv2.medianBlur(gray, 3)

        # ===== 边缘 =====
        canny = cv2.Canny(median, 20, 80)
        # cv2.imshow("canny", resizeImg(canny))
        # cv2.namedWindow("canny", cv2.WINDOW_NORMAL)
        # cv2.waitKey(0)

        # ===== 二值 =====
        _, binary = cv2.threshold(
            canny, 0, 255,
            cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )
        # cv2.imshow("binary", resizeImg(binary))
        # cv2.namedWindow("binary", cv2.WINDOW_NORMAL)
        # cv2.waitKey(0)

        # ===== 膨胀 =====
        dilation = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel=np.ones((11, 11), np.uint8))

        # cv2.imshow("dilation", resizeImg(dilation))
        # cv2.namedWindow("dilation", cv2.WINDOW_NORMAL)
        # cv2.waitKey(0)

        # ===== 找圆 =====
        circles = cv2.HoughCircles(
            dilation, cv2.HOUGH_GRADIENT, 2, minDist=100,
            param1=100, param2=30,
            minRadius=400, maxRadius=600
        )

        if circles is None:
            raise ValueError("未检测到圆！")

        x, y, r = np.uint16(np.around(circles))[0][0]

        # ===== ROI（只保留圆区域）=====
        inv = cv2.bitwise_not(dilation)

        # =====划定核心区域=====
        mask = np.zeros(inv.shape, dtype=np.uint8)
        cv2.circle(mask, (x, y), int(r * 1.15), 255, -1)
        roi = cv2.bitwise_and(inv, inv, mask=mask)

        cv2.circle(img, (x, y), r, (0, 0, 255), 2)

        # ====获得凸出部分=====
        cv2.circle(roi, (int(x), int(y)), int(r * 1.01), (0, 0, 0), -1)

        # ===== 轮廓 =====
        contours, _ = cv2.findContours(
            roi, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE
        )

        contour = max(contours, key=cv2.contourArea)

        # =====最小外接矩形=====
        rect = cv2.minAreaRect(contour)
        (cx, cy), (w, h), rect_angle = rect

        if w < h:
            rect_angle += 90

        # 计算角度
        theta = np.radians(rect_angle)

        # 注意：你的角度体系（0°向下）
        vx = np.sin(theta)
        vy = np.cos(theta)

        center = np.array([x, y])

        pos_score = 0
        neg_score = 0

        for p in contour[:, 0, :]:
            v = p - center

            # 投影到方向轴
            proj = v[0] * vx + v[1] * vy

            dist = np.linalg.norm(v)

            if proj > 0:
                pos_score += dist
            else:
                neg_score += dist

        # 判断哪一侧更突出
        if neg_score > pos_score:
            rect_angle += 180

        angle = rect_angle % 360


        # # 获取四个点
        box = cv2.boxPoints(rect)
        #
        # # ⚠️ 关键：必须转 int
        box = box.astype(int)

        # # 计算角度（可选）
        # dx = box[1][0] - box[0][0]
        # dy = box[1][1] - box[0][1]
        # angle = np.degrees(np.arctan2(dy, dx))

        # 画出来
        cv2.drawContours(img, [box], 0, (255, 0, 0), 2)

        cv2.drawContours(img, [contour], -1, (0, 255, 0), 2)

        # cv2.imshow("roi", resizeImg(roi))
        # cv2.namedWindow("roi", cv2.WINDOW_NORMAL)
        # cv2.waitKey(0)

        # cv2.imshow("img", resizeImg(img))
        # cv2.namedWindow("img", cv2.WINDOW_NORMAL)
        # cv2.waitKey(0)

        checkLine(x, y, angle, img)

        angle = -angle
        # 显示角度
        cv2.putText(img, f"{angle:.2f}", (100, 120),
                    cv2.FONT_HERSHEY_SIMPLEX, 5, (0, 255, 0), 5)

        # 十字参考线
        h, w = img.shape[:2]
        cv2.line(img, (0, y), (w, y), (255, 0, 0), 3)
        cv2.line(img, (x, 0), (x, h), (255, 0, 0), 3)

        return img, round(angle, 2)

    except Exception as e:
        raise RuntimeError(f"图像处理失败，异常报告: {e}")


if __name__ == "__main__":
    path = r"D:\M26003Project\camImg\Left\50.jpg"

    if not os.path.exists(path):
        raise FileNotFoundError(f"文件不存在: {path}")

    img = cv2.imread(path)


    result_img, angle = process_image(img)

    cv2.imwrite(r"D:\M26003Project\tmp\test.jpg", result_img)
