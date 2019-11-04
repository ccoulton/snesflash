#import pycom
# p0-12 on rst side, p13-23 on vin side
import utime
import sys
from machine import I2C, Pin
#sd p23 sdclk, p4 sdcmd, p8 sddata0
#i2c p10 sda, p9 scl wipy
'''
pwr= Pin('P12',  mode=Pin.OUT)
cs = Pin('P8', mode=Pin.OUT)
wr = Pin('P7',  mode=Pin.OUT)
rst= Pin('P6', mode=Pin.OUT)
rd = Pin('P5',  mode=Pin.OUT)
'''
from pycom_mcp230xx import pycom_mcp230xx as mcp230xx
#i2c 1 scl, 2 sda mcp23008 12 scl, 13 sda mcp23017
from micropython import const

HIROMPAGE  = const(65536)
LOWROMPAGE = const(32768)
_PWR = const(0x10)
_CS  = const(0x08)
_WR  = const(0x04)
_RST = const(0x02)
_RD  = const(0x01)

class SnesCart:
    def __init__(self, address=0x20, bank=0x21, data=0x22):
        i2c = I2C(0, I2C.MASTER)
        i2c.init(I2C.MASTER, baudrate=100000)
        self.addrchip = mcp230xx.MCP23017(i2c, address)
        self.bankchip = mcp230xx.MCP23008(i2c, bank)
        self.datachip = mcp230xx.MCP23008(i2c, data)
        self.addrchip.iodir = 0x0000 #set bankA and B as output on mcp23017

        self.bankchip.iodir = 0x00 #set bankchip as OUTPUT set mcp23008 as output`
        self.datachip.iodir = 0xFF #set datachip as input set mcp23008 as input`

        self.datachip.gppu = 0xFF #enable pullups
        self.datachip.defval = 0xff #expect snes data to defaul at 0xff`
        self.datachip.gpinten = 0x89 #set up some of the pins to be interrupts?
        self.datachip.intcon = 0xFF #compares irq to defval
        self.isLowROM = False
        self.currentAddr = -1
        self.currentUpByte = -1
        self.currentLowByte= -1
        self.currentBank = -1
        self.currentOffset = 0
        self.totalChecksum = 0

    def __del__(self):
        self.gotoAddr(00, 0)
        self.gotoBank(00)
        self.datachip.gppu = 0x00
        self.datachip.defval = 0x00
        self.datachip.gpinten = 0x00
        self.addrchip.iodir = 0xFFFF
        self.bankchip.iodir = 0xFF
        self.datachip.iodir = 0xFF
        pwr(False)

    def gotoAddr(self, addr, isLowROM=None):
        isLowROM = self.isLowROM if isLowROM is None else isLowROM
        if addr <= 0xffff:
            upByte = int(addr/256)
            lowByte = addr - (upByte*256)
            self.currentAddr = addr
            if isLowROM: #is not 0
                upByte = upByte | 0x80 # or's 1 to a15 if LoRom
            if self.currentUpByte != upByte:
                self.addrchip.gpiob = upByte
                self.currentUpByte = upByte
            if self.currentLowByte != lowByte:
                self.addrchip.gpioa = lowByte
                self.currentLowByte = lowByte
        else:
            self.addrchip.gpio = 0x0000
            self.currentAddr = 0

    def gotoBank(self, bank):
        if bank != self.currentBank:
            self.bankchip.gpio = bank
            self.currentBank = bank

    def read2Byte(self, addr, isLowROM = None):
        isLowROM = self.isLowROM if isLowROM is None else isLowROM
        output = int.from_bytes(self.readAddr(addr, isLowROM), 'big')
        output += int.from_bytes(self.readAddr(addr+1, isLowROM), 'big')*256
        return output

    def readAddr(self, addr, isLowROM=None):
        isLowROM = self.isLowROM if isLowROM is None else isLowROM
        self.gotoAddr(addr, isLowROM)
        return self.datachip.gpio

    def readAddrBank(self, addr, bank):
        self.gotoBank(bank)
        self.gotoAddr(addr, False)
        return self.datachip.gpio

    def gotoOffset(self, offset, isLowROM=None):
        isLowROM = self.isLowROM if isLowROM is None else isLowROM
        if not isLowROM:
            bank = int( offset / HIROMPAGE) #64k pages
            addr = offset - (bank*HIROMPAGE)
        else:
            bank = int( offset / LOWROMPAGE)
            addr = offset - ( bank * LOWROMPAGE)

        self.gotoBank(bank)
        self.gotoAddr(addr, isLowROM)
        self.currentOffset = offset

    def readOffset(self, offset, isLowROM=None):
        isLowROM = self.isLowROM if isLowROM is None else isLowROM
        self.gotoOffset(offset, isLowROM)
        return int.from_bytes(self.datachip.gpio, 'big')

    def compareROMChecksums(self, header, isLowROM=None):
        isLowROM = self.isLowROM if isLowROM is None else isLowROM
        self.readRom()
        currentOffset = header + 28
        print(hex(self.readOffset(currentOffset, isLowROM)))
        print(hex(self.readOffset(currentOffset+1, isLowROM)))

        currentOffset = header + 30

        checksum = self.readOffset(currentOffset, isLowROM)
        checksum += self.readOffset(currentOffset+1, isLowROM)*256
        print("checksum: " , hex(checksum))
        return (checksum ^ inverseChecksum == 0xffff)

    def getROMsize(self, offset, isLowROM=None):
        isLowROM = self.isLowROM if isLowROM is None else isLowROM
        ROMsizeReg = self.readOffset(offset, isLowROM)
        ROMsizeReg -= 7
        return pow(2, ROMsizeReg) if ROMsizeReg >=0 else -1

    def getNumOfPages(self, actualROMSize, isLowROM=None):
        isLowROM = self.isLowROM if isLowROM is None else isLowROM
        actualROMSize *= 2
        if isLowROM:
            actualROMSize *= 2
        return actualROMSize

    def CX4setROMSize(self, ROMsize):
        self.gotoOffset(0x007f52,False)
        ROMSizeRegister = self.datachip.gpio
        print("$007F52 offset reads  "+str(ROMSizeRegister))
        self.datachip.iodir = 0x00
        self._ioControls(0x13)
        if ROMsize > 8:
            if ROMSizeRegister == 1:
                print("ROM is larger than 8 megs, writing 0x00 to cx4 reg")
                self.datachip.gpio = 0x00
            else:
                print("CX4 register is at correct value, will not change")
        else:
            if ROMSizeRegister == 1:
                print("CX4 Register is at Correct value, will not change")
            else:
                print("ROM is 8 megs, writing 0x01 to CX4 register")
                self.datachip.gpio = 0x01
        self.readRom()
        self.datachip.iodir = 0xFF
        print("$007F52 offset now reads "+str(self.datachip.gpio))

    def ripROM(self, startBank, numberOfPages, isLowROM=None):
        isLowROM = self.isLowROM if isLowROM is None else isLowROM
        ROMdata = ""
        pageChecksum = 0
        currentByte = 0
        bank = 0
        startOffset = startBank* 0x8000 if isLowROM else startBank * 0x10000
        offset = startOffset
        self.gotoOffset(startOffset, isLowROM)
        print("---Start Cart Read----\n")
        for bank in range(startBank, (numberOfPages + startBank)):
            print("currentBank: dec: " + str(self.currentBank) + "; Hex: "+str(hex(self.currentBank)))
        while bank == self.currentBank:
            currentByte = self.datachip.gpio
            ROMdata += str(currentByte)
            pageChecksum += currentByte
            offset += 1
            self.gotoOffset(offset, isLowROM)

        if not isLowROM or (isLowROM and self.currentBank % 2 == 0):
            print(" - Page checksum: " + str( pageChecksum))
            self.totalChecksum += pageChecksum
            pageChecksum = 0
            print("\nCurrent checksum: "+str(self.totalChecksum)+" | Hex: "+str(hex(self.totalChecksum)))
            print("Header checksum: "+str(hex(ROMchecksum))+"\n")
        return ROMdata

    def ripSRAM(self, SRAMsize, ROMsize, isLowROM=None):
        isLowROM = self.isLowROM if isLowROM is None else isLowROM
        SRAMdata = ""
        pageChecksum = 0
        currentByte = 0
        bank = 0
        startBank = 0
        startAddr = 0
        endAddr = 0x7fff
        if isLowROM:
            startBank = 0x70
            startAddr = 0x0000
            endAddr = 0x7fff
        else:
            startBank = 0x30
            startAddr = 0x6000
            endAddr = 0x7fff
            self.ioControls(0x1e) #reset + wr + cs + cart power 0x0e w/ pmosfet
        SRAMsize = (SRAMsize / 8.0) * 1024
        self.gotoBank(startBank)
        self.gotoAddr(startAddr, False)
        while SRAMsize > currentByte:
            currentByte += 1
            SRAMdata += str(self.datachip.gpio)
            if self.currentAddr >= endAddr:
                self.gotoBank(self.currentBank +1)
                self.gotoAddr(startAddr, False)
            else:
                self.gotoAddr(self.currentAddr +1, False)
        self.ioControls(0x16) # pwr, rst, and cs high, 0x06 for pmosfet
        print(str(currentByte) + "SRAM bytes read")
        return SRAMdata

    #readRom = /rd /cs /reset low, /wr hi
    def readRom(self):  #0x14\
        self._ioControls(_PWR | _WR)

'''
# readSram=
#     lowrom: /cs /rd low, /rst /wr high, a15 ba4 ba5 hi
#     higrom: /rd low, /rst /wr /cs high, a13 a14 ba5 hi
'''
    def readSRAM(self, isLowROM=None):
        isLowROM = self.isLowROM if isLowROM is None else isLowROM
        if isLowROM:        #0x16
            self._ioControls(_PWR | _RST | _WR)
        else:               #0x1e
            self._ioControls(_PWR | _RST | _WR | _CS)

'''
# writsram=
#    lowrom: /cs /wr low, /rst /rd high, a15 ba4 ba5 hi
#    higrom: /wr /low, /rst /rd cs high, a13 a14 ba5 hi
'''
    def writeSRAM(self,isLowROM=None):
        isLowROM = self.isLowROM if isLowROM is None else isLowROM
        if isLowROM:        #0x11
            self._ioControls(_RST | _RD)
        else:               #0x19
            self._ioControls(_RST | _RD | _CS)

'''
#commands come in as hex, originally used pmosfet, so power was low active
# irq|x|x|pwr // cs|wr|rst|rd
#io7: /irq | io4: cart power | io3: /cs | io2: /wr | io1: /rst | io0 /rd
'''
    def _ioControls(self, inputs):
        bools = []
        for index in range(8):
            bools.append(inputs & 1)
            inputs = inputs >> 1
        pwr(bools[4])
        cs(bools[3])
        wr(bools[2])
        rst(bools[1])
        rd(bools[0])

pwr= Pin('P12',  mode=Pin.OUT)
cs = Pin('P8', mode=Pin.OUT)
wr = Pin('P7',  mode=Pin.OUT)
rst= Pin('P6', mode=Pin.OUT)
rd = Pin('P5',  mode=Pin.OUT)
#irq= Pin('P7',  mode=Pin.IN)

def returnNULLheader():
    return chr(0x00) * 512

def getUpNibble(value):
    return value >> 4

def getLowNibble(value):
    return value & 0x0F

def splitByte(value):
    return getUpNibble(value), getLowNibble(value)

def main():
'''embedded cart info end of first page,
    32704/7fc0:lowrom
    65472/ffc0:highrom'''
    directory = ""
    readSRAM = True
    readCart = True
    cart = SnesCart()
    convertedSRAMsize = 0
    val = 0
    databyte = ""
    cart.readRom()
    utime.sleep(.25)
    cartname = ""
    headerAddr = 32704
    isValid = False

    if cart.compareROMChecksums(headerAddr,True):
        print("Checksums Matched")
        ROMmakeup = cart.readOffset(headerAddr + 21, True)
        print(hex(ROMmakeup))
        ROMSpeed, bankSize = splitByte(ROMmakeup)

        if bankSize == 0:
            print("Rom Makeup Match for LowRom")
            cart.isLowROM = True
            isValid = True
        elif bankSize == 1:
            print("Rom Make up Match for HiRom")
            cart.isLowROM = False
            isValid = True
            headerAddr = 65472
        else:
            print("Bank Config Read Error")
    else:
        print("Checksums didn't match.")
        return
    currentAddr = headerAddr
    cart.gotoOffset(headerAddr)
    cart.readOffset(headerAddr)
    for index in range(headerAddr, (headerAddr+20)):
        cartname += chr(cart.readOffset(index))
    ROMmakeup = cart.readAddr(headerAddr+21)
    ROMSpeed = getUpNibble(ROMmakeup)
    bankSize = getLowNibble(ROMmakeup)
    #ROMspeed, bankSize = splitByte(ROMmakeup)
    ROMtype = cart.readAddr(headerAddr+ 22)
    ROMsize = cart.getROMsize(headerAddr+23)
    SRAMSize = cart.readAddr(headerAddr+24)
    county = cart.readAddr(headerAddr+25)
    license = cart.readAddr(headerAddr+26)
    version = cart.readAddr(headerAddr+27)

    currentAddr = headerAddr + 28
    inverseChecksum = cart.read32(currentAddr)

    currentAddr += 2
    checksum = cart.read2Byte(currentAddr)

    currentAddr += 2
    VBLvector = cart.read2Byte(currentAddr)

    currentAddr += 2
    resetVector = cart.read2Byte(currentAddr)

    numberOfPages = cart.getNumOfPages(ROMsize)
    print("Game Title:  "+cartname)
    print("Rom Makeup:  "+str(ROMmakeup))
    print("-Rom Speed:  "+str(ROMSpeed))
    print("-Bank Size:  "+str(bankSize))
    print("ROM Type:  "+str(ROMtype))

    if ROMtype == 243:
        print("\nCapcom CX4 Rom Type Detected!")
        cart.CX4setROMSize(ROM.size)
        print("")

    print("Rom Size:  "+str(ROMsize)+" Mbits")
    print("SRAM Size: Value: " +str(SRAMsize))
    if convertedSRAMsize == 0 and (SRAMsize <= 12 and SRAMsize > 0):
        convertedSRAMsize = 1<<(SRAMsize+3)
        print(convertedSRAMsize)
    print(" | " + str(convertedSRAMsize) + "Kbits")

    print("Country:  "+str(county))
    print("license:  "+str(license))
    print("Version:  1."+str(version))
    print("invChkS:  "+str(hex(inverseChecksum)))
    print("RomChkS:  "+str(hex(checksum)))
    print("XORChkS:  "+str(hex(inverseChecksum | checksum)))
    print("\nVBL Vector:  "+ str(VBLvector))
    print("RST Vector:  "+ str(resetVector))
    print("\n#ofPages:  "+str(numberOfPages))
    print("")

    dump = returnNULLheader()
    y = 0
    pageChecksum = 0
    totalChecksum= 0
    currentByte = 0
    numOfRemainPages =0
    firstNumberOfPages =0

    if directory != "" and directory[len(directory)-1] != "/":
        directory +="/"
    g = open("/sd/tmp/insertedCart", 'w')

    if isValid:
        g.write(cartname)
        if readCart:
            if os.path.exists(directory + cartname+ '.smc'):
                print("rom exists not dumping again")
                readCart = False
        elif readCart:
            print("Will not dump cart due to Options")

        if readCart:
            numOfRemainPages = 0
            firstNumberOfPages = numberOfPages
            timeStart = utime.time()

            file = open(directory + cartname + '.smc', 'w')

            if isLowROM:
                print("reading"+ str(numberOfPages)+ "low Rom Pages.")
                data = cart.ripROM(0x00, firstNumberOfPages)
            else:
                if numberOfPages > 64:
                    numOfRemainPages = (numberOfPages - 64)
                    print("reading first of 64 of "+str(numberOfPages)+ "hi Rom Pages")
                    firstNumberOfPages = 64
                else:
                    print("reading "+ str(numberOfPages) + "Hi Rom Pages")
                data = cart.ripROM(0xc0, firstNumberOfPages)

                if numOfRemainPages > 0:
                    print("reading last "+str(numOfRemainPages) + "of High rom pages.")
                    data += cart.ripROM(0x40, firstNumberOfPages)

            print(("\nEntire Checksum: "+str(hex(cart.totalChecksum))))
            print(("\nHeader Checksum: "+str(hex(ROMchecksum))))
            cart.totalChecksum = (cart.totalChecksum & 0xFFFF)

            print("16-bit generated Checksum:  "+str(hex(cart.totalChecksum)))
            print("checksum ok" if cart.totalChecksum == ROMchecksum else "checksum bad")
            timeEnd = utime.time()
            print("\nIt Took "+str(timeEnd - timeStart) + " seconds to read the cart")

            file.write(data)
            file.close()

        if readSRAM:
            with open(directory+cartname+'.srm','w') as file:
                timeStart = utime.time()
                dump = cart.ripSRAM(convertedSRAMsize, ROMsize)
                timeEnd = utime.time()
                print("\nIt Took "+ str(timeEnd-timeStart) + "seconds to Read SRAM data")
                file.write(dump)
    else:
        g.write("NULL")
        g.close()
