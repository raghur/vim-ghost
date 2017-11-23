if exists("g:loaded_ghost")
    finish
endif

let g:loaded_ghost = 1

function! s:installGhost()
    let out = system("./install")
    UpdateRemotePlugins
    echom ":UpdateRemotePlugins executed. Please restart nvim"
endfunction
command! -nargs=0 GhostInstall call s:installGhost()

function! s:startGhost(tid)
    " during first installation, neovim has to be restarted after
    " :UpdateRemotePlugins
    if !exists(":GhostStart")
        echom ":GhostStart not found. If this the first time you have installed nvim, then please restart nvim"
        return
    endif
    GhostStart
endfunction
function! s:loadGhost()
    if !has("nvim")
        return
    endif

    if !has('timers')
        return
    endif

    if exists("g:ghost_autostart") && g:ghost_autostart
        let timer = timer_start(500, function("s:startGhost"))
    endif
endfunction

call s:loadGhost()
