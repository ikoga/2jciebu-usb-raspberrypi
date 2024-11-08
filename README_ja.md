# 2jciebu-usb-raspberrypi
オムロン製センサ 2JCIE-BU を Raspberry Pi 3 Model B で評価する為のサンプルプログラムです。  

2JCIE-BU はさまざまな環境情報のセンシングに活用できる多機能センサモジュールです。  
温度、湿度、光、気圧、騒音、3軸加速度といった各種センサを搭載しています。  
特徴的な機能として、高精度の振動加速に基づいて地震を判断することができます。  
また、揮発性有機化合物（VOC）センサを活用し、室内空気品質の連続モニタリングを実現しています。  
インタフェースとして USB および Bluetooth® を備えています。  


## 言語
- [英語](./README.md)
- [日本語](./README_ja.md)

## 概要
- sample_2jciebu.py  
USBシリアルインタフェースでセンシングデータを取得し、コンソール上で確認できるサンプルプログラムです。  
データの取得中はLEDが点灯します。

***デモ:***  
sample_2jciebu.py を実行するとコンソール上でセンシングデータを確認することができます。  

![console_demo](console_demo.png)

## インストール方法
1. 事前に依存関係のあるソフトウェアをインストールして下さい。  
    [依存関係](#link)
2. ターミナルを開き、次のコマンドを実行します。  
    ```
    $ mkdir omron_sensor
    $ cd omron_sensor
    $ git clone https://github.com/omron-devhub/2jciebu-usb-raspberrypi.git
    ```

## 使い方

サンプルプログラムを動作させる手順です。ターミナルを開き、次のコマンドを実行します。

### ドライバのインストール

USBシリアルで通信を行うために、FTDIドライバをインストールします。

```
$ sudo modprobe ftdi_sio
$ sudo chmod 777 /sys/bus/usb-serial/drivers/ftdi_sio/new_id
$ sudo echo 0590 00d4 > /sys/bus/usb-serial/drivers/ftdi_sio/new_id
```

再起動後も自動的にドライバをロードさせたい場合は、`/etc/udev/rules.d/99-ftdi.rules`に下記を追加してください。

```
ACTION=="add", ATTRS{idVendor}=="0590", ATTRS{idProduct}=="00d4", RUN+="/sbin/modprobe ftdi_sio" RUN+="/bin/sh -c 'echo 0590 00d4 > /sys/bus/usb-serial/drivers/ftdi_sio/new_id'"
```

### サンプルプログラムの起動

`sample_2jciebu.py` を実行します。

```
$ sudo python3 sample_2jciebu.py
```

停止する際は、Ctrl + C を押します。

## <a name="link"></a>依存関係
2jciebu01-usb-raspberrypi には次に挙げるソフトウェアとの依存関係があります。
- [Python3](https://www.python.org/)
- [pyserial](https://pythonhosted.org/pyserial/pyserial.html#installation)

## Contributors
このリポジトリにContributeしていただいた方は[こちら](https://github.com/omron-devhub/2jciebu-usb-raspberrypi/graphs/contributors)です。  
私たちはすべてのContributorに感謝します！

## ライセンス
Copyright (c) OMRON Corporation. All rights reserved.

このリポジトリはMITライセンスの下でライセンスされています。
