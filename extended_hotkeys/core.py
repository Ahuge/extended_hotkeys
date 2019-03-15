import sys
import types
import uuid

try:
    from Qt import QtCore
except ImportError:
    try:
        from PySide2 import QtCore
    except ImportError:
        try:
            from PySide import QtCore
        except ImportError:
            try:
                from PyQt5 import QtCore
            except ImportError:
                try:
                    from PyQt4 import QtCore
                except ImportError:
                    raise ImportError(
                        "Could not import required Qt libraries. Modules tried: [Qt.py, PySide2, PySide, PyQt5, PyQt4]"
                    )

__all__ = ["addExtendedCommand"]


TIMER_FINISHED = 1
TIMER_RUNNING = 0
TIMER_UNSET = -1


def __anonymous(text):
    py2_src = """def __():
        exec \"{text}\"""".format(text=text)

    py3_src = """def __():
    exec(\"{text}\")""".format(text=text)

    if sys.version_info[0] > 2:
        return eval(py3_src)
    return eval(py2_src)


def __sanitize_commands(command_list):
    sanitized = []
    if not hasattr(command_list, "__iter__"):
        # Not iterable, we can assume it's not a list.
        command_list = [command_list]

    for command in command_list:
        if isinstance(command, types.FunctionType):
            sanitized.append(command)
        elif isinstance(command, basestring):
            sanitized.append(__anonymous(command))
    return sanitized


def __clear_list(list_obj):
    for _ in list_obj[:]:
        list_obj.remove(_)


def __bound_timeout_handler(key, callback_stack, callback_list):

    @QtCore.Slot()
    def handle_timeout():
        """
        The timer has run out here.
        We need to reset the state and execute the last satisfied callback.
        """
        if __get_global_value(key) == TIMER_UNSET:
            # Treat unset as IGNORE.
            return

        __set_global_value(key, TIMER_FINISHED)
        # If we have a callback we can run, run it and reset the stack.
        if len(callback_stack):
            callback = callback_stack.pop(-1)

            # Clear the callback stack
            __clear_list(callback_stack)

            # Call the latest callback.
            __set_global_value(key, TIMER_UNSET)
            callback()
        else:
            # There is no callback that we can run!
            __set_global_value(key, TIMER_UNSET)
            print(
                "Expected a callback to call when the timer finished.\nOriginal callback list was %s" % callback_list
            )

    return handle_timeout


def __set_global_value(key, value):
    globals()[key] = value


def __get_global_value(key):
    return globals().get(key)


def make_multiple_hotkey_factory(callback_list, timeout=1000, fast_exit=True):
    key = uuid.uuid4()
    timer = QtCore.QTimer(QtCore.QCoreApplication.instance())
    callback_stack = []

    def multiple_hotkey_manager():
        if len(callback_list) == 1:
            # No need for a timer, we can just call the only one.
            callback_list[0]()
            __clear_list(callback_stack)
        else:
            # Start our callback logic.
            if __get_global_value(key) == TIMER_UNSET:
                # We haven't started a timer. This must be our first keypress.
                __set_global_value(key, TIMER_RUNNING)
                timer.singleShot(timeout, __bound_timeout_handler(key, callback_stack, callback_list))
            elif __get_global_value(key) == TIMER_RUNNING:
                # We need to add our latest callback to the stack
                if len(callback_list) > len(callback_stack):
                    callback_stack.append(callback_list[len(callback_stack)])
                elif len(callback_list) == len(callback_stack) and fast_exit is True:
                    # We are at the last callback and we have been asked to fast_exit. We should call our callback now.
                    __set_global_value(key, TIMER_UNSET)
                    __clear_list(callback_stack)
                    callback_list[-1]()
                else:
                    # We may get here if we press the hotkey too much and we don't want to fast_exit.
                    print(
                        "Hotkey pressed %d times but only %d callbacks registered for the hotkey."
                        % (len(callback_stack), len(callback_list))
                    )
            elif __get_global_value(key) == TIMER_FINISHED:
                # Timer is set to FINISHED. We should not get here because the timer should set itself back to UNSET
                print(
                    "An error has occured in \"extended_hotkeys\". Timer state was set to FINISHED. Did an error occur?"
                )
            else:
                # Timer is set to an unknown value! Set it to UNSET and hope it doesn't get changed again.
                __set_global_value(key, TIMER_UNSET)
                __clear_list(callback_stack)

    return multiple_hotkey_manager


def addExtendedCommand(menu, name, commands, shortcut=None, icon=None, tooltip=None, index=None, readonly=None, shortcutContext=None, timeout=1000):
    """
addExtendedCommand(...)
    self.addCommand(name, command, shortcut, icon, tooltip, index, readonly) -> The menu/toolbar item that was added to hold the command.
    Add a new command to this menu/toolbar. Note that when invoked, the command is automatically enclosed in an undo group, so that undo/redo functionality works. Optional arguments can be specified by name.
    Note that if the command argument is not specified, then the command will be auto-created as a "nuke.createNode()" using the name argument as the node to create.

    Example:
    menubar = nuke.menu('Nuke')
    fileMenu = menubar.findItem('File')
    fileMenu.addCommand('NewCommand', 'print 10', shortcut='t')

    @param name: The name for the menu/toolbar item. The name may contain submenu names delimited by '/' or '', and submenus are created as needed.
    @param commands: Optional. The commands to add to the menu/toolbar. This can be a string to evaluate or a Python Callable (function, method, etc) to run or a list of either.
    @param shortcut: Optional. The keyboard shortcut for the command, such as 'R', 'F5' or 'Ctrl-H'. Note that this overrides pre-existing other uses for the shortcut.
    @param icon: Optional. An icon for the command. This should be a path to an icon in the nuke.pluginPath() directory. If the icon is not specified, Nuke will automatically try to find an icon with the name argument and .png appended to it.
    @param tooltip: Optional. The tooltip text, displayed on mouseover for toolbar buttons.
    @param index: Optional. The position to insert the new item in, in the menu/toolbar. This defaults to last in the menu/toolbar.
    @param readonly: Optional. True/False for whether the item should be available when the menu is invoked in a read-only context.
    @param shortcutContext: Optional. Sets the shortcut context (0==Window, 1=Application, 2=DAG).
    @param timeout: Optional. Only comes active if you pass multiple commands. Sets the timeout for our internal timer on your new hotkey. It's the total time between your first click to your last click to trigger all your callbacks for the hotkey.
    @return: The menu/toolbar item that was added to hold the command.
    """
    sanitized_commands = __sanitize_commands(commands)
    if len(sanitized_commands) == 1:
        output_command = sanitized_commands[0]
    else:
        output_command = make_multiple_hotkey_factory(sanitized_commands, timeout=timeout)
    return menu.addCommand(
        name,
        output_command,
        shortcut=shortcut,
        icon=icon,
        tooltip=tooltip,
        index=index,
        readonly=readonly,
        shortcutContext=shortcutContext
    )

