import sys
import time
import requests
import serial
from serial.tools import list_ports

# ==========================================
# ⚙️ 專案基礎設定 (根據你的環境修改)
# ==========================================
# 1. 你的 FastAPI 後端更新房間狀態的 API 網址
BACKEND_URL = "http://127.0.0.1:8000/api/room/status"

# 2. 自動偵測 Arduino 的 COM 連接埠 (免去手動改 COM 的麻煩！)
def find_arduino_port():
    ports = list_ports.comports()
    for port in ports:
        # 依據常見的 Arduino 晶片關鍵字進行自動匹配
        if "Arduino" in port.description or "CH340" in port.description or "USB" in port.description:
            return port.device
    return None

# ==========================================
# 🚀 核心執行邏輯
# ==========================================
def main():
    target_port = find_arduino_port()
    
    if not target_port:
        print("❌ 錯誤：找不到 Arduino 板子！請檢查 USB 線是否插緊。")
        sys.exit(1)
        
    print(f"🔌 成功偵測到硬體裝置，正在連線至：{target_port}")
    
    try:
        # 初始化序列埠通訊，波特率必須與 Arduino 的 Serial.begin(9600) 一致
        ser = serial.Serial(target_port, 9600, timeout=1)
        time.sleep(2)  # 讓 Arduino 晶片連線初始化穩定
        print("🚀 智慧房務「硬體 ➔ 網頁」橋樑已成功啟動！即時監聽中...")
        
        while True:
            if ser.in_waiting > 0:
                # 讀取來自 Arduino 的狀態字串並去處空白
                status_name = ser.readline().decode('utf-8').strip()
                
                # 驗證收到的狀態是否合法
                if status_name in ["NEED_CLEAN", "CLEANING", "CLEAN_DONE", "OFF"]:
                    print(f"📥 [硬體訊號] 實體按鈕觸發狀態：{status_name}")
                    
                    # 透過 POST 請求，將狀態打包發送給網頁後端 API
                    try:
                        payload = {"status": status_name}
                        response = requests.post(BACKEND_URL, json=payload, timeout=3)
                        print(f"➡️  [網頁同步] 成功同步至後端網頁！回應碼：{response.status_code}")
                    except requests.exceptions.RequestException as e:
                        print(f"❌ [連線失敗] 訊號已擷取，但無法連線至網頁後端 API：{e}")
                        
            time.sleep(0.05)  # 降低 CPU 使用率

    except KeyboardInterrupt:
        print("\n👋 房務監聽程式已安全關閉。")
        if 'ser' in locals() and ser.is_open:
            ser.close()
            
    except Exception as e:
        print(f"💥 程式發生未知錯誤：{e}")

if __name__ == "__main__":
    main()