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
addrchip = MCP23017(i2c, bus[0]) #init mcp23017 chip`
bankchip = MCP23008(i2c, bus[1]) #init mcp23008 chip
datachip = MCP23008(i2c, bus[2]) #inic mcp23008

addrchip.iodir = 0x0000 #set bankA and B as output on mcp23017

bankchip.iodir = 0x00 #set bankchip as OUTPUT set mcp23008 as output`
datachip.iodir = 0xFF #set datachip as input set mcp23008 as input`

datachip.gppu = 0xFF #enable pullups
datachip.defval = 0xff #expect snes data to defaul at 0xff`
datachip.gpinten = 0x89 #set up some of the pins to be inqenable
datachip.intcon = 0xFF #compares irq to defval
