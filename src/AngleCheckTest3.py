import cv2
import numpy as np
import os
from sklearn.cluster import KMeans


def resizeImg(img, scale=50):
    h, w = img.shape[:2]
    return cv2.resize(img, (int(w*scale/100), int(h*scale/100)))


def process_image(img):
    if img is None:
        raise ValueError("图像为空")

    # ===== 1. 灰度增强（黑色工件关键）=====
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(3.0, (8, 8))
    gray = clahe.apply(gray)

    blur = cv2.GaussianBlur(gray, (5, 5), 0)

    # ===== 2. 边缘 =====
    canny = cv2.Canny(blur, 50, 120)

    kernel = np.ones((5, 5), np.uint8)
    canny = cv2.dilate(canny, kernel)

    # ===== 3. 找轮廓 =====
    contours, _ = cv2.findContours(
        canny, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE
    )

    contours = [c for c in contours if cv2.contourArea(c) > 2000]

    if not contours:
        return img, "未找到轮廓"

    contour = max(contours, key=cv2.contourArea)

    # ===== 4. 求圆心（最小外接圆）=====
    (cx, cy), r = cv2.minEnclosingCircle(contour)
    center = np.array([cx, cy])

    # ===== 5. 轮廓点 =====
    points = contour.reshape(-1, 2)

    # ===== 6. 距离分布 =====
    distances = np.linalg.norm(points - center, axis=1)
    r_mean = np.median(distances)

    # ===== 7. 内外异常点（关键）=====
    outer_mask = distances > r_mean * 1.03   # 外凸
    inner_mask = distances < r_mean * 0.97   # 内嵌

    candidate_mask = outer_mask | inner_mask
    candidate_points = points[candidate_mask]

    if len(candidate_points) < 30:
        return img, "未检测到长方形"

    # ===== 8. 聚类（分离长方形区域）=====
    kmeans = KMeans(n_clusters=2, random_state=0).fit(candidate_points)
    labels = kmeans.labels_

    counts = np.bincount(labels)
    target_label = np.argmax(counts)

    rect_points = candidate_points[labels == target_label]

    # ===== 9. 求中心（推荐用最小外接矩形）=====
    rect = cv2.minAreaRect(rect_points.astype(np.float32))
    rect_center = np.array(rect[0])

    box = cv2.boxPoints(rect)
    box = np.int32(box)

    # ===== 10. 可视化 =====
    draw = img.copy()

    # 轮廓
    cv2.drawContours(draw, [contour], -1, (0, 255, 0), 2)

    # 圆心
    cv2.circle(draw, (int(cx), int(cy)), 6, (255, 255, 0), -1)

    # 候选点（黄）
    for p in candidate_points:
        cv2.circle(draw, tuple(p), 1, (0, 255, 255), -1)

    # 长方形点（红）
    for p in rect_points:
        cv2.circle(draw, tuple(p), 1, (0, 0, 255), -1)

    # 外接矩形
    cv2.drawContours(draw, [box], 0, (255, 0, 255), 2)

    # 中心点（蓝）
    cv2.circle(draw, tuple(rect_center.astype(int)), 10, (255, 0, 0), -1)

    # 连线（用于方向观察）
    p2 = (int(cx + 200 * (rect_center[0] - cx)),
          int(cy + 200 * (rect_center[1] - cy)))
    cv2.line(draw, (int(cx), int(cy)), p2, (0, 255, 255), 2)

    # 显示
    cv2.imshow("canny", resizeImg(canny))
    cv2.imshow("result", resizeImg(draw))
    cv2.waitKey(0)

    return draw, rect_center


if __name__ == "__main__":
    path = r"D:\M26003Project\camImg\right\20260418_160759_Right.jpg"

    if not os.path.exists(path):
        raise FileNotFoundError("图片不存在")

    img = cv2.imread(path)

    result, center = process_image(img)

    print("长方形中心:", center)