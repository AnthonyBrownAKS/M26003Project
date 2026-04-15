import cv2;
import numpy as np
from itertools import combinations

# 工件1

# PCA
def get_pca_direction(points):
    mean, eigenvectors = cv2.PCACompute(points, mean=None)

    center = mean[0]
    direction = eigenvectors[0]

    return center, direction


def print_hi(path):

    # 初始处理
    img = cv2.imread(path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    canny = cv2.Canny(gray, 180, 200)
    gauss = cv2.GaussianBlur(canny, (9, 9), 0)
    ret1, binary_otsu = cv2.threshold(gauss, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    kernel = np.ones((3, 3), np.uint8)
    erosion = cv2.dilate(binary_otsu, kernel)

    # ----------------------------------------------------------------------------------------------

    # 霍夫圆检测
    circles = cv2.HoughCircles(
        erosion,
        cv2.HOUGH_GRADIENT,
        dp=1.2,  # 分辨率比例
        minDist=1000,  # 圆心最小间距
        param1=170,  # Canny高阈值
        param2=30,  # 圆检测阈值（越小越容易检测到）
        minRadius=300,  # 最小半径
        maxRadius=500  # 最大半径
    )

    # 绘制霍夫圆找寻结果
    if circles is not None:
        circles = np.uint16(np.around(circles))
        for x, y, r in circles[0, :]:
            # 画圆
            cv2.circle(img, (x, y), r, (0, 0, 255), 2)
            # 画圆心
            cv2.circle(img, (x, y), 2, (0, 0, 255), 3)

    # ------------------------------------------------------------------------------
    # 获取圆心坐标半径
    cx = circles[0, 0][0]
    cy = circles[0, 0][1]
    r = circles[0, 0][2]

    # 建mask（只保留圆附近）-> ROI区域
    mask = np.zeros(erosion.shape[:2], dtype=np.uint8)
    cv2.circle(mask, (cx, cy), int(r * 1.05), 255, -1)
    roi = cv2.bitwise_and(erosion, erosion, mask=mask)
    cv2.imshow("轮廓区域", roi)

    # 找轮廓
    contours, _ = cv2.findContours(roi, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)

    # 取最大轮廓
    contour = max(contours, key=cv2.contourArea)

    # PCA
    points = contour.reshape(-1, 2).astype(np.float32)
    center, direction = get_pca_direction(points)

    # 计算
    angle = np.degrees(np.arctan2(direction[0], direction[1]))

    print("偏移角度:", angle)


    # 画轮廓
    cv2.drawContours(img, [contour], -1, (0, 255, 0), 2)

    # 画主方向
    p1 = (int(center[0]), int(center[1]))
    p2 = (int(center[0] + 200 * direction[0]),
          int(center[1] + 200 * direction[1]))

    cv2.line(img, p1, p2, (0, 0, 255), 3)
    cv2.putText(img,f"{angle}" ,(200, 200), 0, 1, (0, 255, 0), 2, 1)

    # 展示
    cv2.namedWindow("result", cv2.WINDOW_NORMAL)
    cv2.imshow("result", img)

    cv2.waitKey(0)


# 按装订区域中的绿色按钮以运行脚本。
if __name__ == '__main__':
    print_hi("camImg/Test1.jpg")