class Clip():
    def __init__(self, mediatype="", name="", id="", start_frame=0, end_frame=0, in_frame=0, out_frame=0, path="", track=0, color=(0.5, 0.5, 0.5, 1)):

        self.mediatype = mediatype # coming from FCP
        self.name = name
        self.id = id
        self.start_frame = start_frame # position in timeline
        self.end_frame = end_frame # position in timeline
        self.in_frame = in_frame # position in clip
        self.out_frame = out_frame # position in clip
        self.path = path # filename
        self.track = track

        self._color = color

        self._selected = False

        self.producer = None # MLT producer

    def setData(self, key, value):
        try:
            setattr(self, key, value)
        except:
            pass

    def getData(self):
        k = [ "start_frame", "end_frame", "in_frame", "out_frame", "path", "track" ]
        v = [ self.start_frame, self.end_frame, self.in_frame, self.out_frame, self.path, self.track ]

        return (k, v)

    def __repr__(self):
        return "Clip(mediatype='%s', name='%s', id='%s', start_frame=%d, end_frame=%d, in_frame=%d, out_frame=%d, path='%s', track=%d, color=(%.3g, %.3g, %.3g, %.3g))" % \
               ( self.mediatype,
                self.name,
                self.id,
                self.start_frame,
                self.end_frame,
                self.in_frame,
                self.out_frame,
                self.path,
                self.track,
                self._color[0], self._color[1], self._color[2], self._color[3],)

    def small_debug_print(self):
        k, v = self.getData()

        s = ":: "
        for kkk, vvv in zip(k, v):
            s += "%s=%s " % (kkk, str(vvv))

        return s

        #return ":: name='%s', start_frame=%d, end_frame=%d, in_frame=%d, out_frame=%d, path='%s', track=%d" % \
        #       (self.name,
        #        self.start_frame,
        #        self.end_frame,
        #        self.in_frame,
        #        self.out_frame,
        #        self.path,
        #        self.track,
        #        )

    def inside(self, x, y):
        _x = self.start_frame
        __width__ = self.end_frame - self.start_frame

        _y = 0-self.track*50
        __height__ = 50

        return (_x < x) and ((_x+__width__)>x)  and (_y < y) and ((_y+__height__)>y)
