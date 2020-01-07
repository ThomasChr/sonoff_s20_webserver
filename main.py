# Button is: PIN 0              -> INPUT, Active LOW
# Relais is: PIN 12             -> OUTPUT, Active High
# Green LED is: PIN 13          -> OUTPUT, Active LOW
# Blue LED is automaticly lit when Relais ist active
# Flashing:
# esptool.py --port COM20 erase_flash
# esptool.py --port COM20 write_flash -fs 4MB -fm dout 0x0 c:\temp\esp8266-20190529-v1.11.bin
# rshell --buffer-size=30 -p COM20
# cp main.py /pyboard
#
# Connections on Sonoff S20 - top to bottom:
# - GND
# - TX
# - RX
# - VCC (3.3V)
#
# Usb2Serial Cable:
# - Black: GND
# - Green: RX
# - White: TX
# - Red: 5V
#
# Connect Sonoff S20 as follow:
# - BLACK
# - GREEN
# - WHITE
# -> VCC does not need to be connected when it is in the Outlet -> BUT: Don't touch!!!
# --> Other cable have green and white swapped. So you need to try both directions
# ---> And you need to hold the Reset Button on the PCB while powering up the Outlet.
#
import gc
import os
import time
import usocket
import ustruct
import network
import machine

# Reset-IRQ-Handler (called on btnpin and on periodically timer tim)
def resetme(pin):
    print('Button or Timer reset!')
    machine.reset()

# Make sure the REPL is available via UART (for debugging purposes!)
# Already done in boot.py!
#uart = machine.UART(0, 115200)
#os.dupterm(uart)
try:
    print('Startup!')
    startuptime = time.time()
    print('Startup time secs: ' + str(startuptime))

    # Configuration
    Wifi_SSID = "xxx"
    Wifi_Pass = "yyy"
    myip = "172.30.2.111"
    mysubnet = "255.255.0.0"
    myrouter = "172.30.1.240"
    mydns = "172.30.1.240"
    title = "Outlet TC"

    # Set Pins, acivate Relais (value = 1 => active)
    btnpin = machine.Pin(0, machine.Pin.IN)
    relaispin = machine.Pin(12, machine.Pin.OUT, value = 1)     # Relais on
    greenledpin = machine.Pin(13, machine.Pin.OUT, value = 1)   # green LED off

    print('Try to connect to WiFi: ' + Wifi_SSID)

    # Prepare reset on btnpin
    btnpin.irq(trigger=machine.Pin.IRQ_FALLING, handler = resetme)

    # Activate a timer which which resets us all 5 minutes (300 seconds)
    tim = machine.Timer(-1)
    tim.init(period = 300 * 1000, mode = machine.Timer.PERIODIC, callback = resetme)

    # Connect to WiFi
    ap_if = network.WLAN(network.AP_IF)
    ap_if.active(False)
    sta_if = network.WLAN(network.STA_IF)
    sta_if.active(True)
    sta_if.ifconfig((myip, mysubnet, myrouter, mydns))
    sta_if.connect(Wifi_SSID, Wifi_Pass)
    while not sta_if.isconnected():
        pass

    print('WiFi connected:')
    print('IP-Address: ' + str(sta_if.ifconfig()[0]))
    print('Subnet Mask: ' + str(sta_if.ifconfig()[1]))
    print('Gateway: ' + str(sta_if.ifconfig()[2]))
    print('DNS: ' + str(sta_if.ifconfig()[3]))
    print()

    # Start Webserver
    s = usocket.socket()
    ai = usocket.getaddrinfo("0.0.0.0", 80)
    print("Bind address info:", ai)
    addr = ai[0][-1]

    s.setsockopt(usocket.SOL_SOCKET, usocket.SO_REUSEADDR, 1)
    s.bind(addr)
    s.listen(5)
    print("Webserver ready.")

    # Endless-Loop for Webserver hosting Website
    outputheader = 'HTTP/1.0 200 OK\r\n\r\n'
    while True:
        res = s.accept()
        client_sock = res[0]
        client_addr = res[1]
        client_port = client_addr[2:4]
        client_ip = client_addr[4:]
        print("Client IP:", str(client_addr))
        print("Client Port:", str(client_port))
        print()
        client_stream = client_sock
        print("Request:")
        req = client_stream.readline()
        print(req)
        output = '<html><head><title>' + title + '</title></head><body>'
        if req[:7] == b'GET /on':
            print('--> Switching Relais ON')
            relaispin.value(1)
            greenledpin.value(1)
            output += '<p>Switched Relais ON</p><hr>'
        elif req[:8] == b'GET /off':
            print('--> Switching Relais OFF')
            relaispin.value(0)
            greenledpin.value(0)
            output += '<p>Switched Relais OFF</p><hr>'
        elif req[:10] == b'GET /cycle':
            print('--> Switching Relais OFF')
            relaispin.value(0)
            greenledpin.value(0)
            output += '<p>Switched Relais OFF</p>'
            print('--> Switching Relais OFF')
            time.sleep(2)
            relaispin.value(1)
            greenledpin.value(1)
            output += '<p>Switched Relais ON</p><hr>'
        elif req[:11] == b'GET /status':
            relaisstatus = 'undefined'
            ledstatus = 'undefined'
            buttonstatus = 'undefined'
            # RELAIS
            if relaispin.value() == 0:
                relaisstatus = 'OFF'
            if relaispin.value() == 1:
                relaisstatus = 'ON'
            # LED
            if greenledpin.value() == 0:
                ledstatus = 'ON'
            if greenledpin.value() == 1:
                ledstatus = 'OFF'
            # BUTTON
            if btnpin.value() == 0:
                buttonstatus = 'PRESSED'
            if btnpin.value() == 1:
                buttonstatus = 'NOT PRESSED'
            print('-> relaispin: ' + str(relaispin.value()))
            print('-> greenledpin: ' + str(greenledpin.value()))
            print('-> btnpin: ' + str(btnpin.value()))
            print('--> Relais Status is: ' + relaisstatus)
            print('--> Green LED Status is: ' + ledstatus)
            print('--> Button Status is: ' + buttonstatus)
            print('--> Free Mem is: ' + str(gc.mem_free()))
            print('--> Uptime in sec: ' + str(time.time() - startuptime))
            output += '<p>Relais Status is: ' + relaisstatus + '</p>'
            output += '<p>Green LED Status is: ' + ledstatus + '</p>'
            output += '<p>Button Status is: ' + buttonstatus + '</p>'
            output += '<p>Free Mem is: ' + str(gc.mem_free()) + '</p>'
            output += '<p>Uptime in sec: ' + str(time.time() - startuptime) + '</p><hr>'
        output += '<p>Usage:</p><p>Switch on: <a href="/on">/on</a></p><p>Switch off: <a href="/off">/off</a></p><p>Power cycle: <a href="/cycle">/cycle</a></p><p>Status: <a href="/status">/status</a></p></body></html>'
        while True:
            h = client_stream.readline()
            if h == b"" or h == b"\r\n":
                break
            print(h)
        print('Answering: ')
        print('**************************************')
        print(outputheader + output)
        print('**************************************')
        client_stream.write(outputheader + output)
        client_stream.close()
        gc.collect()
        print('Free mem: ' + str(gc.mem_free()))
        print()
except KeyboardInterrupt:
    print('Keyboard Interrupt!')
except:
    print('Exception happend! Rebooting!')
    machine.reset()
