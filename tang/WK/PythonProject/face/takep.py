import cv2
import time
import os


def main():
    # 打开默认摄像头（通常是0）
    cap = cv2.VideoCapture(0)

    # 检查摄像头是否成功打开
    if not cap.isOpened():
        print("无法打开摄像头")
        return

    # 创建窗口
    cv2.namedWindow("摄像头画面 - 按x键截图，按q键退出", cv2.WINDOW_NORMAL)

    print("程序已启动：")
    print(" - 按x键：截图并保存到当前目录")
    print(" - 按q键：退出程序")

    try:
        while True:
            # 读取一帧画面
            ret, frame = cap.read()

            # 如果读取失败，退出循环
            if not ret:
                print("无法获取画面，退出程序")
                break

            # 显示画面
            cv2.imshow("摄像头画面 - 按x键截图，按q键退出", frame)

            # 等待按键输入，1ms超时
            key = cv2.waitKey(1) & 0xFF

            # 按q键退出
            if key == ord('q'):
                print("用户请求退出")
                break

            # 按x键截图
            elif key == ord('x'):
                # 生成带时间戳的文件名，避免覆盖
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"screenshot_{timestamp}.jpg"

                # 保存截图
                cv2.imwrite(filename, frame)
                print(f"截图已保存：{filename}")

    finally:
        # 释放摄像头资源
        cap.release()
        # 关闭所有窗口
        cv2.destroyAllWindows()
        print("程序已退出")


if __name__ == "__main__":
    main()
