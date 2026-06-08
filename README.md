# bsidesdsm26
BSides DSM 2026 Badge Code

## Dependencies
#### Ch32fun
Clone the ch32fun library  
`git clone https://github.com/cnlohr/ch32fun.git`
<br>

## Building
Update Makefile to reference location of ch32fun clone<br>
Run `make` command from root of bsidesdsm26 folder<br>

## Flashing
Clone wagminiator MCU-Flash-Tools
`git clone https://github.com/wagiminator/MCU-Flash-Tools.git`
<br>
Follow the Preparation instructions to make sure your computer recognizes the USB device<br>
Hold the boot button on the badge and then run:<br>
`<path to MCU-Flash-Tools>/chprog.py <path to bsidesdsmbadge.bin>
