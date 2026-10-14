"""Minimal software-rendered Libretro frontend for a Nintendo DS core."""
import ctypes as C
from pathlib import Path
import numpy as np

ENV_GET_SYSTEM_DIRECTORY=9
ENV_SET_PIXEL_FORMAT=10
ENV_GET_VARIABLE=15
ENV_SET_VARIABLES=16
ENV_GET_VARIABLE_UPDATE=17
ENV_GET_SAVE_DIRECTORY=31
ENV_SET_SUPPORT_NO_GAME=18
ENV_GET_LOG_INTERFACE=27
ENV_GET_CORE_OPTIONS_VERSION=52
ENV_GET_INPUT_BITMASKS=51
ENV_GET_LANGUAGE=39
PIXEL_0RGB1555=0
PIXEL_XRGB8888=1
PIXEL_RGB565=2
DEVICE_JOYPAD=1
BUTTONS={'B':0,'Y':1,'SELECT':2,'START':3,'UP':4,'DOWN':5,'LEFT':6,'RIGHT':7,'A':8,'X':9,'L':10,'R':11}

class GameInfo(C.Structure):
    _fields_=[('path',C.c_char_p),('data',C.c_void_p),('size',C.c_size_t),('meta',C.c_char_p)]
class Variable(C.Structure):
    _fields_=[('key',C.c_char_p),('value',C.c_char_p)]
class Geometry(C.Structure):
    _fields_=[('base_width',C.c_uint),('base_height',C.c_uint),('max_width',C.c_uint),('max_height',C.c_uint),('aspect_ratio',C.c_float)]
class Timing(C.Structure):
    _fields_=[('fps',C.c_double),('sample_rate',C.c_double)]
class AVInfo(C.Structure):
    _fields_=[('geometry',Geometry),('timing',Timing)]

ENV_CB=C.CFUNCTYPE(C.c_bool,C.c_uint,C.c_void_p)
VIDEO_CB=C.CFUNCTYPE(None,C.c_void_p,C.c_uint,C.c_uint,C.c_size_t)
AUDIO_CB=C.CFUNCTYPE(None,C.c_int16,C.c_int16)
AUDIO_BATCH_CB=C.CFUNCTYPE(C.c_size_t,C.c_void_p,C.c_size_t)
INPUT_POLL_CB=C.CFUNCTYPE(None)
INPUT_STATE_CB=C.CFUNCTYPE(C.c_int16,C.c_uint,C.c_uint,C.c_uint,C.c_uint)

class DSEmulator:
    def __init__(self,core_path,rom_path,system_dir='system',save_dir='saves'):
        self.core_path=Path(core_path).resolve()
        self.rom_path=Path(rom_path).resolve()
        self.system_dir=Path(system_dir).resolve()
        self.save_dir=Path(save_dir).resolve()
        self.system_dir.mkdir(parents=True,exist_ok=True)
        self.save_dir.mkdir(parents=True,exist_ok=True)
        if not self.core_path.is_file(): raise FileNotFoundError(f'Core missing: {self.core_path}')
        if not self.rom_path.is_file(): raise FileNotFoundError(f'ROM missing: {self.rom_path}')
        self._system_bytes=str(self.system_dir).encode()
        self._save_bytes=str(self.save_dir).encode()
        self._rom_bytes=str(self.rom_path).encode()
        self._variables={}
        self._variable_buffers=[]
        self.pixel_format=PIXEL_0RGB1555
        self.frame=None
        self.buttons=set()
        self.loaded=False
        self.initialized=False
        self.lib=C.CDLL(str(self.core_path))
        self._bind()
        self._install_callbacks()
        self.lib.retro_init()
        self.initialized=True
        info=GameInfo(self._rom_bytes,None,0,None)
        if not self.lib.retro_load_game(C.byref(info)):
            self.close()
            raise RuntimeError('Core rejected ROM. Verify ROM, BIOS/core compatibility, and core options.')
        self.loaded=True
        av=AVInfo()
        self.lib.retro_get_system_av_info(C.byref(av))
        self.fps=av.timing.fps

    def _bind(self):
        lib=self.lib
        for name,cb in [('retro_set_environment',ENV_CB),('retro_set_video_refresh',VIDEO_CB),('retro_set_audio_sample',AUDIO_CB),('retro_set_audio_sample_batch',AUDIO_BATCH_CB),('retro_set_input_poll',INPUT_POLL_CB),('retro_set_input_state',INPUT_STATE_CB)]:
            getattr(lib,name).argtypes=[cb]
            getattr(lib,name).restype=None
        lib.retro_init.argtypes=[];lib.retro_init.restype=None
        lib.retro_deinit.argtypes=[];lib.retro_deinit.restype=None
        lib.retro_load_game.argtypes=[C.POINTER(GameInfo)];lib.retro_load_game.restype=C.c_bool
        lib.retro_unload_game.argtypes=[];lib.retro_unload_game.restype=None
        lib.retro_run.argtypes=[];lib.retro_run.restype=None
        lib.retro_get_system_av_info.argtypes=[C.POINTER(AVInfo)];lib.retro_get_system_av_info.restype=None
        lib.retro_serialize_size.argtypes=[];lib.retro_serialize_size.restype=C.c_size_t
        lib.retro_serialize.argtypes=[C.c_void_p,C.c_size_t];lib.retro_serialize.restype=C.c_bool
        lib.retro_unserialize.argtypes=[C.c_void_p,C.c_size_t];lib.retro_unserialize.restype=C.c_bool

    def _install_callbacks(self):
        @ENV_CB
        def environment(cmd,data):
            if cmd in (ENV_GET_SYSTEM_DIRECTORY,ENV_GET_SAVE_DIRECTORY):
                if not data:return False
                C.cast(data,C.POINTER(C.c_char_p))[0]=self._system_bytes if cmd==ENV_GET_SYSTEM_DIRECTORY else self._save_bytes
                return True
            if cmd==ENV_SET_PIXEL_FORMAT:
                if not data:return False
                fmt=C.cast(data,C.POINTER(C.c_int))[0]
                if fmt not in (PIXEL_0RGB1555,PIXEL_XRGB8888,PIXEL_RGB565):return False
                self.pixel_format=fmt
                return True
            if cmd==ENV_SET_VARIABLES:
                if not data:return False
                vars_ptr=C.cast(data,C.POINTER(Variable))
                i=0
                while vars_ptr[i].key:
                    key=vars_ptr[i].key.decode()
                    raw=(vars_ptr[i].value or b'').decode()
                    choices=raw.split(';',1)[-1].strip().split('|')
                    self._variables.setdefault(key,choices[0].strip().encode())
                    i+=1
                return True
            if cmd==ENV_GET_VARIABLE:
                if not data:return False
                var=C.cast(data,C.POINTER(Variable)).contents
                key=var.key.decode() if var.key else ''
                value=self._variables.get(key)
                if value is None:return False
                var.value=value
                return True
            if cmd==ENV_GET_VARIABLE_UPDATE:
                if data:C.cast(data,C.POINTER(C.c_bool))[0]=False
                return True
            if cmd==ENV_GET_CORE_OPTIONS_VERSION:
                if data:C.cast(data,C.POINTER(C.c_uint))[0]=0
                return True
            if cmd==ENV_GET_LANGUAGE:
                if data:C.cast(data,C.POINTER(C.c_uint))[0]=0
                return True
            if cmd==ENV_GET_INPUT_BITMASKS:return False
            return False

        @VIDEO_CB
        def video(data,width,height,pitch):
            if not data:return  # null pointer = duplicate previous frame
            bpp=4 if self.pixel_format==PIXEL_XRGB8888 else 2
            raw=C.string_at(data,pitch*height)
            if bpp==4:
                pixels=np.frombuffer(raw,dtype='<u4').reshape(height,pitch//4)[:,:width]
                r=((pixels>>16)&255).astype(np.uint8)
                g=((pixels>>8)&255).astype(np.uint8)
                b=(pixels&255).astype(np.uint8)
            else:
                pixels=np.frombuffer(raw,dtype='<u2').reshape(height,pitch//2)[:,:width]
                if self.pixel_format==PIXEL_RGB565:
                    r=(((pixels>>11)&31)*255//31).astype(np.uint8)
                    g=(((pixels>>5)&63)*255//63).astype(np.uint8)
                    b=((pixels&31)*255//31).astype(np.uint8)
                else:
                    r=(((pixels>>10)&31)*255//31).astype(np.uint8)
                    g=(((pixels>>5)&31)*255//31).astype(np.uint8)
                    b=((pixels&31)*255//31).astype(np.uint8)
            self.frame=np.stack((r,g,b),axis=-1)

        @AUDIO_CB
        def audio(left,right):pass
        @AUDIO_BATCH_CB
        def audio_batch(data,frames):return frames
        @INPUT_POLL_CB
        def input_poll():pass
        @INPUT_STATE_CB
        def input_state(port,device,index,button_id):
            if port!=0 or device!=DEVICE_JOYPAD:return 0
            return int(button_id in self._pressed_ids)
        self._pressed_ids=set()
        self._callbacks=[environment,video,audio,audio_batch,input_poll,input_state]
        for method,cb in zip(('retro_set_environment','retro_set_video_refresh','retro_set_audio_sample','retro_set_audio_sample_batch','retro_set_input_poll','retro_set_input_state'),self._callbacks):
            getattr(self.lib,method)(cb)

    def step(self,buttons=(),frames=1):
        self._pressed_ids={BUTTONS[b.upper()] for b in buttons}
        for _ in range(frames):self.lib.retro_run()
        self._pressed_ids.clear()
        return self.frame

    def save_state(self,path):
        size=self.lib.retro_serialize_size()
        if not size:raise RuntimeError('Core does not support serialization at this point')
        buf=C.create_string_buffer(size)
        if not self.lib.retro_serialize(buf,size):raise RuntimeError('Failed to serialize state')
        Path(path).write_bytes(buf.raw)

    def load_state(self,path):
        data=Path(path).read_bytes()
        buf=C.create_string_buffer(data)
        if not self.lib.retro_unserialize(buf,len(data)):raise RuntimeError('Failed to load state (wrong core or incompatible version?)')

    def close(self):
        if self.loaded:self.lib.retro_unload_game();self.loaded=False
        if self.initialized:self.lib.retro_deinit();self.initialized=False
