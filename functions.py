# Reads data in CHUNK and looks for pulse peaks in position 26 of a 51 number array
# Repeats x times
# Calculates zip average
import pyaudio
import wave
import numpy as np
import math

peak = 0.0
trough = 0.0
height = 0.0
p = pyaudio.PyAudio()


# Finds pulses in data over a given threshold
def find_pulses(left_channel):
    samples =[]
    pulses = []
    for i in range(len(left_channel) - 51):
        samples = left_channel[i:i+51]  # Get the first 51 samples
        if samples[25] >= max(samples) and (max(samples)-min(samples)) > 100 and samples[25] < 32768:
            pulses.append(samples)
    if len(pulses) != 0:  # If the list is empty
        #print(".",pulses) # For debugging
        next       
    return pulses

def sum_pulses(pulses):
    pulse_shape = np.zeros(51,dtype=int)
    for i in range(len(pulses)):      
        pulse_shape = np.add(pulse_shape, pulses[i])                
    return pulse_shape     

# Calculates the average pulse shape
def average_pulse(sum_pulse, count):       
    average = []
    for x in sum_pulse:
        average.append(x / count)
    return average 

# Normalises the average pulse shape
def normalise_pulse(average):
    normalised = []
    mean = sum(average) / len(average)   
    normalised = [n - mean for n in average]  
    #print(normalised)
    return normalised

def distortion(pulse, shape):
    
    product = [(x - y)**2 for x, y in zip(shape, pulse)]
    distortion = int(math.sqrt(sum(product)))

    return distortion

def pulse_height(passed):
    #print("pass ",passed)  
    peak = passed[passed.index(max(passed))]
    trough = passed[passed.index(min(passed))]
    height = int(peak-trough)
    return height