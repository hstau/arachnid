''' AutoPicker Parameter Turning GUI

.. Created on Mar 27, 2014
.. codeauthor:: Robert Langlois <rl2528@columbia.edu>
'''

from pyui.AutoPickUI import Ui_Form
from util.qt4_loader import QtGui, QtCore, qtSlot, qtSignal
from util import messagebox
from ..app import program
from util import BackgroundTask
from arachnid.app import autopick
from model.ListTableModel import ListTableModel
from ..metadata import format
import logging
import os

_logger = logging.getLogger(__name__)
_logger.setLevel(logging.DEBUG)

class Widget(QtGui.QWidget): 
    ''' Automated GUI build from command line options
    '''
    taskFinished = qtSignal(object)
    taskUpdated = qtSignal(object)
    taskError = qtSignal(object)
    
    def __init__(self, parent=None):
        "Initialize screener window"
        
        QtGui.QWidget.__init__(self, parent)
        self.parent_control = parent
        
        # Build window
        _logger.info("Building main window ...")
        self.ui = Ui_Form()
        self.ui.setupUi(self)
        self.header = ['# Mics', '# Particles', 'Disk', 'Mask', 'Overlap']
        self.options = [self.ui.diskDoubleSpinBox.statusTip(), self.ui.diskDoubleSpinBox.statusTip(), self.ui.diskDoubleSpinBox.statusTip()]
        self.data = []
        self.micrograph_files=[]
        self.output=None
        self.output_base=None
           
        self.ui.autopickHistoryTableView.setModel(ListTableModel([], self.header, None, self))
        
        #selmodel=self.ui.autopickHistoryTableView.selectionModel()
        self.ui.autopickHistoryTableView.doubleClicked.connect(self.on_runPushButton_clicked)
        
        #doubleClicked ( const QModelIndex & index )
        
        self.ui.progressDialog = QtGui.QProgressDialog('Running...', "Close", 0, 1, self)
        self.ui.progressDialog.setWindowModality(QtCore.Qt.ApplicationModal)
        #self.ui.progressDialog.findChildren(QtGui.QPushButton)[0].hide()
        self.ui.progressDialog.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.WindowTitleHint | QtCore.Qt.CustomizeWindowHint)
        self.task = None
        self.output = None
        self.taskUpdated.connect(self.updateProgress)
        self.option_control_map = self._collect_options_controls()
        self._add_controls()
        # params file
    
    def isValid(self):
        '''
        '''
        
        self.autopick_program = program.generate_settings_tree(autopick, 'cfg')
        if self.autopick_program.values.param_file == "":
            self.autopick_program = None
            messagebox.error_message(self, "Cannot find cfg/autopick.cfg - See details for more information", details="""
            This beta version of the AutoPicker controls only allows you to change a couple of parameters. Thus, it needs
            to be able to read the autopick configuration file (cfg/autopick.cfg).
            
            If you open ara-screen in your project directory, then it should find it.
            
            Please move there or create a properly configured cfg/autopick.cfg.
            """)
            self.close()
            return False
        else:
            self.output_base = self.autopick_program.values.output
        
        extra = vars(self.autopick_program.values)
        for option, control in self.option_control_map.iteritems():
            if hasattr(control, 'isChecked'): control.setChecked(extra[option])
            else: control.setValue(extra[option])
        
        return True
    
    @qtSlot()
    def on_runPushButton_clicked(self, index=None):
        '''
        '''
        
        if index is None:
            extra = self.controlOptionValueDict()
        else:
            #model = self.ui.autopickHistoryTableView.model()
            extra = dict([v for v in zip(self.options, index.data(QtCore.Qt.UserRole)[2:])])
            #disk_mult, mask_mult, overlap_mult = index.data(QtCore.Qt.UserRole)[2:]
        
        # Get list of micrographs
        files = self.parent_control.currentFileList()
        # Update parameters
        if len(files) == 0: 
            return
        self.micrograph_files = files
        self.setEnabled(False)
        '''
        self.ui.diskDoubleSpinBox.setEnabled(False)
        self.ui.maskDoubleSpinBox.setEnabled(False)
        self.ui.overlapDoubleSpinBox.setEnabled(False)
        self.ui.runPushButton.setEnabled(False)
        '''
        
        bin_factor = float(self.parent_control.micrographDecimationFactor())
        output, base = os.path.split(self.output_base)
        output+="-%.2f-%.2f-%.2f"%(extra['disk_mult'], extra['mask_mult'], extra['overlap_mult'])
        output = output.replace(".", "_")
        output = os.path.join(output, base)
        self.autopick_program.update(dict(input_files=self.autopick_program.values.input_files.__class__(files), 
                                          #mask_mult=mask_mult,
                                          #disk_mult=disk_mult,
                                          #overlap_mult=overlap_mult,
                                          bin_factor=bin_factor,
                                          disable_bin=True,
                                          selection_file="",
                                          output=output,
                                          **extra))
        
        self.taskFinished.connect(self.programFinished)
        self.taskError.connect(self.programError)
        def _run_worker(prog):
            yield 1
            yield 0
            _logger.info("Running "+str(prog.name()))
            prog.check_options_validity()
            prog.launch()
            yield 1
        
        self.output = output
        self.task = BackgroundTask.launch_mp(self, _run_worker, self.autopick_program)
        
    def controlOptionValueDict(self):
        '''
        '''
        
        valmap = {}
        for option, control in self.option_control_map.iteritems():
            valmap[option] = control.isChecked() if hasattr(control, 'isChecked') else control.value()
        return valmap
    
    def _add_controls(self):
        '''
        '''
        
        self.header, self.options
        for option, control in self.option_control_map.iteritems():
            title = control.toolTip()
            n = title.find(' (')
            if n != -1: title = title[:n]
            if option in self.options: continue
            self.header.append(title)
            self.options.append(option)
    
    def _collect_options_controls(self):
        '''
        '''
        
        controls={}
        for control_var in vars(self.ui).keys():
            control = getattr(self.ui, control_var)
            if not hasattr(control, 'value') and not hasattr(control, 'isChecked'): continue
            if control.statusTip()=="": continue
            controls[control.statusTip()] = control
        return controls
    
    def programFinished(self, sessions):
        '''
        '''
        
        # Update ara-screen coordinates
        #self.ui.projectTableView.model().setData(sessions)     
        
           
        self.ui.progressDialog.hide()
        self.taskFinished.disconnect(self.programFinished)
        self.taskError.disconnect(self.programError)
        self.task = None
        self.parent_control.setCoordinateFile(self.output)
        self.parent_control.on_loadImagesPushButton_clicked()
        
        count = 0
        for filename in self.micrograph_files:
            try: num = len(format.read(self.output, spiderid=filename))
            except: pass
            else: count += num
        
        valmap = self.controlOptionValueDict()
        self.data.append([ len(self.micrograph_files), count,]+[valmap[o] for o in self.options])
        '''
        self.data.append([ len(self.micrograph_files),
                          count,
                          self.ui.diskDoubleSpinBox.value(),
                          self.ui.maskDoubleSpinBox.value(),
                          self.ui.overlapDoubleSpinBox.value(),
                          ])
        '''
        model = self.ui.autopickHistoryTableView.model()
        model.setData(self.data)
        '''
        self.ui.diskDoubleSpinBox.setEnabled(True)
        self.ui.maskDoubleSpinBox.setEnabled(True)
        self.ui.overlapDoubleSpinBox.setEnabled(True)
        self.ui.runPushButton.setEnabled(True)
        '''
        self.setEnabled(True)
    
    def programError(self, exception):
        '''
        '''
        
        self.ui.progressDialog.hide()
        messagebox.exception_message(self, "Error running ara-autopick", exception)
        self.taskFinished.disconnect(self.programFinished)
        self.taskError.disconnect(self.programError)
        self.task = None
        '''
        self.ui.diskDoubleSpinBox.setEnabled(True)
        self.ui.maskDoubleSpinBox.setEnabled(True)
        self.ui.overlapDoubleSpinBox.setEnabled(True)
        self.ui.runPushButton.setEnabled(True)
        '''
        self.setEnabled(True)
    
    def updateProgress(self, val):
        
        if hasattr(val, '__iter__'):
            if len(val) == 1 and not hasattr(val, '__iter__'):
                self.ui.progressDialog.setMaximum(val[0])
        else:
            self.ui.progressDialog.setValue(val)
    
    @qtSlot(int)
    def on_diskHorizontalSlider_valueChanged(self, value):
        '''
        '''
        
        box = self.ui.diskDoubleSpinBox
        value = value/float(self.ui.diskHorizontalSlider.maximum())
        value *= (box.maximum()-box.minimum())
        value += box.minimum()
        box.blockSignals(True)
        box.setValue(value)
        box.blockSignals(False)
    
    @qtSlot(float)
    def on_diskDoubleSpinBox_valueChanged(self, value=None):
        '''
        '''
        
        box = self.ui.diskDoubleSpinBox
        slider = self.ui.diskHorizontalSlider
        if value is None: value = box.value()
        value -= box.minimum()
        value /= (box.maximum()-box.minimum())
        slider.blockSignals(True)
        slider.setValue(int(slider.maximum()*value))
        slider.blockSignals(False)
    
    @qtSlot(int)
    def on_maskHorizontalSlider_valueChanged(self, value):
        '''
        '''
        
        box = self.ui.maskDoubleSpinBox
        value = value/float(self.ui.maskHorizontalSlider.maximum())
        value *= (box.maximum()-box.minimum())
        value += box.minimum()
        box.blockSignals(True)
        box.setValue(value)
        box.blockSignals(False)
    
    @qtSlot(float)
    def on_maskDoubleSpinBox_valueChanged(self, value=None):
        '''
        '''
        
        box = self.ui.diskDoubleSpinBox
        slider = self.ui.maskHorizontalSlider
        if value is None: value = self.ui.maskDoubleSpinBox.value()
        value -= box.minimum()
        value /= (box.maximum()-box.minimum())
        slider.blockSignals(True)
        slider.setValue(int(slider.maximum()*value))
        slider.blockSignals(False)
    
    @qtSlot(int)
    def on_overlapHorizontalSlider_valueChanged(self, value):
        '''
        '''
        
        box = self.ui.overlapDoubleSpinBox
        value = value/float(self.ui.overlapHorizontalSlider.maximum())
        value *= (box.maximum()-box.minimum())
        value += box.minimum()
        box.blockSignals(True)
        box.setValue(value)
        box.blockSignals(False)
    
    @qtSlot(float)
    def on_overlapDoubleSpinBox_valueChanged(self, value=None):
        '''
        '''
        
        box = self.ui.diskDoubleSpinBox
        slider = self.ui.overlapHorizontalSlider
        if value is None: value = self.ui.overlapDoubleSpinBox.value()
        value -= box.minimum()
        value /= (box.maximum()-box.minimum())
        slider.blockSignals(True)
        slider.setValue(int(slider.maximum()*value))
        slider.blockSignals(False)
        
        