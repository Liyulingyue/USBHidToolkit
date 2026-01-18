import ujson as json
import uos as os
import network
import usocket as socket
import time
from machine import Pin, UART, I2C, reset
from ssd1306 import SSD1306_I2C

# 配置 UART
uart = UART(1, baudrate=9600, tx=Pin(0), rx=Pin(1))
i2c = I2C(0, scl=Pin(5), sda=Pin(4), freq=100000)
oled = SSD1306_I2C(128, 32, i2c)

# 配置WiFi AP相关信息
AP_SSID = "ESP32_Config"  # AP名称
AP_PASSWORD = "12345678"  # AP密码

# 配置服务器监听IP
IP_self = "0.0.0.0"

# 默认配网信息
cfg_dict_default = {  # 默认字典
    "BLE": 1,  # 默认WiFi配网模式
    "SSID": "",  # 默认没有wifi信息
    "PASSWORD": "",  # 默认没有wifi密码
}
config = {}  # 配置信息


# ***************** 开机状态设置 ***************
def load_config():
    # 开机初始化配置文件信息
    cfg_dict = cfg_dict_default.copy()
    # 检查文件是否存在
    if 'cfg.json' in os.listdir():
        with open('cfg.json', 'r') as f:
            loaded_data = json.load(f)
        # 验证读取的数据是否是字典类型
        if isinstance(loaded_data, dict):
            cfg_dict.update(loaded_data)

    # 配置为WiFi配网状态，写入文件
    with open('cfg.json', 'w') as f:
        json.dump(cfg_dict_default, f)

    # 等待2秒，此时重启，下次读取数据时，会变为WiFi配网模式
    oled.fill(0)
    oled.text("Loading", 0, 12)
    oled.show()
    time.sleep(2)

    # 2s内没有重启，还原数据模式
    with open('cfg.json', 'w') as f:
        json.dump(cfg_dict, f)

    return cfg_dict


def start_ap():
    wlan = network.WLAN(network.AP_IF)
    wlan.active(True)
    wlan.config(essid=AP_SSID, authmode=network.AUTH_OPEN)
    print('AP started')
    print('AP IP:', wlan.ifconfig()[0])
    IP_self = wlan.ifconfig()[0]

    # 初始化socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('', 80))
    s.listen(5)
    s.setblocking(False)
    print('Web server listening on port 80...')

    return wlan, s


def handle_request(s):
    try:
        conn, addr = s.accept()
        print('Connected by', addr)
        request = conn.recv(1024)
        request_str = request.decode('utf-8')
        print('Request:', request_str)

        if 'POST' in request_str:
            # 处理POST请求，解析表单数据
            body = request_str.split('\r\n\r\n')[1]
            params = {}
            for pair in body.split('&'):
                if '=' in pair:
                    key, value = pair.split('=', 1)
                    params[key] = value.replace('+', ' ').replace('%20', ' ')

            ssid = params.get('ssid', '')
            password = params.get('password', '')

            if ssid and password:
                config["BLE"] = 0
                config["SSID"] = ssid
                config["PASSWORD"] = password
                with open('cfg.json', 'w') as f:
                    json.dump(config, f)
                oled.fill(0)
                oled.text("Config Saved", 0, 12)
                oled.show()
                time.sleep(1)
                reset()  # 重启设备

            response = 'HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\nConfiguration saved. Rebooting...'
        else:
            # 处理GET请求，返回HTML表单
            html = '''<!DOCTYPE html>
<html>
<head>
    <title>WiFi Configuration</title>
</head>
<body>
    <h1>ESP32 WiFi Configuration</h1>
    <form method="post">
        <label for="ssid">WiFi SSID:</label><br>
        <input type="text" id="ssid" name="ssid" required><br><br>
        <label for="password">WiFi Password:</label><br>
        <input type="password" id="password" name="password" required><br><br>
        <input type="submit" value="Save and Connect">
    </form>
</body>
</html>'''
            response = 'HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n' + html

        conn.send(response.encode())
        conn.close()
        return True
    except OSError:
        return False


# ***************** WIFI通讯设置 ***************
def connect_to_wifi(ssid, password):
    oled.fill(0)
    oled.text("Connecting WIFI", 0, 12)
    oled.show()

    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if wlan.isconnected():
        print('当前已连接到 Wi-Fi，正在断开连接...')
        wlan.disconnect()
    wlan.connect(ssid, password)
    while not wlan.isconnected():
        time.sleep(1)
        print("connecting")
    print('WiFi connected')
    print('IP address:', wlan.ifconfig()[0])
    IP_self = wlan.ifconfig()[0]

    oled.fill(0)
    oled.text(wlan.ifconfig()[0], 0, 12)
    oled.show()


def flush_uart_buffer():
    while uart.any():
        uart.read()  # 一次性读取所有积压数据


def start_server():
    # 创建套接字并绑定到端口80 TCP
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('', 80))
    s.listen(5)
    print('Listening on socket...')

    while True:
        print("Listening")
        conn, addr = s.accept()
        print('Connected by', addr)
        request = conn.recv(1024)
        print('Receive:', request)

        conn.close()

        # 转发给CH9329
        uart.write(request)
        flush_uart_buffer()  # 清空未读数据


def main():
    # 使用示例
    global config
    config = load_config()
    print(config)
    if_ble_model = config.get('BLE', 0)  # 默认为配网模式
    if if_ble_model == 1:
        # AP配网模式
        wlan_ap, s = start_ap()
        scroll_text = "Connect to ESP32_Config, visit 192.168.4.1 to config WiFi"
        scroll_pos = 0
        while True:
            # 滚动显示文本
            oled.fill(0)
            display_text = scroll_text[scroll_pos:scroll_pos + 16]
            oled.text(display_text, 0, 12)
            oled.show()
            scroll_pos = (scroll_pos + 1) % len(scroll_text)
            # 处理web请求
            handle_request(s)
            time.sleep(0.2)
    else:
        # 连接到 Wi-Fi， WIFI名称、密码
        Wifi_Name = config.get('SSID', "******")
        Wifi_Password = config.get('PASSWORD', "******")
        connect_to_wifi(Wifi_Name, Wifi_Password)
        # 启动服务器
        start_server()


if __name__ == '__main__':
    main()