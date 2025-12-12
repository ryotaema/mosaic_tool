import cv2
import numpy as np
import os
import glob
import tkinter as tk
from tkinter import filedialog

class MosaicTool:
    def __init__(self):
        self.drawing = False  # 描画中フラグ
        self.ix, self.iy = -1, -1 # ドラッグ開始座標
        self.img = None       # 編集中の画像データ
        self.temp_img = None  # ドラッグ中のプレビュー用
        self.history = []     # Undo用の履歴
        self.file_list = []   # 画像ファイルパスのリスト
        self.current_index = 0
        self.mosaic_ratio = 0.06 # モザイクの粗さ
        
        # UI設定
        self.ui_height = 120  # 下部の操作パネルの高さ
        self.window_name = 'Mosaic Tool'

    def apply_mosaic(self, img, x, y, w, h):
        """画像の一部にモザイクをかける処理"""
        if w <= 0 or h <= 0: return img
        
        h_img, w_img = img.shape[:2]
        x, y = max(0, x), max(0, y)
        w, h = min(w, w_img - x), min(h, h_img - y)

        roi = img[y:y+h, x:x+w]
        if roi.size == 0: return img

        small = cv2.resize(roi, (max(1, int(w * self.mosaic_ratio)), max(1, int(h * self.mosaic_ratio))))
        mosaic = cv2.resize(small, (w, h), interpolation=cv2.INTER_NEAREST)
        
        img[y:y+h, x:x+w] = mosaic
        return img

    def mouse_callback(self, event, x, y, flags, param):
        """マウス操作のコールバック関数"""
        if self.img is None: return
        
        # UIエリア（画像の下）での操作は無視
        if y >= self.img.shape[0]: return

        if event == cv2.EVENT_LBUTTONDOWN:
            self.drawing = True
            self.ix, self.iy = x, y

        elif event == cv2.EVENT_MOUSEMOVE:
            if self.drawing:
                # プレビュー表示（実際にimgは書き換えず、表示用だけ更新）
                self.update_display(draw_rect=((self.ix, self.iy), (x, y)))

        elif event == cv2.EVENT_LBUTTONUP:
            self.drawing = False
            self.history.append(self.img.copy()) # Undo用に保存

            # 座標計算
            x1, y1 = min(self.ix, x), min(self.iy, y)
            x2, y2 = max(self.ix, x), max(self.iy, y)
            
            # モザイク適用
            self.img = self.apply_mosaic(self.img, x1, y1, x2-x1, y2-y1)
            self.update_display()

    def update_display(self, draw_rect=None):
        """画像とUIパネルを結合して表示"""
        if self.img is None: return
        
        # 1. 画像エリアの準備
        display_img = self.img.copy()
        
        # ドラッグ中なら矩形を描画
        if draw_rect:
            pt1, pt2 = draw_rect
            cv2.rectangle(display_img, pt1, pt2, (0, 255, 0), 2)

        # 2. UIパネル（下部の黒帯）の作成
        h, w = display_img.shape[:2]
        ui_panel = np.zeros((self.ui_height, w, 3), dtype=np.uint8)
        
        # 3. テキスト情報の描画
        filename = os.path.basename(self.file_list[self.current_index])
        status_text = f"File [{self.current_index + 1}/{len(self.file_list)}]: {filename}"
        
        # 色設定 (BGR)
        c_white = (255, 255, 255)
        c_yellow = (0, 255, 255)
        c_green = (0, 255, 0)

        # 1行目: ファイル情報
        cv2.putText(ui_panel, status_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, c_white, 2)
        
        # 2行目: メイン操作（ここを変更しました）
        cv2.putText(ui_panel, "[D]: Save & Next", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.6, c_green, 2)
        cv2.putText(ui_panel, "[Space]: Skip (No Save)", (250, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.6, c_yellow, 1)
        cv2.putText(ui_panel, "[A]: Back", (550, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.6, c_yellow, 1)

        # 3行目: サブ操作
        cv2.putText(ui_panel, "[Drag]: Mosaic  [Z]: Undo  [R]: Reset  [Q]: Quit", (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

        # 4. 画像とUIを縦に結合
        combined_img = cv2.vconcat([display_img, ui_panel])
        
        cv2.imshow(self.window_name, combined_img)

    def load_image_safe(self, path):
        """日本語パス対応の画像読み込み"""
        try:
            stream = np.fromfile(path, dtype=np.uint8)
            img = cv2.imdecode(stream, cv2.IMREAD_COLOR)
            return img
        except Exception as e:
            print(f"Error loading {path}: {e}")
            return None

    def save_image_safe(self, path, img):
        """日本語パス対応の画像保存"""
        try:
            ext = os.path.splitext(path)[1]
            result, encoded_img = cv2.imencode(ext, img)
            if result:
                with open(path, mode='w+b') as f:
                    encoded_img.tofile(f)
            return True
        except Exception as e:
            print(f"Error saving {path}: {e}")
            return False

    def run(self):
        # フォルダ選択
        root = tk.Tk()
        root.withdraw()
        print("処理対象の画像が入っているフォルダを選択してください...")
        target_dir = filedialog.askdirectory(title="画像フォルダを選択")
        
        if not target_dir: return

        # 画像リスト取得
        extensions = ['*.jpg', '*.jpeg', '*.png', '*.bmp']
        self.file_list = []
        for ext in extensions:
            self.file_list.extend(glob.glob(os.path.join(target_dir, ext)))
        self.file_list.sort()

        if not self.file_list:
            print("画像が見つかりませんでした。")
            return

        cv2.namedWindow(self.window_name)
        cv2.setMouseCallback(self.window_name, self.mouse_callback)

        print("--- Start ---")
        
        while self.current_index < len(self.file_list):
            file_path = self.file_list[self.current_index]
            
            if self.img is None:
                self.img = self.load_image_safe(file_path)
                if self.img is None:
                    self.current_index += 1
                    continue
                self.history = []
                self.update_display()

            key = cv2.waitKey(0)

            # --- キー操作 ---
            
            # 保存して次へ (D)
            if key == ord('d') or key == ord('D'): 
                self.save_image_safe(file_path, self.img)
                print(f"Saved: {os.path.basename(file_path)}")
                self.current_index += 1
                self.img = None 

            # 保存せずに次へ (Space)
            elif key == 32: 
                print(f"Skipped: {os.path.basename(file_path)}")
                self.current_index += 1
                self.img = None

            # 前に戻る (A)
            elif key == ord('a') or key == ord('A'): 
                if self.current_index > 0:
                    self.current_index -= 1
                    self.img = None
                else:
                    print("最初の画像です")

            # Undo (Z)
            elif key == ord('z') or key == ord('Z'):
                if self.history:
                    self.img = self.history.pop()
                    self.update_display()

            # Reset (R)
            elif key == ord('r') or key == ord('R'):
                self.img = self.load_image_safe(file_path)
                self.history = []
                self.update_display()

            # Quit (Q or Esc)
            elif key == 27 or key == ord('q') or key == ord('Q'):
                break

        cv2.destroyAllWindows()
        print("Done.")

if __name__ == "__main__":
    tool = MosaicTool()
    tool.run()