if exists("g:loaded_ghost")
    finish
endif

let g:loaded_ghost = 1
command! -nargs=0 GhostInstall call ghost#install()
call ghost#load()
