#!/usr/bin/env bash 

export ROOT_DIR=${PWD}

#sudo apt update
sudo apt install -y build-essential python3-dev python3-virtualenv make gcc 


if [ ! -d venv ]; then
    python3 -m virtualenv venv
    venv/bin/pip install --upgrade pip
    venv/bin/pip install cocotb cocotb-bus
fi

source venv/bin/activate



