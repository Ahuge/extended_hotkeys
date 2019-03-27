import nuke
import nukescripts
VIEWER_INPUT_PROXY = "Viewer/Input/"

def viewer_hotkey(number):
    def default_keypress_hotkey():
        if nuke.selectedNodes():
            # Change what our viewer number is connected through and then look through it.
            node = nuke.selectedNodes()[0]
            nukescripts.connect_selected_to_viewer(int(number))
            node.setSelected(True)
        # Change what we are viewing in the viewer to preset
        nuke.activeViewer().activateInput(number)
    return default_keypress_hotkey


def path_to_hotkey(path):
    """
    path_to_hotkey will take a string path in the form of <menu>/<menu>/<item> of any length where
      <menu> is the name of a Nuke menu and <item> is the resulting item you want to return.

    For example:
        ```path_to_hotkey("Nodes/Color/Grade")``` will return the menu item to create a grade.
    There are some special menu items you may not know about. 
      Check out ```nuke.hotkeys()``` to see them all.

    There is some special case work being done for the "Viewer/Input/<number>" hotkeys 
      because they don't seem to be perfectly mapped to the menuItem.

    For reference:
        "Viewer/Input/<number>" will return the action that gets called when you press <number>.
    """
    if path.startswith(VIEWER_INPUT_PROXY):
        index = path.replace(VIEWER_INPUT_PROXY, "")
        return viewer_hotkey(int(index) - 1)
   
    parts = path.split("/")
    item = nuke.menu(parts.pop(0))
    for part in parts:
        item = item.findItem(part)
        if not item:
            return None
    return item


def jump_to_input(number):
    """
    jump_to_input takes an input number and when called will center 
      your viewer on whichever node your viewer is connected to at index <number>

    :param number: The 0 indexed number corresponding to the input you want
    :type number: int
    :return: A lazy function that will evaluate the input at index <index> when called.
    :rettype: types.FunctionType
    """
    def jump_to_handler():
        for node in nuke.selectedNodes():
            node.setSelected(False)

        viewer = nuke.activeViewer()
        viewer.node().input(number).setSelected(True)
        nuke.zoomToFitSelected()

    return jump_to_handler
