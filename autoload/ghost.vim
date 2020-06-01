function! ghost#install()
    py3 import ghost_install
    py3 ghost_install.install()
    if has("nvim")
        UpdateRemotePlugins
        echom ":UpdateRemotePlugins executed. Please restart nvim"
    endif
endfunction

function! s:startGhost(tid)
    " during first installation, neovim has to be restarted after
    " :UpdateRemotePlugins
    call s:SetWindowId()
    if !exists(":GhostStart")
        echom ":GhostStart not found. If you just installed vim-ghost, please restart nvim"
        return
    endif
    GhostStart
endfunction

function! s:SetWindowId()
    if exists("g:ghost_nvim_window_id")
        return
    endif
    if executable("xdotool")
        let g:ghost_nvim_window_id = system("xdotool getactivewindow")
        return
    endif
endfunction

function! ghost#load()
    if !has('timers')
        call s:SetWindowId()
        return
    endif

    if exists("g:ghost_autostart") && g:ghost_autostart
        let timer = timer_start(500, function("s:startGhost"))
    endif
endfunction
