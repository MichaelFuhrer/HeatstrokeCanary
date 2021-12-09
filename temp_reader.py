# Uses daemon from https://github.com/wcbonner/GoveeBTTempLogger to get BLE temperature advertisements
import os

path = "./templog"

def get_temp():
    with open(path + '/' + os.listdir(path)[0], 'r') as f:
        last_line = f.readlines()[-1]
        arrTemp = last_line.split()
        celciusVal = float(arrTemp[2])
        fahVal = 9.0 / 5.0 * celciusVal + 32
        return fahVal
