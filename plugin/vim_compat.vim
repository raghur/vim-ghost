" plugin/foo.vim
if has('nvim')
    finish
endif

let s:ghost = yarp#py3('ghost_wrapper')

func! GhostNotify(v)
    return s:ghost.call('ghost_notify',a:v)
endfunc

com -nargs=0 GhostStart call s:ghost.call('server_start')
com -nargs=0 GhostStop call s:ghost.call('server_stop')
