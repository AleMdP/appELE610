#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# ../ELE610/py3/appELE610.py 
#  An image viewer and (simple) image processing app to be used in UiS ELE610 course
#
# Karl Skretting, UiS, March 2026  first version (based on earlier appImageViewer programs)

# Example on how to use file:
# (C:\...\Anaconda3) C:\..\py3>activate qtenv310   # the name of environment on Karls PC where OpenCV and Qt works
# (py12) C:\..\py3>python appELE610.py 
# (py12) C:\..\py3>python appELE610.py kart1.png
# (py12) C:\..\py3>python appELE610.py toTerninger.bmp

_fileName = "appELE610S.py"
_author = "Alejandro & Mauro, UiS"  
_version = "2026.09.19"  # year.month.day

import sys
from pathlib import Path  # https://docs.python.org/3/library/pathlib.html 
import numpy as np 

from mySystem import QT_BINDING, cv2Exist, qt5Exist, qt6Exist, qtChartExist

# OpenCV, https://docs.opencv.org/3.4/index.html
if cv2Exist:
    import cv2
else:
    print("Importing OpenCV failed. Alternative program that don't need OpenCV is")
    print("in my Qt image viewer frame, example: ...ELE610> python clsImageViewFrame.py")
    # It may be better just to abort if OpenCV is not properly imported, as below 
    # raise ImportError(f"{_fileName}: Requires OpenCV")

# Qt, https://doc.qt.io/qt-6/classes.html
if QT_BINDING == "None":
    print("Importing Qt failed.")
    raise ImportError(f"{_fileName}: Requires PyQt6, PySide6 or PyQt5")
else: # ok
    from mySystem import (QT_VERSION_STR, QAction, QColor, pyqtSlot, 
      QApplication, QColorDialog, QInputDialog, QMainWindow,
      QImage_Format_Grayscale8, QImage_Format_Indexed8, QImage_Format_RGB32, 
      Qt_LeftButton, Qt_RightButton)

if qt6Exist:
    from PyQt6.QtCore import QTimer
elif qt5Exist:
    from PyQt5.QtCore import QTimer

# IDS Camera software
try:
    from pyueye import ueye   # see https://pypi.org/project/pyueye/ 
    from pyueye_example_camera import Camera
    from pyueye_example_utils import ImageData, ImageBuffer, uEyeException  # FrameThread, 
    ueyeExist = True
    print('Hello')
except ImportError:
    ueye_error = f"{_fileName}: IDS pyueye (camera-) packages were not correctly loaded" 
    print(ueye_error + "\nProgram can still be used, but camera options are disabled.")
    # raise ImportError(ueye_error)
    ueyeExist = False   # --> may run program even without pyueye 
    ImageData = None

# by KS (UiS) 
from clsImageViewFrame import ImageViewFrame
from clsELE610Dialogs import EdgeDialog, FilterDialog, ThresholdDialog
from clsHoughDialogs import HoughLinesDialog, HoughCirclesDialog, getBestHoughLines, draw_lines
from funImageTools import np2qimage, qimage2np, smoothFilter
from funMyTools import printArray

# define 17 colorNames as in: https://doc.qt.io/qt-5/qcolor.html 
colorNames17 = ['white','black','cyan','darkCyan','red','darkRed','magenta','darkMagenta',
                'green','darkGreen','yellow','darkYellow','blue','darkBlue',
                'gray','darkGray','lightGray']

class MainWindow(QMainWindow):  
    """MainWindow class for appELE610 application
    """
    
    def __init__(self, parent=None, fName=""):
        """Initialize the main window object with title, location and size,
        A image file name 'fName' may be given as input (from command line when program is started)
        and if so this image will be opened and displayed.
        """
        print(f"File {_fileName}: MainWindow.__init__() started" )
        super().__init__(parent) 
        #self.setGeometry(150, 50, 1500, 1200)  # initial window position (x,y) and size (w,h)
        self.setWindowTitle(f"{_fileName}: (version {_version}) use Qt {QT_VERSION_STR}")
        self.camOn = False 

        self.lastEyeCount = -1 
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.processVideoFrame)
        
        self.imFrame = ImageViewFrame(parent=self)
        
        self.initMainMenu() 
        
        self.imFrame.imageChanged.connect(self.setMenuItems)  # must connect before image is opened 

        self.showMaximized() #We modified this so the window starts in full size haha
        
        if isinstance(fName, str) and len(fName):
            self.imFrame.openImageFileDlg(fName)
        
        print(f"File {_fileName}: MainWindow.__init__() ended" )
    
    
    def initMainMenu(self):
        """Initialize File, Image, and Info menus."""
        print(f"File {_fileName}: MainWindow.initMainMenu() started" )
        #
        a = self.qaQuitProgram = QAction('Quit', self)
        a.setShortcut('Ctrl+Q')
        a.setToolTip('Close and quit program')
        a.triggered.connect(self.close)
        #
        # menuBar is a function in QMainWindow class, returns a QMenuBar object
        mainMenu = self.menuBar()  
        fileMenu = mainMenu.addMenu('&File')     # '&' make next char a shortcut as Alt+F
        camMenu = mainMenu.addMenu('Ca&mera')
        imageMenu = mainMenu.addMenu('&Image')   # in imView
        if cv2Exist:
            cvMenu =  mainMenu.addMenu('&OpenCV')  
        colorMenu = mainMenu.addMenu("&Color")
        iaMenu = mainMenu.addMenu("I&A tasks")
        diceMenu = mainMenu.addMenu("Dice")
        diskMenu = mainMenu.addMenu("Disk")
        #
        self.imFrame.populateImageMenu(imageMenu)   # need this before some actions are copied (or moved)
        self.populateCamera(camMenu)
        if cv2Exist:
            self.populateOpenCV(cvMenu)
        self.populateColor(colorMenu)
        self.populateIA(iaMenu)
        self.populateDice(diceMenu)
        self.populateDisk(diskMenu)
        #
        fileMenu.addAction(self.imFrame.qaOpenImageFileDlg)
        fileMenu.addAction(self.imFrame.qaSaveImageFileDlg)
        fileMenu.addAction(self.imFrame.qaClearImage)
        fileMenu.addSeparator()
        fileMenu.addAction(self.imFrame.qaPrintImageInfo)
        fileMenu.addAction(self.imFrame.qaMakeHistogram)
        fileMenu.addSeparator()
        fileMenu.addAction(self.qaQuitProgram)
        fileMenu.setToolTipsVisible(True)
        #
        imageMenu.clear()  # want another menu layout here 
        imageMenu.addAction(self.imFrame.qaScaleOne)
        imageMenu.addAction(self.imFrame.qaScaleUp)
        imageMenu.addAction(self.imFrame.qaScaleDown)
        imageMenu.addAction(self.imFrame.qaCrop)
        imageMenu.addAction(self.imFrame.qaResize)
        imageMenu.addAction(self.imFrame.qaToGray)
        imageMenu.addAction(self.imFrame.qaUndoLast)
        imageMenu.setToolTipsVisible(True)
        #
        self.setMenuItems()
        print(f"File {_fileName}: MainWindow.initMainMenu() ended")


    def populateCamera(self, menu):
        a = self.qaCameraOn = QAction('Camera on', self)
        a.triggered.connect(self.cameraOn)
        menu.addAction(a)
        a = self.qaCameraInfo = QAction('Print camera info', self)
        a.triggered.connect(self.printCameraInfo)
        menu.addAction(a)
        a = self.qaEditCameraInfo = QAction('Edit camera info', self)
        a.triggered.connect(self.editCameraInfo)
        menu.addAction(a)
        a = self.qaFindFocus = QAction('Find focus', self)
        a.triggered.connect(self.findFocus)
        menu.addAction(a)
        a = self.qaGetOneImage = QAction('Get one image', self)
        a.setShortcut('Ctrl+N')
        a.triggered.connect(self.getOneImage)
        menu.addAction(a)
        a = self.qaToggleVideo = QAction('Start/Stop Continuous Mode', self)
        a.triggered.connect(self.toggleContinuousMode)
        menu.addAction(a)
        a = self.qaCameraOff = QAction('Camera off', self)
        a.triggered.connect(self.cameraOff)
        menu.addAction(a)

    def populateOpenCV(self, menu):
        # add 5 OpenCV actions (functions) to a menu
        #
        a = self.qaToEdges = QAction('To Edges', self)
        a.triggered.connect(self.toEdges)
        a.setToolTip('Use Sobel filters and low-pass filter and find edges')
        a.setShortcut('Ctrl+E')
        menu.addAction(a)
        a = self.qaFilter = QAction('Filter image', self)
        a.triggered.connect(self.filterImage)
        a.setToolTip('Define a filter plus a low-pass filter and filter image')
        a.setShortcut('Ctrl+F')
        menu.addAction(a)
        a = self.qaToBinary = QAction('To Binary', self)
        a.triggered.connect(self.toBinary)
        a.setToolTip('Threshold image to make binary image')
        a.setShortcut('Ctrl+B')
        menu.addAction(a)
        a = self.qaFindLines = QAction('Find Lines', self)
        a.triggered.connect(self.findHoughLines)
        a.setToolTip('Find lines using HoughLines or HoughLinesP')
        a.setShortcut('Ctrl+L')
        menu.addAction(a)
        a = self.qaFindCircles = QAction('Find Circles', self)
        a.triggered.connect(self.findHoughCircles)
        a.setToolTip('Find circles using HoughCircles')
        menu.addAction(a)

    def populateColor(self, menu):
        # add 9 Color actions (functions) to a menu
        #
        a = self.qaSwapRandB = QAction( "Swap red and blue", self)
        a.triggered.connect(self.swapRandB)
        a.setToolTip("Change from RGB to BGR or opposite")
        menu.addAction(a)
        a = self.qaInvert = QAction( "Invert color in image", self)
        a.triggered.connect(self.invertColor)
        a.setToolTip("Invert black to white, and opposite")
        menu.addAction(a)
        menu.addSeparator()
        a = self.qaEditColors = QAction( "Edit custom colors", self)
        a.triggered.connect(self.editColors)
        a.setToolTip("Edit list of custom colors (in QColorDialog)")
        menu.addAction(a)
        a = self.qaMeanColor = QAction( "Add mean color", self)
        a.triggered.connect(self.meanColorStart)
        a.setToolTip("Add average color from image rectangle to custom color list")
        menu.addAction(a)
        a = self.qaClearColors = QAction( "Clear custom colors", self)
        a.triggered.connect(self.clearColors)
        a.setToolTip("Clear custom color list, i.e. set all to 'white'")
        menu.addAction(a)
        a = self.qaSetColors = QAction( "Set custom colors", self)
        a.triggered.connect(self.setColors)
        a.setToolTip("Set custom color list, i.e. set all to standard colors.")
        menu.addAction(a)
        menu.addSeparator()
        #
        a = self.qaDistColorRGB = QAction( "Distance to RGB color", self)
        a.triggered.connect(self.distColorRGB)
        a.setToolTip("Make a gray scale image by distance to a selected RGB color")
        menu.addAction(a)
        a = self.qaBestDistColorRGB = QAction( "Distance to closest RGB color", self)
        a.triggered.connect(self.bestDistColorRGB)
        a.setToolTip("Make a gray scale image by distance to a closest custom RGB color")
        menu.addAction(a)
        a = self.qaAttractColorRGB = QAction( "Attract to closest RGB color", self)
        a.triggered.connect(self.attractColorRGB)
        a.setToolTip("Attract image to a custom RGB colors")
        menu.addAction(a)

    def populateIA(self, menu):
        # add actions (functions) to a menu for tasks in UiS ELE610 course
        a = self.qa142bw = QAction("IA 1.4.2 bw", self)
        a.triggered.connect(self.ia142bw)
        a.setToolTip("Make a simple black-white or grayscale image")
        menu.addAction(a)
        
        a = self.qa142col = QAction("IA 1.4.2 col", self)
        a.triggered.connect(self.ia142col)
        a.setToolTip("Make a simple color image")
        menu.addAction(a)
        
        a = self.qa143 = QAction("IA 1.4.3", self)
        a.triggered.connect(self.ia143)
        a.setToolTip("Where students should make answer to part 1.4.3 in IA assignment 1")
        menu.addAction(a)

        menu.addSeparator()

        a = self.qa144cGray = QAction("IA 1.4.4c Convert to Gray (OpenCV)", self)
        a.triggered.connect(self.ia144cGray)
        a.setToolTip("Convert active image to grayscale using OpenCV")
        menu.addAction(a)

        a = self.qa144dHist = QAction("IA 1.4.4d Histogram", self)
        a.triggered.connect(self.ia144dHist)
        a.setToolTip("Plot image histogram")
        menu.addAction(a)
        

    def populateDice(self, menu):
        a = self.qaDices = QAction("Find dices", self)
        a.triggered.connect(self.findDices)
        menu.addAction(a)
        a = self.qaEyes = QAction("Find eyes on a dice", self)
        a.triggered.connect(self.findEyes)
        menu.addAction(a)
        a = self.qaColorDices = QAction("Find color and eyes", self)
        a.triggered.connect(self.colorDices)
        menu.addAction(a)
        menu.addSeparator()
        a = self.qaBlackDots = QAction("Black Dots", self)
        a.triggered.connect(self.findBlackDots)
        menu.addAction(a)
        a = self.qaDiceCircles = QAction("Find Circles (Dice)", self)
        a.triggered.connect(self.findDiceCircles)
        menu.addAction(a)

    def populateDisk(self, menu):
        a = self.qaDisk = QAction("Find disk", self)
        a.triggered.connect(self.findDisk)
        menu.addAction(a)
        a = self.qaRedSector = QAction("Find red sector", self)
        a.triggered.connect(self.findRedSector)
        menu.addAction(a)
        a = self.qaFindSpeed = QAction("Find speed", self)
        a.triggered.connect(self.findSpeed)
        menu.addAction(a)

    @pyqtSlot()
    def setMenuItems(self):
        """Slot for self.imFrame.imageChanged signal
        """
        im = self.imFrame.image 
        isOk = not (im.isNull() or self.imFrame.rubberBandActive)
        isGray = (im.format() == QImage_Format_Grayscale8) 
        # print(f"MainWindow.setMenuItems(): {im.format()=} --> {isOk=}, {isGray=}")
        if cv2Exist:
            # OpenCV menu items
            self.qaToEdges.setEnabled(isOk and isGray and cv2Exist)
            self.qaFilter.setEnabled(isOk and isGray and cv2Exist)
            self.qaToBinary.setEnabled(isOk and isGray and cv2Exist)
            self.qaFindLines.setEnabled(isOk and isGray and cv2Exist)
            self.qaFindCircles.setEnabled(isOk and isGray and cv2Exist)
        # Camera menu items
        self.qaCameraOn.setEnabled(ueyeExist and (not self.camOn))   
        self.qaCameraInfo.setEnabled(ueyeExist and self.camOn)   
        self.qaEditCameraInfo.setEnabled(ueyeExist and self.camOn)
        self.qaFindFocus.setEnabled(ueyeExist and self.camOn)
        self.qaGetOneImage.setEnabled(ueyeExist and self.camOn)   
        self.qaToggleVideo.setEnabled(ueyeExist and self.camOn)
        self.qaCameraOff.setEnabled(ueyeExist and self.camOn)   
        # Color menu items
        self.qaSwapRandB.setEnabled(isOk and not isGray)   
        self.qaInvert.setEnabled(isOk)   
        self.qaClearColors.setEnabled(True)
        self.qaSetColors.setEnabled(True)
        self.qaEditColors.setEnabled(True)
        self.qaMeanColor.setEnabled(isOk)
        self.qaDistColorRGB.setEnabled(isOk and not isGray)
        self.qaBestDistColorRGB.setEnabled(isOk and not isGray)
        self.qaAttractColorRGB.setEnabled(isOk and not isGray)
        # Actions 
        self.qa142bw.setEnabled(cv2Exist)
        self.qa142col.setEnabled(cv2Exist)
        self.qa143.setEnabled(cv2Exist)
        self.qa144cGray.setEnabled(cv2Exist and isOk)
        self.qa144dHist.setEnabled(cv2Exist and isOk)
        #
        self.qaDices.setEnabled(cv2Exist and isOk)
        self.qaEyes.setEnabled(cv2Exist and isOk) 
        self.qaColorDices.setEnabled(cv2Exist and isOk)
        self.qaBlackDots.setEnabled(cv2Exist and isOk)
        self.qaDiceCircles.setEnabled(cv2Exist and isOk)
        #
        self.qaDisk.setEnabled(cv2Exist and isOk)
        self.qaRedSector.setEnabled(cv2Exist and isOk and not isGray)
        self.qaFindSpeed.setEnabled(cv2Exist and isOk)


    # *** The 10 OpenCV functions, 2 for each menu item (dialog and slot for signal from dialog) ***

    def toEdges(self): 
        """Show the edge dialog, and process the grayscale image 
        according to the values returned from the dialog.
        Use Sobel filters and separable low-pass filter and find edges.
        """
        im = self.imFrame.image 
        if im.format() == QImage_Format_Grayscale8 and not im.isNull():
            d = EdgeDialog(parent=self)   # create object (but does not run it)
            d.edgeValuesChanged.connect(self.showEdges)
            (valK,valS) = d.getValues()   # display dialog and return values
            d.edgeValuesChanged.disconnect(self.showEdges)
            if d.result():  # [Ok]-button
                self.imFrame.prevImage = im  # = self.imFrame.image (as it should not have been updated yet)
                self.showEdges(valK, valS, update=True)
                im = self.imFrame.image 
                self.imFrame.imHead.setText(f"Edge image, (w,h) = ({im.width()},{im.height()})")
                self.imFrame.imFile.setText("Filename: ")
            else:  # [Cancel]-button 
                self.imFrame.showImageOnScene(im)   

    def showEdges(self, valK, valS, update=False):
        """This method may be started with signal from the edge dialog 
        to (quickly) show results of new edge filter values.
        """
        im = self.imFrame.image 
        B = qimage2np(im).astype(np.float32)
        Eh = cv2.Sobel(B, ddepth=cv2.CV_32F, dx=0, dy=1, ksize=valK)
        Ev = cv2.Sobel(B, ddepth=cv2.CV_32F, dx=1, dy=0, ksize=valK)
        B = np.sqrt( 1 + np.power(Eh,2) + np.power(Ev,2) )
        if (valS > 1):
            a = smoothFilter(len=valS)
            B = cv2.sepFilter2D(B, ddepth=-1, kernelX=a, kernelY=a)
        B = np.floor(B * (255/np.max(B))).astype(np.uint8)
        qim = np2qimage(B)
        if qim.isNull():
            print("showEdges: The QImage made is Null, strange.")
        else:
            qim.convertTo(QImage_Format_Grayscale8)
            if update:
                self.imFrame.image = qim
            self.imFrame.showImageOnScene(qim)  


    def filterImage(self):  
        """Show the filter dialog, and filter the (grayscale) image 
        according to the values returned from the dialog.
        OpenCV function cv2.filter2D(..) do the actual work.
        """
        im = self.imFrame.image 
        if im.format() == QImage_Format_Grayscale8 and not im.isNull():
            d = FilterDialog(parent=self)   # create object (but does not run it)
            d.filterValuesChanged.connect(self.showFiltered)
            H, valS = d.getValues()   # display dialog and return values
            d.filterValuesChanged.disconnect(self.showFiltered)
            if d.result():  # [Ok]-button
                self.imFrame.prevImage = im  # = self.imFrame.image (as it should not have been updated yet)
                self.showFiltered(H, valS, update=True)
                im = self.imFrame.image 
                self.imFrame.imHead.setText(f"Filtered image, (w,h) = ({im.width()},{im.height()})")
                self.imFrame.imFile.setText("Filename: ")
            else:  # [Cancel]-button 
                self.imFrame.showImageOnScene(im)   

    def showFiltered(self, H, valS, update=False):
        """This method may be started with signal from the filter dialog 
        to (quickly) filter image and show filtered image.
        """
        im = self.imFrame.image 
        B = qimage2np(im).astype(np.float32)
        if len(H): 
            B = cv2.filter2D(B, ddepth=-1, kernel=H)
        if (valS > 1):
            a = smoothFilter(len=valS)
            B = cv2.sepFilter2D(B, ddepth=-1, kernelX=a, kernelY=a)
        B = B - np.min(B)
        B = np.floor(B * (255/np.max(B))).astype(np.uint8)
        qim = np2qimage(B)
        if qim.isNull():
            print("showFiltered: The QImage made is Null, strange.")
        else:
            # qim.convertTo(QImage_Format_Grayscale8)
            if update:
                self.imFrame.image = qim
            self.imFrame.showImageOnScene(qim)  


    def toBinary(self): 
        """Show the threshold dialog, and convert the grayscale image 
        to a binary image using the returned threshold.
        """
        im = self.imFrame.image 
        if im.format() == QImage_Format_Grayscale8 and not im.isNull():
            d = ThresholdDialog(parent=self)   # create object (but does not run it)
            d.thresholdValueChanged.connect(self.showBinary)
            thr = d.getValue()   # display dialog and return values
            d.thresholdValueChanged.disconnect(self.showBinary)
            if d.result():  # [Ok]-button
                self.imFrame.prevImage = im 
                self.showBinary(thr, update=True)
                im = self.imFrame.image 
                self.imFrame.imHead.setText(f"Binary image, (w,h) = ({im.width()},{im.height()})")
                self.imFrame.imFile.setText("Filename: ")
            else:  # [Cancel]-button 
                self.imFrame.showImageOnScene(im)   

    def showBinary(self, thr=0, update=False):
        """This method may be started from the threshold dialog 
        to (quickly) show results of threshold 'thr'.
        """
        im = self.imFrame.image 
        A = qimage2np(im).astype(np.uint8)
        if (thr < 1):
            (used_thr, B) = cv2.threshold(A, thresh=1, maxval=255, type=cv2.THRESH_OTSU)
            print(f"showBinary: The used Otsu threshold value is {used_thr}") 
        else:
            (used_thr, B) = cv2.threshold(A, thresh=thr, maxval=255, type=cv2.THRESH_BINARY)
            print(f"showBinary: The used threshold value is {used_thr}") 
        qim = np2qimage(B)
        if qim.isNull():
            print("showBinary: The QImage made is Null, strange.")
        else:
            qim.convertTo(QImage_Format_Grayscale8)
            if update:
                self.imFrame.image = qim
            self.imFrame.showImageOnScene(qim)  


    def findHoughLines(self):
        """Show the HoughLines dialog, and indicate where lines where found.
        The current binary image is processed in OpenCV, result is shown as RGB image
        """
        im = self.imFrame.image 
        if im.format() == QImage_Format_Grayscale8 and not im.isNull():
            # check if image is binary as it should be, i.e. values should be 0 or 255
            B = qimage2np(im) 
            count0 = (B==0).sum()
            count255 = (B==255).sum()
            if (count0+count255)==B.size:
                print("findHoughLines(): image B is binary as it should be, ", end="")
            else: 
                print("findHoughLines(): image B is grayscale but not binary, ", end="") 
            print(f"{count0} 0-values, {count255} 255-values, and {B.size=}") 
            #
            if ((count0+count255)==B.size):
                d = HoughLinesDialog(parent=self) 
                d.lineValuesChanged.connect(self.showHoughLines)
                t = d.getValues()   # display dialog and return values
                d.lineValuesChanged.disconnect(self.showHoughLines)
                if d.result():  # [Ok]-button
                    self.imFrame.prevImage = im 
                    self.showHoughLines(t, update=True)
                    im = self.imFrame.image 
                    self.imFrame.imHead.setText(f"Hough lines image, (w,h) = ({im.width()},{im.height()})")
                else:  # [Cancel]-button 
                    self.imFrame.showImageOnScene(im)   

    def showHoughLines(self, t, update=False):
        """This method may be started from the HoughLines dialog 
        to (quickly) show results of parameters in tuple t.
        """
        im = self.imFrame.image 
        B = qimage2np(im).astype(np.uint8)   # binary image!
        if (len(t) == 5):   # use cv2.HoughLines() to find the lines
            (rho, theta, threshold, nofLines, distLines) = t
            # print( f"argument t = ({rho=}, {theta=}*pi/180, {threshold=}, {nofLines=}, {distLines=})" )
            linesFound = cv2.HoughLines(B, rho=rho, theta=theta*np.pi/180.0, threshold=threshold)
        elif (len(t) == 7): # use cv2.HoughLinesP() to find the lines
            (rho, theta, threshold, minLineLength, maxLineGap, nofLines, distLines) = t
            # print( f"argument t = ({rho=}, {theta=}*pi/180, {threshold=}, " + \
            # 	   f"{minLineLength=}, {maxLineGap=}, {nofLines=}, {distLines=})" )
            linesFound = cv2.HoughLinesP(B, rho=rho, theta=theta*np.pi/180.0, \
                    threshold=threshold, minLineLength=minLineLength, maxLineGap=maxLineGap)
        else:
            # print( "tryHoughLines: argument 't', dialog response, has not expected length." )
            linesFound = None
        #
        if isinstance(linesFound, np.ndarray):
            if update:
                # the 'involved' way to find lines
                print(f"linesFound has ndim={linesFound.ndim}, shape={linesFound.shape} and dtype={linesFound.dtype}")
                linesToDraw = getBestHoughLines(linesFound, B, nofLines, distLines, verbose=False)
                print(f"linesToDraw has ndim={linesToDraw.ndim}, shape={linesToDraw.shape} and dtype={linesToDraw.dtype}")
                txt = f"showHoughLines: Show 'best' {linesToDraw.shape[0]} of {linesFound.shape[0]} lines"
            else:
                # the easy way to find lines
                linesToDraw = linesFound[:min(nofLines,linesFound.shape[0])]   
                txt = f"showHoughLines: Show first {linesToDraw.shape[0]} of {linesFound.shape[0]} lines"
            self.imFrame.imFile.setText(txt)
            imgBGR = cv2.cvtColor(B, cv2.COLOR_GRAY2BGR)  # and result shown in a BGR image
            draw_lines(linesToDraw, imgBGR, color=(0,255,0), thickness=3, verbose=False)
            qim = np2qimage(imgBGR)
            if qim.isNull():
                print("showHoughLines: The QImage made is Null, strange.")
            else:
                if update:
                    self.imFrame.image = qim
                self.imFrame.showImageOnScene(qim)  


    def findHoughCircles(self):
        """Find circles in active grayscale image using HoughCircles(..)
        """
        im = self.imFrame.image 
        if im.format() == QImage_Format_Grayscale8 and not im.isNull():
            d = HoughCirclesDialog(parent=self)   # create object (but does not run it)
            d.circleValuesChanged.connect(self.showHoughCircles)
            t = d.getValues()   # display dialog and return values
            d.circleValuesChanged.disconnect(self.showHoughCircles)
            if d.result():  # [Ok]-button
                self.imFrame.prevImage = im 
                self.showHoughCircles(t, update=True)
                im = self.imFrame.image 
                self.imFrame.imHead.setText(f"Hough Circle image, (w,h) = ({im.width()},{im.height()})")
            else:  # [Cancel]-button 
                self.imFrame.showImageOnScene(im)   

    def showHoughCircles(self, t, update=False):
        """Show circles for the parameters given in tuple 't', without committing.
        """
        im = self.imFrame.image 
        B = qimage2np(im).astype(np.uint8)    # grayscale image should be used as input
        (dp, minDist, param1, param2, minRadius, maxRadius, maxCircles) = t
        circFound = cv2.HoughCircles(B, cv2.HOUGH_GRADIENT, dp=dp, minDist=minDist,
                param1=param1, param2=param2, minRadius=minRadius, maxRadius=maxRadius)
        #
        if isinstance(circFound, np.ndarray):
            # print(f"circFound is a numpy array of ndim={circFound.ndim}, shape={circFound.shape} and dtype={circFound.dtype}")
            circFound = np.int16(np.around(circFound))
            nofToShow = min(maxCircles, circFound.shape[1])
            txt = f"showHoughCircles: Show {nofToShow} of {circFound.shape[1]} circles,  " + \
                  f"({circFound[0,:,2].min()} <= radius <= {circFound[0,:,2].max()})"
            self.imFrame.imFile.setText(txt)
            imgBGR = cv2.cvtColor(B, cv2.COLOR_GRAY2BGR)  # and result shown in a BGR image
            for i in range(nofToShow):
                (x,y,r) = ( circFound[0,i,0], circFound[0,i,1], circFound[0,i,2] )  # center and radius
                cv2.circle(imgBGR, (x,y), r, (255, 0, 255), 2) # and circle outline 
                # print(f"  circle {i} has center in ({x},{y}) and radius {r}")
            # print(f"  imgBGR is ndarray of {imgBGR.dtype.name}, shape: {str(imgBGR.shape)}")
            qim = np2qimage(imgBGR)
            if qim.isNull():
                print("showHoughCircles: The QImage made is Null, strange.")
            else:
                if update:
                    self.imFrame.image = qim
                self.imFrame.showImageOnScene(qim)  

    # *** The 10 Color functions, one for each menu item, two for select color ***

    def swapRandB(self):
        """Swap red and blue component of RGB or BGR image 
        Have no 'undo' here as doing the operation once more undo these changes, 
        thus 'undo' will undo previous operation as before.
        """
        im = self.imFrame.image 
        if (not im.isNull()):
            A = qimage2np(im)
            if (A.ndim == 3) and (A.shape[2] >= 3):
                print( "swapRandB(): swap red and blue component of RGB or BGR image" )
                im = self.imFrame.image = np2qimage( A[:,:,[2,1,0]] )
                self.imFrame.showImageOnScene()
                self.imFrame.imHead.setText(f"RGB image, (w,h) = ({im.width()},{im.height()})")
                self.imFrame.imFile.setText("swapRandB: image has Red and Blue components swapped")
        
    def invertColor(self):
        """Invert black to white and white to black.
        Have no 'undo' here as doing the operation once more undo these changes, 
        thus 'undo' will undo previous operation as before.
        """
        im = self.imFrame.image 
        if (not im.isNull()):
            A = qimage2np(im)
            if (A.dtype == np.uint8):
                print( "invertColor(): invert black to white and white to black" )
                if (A.ndim == 3) and (A.shape[2] >= 3):  # don't invert alpha!
                    A[:,:,:3] = (255-A[:,:,:3]).astype(np.uint8) 
                else:
                    A = (255-A).astype(np.uint8)
                im = np2qimage(A)
                self.imFrame.image = im
                self.imFrame.showImageOnScene(im)
                self.imFrame.imHead.setText(f"Inverted image, (w,h) = ({im.width()},{im.height()})")
                self.imFrame.imFile.setText("invertColor: image colors are inverted")
        
    def editColors(self):
        """Set colors for the custom color list in QColorDialog by simply calling it.
        Just print returned color
        """
        newColor = QColorDialog.getColor(title="You may now add or change custom colors.")
        if newColor.isValid():
            print( f"editColors(): selected color from dialog box is {newColor.name()}." )
            print( f"  There are {QColorDialog.customCount()} colors in the custom color list:" )
            for cNo in range(QColorDialog.customCount()):
                print( f"  {QColorDialog.customColor(cNo).name()}", end="" )
            print(" ")
        else:
            print( "editColors(): no valid color, [Cancel] button pressed." )
    
    def meanColorStart(self):
        """Turn rubber band on to select rectangle for color
        """
        im = self.imFrame.image 
        if (not im.isNull()):
            # perhaps this would be better solved with signals ?
            self.imFrame.rubberBandActive = True
            self.imFrame.view.rubberBandRectGiven.connect(self.meanColorEnd)
            self.imFrame.imFile.setText("Use mouse click-and-drag to select color rectangle")
            self.imFrame.setMenuItems()
            self.setMenuItems()
        return
    
    def meanColorEnd(self, rectangle):
        """Find mean color using the input rectangle (in image pixels) on the current pixmap .
        The mean color replaces the first 'white' color in QColorDialog custom color list.
        This function does not change the image.
        """
        def intRGB(rgb):
            # (r,g,b) = intRGB(rgb)
            r = min(max(0,int(rgb[0]+0.5)),255)
            g = min(max(0,int(rgb[1]+0.5)),255)
            b = min(max(0,int(rgb[2]+0.5)),255)
            return (r,g,b)
        #
        # perhaps this would be better solved with signals ?
        if self.imFrame.rubberBandActive:  
            im = self.imFrame.image 
            self.imFrame.rubberBandActive = False
            self.imFrame.view.rubberBandRectGiven.disconnect(self.meanColorEnd)
            x1 = max(0, rectangle.topLeft().x())
            x2 = min(rectangle.bottomRight().x(), im.width())
            y1 = max(0, rectangle.topLeft().y())
            y2 = min(rectangle.bottomRight().y(), im.height())
            w = x2 - x1
            h = y2 - y1
            #
            A = qimage2np(im)   # prefer a numpy array for the image
            R = np.float32(np.reshape(A[y1:y2,x1:x2,:3], (w*h, 3)))
            print(f"  A is ndarray of {A.dtype.name}, shape: {str(A.shape)}")
            print(f"  (x1,y1) = ({x1},{y1}),  (x2,y2) = ({x2},{y2}),  (w,h) = ({w},{h})  w*h = {w*h}")
            print(f"  R is ndarray of {R.dtype.name}, shape: {str(R.shape)}")
            #
            meanCol = np.mean(R, axis=0)  # ndarray 
            print(f"  mean color in rectangle is = ({meanCol[2]:5.1f}, {meanCol[1]:5.1f}, {meanCol[0]:5.1f}) (rgb)")
            (r,g,b) = intRGB(meanCol)
            print(f"  mean color in rectangle is = ({r:3d},   {g:3d},   {b:3d}  ) (rgb)")
            #
            for cNo in range(QColorDialog.customCount()):
                if QColorDialog.customColor(cNo) == QColor('white'):
                    QColorDialog.setCustomColor(cNo, QColor(r,g,b))
                    break
            #
            self.imFrame.setMenuItems()  # meanColor should be turned back on
            self.setMenuItems()  # meanColor should be turned back on
    
    def clearColors(self):
        """Clear all custom colors, i.e. set each to 'white'
        """
        for cNo in range(QColorDialog.customCount()):
            if not (QColorDialog.customColor(cNo) == QColor('white')):
                QColorDialog.setCustomColor(cNo, QColor('white'))
        
    def setColors(self):
        """Set all custom colors, i.e. set each to standard color
        """
        for cNo in range(min(QColorDialog.customCount(),16)):
            QColorDialog.setCustomColor(cNo, QColor(colorNames17[cNo+1]))
        return
    
    # RGB seems to be swapped here, generally RGB is confusing
    def distColorRGB(self):
        """Make grayscale image by testing if pixel color is close to a selected RGB color.
        Distance is measured for each pixel p with color (r,g,b) to selected color (R,G,B) as
           d = max(abs(r-R), abs(g-G), abs(b-B)), 
        where d is pixel value for resulting grayscale image
        """
        color = QColorDialog.getColor(title="Select the color to measure distance to.")
        im = self.imFrame.image 
        if color.isValid() and (not im.isNull()):
            print(f"  selected color is {color.name()}")
            bgr = [color.blue(), color.green(), color.red()]
            A = qimage2np(im).astype(np.float32)   # prefer a numpy array for the image
            if (A.ndim > 2) and (A.shape[2] >= 3): 
                A = A[:,:,[2,1,0]]  # or A[:,:,:3]
                B = np.ones(shape=A.shape, dtype=np.float32)  # the one color image
                B[:,:,:] = bgr
                D = np.max(np.abs(A-B),axis=2).astype(np.uint8)  # the distance image
                del B
            else:
                grayLevel = int((color.red() + color.green() + color.blue() + 0.5)/3)
                print(f"Color '{color.name()}' = ({color.red()}, {color.green()}, {color.blue()}) has grayLevel {grayLevel}")
                D = np.abs(A - grayLevel).astype(np.uint8)
                del grayLevel
            #
            print(f"  A is ndarray of {A.dtype.name}, shape: {str(A.shape)}")
            print(f"  D is ndarray of {D.dtype.name}, shape: {str(D.shape)}, max: {D.max()}")
            #
            self.imFrame.prevImage = im 
            im = np2qimage(D)
            self.imFrame.image = im 
            self.imFrame.showImageOnScene(im)
            self.imFrame.imHead.setText(f"distColorRGB(): distance to color {color.name()}")
            self.imFrame.imFile.setText(f"Distance image, (w,h) = ({im.width()},{im.height()})")

    def bestDistColorRGB(self):
        """Make binary image by testing if pixel color is close to one of custom RGB color.
        Distance is measured for each pixel p with color (r,g,b) to custom colors (Ri,Gi,Bi) as
           d = min_i max(abs(r-Ri), abs(g-Gi), abs(b-Bi)),   i in range(nofCustomColors)
        where d is pixel value for resulting gray scale image
        """
        im = self.imFrame.image 
        if not im.isNull():
            A = qimage2np(im).astype(np.float32)   # prefer a numpy array for the image
            if (A.ndim > 2) and (A.shape[2] >= 3): 
                A = A[:,:,[2,1,0]]  # or A[:,:,:3]
            D = 255*np.ones((A.shape[0], A.shape[1]), dtype=np.uint8)
            for cNo in range(QColorDialog.customCount()):
                color = QColorDialog.customColor(cNo)
                if not (color == QColor('white')):
                    if (len(A.shape) > 2) and (A.shape[2] >= 3): 
                        bgr = [color.blue(), color.green(), color.red()]
                        B = np.ones(shape=A.shape, dtype=np.float32)  # the one color image
                        B[:,:,:] = bgr
                        Di = np.max(np.abs(A-B),axis=2).astype(np.uint8)  # the distance image
                        del B
                    else:
                        grayLevel = int((color.red() + color.green() + color.blue() + 0.5)/3)
                        Di = np.abs(A - grayLevel).astype(np.uint8)
                    #end if
                    D = np.minimum(D,Di)
                #end if
            #end for
            print(f"  A is ndarray of {A.dtype.name}, shape: {str(A.shape)}")
            print(f"  D is ndarray of {D.dtype.name}, shape: {str(D.shape)}, max: {D.max()}")
            #
            self.imFrame.prevImage = im 
            im = np2qimage(D)
            self.imFrame.image = im 
            self.imFrame.showImageOnScene(im)
            self.imFrame.imHead.setText(f"bestDistColorRGB(): distance to best color")
            self.imFrame.imFile.setText(f"Distance image, (w,h) = ({im.width()},{im.height()})")
        
    def attractColorRGB(self):
        """Make image by assigning colors to closest of custom RGB colors.
        """
        im = self.imFrame.image 
        if not im.isNull():
            A = qimage2np(im).astype(np.float32)   # prefer a numpy array for the image
            if (A.ndim > 2) and (A.shape[2] >= 3): 
                A = A[:,:,[2,1,0]]  # or A[:,:,:3]
            D = 255*np.ones((A.shape[0], A.shape[1], QColorDialog.customCount()), dtype=np.uint8)   # 3D-array
            for cNo in range(QColorDialog.customCount()):
                color = QColorDialog.customColor(cNo)
                if not (color == QColor('white')):
                    if (A.ndim > 2) and (A.shape[2] >= 3): 
                        bgr = [color.blue(), color.green(), color.red()]
                        B = np.ones(shape=A.shape, dtype=np.float32)  # the one color image
                        B[:,:,:] = bgr
                        D[:,:,cNo] = np.max(np.abs(A-B),axis=2).astype(np.uint8)  # the distance images
                        del B
                    else:
                        grayLevel = int((color.red() + color.green() + color.blue() + 0.5)/3)
                        D[:,:,cNo] = np.abs(A - grayLevel).astype(np.uint8)

            print(f"  A is ndarray of {A.dtype.name}, shape: {str(A.shape)}")
            print(f"  D is ndarray of {D.dtype.name}, shape: {str(D.shape)}, max: {D.max()}")
            distLimit, ok = QInputDialog.getInt(self,    # parent
                    f"attractColorRGB(): input 'distLimit'",  # title
                    "Give limit distance for attracted color (else 'white')",      # label
                    value=25, min=0, max=255)
            print(f"QInputDialog.getInt(..) returned  distLimit = {distLimit},  ok = {ok}")
            if ok:
                B = 255*np.ones((A.shape[0], A.shape[1], 3), dtype=np.uint8)
                minD = D.min(axis=2)  # distance to closest color
                I = D.argmin(axis=2)  # indexes for best color
                for cNo in range(QColorDialog.customCount()):
                    color = QColorDialog.customColor(cNo)
                    if not (color == QColor('white')):
                        idx = np.logical_and(I==cNo, minD<=distLimit)
                        print(f"  set {np.count_nonzero(idx)} pixels to color {color.name()}")
                        B[idx,0] = color.red()   
                        B[idx,1] = color.green()
                        B[idx,2] = color.blue()
                    #end if
                #end for
                print(f"  B is ndarray of {B.dtype.name}, shape: {str(B.shape)}")
                #
                self.imFrame.prevImage = im 
                im = np2qimage(B)
                self.imFrame.image = im 
                self.imFrame.showImageOnScene(im)
                self.imFrame.imHead.setText(f"attractColorRGB(): change colors")
                self.imFrame.imFile.setText(f"Color image, (w,h) = ({im.width()},{im.height()})")


    # *** Methods on the camera menu  ***
    
    def cameraOn(self):
        """Turn IDS camera on.
        I have only tested this on the small IDS XS camera used i IA2 and IA3.
        Perhaps a modified function is needed for the CP camera used in IA4.
        """
        if ueyeExist and (not self.camOn):
            try:
                self.cam = Camera()
                self.cam.init() 
                self.cam.set_colormode(ueye.IS_CM_BGR8_PACKED)
                # This function is currently not supported by the camera models USB 3 uEye XC and XS.
                self.cam.set_aoi(0, 0, 720, 1280)  # but this is the size used
                self.cam.alloc(3)  # argument is number of buffers
                self.camOn = True
                self.imFrame.imHead.setText("Camera started")
                print( f"cameraOn() Camera started ok" )
            except uEyeException as e:
                print(f"cameraOn() Caught camera error: {e}")
                print("  Typically gives error 212 when camera is not connected (not present)")
                self.camOn = False
            #
            self.setMenuItems()

    def cameraOff(self):
        """Turn IDS camera off and print some information.
        I have only tested this on the small IDS XS camera used i IA2 and IA3.
        Perhaps a modified function is needed for the CP camera used in IA4.
        """
        if ueyeExist and self.camOn:
            if self.timer.isActive():
                self.timer.stop()
            self.cam.exit()
            self.camOn = False
            self.setMenuItems()
            self.imFrame.imHead.setText("Camera stopped")
            print( f"cameraOff() Camera stopped ok" )

    def printCameraInfo(self):
            """Print some information on camera.
            I have only tested this on the small IDS XS camera used i IA2 and IA3.
            Perhaps a modified function is needed for the CP camera used in IA4.
            """
            if ueyeExist and self.camOn:
                print("printCameraInfo(): print (test) state and settings.")
                # just set a camera option (parameter) even if it is not used here
                d = ueye.double()
                # d1 = ueye.double() 
                # d2 = ueye.double()
                ui1 = ueye.uint()
                retVal = ueye.is_SetFrameRate(self.cam.handle(), 2.0, d)
                if retVal == ueye.IS_SUCCESS:
                    print(f"  frame rate set to                      {float(d):8.3f} fps")
                retVal = ueye.is_Exposure(self.cam.handle(), 
                                          ueye.IS_EXPOSURE_CMD_GET_EXPOSURE_DEFAULT, d, 8)
                if retVal == ueye.IS_SUCCESS:
                    print(f"  default setting for the exposure time  {float(d):8.3f} ms")
                retVal = ueye.is_Exposure(self.cam.handle(), 
                                          ueye.IS_EXPOSURE_CMD_GET_EXPOSURE_RANGE_MIN, d, 8)
                if retVal == ueye.IS_SUCCESS:
                    print(f"  minimum exposure time                  {float(d):8.3f} ms")
                retVal = ueye.is_Exposure(self.cam.handle(), 
                                          ueye.IS_EXPOSURE_CMD_GET_EXPOSURE_RANGE_MAX, d, 8)
                if retVal == ueye.IS_SUCCESS:
                    print(f"  maximum exposure time                  {float(d):8.3f} ms")
                # 
                print(f"  sys.getsizeof(d) returns   {sys.getsizeof(d)}  (??)")
                print(f"  sys.getsizeof(ui1) returns {sys.getsizeof(ui1)}  (??)")
                retVal = ueye.is_Focus(self.cam.handle(), ueye.FDT_CMD_GET_CAPABILITIES, ui1, 4)
                if ((retVal == ueye.IS_SUCCESS) and (ui1 & ueye.FOC_CAP_AUTOFOCUS_SUPPORTED)):
                    print( "  autofocus supported" )
                if retVal == ueye.IS_SUCCESS:
                    print(f"  is_Focus() is success          ui1 = {ui1}")
                else:
                    print(f"  is_Focus() is NOT success   retVal = {retVal}")
                fZR = ueye.IS_RECT()   # may be used to set focus ??
                retVal = ueye.is_Focus(self.cam.handle(), ueye.FOC_CMD_SET_ENABLE_AUTOFOCUS, ui1, 0)
                if retVal == ueye.IS_SUCCESS:
                    print(f"  is_Focus( ENABLE ) is success      ")
                retVal = ueye.is_Focus(self.cam.handle(), ueye.FOC_CMD_GET_AUTOFOCUS_STATUS, ui1, 4)
                if retVal == ueye.IS_SUCCESS:
                    print(f"  is_Focus( STATUS ) is success  ui1 = {ui1}")
                # There may be some trouble setting exposure time
                retVal = ueye.is_Exposure(self.cam.handle(), ueye.IS_EXPOSURE_CMD_GET_EXPOSURE, d, 8)
                if retVal == ueye.IS_SUCCESS:
                    print(f"  currently set exposure time            {float(d):8.3f} ms")
                d =  ueye.double(5.0)
                retVal = ueye.is_Exposure(self.cam.handle(), ueye.IS_EXPOSURE_CMD_SET_EXPOSURE, d, 8)
                if retVal == ueye.IS_SUCCESS:
                    print(f"  tried to changed exposure time to      {float(d):8.3f} ms")
                retVal = ueye.is_Exposure(self.cam.handle(), ueye.IS_EXPOSURE_CMD_GET_EXPOSURE, d, 8)
                if retVal == ueye.IS_SUCCESS:
                    print(f"  currently set exposure time            {float(d):8.3f} ms")

    def countEyesInArray(self, gray_img, updateScene=False):
        """Ultra-stable helper based on SimpleBlobDetector."""
        blurred = cv2.GaussianBlur(gray_img, (5, 5), 0)
        
        params = cv2.SimpleBlobDetector_Params()
        
        params.filterByColor = True
        params.blobColor = 0
        
        params.minThreshold = 10
        params.maxThreshold = 160
        params.thresholdStep = 10
        
        params.filterByArea = True
        params.minArea = 80
        params.maxArea = 8000
        
        params.filterByCircularity = True
        params.minCircularity = 0.35
        
        params.filterByInertia = True
        params.minInertiaRatio = 0.35
        
        detector = cv2.SimpleBlobDetector_create(params)
        keypoints = detector.detect(blurred)
        
        if updateScene:
            imgBGR = cv2.cvtColor(gray_img, cv2.COLOR_GRAY2BGR)
            imgBGR = cv2.drawKeypoints(imgBGR, keypoints, np.array([]), (0, 0, 255),
                                       cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS)
            qim = np2qimage(imgBGR)
            self.imFrame.image = qim
            self.imFrame.showImageOnScene(qim)
            
        return len(keypoints)

    def getOneImage(self):
        """Get one image from IDS camera.
        There may be a better way to get one image, here image may be out of focus, 
        and perhaps this is done more as video should be captured.
        In ELE610 the students should try to improve this function, 
        and make another function to capture video.
        Also, I only tested this on the small IDS XS camera used i IA2 and IA3.
        Perhaps a modified function is needed for the CP camera used in IA4.
        """
        if ueyeExist and self.camOn:
            print(f"getOneImage() try to capture one image")
            imBuf = ImageBuffer()  # used to get return pointers
            self.cam.freeze_video(True)
            retVal = ueye.is_WaitForNextImage(self.cam.handle(), 1000, imBuf.mem_ptr, imBuf.mem_id)
            if retVal == ueye.IS_SUCCESS:
                print(f"  ueye.IS_SUCCESS: image buffer id = {imBuf.mem_id}")
                self.showCameraImage( ImageData(self.cam.handle(), imBuf) )  # copy image_data 
            else: 
                self.setWindowTitle("getOneImage() error retVal = {retVal}")
            #end if
            self.setMenuItems()

    def showCameraImage(self, image_data):  # image_data is an ImageData object
        """Copy an image from camera memory to self.image, via a numpy array,
        and then show the image on scene
        """
        tempImage = image_data.as_1d_image()  
        if np.min(tempImage) != np.max(tempImage):
            A = np.copy(tempImage[:,:,[2,1,0]])  # or [0,1,2] ??  RGB or BGR ??
            #print(f"showCameraImage(): A is an ndarray of {A.dtype.name}, shape {str(A.shape)}.") 
        else: 
            A = np.array([])
            print("showCameraImage(): the ImageData object is not as it should be.")  
        #end if 
        image_data.unlock()  # important action
        #
        if (A.size > 0): # ok 
            im = self.imFrame.image   
            if not im.isNull():
                self.imFrame.prevImage = im   
            #
            im = np2qimage(A)
            self.imFrame.image = im 
            self.imFrame.showImageOnScene(im)
            if not (hasattr(self, 'timer') and self.timer.isActive()):
                self.imFrame.imHead.setText("Image from camera")
                self.imFrame.imFile.setText(f"Image size (w,h) = ({im.width()},{im.height()})")
        else:  # empty image A
            print("showCameraImage(): no image in buffer") 


    

    # *** The methods for UiS ELE610 Image Acquisition assignments  ***

    def ia142bw(self):
        """Make the black and white image with 3 simple objects as in IA 1.4.2
        """
        # keep current image, if any
        im = self.imFrame.image   
        if not im.isNull():
            self.imFrame.prevImage = im   
        #
        A = np.zeros((300,400),dtype=np.uint8)
        A = cv2.line(A, (10,10), (10,50), 255)
        A = cv2.rectangle(A, (20,10), (50,60), 255, thickness=-1)
        A = cv2.ellipse(A, (120,50), (40,40), angle=360, startAngle=0, endAngle=360, color=255, thickness=2)
        #
        im = np2qimage(A)
        self.imFrame.image = im 
        self.imFrame.showImageOnScene(im)
        self.imFrame.imHead.setText(f"Image made as in IA 1.4.2")
        self.imFrame.imFile.setText(f"Black-White image, (w,h) = ({im.width()},{im.height()})")

    def ia142col(self):
        """Make a color image with some simple objects as in IA 1.4.2
        Red line, green rectangle and blue circle. 
        """
        def diskAA(A,cx,cy,r,col):
            # draw a disk with anti-aliasing in image A 
            h = A.shape[0]
            w = A.shape[1]
            y1 = max(0,int(np.floor(cy-r-1.0)))
            y2 = min(int(np.ceil(cy+r+1.0001)),h)
            x1 = max(0,int(np.floor(cx-r-1.0)))
            x2 = min(int(np.ceil(cx+r+1.0001)),w)
            # print(f"Image A: {w=}, {h=}, {cx=}, {cy=}, {r=}, --> {y1=}, {y2=}, {x1=}, {x2=}")
            yD2 = np.power(np.arange(y1-cy,y2-cy), 2)
            xD2 = np.power(np.arange(x1-cx,x2-cx), 2)
            # xyD is distance for each pixel (x,y) to circle center
            xyD = np.sqrt(np.dot(yD2.reshape(len(yD2),1), np.ones((1,len(xD2)))) + 
                          np.dot(np.ones((len(yD2),1)), xD2.reshape(1,len(xD2))))
            # B is the 'alpha'-factor for each pixel, 1.0 -> only col, 0.0 -> only background
            delta = 0.7  # half the width of transistion area
            #  r-delta < xyD[y,x] < r+delta -> there is a blending: partly col partly background
            B = np.clip((r+delta-xyD)/(2*delta), 0.0, 1.0)
            # printArray(B,'B')
            # set A in circle square, i.e. A[y1:y2,x1:x2]
            if A.ndim == 2:
                A[y1:y2,x1:x2] = B*col + (1.0-B)*A[y1:y2,x1:x2]
            elif A.ndim == 3:
                for i in range(A.shape[2]):  # 3 or 4, and same as col.size
                    A[y1:y2,x1:x2,i] = B*col[i] + (1.0-B)*A[y1:y2,x1:x2,i]
            A = A.astype(np.uint8)

        # keep current image
        im = self.imFrame.image   
        if not im.isNull():
            self.imFrame.prevImage = im   
        #
        A = np.zeros((300,400,3),dtype=np.uint8)   
        A = cv2.line(A, (10,10), (10,50), [250,10,10])   
        A = cv2.rectangle(A, (20,10), (50,60), [10,250,10], thickness=-1) 
        A = cv2.ellipse(A, (120,50), (40,40), angle=360, startAngle=0, endAngle=360, color=[10,10,255], thickness=2)
        diskAA(A, 300, 150, 25, [150,150,10])
        diskAA(A, 66.66, 58.25, 30, [200,10,10])
        #
        im = np2qimage(A)
        self.imFrame.image = im 
        self.imFrame.showImageOnScene(im)
        self.imFrame.imHead.setText(f"Image made as in IA 1.4.2")
        self.imFrame.imFile.setText(f"Color image, (w,h) = ({im.width()},{im.height()})")

    def ia143(self):
        """Make the black and white image with objects as described in part 1.4.3
        """
        # keep current image, if any
        im = self.imFrame.image   
        if not im.isNull():
            self.imFrame.prevImage = im   
        #
        A = np.zeros((300,400),dtype=np.uint8)  # all black image
        #
        # students put their code here
        
        # 
        im = np2qimage(A)
        self.imFrame.image = im 
        self.imFrame.showImageOnScene(im)
        self.imFrame.imHead.setText(f"Image made as in IA 1.4.3")
        self.imFrame.imFile.setText(f"Color image, (w,h) = ({im.width()},{im.height()})")

    

    def ia144cGray(self):
        """1.4.4c: Convert active image to grayscale using OpenCV cv2.cvtColor"""
        im = self.imFrame.image
        if not im.isNull():
            self.imFrame.prevImage = im
            A = qimage2np(im)
            if A.ndim == 3 and A.shape[2] >= 3:
                gray = cv2.cvtColor(A[:, :, :3], cv2.COLOR_RGB2GRAY)
            else:
                gray = A.copy()
            qim = np2qimage(gray)
            qim.convertTo(QImage_Format_Grayscale8)
            self.imFrame.image = qim
            self.imFrame.showImageOnScene(qim)
            self.imFrame.imHead.setText("Grayscale image (OpenCV cv2.cvtColor)")
            self.imFrame.imFile.setText(f"Size (w,h) = ({qim.width()},{qim.height()})")

    def ia144dHist(self):
        """1.4.4d: Replace image by its histogram plot using OpenCV and Matplotlib"""
        im = self.imFrame.image
        if not im.isNull():
            self.imFrame.prevImage = im
            A = qimage2np(im)
            if A.ndim == 3:
                A = cv2.cvtColor(A[:, :, :3], cv2.COLOR_RGB2GRAY)
            
            hist = cv2.calcHist([A], [0], None, [256], [0, 256])
            
            import matplotlib.pyplot as plt
            fig, ax = plt.subplots(figsize=(5, 4), dpi=100)
            ax.plot(hist, color='black')
            ax.set_title('Image Histogram')
            ax.set_xlabel('Pixel Intensity (0-255)')
            ax.set_ylabel('Pixel Count')
            ax.grid(True)
            fig.tight_layout()
            
            fig.canvas.draw()
            rgba_buffer = fig.canvas.buffer_rgba()
            hist_img = np.asarray(rgba_buffer)[:, :, :3]
            plt.close(fig)
            
            qim = np2qimage(hist_img)
            self.imFrame.image = qim
            self.imFrame.showImageOnScene(qim)
            
            cv2.imwrite("../task1_4_4d_histogram.png", cv2.cvtColor(hist_img, cv2.COLOR_RGB2BGR))
            self.imFrame.imHead.setText("Histogram Plot (Press Ctrl+Z to undo)")
            self.imFrame.imFile.setText("Saved as task1_4_4d_histogram.png")

    def findFocus(self):
            """2.3.b: Trigger autofocus and capture sequence to let lens settle (IA2)."""
            import time
            if ueyeExist and self.camOn:
                print("findFocus(): Starting autofocus and stabilization routine")
                
                ui_status = ueye.uint()
                retVal = ueye.is_Focus(self.cam.handle(), ueye.FOC_CMD_SET_ENABLE_AUTOFOCUS, ui_status, 0)
                if retVal == ueye.IS_SUCCESS:
                    print("findFocus(): Hardware autofocus command sent successfully.")
    
                print("findFocus(): Capturing frames while autofocus settles")
                for i in range(5):
                    self.getOneImage()
                    time.sleep(0.15)
    
                print("findFocus(): Autofocus sequence completed.")
    
    def editCameraInfo(self):
        """2.3.f & 3.2.f: Allows you to view and edit the camera's FPS and exposure time."""
        if ueyeExist and self.camOn:
            d_fps = ueye.double()
            ueye.is_SetFrameRate(self.cam.handle(), ueye.IS_GET_FRAMERATE, d_fps)
            current_fps = float(d_fps)

            exp_curr = ueye.double()
            ueye.is_Exposure(self.cam.handle(), ueye.IS_EXPOSURE_CMD_GET_EXPOSURE, exp_curr, 8)
            current_exp = float(exp_curr)

            new_fps, ok_fps = QInputDialog.getDouble(
                self, "Edit Camera Info", "Set Frame Rate (FPS):", 
                value=current_fps, min=1.0, max=60.0, decimals=2
            )
            
            if ok_fps:
                disable_auto = ueye.double(0)
                ueye.is_SetAutoParameter(self.cam.handle(), ueye.IS_SET_ENABLE_AUTO_SENSOR_GAIN, disable_auto, ueye.double(0))
                ueye.is_SetAutoParameter(self.cam.handle(), ueye.IS_SET_ENABLE_AUTO_SENSOR_SHUTTER, disable_auto, ueye.double(0))

                fps_to_set = ueye.double(new_fps)
                retVal = ueye.is_SetFrameRate(self.cam.handle(), fps_to_set, d_fps)
                
                ueye.is_SetFrameRate(self.cam.handle(), ueye.IS_GET_FRAMERATE, d_fps)
                actual_fps = float(d_fps)
                
                if retVal == ueye.IS_SUCCESS:
                    msg = f"Frame rate changed to {actual_fps:.2f} FPS"
                    print(f"editCameraInfo(): {msg}")
                    if hasattr(self, 'imFrame'):
                        self.imFrame.imHead.setText(f"Camera Info: {msg}")
                else:
                    print(f"editCameraInfo(): Failed to set frame rate. Error code: {retVal}")

            new_exp, ok_exp = QInputDialog.getDouble(
                self, "Edit Camera Info", "Set Exposure Time (ms):", 
                value=current_exp, min=0.1, max=100.0, decimals=2
            )

            if ok_exp:
                exp_to_set = ueye.double(new_exp)
                retVal_exp = ueye.is_Exposure(self.cam.handle(), ueye.IS_EXPOSURE_CMD_SET_EXPOSURE, exp_to_set, 8)

                ueye.is_Exposure(self.cam.handle(), ueye.IS_EXPOSURE_CMD_GET_EXPOSURE, exp_curr, 8)
                actual_exp = float(exp_curr)

                if retVal_exp == ueye.IS_SUCCESS:
                    msg = f"Exposure changed to {actual_exp:.2f} ms"
                    print(f"editCameraInfo(): {msg}")
                    if hasattr(self, 'imFrame'):
                        self.imFrame.imHead.setText(f"Camera Info: {msg}")
                else:
                    print(f"editCameraInfo(): Failed to set exposure time. Error code: {retVal_exp}")

        else:
            print("editCameraInfo(): Camera is not turned on or uEye module unavailable.")
            if hasattr(self, 'imFrame'):
                self.imFrame.imHead.setText("Edit Camera Info: Turn on the camera first.")

    def findBlackDots(self):
        """2.3.c: Isolate black dots on dice using Value/Brightness channel thresholding (IA2)."""
        from PyQt6.QtGui import QImage

        im = self.imFrame.image
        if not im.isNull():
            self.imFrame.prevImage = im
            
            A = qimage2np(im)
            
            if A.ndim == 3 and A.shape[2] == 4:
                bgr = cv2.cvtColor(A, cv2.COLOR_RGBA2BGR)
            elif A.ndim == 3 and A.shape[2] == 3:
                bgr = cv2.cvtColor(A, cv2.COLOR_RGB2BGR)
            else:
                bgr = cv2.cvtColor(A, cv2.COLOR_GRAY2BGR)

            hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
            _, _, v_channel = cv2.split(hsv)
            
            blurred = cv2.GaussianBlur(v_channel, (9, 9), 0)
            
            _, binary = cv2.threshold(blurred, 85, 255, cv2.THRESH_BINARY_INV)
            
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
            cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
            cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, kernel)

            contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            dots_mask = np.zeros_like(cleaned)
            
            dots_count = 0
            for cnt in contours:
                area = cv2.contourArea(cnt)
                if 200 < area < 40000:
                    cv2.drawContours(dots_mask, [cnt], -1, 255, thickness=-1)
                    dots_count += 1

            if dots_count == 0:
                dots_mask = cleaned

            rgb_mask = cv2.cvtColor(dots_mask, cv2.COLOR_GRAY2RGB)
            
            qim = np2qimage(rgb_mask)
            self.imFrame.image = qim
            self.imFrame.showImageOnScene(qim)
            self.imFrame.imHead.setText(f"Black Dots isolated: {dots_count} dots found")
            self.imFrame.imFile.setText(f"Size = ({qim.width()},{qim.height()})")

    def findDiceCircles(self):
        """2.3.d: Detect circular dots on dice using Hough Circles (IA2)."""
        im = self.imFrame.image
        if not im.isNull():
            self.imFrame.prevImage = im
            A = qimage2np(im)
            
            if A.ndim == 3 and A.shape[2] == 4:
                bgr = cv2.cvtColor(A, cv2.COLOR_RGBA2BGR)
            elif A.ndim == 3 and A.shape[2] == 3:
                bgr = cv2.cvtColor(A, cv2.COLOR_RGB2BGR)
            else:
                bgr = cv2.cvtColor(A, cv2.COLOR_GRAY2BGR)

            output = bgr.copy()
            
            gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
            blurred = cv2.medianBlur(gray, 5)

            circles = cv2.HoughCircles(
                blurred, 
                cv2.HOUGH_GRADIENT, 
                dp=1, 
                minDist=25, 
                param1=100, 
                param2=18, 
                minRadius=10, 
                maxRadius=60
            )

            circles_count = 0
            if circles is not None:
                circles = np.uint16(np.around(circles))
                for i in circles[0, :]:
                    center = (i[0], i[1])
                    radius = i[2]
                    cv2.circle(output, center, radius, (0, 255, 0), 3)
                    cv2.circle(output, center, 2, (0, 0, 255), 3)
                    circles_count += 1

            print(f"findCirclesDice(): It has been found {circles_count} circles using Hough.")

            rgb_output = cv2.cvtColor(output, cv2.COLOR_BGR2RGB)
            qim = np2qimage(rgb_output)
            self.imFrame.image = qim
            self.imFrame.showImageOnScene(qim)
            self.imFrame.imHead.setText(f"Hough Circles: {circles_count} circles found")
            self.imFrame.imFile.setText(f"Size = ({qim.width()},{qim.height()})")

    def toggleContinuousMode(self):
        """2.3g: Starts or stops continuous mode (IA2)."""
        if self.timer.isActive():
            self.timer.stop()
            print("Continuous mode stopped.")
            self.imFrame.imHead.setText("Continuous mode stopped")
        else:
            if not self.camOn:
                return
            
            self.lastEyeCount = -1
            self.timer.start(1000)
            print("Continuous mode started.")
            self.imFrame.imHead.setText("Continuous mode started")

    def processVideoFrame(self):
        """2.3g: Captures frames continuously and only print on console when the number of eyes changes (IA2)."""
        if ueyeExist and self.camOn:
            imBuf = ImageBuffer()
            self.cam.freeze_video(True)
            retVal = ueye.is_WaitForNextImage(self.cam.handle(), 200, imBuf.mem_ptr, imBuf.mem_id)
            
            if retVal == ueye.IS_SUCCESS:
                self.showCameraImage(ImageData(self.cam.handle(), imBuf))
                
                im = self.imFrame.image
                if not im.isNull():
                    A = qimage2np(im)
                    if A.ndim == 3 and A.shape[2] >= 3:
                        gray = cv2.cvtColor(A[:, :, :3], cv2.COLOR_RGB2GRAY)
                    else:
                        gray = A.copy()
                    
                    currentEyes = self.countEyesInArray(gray, updateScene=False)
                    
                    if currentEyes != self.lastEyeCount:
                        print(f"Change detected: Eyes: {self.lastEyeCount} -> {currentEyes}")
                        self.lastEyeCount = currentEyes
                        self.imFrame.imHead.setText(f"Eyes detected: {currentEyes}")
        
        QApplication.processEvents()


    def findDices(self):
        """2.3.e: Locate dice reliably based on dot density per bounding region (IA2)."""
        im = self.imFrame.image
        if not im.isNull():
            self.imFrame.prevImage = im
            A = qimage2np(im)
            
            if A.ndim == 3 and A.shape[2] == 4:
                bgr = cv2.cvtColor(A, cv2.COLOR_RGBA2BGR)
            elif A.ndim == 3 and A.shape[2] == 3:
                bgr = cv2.cvtColor(A, cv2.COLOR_RGB2BGR)
            else:
                bgr = cv2.cvtColor(A, cv2.COLOR_GRAY2BGR)

            output = bgr.copy()
            
            hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
            _, _, v_channel = cv2.split(hsv)
            blurred = cv2.GaussianBlur(v_channel, (5, 5), 0)
            _, binary = cv2.threshold(blurred, 85, 255, cv2.THRESH_BINARY_INV)
            
            dot_contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            dots = []
            for cnt in dot_contours:
                area = cv2.contourArea(cnt)
                if 200 < area < 40000:
                    x, y, w, h = cv2.boundingRect(cnt)
                    dots.append((x + w // 2, y + h // 2, x, y, w, h))
            
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (35, 35))
            dilated = cv2.dilate(binary, kernel, iterations=2)
            
            contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            final_boxes = []
            for cnt in contours:
                area = cv2.contourArea(cnt)
                if area > 2000:
                    bx, by, bw, bh = cv2.boundingRect(cnt)
                    
                    dots_in_box = [d for d in dots if bx <= d[0] <= bx + bw and by <= d[1] <= by + bh]
                    
                    if len(dots_in_box) > 6 or bh > 1.3 * bw:
                        half_h = bh // 2
                        final_boxes.append((bx, by, bw, half_h))
                        final_boxes.append((bx, by + half_h, bw, bh - half_h))
                    else:
                        final_boxes.append((bx, by, bw, bh))

            dice_count = 0
            for (bx, by, bw, bh) in final_boxes:
                dice_count += 1
                pad_x = 8
                pad_y = 8
                
                x_pad = max(0, bx - pad_x)
                y_pad = max(0, by - pad_y)
                w_pad = min(output.shape[1] - x_pad, bw + 2 * pad_x)
                h_pad = min(output.shape[0] - y_pad, bh + 2 * pad_y)
                
                cv2.rectangle(output, (x_pad, y_pad), (x_pad + w_pad, y_pad + h_pad), (0, 255, 0), 3)
                cv2.putText(
                    output, f"Dice #{dice_count}", (x_pad, max(25, y_pad - 10)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2
                )

            print(f"findDices(): There has been found {dice_count} dices.")

            rgb_output = cv2.cvtColor(output, cv2.COLOR_BGR2RGB)
            qim = np2qimage(rgb_output)
            self.imFrame.image = qim
            self.imFrame.showImageOnScene(qim)
            self.imFrame.imHead.setText(f"Find Dices: {dice_count} dice detected")
            self.imFrame.imFile.setText(f"Size = ({qim.width()},{qim.height()})")

    def findEyes(self):
        """2.3.e: Accurately locate each dice and count its corresponding eyes (IA2)."""
        im = self.imFrame.image
        if not im.isNull():
            self.imFrame.prevImage = im
            A = qimage2np(im)
            
            if A.ndim == 3 and A.shape[2] == 4:
                bgr = cv2.cvtColor(A, cv2.COLOR_RGBA2BGR)
            elif A.ndim == 3 and A.shape[2] == 3:
                bgr = cv2.cvtColor(A, cv2.COLOR_RGB2BGR)
            else:
                bgr = cv2.cvtColor(A, cv2.COLOR_GRAY2BGR)

            output = bgr.copy()
            
            hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
            _, _, v_channel = cv2.split(hsv)
            blurred = cv2.GaussianBlur(v_channel, (5, 5), 0)
            _, binary = cv2.threshold(blurred, 85, 255, cv2.THRESH_BINARY_INV)
            
            contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            dots = []
            for cnt in contours:
                area = cv2.contourArea(cnt)
                if 400 < area < 15000:
                    x, y, w, h = cv2.boundingRect(cnt)
                    aspect_ratio = float(w) / h
                    if 0.6 < aspect_ratio < 1.6:
                        dots.append({'center': (x + w // 2, y + h // 2), 'box': (x, y, w, h)})

            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (35, 35))
            dilated = cv2.dilate(binary, kernel, iterations=2)
            
            dice_contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            dice_regions = []
            for cnt in dice_contours:
                area = cv2.contourArea(cnt)
                if area > 2000:
                    bx, by, bw, bh = cv2.boundingRect(cnt)
                    
                    dots_in_region = [
                        d for d in dots 
                        if bx <= d['center'][0] <= bx + bw and by <= d['center'][1] <= by + bh
                    ]
                    
                    if len(dots_in_region) > 6 or bh > 1.35 * bw:
                        half_h = bh // 2
                        top_box = (bx, by, bw, half_h)
                        top_dots = [d for d in dots_in_region if d['center'][1] < by + half_h]
                        dice_regions.append({'box': top_box, 'dots': top_dots})
                        
                        bottom_box = (bx, by + half_h, bw, bh - half_h)
                        bottom_dots = [d for d in dots_in_region if d['center'][1] >= by + half_h]
                        dice_regions.append({'box': bottom_box, 'dots': bottom_dots})
                    else:
                        dice_regions.append({'box': (bx, by, bw, bh), 'dots': dots_in_region})

            total_eyes = 0
            for idx, dice in enumerate(dice_regions, start=1):
                bx, by, bw, bh = dice['box']
                dice_dots = dice['dots']
                eyes_count = len(dice_dots)
                total_eyes += eyes_count
                
                pad_x, pad_y = 6, 6
                x_pad = max(0, bx - pad_x)
                y_pad = max(0, by - pad_y)
                w_pad = min(output.shape[1] - x_pad, bw + 2 * pad_x)
                h_pad = min(output.shape[0] - y_pad, bh + 2 * pad_y)
                
                cv2.rectangle(output, (x_pad, y_pad), (x_pad + w_pad, y_pad + h_pad), (0, 255, 0), 3)
                
                for dot in dice_dots:
                    dx, dy, dw, dh = dot['box']
                    center = dot['center']
                    radius = max(dw, dh) // 2 + 2
                    cv2.circle(output, center, radius, (0, 0, 255), 2)
                
                cv2.putText(
                    output, f"Dice #{idx}: {eyes_count} eyes", (x_pad, max(25, y_pad - 10)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2
                )

            print(f"findEyes(): It has been found {len(dice_regions)} dices with {total_eyes} total eyes.")

            rgb_output = cv2.cvtColor(output, cv2.COLOR_BGR2RGB)
            qim = np2qimage(rgb_output)
            self.imFrame.image = qim
            self.imFrame.showImageOnScene(qim)
            self.imFrame.imHead.setText(f"Find Eyes: Total {total_eyes} eyes detected across {len(dice_regions)} dice")
            self.imFrame.imFile.setText(f"Size = ({qim.width()},{qim.height()})")

    # *** (IA3) ***

    def colorDices(self):
        """3.2.c, d, e: Find color and eyes."""
        im = self.imFrame.image
        if not im.isNull():
            self.imFrame.prevImage = im
            A = qimage2np(im)
            
            if A.ndim == 3 and A.shape[2] == 4:
                bgr = cv2.cvtColor(A, cv2.COLOR_RGBA2BGR)
            elif A.ndim == 3 and A.shape[2] == 3:
                bgr = cv2.cvtColor(A, cv2.COLOR_RGB2BGR)
            else:
                bgr = cv2.cvtColor(A, cv2.COLOR_GRAY2BGR)

            output_bgr, results = self._analyze_dices_in_image(bgr)

            print("\n--- DICE DETECTION RESULTS ---")
            if len(results) == 0:
                print("No dice detected in image.")
            else:
                for color, eyes in results:
                    print(f"{color} dice shows {eyes} eyes.")
            print("------------------------------\n")

            rgb_out = cv2.cvtColor(output_bgr, cv2.COLOR_BGR2RGB)
            qim = np2qimage(rgb_out)
            self.imFrame.image = qim
            self.imFrame.showImageOnScene(qim)
            self.imFrame.imHead.setText(f"Detected {len(results)} dice(s)")
    
    def _detect_dice_color_robust(self, bgr_crop):
        """3.2.c: Detects the color of the dice (IA3)."""
        if bgr_crop.size == 0 or bgr_crop.shape[0] < 10 or bgr_crop.shape[1] < 10:
            return "Unknown"

        hsv_crop = cv2.cvtColor(bgr_crop, cv2.COLOR_BGR2HSV)
        v_channel = hsv_crop[:, :, 2]
        s_channel = hsv_crop[:, :, 1]
        
        surface_mask = v_channel > 80

        if cv2.countNonZero(surface_mask) < 20:
            return "Black"

        b_med = np.median(bgr_crop[:, :, 0][surface_mask])
        g_med = np.median(bgr_crop[:, :, 1][surface_mask])
        r_med = np.median(bgr_crop[:, :, 2][surface_mask])
        
        h_med = np.median(hsv_crop[:, :, 0][surface_mask])
        s_med = np.median(s_channel[surface_mask])

        rgb_max = max(r_med, g_med, b_med)
        rgb_min = min(r_med, g_med, b_med)
        
        if (rgb_max - rgb_min) < 32 and s_med < 45 and rgb_max > 130:
            return "White"

        if r_med > 110 and (r_med - g_med) > 30 and b_med > (g_med * 0.75):
            return "Pink"

        if r_med > 110 and g_med > (r_med * 0.80) and b_med < (g_med * 0.70):
            return "Yellow"

        if r_med > 110 and (r_med * 0.35) < g_med <= (r_med * 0.79) and b_med < (g_med * 0.70):
            return "Orange"

        if (h_med <= 8 or h_med >= 160):
            return "Red"
        elif 9 <= h_med <= 18:
            return "Orange"
        elif 19 <= h_med <= 34:
            return "Yellow"
        elif 35 <= h_med <= 85:
            return "Green"
        elif 86 <= h_med <= 135:
            return "Blue"
        elif 136 <= h_med <= 159:
            return "Pink"

        return "White" if s_med < 35 else "Unknown"

    def _analyze_dices_in_image(self, bgr_img):
        """3.2.b-e: Detects eyes and outlines the dice."""
        output = bgr_img.copy()
        hsv = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2HSV)
        v_channel = hsv[:, :, 2]

        blurred_v = cv2.GaussianBlur(v_channel, (5, 5), 0)
        _, binary_dots = cv2.threshold(blurred_v, 90, 255, cv2.THRESH_BINARY_INV)

        dot_contours, _ = cv2.findContours(binary_dots, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        dots = []
        dots_mask = np.zeros_like(binary_dots)

        for cnt in dot_contours:
            area = cv2.contourArea(cnt)
            if 60 < area < 18000:
                perimeter = cv2.arcLength(cnt, True)
                if perimeter > 0:
                    circularity = 4 * np.pi * (area / (perimeter * perimeter))
                    if circularity > 0.25:
                        x, y, w, h = cv2.boundingRect(cnt)
                        if 0.3 < (w / h) < 3.0:
                            dots.append((x + w // 2, y + h // 2))
                            cv2.drawContours(dots_mask, [cnt], -1, 255, -1)

        kernel_dilate = cv2.getStructuringElement(cv2.MORPH_RECT, (65, 65))
        dilated_mask = cv2.dilate(dots_mask, kernel_dilate, iterations=2)

        dice_contours, _ = cv2.findContours(dilated_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        results_summary = []

        for cnt in dice_contours:
            bx, by, bw, bh = cv2.boundingRect(cnt)

            margin = 20
            bx_pad = max(0, bx - margin)
            by_pad = max(0, by - margin)
            bw_pad = min(bgr_img.shape[1] - bx_pad, bw + 2 * margin)
            bh_pad = min(bgr_img.shape[0] - by_pad, bh + 2 * margin)

            dice_dots = [pt for pt in dots if bx_pad <= pt[0] <= bx_pad + bw_pad and by_pad <= pt[1] <= by_pad + bh_pad]
            eyes_count = len(dice_dots)

            if eyes_count < 1 or eyes_count > 6:
                continue

            crop_x1 = bx_pad + int(bw_pad * 0.1)
            crop_y1 = by_pad + int(bh_pad * 0.1)
            crop_x2 = bx_pad + bw_pad - int(bw_pad * 0.1)
            crop_y2 = by_pad + bh_pad - int(bh_pad * 0.1)

            bgr_crop = bgr_img[crop_y1:crop_y2, crop_x1:crop_x2]
            color_name = self._detect_dice_color_robust(bgr_crop)

            cv2.rectangle(output, (bx_pad, by_pad), (bx_pad + bw_pad, by_pad + bh_pad), (0, 255, 0), 3)
            for pt in dice_dots:
                cv2.circle(output, pt, 5, (0, 0, 255), -1)

            label = f"{color_name} dice: {eyes_count} eyes"
            cv2.putText(output, label, (bx_pad, max(25, by_pad - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

            results_summary.append((color_name, eyes_count))

        return output, results_summary

    def processVideoFrame(self):
        """3.2.g: Processes the video frames, printing only when the state changes."""
        if ueyeExist and self.camOn:
            imBuf = ImageBuffer()
            self.cam.freeze_video(True)
            retVal = ueye.is_WaitForNextImage(self.cam.handle(), 200, imBuf.mem_ptr, imBuf.mem_id)
            
            if retVal == ueye.IS_SUCCESS:
                img_data = ImageData(self.cam.handle(), imBuf)
                tempImage = img_data.as_1d_image()
                
                if np.min(tempImage) != np.max(tempImage):
                    bgr = np.copy(tempImage[:, :, [0, 1, 2]])
                    img_data.unlock()

                    output_bgr, results = self._analyze_dices_in_image(bgr)
                    
                    current_str = str(results)
                    if getattr(self, 'last_dice_str', '') != current_str:
                        self.last_dice_str = current_str
                        print("[VIDEO LIVE]:")
                        for color, eyes in results:
                            print(f"  {color} dice shows {eyes} eyes.")

                    rgb_out = cv2.cvtColor(output_bgr, cv2.COLOR_BGR2RGB)
                    qim = np2qimage(rgb_out)
                    self.imFrame.image = qim
                    self.imFrame.showImageOnScene(qim)

        QApplication.processEvents()
        
    def findDisk(self):
        """Find the large disk in the center of the image using ??.
        """
        print("findDisk(..) function is not ready yet.")
        
    def findRedSector(self):
        """Find red sector for disc in active image using ??.
        """
        print("findRedSector(..) function is not ready yet.")
        
    def findSpeed(self):
        """Find speed for disk using ??.
        """
        print("findSpeed(..) function is not ready yet.")


    def mousePressEvent(self, event):
        """Just print which mouse button has been pressed in main window.
        Note that the frame catches most mouse events, so this does only happen
        when mouse is on the bottom of the main window
        Normally we are fine if this function does nothing.
        """
        if (event.button() == Qt_LeftButton):
            print("MainWindow: LeftButton pressed at:  " + str(event.pos()))
        if (event.button() == Qt_RightButton):
            print("MainWindow: RightButton pressed at: " + str(event.pos()))

    def resizeEvent(self, arg1):
        """Make the size of the frame follow any changes in the size of the main window.
        This method is a 'slot' that is called whenever the size of the main window changes.
        """
        self.imFrame.setGeometry( 10, 30, self.width()-20, self.height()-40 ) 

#end class MainWindow

if __name__ == '__main__':
    print( f"{_fileName}: (version {_version}) and using Qt {QT_VERSION_STR}" )
    mainApp = QApplication(sys.argv)
    if (len(sys.argv) >= 2):
        fn = sys.argv[1]
        mainWin = MainWindow(fName=fn)    # may start with file name
    else:
        mainWin = MainWindow()
    mainWin.show()
    if qt6Exist:
        sys.exit(mainApp.exec())
    else:
        sys.exit(mainApp.exec_())

