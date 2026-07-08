"""귀여운 토끼 아이콘 생성 (3D 스타일)"""

from PIL import Image, ImageDraw
import math


def create_rabbit_icon(size=200, filename="assets/rabbit_icon.png"):
    """귀여운 토끼 아이콘을 생성합니다."""
    img = Image.new("RGBA", (size, size), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img, "RGBA")

    center_x, center_y = size // 2, size // 2
    scale = size / 200

    # 토끼 얼굴 (원형)
    face_rad = int(60 * scale)
    draw.ellipse(
        [center_x - face_rad, center_y - int(50 * scale),
         center_x + face_rad, center_y + int(70 * scale)],
        fill=(240, 240, 255)  # 밝은 흰색
    )

    # 양쪽 귀 (긴 타원)
    ear_width = int(30 * scale)
    ear_height = int(80 * scale)
    left_ear_x = center_x - int(40 * scale)
    right_ear_x = center_x + int(40 * scale)

    # 왼쪽 귀
    draw.ellipse(
        [left_ear_x - int(15 * scale), center_y - int(50 * scale),
         left_ear_x + int(15 * scale), center_y - int(50 * scale) + ear_height],
        fill=(250, 220, 240)  # 분홍색
    )

    # 오른쪽 귀
    draw.ellipse(
        [right_ear_x - int(15 * scale), center_y - int(50 * scale),
         right_ear_x + int(15 * scale), center_y - int(50 * scale) + ear_height],
        fill=(250, 220, 240)
    )

    # 귀 내부
    draw.ellipse(
        [left_ear_x - int(8 * scale), center_y - int(40 * scale),
         left_ear_x + int(8 * scale), center_y - int(40 * scale) + int(60 * scale)],
        fill=(255, 200, 220)
    )
    draw.ellipse(
        [right_ear_x - int(8 * scale), center_y - int(40 * scale),
         right_ear_x + int(8 * scale), center_y - int(40 * scale) + int(60 * scale)],
        fill=(255, 200, 220)
    )

    # 눈
    eye_y = center_y - int(15 * scale)
    eye_size = int(12 * scale)

    # 왼쪽 눈
    draw.ellipse(
        [center_x - int(25 * scale) - eye_size // 2, eye_y - eye_size // 2,
         center_x - int(25 * scale) + eye_size // 2, eye_y + eye_size // 2],
        fill=(50, 50, 50)
    )

    # 오른쪽 눈
    draw.ellipse(
        [center_x + int(25 * scale) - eye_size // 2, eye_y - eye_size // 2,
         center_x + int(25 * scale) + eye_size // 2, eye_y + eye_size // 2],
        fill=(50, 50, 50)
    )

    # 눈 하이라이트
    light_size = int(5 * scale)
    draw.ellipse(
        [center_x - int(25 * scale) - int(2 * scale), eye_y - int(2 * scale),
         center_x - int(25 * scale) + light_size, eye_y + light_size],
        fill=(255, 255, 255)
    )
    draw.ellipse(
        [center_x + int(25 * scale) - int(2 * scale), eye_y - int(2 * scale),
         center_x + int(25 * scale) + light_size, eye_y + light_size],
        fill=(255, 255, 255)
    )

    # 코
    nose_y = center_y + int(10 * scale)
    nose_size = int(8 * scale)
    draw.ellipse(
        [center_x - nose_size // 2, nose_y - nose_size // 2,
         center_x + nose_size // 2, nose_y + nose_size // 2],
        fill=(255, 150, 180)  # 분홍색
    )

    # 입 (웃는 표정)
    mouth_y = nose_y + int(15 * scale)
    mouth_width = int(20 * scale)
    draw.arc(
        [center_x - mouth_width, mouth_y - int(10 * scale),
         center_x + mouth_width, mouth_y + int(10 * scale)],
        start=0, end=180, fill=(50, 50, 50), width=int(3 * scale)
    )

    # 뺨 (분홍 동그라미)
    cheek_size = int(15 * scale)
    draw.ellipse(
        [center_x - int(55 * scale) - cheek_size // 2, center_y - int(10 * scale) - cheek_size // 2,
         center_x - int(55 * scale) + cheek_size // 2, center_y - int(10 * scale) + cheek_size // 2],
        fill=(255, 180, 200, 150)  # 반투명 분홍
    )
    draw.ellipse(
        [center_x + int(55 * scale) - cheek_size // 2, center_y - int(10 * scale) - cheek_size // 2,
         center_x + int(55 * scale) + cheek_size // 2, center_y - int(10 * scale) + cheek_size // 2],
        fill=(255, 180, 200, 150)
    )

    img.save(filename)
    print(f"✅ 토끼 아이콘 생성됨: {filename}")


def create_rabbit_icon_jumping(size=200, frame=0, filename="assets/rabbit_jumping_{frame}.png"):
    """점프하는 토끼 애니메이션 프레임 생성"""
    # 점프 높이 계산 (사인파)
    jump_height = int(20 * math.sin(frame * math.pi / 8)) if frame < 8 else 0

    img = Image.new("RGBA", (size, size), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img, "RGBA")

    center_x, center_y = size // 2, size // 2
    center_y -= jump_height  # 점프 높이만큼 위로 이동
    scale = size / 200

    # 토끼 그리기 (동일하게)
    face_rad = int(60 * scale)
    draw.ellipse(
        [center_x - face_rad, center_y - int(50 * scale),
         center_x + face_rad, center_y + int(70 * scale)],
        fill=(240, 240, 255)
    )

    ear_height = int(80 * scale)
    left_ear_x = center_x - int(40 * scale)
    right_ear_x = center_x + int(40 * scale)

    draw.ellipse(
        [left_ear_x - int(15 * scale), center_y - int(50 * scale),
         left_ear_x + int(15 * scale), center_y - int(50 * scale) + ear_height],
        fill=(250, 220, 240)
    )
    draw.ellipse(
        [right_ear_x - int(15 * scale), center_y - int(50 * scale),
         right_ear_x + int(15 * scale), center_y - int(50 * scale) + ear_height],
        fill=(250, 220, 240)
    )

    draw.ellipse(
        [left_ear_x - int(8 * scale), center_y - int(40 * scale),
         left_ear_x + int(8 * scale), center_y - int(40 * scale) + int(60 * scale)],
        fill=(255, 200, 220)
    )
    draw.ellipse(
        [right_ear_x - int(8 * scale), center_y - int(40 * scale),
         right_ear_x + int(8 * scale), center_y - int(40 * scale) + int(60 * scale)],
        fill=(255, 200, 220)
    )

    eye_y = center_y - int(15 * scale)
    eye_size = int(12 * scale)

    draw.ellipse(
        [center_x - int(25 * scale) - eye_size // 2, eye_y - eye_size // 2,
         center_x - int(25 * scale) + eye_size // 2, eye_y + eye_size // 2],
        fill=(50, 50, 50)
    )
    draw.ellipse(
        [center_x + int(25 * scale) - eye_size // 2, eye_y - eye_size // 2,
         center_x + int(25 * scale) + eye_size // 2, eye_y + eye_size // 2],
        fill=(50, 50, 50)
    )

    light_size = int(5 * scale)
    draw.ellipse(
        [center_x - int(25 * scale) - int(2 * scale), eye_y - int(2 * scale),
         center_x - int(25 * scale) + light_size, eye_y + light_size],
        fill=(255, 255, 255)
    )
    draw.ellipse(
        [center_x + int(25 * scale) - int(2 * scale), eye_y - int(2 * scale),
         center_x + int(25 * scale) + light_size, eye_y + light_size],
        fill=(255, 255, 255)
    )

    nose_y = center_y + int(10 * scale)
    nose_size = int(8 * scale)
    draw.ellipse(
        [center_x - nose_size // 2, nose_y - nose_size // 2,
         center_x + nose_size // 2, nose_y + nose_size // 2],
        fill=(255, 150, 180)
    )

    mouth_y = nose_y + int(15 * scale)
    mouth_width = int(20 * scale)
    draw.arc(
        [center_x - mouth_width, mouth_y - int(10 * scale),
         center_x + mouth_width, mouth_y + int(10 * scale)],
        start=0, end=180, fill=(50, 50, 50), width=int(3 * scale)
    )

    cheek_size = int(15 * scale)
    draw.ellipse(
        [center_x - int(55 * scale) - cheek_size // 2, center_y - int(10 * scale) - cheek_size // 2,
         center_x - int(55 * scale) + cheek_size // 2, center_y - int(10 * scale) + cheek_size // 2],
        fill=(255, 180, 200, 150)
    )
    draw.ellipse(
        [center_x + int(55 * scale) - cheek_size // 2, center_y - int(10 * scale) - cheek_size // 2,
         center_x + int(55 * scale) + cheek_size // 2, center_y - int(10 * scale) + cheek_size // 2],
        fill=(255, 180, 200, 150)
    )

    filename_formatted = filename.format(frame=frame)
    img.save(filename_formatted)
    print(f"✅ 애니메이션 프레임 생성됨: {filename_formatted}")


if __name__ == "__main__":
    import os
    os.makedirs("assets", exist_ok=True)

    # 정적 토끼 아이콘
    create_rabbit_icon(200)

    # 점프 애니메이션 프레임들
    print("\n🐰 점프 애니메이션 프레임 생성 중...")
    for i in range(8):
        create_rabbit_icon_jumping(200, i, "assets/rabbit_jumping_{frame}.png")
