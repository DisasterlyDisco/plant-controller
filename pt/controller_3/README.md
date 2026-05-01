# Raspberry Pi
The machine on which the controller runs is assumed to be a Raspberry Pi.
The controller works well on a 4GB ram Raspberry Pi 5, and is functional on as early as a Raspberry Pi 3. If running the controller software on an older Raspberry Pi it is recommended to have the database running on another machine, and update the `host` in the `./impl/config.toml` to the address and port of the database on the external machine.

The software assumes that the machine runs Raspberry Pi OS 64bit Lite, version Trixie or later.

After installing the OS on the machine, SSH into it and ensure that it updated:
```bash
sudo apt-get update -y && sudo apt-get upgrade -y
```

# InfluxDB
*version* 3.0 or later
*location* can be installed locally or remotely
*Note one RPI5s* The default OS that is build for Rapsberry Pi 5 uses a page-size of 16k. This doesn't work with local installation of InfluxDB3, which assumes a page size of 4k. Make sure to change the page size.
This is done in `/boot/firmware/config.txt` by setting the paramaeter `kernel` to `kernel8.img`: `kernel=kernel8.img`

## Install the database
The database needs to exist somewhere. This small guide assumes that it is installed on the Raspberry Pi.

Run
```bash
curl -O https://www.influxdata.com/d/install_influxdb3.sh \
&& sh install_influxdb3.sh 
```
using the local install and not letting the install script start the server at the end.

Then, start the server yourself:
```bash
influxdb3 serve --node-id node0
```

With it set up, create the admin token.
```bash
influxdb3 create token --admin
```

Save this in the plant_controllers config file, and note it for the next step.

(If you haven't already set this up, you should start out by copying the example file:)
```bash
cp ./impl/config.toml.example ./impl/config.toml
```
(... and then modifying it as needed)

Then create the "database" for our controller (called a bucket in previous versions of InfluxDB):
```bash
influxdb3 create database --token <ADMIN_TOKEN> --retention-period 7d plant-controller
```
(Here I've set the retention period for the database to 7 days to avoid gumming up the controllers persistent memory, and set the database name to `plant-controller` as that is the default in the config file. Feel free to change this (as long as you update the database name in the config file accordingly))

The Database is now up and running, and ready for use. Make sure to run `influxdb3 serve --node-id node0` whenever you turn on the plant controller.

# Setting up the environment for the plant_controller software
The plant_controller software is a python program. It is not pacakged with its dependencies (yet) and therefore assumes that they are installed in the environment. Before running the program we'll have to set this up first.

First, make sure that the base OS is updated and upgraded.

Then let's install the python we need:
```bash
sudo apt-get install -y python3-pip, python3-venv
sudo apt install --upgrade python3-setuptools
```

Then, make a virtual environment for python in the home directory and enter it:
```bash
cd ~
python -m venv .venv --system-site-packages
source .venv/bin/activate
```

## Adafruit-Blinka
Adafruit-Blinka gives us a python API that makes it easy to interact with the Raspberry Pis GPIO header. We use this for our I2C communication, getting easy interaction with the adafruit sensor software modules on top. While it is a collection of python modules it cannot just be installed with pip as it needs to configure some stuff in the actual machine.

We can do this manually, but Adafruit has supplied us with a nice little script for convenience:
```bash
cd ~
pip install --upgrade adafruit-python-shell
wget https://raw.githubusercontent.com/adafruit/Raspberry-Pi-Installer-Scripts/master/raspi-blinka.py
sudo -E env PATH=$PATH python3 raspi-blinka.py
```

## The rest of the modules
With Adafruit-Blinka installed, install the rest of the python requirements as normal.

From the root of the plant-controller repo:
```bash
cd ./pt/controller_3
pip install -r requirements.txt
```

# Running the damned thing
Now that everything is setup, the controller is ready to run.
Assuming that you are in the root of the plant-controlelr repo:
```bash
cd ./pt/controller_3/src
python -m plant_controller
```
Et voila! it should now be running, and the web interface should be accessible on port 8099 off the controller.

