#!/usr/bin/python3
import os
import time
import curses
import sys
import argparse
from datetime import datetime
from prometheus_client import CollectorRegistry, Gauge, write_to_textfile

version = '1.0 (20241208)'

try:
    import serial
except ModuleNotFoundError:
    print("Error: 必要なモジュール 'pyserial' が見つかりません。\n"
          "以下のコマンドでインストールするか OS のパッケージマネージャでインストールしてください。")
    print("    pip3 install pyserial")
    print("")
    sys.exit(1)

# LED 表示 (0 で off)
DISPLAY_RULE_NORMALLY_OFF = 0
DISPLAY_RULE_NORMALLY_ON = 0

# 基準値の設定
THRESHOLD_ECO2 = 1000
# Prometheus ファイルの出力先
PROMETHEUS_FILE_PATH = '/var/lib/prometheus/node-exporter/sensor_omron.prom'

def s16(value):
    return -(value & 0x8000) | (value & 0x7fff)

# Prometheus 用の設定
registry = CollectorRegistry()
temperature = Gauge('sensor_omron_temperature', 'Temperature', registry=registry)
humidity = Gauge('sensor_omron_humidity', 'Humidity', registry=registry)
light = Gauge('sensor_omron_light', 'Ambient light', registry=registry)
barometric = Gauge('sensor_omron_barometric', 'Barometric pressure', registry=registry)
noise = Gauge('sensor_omron_noise', 'Sound noise', registry=registry)
discomfort = Gauge('sensor_omron_discomfort', 'Discomfort index', registry=registry)
heat = Gauge('sensor_omron_heat', 'Heat stroke', registry=registry)
etvoc = Gauge('sensor_omron_etvoc', 'eTVOC', registry=registry)
eco2 = Gauge('sensor_omron_eco2', 'eCO2', registry=registry)

# データを Prometheus に書き出す関数
def write_to_prometheus(data):
    temperature.set(data['Temperature'])
    humidity.set(data['Relative humidity'])
    light.set(data['Ambient light'])
    barometric.set(data['Barometric pressure'])
    noise.set(data['Sound noise'])
    discomfort.set(data['Discomfort index'])
    heat.set(data['Heat stroke'])
    etvoc.set(data['eTVOC'])
    eco2.set(data['eCO2'])
    write_to_textfile(PROMETHEUS_FILE_PATH, registry)
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

def get_discomfort_index_label(index):
    """
    不快指数に応じた体感の指標を返す
    """
    if index < 55:
        return "寒い"
    elif 55 <= index < 60:
        return "肌寒い"
    elif 60 <= index < 65:
        return "何も感じない"
    elif 65 <= index < 70:
        return "心地よい"
    elif 70 <= index < 75:
        return "暑くはない"
    elif 75 <= index < 80:
        return "やや暑い"
    elif 80 <= index < 85:
        return "暑くて汗が出る"
    else:
        return "暑くてたまらない"


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

            discomfort_index = int(hex(data[25]) + '{:02x}'.format(data[24], 'x'), 16) / 100

            return {
                "Time measured": datetime.now().strftime("%Y/%m/%d %H:%M:%S"),
                "Temperature": f"{s16(int(hex(data[9]) + '{:02x}'.format(data[8], 'x'), 16)) / 100:.2f}",
                "Relative humidity": f"{int(hex(data[11]) + '{:02x}'.format(data[10], 'x'), 16) / 100:.2f}",
                "Ambient light": str(int(hex(data[13]) + '{:02x}'.format(data[12], 'x'), 16)),
                "Barometric pressure": f"{int(hex(data[17]) + '{:02x}'.format(data[16], 'x') + '{:02x}'.format(data[15], 'x') + '{:02x}'.format(data[14], 'x'), 16) / 1000:.2f}",
                "Sound noise": f"{int(hex(data[19]) + '{:02x}'.format(data[18], 'x'), 16) / 100:.2f}",
                "eTVOC": str(int(hex(data[21]) + '{:02x}'.format(data[20], 'x'), 16)),
                "eCO2": str(int(hex(data[23]) + '{:02x}'.format(data[22], 'x'), 16)),
                "Discomfort index": discomfort_index,
                "Heat stroke": f"{s16(int(hex(data[27]) + '{:02x}'.format(data[26], 'x'), 16)) / 100:.2f}",
            }
    except serial.SerialException as e:
        print(f"Error: デバイスへのアクセスに失敗しました: {e}")
        sys.exit(1)

def display_csv(serial_device, no_header):
    """
    CSV形式で1回データを取得して出力する
    """
    latest_data = fetch_sensor_data(serial_device)

    # CSV形式で出力
    if not no_header:
        headers = ",".join(latest_data.keys())
        print(headers)
    values = ",".join(str(value) for value in latest_data.values())
    print(values)

    if args.prometheus_exporter_once:
        write_to_prometheus(latest_data)

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

            discomfort_index = latest_data['Discomfort index']
            discomfort_label = get_discomfort_index_label(discomfort_index)

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
            stdscr.addstr(3, 35, f"[eCO2] {latest_data['eCO2']} ppm", color)
            
            stdscr.addstr(5,  0, f"[不快指数] {discomfort_index:.2f} ({discomfort_label})")
            stdscr.addstr(5, 35, f"[熱中症度] {latest_data['Heat stroke']}")

            stdscr.addstr(6,  0, f"[総揮発性有機化合物濃度(eTVOC): {latest_data['eTVOC']} ppb")

            stdscr.refresh()

            if stdscr.getch() == ord('q'):
                break

            if args.prometheus_exporter or args.prometheus_exporter_once:
                write_to_prometheus(latest_data)

            if args.prometheus_exporter_once:
                break

            time.sleep(args.interval)

    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="OMRON 2JCIE-BU01 Sensor Data Display v" + version + "\nhttps://github.com/ikoga/2jciebu-usb-raspberrypi",
        epilog="Press 'q' to exit the program."
    )
    parser.add_argument("-d", "--device", default="/dev/ttyUSB0", help="Serial device to use (default: /dev/ttyUSB0)")
    parser.add_argument("-i", "--interval", type=int, default=2, help="Data fetch interval in seconds (default: 2)")
    parser.add_argument("--csv", action="store_true", help="Output CSV format")
    parser.add_argument("--no-csv-header", action="store_true", help="Do not print CSV header")
    parser.add_argument('--prometheus-exporter', action='store_true', help="Enable Prometheus exporter mode")
    parser.add_argument('--prometheus-exporter-once', action='store_true', help="Enable Prometheus exporter mode (one-shot)")
    parser.add_argument("-v", "--version", action='store_true', help="Print version and exit")
    args = parser.parse_args()

    if args.version:
       print("envtop.py " + version)
       sys.exit(0)

    if args.interval < 1:
        print("Error: 更新間隔は 1 以上の整数である必要があります。")
        sys.exit(1)

    if not os.access(args.device, os.R_OK | os.W_OK):
        print(f"Error: '{args.device}' への読み取り権限がありません。\n"
              "root で実行するか、環境センサへのアクセス権限を持つユーザで実行してください。")
        sys.exit(1)

    if args.csv:
        display_csv(args.device, args.no_csv_header)

    else:
        curses.wrapper(main, args.device)
