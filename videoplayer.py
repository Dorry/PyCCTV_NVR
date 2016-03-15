import os, time, glob
import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstPbutils', '1.0')

from gi.repository import Gst, Gtk, Gdk
from gi.repository import GdkX11, GstVideo, GstPbutils

from utils import nsec2time

class VideoPlayer(Gtk.Window):
    player_title = u'PyCCTV_NVR VideoPlayer'
    def __init__(self, app, prefix, period, isDate=True):
        super(VideoPlayer, self).__init__(type=Gtk.WindowType.TOPLEVEL)
        
        self.app = app
        self.playlist = []
        self.play_index = -1
        self.is_playing = False
        
        self.set_title(self.player_title)
        self.set_border_width(2)
        self.modify_bg(Gtk.StateType.NORMAL, Gdk.Color(20000, 20000, 20000))
        self.set_transient_for(app)
        self.set_destroy_with_parent(True)
        self.set_modal(True)
        
        self._setupUI()
        
        if prefix is not None:
            self._get_videos(prefix, isDate, period)
        
        
    def _setupUI(self):
        hbox = Gtk.HBox()
        self.add(hbox)
        
        vbox = Gtk.VBox()
        hbox.add(vbox)
        
        sc_win = Gtk.ScrolledWindow()
        sc_win.set_size_request(200, -1)
        sc_win.set_border_width(4)
        sc_win.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        sc_win.set_shadow_type(Gtk.ShadowType.IN)
        
        self.store = self._create_model()
        self.listview = Gtk.TreeView(self.store)
        
        sc_win.add(self.listview)
        
        hbox.pack_end(sc_win, False, True, 0)
        
        self.video_frame = Gtk.DrawingArea()
        self.video_frame.modify_bg(Gtk.StateType.NORMAL, Gdk.Color(0, 0, 0))
        self.video_frame.set_size_request(640, 480)
        vbox.pack_start(self.video_frame, True, True, 0)
        
        # play control
        ctrl2_hbox = Gtk.HBox()
        
        self.prev_btn = Gtk.Button()
        self.rewind_btn = Gtk.Button()
        self.play_btn = Gtk.Button()
        self.stop_btn = Gtk.Button()
        self.forward_btn = Gtk.Button()
        self.next_btn = Gtk.Button()
        
        ctrl_buttons = ((self.prev_btn, Gtk.STOCK_MEDIA_PREVIOUS, u'이전 영상 <B>', self.on_prev_clicked, ),
                        (self.rewind_btn, Gtk.STOCK_MEDIA_REWIND, u'10초전으로 <Right Arrow>', self.on_rewind_clicked),
                        (self.play_btn, Gtk.STOCK_MEDIA_PLAY, u'재생 <Spacebar>', self.on_play_clicked),
                        (self.stop_btn, Gtk.STOCK_MEDIA_STOP, u'정지 <S>', self.on_stop_clicked),
                        (self.forward_btn, Gtk.STOCK_MEDIA_FORWARD, u'10초앞으로 <Left Arrow>', self.on_forward_clicked),
                        (self.next_btn, Gtk.STOCK_MEDIA_NEXT, u'다음 영상 <N>', self.on_next_clicked))
        
        for btn, st_img, tooltip, clickfunc in ctrl_buttons:
            btn_img = Gtk.Image()
            btn_img.set_from_stock(st_img, Gtk.IconSize.BUTTON)
            btn.set_image(btn_img)
            btn.set_tooltip_text(tooltip)
            btn.set_relief(Gtk.ReliefStyle.NONE)
            btn.set_sensitive(False)
            btn.connect('clicked', clickfunc)
            ctrl2_hbox.pack_start(btn, False, False, 0)
            
        self.connect('key-release-event', self.on_key_release)
        
        vbox.pack_end(ctrl2_hbox, False, False, 2)
        
        # play time, progress
        ctrl1_hbox = Gtk.HBox(spacing=4)
        
        self.lbl_pos = Gtk.Label('00:00:00')
        self.lbl_pos.set_margin_left(4)
        self.lbl_pos.modify_fg(Gtk.StateType.NORMAL, Gdk.Color(65535, 30000, 0))
        ctrl1_hbox.pack_start(self.lbl_pos, False, False, 0)
        
        self.progress = Gtk.HScale()
        self.progress.set_draw_value(False)
        self.progress.modify_bg(Gtk.StateType.NORMAL, Gdk.Color(65535, 30000, 0))
        ctrl1_hbox.pack_start(self.progress, True, True, 0)
        
        self.lbl_dur = Gtk.Label('00:00:00')
        self.lbl_dur.set_margin_right(4)
        self.lbl_dur.modify_fg(Gtk.StateType.NORMAL, Gdk.Color(65535, 30000, 0))
        ctrl1_hbox.pack_start(self.lbl_dur, False, False, 0)
        
        vbox.pack_end(ctrl1_hbox, False, False, 3)
        
        self.show_all()
    
    def _create_model(self):
        store = Gtk.ListStore(str, str)
        return store
    
    def _get_videos(self, prefix, isDate, period):
        #vid_list = glob.glob(os.path.join(self.app.config['VIDEO_PATH'], prefix+'_*'))
        vid_list = glob.glob(os.path.join('.', prefix+'_*'))
        
        if len(vid_list) == 0:
            dialog = Gtk.MessageDialog(self, 0, Gtk.MessageType.ERROR,
                                       Gtk.ButtonsType.CLOSE, "Don't exists CCTV Videos")
            dialog.format_secondary_text("재생가능한 CCTV 영상이 존재하지 않습니다!!!")
            dialog.run()
            print('Error dialog closed')
            dialog.destroy()
            
            return False
        
        video_count = 0
        info = None
        create_time = int(time.time())
         
        def get_duration(fname):
            discoverer = GstPbutils.Discoverer.new(Gst.SECOND)
            return discoverer.discover_uri('file://'+fname)
        
        for filename in vid_list:
            full_filename = os.path.join(self.app.config['VIDEO_PATH'], filename)
            if os.path.isfile(full_filename):
                if (create_time - os.path.getctime(full_filename)) >= 1800:
                    _date, _time = str(filename.split('.')[0]).split('_')[1:]
                    if isDate:
                        if int(_date) >= period[0] and int(_date) <= period[1]:
                            info = get_duration(full_filename)
                    else:
                        if int(_time) >= period[0] and int(_time) <= period[1]:
                            info = get_duration(full_filename)
                            
                    if info is not None:
                        video_count = video_count + 1
                        self.playlist.append(filename)
                        print(info.get_duration())
                        self.store.append([filename, nsec2time(info.get_duration())])
                        info = None

        if video_count == 0:
            dialog = Gtk.MessageDialog(self, 0, Gtk.MessageType.ERROR,
                                       Gtk.ButtonsType.CLOSE, "Don't exists CCTV Videos")
            dialog.format_secondary_text("재생가능한 CCTV 영상이 존재하지 않습니다!!!")
            dialog.run()
            print('Error dialog closed')
            dialog.destroy()
            
            return False
        
        self._init_controller()
        return True
        
    def _init_controller(self):
        if len(self.playlist) > 1:
            self.next_btn.set_sensitive(True)
            
        self.play_btn.set_sensitive(True)
        self.stop_btn.set_sensitive(True)
        
        self.play_index = 0
        self.on_play_clicked(None)
        
    def _change_title(self):
        self.set_title(self.playlist[self.play_index] + ' - ' + self.player_title)
        
    def _play(self):
        pass
    
    def _pause(self):
        pass
    
    def _stop(self):
        pass

    def on_key_release(self, widget, eventkey):
        if eventkey.keyval == Gdk.KEY_b:
            if self.prev_btn.get_sensitive():
                self.prev_btn.clicked()

        elif eventkey.keyval == Gdk.KEY_Left:
            if self.rewind_btn.get_sensitive():
                self.rewind_btn.clicked()

        elif eventkey.keyval == Gdk.KEY_Right:
            if self.forward_btn.get_sensitive():
                self.forward_btn.clicked()
            
        elif eventkey.keyval == Gdk.KEY_space:
            if self.play_btn.get_sensitive():
                self.play_btn.clicked()
            
        elif eventkey.keyval == Gdk.KEY_s:
            if self.stop_btn.get_sensitive():
                self.stop_btn.clicked()
                
        elif eventkey.keyval == Gdk.KEY_n:
            if self.next_btn.get_sensitive():
                self.next_btn.clicked()

        print('%s key is released' % eventkey.keyval)
        

    def on_prev_clicked(self, widget):
        self.play_index = self.play_index - 1
        
        if self.play_index <= 0:
            self.prev_btn.set_sensitive(False)
        else:
            self.prev_btn.set_sensitive(True)
            
        self._change_title()
        
    def on_rewind_clicked(self, widget):
        pass

    def on_play_clicked(self, widget):
        if not self.is_playing:
            btn_img = Gtk.Image()
            btn_img.set_from_stock(Gtk.STOCK_MEDIA_PAUSE, Gtk.IconSize.BUTTON)
            self.play_btn.set_image(btn_img)
            self._play()
        else:
            btn_img = Gtk.Image()
            btn_img.set_from_stock(Gtk.STOCK_MEDIA_PLAY, Gtk.IconSize.BUTTON)
            self.play_btn.set_image(btn_img)
            self._pause()
            
        self.is_playing = not self.is_playing
        self.rewind_btn.set_sensitive(True)
        self.forward_btn.set_sensitive(True)

    def on_stop_clicked(self, widget):
        if self.is_playing:
            btn_img = Gtk.Image()
            btn_img.set_from_stock(Gtk.STOCK_MEDIA_PLAY, Gtk.IconSize.BUTTON)
            self.play_btn.set_image(btn_img)
            
            self.is_playing = False
            self._stop()        

    def on_forward_clicked(self, widget):
        pass

    def on_next_clicked(self, widget):
        self.play_index = self.play_index + 1
        
        if self.play_index == (len(self.playlist) - 1):
            self.next_btn.set_sensitive(False)
            
        self._change_title()
    
    
if __name__ == '__main__':
    from gi.repository import GObject
    
    GObject.threads_init()
    #Gst.init(None)
    
    vp = VideoPlayer(None, 'cam1', None)
    vp.connect('destroy', Gtk.main_quit)
    Gtk.main()