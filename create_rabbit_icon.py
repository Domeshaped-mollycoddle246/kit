"""3D 토끼 아이콘 + 점프 애니메이션 프레임 생성

원본: Microsoft Fluent Emoji 3D 'Rabbit Face' (MIT 라이선스)
assets/rabbit_3d.png 를 바탕으로 아이콘과 점프 프레임 8장을 만듭니다.
"""

import math
import os

from PIL import Image

APP_DIR = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(APP_DIR, "assets", "rabbit_3d.png")
SIZE = 200          # 출력 캔버스 크기
RABBIT = 150        # 토끼 기본 크기
JUMP = 26           # 최대 점프 높이(px)
FRAMES = 8


def make_frame(frame: int) -> Image.Image:
    """점프 중인 토끼 한 프레임 (squash & stretch 포함)"""
    src = Image.open(SRC).convert("RGBA")

    t = frame / FRAMES                      # 0 → 1
    height = math.sin(t * math.pi)          # 0 → 1 → 0 (포물선)
    jump = int(JUMP * height)

    # 뛰어오를 때 세로로 길쭉하게, 착지 직전엔 납작하게
    stretch = 1.0 + 0.10 * math.sin(t * 2 * math.pi)
    w = int(RABBIT / stretch)
    h = int(RABBIT * stretch)
    rabbit = src.resize((w, h), Image.LANCZOS)

    canvas = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    x = (SIZE - w) // 2
    y = SIZE - h - 10 - jump                # 바닥 기준으로 점프
    canvas.paste(rabbit, (x, y), rabbit)
    return canvas


def main():
    os.makedirs(os.path.join(APP_DIR, "assets"), exist_ok=True)

    # 정지 아이콘: 원본을 캔버스 중앙에
    src = Image.open(SRC).convert("RGBA").resize((RABBIT, RABBIT), Image.LANCZOS)
    canvas = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    canvas.paste(src, ((SIZE - RABBIT) // 2, SIZE - RABBIT - 10), src)
    canvas.save(os.path.join(APP_DIR, "assets", "rabbit_icon.png"))
    print("✅ assets/rabbit_icon.png")

    for i in range(FRAMES):
        path = os.path.join(APP_DIR, "assets", f"rabbit_jumping_{i}.png")
        make_frame(i).save(path)
        print(f"✅ {path}")


if __name__ == "__main__":
    main()
