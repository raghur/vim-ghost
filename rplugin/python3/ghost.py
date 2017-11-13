from http.server import HTTPServer, BaseHTTPRequestHandler
from SimpleWebSocketServer import SimpleWebSocketServer, WebSocket
from random import randint
from threading import Thread
from tempfile import mkstemp
import logging
import json
import neovim
bufferHandlerMap = {}


class GhostWebSocketHandler(WebSocket):
    def handleMessage(self):
        # echo message back to client
        logging.info("recd websocket message")
        self.server.context.onMessage(self.data, self)

    def handleConnected(self):
        print(self.address, 'connected')

    def handleClose(self):
        print(self.address, 'closed')


class MyWebSocketServer(SimpleWebSocketServer):
    def __init__(self, context, *args, **kwargs):
        self.context = context
        SimpleWebSocketServer.__init__(self, *args, **kwargs)

def startWebSocketSvr(context, port):
    webSocketServer = MyWebSocketServer(context, '', port, GhostWebSocketHandler)
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
        startWebSocketSvr(self.server.context, port)
        self.wfile.write(json.dumps(responseObj).encode())

class MyHTTPServer(HTTPServer):
    def __init__(self, context, *args, **kwargs):
        self.context = context
        HTTPServer.__init__(self, *args, **kwargs)

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

        self.httpserver = MyHTTPServer(self, ('', 4001), WebRequestHandler)
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

    @neovim.function("GhostSend")
    def ghostSend(self, args):
        print("in ghostSend", args)
        logging.info(args)
        bufnr = args[0]
        self.nvim.command("echo 'message from command %s'" % args)
        if bufnr in bufferHandlerMap:
            logging.info("sending message to client ")
            wsclient = bufferHandlerMap[bufnr]
            text = "\n".join(self.nvim.buffers[bufnr][:])
            self.nvim.command("echo '%s'" % text)
            wsclient.sendMessage(text)
        else:
            logging.warning("Did not find buffer number %d in map", bufnr)


    def _handleOnMessage(self, text, websocket):
        try:
            tempfileHandle, tempfileName = mkstemp(suffix=".txt", text=True)
            self.nvim.command("ed %s" % tempfileName)
            self.nvim.current.buffer[:] = text.split("\n")
            bufnr = self.nvim.current.buffer.number
            aucmd = ("au TextChanged,TextChangedI <buffer> call"
                     " GhostSend(%d)" % bufnr)
            bufferHandlerMap[bufnr] = websocket
            self.nvim.command(aucmd)
            logging.debug("Set up aucmd: %s", aucmd)
        except Exception as ex:
            logging.error("Caught exception handling message: %s", ex)
            self.nvim.command("echo '%s'" % ex)

    def onMessage(self, text, websocket):
        self.nvim.async_call(self._handleOnMessage, text, websocket)
        # self.nvim.command("echo 'connected direct'")
        return
    # @neovim.autocmd('BufEnter', pattern='*.py', eval='expand("<afile>")',
    #                 sync=True)
    # def autocmd_handler(self, filename):
    #     self.nvim.current.line = (
    #         'Autocmd: Called %s times, file: %s' % (self.calls, filename))

    # @neovim.function('Func')
    # def function_handler(self, args):
    #     self.nvim.current.line = (
    #         'Function: Called %d times, args: %s' % (self.calls, args))

