from Cocoa import (
    NSApplication, NSStatusBar, NSVariableStatusItemLength, # pyright: ignore[reportAttributeAccessIssue]
    NSObject, NSMenu, NSMenuItem, NSUserNotification, NSUserNotificationCenter, NSImage, NSImageSymbolConfiguration # pyright: ignore[reportAttributeAccessIssue]
)
import objc
from objc import python_method
from whisper import load_model
from simple_ai import SimpleAi
from nova import Nova
import yaml
import sys
from random import choice
import os
import functools
import logging
from typing import Callable

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


import tempfile
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
    def init(self):
        self = objc.super(AppDelegate, self).init() # pyright: ignore[reportAttributeAccessIssue]
        if self is None:
            return None

        self.settings = read_settings()

        # Initialize AI models
        self.nova_prime = True
        self.nova = Nova(SimpleAi("llama3.1:8b", self.settings["system-prompt"]))
        self.listening = False

        return self

    def applicationDidFinishLaunching_(self, notification):
        # Create the status bar item
        self.status_item = NSStatusBar.systemStatusBar().statusItemWithLength_(NSVariableStatusItemLength)

        # Pick an SF Symbol (e.g., "triangle" looks like an A without bar)
        # self.setIcon("atom")
        config = NSImageSymbolConfiguration.configurationWithPointSize_weight_scale_(16, 0, 1)  
        icon = NSImage.imageWithSystemSymbolName_accessibilityDescription_("atom", None)
        icon = icon.imageWithSymbolConfiguration_(config)

        self.status_item.button().setImage_(icon)


        # Enable left & right clicks
        button = self.status_item.button()
        button.setTarget_(self)
        button.setAction_("statusItemClicked:")
        button.sendActionOn_(NSEventMaskLeftMouseUp | NSEventMaskRightMouseUp)

        # Right-click menu
        self.menu = NSMenu.alloc().init()
        reset_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Reset Model", "resetModel:", "")
        quit_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Quit", "terminate:", "")
        self.menu.addItem_(reset_item)
        self.menu.addItem_(quit_item)

    @log_exceptions
    def statusItemClicked_(self, sender):
        """Handle left vs right click on status bar icon"""
        event = NSApplication.sharedApplication().currentEvent()
        logging.info(msg=f"menu bar clicked: self.listening={self.listening}")
        if event.type() == 3:  # Right-click
            # print("right", event.type())
            if self.listening:
                self.nova.stop()
                self.listening = False
            else:
                self.status_item.popUpStatusItemMenu_(self.menu)
        elif event.type() == 2:  # Left-click
            # print("left", event.type())
            if self.listening:
                self.nova.stop()
                self.nova.process(self.nova_prime, temp_file)
            else:
                self.nova.start(choice(self.settings["human-prompts"]), temp_file)
            self.listening = not self.listening
            logging.info(f"changing self.listening to {self.listening}")

    def resetModel_(self, sender):
        """Reset the AI model and show a macOS notification"""
        self.ai = SimpleAi("llama3.1:8b", self.settings["system-prompt"])
        self.showNotification(
            title="Nova Model Reset",
            subtitle="Conversation history cleared",
            message="Nova has been reset and is ready for a fresh start."
        )


def run():
    app = NSApplication.sharedApplication()
    delegate = AppDelegate.alloc().init()
    app.setDelegate_(delegate)
    app.run()

import logging
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
    ]
)

# Example usage
logging.info("Application started.")

if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        logging.error(e)