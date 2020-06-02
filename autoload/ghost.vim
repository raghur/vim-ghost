function! ghost#install()
    py3 import ghost_install
    py3 ghost_install.install()
    if has("nvim")
        UpdateRemotePlugins
        echom ":UpdateRemotePlugins executed. Please restart nvim"
    endif
endfunction

function! s:initGhost(...)
    " init ghost - capture window id to raise if necessary (*nix only)
    " Then if autostart is enabled, then start
    call s:SetWindowId()
    if !exists(":GhostStart")
        echom ":GhostStart not found. If you just installed vim-ghost, please restart nvim"
        return
    endif
    if exists("g:ghost_autostart") && g:ghost_autostart
        GhostStart
    endif
endfunction

function! s:SetWindowId()
    if executable("xdotool")
        let g:ghost_nvim_window_id = system("xdotool getactivewindow")
        return
    endif
endfunction

function! ghost#load()
    if !has('timers')
        call s:initGhost()
        return
    endif
    let timer = timer_start(500, function("s:initGhost"))
endfunction
