Cart ROM-Reader
(for reading SNES-/SFC-Game Cartridges with an Arduino)
by Michael Kovacs

v0.1 / 2013-04-07

--------------------------------------------------------------------------------
THIS PACKAGE IS PROVIDED "AS IS" AND FREE OF CHARGE BUT WITHOUT WARRANTY OF 
ANY KIND! USE IT AT YOUR OWN RISK - THERE IS ALWAYS THE POSSIBILITY TO DAMAGE
YOUR PRECIOUS EQUIPMENT (GAME-CARTRIDGES, ARDUINO, ANY OTHER SYSTEM-COMPONENT)!

This project is NOT connected or affiliated with any mentioned company in any 
way. All trademarks are property of their respective holders.

You may use this project for reading game cartridges only in compliance with the 
copyright and intellectual property rights of the respective owners!
--------------------------------------------------------------------------------

Contents:

1. Introduction
2. Requirements
3. How to build
4. How to use
5. References / Acknowledgements
6. History
7. License

--------------------------------------------------------------------------------

1. Introduction

Having seen several projects making use of Arduino and/or Raspberry Pi to read
game cartridges of several platforms (see references), I was not able to find
a ready solution for reading game cartridges of the Super Nintendo 
Entertainment System using the Arduino. Especially there was contradicting
information if it is possible to read the ROM of the japanese game cartridge
"Star Ocean" without any "special" equipment because of the S-DD1 chip the game
uses for graphics compression. This sparked my interest and I decided to try it 
myself, though I am an amateur in electrical engineering.

Based on the information of the other game cartridge reader projects, the
Arduino homepage and the information published on the Internet about the Super 
Nintendo Entertainment System game carts, I designed a cart reader on a 
perfboard and wrote some software to read the contents of the cart's ROM and
write it to the serial out interface of the Arduino.

To give something back to the Arduino & SNES community, I hereby would like to 
share my results in the spirit of Arduino, quoting the Arduino homepage:
"Build it, hack it and share it. Because Arduino is you!"

I will most propably not spend any more time on this project because I have 
reached my goal to read the ROM of all my SNES game cartridges and I have 
learned much on my way there. If you would like to contribute, there are many 
things left to be done, e.g. reading / writing of the Save RAM of the game
cartridges. Please share your results as well!

Also, please also keep in mind that I am an amateur in electrical engineering, 
so this project may contain severe errors and blow up your entire equipment, but 
at least it worked fine for me without doing any damage to my equipment. :-)

--------------------------------------------------------------------------------

2. Requirements

a. An Arduino providing 5V input/output pins - I used an Arduino Uno R3.
b. The Arduino IDE >= 1.0 installed an a PC.
c. A cart-reader built based on the schematics included in this package.
d. A USB-connection to the PC to upload the code included in this package to the 
   Arduino and to receive the ROM-data (using serial communication).
e. A program to receive the serial data from Arduino - I used standard command 
   line-tools in Linux. If you use any other OS, please use Google to find a way
   to read the data...

--------------------------------------------------------------------------------

3. How to build

a. Build the cartridge-reader board:

   Please find the schematics and parts list in the following file:
   Cart_ROM_Reader_schematics.[svg|dia]
   --> I apologise if this diagram does not meet certain standards, but as I
       said, I am an amateur in electrical engineering... :-)
   --> This file was created using "Dia" - see: https://live.gnome.org/Dia

b. Wire the cartridge-reader board to the Arduino according to the schematics.

c. Upload the reader-software to your Arduino:

   Please find the sourcecode including some inline documentation in the 
   following file:
   Cart_ROM_Reader.ino
   --> Adapt the variables at the beginning of the program as necessary for 
       your environment.
   --> Upload the sourcecode to the Arduino with the Arduino IDE.

--------------------------------------------------------------------------------

4. How to use

a. Unplug Arduino from USB (and power, if applicable)!!!
b. Plug the cart into the reader-board - pay attention to the right cartridge
   orientation (pin 1 / 5)!
c. Prepare file-writing as root in a linux-shell (but do not execute, yet):
   (stty raw; cat > rom.sfc) < /dev/ttyACM0
           filename ^          ^ serial-device to read from
d. Plug USB into Arduino
e. Within 5 seconds, start the command prepared in step (c)
f. The cart is now being read (takes ~ 20 minutes per 8 megabits)
g. When reading is finished (only 1 led is lit) unplug Arduino from USB, the
   command automatically returns to the shell 
h. Check md5sum and compare with a reliable source and/or read the cart a second 
   time and do a binary compare to make sure you have a bit-perfect read-out.

--------------------------------------------------------------------------------

5. References / Acknowledgements

Special thanks go to:
- Arduino ShiftOut tutorial started by Carlyn Maw and Tom Igoe:
  http://arduino.cc/en/Tutorial/ShiftOut
- SNES kart guide by DiskDude:
  http://www.emulatronia.com/doctec/consolas/snes/sneskart.html
- SNES (Super Nintendo Emulated System) by Waterbury:
  http://familab.org/blog/2012/12/snes-super-nintendo-emulated-system/
- ArDUMPino for reading Sega Genesis game cartridges by Bruno Freitas:
  http://www.brunofreitas.com/node/31
- GBCartRead: Arduino based Gameboy Cart Reader by alex@insidegadgets.com:
  http://www.insidegadgets.com/2011/03/19/gbcartread-arduino-based-gameboy-cart-reader-%E2%80%93-part-1-read-the-rom/
- uCON64-sourcecode for S-DD1 dumping:
  http://ucon64.cvs.sourceforge.net/viewvc/ucon64/ucon64/src/backup/swc.c?view=markup
- Forum-postings by "byuu" and "waterbury" on how to write to a cart's register:
  http://forums.nesdev.com/viewtopic.php?f=12&t=9850
- Super Nintendo (SNES) Games Database: 
  http://superfamicom.org

DISCLAIMER: I AM NOT RESPONSIBLE FOR THE CONTENT OF THESE WEBSITES!

--------------------------------------------------------------------------------

6. History

v0.1 / 2013-04-07 / Initial release.

--------------------------------------------------------------------------------

7. License

Copyright (C) 2013  Michael Kovacs

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

