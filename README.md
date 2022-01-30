# VR-setup
Hardware &amp; Software for Mice VR navigation training and Imaging System  

## 3d printings
 
 We Used [Arthur Sugden] (https://github.com/asugden/bebox/tree/master/3d) model with slight changes.
 
 The modified model's `.SCAD files` can be found in `3D printing models` directory which contains models for:
 
 - The wheel
 - U shape construct for the wheel axis
 - Screen for VR projection
 

## Electronics

- [capacitance sensor] (https://www.sparkfun.com/products/12041) - for mice licks detections.
- [solenoid valve] (https://theleedifference.com/products/#solenoid-valves/3) - for reward control.
- [H bridge] (https://howtomechatronics.com/tutorials/arduino/arduino-dc-motor-control-tutorial-l298n-pwm-h-bridge/) - for 12V voltage supply for the valve.
- [Rotary encoder] (https://www.ia.omron.com/data_pdf/cat/e6b2-c_ds_e_6_1_csm491.pdf?id=487) - for wheel spinning detection.
- [Arduino Uno] (https://docs.arduino.cc/hardware/uno-rev3) - controlling the electrical devices.

## Hardware all together

 <<images of our set up>>
 ![alt text](https://github.com/[username]/[reponame]/blob/[branch]/image.jpg?raw=true)
 
 We based the Wheel on [ThorLabs Board] (https://www.thorlabs.com/newgrouppage9.cfm?objectgroup_id=159) with ThorLabs basic rods.
 The mice head was fixed by [Neurotar head fixation system](https://www.neurotar.com/the-mobile-homecage/#stability).
 plastic pipe that went out from a tube 
 (filled with 10% sucrose water for reward) and connect to [Neurotar lick port] (https://www.neurotar.com/the-mobile-homecage/#stability).
 << image of the reward setup>>
 
 A wire connected to the capacitance detector was soldered to the needle for getting 
 indication of mice licking.
 
 The water tube was connected to the solenoid valve, which connect to the H-bridge, for reward control.
 <<photo of the valve>>
 
 The rotary encoder was fixed on the shaft for detection of spinning amount of the wheel.
 (which will be used as a VR forward signal).
 
 all those electronics connected to an Arduinu UNO, which together with the virmen software (more detailed below)
 control the system.
 

## Software

Based on ViRnEn, a blank VR package for VR Rendering, we built a software that:
- render VR 
- control rewards giving and task specific architecture
- save behavioral data as `.csv file`
- send Email Update with bhavior statistics

### VR Rendering

virmen...

### Electronics control

arduino..

### data saving format
frame each 30 ms
an image of the csv table

### Email update


