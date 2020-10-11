import network
import time
from umqtt.robust import MQTTClient
import os
import gc
import sys
from machine import Pin, PWM
import onewire, ds18x20
import json

global relay 
global led

relay = Pin(5,Pin.OUT)
led = PWM(Pin(15), 500, 512)

# the following function is the callback which is 
# called when subscribed data is received
def callback_subscriber(topic, msg):
    print('Subscribe:  Received Data:  Topic = {}, Msg = {}\n'.format(topic, msg))
    if msg == b'on':
        relay.on()
    elif msg == b'off':
        relay.off()
    else:
        y = json.loads(msg)
        if 'brightness' in y: 
            led.duty(int(y["brightness"]))
        if 'brightness' not in y:
            led.duty(255)
            arms = y.get("state")
            if arms == "OFF":
                led.duty(0)

def do_connect():

    sta_if = network.WLAN(network.STA_IF)
    if not sta_if.isconnected():
        print('connecting to network...')
        
        sta_if.active(True)
        sta_if.connect('UPC4C89F1F', 'X2cumpebeJuc')
        while not sta_if.isconnected():
            pass
    print('network config:', sta_if.ifconfig())

def main():
    #Configure network
    do_connect()

    # create a random MQTT clientID 
    random_num = int.from_bytes(os.urandom(3), 'little')
    mqtt_client_id = bytes('client_'+str(random_num), 'utf-8')

    client = MQTTClient(mqtt_client_id, '192.168.0.87')
                        
    try:            
        client.connect()
    except Exception as e:
        print('could not connect to MQTT server {}{}'.format(type(e).__name__, e))
        sys.exit()

    client.set_callback(callback_subscriber)      
    client.subscribe("relay_cmd")
    client.subscribe("light/set")  

    #client.subscribe(mqtt_feedname_sub_2)  
    PUBLISH_PERIOD_IN_SEC = 0.5
    PUBLISH_PERIOD_IN_SEC2 = 1
    SUBSCRIBE_CHECK_PERIOD_IN_SEC = 0.5 
    accum_time = 0
    accum_time2 = 0

    #Initialize necessary pins for relay, button, led etc.
    button = Pin(4,Pin.IN)
    
    #Temporary variable
    button_pressed=0
    button_old=0
    temp_old=0

    #Temperature sensor (ds18b20)
    ds_pin = Pin(14)
    ds = ds18x20.DS18X20(onewire.OneWire(ds_pin))
    roms = ds.scan()
    
    while True:
        #Measue the temperature
        ds.convert_temp()
        time.sleep(0.75) 
        temp = (ds.read_temp(roms[0]))
        try:
            #Publish the temperature and button status.
            if accum_time >= PUBLISH_PERIOD_IN_SEC:
                if accum_time2 >= PUBLISH_PERIOD_IN_SEC2:
                    if temp != temp_old:
                        temp_old=temp
                        client.publish("temp",'{:3.1f}'.format(temp))
                        print('Temperatura = {:3.1f}'.format(temp))
                        accum_time2=0
                if button.value() != button_old:          
                    if button.value() == 0:
                        button_pressed=1
                        button_old=button.value()
                        print('Publish:  Button pressed = {}'.format(button_pressed)) 
                        client.publish("button","on")
                    else:
                        button_old=button.value()
                        button_pressed=0
                        print('Publish:  Button pressed = {}'.format(button_pressed)) 
                        client.publish("button","off")     
                    accum_time = 0

            # Subscribe.  Non-blocking check for a new message.  
            client.check_msg()

            time.sleep(SUBSCRIBE_CHECK_PERIOD_IN_SEC)
            accum_time += SUBSCRIBE_CHECK_PERIOD_IN_SEC
            accum_time2 += SUBSCRIBE_CHECK_PERIOD_IN_SEC
        except KeyboardInterrupt:
            print('Ctrl-C pressed...exiting')
            client.disconnect()
            sys.exit()
main()
