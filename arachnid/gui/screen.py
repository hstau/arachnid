''' Graphical user interface for screening images

.. Created on Jul 17, 2013
.. codeauthor:: Robert Langlois <rl2528@columbia.edu>
'''
from ..core.gui.util import qtapp
from ..core.app import tracing
import logging, sys

_logger = logging.getLogger(__name__)
_logger.setLevel(logging.DEBUG)

def main():
    # Create GUI and display
    
    tracing.configure_logging()
    app = qtapp.create_app()
    if app is None:
        _logger.error("PyQT4 not installed")
        sys.exit(1)
    
    try:
        from ..core.gui.ImageScreener import MainWindow as Screener
    except:
        _logger.error("Failed to load screener window")
        _logger.exception("Failed to load screener window")
        raise
        sys.exit(1)
    
    dialog = Screener() 
    dialog.show()
    if len(sys.argv) > 1:
        dialog.openImageFiles(sys.argv[1:])
    
    sys.exit(app.exec_())

