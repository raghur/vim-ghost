if has('nvim')
    finish
endif

let s:ghost = yarp#py3('ghost_wrapper')

func! GhostNotify(event, buffer)
    return s:ghost.call('ghost_notify', a:event, a:buffer)
endfunc

com! -nargs=0 GhostStart call s:ghost.call('server_start')
com! -nargs=0 GhostStop call s:ghost.call('server_stop')
com! -nargs=0 GhostToggleSync call s:ghost.call('ghost_toggle_sync')
com! -nargs=0 GhostSync call s:ghost.call('ghost_sync')
