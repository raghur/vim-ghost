from ghost import Ghost as _Ghost
import vim

_obj = _Ghost(vim)

def server_start(*args):
    return _obj.server_start(args, '')

def server_stop(*args):
    return _obj.server_stop(args, '')

def ghost_notify(*args):
    return _obj.ghost_notify(args)
