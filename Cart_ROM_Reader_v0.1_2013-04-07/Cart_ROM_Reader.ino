/*******************************************************************************

  Name      : Cart ROM-Reader
              (for reading SNES-/SFC-Game Cartridges with an Arduino)
  
  Author    : Michael Kovacs
  
  Date      : 2013-04-07
  
  Version   : 0.1
  
  Descr.    : Program that reads ROM-data from an SNES cart and writes this
              data to serial out of Arduino.

  Usage     : Please find further details including references and 
              acknowledgements in the README-file.
            
  Debugging : If you set debugLevel > 0, only debug info will be sent to serial 
              out, not the actual ROM-data!
            
  License   : Copyright (C) 2013  Michael Kovacs

              This program is free software: you can redistribute it and/or modify
              it under the terms of the GNU General Public License as published by
              the Free Software Foundation, either version 3 of the License, or
              (at your option) any later version.

              This program is distributed in the hope that it will be useful,
              but WITHOUT ANY WARRANTY; without even the implied warranty of
              MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
              GNU General Public License for more details.

              You should have received a copy of the GNU General Public License
              along with this program.  If not, see <http://www.gnu.org/licenses/>.

 Disclaimer : This program is NOT connected or affiliated with any mentioned 
              company in any way. All trademarks are property of their 
              respective holders.

              You may use this program for reading game cartridges only in 
              compliance with the copyright and intellectual property rights 
              of the respective owners!

 *******************************************************************************/

// TODO: Improve detection of e.g. 24 / 48 megabit carts - are currently overdumped...
// TODO: Implement checksum checking - create checksum on-the-fly and compare the result to the interal checksum of the cart... What to do over serial connection, when the checksums mismatch???

// Pin connected to ST_CP of 74HC595
int latchPin = 10;
// Pin connected to SH_CP of 74HC595
int clockPin = 11;
// Pin connected to DS of 74HC595
int dataPin = 12;
// Input Pins for D0-D7
int d0Pin = 2;
int d1Pin = 3;
int d2Pin = 4;
int d3Pin = 5;
int d4Pin = 6;
int d5Pin = 7;
int d6Pin = 8;
int d7Pin = 9;
//IRQ Pin
int irqPin = 13;

int dumpWait = 50;     // Delay in microseconds between setting address @ shiftout-registers and reading data lines

int debugLevel = 0;

int verifySORead = 0;  // Only used for Star Ocean reading: 0 = read every byte once; 1 = read every byte at least twice and keep reading if those do not match
    // Needed to implement this because 2 dumps of Star Ocean differed in some bytes, whereas all other carts without S-DD1 dumped correct (every single bit... :-) )
    // Attention: Setting this to 1 practically doubles the dumping time to 16 minutes per 8 megabits...

// The following variables will be automatically set based on the information in the cart's header
unsigned long romChecksum = 0;
unsigned long inverseRomChecksum = 0;
unsigned long crc32Checksum = 0;
int romSpeed = 0;      // 0 = SlowROM, 3 = FastROM
int romType = 0;       // 0 = LoROM, 1 = HiROM
int romChips = 0;      // 0 = ROM only, 1 = ROM & RAM, 2 = ROM & Save RAM,  3 = ROM & DSP1, 4 = ROM & RAM & DSP1, 5 = ROM & Save RAM & DSP1, 19 = ROM & SFX
                       // 227 = ROM & RAM & GameBoy data, 246 = ROM & DSP2
int romSize = 0;       // ROM-Size in megabits
int numBanks = 0;
int sramSize = 0;      // SRAM-Size in kilobits
int cartCountry = 255;
int cartLicense = 0;
int gameVersion = 0;

void setup() {
  
  Serial.begin(115200);
  
  pinMode(latchPin, OUTPUT);
  pinMode(clockPin, OUTPUT);
  pinMode(dataPin, OUTPUT);
  pinMode(d0Pin, INPUT);
  pinMode(d1Pin, INPUT);
  pinMode(d2Pin, INPUT);
  pinMode(d3Pin, INPUT);
  pinMode(d4Pin, INPUT);
  pinMode(d5Pin, INPUT);
  pinMode(d6Pin, INPUT);
  pinMode(d7Pin, INPUT);
  pinMode(irqPin, INPUT);
  
  // Activate pull-up resistors for input-pins
  digitalWrite(d0Pin, HIGH);
  digitalWrite(d1Pin, HIGH);
  digitalWrite(d2Pin, HIGH);
  digitalWrite(d3Pin, HIGH);
  digitalWrite(d4Pin, HIGH);
  digitalWrite(d5Pin, HIGH);
  digitalWrite(d6Pin, HIGH);
  digitalWrite(d7Pin, HIGH);
  digitalWrite(irqPin, HIGH);
  
  delay(500);
}

void loop() {
  
  delay(5000);
  
  if (debugLevel >= 2)
    dumpHeader();

  // Read checksum bytes and check, if valid
  if (debugLevel >= 1)
    Serial.println("Checking ROM-checksum...");
  do {
    romChecksum = word(dumpByte(0, 65500)) + (word(dumpByte(0, 65501)) * 256);
    inverseRomChecksum = word(dumpByte(0, 65502)) + (word(dumpByte(0, 65503)) * 256);
    if (debugLevel >= 2) {
      Serial.println(romChecksum);
      Serial.println(inverseRomChecksum);
    }
    delay(1000);
  } while ( (romChecksum + inverseRomChecksum) != 65535 );
  
  // Check if LoROM or HiROM
  if (debugLevel >= 1)
    Serial.println("Checking ROM-type...");
  romType = (dumpByte(0, 65493) & 1);
    if (debugLevel >= 2) {
      Serial.println(romType);
    }

  // Check RomSpeed
  if (debugLevel >= 1)
    Serial.println("Checking ROM-speed...");
  romSpeed = (dumpByte(0, 65493) >> 4);
    if (debugLevel >= 2) {
      Serial.println(romSpeed);
    }

  // Check RomChips
  if (debugLevel >= 1)
    Serial.println("Checking what chips are on the cart...");
  romChips = dumpByte(0, 65494);
    if (debugLevel >= 2) {
      Serial.println(romChips);
    }

  // Check RomSize
  if (debugLevel >= 1)
    Serial.println("Checking ROM-size...");
  byte romSizeExp = dumpByte(0, 65495) - 7;
  romSize = 1;
  while (romSizeExp--)
    romSize *= 2;
  numBanks = (long(romSize / 8) * 1024 * 1024) / (32768 + (long(romType) * 32768));
  if (debugLevel >= 2) {
    Serial.print("ROM-size MBit: ");
    Serial.println(romSize);
    Serial.print("ROM-Banks: ");
    Serial.println(numBanks);
  }
  
  // Check SramSize
  if (debugLevel >= 1)
    Serial.println("Checking SRAM-size...");
  byte sramSizeExp = dumpByte(0, 65496);
  if (sramSizeExp != 0) {
    sramSizeExp = sramSizeExp + 3;
    sramSize = 1;
    while (sramSizeExp--)
      sramSize *= 2;
  } else {
    sramSize = 0;
  }
  if (debugLevel >= 2) {
    Serial.print("SRAM-size kBit: ");
    Serial.println(sramSize);
  }
  
  // Check Cart Country
  if (debugLevel >= 1)
    Serial.println("Checking cart country byte...");
  cartCountry = dumpByte(0, 65497);
    if (debugLevel >= 2) {
      Serial.println(cartCountry);
    }

  // Check Cart License Byte (i.e. the game-vendor?!)
  if (debugLevel >= 1)
    Serial.println("Checking cart license byte...");
  cartLicense = dumpByte(0, 65498);
    if (debugLevel >= 2) {
      Serial.println(cartLicense);
    }

  // Check Game Version
  if (debugLevel >= 1)
    Serial.println("Checking game version...");
  gameVersion = dumpByte(0, 65499);
    if (debugLevel >= 2) {
      Serial.println(gameVersion);
    }

  // Dump ROM
  // Read ROM from command line in linux as root using:  (stty raw; cat > rom.sfc) < /dev/ttyACM0
  if (debugLevel >= 1)
    Serial.println("Dumping ROM...");
  long dumpedBytes = 0;
  
  // Star Ocean detection - see below...
  if (romChips != 69) {
    
    // Check if LoROM or HiROM...
    if (romType == 0) {
  
      if (debugLevel >= 2)
        Serial.println("Starting Lo-type dump...");
  
      // Read up to 96 banks starting at bank 0×00.
      
      for(int currBank=0; currBank < numBanks; currBank++) {
        if (debugLevel >= 2) {
          Serial.print("Dumping bank ");
          Serial.print(currBank);
          Serial.println("...");
        }
        for(long currByte=32768; currByte < 65536; currByte++) {
          if (debugLevel == 0)
            Serial.write(dumpByte(currBank, currByte));
          else
            dumpByte(currBank, currByte);
          dumpedBytes++;
        }
        if (debugLevel >= 2) {
          Serial.print("Total dumped bytes: ");
          Serial.println(dumpedBytes);
        }
      }
      
    } else {
      // Dump High-type ROM
      
      if (romSize <= 32) {
  
        // If Romsize <= 32 mbit, read up to 64 banks beginning at 0xc0.
        
        if (debugLevel >= 2)
          Serial.println("Starting Hi-type dump of <= 32mbit...");
        
        for(int currBank=192; currBank < (numBanks + 192); currBank++) {
          if (debugLevel >= 2) {
            Serial.print("Dumping bank ");
            Serial.print(currBank);
            Serial.println("...");
          }
          for(long currByte=0; currByte < 65536; currByte++) {
            if (debugLevel == 0)
              Serial.write(dumpByte(currBank, currByte));
            else
              dumpByte(currBank, currByte);
            dumpedBytes++;
          }
          if (debugLevel >= 2) {
            Serial.print("Total dumped bytes: ");
            Serial.println(dumpedBytes);
          }
        }
  
      } else {
        
        // If Romsize > 32 mbit, read the first 64 banks beginning at 0xc0 and the rest (max. 32?!) starting at bank 0×40.
        // THIS PART OF THE CODE IS UNTESTED AS I DO NOT OWN SUCH A CART!!!

        if (debugLevel >= 2)
          Serial.println("Starting Hi-type dump of > 32mbit...");
        
        for(int currBank=192; currBank < 256; currBank++) {
          if (debugLevel >= 2) {
            Serial.print("Dumping bank ");
            Serial.print(currBank);
            Serial.println("...");
          }
          for(long currByte=0; currByte < 65536; currByte++) {
            if (debugLevel == 0)
              Serial.write(dumpByte(currBank, currByte));
            else
              dumpByte(currBank, currByte);
            dumpedBytes++;
          }
          if (debugLevel >= 2) {
            Serial.print("Total dumped bytes: ");
            Serial.println(dumpedBytes);
          }
        }
  
        for(int currBank=64; currBank < (numBanks - 64 + 64); currBank++) {
          if (debugLevel >= 2) {
            Serial.print("Dumping bank ");
            Serial.print(currBank);
            Serial.println("...");
          }
          for(long currByte=0; currByte < 65536; currByte++) {
            if (debugLevel == 0)
              Serial.write(dumpByte(currBank, currByte));
            else
              dumpByte(currBank, currByte);
            dumpedBytes++;
          }
          if (debugLevel >= 2) {
            Serial.print("Total dumped bytes: ");
            Serial.println(dumpedBytes);
          }
        }
  
      }
    }
  } else {

    // Star Ocean (JP) has romChips set to 69 - none of my other carts has romChips set to (dec) 69, so I use this to identfy the Star Ocean cart...
    if (debugLevel >= 1)
      Serial.println("Using special routines for Star Ocean dumping - might not work with other carts having romChips set to 69...");

    byte currDumpedByte = 0;
    byte currDumpedByteVerify = 0;

    // Calculation of ROM-size is not correct in case of Star Ocean, so I set it manually...
    romSize = 48;
    numBanks = 96;
    // Remark: Although Star Ocean reports LoROM, we will read 1M chunks HiROM in the area 0xf00000-0xffffff while setting the appropriate memory mapping in register 0x004807
    // I.e. Star Ocean exposes the original ("compressed") ROM data in this address area in 8 megabit chunks!!!

    // Check initial content of mapping register...
    if (debugLevel >= 1)
      Serial.println("Checking initial memory mapping...");
    byte initialSOMap = dumpByte(0, 18439);
    // Remark: Usually returns 3, that's why uCON64 sets it to 3 at the end of the dumping process?!
    if (debugLevel >= 2) {
      Serial.println(initialSOMap);
    }

    for (int currMemmap=0; currMemmap < (numBanks / 16); currMemmap++) {

      if (debugLevel >= 2) {
        Serial.print("Starting HiROM-type dump of chunk ");
        Serial.print(currMemmap);
        Serial.println(" at address area 0xf00000-0xffffff...");
      }
      
      // Set new memory chunk...
      setByte(0, 18439, currMemmap);
      if (debugLevel >= 2) {
        Serial.print("Current memory chunk is set to: ");
        Serial.println(dumpByte(0, 18439));
      }
      
      for(int currBank=240; currBank < 256; currBank++) {
        if (debugLevel >= 2) {
          Serial.print("Dumping bank ");
          Serial.print(currBank);
          Serial.println("...");
        }
        for(long currByte=0; currByte < 65536; currByte++) {
          do {
            currDumpedByte = dumpByte(currBank, currByte);
            if (verifySORead)
              currDumpedByteVerify = dumpByte(currBank, currByte);
            else
              currDumpedByteVerify = currDumpedByte;
          } while (currDumpedByte != currDumpedByteVerify);
          if (debugLevel == 0)
            Serial.write(currDumpedByte);
          dumpedBytes++;
        }
        if (debugLevel >= 2) {
          Serial.print("Total dumped bytes: ");
          Serial.println(dumpedBytes);
        }
      }

    }
    
    // Return mapping register to initial setting...
    setByte(0, 18439, initialSOMap);
    if (debugLevel >= 2) {
      Serial.print("Current memory chunk is set back to: ");
      Serial.println(dumpByte(0, 18439));
    }
          
  }
  
  // DONE - endless loop...
  if (debugLevel >= 1)
    Serial.println("Done! :-)");
  do {
    delay(1000*60);
  } while (1 == 1);
  
}

void dumpHeader() {

  Serial.println("HEADER START");

  String myHeader = ""; 
  byte myByte = 0;
  
  for (long i = (32704 + 32768); i < (32768 + 32768); i++) {
    commandOut(latchPin, dataPin, clockPin, false, true, true, false, 0, i);
    delayMicroseconds(dumpWait);
    myByte = readByte(d0Pin, d1Pin, d2Pin, d3Pin, d4Pin, d5Pin, d6Pin, d7Pin);
    myHeader = myHeader + char(myByte);
    // Serial.write(readByte(d0Pin, d1Pin, d2Pin, d3Pin, d4Pin, d5Pin, d6Pin, d7Pin));
    Serial.print(i);
    Serial.print(": 0x");
    Serial.print(myByte,HEX);
    Serial.print("; ");
    Serial.println(myByte,BIN);
  }
  
  Serial.println(myHeader);
  Serial.println("HEADER END");

}

byte dumpByte(byte myBank, word myAddress) {
  commandOut(latchPin, dataPin, clockPin, false, true, true, false, myBank, myAddress);
  delayMicroseconds(dumpWait);
  return readByte(d0Pin, d1Pin, d2Pin, d3Pin, d4Pin, d5Pin, d6Pin, d7Pin);
}

byte readByte(int myd0, int myd1, int myd2, int myd3, int myd4, int myd5, int myd6, int myd7) {
  
  byte tempByte = 0;
  
  if (digitalRead(myd0)) tempByte = tempByte + 1;
  if (digitalRead(myd1)) tempByte = tempByte + 2;
  if (digitalRead(myd2)) tempByte = tempByte + 4;
  if (digitalRead(myd3)) tempByte = tempByte + 8;
  if (digitalRead(myd4)) tempByte = tempByte + 16;
  if (digitalRead(myd5)) tempByte = tempByte + 32;
  if (digitalRead(myd6)) tempByte = tempByte + 64;
  if (digitalRead(myd7)) tempByte = tempByte + 128;
  
  if (debugLevel >= 3) {
    Serial.print("Byte read: 0x");
    Serial.print(tempByte,HEX);
    Serial.print("; ");
    Serial.println(tempByte,BIN);
  }
  
  return tempByte;

}

void setByte(byte myBank, word myAddress, byte myData) {
  // For that set /RD and /RESET to HIGH (/CS and /WR to LOW) and write the chunk number to the given address
  writeByte(d0Pin, d1Pin, d2Pin, d3Pin, d4Pin, d5Pin, d6Pin, d7Pin, myData);
  commandOut(latchPin, dataPin, clockPin, false, true, false, true, myBank, myAddress);
  pinMode(d0Pin, OUTPUT);
  pinMode(d1Pin, OUTPUT);
  pinMode(d2Pin, OUTPUT);
  pinMode(d3Pin, OUTPUT);
  pinMode(d4Pin, OUTPUT);
  pinMode(d5Pin, OUTPUT);
  pinMode(d6Pin, OUTPUT);
  pinMode(d7Pin, OUTPUT);
  delay(100);
  pinMode(d0Pin, INPUT);
  pinMode(d1Pin, INPUT);
  pinMode(d2Pin, INPUT);
  pinMode(d3Pin, INPUT);
  pinMode(d4Pin, INPUT);
  pinMode(d5Pin, INPUT);
  pinMode(d6Pin, INPUT);
  pinMode(d7Pin, INPUT);
  commandOut(latchPin, dataPin, clockPin, false, true, true, false, myBank, myAddress);
  // Activate pull-up resistors for input-pins
  writeByte(d0Pin, d1Pin, d2Pin, d3Pin, d4Pin, d5Pin, d6Pin, d7Pin, 255);
  delay(400);
}

void writeByte(int myd0, int myd1, int myd2, int myd3, int myd4, int myd5, int myd6, int myd7, byte myData) {
  
  if ( (myData & 1) == 1 ) digitalWrite(myd0,1); else digitalWrite(myd0,0);
  if ( (myData & 2) == 2 ) digitalWrite(myd1,1); else digitalWrite(myd1,0);
  if ( (myData & 4) == 4 ) digitalWrite(myd2,1); else digitalWrite(myd2,0);
  if ( (myData & 8) == 8 ) digitalWrite(myd3,1); else digitalWrite(myd3,0);
  if ( (myData & 16) == 16 ) digitalWrite(myd4,1); else digitalWrite(myd4,0);
  if ( (myData & 32) == 32 ) digitalWrite(myd5,1); else digitalWrite(myd5,0);
  if ( (myData & 64) == 64 ) digitalWrite(myd6,1); else digitalWrite(myd6,0);
  if ( (myData & 128) == 128 ) digitalWrite(myd7,1); else digitalWrite(myd7,0);
  
  if (debugLevel >= 3) {
    Serial.print("Byte written: 0x");
    Serial.print(myData,HEX);
    Serial.print("; ");
    Serial.println(myData,BIN);
  }

}

void commandOut(int myLatchPin, int myDataPin, int myClockPin, boolean myCS, boolean myReset, boolean myWR, boolean myRD, byte myBankOut, word myAdrOut) {
  
  int myControlOut = 0;
  if (myCS) myControlOut = myControlOut + 1;
  if (myReset) myControlOut = myControlOut + 2;
  if (myWR) myControlOut = myControlOut + 4;
  if (myRD) myControlOut = myControlOut + 8;
  
  byte myAdrLowOut = myAdrOut & 0xFF;
  byte myAdrHighOut = myAdrOut >> 8;

  if (debugLevel >= 3) {
    Serial.print("ControlByte: 0x");
    Serial.print(myControlOut,HEX);
    Serial.print("; ");
    Serial.println(myControlOut,BIN);
    Serial.print("ControlByte: 0x");
    Serial.print(myBankOut,HEX);
    Serial.print("; ");
    Serial.println(myBankOut,BIN);
    Serial.print("ControlByte: 0x");
    Serial.print(myAdrLowOut,HEX);
    Serial.print("; ");
    Serial.println(myAdrLowOut,BIN);
    Serial.print("ControlByte: 0x");
    Serial.print(myAdrHighOut,HEX);
    Serial.print("; ");
    Serial.println(myAdrHighOut,BIN);
  }
  
  digitalWrite(myLatchPin, 0);
  shiftOut(myDataPin, myClockPin, myControlOut); 
  shiftOut(myDataPin, myClockPin, myBankOut); 
  shiftOut(myDataPin, myClockPin, myAdrLowOut); 
  shiftOut(myDataPin, myClockPin, myAdrHighOut); 
  digitalWrite(myLatchPin, 1);
}

void shiftOut(int myDataPin, int myClockPin, byte myDataOut) {
  // This shifts 8 bits out MSB first, on the rising edge of the clock, clock idles low
  // Taken from Arduino-ShiftOut Tutorial - Example 2.1 - see: http://arduino.cc/en/Tutorial/ShftOut21
  int i=0;
  int pinState;
  digitalWrite(myDataPin, 0);
  digitalWrite(myClockPin, 0);
  for (i=7; i>=0; i--)  {
    digitalWrite(myClockPin, 0);
    if ( myDataOut & (1<<i) ) {
      pinState= 1;
    }
    else {	
      pinState= 0;
    }
    digitalWrite(myDataPin, pinState);
    digitalWrite(myClockPin, 1);
    digitalWrite(myDataPin, 0);
  }
  digitalWrite(myClockPin, 0);
}

