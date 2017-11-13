from http.server import HTTPServer, BaseHTTPRequestHandler
from SimpleWebSocketServer import SimpleWebSocketServer, WebSocket
from random import randint
from threading import Thread
from tempfile import mkstemp
import logging
import json
import neovim
from neovim.api.nvim import NvimError
import os
bufferHandlerMap = {}
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


class GhostWebSocketHandler(WebSocket):
    def handleMessage(self):
        logger.info("recd websocket message")
        self.server.context.onMessage(json.loads(self.data), self)

    def handleConnected(self):
        print(self.address, 'connected')

    def handleClose(self):
        print(self.address, 'closed')
        self.server.context.onWebSocketClose(self)


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
        self.serverStarted = False

    @neovim.command('GhostStart', range='', nargs='0', sync=True)
    def server_start(self, args, range):
        if self.serverStarted:
            self.nvim.command("echo 'Ghost server already running'")
            logger.info("server already running")
            return

        self.httpserver = MyHTTPServer(self, ('', 4001), WebRequestHandler)
        httpserverThread = Thread(target=self.httpserver.serve_forever, daemon=True)
        httpserverThread.start()
        self.serverStarted = True
        logger.info("server started")
        self.nvim.command("echo 'Ghost server started'")

    @neovim.command('GhostStop', range='', nargs='0', sync=True)
    def server_stop(self, args, range):
        if not self.serverStarted:
            self.nvim.command("echo 'Server not running'")
            return
        self.httpserver.shutdown()
        self.nvim.command("echo 'Ghost server stopped'")

    @neovim.function("GhostNotify")
    def ghostSend(self, args):
        print("in ghostSend", args)
        logger.info(args)
        event, bufnr = args
        if bufnr not in bufferHandlerMap:
            return
        wsclient, req = bufferHandlerMap[bufnr]
        self.nvim.command("echo 'event recd command %s, %s'" % (event, bufnr))
        if event == "text_changed":
            logger.info("sending message to client ")
            text = "\n".join(self.nvim.buffers[bufnr][:])
            req["text"] = text
            # self.nvim.command("echo '%s'" % text)
            wsclient.sendMessage(json.dumps(req))
        elif event == "closed":
            logger.info(("Calling _handleOnWebSocketClose in response to buffer"
                        " %d closure in nvim" % bufnr))
            self._handleOnWebSocketClose(wsclient)

    def _handleOnMessage(self, req, websocket):
        try:
            if websocket in bufferHandlerMap:
                # existing buffer
                bufnr, fh = bufferHandlerMap[websocket]
                logger.info("delete buffer changed autocmd")
                self.nvim.command("au! TextChanged,TextChangedI <buffer=%d>" %
                                  bufnr)
                self.nvim.buffers[bufnr][:] = req["text"].split("\n")
            else:
                # new client
                tempfileHandle, tempfileName = mkstemp(suffix=".txt", text=True)
                self.nvim.command("ed %s" % tempfileName)
                self.nvim.current.buffer[:] = req["text"].split("\n")
                bufnr = self.nvim.current.buffer.number
                deleteCmd = ("au BufDelete <buffer> call"
                             " GhostNotify('closed', %d)" % bufnr)
                bufferHandlerMap[bufnr] = [websocket, req]
                bufferHandlerMap[websocket] = [bufnr, tempfileHandle]
                self.nvim.command(deleteCmd)
                logger.debug("Set up aucmd: %s", deleteCmd)

            changeCmd = ("au TextChanged,TextChangedI <buffer> call"
                         " GhostNotify('text_changed', %d)" % bufnr)
            self.nvim.command(changeCmd)
            logger.debug("Set up aucmd: %s", changeCmd)
        except Exception as ex:
            logger.error("Caught exception handling message: %s", ex)
            self.nvim.command("echo '%s'" % ex)

    def onMessage(self, req, websocket):
        self.nvim.async_call(self._handleOnMessage, req, websocket)
        # self.nvim.command("echo 'connected direct'")
        return

    def _handleOnWebSocketClose(self, websocket):
        logger.debug("Cleaning up before websocket close")
        if websocket not in bufferHandlerMap:
            logger.warn("websocket closed but no matching buffer found")
            return

        bufnr, fh = bufferHandlerMap[websocket]
        bufFilename = self.nvim.buffers[bufnr].name
        try:
            self.nvim.command("bdelete! %d" % bufnr)
        except NvimError as nve:
            logger.error("Error while deleting buffer %s", nve)

        try:
            os.close(fh)
            os.remove(bufFilename)
            logger.debug("Deleted file %s and removed buffer %d", bufFilename,
                         bufnr)
        except OSError as ose:
            logger.error("Error while closing & deleting file %s", ose)

        bufferHandlerMap.pop(bufnr, None)
        bufferHandlerMap.pop(websocket, None)
        websocket.close()
        logger.debug("Websocket closed")

    def onWebSocketClose(self, websocket):
        self.nvim.async_call(self._handleOnWebSocketClose, websocket)

