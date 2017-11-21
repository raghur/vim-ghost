" let s:install_path=expand('<sfile>:p:h:h')
" function! GhostInstallDepsfn()
"     let cmd = ['pip3', 'install', '--user', '-r', s:install_path . '/requirements.txt']
"     echom "Running: " . join(cmd, " ")
"     call system(cmd)
"     echom "ghost dependencies installed."
" endfunction
" command! -nargs=0 GhostInstallDeps call GhostInstallDepsfn()

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
