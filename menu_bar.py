from Cocoa import ( # type: ignore
    NSApplication, NSStatusBar, NSVariableStatusItemLength, # pyright: ignore[reportAttributeAccessIssue]
    NSObject, NSMenu, NSMenuItem, NSUserNotification, NSUserNotificationCenter, NSImage, NSImageSymbolConfiguration, # pyright: ignore[reportAttributeAccessIssue]
    NSControlStateValueOn, NSControlStateValueOff
)
import objc # type: ignore
from objc import python_method
from whisper import load_model # type: ignore
from simple_ai import SimpleAi
from nova import Nova
import yaml # type: ignore
import sys
import ollama
from random import choice
import os
import functools
import logging
from typing import Callable
import inspect
import threading
import tempfile
import logging
import multiprocessing
from datetime import datetime, timedelta

os.environ["PATH"] += os.pathsep + "/opt/homebrew/bin"
logging.info(f"Path: {os.environ["PATH"]}")

# Event masks for mouse clicks
NSEventMaskLeftMouseUp = 1 << 2
NSEventMaskRightMouseUp = 1 << 3

def read_settings():
    if getattr(sys, 'frozen', False):
        # Running in PyInstaller bundle
        base_dir = sys._MEIPASS # pyright: ignore[reportAttributeAccessIssue]
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    settings_path = os.path.join(base_dir, 'settings.yml')
    with open(settings_path, 'r') as f:
        return list(yaml.safe_load_all(f))[0]

temp_file = os.path.join(tempfile.gettempdir(), "said.mp3")


@python_method
def showNotification(title, subtitle, message):
    """Show a macOS native notification."""
    notification = NSUserNotification.alloc().init()
    notification.setTitle_(title)
    notification.setSubtitle_(subtitle)
    notification.setInformativeText_(message)
    NSUserNotificationCenter.defaultUserNotificationCenter().deliverNotification_(notification)

def log_exceptions(func: Callable):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logging.error("Exception in %s: %s", func.__name__, e, exc_info=True)
            showNotification("Error", f"{type(e)}", str(e))
            return None
    return wrapper


class AppDelegate(NSObject):
    status_item = None    

    @log_exceptions
    def init(self) -> "AppDelgate":
        self = objc.super(AppDelegate, self).init() # pyright: ignore[reportAttributeAccessIssue]
        self.settings = read_settings()
        self.nova_prime = self.settings["prime-mode"]
        self.model = self.settings["default-model"]
        self.listening = False
        self.processing = False
        self.last_request: datetime|None = None
        return self


    def set_nova_mode(self, prime: bool, model: str) -> None:
        if prime:
            logging.info("Nova Prime engaged")
            self.nova_settings = self.settings["nova-prime-defaults"]
            self.nova_prime = True

            self.menu_item_prime.setState_(NSControlStateValueOn)
            self.menu_item_prime.setEnabled_(False)
            self.menu_item_core.setState_(NSControlStateValueOff)
            self.menu_item_core.setEnabled_(True)

        else:
            logging.info("Nova Core engaged")
            self.nova_settings = self.settings["nova-core-defaults"]
            self.nova_prime = False

            self.menu_item_prime.setState_(NSControlStateValueOff)
            self.menu_item_prime.setEnabled_(True)
            self.menu_item_core.setState_(NSControlStateValueOn)
            self.menu_item_core.setEnabled_(False)


        self.nova = Nova(SimpleAi(model, self.nova_settings["system-prompt"]), self.nova_settings["voice"])
        logging.info(f"Configuring Nova: model={model}; prime={self.nova_prime}; voice={self.nova_settings["voice"]}")


    def switchMode_(self, sender):
        self.set_nova_mode(sender.tag(), self.model)


    @objc.IBAction
    def selectModel_(self, sender):
        self.model = sender.title()
        logging.info(f"sender={sender}; sender.title()={sender.title()}")
        for i in range(self.modelMenu.numberOfItems()):
            logging.info(f"i={i}   it={self.modelMenu.itemAtIndex_(i)}")
            it = self.modelMenu.itemAtIndex_(i)
            it.setState_(NSControlStateValueOn if it.title() == self.model else NSControlStateValueOff)
        self.set_nova_mode(self.set_nova_mode, self.model)


    @log_exceptions
    def applicationDidFinishLaunching_(self, notification):
        # Don't create a duplicate menu bar icon
        if self.status_item:
            return

        stack = " → ".join(f"{f.function}:{f.lineno}" for f in inspect.stack()[1:5])
        logging.info(f"Status item created: pid={os.getpid()} | thread={threading.current_thread().name} | stack={stack}")

        # Create the status bar item
        self.status_item = NSStatusBar.systemStatusBar().statusItemWithLength_(NSVariableStatusItemLength)
        self.set_icon("atom")

        # Enable left & right clicks
        button = self.status_item.button()
        button.setTarget_(self)
        button.setAction_("statusItemClicked:")
        button.sendActionOn_(NSEventMaskLeftMouseUp | NSEventMaskRightMouseUp)

        # Right-click menu
        self.menu = NSMenu.alloc().init()
        self.menu.setAutoenablesItems_(False)

        # # Nova Prime/Core options
        self.menu_item_prime = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Nova Prime", "switchMode:", "")
        self.menu_item_prime.setTarget_(self)
        self.menu_item_prime.setTag_(True)
        self.menu.addItem_(self.menu_item_prime)

        self.menu_item_core = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Nova Core", "switchMode:", "")
        self.menu_item_core.setTarget_(self)
        self.menu_item_core.setTag_(False)
        self.menu.addItem_(self.menu_item_core)

        # Models submenu
        self.modelMenu = NSMenu.alloc().init()
        modelRoot = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Models", None, "")
        modelRoot.setSubmenu_(self.modelMenu)
        self.menu.addItem_(modelRoot)

        # Query installed models
        resp = ollama.list()  # {'models': [{'name': 'llama3:8b', ...}, ...]}
        names = [m.get('model') for m in resp.get('models', [])]

        if not names:
            placeholder = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("No models found", None, "")
            placeholder.setEnabled_(False)
            self.modelMenu.addItem_(placeholder)
        else:
            if not getattr(self, "currentModel", None) or self.currentModel not in names:
                self.currentModel = names[0]
            for name in names:
                item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(name, "selectModel:", "")
                item.setTarget_(self)
                item.setRepresentedObject_(name)
                item.setState_(NSControlStateValueOn if name == self.currentModel else NSControlStateValueOff)
                self.modelMenu.addItem_(item)

        # Reset/Quit
        self.menu.addItem_(
            NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Reset Model", "resetModel:", "")
        )
        self.menu.addItem_(
            NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Quit", "terminate:", "")
        )

        self.set_nova_mode(self.nova_prime, self.model)


    def set_icon(self, name):
        config = NSImageSymbolConfiguration.configurationWithPointSize_weight_scale_(16, 0, 1)  
        icon = NSImage.imageWithSystemSymbolName_accessibilityDescription_(name, None)
        icon = icon.imageWithSymbolConfiguration_(config)
        
        self.status_item.button().setImage_(icon) # pyright: ignore[reportOptionalMemberAccess]

    @log_exceptions
    def statusItemClicked_(self, sender):
        """Handle left vs right click on status bar icon"""
        event = NSApplication.sharedApplication().currentEvent()
        logging.info(msg=f"menu bar clicked: self.listening={self.listening}")
        if event.type() == 3:  # Right-click
            if self.listening:
                self.nova.stop_listening()
                self.listening = False
                self.set_icon("atom")
            elif self.processing:
                self.stopped_processing()
            else:
                self.status_item.popUpStatusItemMenu_(self.menu) # pyright: ignore[reportOptionalMemberAccess]
        elif event.type() == 2:  # Left-click
            if self.processing:
                return
            if self.listening:
                self.nova.stop_listening()
                self.nova.process(self.nova_prime, temp_file, self.stopped_processing)
                self.processing = True
                self.set_icon("cpu")
            else:
                if self.last_request and datetime.now() - self.last_request > timedelta(minutes=30):
                    self.set_nova_mode(self.nova_prime)
                self.nova.start(choice(self.nova_settings["human-prompts"]), temp_file)
                self.set_icon("microphone")
                self.last_request = datetime.now()
            self.listening = not self.listening
            logging.info(f"changing self.listening to {self.listening}")


    def resetModel_(self, sender):
        """Reset the AI model and show a macOS notification"""
        self.ai = SimpleAi("llama3.1:8b", self.nova_settings["system-prompt"])
        self.showNotification(
            title="Nova Model Reset",
            subtitle="Conversation history cleared",
            message="Nova has been reset and is ready for a fresh start."
        )
    

    def stopped_processing(self):
        self.nova.stop_processing()
        self.processing = False
        self.set_icon("atom")


def run():
    app = NSApplication.sharedApplication()
    delegate = AppDelegate.alloc().init()
    app.setDelegate_(delegate)
    app.run()

log_dir = os.path.expanduser("~/Library/Logs/Nova")
os.makedirs(log_dir, exist_ok=True)
log_file_name = os.path.join(log_dir, "nova.log")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file_name),
        logging.StreamHandler()  # Also log to console for development/debugging
    ],
    force=True
)

# Example usage
logging.info("Application started.")

if __name__ == "__main__":
    # Guard against duplicating the menu bar application
    multiprocessing.freeze_support()
    if multiprocessing.current_process().name == "MainProcess":
        try:
            run()
        except Exception as e:
            logging.error(e)