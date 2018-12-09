import pycom
import network
import time
from machine import I2C
from pycom_mcp230xx import MCP23008, MCP23017

i2c = I2C(0, I2C.MASTER)
i2c.init(I2C.MASTER, baudrate=100000)
pycom.heartbeat(False)

pycom.rgbled(0x000015)
bus = i2c.scan()
addrchip = MCP23017(i2c, bus[0])
bankchip = MCP23008(i2c, bus[1])
datachip = MCP23008(i2c, bus[2])

addrchip.iodir = 0x0000

bankchip.iodir = 0x00

datachip.iodir = 0xFF
datachip.gppu = 0xFF
datachip.defval = 0xff
datachip.gpinten = 0x89
datachip.intcon = 0xFF
