#!/usr/bin/python3
import os
import time
from datetime import datetime
import curses
import sys
import argparse
try:
    import serial
except ModuleNotFoundError:
    print("Error: 必要なモジュール 'pyserial' が見つかりません。\n"
          "以下のコマンドでインストールするか OS のパッケージマネージャでインストールしてください。")
    print("    pip3 install pyserial")
    print("")
    sys.exit(1)

DISPLAY_RULE_NORMALLY_OFF = 0
DISPLAY_RULE_NORMALLY_ON = 0

# 基準値の設定
THRESHOLD_ECO2 = 1000

def s16(value):
    return -(value & 0x8000) | (value & 0x7fff)

def calc_crc(buf, length):
    crc = 0xFFFF
    for i in range(length):
        crc = crc ^ buf[i]
        for j in range(8):
            carrayFlag = crc & 1
            crc = crc >> 1
            if (carrayFlag == 1):
                crc = crc ^ 0xA001
    crcH = crc >> 8
    crcL = crc & 0x00FF
    return (bytearray([crcL, crcH]))

def fetch_sensor_data(serial_device):
    """
    センサから最新のデータを取得してフォーマット済み辞書を返す
    """
    try:
        with serial.Serial(serial_device, 115200, serial.EIGHTBITS, serial.PARITY_NONE) as ser:
            # データ取得コマンド
            command = bytearray([0x52, 0x42, 0x05, 0x00, 0x01, 0x21, 0x50])
            command += calc_crc(command, len(command))
            ser.write(command)
            time.sleep(0.1)
            data = ser.read(ser.inWaiting())

            if len(data) < 28:  # データの不足確認
                raise ValueError("Incomplete data received from sensor.")

            return {
                "Time measured": datetime.now().strftime("%Y/%m/%d %H:%M:%S"),
                "Temperature": f"{s16(int(hex(data[9]) + '{:02x}'.format(data[8], 'x'), 16)) / 100:.2f}",
                "Relative humidity": f"{int(hex(data[11]) + '{:02x}'.format(data[10], 'x'), 16) / 100:.2f}",
                "Ambient light": str(int(hex(data[13]) + '{:02x}'.format(data[12], 'x'), 16)),
                "Barometric pressure": f"{int(hex(data[17]) + '{:02x}'.format(data[16], 'x') + '{:02x}'.format(data[15], 'x') + '{:02x}'.format(data[14], 'x'), 16) / 1000:.2f}",
                "Sound noise": f"{int(hex(data[19]) + '{:02x}'.format(data[18], 'x'), 16) / 100:.2f}",
                "eTVOC": str(int(hex(data[21]) + '{:02x}'.format(data[20], 'x'), 16)),
                "eCO2": str(int(hex(data[23]) + '{:02x}'.format(data[22], 'x'), 16)),
                "Discomfort index": f"{int(hex(data[25]) + '{:02x}'.format(data[24], 'x'), 16) / 100:.2f}",
                "Heat stroke": f"{s16(int(hex(data[27]) + '{:02x}'.format(data[26], 'x'), 16)) / 100:.2f}",
            }
    except serial.SerialException as e:
        print(f"Error: デバイスへのアクセスに失敗しました: {e}")
        sys.exit(1)

def display_csv(serial_device):
    """
    CSV形式で1回データを取得して出力する
    """
    latest_data = fetch_sensor_data(serial_device)

    # CSV形式で出力
    headers = ",".join(latest_data.keys())
    values = ",".join(latest_data.values())
    print(headers)
    print(values)

def main(stdscr, serial_device):
    curses.curs_set(0)
    stdscr.nodelay(1)
    stdscr.timeout(1000)

    curses.start_color()
    curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)  # 白色文字、黒背景
    curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)    # 赤色文字、黒背景

    try:
        while True:
            latest_data = fetch_sensor_data(serial_device)

            stdscr.clear()
            stdscr.addstr(0, 0, f"OMRON 2JCIE-BU01 Sensor           {latest_data['Time measured']}")
            stdscr.addstr(1, 0, f"-----------------------------------------------------")

            stdscr.addstr(2,  0, f"[気温] {latest_data['Temperature']} C")
            stdscr.addstr(2, 17, f"[湿度] {latest_data['Relative humidity']} %")
            stdscr.addstr(2, 35, f"[気圧] {latest_data['Barometric pressure']} hPa")
            
            stdscr.addstr(3,  0, f"[照度] {latest_data['Ambient light']} lx")
            stdscr.addstr(3, 17, f"[騒音] {latest_data['Sound noise']} dB")

            eco2_value = float(latest_data['eCO2'])
            color = curses.color_pair(2) if eco2_value >= THRESHOLD_ECO2 else curses.color_pair(1)
            stdscr.addstr(3, 35, f"[eCO2] {latest_data['eCO2']}", color)
            
            stdscr.addstr(5,  0, f"[不快指数] {latest_data['Discomfort index']}")
            stdscr.addstr(5, 35, f"[熱中症度] {latest_data['Heat stroke']}")

            stdscr.addstr(6,  0, f"[総揮発性有機化合物濃度(eTVOC): {latest_data['eTVOC']}")

            stdscr.refresh()

            if stdscr.getch() == ord('q'):
                break

            time.sleep(1)

    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="OMRON 2JCIE-BU01 Sensor Data Display",
        epilog="Press 'q' to exit the program."
    )
    parser.add_argument(
        "-d", "--device",
        default="/dev/ttyUSB0",
        help="Serial device to use (default: /dev/ttyUSB0)"
    )
    parser.add_argument(
        "--csv",
        action="store_true",
        help="Output CSV format"
    )
    args = parser.parse_args()

    if not os.access(args.device, os.R_OK | os.W_OK):
        print(f"Error: '{args.device}' への読み取り権限がありません。\n"
              "root で実行するか、環境センサへのアクセス権限を持つユーザで実行してください。")
        sys.exit(1)

    if args.csv:
        display_csv(args.device)
    else:
        curses.wrapper(main, args.device)
