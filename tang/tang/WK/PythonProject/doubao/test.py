import pygame
import time


def play_mp3(file_path):
    # 初始化pygame音频模块
    pygame.mixer.init()
    try:
        # 加载MP3文件
        pygame.mixer.music.load(file_path)
        # 播放音频
        pygame.mixer.music.play()
        print(f"正在播放：{file_path}")

        # 等待播放完成（需要保持程序运行）
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)  # 每隔0.1秒检查一次播放状态
    except Exception as e:
        print(f"播放失败：{str(e)}")
    finally:
        # 释放资源
        pygame.mixer.music.stop()
        pygame.mixer.quit()


# 播放指定路径的MP3
time.sleep(20)
mp3_path = "/home/zhuo/PycharmProjects/PythonProject/py-xiaozhi-main/111.mp3"
play_mp3(mp3_path)
