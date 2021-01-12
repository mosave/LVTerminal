from ctypes import *

# From alsa-lib Git 3fd4ab9be0db7c7430ebd258f2717a976381715d
# $ grep -rn snd_lib_error_handler_t
# include/error.h:59:typedef void (*snd_lib_error_handler_t)(const char *file, int line, const char *function, int err, const char *fmt, ...) /* __attribute__ ((format (printf, 5, 6))) */;

ERROR_HANDLER_FUNC = CFUNCTYPE(None, c_char_p, c_int, c_char_p, c_int, c_char_p)

def py_error_handler(filename, line, function, err, fmt):
  #print('messages are yummy')
  pass

errorHandler = ERROR_HANDLER_FUNC(py_error_handler)
asoundLib = None

class AlsaSupressor():
    def disableWarnings():
        global asoundLib
        global errorHandler

        try: 
            asoundLib = cdll.LoadLibrary('libasound.so.2.0.0')
        except: 
            try: 
                asoundLib = cdll.LoadLibrary('libasound.so.2')
            except: 
                try: asoundLib = cdll.LoadLibrary('libasound.so')
                except: asoundLib = None

        if asoundLib != None: 
            try:
                asoundLib.snd_lib_error_set_handler(errorHandler)
            except Exception as e :
                asoundLib = None

    def enableWarnings():
        global asoundLib
        if asoundLib != None :
            try:
                # Reset to default error handler
                asoundLib.snd_lib_error_set_handler(None)
            except:
                pass
