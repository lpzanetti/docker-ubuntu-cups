#!/bin/bash

# This is a simple shell script to echo "TESTING"
echo "TESTING"
killall -9 python3
nohup /usr/bin/python3 /var/www/sistemas/auxiliar/imprime/check.py > /output.log 2>&1 &