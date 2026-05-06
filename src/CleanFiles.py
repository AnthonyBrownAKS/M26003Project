import os
from datetime import datetime, timedelta

def clean_old_images(base_dir, days=3):
    """
    自动删除超过指定天数的图片

    :param base_dir: 根目录 (例如 D:/M26003Project/camImg)
    :param days: 保留天数
    """
    now = datetime.now()
    expire_time = now - timedelta(days=days)

    for root, dirs, files in os.walk(base_dir):
        for file in files:
            if not file.endswith(".jpg"):
                continue

            try:
                # 解析时间（取前15位：20260422_153012）
                time_str = file[:15]
                file_time = datetime.strptime(time_str, "%Y%m%d_%H%M%S")

                # 判断是否过期
                if file_time < expire_time:
                    file_path = os.path.join(root, file)
                    os.remove(file_path)
                    print(f"已删除: {file_path}")

            except Exception as e:
                # 文件名不符合规则就跳过
                print(f"跳过文件: {file}, 原因: {e}")

