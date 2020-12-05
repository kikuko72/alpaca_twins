import os
import wave
import sys

source = sys.argv[1]
result = os.path.splitext(source)[0]+ '.wav'

with open(source, 'rb') as f:
    with wave.open(result, 'wb') as dest:

        dest.setnchannels(1)
        dest.setnchannels(2)
        dest.setframerate(48000)
        dest.setnframes(960)
        dest.setsampwidth(2)

        for data in f:
             dest.writeframes(data) 
