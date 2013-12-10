from PyQt4 import QtGui, QtCore
import time
import random

import os

from OpenGL.GL import *
import numpy
import pprint

from lib.mlt import mlt as mlt
from lib.view import GLView
from lib.pytimecode import PyTimeCode as tc

from lib.core import Clip

from window_parameters import ParameterWindow

texture_mode = GL_TEXTURE_RECTANGLE

mlt.Factory.init()
#mlt_profile = mlt.Profile('square_pal_wide')
mlt_profile = mlt.Profile('hdv_720_25p')

class Scene():
    def __init__(self):
        self.clips = []
        self.tracks = 2
        self.filename = ""

        self.playlists = []

    def load(self, filename):
        self.filename = filename

        try:
            fin = open(self.filename, "r")
            self.clips = eval(fin.read())
            fin.close()
        except:
            pass

    def save(self):
        fout = open(self.filename, "w")
        pprint.pprint(self.clips, fout)
        fout.close()

    def save_as(self, filename):
        self.filename = filename
        self.save()

    def generate_mlt(self):
        max_tracks = 0
        for c in self.clips:
            c.producer = mlt.Producer(mlt_profile, c.path)

            if (c.in_frame == 0) and (c.out_frame == 0): # badly generated data
                c.out_frame = c.end_frame-c.start_frame

            c.producer.set("in", c.in_frame)
            c.producer.set("out", c.out_frame)
            max_tracks = max(max_tracks, c.track)

        self.tracks = int(max_tracks)

        del self.playlists[:]

        for track in range(int(max_tracks)+1):

            pl = mlt.Playlist()

            self.playlists.append(pl)

            clips1 = filter(lambda x: x.track == track, self.clips)
            clips2 = sorted(clips1, key=lambda x: x.start_frame)

            if clips2[0].start_frame-1 > 0:
                pl.blank(int(clips2[0].start_frame-1))

            for x in range(len(clips2)):
                pl.append(clips2[x].producer)
                if x < len(clips2)-1:
                    if clips2[x].end_frame+1 != clips2[x+1].start_frame:
                        l = clips2[x+1].start_frame-clips2[x].end_frame-2
                        pl.blank(int(l))

            #pl.get_clip_at(100)

            #i = pl.count()
            #for c in range(i):
            #    info = pl.clip_info(c)
            #    print info.start, info.length, info.frame_in, info.frame_out, info.frame_count, info.resource

        self.tractor = mlt.Tractor()
        self.multitrack = self.tractor.multitrack()

        for c, pl in enumerate(self.playlists):
            self.multitrack.connect(pl, c)

        #self.consumer = mlt.Consumer(mlt_profile, "null")
        self.consumer = mlt.Consumer(mlt_profile, "sdl_audio")

        #

        ##ifdef Q_OS_WIN
        #m_consumer->set("audio_buffer", 2048);
        ##else
        self.consumer.set("audio_buffer", 512)
        ##endif

        self.consumer.set("progressive", True)
        #self.consumer.set("buffer", 25)
        self.consumer.set("buffer", 1)
        self.consumer.set("prefill", 1)
        self.consumer.set("scrub_audio", 1)
        self.consumer.set("volume", 1.0)

        #self.consumer.set("test_card", "colour:colour=black")

        #

        #self.consumer.set("real_time", -2)
        self.consumer.set("rescale", "none")

        self.consumer.connect(self.tractor)

class MainForm(GLView):

    def __init__(self, parent=None):
        GLView.__init__(self, parent)

        self.setWindowTitle("very-simple-nle")
        self.setAcceptDrops(True)

        self.scene = Scene()

        self.parameters = ParameterWindow(main_window=self, parent=None)
        self.parameters.show()
        self.parameters.raise_()

        self.setAutoFillBackground(False)
        self.setAttribute(QtCore.Qt.WA_StaticContents, True)
        self.setAttribute(QtCore.Qt.WA_OpaquePaintEvent, True)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground, True)
        self.setAttribute(QtCore.Qt.WA_PaintOnScreen, True)

        self.playhead = 0
        self.texture = -1
        self.texture_data = None

        self.tc = tc(25)

        self.playbackTimer = QtCore.QTimer(self)
        self.playbackTimer.setInterval(1000/25)
        self.connect(self.playbackTimer, QtCore.SIGNAL("timeout()"), self.onPlaybackTimer)

        self.play = False

        if os.path.exists("test.scene"):
            self.scene.load("test.scene")

        else:
            for c in range(10):
                hue = random.random()

                color = QtGui.QColor.fromHsvF(hue, 0.5, 0.75)
                r, g, b = color.redF(), color.greenF(), color.blueF()

                clip = Clip()
                clip._color = (r, g, b, 1)
                clip.name = "clip%d" % c

                clip.start_frame = c*120
                clip.end_frame = c*120+119

                clip.track = random.randint(0, 1)
                clip.path = "../media/output%d.mov" % (clip.track+1)

                self.scene.clips.append(clip)

            self.scene.save_as("test.scene")

        self.scene.generate_mlt()

        self.camera.translate(100, self.height()-50)

        self.updateImage()

        self.extendLeft = None
        self.extendRight = None

        self.cursorLeft = QtGui.QCursor(QtGui.QPixmap("img/trim_left.png"))
        self.cursorRight = QtGui.QCursor(QtGui.QPixmap("img/trim_right.png"))

        self.gl_font = QtGui.QFont("Tahoma", 9)

        self.pointVertices = []
        self.textureCoordinates = []

    def dragEnterEvent(self, event):
        event.accept()

    def dragMoveEvent(self, event):
        event.accept()

    def dropEvent(self, event):
        GLView.dropEvent(self, event)

        if event.mimeData().hasUrls():
            p = self.camera.qt_to_opengl(event.pos())
            current_x = p.x()
            for url in event.mimeData().urls():
                filename = str(url.toString(QtCore.QUrl.RemoveScheme))
                filename = os.path.normpath(filename)

                hue = random.random()

                color = QtGui.QColor.fromHsvF(hue, 0.5, 0.75)
                r, g, b = color.redF(), color.greenF(), color.blueF()

                clip = Clip()
                clip._color = (r, g, b, 1)
                clip.name = os.path.basename(filename)

                clip.producer = mlt.Producer(mlt_profile, filename)

                clip.start_frame = current_x

                cpgl = clip.producer.get_length()

                if cpgl == 15000: # some hardcoded value?
                    cpgl = 25

                clip.end_frame = clip.start_frame+cpgl

                current_x = clip.end_frame+1

                clip.producer.set("in", 0)
                clip.producer.set("out", cpgl)

                clip.track = self.scene.tracks
                clip.path = filename

                self.scene.clips.append(clip)

                self.scene.generate_mlt()
                self.updateImage()

    def resizeEvent(self, event):
        GLView.resizeEvent(self, event)
        self.parameters.setGeometry(self.geometry().left()+5, self.geometry().top()+25, self.parameters.width(), self.parameters.height())

        w = 1280/2
        h = 720/2

        x1 = self.width()-w
        y1 = 0

        x2 = x1+w
        y2 = y1+h

        self.pointVertices = numpy.array([ x1, y1, x1, y2, x2, y2, x2, y1 ], dtype=numpy.float32)

        x1 = 0
        y1 = 0

        x2 = w*2
        y2 = h*2

        self.textureCoordinates = numpy.array([ 0, 0, 0, y2, x2, y2, x2, 0 ], dtype=numpy.float32)


    def moveEvent(self, event):
        GLView.moveEvent(self, event)
        self.parameters.setGeometry(self.geometry().left()+5, self.geometry().top()+25, self.parameters.width(), self.parameters.height())

    def closeEvent(self, event):
        self.parameters.close()
        GLView.closeEvent(self, event)
        self.scene.save()

    def updateImage(self):
        self.scene.consumer.purge()
        self.scene.tractor.set_speed(0)
        self.scene.tractor.seek(self.playhead)
        self.scene.tractor.set_speed(1)

        #print "--"*10
        #for c, pl in enumerate(self.scene.playlists):
        #    try:
        #        producer = pl.get_clip_at(self.playhead)
        #        print c, producer.is_blank() #producer.position()
        #    except:
        #        print c, "None"

        frame = self.scene.consumer.get_frame()
        frame.set("consumer_deinterlace", 1)

        # Now we are ready to get the image and save it.
        #size = (mlt_profile.width(), mlt_profile.height())
        #size = (1280, 720)

        w = 1280
        h = 720

        size = (w, h)
        rgb = frame.get_image(mlt.mlt_image_rgb24, *size)

        arr = numpy.fromstring(rgb, dtype=numpy.uint8)
        #self.texture_data = arr.reshape((mlt_profile.width(), mlt_profile.height()+1, 3))
        self.texture_data = arr.reshape((w, h+1, 3))

        glDeleteTextures(self.texture)
        self.texture = -1

        self.update()

    def onPlaybackTimer(self):
        self.playhead += 1 # self.scene.tractor.frame()
        self.updateImage()
        self.update()

    def mouseReleaseEvent(self, event):
        self.extendLeft = None
        self.extendRight = None
        self.setCursor(QtCore.Qt.ArrowCursor)

    def mousePressEvent(self, event):
        GLView.mousePressEvent(self, event)

        p = self.camera.qt_to_opengl(event.pos())

        if event.buttons() & QtCore.Qt.LeftButton:
            for c in self.scene.clips:
                c._selected = c.inside(p.x(), p.y())

        #self.update()

        selectedClips = filter(lambda i: i._selected, self.scene.clips)

        for c in selectedClips:
            k, v = c.getData()
            self.parameters.setData(c, k, v)

        self.setUpdatesEnabled(False)
        self.setCursor(QtCore.Qt.ArrowCursor)
        for c in selectedClips:
            if c.inside(p.x(), p.y()):
                if p.x()-c.start_frame in range(0, 15):
                    self.extendLeft = c
                    self.setCursor(self.cursorLeft)
                elif c.end_frame-p.x() in range(0, 15):
                    self.extendRight = c
                    self.setCursor(self.cursorRight)
                else:
                    self.setCursor(QtCore.Qt.ArrowCursor)
        self.setUpdatesEnabled(True)
        self.update()

    def mouseMoveEvent(self, event):

        dx = 1.0*(event.x() - self._mousePos.x())/self.camera.m[0]
        dy = 1.0*(event.y() - self._mousePos.y())/self.camera.m[0]

        GLView.mouseMoveEvent(self, event)

        if event.buttons() & QtCore.Qt.LeftButton:

            nodesMoved = False

            # move selected nodes...

            selectedClips = filter(lambda i: i._selected, self.scene.clips)
            nodesMoved = bool(selectedClips)

            if (self.extendLeft is None) and (self.extendRight is None):
                for n in selectedClips:
                    n.start_frame = int(n.start_frame+dx)
                    n.end_frame = int(n.end_frame+dx)
            else:
                if self.extendLeft:
                    sel = self.extendLeft

                    sel.start_frame += dx
                    sel.in_frame += dx

                    if sel.in_frame < 0:
                        ddx = sel.in_frame
                        sel.in_frame = 0
                        sel.end_frame += ddx

                    #elif self.start_frame > self.stop_frame:

                    self.playhead = int(sel.start_frame)

                elif self.extendRight:
                    sel = self.extendRight
                    sel.end_frame += dx
                    sel.out_frame += dx

                    if sel.out_frame > sel.producer.get_length()-sel.in_frame:
                        sel.end_frame -= dx
                        sel.out_frame -= dx

                    self.playhead = int(sel.end_frame)

            if nodesMoved:
                c = selectedClips[0]
                k, v = c.getData()

                self.parameters.setData(c, k, v)

                self.scene.generate_mlt()
                self.updateImage()

            if not nodesMoved:

                if (self.extendLeft is None) and (self.extendRight is None):
                    ph = self.camera.qt_to_opengl(event.pos())
                    self.playhead = ph.x()

                self.updateImage()

        else:
            self.setCursor(QtCore.Qt.ArrowCursor)
            p = self.camera.qt_to_opengl(event.pos())
            selectedClips = filter(lambda i: i._selected, self.scene.clips)
            for c in selectedClips:
                if c.inside(p.x(), p.y()):
                    if p.x()-c.start_frame in range(0, 15):
                        self.setCursor(self.cursorLeft)
                    elif c.end_frame-p.x() in range(0, 15):
                        self.setCursor(self.cursorRight)
                    else:
                        self.setCursor(QtCore.Qt.ArrowCursor)

    def keyPressEvent(self, event):
        GLView.keyPressEvent(self, event)

        if event.key() == QtCore.Qt.Key_Space:
            self.play = not self.play

            if self.play:
                self.scene.consumer.purge()
                self.playbackTimer.start()
                # self.scene.consumer.start()
            else:
                self.playbackTimer.stop()
                # self.scene.consumer.stop()
                self.scene.consumer.purge()

        elif event.key() == QtCore.Qt.Key_Left:

            if event.modifiers() & QtCore.Qt.ShiftModifier:
                for clip in self.scene.clips:
                    if clip._selected:
                        clip.start_frame -= 1
                        clip.end_frame -= 1

                self.scene.generate_mlt()
                self.updateImage()

            else:
                self.playhead -= 1
                self.updateImage()
                self.update()

        elif event.key() == QtCore.Qt.Key_Right:
            if event.modifiers() & QtCore.Qt.ShiftModifier:
                for clip in self.scene.clips:
                    if clip._selected:
                        clip.start_frame += 1
                        clip.end_frame += 1

                self.scene.generate_mlt()
                self.updateImage()

            else:
                self.playhead += 1
                self.updateImage()
                self.update()

        elif event.key() == QtCore.Qt.Key_1: # view 1:1
            self.camera.identity()
            self.camera.translate(100, self.height()-50)
            self.update()

        elif event.key() == QtCore.Qt.Key_R: # render

            # parameters = "f=avi acodec=pcm_s16le ac=2 vcodec=huffyuv"
            parameters = "f=avi acodec=pcm_s16le ac=2 vcodec=huffyuv"
            consumer = mlt.Consumer(mlt_profile, "avformat", "output.avi")
            consumer.set("rescale", "none")

            data = parameters.split(" ")
            for l in data:
                k, v = l.split("=")
                consumer.set(k, v)

            consumer.connect(self.scene.tractor)

            self.scene.tractor.set_speed(0)
            self.scene.tractor.seek(0)
            self.scene.tractor.set_speed(1)

            print "starting rendering"
            consumer.start()

            import time
            while consumer.is_stopped() == 0:
                progress = int(100.0*self.scene.tractor.frame()/self.scene.tractor.get_length())
                print "%3d" % progress,
                print "[%s%s]" % ( "#"*progress, " "*(100-progress) )
                time.sleep(1)

            progress = 100
            print "%3d" % progress,
            print "[%s%s]" % ( "#"*progress, " "*(100-progress) )
            print "finished"

        elif event.key() == QtCore.Qt.Key_A: # analyze
            for count, pl in enumerate(self.scene.playlists):
                print "---"*10
                print "Playlist #%d" % count
                for c in range(pl.count()):
                    info = pl.clip_info(c)
                    print info.start, info.frame_in, info.frame_out, info.length, info.frame_count, info.resource

        elif event.key() == QtCore.Qt.Key_C: # compact

            self.empty_frames = []

            max_frame = 0

            for c in self.scene.clips:
                max_frame = max(max_frame, int(c.end_frame))

            for f in range(max_frame+1):

                blanks = []
                for c, pl in enumerate(self.scene.playlists):
                    producer = pl.get_clip_at(f)
                    if producer is None:
                        blanks.append(True)
                    else:
                        blanks.append(producer.is_blank())

                if sum(blanks) == len(self.scene.playlists):
                    self.empty_frames.append(f)

            for clip in self.scene.clips:
                ef = filter(lambda i: i < clip.start_frame, self.empty_frames)

                clip.start_frame -= len(ef)
                clip.end_frame -= len(ef)

            self.scene.generate_mlt()

            self.updateImage()
            self.update()

        elif event.key() == QtCore.Qt.Key_Delete:
            for clip in self.scene.clips:
                if clip._selected:

                    self.scene.clips.remove(clip)

                    self.scene.generate_mlt()
                    self.updateImage()

        elif event.key() == QtCore.Qt.Key_B: # split
            selectedClips = filter(lambda i: i._selected, self.scene.clips)
            sc2 = []

            for c in selectedClips:
                if c.inside(self.playhead, -50*c.track+10):
                    sc2.append(c)

            if sc2:
                clip = sc2[0]

                del clip.producer

                import copy
                c1 = copy.deepcopy(clip)
                c2 = copy.deepcopy(clip)

                c1.end_frame = self.playhead
                c1.out_frame = c1.in_frame + (c1.end_frame-c1.start_frame)

                c2.in_frame = c2.in_frame + (self.playhead-c2.start_frame) + 1
                c2.start_frame = self.playhead+1

                self.scene.clips.remove(clip)

                self.scene.clips.append(c1)
                self.scene.clips.append(c2)

                self.scene.generate_mlt()
                self.updateImage()

        elif event.key() == QtCore.Qt.Key_I: # move in point
            selectedClips = filter(lambda i: i._selected, self.scene.clips)
            if selectedClips:
                c = selectedClips[0]

                dx = self.playhead-c.start_frame
                c.in_frame += dx
                c.start_frame += dx

                self.scene.generate_mlt()
                self.updateImage()

        elif event.key() == QtCore.Qt.Key_O: # move out point
            selectedClips = filter(lambda i: i._selected, self.scene.clips)
            if selectedClips:
                c = selectedClips[0]

                dx = self.playhead-c.end_frame
                c.out_frame -= dx
                c.end_frame -= dx

                self.scene.generate_mlt()
                self.updateImage()

        elif event.key() == QtCore.Qt.Key_F2: # rename
            selectedClips = filter(lambda i: i._selected, self.scene.clips)
            if selectedClips:
                c = selectedClips[0]
                new_name, ok = QtGui.QInputDialog.getText(self, "Rename clip", "Rename clip to", text = c.name)
                if ok:
                    c.name = str(new_name)
                    self.update()

    def paintGL(self):
        leftHandWidth = 100

        time1 = time.time()

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        glEnable(GL_BLEND)
        glDepthMask(GL_FALSE)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        glLoadIdentity()

        glLoadMatrixf(self.camera.m)

        glColor4f(1.0, 1.0, 1.0, 1.0)

        # clips

        for clip in self.scene.clips:
            self.unoptimizedLabelRect(clip.start_frame, 0-clip.track*50, clip.end_frame+1, 50-clip.track*50, clip.name, clip._color, selected = clip._selected)

        # switch back to screen space

        glLoadIdentity()

        # test = find tracks top and display stuff there

        trackTop = self.camera.opengl_to_qt(QtCore.QPoint(-self.scene.tracks*50, 0))

        # timeline

        timelineTicks = []

        #max_frame = 0
        #
        #for c in self.scene.clips:
        #    max_frame = max(max_frame, int(c.end_frame))
        #
        #max_frame = max(max_frame, self.width())
        #for c in range((max_frame/25)+1):

        glColor4f(1, 1, 1, 1.0)
        for c in range(self.width()/25):

            p1 = self.camera.opengl_to_qt(QtCore.QPoint(c*25, 0))

            top = trackTop.y()
            height = 5

            if c % 10 == 0:
                height = 10

                self.tc.frames = c*25
                self.renderText(p1.x()+1, top-10-self.scene.tracks*50, "%s" % str(self.tc), self.gl_font)

            if c % 30 == 0:
                height = 10

                self.tc.frames = c*25
                self.renderText(p1.x()+1, top-10-self.scene.tracks*50, "%s" % str(self.tc), self.gl_font)

            if c % 60 == 0:
                height = 35

            timelineTicks.extend([p1.x(), top-height-self.scene.tracks*50, p1.x(), top-self.scene.tracks*50])

        #glColor4f(1, 1, 1, 1.0)
        #for c in range(self.width()/25):
        #    timelineTicks.extend([p1.x(), top-height-self.scene.tracks*50, p1.x(), top-self.scene.tracks*50])

        glColor4f(1.0, 0.0, 1.0, 1.0)
        glVertexPointer(2, GL_FLOAT, 0, timelineTicks)
        glEnableClientState(GL_VERTEX_ARRAY)

        glDrawArrays(GL_LINES, 0, len(timelineTicks)/2)

        glDisableClientState(GL_VERTEX_ARRAY)

        # playhead

        sph_width = max(1.0, 1 * self.camera.m[0])

        p2 = self.camera.opengl_to_qt(QtCore.QPoint(self.playhead, 0))
        sph = p2.x()

        glColor(0, 255, 0)
        glEnableClientState(GL_VERTEX_ARRAY)
        squareVertices = [
              sph,           trackTop.y()-self.scene.tracks*50-25,
              sph,           trackTop.y()+50,
              sph+sph_width, trackTop.y()+50,
              sph+sph_width, trackTop.y()-self.scene.tracks*50-25,
        ]

        glVertexPointer(2, GL_FLOAT, 0, squareVertices)

        glDrawArrays(GL_QUADS, 0, len(squareVertices)/2)

        squareVertices = [
              sph-35, trackTop.y()-self.scene.tracks*50-25-25,
              sph-35, trackTop.y()-self.scene.tracks*50-25,
              sph+35, trackTop.y()-self.scene.tracks*50-25,
              sph+35, trackTop.y()-self.scene.tracks*50-25-25,
        ]

        glVertexPointer(2, GL_FLOAT, 0, squareVertices)

        glDrawArrays(GL_QUADS, 0, len(squareVertices)/2)

        glDisableClientState(GL_VERTEX_ARRAY)

        glColor4f(0.0, 0.0, 0.0, 1.0)
        self.tc.frames = self.playhead#-leftHandWidth
        self.renderText(sph-30+2, trackTop.y()-self.scene.tracks*50-25-15, "%s" % str(self.tc), self.gl_font)
        self.renderText(sph-30+2, trackTop.y()-self.scene.tracks*50-25-15+12, "%s" % str(self.tc.frames), self.gl_font)

        # track names

        for c in range(self.scene.tracks+1):
            clipsCoordinates = 0 # vertically

            p1 = self.camera.opengl_to_qt(QtCore.QPoint(0, clipsCoordinates))
            self.unoptimizedLabelRect(0, p1.y()-(c)*50, leftHandWidth, p1.y()-(c-1)*50, "track %d" % c, (0.5, 0.5, 0.5, 1), False, False)

        # image

        if self.texture_data is not None:
            if self.texture == -1:
                self.texture = self.convertNumpyToGLTexture(self.texture_data)
                self.texture_data = None

        if self.texture != -1:

            glColor4f(1.0, 1.0, 1.0, 1.0)

            glEnable(texture_mode)

            glEnableClientState(GL_VERTEX_ARRAY)
            glEnableClientState(GL_TEXTURE_COORD_ARRAY)

            glBindTexture(texture_mode, self.texture)


            glVertexPointer(2, GL_FLOAT, 0, self.pointVertices)
            glTexCoordPointer(2, GL_FLOAT, 0, self.textureCoordinates)

            glDrawArrays(GL_QUADS, 0, len(self.pointVertices)/2)

            glDisableClientState(GL_TEXTURE_COORD_ARRAY)
            glDisableClientState(GL_VERTEX_ARRAY)
            glDisable(texture_mode)

            # border

            glEnableClientState(GL_VERTEX_ARRAY)

            glVertexPointer(2, GL_FLOAT, 0, self.pointVertices)
            glDrawArrays(GL_LINE_STRIP, 0, len(self.pointVertices)/2)

            glDisableClientState(GL_VERTEX_ARRAY)

        # debugging - fps

        glColor4f(1.0, 1.0, 1.0, 1.0)
        dtime = time.time()-time1
        self.renderText(self.width()-100, self.height()-25, "%05d fps" % (int(1/dtime)))

        # current tc

        #self.renderText(self.width()-100, self.height()-50, "%s" % str(self.tc))

    def _prepare_gl_line_loop_tl(self, x1, y1, x2, y2):
        sz = 2

        return [
              x1, y1,
              x1, y2,
              x1+sz, y2,
              x1+sz, y1,

              x1, y1,
              x2, y1,
              x2, y1+sz,
              x1, y1+sz,

              ]

    def _prepare_gl_line_loop_br(self, x1, y1, x2, y2):
        sz = 2

        return [
              x2, y1,
              x2, y2,
              x2-sz, y2,
              x2-sz, y1,

              x1, y2,
              x2, y2,
              x2, y2-sz,
              x1, y2-sz,

              ]


    def _prepare_gl_quads(self, x1, y1, x2, y2):
        return [
              x1, y1,
              x1, y2,
              x2, y2,
              x2, y1, ]

    def unoptimizedLabelRect(self, x1, y1, x2, y2, label, color1, fontScaled = True, selected = False):

        if selected:
            color1 = (color1[0]*1.1, color1[1]*1.1, color1[2]*1.1, color1[3])

            vertices_br = self._prepare_gl_line_loop_tl(x1, y1, x2, y2)
            vertices_lt = self._prepare_gl_line_loop_br(x1, y1, x2, y2)

        else:

            vertices_lt = self._prepare_gl_line_loop_tl(x1, y1, x2, y2)
            vertices_br = self._prepare_gl_line_loop_br(x1, y1, x2, y2)

        vertices  = self._prepare_gl_quads(x1, y1, x2, y2)

        glEnableClientState(GL_VERTEX_ARRAY)

        #if selected:
        #    verticesSelected  = self._prepare_gl_quads(x1-3, y1-3, x2+3, y2+3)
        #
        #    glColor4f(1, 0, 0, 0.5)
        #    glVertexPointer(2, GL_FLOAT, 0, verticesSelected)
        #    glDrawArrays(GL_QUADS, 0, len(verticesSelected)/2)

        glColor4f(*color1)
        glVertexPointer(2, GL_FLOAT, 0, vertices)
        glDrawArrays(GL_QUADS, 0, len(vertices)/2)

        #

        bcolor = (color1[0]*1.3, color1[1]*1.3, color1[2]*1.3, color1[3])
        dcolor = (color1[0]/1.1, color1[1]/1.1, color1[2]/1.1, color1[3])

        glColor4f(*bcolor)
        glVertexPointer(2, GL_FLOAT, 0, vertices_lt)
        glDrawArrays(GL_QUADS, 0, len(vertices_lt)/2)

        glColor4f(*dcolor)
        glVertexPointer(2, GL_FLOAT, 0, vertices_br)
        glDrawArrays(GL_QUADS, 0, len(vertices_br)/2)

        glDisableClientState(GL_VERTEX_ARRAY)

        glColor4f(0.2, 0.2, 0.2, 1.0)
        if selected:
            dx = 1
        else:
            dx = 0

        if fontScaled:
            p1 = self.camera.opengl_to_qt(QtCore.QPoint(x1, y1))
            self.renderText(p1.x()+2+dx, p1.y()+10+2+dx, label, self.gl_font)
        else:
            self.renderText(x1+2+dx, y1+10+2+dx, label, self.gl_font)

if __name__ == '__main__':

    app = QtGui.QApplication([])

    f = MainForm()
    f.show()
    f.raise_()

    app.exec_()
