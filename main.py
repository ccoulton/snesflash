import pycom
import network
import utime
import usys
from machine import I2C
from pycom_mcp230xx import MCP23008, MCP23017
from micropython import const

HIROMPAGE  = const(65536)
LOWROMPAGE = const(32768)

class SnesCart:
    def __init__(self, address=0x20, bank=0x21, data=0x22):
        i2c = I2C(0, I2C.MASTER)
        i2c.init(I2C.MASTER, baudrate=400000)
        self.addrchip = MCP23017(i2c, address)
        self.bankchip = MCP23008(i2c, bank)
        self.datachip = MCP23008(i2c, data)
        self.addrchip.iodir = 0x0000 #set bankA and B as output on mcp23017

        self.bankchip.iodir = 0x00 #set bankchip as OUTPUT set mcp23008 as output`
        self.datachip.iodir = 0xFF #set datachip as input set mcp23008 as input`

        self.datachip.gppu = 0xFF #enable pullups
        self.datachip.defval = 0xff #expect snes data to defaul at 0xff`
        self.datachip.gpinten = 0x89 #set up some of the pins to be inqenable
        self.datachip.intcon = 0xFF #compares irq to defval
        #TODO, set up ioControls
        #io7 /irq input, io4 cart_pow | io3 /cs | io2 /wr | io1 /rst | io0 /rd outputs
        #write io x60
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
        self.datachip.defval = 0xff
        self.datachip.gpinten = 0x00
        self.addrchip.iodir = 0xFFFF
        self.bankchip.iodir = 0xFF
        self.datachip.iodir = 0xFF

    @isLowROM.setter
    def isLowROM(self, val):
        self.isLowROM = val

    def gotoAddr(self, addr, isLowROM=self.isLowROM):
        if addr <= 0xffff:
            upByte = int(addr/256)
            lowByte = addr - (upByte*256)
            self.currentAddr = addr
            if isLowROM:
                upByte = upByte | 0x80
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

    def read32(self, addr, isLowROM=self.isLowROM):
        output = self.readAddr(addr, isLowROM)
        output += self.readAddr(addr+1, isLowROM)*256
        return output

    def readAddr(self, addr, isLowROM=self.isLowROM):
        self.gotoAddr(addr, isLowROM)
        return datachip.gpio

    def readAddrBank(self, addr, bank):
        self.gotoBank(bank)
        self.gotoAddr(addr, False)
        return self.datachip.gpio

    def gotoOffset(self, offset, isLowROM=self.isLowROM):
        if not isLowROM:
            bank = int( offset / HIROMPAGE) #64k pages
            addr = offset - (bank*HIROMPAGE)
        else:
            bank = int( offset / LOWROMPAGE)
            addr = offset - ( bank * LOWROMPAGE)

        self.gotoBank(bank)
        self.gotoAddr(addr, isLowROM)
        self.currentOffset = offset

    def readOffset(self, offset, isLowROM=self.isLowROM):
        self.gotoOffset(offset, isLowROM)
        return datachip.gpio

    def compareROMChecksums(self, header, isLowROM=self.isLowROM):
        if isLowROM:
            pass #0 /rd, 1 /reset, 2 /wr, 3 /cs, 4 cart mosfet/power?, 7 /irq
            #hold reset, and power high.
            #write to io controls 0x06 which should be reset?
        currentOffset = header + 28
        inverseChecksum = self.readOffset(currentOffset, isLowROM)
        inverseChecksum += self.readOffset(currentOffset+1, isLowROM)*256
        print "inverseChecksum: " + str( hex(inverseChecksum))

        currentOffset = header + 30

        checksum = self.readOffset(currentOffset, isLowROM)
        checksum += self.readOffset(currentOffset+1, isLowROM)*256
        print "checksum: " + str(hex(checksum))

        return True if (inverseChecksum ^ checksum) == 0xffff else False

    def getROMsize(self, offset, isLowROM=self.isLowROM):
        ROMsizeReg = self.readOffset(offset, isLowROM)
        ROMsizeReg -= 7
        return pow(2, ROMsizeReg) if ROMsizeReg >=0 else -1

    def getNumOfPages(self, actualROMSize, isLowROM=self.isLowROM):
        actualROMSize *= 2
        if isLowROM:
            actualROMSize *= 2
        return actualROMSize

    def ripROM(self, startBank, numberOfPages, isLowROM=self.isLowROM):
        ROMdata = ""
        pageChecksum = 0
        currentByte = 0
        bank = 0
        if isLowROM:
            startOffset = startBank * 0x8000
        else:
            startOffset = startBank * 0x1000
        offset = startOffset
        self.gotoOffset(startOffset, isLowROM)
        print "---Start Cart Read----\n"
        for bank in range(startBank, (numberOfPages + startBank)):
            print"currentBank: dec: " + str(self.currentBank) + "; Hex: "+str(hex(self.currentBank))
        while bank == self.currentBank:
            currentByte = self.datachip.gpio
            ROMdata +=str(currentByte)
            pageChecksum += currentByte
            offset += 1
            self.gotoOffset(offset, isLowROM)

        if not isLowROM or (isLowROM and self.currentBank % 2 == 0):
            print " - Page checksum: " + str( pageChecksum)
            self.totalChecksum += pageChecksum
            pageChecksum = 0
            print "\nCurrent checksum: "+str(self.totalChecksum)+" | Hex: "+str(hex(self.totalChecksum))
            #print "Header checksum: "+str(hex(ROMchecksum))+"\n"
        return ROMdata

    def ripSRAM(self, SRAMsize, ROMsize, isLowROM=self.isLowROM):
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
            #TODO write ioControls x0e, reset + wr + cs + cart power + rst
        #io7: /irq | io4: cart power | io3: /cs | io2: /wr | io1: /rst | io0 /rd
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
        #io.gpio = 0x06 # reset + wr high
        print str(currentByte) + "SRM bytes read"
        return SRAMdata

def returnNULLheader(self):
    return str(0x00) * 512

def getUpNibble(vale):
    return int(value/16)

def getLowNibble(value):
    return (value - (getUpNibble(value)*16))

def splitByte(value):
    return getUpNibble(value), getLowNibble(value)

def main():
    #setup
    pycom.heartbeat(False)
    pycom.rgbled(0x000015)
    directory = ""
    readSRAM = True
    readCart = True
    cart = SnesCart()
    convertedSRAMsize = 0
    val = 0
    databyte = ""
    #todo set cart power, and reset high
    utime.sleep(.25)
    cartname = ""
    headerAddr = 32704
    isValid = False

    if cart.compareROMChecksums(32704,True):
        print "Checksums Matched"
        ROMmakeup = cart.readOffset(headerAddr + 21, isLowROM)
        ROMSpeed, bankSize = splitByte(ROMmakeup)

        if bankSize == 0:
            print "Rom Makeup Match for LowRom"
            cart.isLowROM = True
            isValid = True
        elif bankSize == 1:
            print "Rom Make up Match for HiRom"
            cart.isLowROM = False
            isValid = True
            headerAddr = 65472
        else:
            print "Bank Config Read Error"
    else:
        print "Checksums didn't match."
    currentAddr = headerAddr
    cart.gotoOffset(headerAddr):
    for index in range(headerAddr, (headerAddr+20)):
        cartname += str(cart.readOffset(index))
    ROMmakeup = cart.readAddr(headerAddr+21)
    ROMspeed, bankSize = splitByte(ROMmakeup)
    ROMtype = cart.readAddr(headerAddr+ 22)
    ROMsize = cart.getROMsize(headerAddr+23)
    SRAMSize = cart.readAddr(headerAddr+24)
    county = cart.readAddr(headerAddr+25)
    license = cart.readAddr(headerAddr+26)
    version = cart.readAddr(headerAddr+27)

    currentAddr = headerAddr + 28
    inverseChecksum = cart.read32(currentAddr)

    currentAddr += 2
    checksum = cart.read32(currentAddr)

    currentAddr += 2
    VBLvector = cart.read32(currentAddr)

    currentAddr += 2
    resetVector = read32(currentAddr)

    numberOfPages = cart.getNumOfPages(ROMsize)
    print "Game Title:  "+cartname
    print "Rom Makeup:  "+str(ROMmakeup)
    print "-Rom Speed:  "+str(ROMSpeed)
    print "-Bank Size:  "+str(bankSize)
    print "ROM Type:  "+str(ROMtype)

    if ROMtype == 243:
        print"\nCapcom CX4 Rom Type Detected!"
        #
        print ""

    print "Rom Size:  "+str(ROMsize)+" Mbits"
    print "SRAM Size: Value: " +str(SRAMsize),
    if convertedSRAMsize == 0 and (SRAMsize <= 12 and SRAMsize > 0):
        convertedSRAMsize = 1<<(SRAMsize+3)
    print " | " + str(convertedSRAMsize) + "Kbits"

    print "Country:  "+str(county)
    print "license:  "+str(license)
    print "Version:  1."+str(version)
    print "invChkS:  "+str(hex(inverseChecksum))
    print "RomChkS:  "+str(hex(checksum))
    print "XORChkS:  "+str(hex(inverseChecksum | checksum))
    print ""
    print "VBL Vector:  "+ str(VBLvector)
    print "RST Vector:  "+ str(resetVector)
    print ""
    print "#ofPages:  "+str(numberOfPages)
    print ""

    data = ""
    dump = returnNULLheader()
    y = 0
    pageChecksum = 0
    totalChecksum= 0
    currentByte = 0
    numOfRemainPages =0
    firstNumberOfPages =0

    if directory != "" and directory[len(directory)-1] != "/":
        directory +="/"
    g = open("/tmp/insertedCart", 'w')

    if isValid:
        g.write(cartname)
    if readCart and os.path.exists(directory + cartname+ '.smc'):
        print "rom exists not dumping again"
        readCart = False
    elif readCart:
        print "Will not dump cart due to Options"

    if readCart:
        numOfRemainPages = 0
        firstNumberOfPages = numberOfPages
        timeStart = utime.time()

    file = open(directory + cartname + '.smc', 'w')

    if isLowROM:
        print "reading"+ str(numberOfPages)+ "low Rom Pages."
        data = cart.ripROM(0x00, firstNumberOfPages)
    else:
        if numberOfPages > 64:
            numOfRemainPages = (numberOfPages - 64)
            print "reading first of 64 of "+str(numberOfPages)+ "hi Rom Pages"
            firstNumberOfPages = 64
        else:
            print "reading "+ str(numberOfPages) + "Hi Rom Pages"
        data = cart.ripROM(0xc0, firstNumberOfPages)

        if numOfRemainPages > 0
            print "reading last "+str(numOfRemainPages) + "of High rom pages."
            data += cart.ripROM(0x40, firstNumberOfPages)
    print ("\nEntire Checksum: "+str(hex(cart.totalChecksum)))
    print ("\nHeader Checksum: "+str(hex(ROMchecksum)))
    cart.totalChecksum = (cart.totalChecksum & 0xFFFF)

    print "16-bit generated Checksum:  "+str(hex(cart.totalChecksum))

    print "checksum ok" if cart.totalChecksum == ROMchecksum else "checksum bad"
    timeEnd = utime.time()
    print "\nIt Took "+str(timeEnd - timeStart) + " seconds to read the cart"

    file.write(data)
    file.close()

    if readSRAM:
        file = open(directory+cartname+'.srm','w')
        timeStart = utime.time()
        dump = cart.ripSRAM(convertedSRAMsize, ROMsize)
        timeEnd = utime.time()
        print ""
        print "It Took "+ str(timeEnd-timeStart) + "seconds to Read SRAM data"
        file.write(dump)
        file.close()
    else:
        g.write("NULL")
        g.close()
