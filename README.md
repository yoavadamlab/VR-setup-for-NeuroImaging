# VR-setup

We study the neural activity of mice's hippocampus using optogenetics methods.
Specifically, we are training mice to navigate in VR environment for studying in-vivo place-cells activity using voltage-imaging technique.

Here we share our homemade hardware &amp; software experimental setup.

<<gif of all together>>


## 3d printings
 
 We Used [Arthur Sugden](https://github.com/asugden/bebox/tree/master/3d/wheel) model with slight changes.
 
 The modified model's `.SCAD files` can be found in `3D printing models` directory which contains models for:
 
 - The wheel
 - U shape construct for the wheel axis
 - Screen for VR projection
 
 
## Electronics

- [capacitance sensor](https://www.sparkfun.com/products/12041) - for mice licks detections.
- [solenoid valve](https://theleedifference.com/products/#solenoid-valves/3) - for reward control.
- [H bridge](https://m.banggood.com/10-Pcs-Geekcreit-L298N-Dual-H-Bridge-Stepper-Motor-Driver-Board-p-1054211.html?utm_source=googleshopping&utm_source=googleshopping&utm_medium=cpc_organic&utm_medium=cpc_bgs&gmcCountry=IL&utm_content=minha&utm_content=sandra&utm_campaign=minha-il-en-mb&utm_campaign=sandra-ssc-il-all-0507&currency=ILS&cur_warehouse=CN&createTmp=1&ad_id=519822680399&gclid=Cj0KCQiA6NOPBhCPARIsAHAy2zBwOR6kqKPrn7NYVQt2XXXowL66YlR-dfJfsxjh51QuHRhCAJZCJ7saAtPREALw_wcB) - for 12V voltage supply for the valve.
- [Rotary encoder](https://www.ia.omron.com/data_pdf/cat/e6b2-c_ds_e_6_1_csm491.pdf?id=487) - for wheel spinning detection.
- [Arduino Uno](https://docs.arduino.cc/hardware/uno-rev3) - controlling the electrical devices.
- [projector](https://docs.arduino.cc/hardware/uno-rev3) - for project the VR environment in front of the mice.

## Hardware all together

 We based the Wheel on [ThorLabs Board](https://www.thorlabs.com/newgrouppage9.cfm?objectgroup_id=159) with ThorLabs basic rods.
 The mice head was fixed by [Neurotar head fixation system](https://www.neurotar.com/the-mobile-homecage/#stability).
 
 <<images of wheel, head fixation>>
 ![alt text](https://github.com/[username]/[reponame]/blob/[branch]/image.jpg?raw=true)
 
 Tube (filled with 10% sucrose water for reward delivery), was connected to [Neurotar lick port](https://www.neurotar.com/the-mobile-homecage/#stability) 
 from one end, and to solenoid valve from the other end. 
 The solenoid valve was connected to an H-bridge for voltage supply.
 An electrical wire was soldered to the edge of a needle which compose on the lick port.
 This wire was connected to a capacitance sensor for mice lick detection.
 
  <<images of lick port, tube, solenoid valve>>
 ![alt text](https://github.com/[username]/[reponame]/blob/[branch]/image.jpg?raw=true)
  
 A rotary encoder was fixed on the shaft of the wheel spinning indication.
  
  <<images of the wheel from the side of the rotarry encoder>>
 ![alt text](https://github.com/[username]/[reponame]/blob/[branch]/image.jpg?raw=true)

 The H-bridge, capacitance sensor and the rotary encoder was connected to an arduino uno.
  <<images of the arduino circuitry>>
 ![alt text](https://github.com/[username]/[reponame]/blob/[branch]/image.jpg?raw=true)
 
 The arduino was connected to a standard computer, which the ViRMen software was installed on.
 Beside the regular monitor of the computer, a projector was connected to it too.
 The projector was mount on the ThorLabs board and project the VR enviroment on 3d printted screen\
 that was placed in front of the wheel.

  <<images of the setup from the side - projector on, screen, wheel, mice>>
 ![alt text](https://github.com/[username]/[reponame]/blob/[branch]/image.jpg?raw=true)

 
## Software

The VR rendering designed and executed by [ViRMEn v.2016-02-12](http://pni.princeton.edu/pni-software-tools/virmen-download).
Configurations files for 3 different VR worlds can be found at [`ViRmEn\Mice_Training.mat`](https://github.com/yoavadamlab/VR-setup/tree/main/ViRmEn).

Beside the VR design we had to control on the following:
- Progress of the VR according to the mice movement on the wheel
- Release specific amount of reward (i.e sucrose water) at specific location (i.e. reward zone)
- keep track of the mice licking the lick port (for learning rate analysis)
- Save the behavioral data from the training and Imaging sessions for future analysis

For reliable rendering the VR according to the mice behavior,

Based on our `Mice training protocol.pdf` 

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


