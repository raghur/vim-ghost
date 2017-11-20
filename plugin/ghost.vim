
function s:loadGhost()
    if !has("nvim")
        return
    endif

    if !has('timers')
        return
    endif

    if exists("g:ghost_autostart") && g:ghost_autostart
        let timer = timer_start(500,
                    \ { -> execute("GhostStart") })
    endif
endfunction

call s:loadGhost()
