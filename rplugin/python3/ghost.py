from http.server import HTTPServer, BaseHTTPRequestHandler
from SimpleWebSocketServer import SimpleWebSocketServer, WebSocket
from random import randint
from threading import Thread
from tempfile import mkstemp
import logging
import json
import neovim
bufferHandlerMap = {}
nvimObj = None
class GhostWebSocketHandler(WebSocket):
    def handleMessage(self):
        # echo message back to client
        logging.info("recd websocket message")
        self._onMessage(self.data)

    def handleConnected(self):
        print(self.address, 'connected')

    def handleClose(self):
        print(self.address, 'closed')

    def _onMessage(self, text):
        tempfileHandle, tempfileName = mkstemp(suffix=".txt", text=True)
        nvimObj.command("ed %s" % tempfileName)
        nvimObj.current.buffer[:] = text.split("\n")
        bufnr = nvimObj.current.buffer.number
        aucmd = ("au TextChanged, TextChangedI <buffer> call"
                          " ghostSend(%d)" % bufnr)
        bufferHandlerMap[bufnr]=self
        nvimObj.command(aucmd)

def startWebSocketSvr(port):
    webSocketServer = SimpleWebSocketServer('', port, GhostWebSocketHandler)
    wsThread = Thread(target=webSocketServer.serveforever, daemon=True)
    wsThread.start()

class WebRequestHandler(BaseHTTPRequestHandler):
    def _set_headers(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

    def do_GET(self):
        self._set_headers()
        port = randint(60000, 65535)
        responseObj = {"ProtocolVersion": 1}
        responseObj["WebSocketPort"] = port
        startWebSocketSvr(port)
        self.wfile.write(json.dumps(responseObj).encode())


@neovim.plugin
class Ghost(object):
    def __init__(self, vim):
        self.nvim = vim
        nvimObj = vim
        logging.basicConfig(level=logging.DEBUG)
        self.serverStarted = False

    @neovim.command('GhostStart', range='', nargs='0', sync=True)
    def server_start(self, args, range):
        if self.serverStarted:
            self.nvim.command("echo 'Ghost server already running'")
            logging.info("server already running")
            return

        self.httpserver = HTTPServer(('', 4001), WebRequestHandler)
        httpserverThread = Thread(target=self.httpserver.serve_forever, daemon=True)
        httpserverThread.start()
        self.serverStarted = True
        logging.info("server started")
        self.nvim.command("echo 'Ghost server started'")

    @neovim.command('GhostStop', range='', nargs='0', sync=True)
    def server_stop(self, args, range):
        if not self.serverStarted:
            self.nvim.command("echo 'Server not running'")
            return
        self.httpserver.shutdown()
        self.nvim.command("echo 'Ghost server stopped'")

    @neovim.function("GhostSend", sync=True)
    def ghostSend(self, args):
        print("in ghostSend", args)
        logging.info(args)


    # @neovim.autocmd('BufEnter', pattern='*.py', eval='expand("<afile>")',
    #                 sync=True)
    # def autocmd_handler(self, filename):
    #     self.nvim.current.line = (
    #         'Autocmd: Called %s times, file: %s' % (self.calls, filename))

    # @neovim.function('Func')
    # def function_handler(self, args):
    #     self.nvim.current.line = (
    #         'Function: Called %d times, args: %s' % (self.calls, args))

