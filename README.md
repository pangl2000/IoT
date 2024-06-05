# Required apps:

+ Download and install Nodejs from the official Node.js website: https://nodejs.org/
+ Download docker desktop from https://docs.docker.com/desktop/install/windows-install/ 

# Required packages:

## Repository files
+ Install all files and place them in a main folder
+ Download GitRepo_LargeFiles from [here](https://www.dropbox.com/scl/fo/xkffl87ia2yy5pp4ahwvg/h?rlkey=nb8zr8kwkz41wdny6tdgwtgec&dl=0) and place it in the same folder as the rest of the files

## Python packages:
+ For python packages needed, in your main folder, run:
```bash
pip install Flask pymongo Flask-RESTful requests aiohttp flask[async] schedule opencv-python torch ultralytics supervision==0.2.0 paho-mqtt numpy pandas torchvision detectron2 IPython openpyxl
```
+ If detectron2 fails to install, use this command instead:
```bash
python -m pip install 'git+https://github.com/facebookresearch/detectron2.git'
```

## Node.js packages:
+ For Node.js packages, in frontEnd-backEnd folder, run:
```bash
npm install express cors axios body-parser node-fetch@2.6.1 nodemailer xlsx socket.io
```

# How to run:

1. Open Docker Desktop

2. Double click run_commands.dat
> *Or in main folder open cmd and type:*
```bash
run_commands.dat
```

### Local ports used:
| File | Port |
| --------------- | --------------- |
| backend.js   | 3000    |
| busai.py    | 5000    |
| busStopFaker.py    | 5001    |
| edgeController.py   | 5002    |
| mainApp.py   | 5003    |
| edgeControllerSyncSupport.py   | 5004    |
| notifyDriver.py   | 5005    |
| bckend22.js   | 8080    |

### DEMO Link
Watch a demo at https://1drv.ms/v/s!Au7ctQFlF0NSr0Km3QzTG6YtSQll?e=BMoj2E