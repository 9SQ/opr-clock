import os
import sys
import time
import datetime
from PIL import Image, ImageDraw, ImageFont

# 画面解像度
WIDTH, HEIGHT = 1920, 480
# 背景色
BACKGROUND = (0, 0, 0, 255)
# ラベルの背景色
LABEL_BACKGROUND = (255, 255, 255, 255)
# ラベルのフォント色
LABEL_COLOR = (0, 0, 0, 255)
# セグメント点灯/消灯時のフォント色
SEG_ON = (255, 255, 255, 255)
SEG_OFF = (34, 34, 34, 255)
# 年月日曜日時分秒のフォント色
TEXT_COLOR = (255, 255, 255, 255)
# 7セグのフォント
FONT_7SEG = ImageFont.truetype("fonts/DSEG7Classic-BoldItalic.ttf", 110)
# 曜日表示のフォント
FONT_WEEKDAY = ImageFont.truetype("fonts/KosugiMaru-Regular.ttf", 100)
# 年月日曜日時分秒とラベルのフォント
FONT_TEXT = ImageFont.truetype("fonts/KosugiMaru-Regular.ttf", 60)
# 曜日の定義
WEEKDAYS_JP = ['月', '火', '水', '木', '金', '土', '日']

def draw_label(draw, pos, label):
    # ラベルの背景を描画
    draw.rectangle((0, pos[1] - 35, WIDTH, pos[1] + 40), fill=LABEL_BACKGROUND)
    # ラベルのテキストを描画
    draw.text((pos[0],pos[1]+3), label, font=FONT_TEXT, fill=LABEL_COLOR, anchor='mm')

def draw_7seg(draw, pos, base, text):
    # 7セグ消灯の表現
    draw.text(pos, base, font=FONT_7SEG, fill=SEG_OFF, anchor='rb')
    # 7セグ点灯の表現
    draw.text(pos, text, font=FONT_7SEG, fill=SEG_ON, anchor='rb')

def draw_line(draw, base_y, dt):
    # 年
    draw_7seg(draw, (355, base_y), '8888', f'{dt.year}')
    draw.text((355, base_y), "年", font=FONT_TEXT, fill=TEXT_COLOR, anchor='lb')
    # 月
    draw_7seg(draw, (565, base_y), '18',  f'{dt.month}')
    draw.text((565, base_y), "月", font=FONT_TEXT, fill=TEXT_COLOR, anchor='lb')
    # 日
    draw_7seg(draw, (825, base_y), '88', f'{dt.day}')
    draw.text((825, base_y), "日", font=FONT_TEXT, fill=TEXT_COLOR, anchor='lb')
    # 曜日
    weekday = WEEKDAYS_JP[dt.weekday()]
    draw.text((1020, base_y), weekday, font=FONT_WEEKDAY, fill=TEXT_COLOR, anchor='rb')
    draw.text((1020, base_y), "曜日", font=FONT_TEXT, fill=TEXT_COLOR, anchor='lb')
    # 時
    draw_7seg(draw, (1340, base_y), '88', f'{dt.hour}')
    draw.text((1340, base_y), "時", font=FONT_TEXT, fill=TEXT_COLOR, anchor='lb')
    # 分
    draw_7seg(draw, (1600, base_y), '88', dt.strftime("%M"))
    draw.text((1600, base_y), "分", font=FONT_TEXT, fill=TEXT_COLOR, anchor='lb')
    # 秒
    draw_7seg(draw, (1860, base_y), '88', dt.strftime("%S"))
    draw.text((1860, base_y), "秒", font=FONT_TEXT, fill=TEXT_COLOR, anchor='lb')


def generate_image():
    # 日本標準時
    jst = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
    # グリニッジ標準時
    utc = jst.astimezone(datetime.timezone.utc)
    # 背景黒画像を生成
    img = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND)
    draw = ImageDraw.Draw(img)
    # 上段 日本標準時
    draw_label(draw, (WIDTH // 2, 35), "日本標準時")
    draw_line(draw, 210, jst)
    # 下段 グリニッジ標準時
    draw_label(draw, (WIDTH // 2, 280), "グリニッジ標準時")
    draw_line(draw, 455, utc)
    return img


def run_framebuffer_loop():
    import numpy as np
    prev_sec = -1
    while True:
        now = datetime.datetime.now()
        if now.second != prev_sec:
            img = generate_image()
            # 横長の画像をフレームバッファに合わせて90度回転
            img = img.rotate(90, expand=True)
            # 画像をRGB565形式に変換
            arr = np.array(img, dtype=np.uint8)
            r = (arr[..., 0] >> 3).astype(np.uint16)
            g = (arr[..., 1] >> 2).astype(np.uint16)
            b = (arr[..., 2] >> 3).astype(np.uint16)
            rgb565 = (r << 11) | (g << 5) | b
            rgb565_data = rgb565.tobytes()
            # フレームバッファに書き込む
            with open("/dev/fb0", "rb+") as f:
                f.write(rgb565_data)
            prev_sec = now.second
        else:
            # 時刻に変化がない場合は0.01秒待機
            time.sleep(0.01)


def show_preview():
    import tkinter as tk
    from PIL import ImageTk
    window_width = WIDTH
    window_height = HEIGHT
    prev_sec = -1
    
    def resize(event):
        nonlocal window_width, window_height
        window_width = event.width
        window_height = int(event.width * HEIGHT / WIDTH)

    def update():
        nonlocal prev_sec, window_width, window_height
        if datetime.datetime.now().second != prev_sec:
            img = generate_image()
            # ウィンドウサイズが変更されている場合はリサイズ
            if window_width != WIDTH or window_height != HEIGHT:
                img = img.resize((window_width, window_height), Image.LANCZOS)
                root.geometry(f"{window_width}x{window_height}")
            tk_img = ImageTk.PhotoImage(img)
            label.config(image=tk_img)
            label.image = tk_img
            prev_sec = datetime.datetime.now().second
        root.after(100, update)

    root = tk.Tk()
    root.title("opr-clock")
    root.bind("<Configure>", resize)
    root.geometry(f"{WIDTH}x{HEIGHT}")
    root.tk_setPalette(background="black")
    label = tk.Label(root)
    label.pack()
    update()
    root.mainloop()

if __name__ == "__main__":
    if "--preview" in sys.argv:
        show_preview()
    else:
        run_framebuffer_loop()
