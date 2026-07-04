import os
import cv2
import base64
import time
import threading
from datetime import datetime
from openai import OpenAI

# 全局变量用于存储分析结果
analysis_result = None
analysis_complete = False


def capture_image():
    """捕获摄像头第5帧图像并保存，返回保存路径"""
    # 创建保存照片的目录（如果不存在）
    save_dir = "captured_photos"
    os.makedirs(save_dir, exist_ok=True)

    # 打开摄像头（设备索引根据实际情况调整）
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("无法打开摄像头")
        return None

    frame_count = 0
    target_frame = 5  # 目标保存第5帧
    saved_path = None

    # 捕获目标帧图像
    while frame_count < target_frame:
        ret, frame = cap.read()
        if not ret:
            print(f"无法获取第{frame_count + 1}帧图像")
            cap.release()
            return None

        frame_count += 1

        # 保存目标帧
        if frame_count == target_frame:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            saved_path = os.path.join(save_dir, f"photo_{timestamp}.jpg")
            cv2.imwrite(saved_path, frame)
            break

    cap.release()  # 释放摄像头
    return saved_path


def analyze_image_thread(image_path):
    """在单独线程中使用OpenAI客户端分析图像内容"""
    global analysis_result, analysis_complete
    try:
        # 初始化客户端
        client = OpenAI(
            base_url="https://ark.cn-beijing.volces.com/api/v3",
            api_key="豆包注册",
        )

        # 读取图片并转换为Base64
        with open(image_path, "rb") as f:
            img_base64 = base64.b64encode(f.read()).decode("utf-8")

        # 发送分析请求
        response = client.chat.completions.create(
            model="doubao-seed-1-6-thinking-250715",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{img_base64}"
                            },
                        },
                        {"type": "text", "text": "画面中央是什么东西？"},
                    ],
                }
            ],
        )

        analysis_result = response.choices[0].message.content
    except Exception as e:
        analysis_result = f"分析过程出错：{str(e)}"
    finally:
        analysis_complete = True


def save_result_to_file(result):
    """将识别结果保存到同目录的txt文件中"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"recognition_result.txt"

    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"识别时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("识别结果:\n")
        f.write(result)

    return filename


def main():
    global analysis_result, analysis_complete
    # 捕获图像
    image_path = capture_image()
    if not image_path or not os.path.exists(image_path):
        print("图像捕获失败，无法进行分析")
        return

    # 在新线程中开始分析图像
    analysis_thread = threading.Thread(target=analyze_image_thread, args=(image_path,))
    analysis_thread.start()

    # 等待最多8秒
    timeout = 8
    elapsed = 0
    check_interval = 0.1  # 检查间隔0.1秒

    while elapsed < timeout and not analysis_complete:
        time.sleep(check_interval)
        elapsed += check_interval

    # 检查分析是否完成
    if analysis_complete:
        print("\n分析结果：")
        print(analysis_result)
        # 保存结果到文件
        filename = save_result_to_file(analysis_result)
        # print(f"分析结果已保存到: {filename}")
    else:
        # 超时未完成，提示用户并等待最终结果
        print("\n你告诉用户你正在识别")
        # 等待分析线程完成
        analysis_thread.join()
        # 保存结果到文件
        filename = save_result_to_file(analysis_result)
        # print(f"分析完成，结果已保存到: {filename}")


if __name__ == "__main__":
    main()
# print(f"告诉用户你正在前往卫生间")
# import os
# import subprocess
#
#
# def run_test_script():
#     # 定义目标脚本的完整路径
#     script_path = "/home/zhuo/PycharmProjects/PythonProject/doubao/test.py"
#
#     # 1. 检查脚本是否存在
#     if not os.path.exists(script_path):
#         # print(f"错误：脚本不存在 - {script_path}")
#         return
#
#     # 2. 检查路径是否为文件（避免目录重名导致错误）
#     if not os.path.isfile(script_path):
#         # print(f"错误：{script_path} 不是一个文件")
#         return
#
#     try:
#         # 3. 使用subprocess运行脚本，捕获输出和错误
#         result = subprocess.run(
#             ["python", script_path],  # 用python解释器执行脚本
#             stdout=subprocess.PIPE,  # 捕获标准输出
#             stderr=subprocess.PIPE,  # 捕获错误输出
#             text=True,  # 输出转为字符串（而非字节）
#             check=True  # 若脚本运行出错（返回非0状态码），抛出异常
#         )
#
#         # 4. 打印脚本的输出结果
#         # print(f"脚本 {script_path} 运行成功！")
#         # print("脚本输出：")
#         # print(result.stdout)
#
#     except subprocess.CalledProcessError as e:
#         # 脚本运行出错（如语法错误、逻辑错误等）
#         # print(f"脚本运行失败，错误码：{e.returncode}")
#         # print("错误信息：")
#         print(e.stderr)
#     except Exception as e:
#         # 其他异常（如权限不足、Python解释器不存在等）
#         print(f"执行过程出错：{str(e)}")
#
#
# # 调用函数拉起脚本
# run_test_script()



