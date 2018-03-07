import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler
from random import randint
from threading import Thread
from tempfile import mkstemp
import logging
import json
import os
from SimpleWebSocketServer import SimpleWebSocketServer, WebSocket
import neovim
from neovim.api.nvim import NvimError
from slugify import slugify

buffer_handler_map = {}
websocket_servers = []
logger = logging.getLogger()
NVIM_GHOSTPY_LOGLEVEL = 'NVIM_GHOSTPY_LOG_LEVEL'
loglevelstr = os.environ.get(NVIM_GHOSTPY_LOGLEVEL, "WARNING")
logger.setLevel(logging.getLevelName(loglevelstr))
PYWINAUTO = False
if os.name == "nt":
    try:
        from pywinauto.application import Application, ProcessNotFoundError
        PYWINAUTO = True
        logger.info("pywinauto imported successfully.")
    except ImportError as ie:
        logger.info("Pywinauto module not available.")


class GhostWebSocketHandler(WebSocket):

    def handleMessage(self):
        req = json.loads(self.data)
        logger.info("recd on websocket: %s message: %s",
                    self.address, self.data)
        self.server.context.on_message(req, self)

    def handleConnected(self):
        logger.debug("Websocket connected %s", self.address)

    def handleClose(self):
        logger.debug("Websocket closed event %s ", self.address)
        self.server.context.on_websocket_close(self)


class MyWebSocketServer(SimpleWebSocketServer):

    def __init__(self, context, *args, **kwargs):
        self.context = context
        SimpleWebSocketServer.__init__(self, *args, **kwargs)


def startWebSocketSvr(context, port):
    websocket_server = MyWebSocketServer(context, '', port,
                                         GhostWebSocketHandler)
    ws_thread = Thread(target=websocket_server.serveforever, daemon=True)
    ws_thread.start()
    websocket_servers.append(websocket_server)


class WebRequestHandler(BaseHTTPRequestHandler):

    def _set_headers(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

    def do_GET(self):
        self._set_headers()
        port = randint(60000, 65535)
        response_obj = {"ProtocolVersion": 1}
        response_obj["WebSocketPort"] = port
        startWebSocketSvr(self.server.context, port)
        self.wfile.write(json.dumps(response_obj).encode())


class MyHTTPServer(HTTPServer):

    def __init__(self, context, *args, **kwargs):
        self.context = context
        HTTPServer.__init__(self, *args, **kwargs)


@neovim.plugin
class Ghost(object):

    def __init__(self, vim):
        self.nvim = vim
        self.server_started = False
        self.port = 4001
        self.winapp = None
        self.linux_window_id = None

    @neovim.command('GhostStart', range='', nargs='0')
    def server_start(self, args, range):
        if self.server_started:
            self.nvim.command("echo 'Ghost server already running on port %d'"
                              % self.port)
            logger.info("server already running on port %d", self.port)
            return

        if self.nvim.funcs.exists("g:ghost_port") == 1:
            self.port = self.nvim.api.get_var("ghost_port")
        else:
            self.nvim.api.set_var("ghost_port", self.port)

        self.httpserver = MyHTTPServer(self, ('', self.port),
                                       WebRequestHandler)
        http_server_thread = Thread(target=self.httpserver.serve_forever,
                                    daemon=True)
        http_server_thread.start()
        self.server_started = True
        logger.info("server started")
        self.nvim.command("echom 'Ghost server started on port %d'"
                          % self.port)
        if PYWINAUTO:
            # for windows
            try:
                app = Application().connect(path="nvim-qt.exe", timeout=0.1)
                self.winapp = app
                logger.debug("Connected to nvim-qt with process id: %s",
                             self.winapp.process.real)
            except ProcessNotFoundError as pne:
                logger.warning("No process called nvim-qt found: %s", pne)
        elif self.nvim.funcs.exists("g:ghost_nvim_window_id") == 1:
            # for linux
            self.linux_window_id = self.nvim.api.get_var(
                "ghost_nvim_window_id").strip()

    @neovim.command('GhostStop', range='', nargs='0', sync=True)
    def server_stop(self, args, range):
        if not self.server_started:
            self.nvim.command("echo 'Server not running'")
            return
        self.httpserver.shutdown()
        self.httpserver.socket.close()
        for server in websocket_servers:
            logger.info("Shutting down websocket server on port: %d",
                        server.serversocket.getsockname()[1])
            server.close()
        logger.info("Shutdown websockets and httpd")
        self.nvim.command("echom 'Ghost server stopped'")
        self.server_started = False

    @neovim.function("GhostNotify")
    def ghost_notify(self, args):
        logger.info(args)
        event, bufnr = args
        if bufnr not in buffer_handler_map:
            return
        wsclient, req = buffer_handler_map[bufnr]
        logger.debug('event recd: %s, buffer: %d', event, bufnr)
        if event == "text_changed":
            logger.info("sending message to client ")
            text = "\n".join(self.nvim.buffers[bufnr][:])
            req["text"] = text
            # self.nvim.command("echo '%s'" % text)
            wsclient.sendMessage(json.dumps(req))
        elif event == "closed":
            logger.info(("Calling _handleOnWebSocketClose"
                         " in response to buffer"
                         " %d closure in nvim", bufnr))
            self._handle_web_socket_close(wsclient)

    def _handle_on_message(self, req, websocket):
        try:
            if websocket in buffer_handler_map:
                # existing buffer
                bufnr, fh = buffer_handler_map[websocket]
                # delete textchanged autocmds otherwise we'll get a loop
                logger.info("delete buffer changed autocmd")
                self.nvim.command("au! TextChanged,TextChangedI <buffer=%d>" %
                                  bufnr)
                self.nvim.buffers[bufnr][:] = req["text"].split("\n")
            else:
                # new client
                prefix = "ghost-" + req["url"] + "-" + \
                    slugify(req["title"])[:50]
                temp_file_handle, temp_file_name = mkstemp(prefix=prefix,
                                                           suffix=".txt",
                                                           text=True)
                self.nvim.command("ed %s" % temp_file_name)
                self.nvim.current.buffer[:] = req["text"].split("\n")
                bufnr = self.nvim.current.buffer.number
                delete_cmd = ("au BufDelete <buffer> call"
                              " GhostNotify('closed', %d)" % bufnr)
                buffer_handler_map[bufnr] = [websocket, req]
                buffer_handler_map[websocket] = [bufnr, temp_file_handle]
                self.nvim.command(delete_cmd)
                logger.debug("Set up aucmd: %s", delete_cmd)
                self._raise_window()
            change_cmd = ("au TextChanged,TextChangedI <buffer> call"
                          " GhostNotify('text_changed', %d)" % bufnr)
            self.nvim.command(change_cmd)
            logger.debug("Set up aucmd: %s", change_cmd)
        except Exception as ex:
            logger.error("Caught exception handling message: %s", ex)
            self.nvim.command("echo '%s'" % ex)

    def _raise_window(self):
        if self.linux_window_id:
            subprocess.call(["xdotool", "windowactivate", self.linux_window_id])
            logger.debug("activated window: %s", self.linux_window_id)
        elif self.winapp:
            logger.debug("WINDOWS: trying to raise window")
            # dragons - this is the only thing that works.
            try:
                self.winapp.windows()[0].set_focus()
                self.winapp.windows()[0].ShowInTaskbar()
            except Exception as e:
                logger.warning("Error during _raise_window, %s", e)

    def on_message(self, req, websocket):
        self.nvim.async_call(self._handle_on_message, req, websocket)
        # self.nvim.command("echo 'connected direct'")
        return

    def _handle_web_socket_close(self, websocket):
        logger.debug("Cleaning up on websocket close")
        if websocket not in buffer_handler_map:
            logger.warning("websocket closed but no matching buffer found")
            return

        bufnr, fh = buffer_handler_map[websocket]
        buf_file = self.nvim.buffers[bufnr].name
        try:
            self.nvim.command("bdelete! %d" % bufnr)
        except NvimError as nve:
            logger.error("Error while deleting buffer %s", nve)

        try:
            os.close(fh)
            os.remove(buf_file)
            logger.debug("Deleted file %s and removed buffer %d", buf_file,
                         bufnr)
        except OSError as ose:
            logger.error("Error while closing & deleting file %s", ose)

        buffer_handler_map.pop(bufnr, None)
        buffer_handler_map.pop(websocket, None)
        websocket.close()
        logger.debug("Websocket closed")

    def on_websocket_close(self, websocket):
        self.nvim.async_call(self._handle_web_socket_close, websocket)
