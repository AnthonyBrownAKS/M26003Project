import cv2;
import numpy as np
from itertools import combinations

# 工件2

def farthest_two_points(circles):
    # ===== 1. 取半径最大的3个圆 =====
    circles = sorted(circles, key=lambda c: c[2], reverse=True)[:3]

    max_dist = -1
    best_pair = None

    # ===== 2. 两两计算距离（只用x,y）=====
    for c1, c2 in combinations(circles, 2):
        x1, y1, _ = c1
        x2, y2, _ = c2

        dx = x1 - x2
        dy = y1 - y2

        dist2 = dx * dx + dy * dy  # 不开根号

        if dist2 > max_dist:
            max_dist = dist2
            best_pair = ((x1, y1), (x2, y2))  # 只返回坐标

    return best_pair

# 计算两个最远圆连线偏移角度
def calc_angle(p1, p2):
    x1, y1 = p1
    x2, y2 = p2

    dx = x2 - x1
    dy = y2 - y1

    angle = np.degrees(np.arctan2(dy, dx))

    # 归一化到 [-90, 90]
    if angle < -90:
        angle += 180
    elif angle > 90:
        angle -= 180

    return angle


def print_hi(path):

    img = cv2.imread(path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    gauss = cv2.GaussianBlur(gray, (5, 5), 0)
    ret1, binary_otsu = cv2.threshold(gauss, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # ----------------------------------------------------------------------------------------------

    # 霍夫圆检测
    circles = cv2.HoughCircles(
        binary_otsu,
        cv2.HOUGH_GRADIENT,
        dp=1.2,  # 分辨率比例
        minDist=200,  # 圆心最小间距
        param1=100,  # Canny高阈值
        param2=30,  # 圆检测阈值（越小越容易检测到）
        minRadius=10,  # 最小半径
        maxRadius=80  # 最大半径
    )

    # 绘制结果
    if circles is not None:
        circles = np.uint16(np.around(circles))
        for x, y, r in circles[0, :]:
            # 画圆
            cv2.circle(img, (x, y), r, (0, 255, 0), 2)
            # 画圆心
            cv2.circle(img, (x, y), 2, (0, 0, 255), 3)

    # ------------------------------------------------------------------------------

    cir = np.round(circles[0]).astype(int)

    c1, c2 = farthest_two_points(cir)

    angle = calc_angle(c1, c2)
    print("偏移角度: ", angle)

    cv2.namedWindow("result", cv2.WINDOW_NORMAL)
    cv2.imshow("result", img)

    cv2.waitKey(0)


# 按装订区域中的绿色按钮以运行脚本。
if __name__ == '__main__':
    print_hi("camImg/Test2.jpg")