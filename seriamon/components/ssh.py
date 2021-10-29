import asyncio
import asyncssh
import queue
import traceback
from PyQt5.QtWidgets import *
from PyQt5 import QtCore
from PyQt5.QtCore import QVariant
from asyncssh.misc import ConnectionLost

from seriamon.component import *
from seriamon.utils import *

class Component(QWidget, SeriaMonPort):

    component_default_name = 'Ssh'
    component_default_num_of_instances = 1

    def __init__(self, compId, sink, instanceId=0):
        super().__init__(compId=compId, sink=sink, instanceId=instanceId)

        self.generation = 0

        self.setLayout(self._setupUart())
        self.thread = _Thread(self)
        self.thread.start()
        self.queue = queue.Queue(1)

    def setupWidget(self):
        return self

    def write(self, data, block=True, timeout=None):
        if isinstance(data, str):
            data = data.encode()
        deadline = Util.deadline(timeout)
        try:
            self.queue.put(data, block=block, timeout=Util.remaining_seconds(deadline))
        except queue.Full as e:
            return False
        self.queue.all_tasks_done.acquire()
        try:
            while self.queue.unfinished_tasks:
                self.queue.all_tasks_done.wait(Util.remaining_seconds(deadline))
                if deadline <= Util.now():
                    break
        finally:
            self.queue.all_tasks_done.release()
        if not self.queue.empty():
            self.queue.get_nowait()
            return False
        return True

    def _setupUart(self):

        self.hostTextEdit = QLineEdit()
        width = self.hostTextEdit.fontMetrics().boundingRect('________').width()
        self.hostTextEdit.setMinimumWidth(width)
        self.userTextEdit = QLineEdit()
        self.userTextEdit.setMinimumWidth(width)
        self.passwordTextEdit = QLineEdit()
        self.passwordTextEdit.setMinimumWidth(width)
        self.commandTextEdit = QLineEdit()
        self.commandTextEdit.setMinimumWidth(width)

        self.initPreferences('{}.{}.{}.'.format(type(self).__module__, type(self).__name__, self.instanceId),
                             [[ str,    'host',     '',           self.hostTextEdit ],
                              [ str,    'user',     '',           self.userTextEdit ],
                              [ str,    'password', '',           self.passwordTextEdit ],
                              [ str,    'command',  '/bin/sh',    self.commandTextEdit ],
                              [ bool,   'connect',  False,         None ]])

        self.connectButton = QPushButton()
        self.connectButton.clicked.connect(self._buttonClicked)

        layout = QHBoxLayout()
        layout.addWidget(QLabel('host:'))
        layout.addWidget(self.hostTextEdit)
        layout.addWidget(QLabel('user:'))
        layout.addWidget(self.userTextEdit)
        layout.addWidget(QLabel('password:'))
        layout.addWidget(self.passwordTextEdit)

        grid = QGridLayout()
        grid.addLayout(layout, 1, 0, 1, 4)
        grid.addWidget(QLabel('command:'), 2, 0)
        grid.addWidget(self.commandTextEdit, 2, 1)
        grid.addWidget(self.connectButton, 4, 4)

        return grid

    def stopLog(self):
        self.run = False
        self.updatePreferences()

    def shutdown(self):
        if self.thread:
            self.log(self.LOG_DEBUG, 'Stop internal thread...')
            self.thread.stayAlive = False
            self.thread.task.cancel()
            self.thread.wait()

    def updatePreferences(self):
        super().updatePreferences()
        self.hostTextEdit.setEnabled(not self.connect)
        self.userTextEdit.setEnabled(not self.connect)
        self.passwordTextEdit.setEnabled(not self.connect)
        self.commandTextEdit.setEnabled(not self.connect)
        self.connectButton.setText('Disconnect' if self.connect else 'Connect')
        self.generation += 1

    def _buttonClicked(self):
        self.reflectFromUi()
        self.connect = not self.connect
        self.updatePreferences()

class _Thread(QtCore.QThread):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.stayAlive = True
        self.generation = parent.generation
        self.conn = None
        self.proc = None
        self.delay = None

    def run(self):
        self.thread_context = Util.thread_context(f'{self.parent.getComponentName()}')
        asyncio.run(self.async_run())

    async def async_run(self):
        #self.task = asyncio.ensure_future(self.async_run())
        self.task = asyncio.ensure_future(asyncio.gather(
            self.reconnect(), self.send(),
            self.receive('stdout'), self.receive('stderr')))
        try:
            await self.task
        except asyncio.CancelledError as e:
            pass

    async def reconnect(self):
        parent = self.parent
        self.error = False
        prevStatus = parent.STATUS_NONE

        while self.stayAlive:
            """
                update status indicator
            """
            if parent.connect:
                if self.conn and not self.error:
                    status = parent.STATUS_ACTIVE
                else:
                    status = parent.STATUS_WAITING
            else:
                status = parent.STATUS_DEACTIVE
            if prevStatus != status:
                parent.setStatus(status)
                prevStatus = status

            """try to (re)connect to the host if
                 settings has been changed
                 connect / disconnect button was clicked
                 errors were reported on the connection
            """
            if self.generation != parent.generation or self.error:
                if self.conn:
                    self.conn.close()
                    parent.sink.putLog('---- close {} -----\n'.
                                       format(parent.host), parent.compId)
                    self.conn = None
                if self.delay:
                    delay = self.delay
                    self.delay = None
                    await asyncio.sleep(delay)
                if parent.connect:
                    try:
                        self.conn = await asyncssh.connect(parent.host, port=22,
                                username=parent.user, password=parent.password,
                                client_keys=None,  known_hosts=None)
                        self.proc = await self.conn.create_process(parent.command)
                        self.error = False
                    except Exception as e:
                        known_errors = { ('OSError', 22) }
                        if (type(e).__name__, e.args[0]) in known_errors:
                            parent.log(parent.LOG_DEBUG, e)
                        else:
                            parent.sink.putLog('---- fail to connect to {} -----\n'.
                                               format(parent.host), parent.compId)
                            parent.log(parent.LOG_INFO, f'Exception: {type(e).__name__} {e.args}')
                            parent.log(parent.LOG_ERROR, e)
                            self.error = True
                        await asyncio.sleep(1.0)
                        continue
                    parent.sink.putLog('---- connect to {} -----\n'.
                                       format(parent.host), parent.compId)
                self.types = None
                self.generation = parent.generation
            else:
                await asyncio.sleep(1.0)

    async def send(self):
        parent = self.parent

        while self.stayAlive:
            """
               send command
            """
            if self.conn:
                try:
                    if not parent.queue.empty():
                        try:
                            value = parent.queue.get_nowait()
                            if isinstance(value, bytes):
                                value = value.decode()
                            self.proc.stdin.write(value)
                            parent.queue.task_done()
                        except queue.Empty as e:
                            pass
                    else:
                        await asyncio.sleep(1.0)
                except Exception as e:
                    if isinstance(e, ConnectionLost) or isinstance(e, ConnectionAbortedError):
                        parent.log(parent.LOG_DEBUG, e)
                        self.delay = 1.0
                    else:
                        traceback.print_exc()
                        parent.log(parent.LOG_ERROR, e)
                    self.error = True
                    await asyncio.sleep(1.0)
                    continue
            else:
                await asyncio.sleep(1.0)

    async def receive(self, output):
        parent = self.parent

        while self.stayAlive:
            """
               read serial port if it is open
            """
            if self.conn:
                try:
                    if output == 'stdout':
                        value = await self.proc.stdout.read(n=1)
                    else:
                        value = await self.proc.stderr.read(n=1)
                    if len(value) == 0:
                        # timeout
                        await asyncio.sleep(0.1)
                        continue
                    if not parent.connect:
                        # connection was closed
                        await asyncio.sleep(1.0)
                        continue
                    parent.sink.putLog(value, parent.compId, self.types)
                    self.error = False
                except Exception as e:
                    if isinstance(e, ConnectionLost) or isinstance(e, ConnectionAbortedError):
                        parent.log(parent.LOG_DEBUG, e)
                        self.delay = 1.0
                    else:
                        traceback.print_exc()
                        parent.log(parent.LOG_ERROR, e)
                    self.error = True
                    await asyncio.sleep(1.0)
                    continue
            else:
                await asyncio.sleep(1.0)
