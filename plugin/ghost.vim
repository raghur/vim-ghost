if exists("g:loaded_ghost")
    finish
endif

let g:loaded_ghost = 1

function! s:installGhost()
    let out = system("./install")
    UpdateRemotePlugins
endfunction
command! -nargs=0 GhostInstall call s:installGhost()

function! s:loadGhost()
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
