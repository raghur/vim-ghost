if exists("g:loaded_ghost")
    finish
endif

let g:loaded_ghost = 1

function! s:installGhost()
    " just running ./install doesn't work on windows.
    " form full path and call.
    let out = system(getcwd() . "/install")
    UpdateRemotePlugins
    echom ":UpdateRemotePlugins executed. Please restart nvim"
endfunction
command! -nargs=0 GhostInstall call s:installGhost()

function! s:startGhost(tid)
    " during first installation, neovim has to be restarted after
    " :UpdateRemotePlugins
    if !exists(":GhostStart")
        echom ":GhostStart not found. If you just installed vim-ghost, please restart nvim"
        return
    endif
    GhostStart
endfunction

function! s:getWindowLocater(tid)
    if executable("xdotool")
        let g:ghost_nvim_window_id = system("xdotool getactivewindow")
    endif
    if executable("powershell")
        " Does not work with terminal nvim.
        let g:ghost_nvim_process_id 
                    \ = system("powershell -Command \"Get-Process -Name nvim-qt |select -ExpandProperty Id\"")
    endif
endfunction

function! s:loadGhost()
    if !has("nvim")
        return
    endif

    if !has('timers')
        return
    endif

    call timer_start(250, function("s:getWindowLocater"))

    if exists("g:ghost_autostart") && g:ghost_autostart
        let timer = timer_start(500, function("s:startGhost"))
    endif
endfunction

call s:loadGhost()
