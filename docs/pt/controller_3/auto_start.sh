#!/bin/bash

source ~/.plant_controller/.venv/bin/activate
~/.influxdb/influxdb3 serve --node-id node0 > /dev/null 2>&1 &
cd ~/repos/plant-controller/pt/controller_3/src
python -m plant_controller --log-level INFO run