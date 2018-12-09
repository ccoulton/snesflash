import pycom
import network
import time
from machine import I2C
from pycom_mcp230xx import MCP23008, MCP23017

i2c = I2C(0, I2C.MASTER)
i2c.init(I2C.MASTER, baudrate=1700000)
pycom.heartbeat(False)

pycom.rgbled(0x000015)
bus = i2c.scan()
addrchip = MCP23017(i2c, bus[0])
buschip = MCP23008(i2c, bus[1])
datachip = MCP23008(i2c, bus[2])
