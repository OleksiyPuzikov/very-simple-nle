from lib.mlt import mlt

from PyQt4 import QtGui

import sys
import math
import struct

mlt.Factory.init()
profile = mlt.Profile()

def get_thumbnail(filename, filename2):
    producer = mlt.Producer(profile, filename)
    size = (320, 240)

    frame = producer.get_frame()

    if filename.endswith(".wav"):
        values = []
        #raw_values = []
        WAVE_IMG_HEIGHT = 50
        WAVE_IMG_WIDTH = 10
        VAL_MIN = 5100.0
        #VAL_MAX = 15000.0
        VAL_MAX = 30000.0
        VAL_RANGE = VAL_MAX - VAL_MIN

        for frame in range(0, producer.get_length() + 1):
            producer.seek(frame)

            wave_img_array = mlt.frame_get_waveform(producer.get_frame(), WAVE_IMG_WIDTH, WAVE_IMG_HEIGHT)
            val = 0
            for i in range(0, len(wave_img_array)):
                val += max(struct.unpack("B", wave_img_array[i]))

            #raw_values.append(val)

            if val > VAL_MAX:
                val = VAL_MAX
            val -= VAL_MIN
            val = math.sqrt(float(val) / VAL_RANGE)

            values.append(val)

        #print max(raw_values)

        img = QtGui.QImage(len(values), 32,  QtGui.QImage.Format_RGB32)
        img.fill(0)

        painter = QtGui.QPainter()
        painter.begin(img)

        for c, v in enumerate(values):
            painter.setPen(QtGui.QColor(175, 175, 175))
            painter.drawLine(c, 35-int(v*35), c, 35)

            painter.setPen(QtGui.QColor(255, 255, 255))
            painter.drawPoint(c, 35-int(v*35))

        painter.end()

        img.save(filename2)

    else:
        frame.set("consumer_deinterlace", 1)

        rgb = frame.get_image(mlt.mlt_image_rgb24, *size)

        img = QtGui.QImage(rgb, size[0], size[1], QtGui.QImage.Format_RGB888)

        img.save(filename2)

get_thumbnail(sys.argv[-1], "test.png")

